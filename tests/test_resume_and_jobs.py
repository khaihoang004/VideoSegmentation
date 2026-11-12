import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from videosegmentation import extraction
from videosegmentation.cli import main
from videosegmentation.storage import extract_archive


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.archive = self.root / "fixture.zip"
        with zipfile.ZipFile(self.archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for i in range(12):
                bundle.writestr(f"clips/{i:02}.mp4", bytes([i]) * 10000)
        self.destination = self.root / "output"
        self.workdir = self.root / ".output.extracting"
        self.stdout = redirect_stdout(io.StringIO())
        self.stdout.__enter__()

    def tearDown(self):
        self.stdout.__exit__(None, None, None)
        self.temp.cleanup()

    def interrupt_second_file(self):
        original = extraction._write_member
        calls = []

        def interrupted(*args, **kwargs):
            calls.append(args[2])
            if len(calls) == 2:
                raise KeyboardInterrupt()
            return original(*args, **kwargs)

        with patch.object(extraction, "_write_member", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                extract_archive(self.archive, self.destination)

    def test_resume_preserves_completed_files_after_interrupt(self):
        self.interrupt_second_file()
        first = self.workdir / "clips/00.mp4"
        modified = first.stat().st_mtime_ns
        self.assertFalse(self.destination.exists())
        extract_archive(self.archive, self.destination)
        self.assertEqual((self.destination / "clips/00.mp4").stat().st_mtime_ns, modified)
        self.assertEqual(len(list((self.destination / "clips").iterdir())), 12)
        self.assertFalse(self.workdir.exists())

    def test_partial_file_is_rewritten_and_not_treated_as_complete(self):
        self.interrupt_second_file()
        (self.workdir / "clips/01.mp4").write_bytes(b"incomplete")
        extract_archive(self.archive, self.destination)
        self.assertEqual((self.destination / "clips/01.mp4").read_bytes(), b"\x01" * 10000)

    def test_truncated_checkpoint_line_does_not_prevent_resume(self):
        self.interrupt_second_file()
        with (self.workdir / extraction.JOURNAL).open("a") as journal:
            journal.write('{"name": "interrupted')
        extract_archive(self.archive, self.destination)
        self.assertTrue((self.destination / extraction.COMPLETE).exists())

    def test_crc_verification_repairs_same_size_corruption(self):
        extract_archive(self.archive, self.destination)
        first = self.destination / "clips/00.mp4"
        first.write_bytes(b"bad!" * 2500)
        extract_archive(self.archive, self.destination, verify_existing=True)
        self.assertEqual(first.read_bytes(), b"\x00" * 10000)

    def test_parallel_zip_matches_archive_contents(self):
        extract_archive(self.archive, self.destination, workers=2)
        for i in range(12):
            self.assertEqual((self.destination / f"clips/{i:02}.mp4").read_bytes(), bytes([i]) * 10000)

    def test_filter_can_be_expanded_without_rewriting_existing_files(self):
        extract_archive(self.archive, self.destination, include=["clips/00.mp4"])
        first = self.destination / "clips/00.mp4"
        modified = first.stat().st_mtime_ns
        self.assertEqual(len(list((self.destination / "clips").iterdir())), 1)
        extract_archive(self.archive, self.destination)
        self.assertEqual(first.stat().st_mtime_ns, modified)
        self.assertEqual(len(list((self.destination / "clips").iterdir())), 12)

    def test_no_filter_matches_does_not_mark_extraction_complete(self):
        with self.assertRaisesRegex(ValueError, "No archive files match"):
            extract_archive(self.archive, self.destination, include=["*.csv"])
        self.assertFalse((self.destination / extraction.COMPLETE).exists())

    def test_changed_archive_does_not_reuse_partial_state(self):
        self.interrupt_second_file()
        with self.archive.open("ab") as archive:
            archive.write(b"changed")
        with self.assertRaisesRegex(ValueError, "different archive"):
            extract_archive(self.archive, self.destination)

    def test_same_runtime_lock_prevents_duplicate_extraction(self):
        with extraction._lock(self.destination):
            with self.assertRaisesRegex(ValueError, "already running"):
                extract_archive(self.archive, self.destination)

    def test_legacy_complete_ikea_marker_is_kept(self):
        self.destination.mkdir()
        signature = {"archive": self.archive.name, "size": self.archive.stat().st_size, "mtime_ns": self.archive.stat().st_mtime_ns}
        (self.destination / extraction.COMPLETE).write_text(json.dumps(signature))
        with patch.object(extraction, "_zip_extract", side_effect=AssertionError("must keep completed dataset")):
            self.assertEqual(extract_archive(self.archive, self.destination), self.destination)

    def test_tar_resume_skips_completed_writes(self):
        archive = self.root / "fixture.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            for name in ("one.txt", "two.txt"):
                info = tarfile.TarInfo(name)
                info.size = 7
                bundle.addfile(info, io.BytesIO(b"payload"))
        original = extraction._write_member
        count = 0

        def interrupted(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise KeyboardInterrupt()
            return original(*args, **kwargs)

        with patch.object(extraction, "_write_member", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                extract_archive(archive, self.destination)
        modified = (self.workdir / "one.txt").stat().st_mtime_ns
        extract_archive(archive, self.destination)
        self.assertEqual((self.destination / "one.txt").stat().st_mtime_ns, modified)
        self.assertEqual((self.destination / "two.txt").read_bytes(), b"payload")

    def test_hard_kill_recovers_unjournaled_completed_file(self):
        script = """
import time
from pathlib import Path
from videosegmentation import extraction
original = extraction._write_member
def slow(*args, **kwargs):
    result = original(*args, **kwargs)
    time.sleep(1)
    return result
extraction._write_member = slow
extraction.extract_archive(Path(__import__('sys').argv[1]), Path(__import__('sys').argv[2]))
"""
        process = subprocess.Popen([sys.executable, "-c", script, str(self.archive), str(self.destination)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        first = self.workdir / "clips/00.mp4"
        try:
            deadline = time.monotonic() + 8
            while not first.exists() and time.monotonic() < deadline:
                if process.poll() is not None:
                    self.fail("Extraction child stopped before producing the first file")
                time.sleep(0.02)
            self.assertTrue(first.exists())
            modified = first.stat().st_mtime_ns
        finally:
            process.kill()
            process.wait(timeout=5)
        extract_archive(self.archive, self.destination)
        self.assertEqual((self.destination / "clips/00.mp4").stat().st_mtime_ns, modified)


class JobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.archive = self.root / "fixture.zip"
        with zipfile.ZipFile(self.archive, "w") as bundle:
            bundle.writestr("data.txt", "background fixture")

    def tearDown(self):
        self.temp.cleanup()

    def wait_for_job(self):
        directory = self.root / "JobDataset/jobs"
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            records = sorted(directory.glob("*.json"))
            if records:
                data = json.loads(records[-1].read_text())
                if data["status"] in ("completed", "failed"):
                    return data
            time.sleep(0.05)
        self.fail("Background job did not finish before the test deadline")

    def test_real_background_cli_extracts_and_persists_status_and_log(self):
        with redirect_stdout(io.StringIO()):
            result = main(["extract", str(self.archive), "--name", "JobDataset", "--root", str(self.root), "--background"])
        self.assertEqual(result, 0)
        job = self.wait_for_job()
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["exit_code"], 0)
        self.assertIn("Extracted:", Path(job["log"]).read_text())
        self.assertEqual((self.root / "JobDataset/extracted/fixture/data.txt").read_text(), "background fixture")
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["status", "--name", "JobDataset", "--root", str(self.root)]), 0)
        self.assertIn("completed", output.getvalue())

    def test_failed_background_job_is_reported_as_failed(self):
        with redirect_stdout(io.StringIO()):
            main(["extract", str(self.root / "missing.zip"), "--name", "JobDataset", "--root", str(self.root), "--background"])
        job = self.wait_for_job()
        self.assertEqual(job["status"], "failed")
        self.assertEqual(job["exit_code"], 1)

    def test_ikea_video_only_keeps_labels_and_omits_frames(self):
        source = self.root / "source"
        contents = {
            "data/ikea_asm_dataset_RGB_top.zip": {"video/scan_video.avi": b"video", "frames/00001.jpg": b"image"},
            "data/utility_files.zip": {"splits.txt": b"splits"},
            "annotations/action_annotations.zip": {"actions.csv": b"labels"},
        }
        for name, members in contents.items():
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(path, "w") as bundle:
                for member, data in members.items():
                    bundle.writestr(member, data)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["ikea_asm", "--source-dir", str(source), "--root", str(self.root), "--video-only", "--extract-workers", "2"]), 0)
        extracted = self.root / "IKEA_ASM/extracted"
        self.assertTrue((extracted / "ikea_asm_dataset_RGB_top/video/scan_video.avi").is_file())
        self.assertFalse((extracted / "ikea_asm_dataset_RGB_top/frames/00001.jpg").exists())
        self.assertTrue((extracted / "action_annotations/actions.csv").is_file())
        self.assertTrue((extracted / "utility_files/splits.txt").is_file())


if __name__ == "__main__":
    unittest.main()
