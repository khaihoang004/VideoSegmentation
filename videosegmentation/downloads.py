"""Download providers. Large payloads and partial files stay in the destination."""

import fnmatch
import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

import requests
from tqdm import tqdm

from .storage import safe_filename


def verify_sha256(path: Path, expected: str | None) -> None:
    if expected is None:
        return
    if not re.fullmatch(r"[a-fA-F0-9]{64}", expected):
        raise ValueError("--sha256 must contain 64 hexadecimal characters.")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected.lower():
        raise ValueError(f"SHA-256 mismatch: {path}. The file was retained for inspection.")
    print(f"SHA-256 verified: {path.name}")


def download_url(url: str, directory: Path, filename: str | None = None, sha256: str | None = None) -> Path:
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Use an HTTP(S) direct download URL.")
    if parsed.hostname in ("drive.google.com", "docs.google.com"):
        raise ValueError("For Google Drive share links use the 'drive' command.")
    name = safe_filename(filename or unquote(parsed.path.rsplit("/", 1)[-1]))
    directory.mkdir(parents=True, exist_ok=True)
    final = directory / name
    if final.exists():
        verify_sha256(final, sha256)
        print(f"Already downloaded: {final}")
        return final
    partial = directory / (name + ".part")
    metadata_path = directory / (name + ".part.json")
    # Store a fingerprint rather than the URL, which may contain credentials.
    identity = hashlib.sha256(url.encode()).hexdigest()
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    if partial.exists() and metadata.get("source") != identity:
        raise ValueError(f"Partial download belongs to a different URL: {partial}. Use another --filename.")
    with requests.Session() as session:
        for attempt in range(3):
            size = partial.stat().st_size if partial.exists() else 0
            validator = metadata.get("etag") or metadata.get("last_modified")
            headers = {"Accept-Encoding": "identity"}
            if size and validator:
                headers.update({"Range": f"bytes={size}-", "If-Range": validator})
            else:
                size = 0
            try:
                with session.get(url, headers=headers, stream=True, timeout=(20, 60)) as response:
                    if response.status_code == 416:
                        # Never assume a partial file is complete based on a 416 response.
                        metadata = {}
                        continue
                    response.raise_for_status()
                    if response.status_code not in (200, 206):
                        raise ValueError(f"Unexpected HTTP status: {response.status_code}")
                    if response.headers.get("Content-Type", "").split(";")[0].lower() == "text/html":
                        raise ValueError("The URL returned an HTML page. Use the actual file download link.")
                    if response.headers.get("Content-Encoding", "identity").lower() not in ("", "identity"):
                        raise ValueError("Server ignored Accept-Encoding: identity; use a direct unencoded file URL.")
                    if response.status_code == 206:
                        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                        if not match or int(match[1]) != size or int(match[2]) != int(match[3]) - 1:
                            raise ValueError("Server returned an unexpected byte range; partial file was retained.")
                        total = int(match[3])
                    else:
                        size = 0  # Server ignored Range or If-Range detected a changed remote file.
                        length = response.headers.get("Content-Length")
                        total = int(length) if length is not None else None
                    etag = response.headers.get("ETag")
                    metadata = {
                        "source": identity,
                        "etag": etag if etag and not etag.startswith("W/") else None,
                        "last_modified": response.headers.get("Last-Modified"),
                    }
                    metadata_path.write_text(json.dumps(metadata) + "\n")
                    with partial.open("ab" if size else "wb") as output:
                        with tqdm(total=total, initial=size, unit="B", unit_scale=True, desc=name) as progress:
                            for chunk in response.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    output.write(chunk)
                                    progress.update(len(chunk))
                    if total is not None and partial.stat().st_size != total:
                        raise requests.ConnectionError("Downloaded size differs from the server's advertised size.")
                verify_sha256(partial, sha256)
                partial.replace(final)
                metadata_path.unlink(missing_ok=True)
                print(f"Downloaded: {final}")
                return final
            except requests.HTTPError as error:
                status = error.response.status_code
                if status < 500 or attempt == 2:
                    raise ValueError(f"HTTP {status}. Check the download link and access permissions.") from None
            except requests.RequestException:
                if attempt == 2:
                    raise ValueError(f"Download interrupted; partial data remains at {partial}. Run the same command to retry.") from None
            time.sleep(2 ** attempt)
    raise ValueError(f"Unable to complete download. Partial data remains at {partial}.")


def download_drive(url: str, directory: Path, filename: str | None, folder: bool, sha256: str | None) -> list[Path]:
    import gdown

    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ("drive.google.com", "docs.google.com"):
        raise ValueError("Use an HTTPS Google Drive share URL.")
    directory.mkdir(parents=True, exist_ok=True)
    if folder:
        if filename or sha256:
            raise ValueError("--filename and --sha256 apply to individual files, not folders.")
        result = gdown.download_folder(url=url, output=str(directory), quiet=False, resume=True)
        if result is None:
            raise ValueError("Google Drive folder download failed. Check sharing permissions and quota.")
        return [Path(path) for path in result]
    path = directory / safe_filename(filename) if filename else None
    if path is not None and path.exists():
        verify_sha256(path, sha256)
        print(f"Already downloaded: {path}")
        return [path]
    output = str(path) if path is not None else str(directory) + os.sep
    result = gdown.download(url=url, output=output, fuzzy=True, quiet=False, resume=True)
    if result is None:
        raise ValueError("Google Drive download failed. Check sharing permissions and quota.")
    result_path = Path(result)
    if result_path.resolve().parent != directory.resolve():
        raise ValueError("Google Drive returned a filename outside the download directory.")
    verify_sha256(result_path, sha256)
    return [result_path]


def download_hf(repo: str, directory: Path, revision: str, include: list[str] | None, exclude: list[str] | None, workers: int, list_only: bool = False) -> list[Path]:
    # Set before importing the Hub: Xet's optional chunk cache must also live on Drive.
    os.environ.setdefault("HF_XET_CACHE", str(directory / ".cache" / "xet"))
    from huggingface_hub import HfApi, snapshot_download

    files = HfApi().list_repo_files(repo_id=repo, repo_type="dataset", revision=revision)
    selected = [
        name for name in files
        if (not include or any(fnmatch.fnmatchcase(name, pattern) for pattern in include))
        and not (exclude and any(fnmatch.fnmatchcase(name, pattern) for pattern in exclude))
    ]
    if not selected:
        raise ValueError("No files match --include/--exclude at the selected dataset revision.")
    if list_only:
        print("\n".join(selected))
        print(f"{len(selected)} matching files. No dataset files were downloaded.")
        return []
    print(f"Downloading {len(selected)} files from dataset {repo} (revision: {revision})")
    snapshot_download(
        repo_id=repo, repo_type="dataset", revision=revision, local_dir=str(directory),
        allow_patterns=include, ignore_patterns=exclude, max_workers=workers,
    )
    return [directory / name for name in selected]
