import io
import subprocess
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from videosegmentation.cli import main
from videosegmentation.storage import find_archives
from downloaders.ikea_asm import IkeaASMDownloader


class DatasetSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "mounted-source"
        self.source.mkdir()
        self.output = self.root / "datasets"
        self.stdout = redirect_stdout(io.StringIO())
        self.stderr = redirect_stderr(io.StringIO())
        self.stdout.__enter__()
        self.stderr.__enter__()

    def tearDown(self):
        self.stderr.__exit__(None, None, None)
        self.stdout.__exit__(None, None, None)
        self.temp.cleanup()

    def archive(self, name="videos.zip"):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("recording/video.txt", "fixture data")
        return path

    def test_ikea_extracts_mounted_source_without_network_or_copy(self):
        archive = self.archive()
        args = ["ikea_asm", "--source-dir", str(self.source), "--root", str(self.output)]
        with patch("downloaders.ikea_asm.download_drive", side_effect=AssertionError("unexpected download")):
            self.assertEqual(main(args), 0)
            self.assertEqual(main(args), 0)
        self.assertEqual((self.output / "IKEA_ASM/extracted/videos/recording/video.txt").read_text(), "fixture data")
        self.assertTrue(archive.exists())
        self.assertFalse((self.output / "IKEA_ASM/raw/videos.zip").exists())

    def test_ikea_list_mounted_archives_does_not_extract(self):
        self.archive()
        self.assertEqual(main(["ikea_asm", "--source-dir", str(self.source), "--list-files", "--root", str(self.output)]), 0)
        self.assertFalse(self.output.exists())

    def publisher_archives(self):
        return [self.archive(name) for name in (
            "data/ikea_asm_dataset_RGB_top.zip",
            "data/utility_files.zip",
            "data/camera_params.zip",
            "data/ikea_asm_dataset_depth.zip",
            "data/ikea_asm_dataset_RGB_multiview.zip",
            "annotations/action_annotations.zip",
            "annotations/pose_annotations.zip",
            "trained_models/pt_models_action_recognition.zip",
        )]

    def test_ikea_publisher_default_extracts_only_rgb_labels_and_utilities(self):
        archives = self.publisher_archives()
        original = {path: path.read_bytes() for path in archives}
        self.assertEqual(main(["ikea_asm", "--source-dir", str(self.source), "--root", str(self.output)]), 0)
        extracted = self.output / "IKEA_ASM/extracted"
        self.assertEqual({path.name for path in extracted.iterdir()}, {
            "ikea_asm_dataset_RGB_top", "action_annotations", "utility_files",
        })
        self.assertEqual({path: path.read_bytes() for path in archives}, original)

    def test_ikea_default_source_follows_a_shortcut_to_read_only_archives(self):
        archives = self.publisher_archives()
        for path in archives:
            path.chmod(0o444)
        shortcut = self.root / "shortcut"
        shortcut.symlink_to(self.source, target_is_directory=True)
        with patch.object(IkeaASMDownloader, "default_source", shortcut):
            with patch("downloaders.ikea_asm.download_drive", side_effect=AssertionError("unexpected download")):
                self.assertEqual(main(["ikea_asm", "--root", str(self.output)]), 0)
        self.assertTrue((self.output / "IKEA_ASM/extracted/action_annotations/recording/video.txt").exists())
        self.assertTrue(shortcut.is_symlink())

    def test_ikea_publisher_part_selection_supports_multiple_parts(self):
        self.publisher_archives()
        args = ["ikea_asm", "--source-dir", str(self.source), "--part", "rgb-multi", "--part", "camera", "--root", str(self.output)]
        self.assertEqual(main(args), 0)
        self.assertEqual({p.name for p in (self.output / "IKEA_ASM/extracted").iterdir()}, {
            "ikea_asm_dataset_RGB_multiview", "camera_params",
        })

    def test_ikea_custom_include_finds_publisher_subfolders(self):
        self.publisher_archives()
        self.assertEqual(main(["ikea_asm", "--source-dir", str(self.source), "--include", "annotations/action*", "--root", str(self.output)]), 0)
        self.assertEqual({p.name for p in (self.output / "IKEA_ASM/extracted").iterdir()}, {"action_annotations"})

    def test_ikea_missing_selected_part_fails_before_extracting_rgb(self):
        self.archive("data/ikea_asm_dataset_RGB_top.zip")
        (self.source / "annotations").mkdir()
        self.assertEqual(main(["ikea_asm", "--source-dir", str(self.source), "--root", str(self.output)]), 1)
        self.assertFalse(self.output.exists())

    def test_ikea_parts_and_include_are_mutually_exclusive(self):
        self.publisher_archives()
        self.assertEqual(main(["ikea_asm", "--source-dir", str(self.source), "--part", "pose", "--include", "*", "--root", str(self.output)]), 1)
        self.assertFalse(self.output.exists())

    def test_mounted_selection_and_nested_archives(self):
        self.archive("nested/videos.zip")
        self.archive("labels.zip")
        self.assertEqual(find_archives(self.source, ["nested/*"], recursive=True), [self.source / "nested/videos.zip"])
        with self.assertRaises(ValueError):
            find_archives(self.source, ["nested/*"], recursive=False)

    def test_single_archive_source_is_supported(self):
        archive = self.archive()
        self.assertEqual(find_archives(archive), [archive])

    def test_duplicate_archive_names_are_rejected_before_extraction(self):
        self.archive("one/videos.zip")
        self.archive("two/videos.zip")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            find_archives(self.source, recursive=True)

    def test_repcount_and_fineaction_use_their_own_destination_names(self):
        self.archive()
        for dataset, folder in (("repcount", "RepCount"), ("fineaction", "FineAction")):
            self.assertEqual(main([dataset, "--source-dir", str(self.source), "--root", str(self.output)]), 0)
            self.assertTrue((self.output / folder / "extracted/videos/recording/video.txt").is_file())

    def test_source_modes_cannot_be_combined(self):
        for dataset in ("repcount", "fineaction"):
            self.assertEqual(main([dataset, "--source-dir", str(self.source), "--url", "https://example.com/archive.zip"]), 1)
        self.assertEqual(main(["ikea_asm", "--source-dir", str(self.source), "--source", "download"]), 1)

    def test_fineaction_source_listing_needs_no_sdk_or_network(self):
        with patch("downloaders.fineaction.subprocess.run", side_effect=AssertionError("unexpected SDK call")):
            self.assertEqual(main(["fineaction", "--part", "all", "--list-files"]), 0)

    def test_fineaction_sdk_uses_selected_path_and_drive_target(self):
        expected_raw = self.output / "FineAction/raw"

        def fake_sdk(command, **kwargs):
            self.assertEqual(command[1:3], ["dataset", "download"])
            self.assertEqual(command[command.index("--source-path") + 1], "/raw/annotations_gt.json")
            self.assertEqual(command[command.index("--target-path") + 1], str(expected_raw))
            self.assertEqual(kwargs["cwd"], expected_raw)
            self.assertTrue(Path(kwargs["env"]["TMPDIR"]).is_relative_to(expected_raw))
            (expected_raw / "annotations_gt.json").write_text('{"fixture": true}')
            return subprocess.CompletedProcess(command, 0)

        with patch("downloaders.fineaction.shutil.which", return_value="/test/openxlab"):
            with patch("downloaders.fineaction.subprocess.run", side_effect=fake_sdk):
                self.assertEqual(main(["fineaction", "--root", str(self.output)]), 0)

    def test_fineaction_sdk_failure_and_empty_output_are_not_success(self):
        args = ["fineaction", "--root", str(self.output)]
        with patch("downloaders.fineaction.shutil.which", return_value="/test/openxlab"):
            with patch("downloaders.fineaction.subprocess.run", side_effect=subprocess.CalledProcessError(1, "openxlab")):
                self.assertEqual(main(args), 1)
            with patch("downloaders.fineaction.subprocess.run", return_value=subprocess.CompletedProcess([], 0)):
                self.assertEqual(main(args), 1)

    def test_missing_mounted_source_is_not_silently_downloaded(self):
        with patch("downloaders.ikea_asm.download_drive") as download:
            self.assertEqual(main(["ikea_asm", "--root", str(self.output)]), 1)
            self.assertEqual(main(["ikea_asm", "--source-dir", str(self.source / "missing"), "--root", str(self.output)]), 1)
            download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
