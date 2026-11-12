"""Resumable extraction: atomic files, a batched journal and a persistent workdir."""

import fnmatch
import hashlib
import itertools
import json
import os
import stat
import tarfile
import tempfile
import threading
import time
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from .storage import archive_stem

STATE = ".videoseg-state.json"
JOURNAL = ".videoseg-progress.jsonl"
COMPLETE = ".videoseg-extracted.json"


def _read_json(path):
    return json.loads(path.read_text()) if path.is_file() else None


def _json_write(path, data):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False) + "\n")
    temporary.replace(path)


def _relative(name):
    member = PurePosixPath(name)
    if "\\" in name or "\x00" in name or member.is_absolute() or ".." in member.parts:
        raise ValueError(f"Unsafe archive member: {name!r}")
    if member.parts and (":" in member.parts[0] or any(p.startswith(".videoseg-") for p in member.parts)):
        raise ValueError(f"Unsafe or reserved archive member: {name!r}")
    return member.as_posix()


def _selected(name, include, exclude):
    return (not include or any(fnmatch.fnmatchcase(name, p) for p in include)) and not any(
        fnmatch.fnmatchcase(name, p) for p in exclude or []
    )


@contextmanager
def _lock(destination):
    # Local flock is reliable on Colab; Drive FUSE may not support advisory locks.
    # This prevents duplicate jobs within one runtime, not across multiple VMs.
    import fcntl

    locks = Path(tempfile.gettempdir()) / "videoseg-extraction-locks"
    locks.mkdir(exist_ok=True)
    key = hashlib.sha256(str(destination.resolve()).encode()).hexdigest()
    with (locks / (key + ".lock")).open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError(f"Another extraction is already running for {destination} in this runtime.") from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


class _Directories:
    def __init__(self, root):
        self.root = root
        self.known = {root}
        self.lock = threading.RLock()

    def ensure(self, directory):
        # Check each parent only once, instead of resolving every ancestor per file
        # over the Drive mount. Never traverse pre-existing archive symlinks.
        with self.lock:
            if directory in self.known:
                return
            if not directory.is_relative_to(self.root):
                raise ValueError("Archive directory escapes extraction root.")
            self.ensure(directory.parent)
            try:
                mode = directory.lstat().st_mode
                if not stat.S_ISDIR(mode):
                    raise ValueError(f"Expected a real directory: {directory}")
            except FileNotFoundError:
                directory.mkdir()
            self.known.add(directory)


class _Journal:
    def __init__(self, root, fresh=False):
        self.fresh = fresh
        self.records = {}
        path = root / JOURNAL
        if path.exists():
            with path.open() as source:
                for line in source:
                    try:
                        record = json.loads(line)
                        self.records[record["name"]] = record
                    except (ValueError, KeyError, TypeError):
                        # A killed runtime can leave an incomplete last record.
                        continue
        self.handle = path.open("a")
        # Separate a possible truncated final record from subsequent writes.
        self.handle.write("\n")
        self.pending = 0
        self.flushed_at = time.monotonic()

    def add(self, record):
        self.records[record["name"]] = record
        self.handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.pending += 1
        if self.pending >= 100 or time.monotonic() - self.flushed_at >= 5:
            self.handle.flush()
            self.pending = 0
            self.flushed_at = time.monotonic()

    def close(self):
        self.handle.close()


def _crc(path):
    value = 0
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value = zlib.crc32(block, value)
    return value


def _existing(root, name, size, expected_crc, record, verify, directories):
    target = root / name
    directories.ensure(target.parent)
    try:
        details = target.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(details.st_mode):
        raise ValueError(f"Expected a regular extracted file: {target}")
    if details.st_size != size:
        return None
    trusted = record and record.get("size") == size and (
        expected_crc is None or record.get("crc") == expected_crc
    )
    if trusted and not verify:
        return record
    checksum = expected_crc if expected_crc is not None else (record or {}).get("crc")
    if checksum is not None and _crc(target) == checksum:
        return {"name": name, "size": size, "crc": checksum}
    return None


def _write_member(source, root, name, size, directories):
    target = root / name
    directories.ensure(target.parent)
    temporary = target.with_name(".videoseg-part-" + target.name)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    count = checksum = 0
    with os.fdopen(os.open(temporary, flags, 0o600), "wb") as output:
        while block := source.read(1024 * 1024):
            output.write(block)
            checksum = zlib.crc32(block, checksum)
            count += len(block)
    if count != size:
        raise ValueError(f"Incomplete archive member: {name} ({count}/{size} bytes)")
    temporary.replace(target)
    return {"name": name, "size": count, "crc": checksum}


