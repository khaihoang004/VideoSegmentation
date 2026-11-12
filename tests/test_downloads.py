import hashlib
import io
import json
import socket
import tarfile
import tempfile
import threading
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from videosegmentation.cli import main
from videosegmentation.downloads import download_hf, download_url
from videosegmentation.storage import dataset_directory, extract_archive

PAYLOAD = bytes(range(256)) * 8192
ETAG = '"fixture-v1"'


class DownloadHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    seen = []
    interruptions = 0

    def log_message(self, *args):
        pass

    def do_GET(self):
        type(self).seen.append((self.path, self.headers.get("Range"), self.headers.get("If-Range")))
        if self.path == "/missing.zip":
            self.send_error(404)
            return
        if self.path == "/page":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", "5")
            self.end_headers()
            self.wfile.write(b"login")
            return
        offset = int(self.headers["Range"][6:-1]) if self.headers.get("Range") else 0
        if self.path == "/ignore.bin" or self.headers.get("If-Range") not in (None, ETAG):
            offset = 0
        if self.path == "/invalid.bin" and offset:
            self.send_response(206)
            self.send_header("Content-Range", f"bytes 0-{len(PAYLOAD)-1}/{len(PAYLOAD)}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if offset >= len(PAYLOAD):
            self.send_response(416)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(206 if offset else 200)
        if offset:
            self.send_header("Content-Range", f"bytes {offset}-{len(PAYLOAD)-1}/{len(PAYLOAD)}")
        self.send_header("Content-Length", str(len(PAYLOAD) - offset))
        self.send_header("ETag", ETAG)
        self.end_headers()
        if self.path == "/disconnect.bin" and not type(self).interruptions:
            type(self).interruptions += 1
            self.wfile.write(PAYLOAD[:1200000])
            self.wfile.flush()
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        self.wfile.write(PAYLOAD[offset:])


class HTTPDownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), DownloadHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        DownloadHandler.seen.clear()
        DownloadHandler.interruptions = 0
        self.stdout = redirect_stdout(io.StringIO())
        self.stderr = redirect_stderr(io.StringIO())
        self.stdout.__enter__()
        self.stderr.__enter__()

    def tearDown(self):
        self.stderr.__exit__(None, None, None)
        self.stdout.__exit__(None, None, None)
        self.temp.cleanup()

    def seed_partial(self, route, data=PAYLOAD[:10000], etag=ETAG):
        url = self.base + route
        name = route[1:]
        (self.directory / (name + ".part")).write_bytes(data)
        (self.directory / (name + ".part.json")).write_text(json.dumps({
            "source": hashlib.sha256(url.encode()).hexdigest(), "etag": etag,
        }))
        return url

    def test_download_checksum_skip_and_cli_layout(self):
        digest = hashlib.sha256(PAYLOAD).hexdigest()
        args = ["ha4m", "--root", str(self.directory), "--url", self.base + "/data.bin", "--sha256", digest]
        self.assertEqual(main(args), 0)
        result = self.directory / "HA4M/raw/data.bin"
        self.assertEqual(result.read_bytes(), PAYLOAD)
        self.assertEqual(main(args), 0)
        self.assertEqual(len(DownloadHandler.seen), 1)
        self.assertFalse(result.with_name("data.bin.part").exists())

    def test_resume_valid_range(self):
        result = download_url(self.seed_partial("/resume.bin"), self.directory)
        self.assertEqual(result.read_bytes(), PAYLOAD)
        self.assertEqual(DownloadHandler.seen[0][1:], ("bytes=10000-", ETAG))

    def test_server_ignoring_range_restarts_without_appending(self):
        result = download_url(self.seed_partial("/ignore.bin"), self.directory)
        self.assertEqual(result.read_bytes(), PAYLOAD)

    def test_changed_etag_restarts(self):
        result = download_url(self.seed_partial("/changed.bin", data=b"old data", etag='"old"'), self.directory)
        self.assertEqual(result.read_bytes(), PAYLOAD)

    def test_no_validator_restarts(self):
        result = download_url(self.seed_partial("/no-validator.bin", etag=None), self.directory)
        self.assertEqual(result.read_bytes(), PAYLOAD)
        self.assertIsNone(DownloadHandler.seen[0][1])

    def test_interrupted_transfer_retries_and_resumes(self):
        with patch("videosegmentation.downloads.time.sleep"):
            result = download_url(self.base + "/disconnect.bin", self.directory)
        self.assertEqual(result.read_bytes(), PAYLOAD)
        self.assertTrue(DownloadHandler.seen[1][1].startswith("bytes="))

    def test_416_does_not_mark_incorrect_partial_complete(self):
        url = self.seed_partial("/full.bin", data=b"X" * len(PAYLOAD))
        with patch("videosegmentation.downloads.time.sleep"):
            result = download_url(url, self.directory)
        self.assertEqual(result.read_bytes(), PAYLOAD)
        self.assertIsNone(DownloadHandler.seen[1][1])

    def test_bad_range_rejected_without_touching_partial(self):
        url = self.seed_partial("/invalid.bin")
        with self.assertRaisesRegex(ValueError, "unexpected byte range"):
            download_url(url, self.directory)
        self.assertEqual((self.directory / "invalid.bin.part").read_bytes(), PAYLOAD[:10000])

    def test_different_partial_source_is_rejected(self):
        self.seed_partial("/resume.bin")
        with self.assertRaisesRegex(ValueError, "different URL"):
            download_url(self.base + "/different.bin", self.directory, filename="resume.bin")
        self.assertEqual(DownloadHandler.seen, [])

    def test_checksum_failure_never_promotes_partial(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            download_url(self.base + "/data.bin", self.directory, sha256="0" * 64)
        self.assertFalse((self.directory / "data.bin").exists())
        self.assertTrue((self.directory / "data.bin.part").exists())

    def test_html_and_404_fail_without_final_file(self):
        for route in ("/page", "/missing.zip"):
            with self.assertRaises(ValueError):
                download_url(self.base + route, self.directory)
            self.assertFalse((self.directory / route[1:]).exists())


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def make_archive(self, kind, member="nested/video.txt", link=False):
        archive = self.directory / ("data.zip" if kind == "zip" else "data.tar.gz")
        if kind == "zip":
            with zipfile.ZipFile(archive, "w") as bundle:
                info = zipfile.ZipInfo(member)
                if link:
                    info.create_system = 3
                    info.external_attr = 0o120777 << 16
                bundle.writestr(info, b"payload")
        else:
            with tarfile.open(archive, "w:gz") as bundle:
                info = tarfile.TarInfo(member)
                if link:
                    info.type = tarfile.SYMTYPE
                    info.linkname = "../../outside"
                    bundle.addfile(info)
                else:
                    info.size = 7
                    bundle.addfile(info, io.BytesIO(b"payload"))
        return archive

    def test_zip_and_tar_extraction_and_idempotent_rerun(self):
        for kind in ("zip", "tar"):
            archive = self.make_archive(kind)
            destination = self.directory / kind
            with redirect_stdout(io.StringIO()):
                extract_archive(archive, destination)
                extract_archive(archive, destination)
            self.assertEqual((destination / "nested/video.txt").read_bytes(), b"payload")
            self.assertTrue(archive.exists())

    def test_traversal_and_links_leave_no_extracted_output(self):
        for kind in ("zip", "tar"):
            for name, link in (("../escaped.txt", False), ("/absolute.txt", False), ("link", True), ("C:/escape", False)):
                with self.subTest(kind=kind, name=name):
                    archive = self.make_archive(kind, name, link)
                    destination = self.directory / "output"
                    with self.assertRaises(ValueError):
                        extract_archive(archive, destination)
                    self.assertFalse(destination.exists())
                    self.assertFalse((self.directory / "escaped.txt").exists())

    def test_existing_output_is_not_overwritten(self):
        archive = self.make_archive("zip")
        destination = self.directory / "output"
        destination.mkdir()
        (destination / "keep").write_text("untouched")
        with self.assertRaisesRegex(ValueError, "already exists"):
            extract_archive(archive, destination)
        self.assertEqual((destination / "keep").read_text(), "untouched")

    def test_drive_mount_guard_and_names(self):
        with patch("videosegmentation.storage.Path.is_dir", return_value=False):
            with self.assertRaisesRegex(ValueError, "not mounted"):
                dataset_directory("/content/drive/MyDrive/Datasets", "Demo")
        for name in ("../escape", "/absolute", ".", "..", "with/slash"):
            with self.assertRaises(ValueError):
                dataset_directory(self.directory, name)

    def test_dataset_symlink_escape(self):
        outside = self.directory / "outside"
        outside.mkdir()
        root = self.directory / "root"
        root.mkdir()
        (root / "Demo").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            dataset_directory(root, "Demo")


class ProviderTests(unittest.TestCase):
    def test_hf_patterns_and_direct_storage_arguments(self):
        import huggingface_hub

        with patch.object(huggingface_hub.HfApi, "list_repo_files", return_value=["train/a.zip", "test/b.zip", "README.md"]):
            with patch.object(huggingface_hub, "snapshot_download", return_value="/tmp/selected/raw") as download:
                download_hf("owner/dataset", Path("/tmp/selected/raw"), "fixed-revision", ["*.zip"], ["test/*"], 2)
                self.assertEqual(download.call_args.kwargs["local_dir"], "/tmp/selected/raw")
                self.assertEqual(download.call_args.kwargs["revision"], "fixed-revision")
                download.reset_mock()
                download_hf("owner/dataset", Path("/tmp/selected/raw"), "main", ["*.zip"], None, 2, list_only=True)
                download.assert_not_called()
                with self.assertRaisesRegex(ValueError, "No files match"):
                    download_hf("owner/dataset", Path("/tmp/selected/raw"), "main", ["*.mp4"], None, 2)

    def test_drive_provider_options(self):
        import gdown
        from videosegmentation.downloads import download_drive

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with patch.object(gdown, "download", return_value=str(path / "data.zip")) as download:
                download_drive("https://drive.google.com/file/d/example/view", path, "data.zip", False, None)
                self.assertTrue(download.call_args.kwargs["resume"])
                self.assertEqual(download.call_args.kwargs["output"], str(path / "data.zip"))
            with patch.object(gdown, "download_folder", return_value=[]) as folder:
                download_drive("https://drive.google.com/drive/folders/example", path, None, True, None)
                self.assertTrue(folder.call_args.kwargs["resume"])
            with self.assertRaises(ValueError):
                download_drive("https://drive.google.com/file/d/example/view", path, "../escape", False, None)


if __name__ == "__main__":
    unittest.main()