def _zip_extract(archive, workdir, journal, include, exclude, workers, verify):
    directories = _Directories(workdir)
    with zipfile.ZipFile(archive) as bundle:
        entries = []
        seen = set()
        for member in bundle.infolist():
            name = _relative(member.filename)
            kind = stat.S_IFMT(member.external_attr >> 16)
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError(f"Archive links/special files are not supported: {member.filename}")
            if member.is_dir():
                if not include and name != ".":
                    directories.ensure(workdir / name)
                continue
            if name in seen:
                raise ValueError(f"Duplicate archive output path: {name}")
            seen.add(name)
            if _selected(name, include, exclude):
                entries.append((name, member))
        if not entries and (include or exclude):
            raise ValueError("No archive files match the extraction filters. Adjust --extract-include/--extract-exclude or omit --video-only.")
        print(f"ZIP: {len(entries):,} selected files; {workers} worker(s); checking saved progress.", flush=True)
        completed = skipped = 0
        last_report = time.monotonic()

        def process(entry):
            name, member = entry
            record = journal.records.get(name)
            previous = None if journal.fresh else _existing(workdir, name, member.file_size, member.CRC, record, verify, directories)
            if previous:
                return previous, True
            with bundle.open(member) as source:
                return _write_member(source, workdir, name, member.file_size, directories), False

        def record_result(result):
            nonlocal completed, skipped, last_report
            record, reused = result
            if not reused or record["name"] not in journal.records:
                journal.add(record)
            completed += 1
            skipped += int(reused)
            if time.monotonic() - last_report >= 10:
                print(f"Progress: {completed:,}/{len(entries):,} files; {skipped:,} reused.", flush=True)
                last_report = time.monotonic()

        if workers == 1:
            for entry in entries:
                record_result(process(entry))
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                iterator = iter(entries)
                while batch := list(itertools.islice(iterator, workers * 2)):
                    # Bound outstanding work; do not queue millions of image files.
                    for future in as_completed([pool.submit(process, entry) for entry in batch]):
                        record_result(future.result())
        print(f"ZIP complete: {completed:,} files; {skipped:,} reused.", flush=True)


def _tar_extract(archive, workdir, journal, include, exclude, verify):
    directories = _Directories(workdir)
    completed = skipped = 0
    last_report = time.monotonic()
    seen = set()
    with tarfile.open(archive, "r|*") as bundle:
        for member in bundle:
            name = _relative(member.name)
            if member.isdir():
                if not include and name != ".":
                    directories.ensure(workdir / name)
                continue
            if not member.isfile():
                raise ValueError(f"Archive links/special files are not supported: {member.name}")
            if name in seen:
                raise ValueError(f"Duplicate archive output path: {name}")
            seen.add(name)
            if not _selected(name, include, exclude):
                continue
            previous = None if journal.fresh else _existing(workdir, name, member.size, None, journal.records.get(name), verify, directories)
            if previous:
                skipped += 1
            else:
                with bundle.extractfile(member) as source:
                    journal.add(_write_member(source, workdir, name, member.size, directories))
            completed += 1
            if time.monotonic() - last_report >= 10:
                print(f"TAR progress: {completed:,} files; {skipped:,} reused.", flush=True)
                last_report = time.monotonic()
    if not completed and (include or exclude):
        raise ValueError("No archive files match the extraction filters.")
    print(f"TAR complete: {completed:,} files; {skipped:,} reused. TAR resumes still read the compressed stream from the start.", flush=True)


def extract_archive(archive, destination, *, include=None, exclude=None, workers=1, verify_existing=False):
    archive = Path(archive).resolve(strict=True)
    archive_stem(archive)
    destination = Path(destination).absolute()
    if workers < 1 or workers > 8:
        raise ValueError("--extract-workers must be between 1 and 8.")
    info = archive.stat()
    signature = {"archive": archive.name, "size": info.st_size, "mtime_ns": info.st_mtime_ns}
    selection = {"archive": signature, "include": include or [], "exclude": exclude or []}
    with _lock(destination):
        if destination.is_symlink():
            raise ValueError("Extraction destination must not be a symlink.")
        old_marker = _read_json(destination / COMPLETE)
        # The previous release's completion marker denotes the entire archive.
        legacy_complete = old_marker == signature
        if not verify_existing and (legacy_complete or old_marker == selection):
            print(f"Already extracted: {destination}", flush=True)
            return destination
        staging = destination.parent / ("." + destination.name + ".extracting")
        workdir = destination if destination.exists() else staging
        if workdir.is_symlink():
            raise ValueError("Extraction work directory must not be a symlink.")
        state = _read_json(workdir / STATE)
        recognized_marker = legacy_complete or (isinstance(old_marker, dict) and old_marker.get("archive") == signature)
        if destination.exists() and state is None and not recognized_marker:
            raise ValueError(f"Extraction destination already exists: {destination}. Choose another --name or move it first.")
        if state is not None and state.get("archive") != signature:
            raise ValueError(f"Saved progress belongs to a different archive: {workdir}. Move it aside before continuing.")
        fresh = not workdir.exists()
        workdir.mkdir(parents=True, exist_ok=True)
        if state is None:
            _json_write(workdir / STATE, {"version": 2, "archive": signature})
        journal = _Journal(workdir, fresh=fresh)
        print(f"Saved progress: {len(journal.records):,} file records. Work directory: {workdir}", flush=True)
        try:
            if archive.name.lower().endswith(".zip"):
                _zip_extract(archive, workdir, journal, include, exclude, workers, verify_existing)
            else:
                _tar_extract(archive, workdir, journal, include, exclude, verify_existing)
        finally:
            # Keep complete files and flush their journal even on Ctrl+C/errors.
            journal.close()
        _json_write(workdir / COMPLETE, selection)
        if workdir != destination:
            os.rename(workdir, destination)
        print(f"Extracted: {destination}", flush=True)
        return destination
