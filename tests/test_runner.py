import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from downloaders import DOWNLOADERS
from videosegmentation.cli import build_parser, main


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.stdout = redirect_stdout(io.StringIO())
        self.stderr = redirect_stderr(io.StringIO())
        self.stdout.__enter__()
        self.stderr.__enter__()

    def tearDown(self):
        self.stderr.__exit__(None, None, None)
        self.stdout.__exit__(None, None, None)
        self.temp.cleanup()

    def test_list_is_offline_and_does_not_create_dataset_directories(self):
        with patch("requests.get", side_effect=AssertionError("Unexpected network access")):
            self.assertEqual(main(["--list"]), 0)
            self.assertEqual(main(["ikea_asm", "--list-files"]), 0)
            self.assertEqual(main(["ha4m", "--list-files"]), 0)
            self.assertEqual(main(["repcount", "--list-files"]), 0)

    def test_runner_delegates_to_selected_dataset(self):
        adapter = DOWNLOADERS["industreal"]
        with patch.object(adapter, "run") as run:
            self.assertEqual(main(["industreal", "--part", "rgb", "--root", str(self.root)]), 0)
            self.assertEqual(run.call_args.args[0].part, "rgb")

    def test_assembly_camera_selection(self):
        with patch("downloaders.assembly101.download_hf", return_value=[]) as download:
            self.assertEqual(main(["assembly101", "--part", "videos", "--view", "v1", "--root", str(self.root)]), 0)
            self.assertEqual(download.call_args.args[0], "cvml-nus/assembly101")
            self.assertEqual(download.call_args.args[3], ["recordings/*/C10095_rgb.mp4"])

    def test_assembly_bad_view_part_combination_fails_before_download(self):
        with patch("downloaders.assembly101.download_hf") as download:
            self.assertEqual(main(["assembly101", "--part", "annotations", "--view", "v1", "--root", str(self.root)]), 1)
            download.assert_not_called()

    def test_breakfast_annotations_and_videos_are_different_sources(self):
        with patch("downloaders.breakfast.download_hf", return_value=[]) as hub:
            self.assertEqual(main(["breakfast", "--root", str(self.root)]), 0)
            self.assertEqual(hub.call_args.args[3], ["segmentation_coarse.tar.gz", "segmentation_fine.tar.gz"])
        with patch("downloaders.breakfast.download_drive", return_value=[]) as drive:
            self.assertEqual(main(["breakfast", "--part", "videos", "--root", str(self.root)]), 0)
            self.assertIn("1jgSoof1AatiDRpGY091qd4TEKF-BUt6I", drive.call_args.args[0])

    def test_industreal_list_uses_metadata_filters_without_downloading(self):
        response = Mock()
        response.json.return_value = {"version": 2, "files": [
            {"name": "train_p1.zip", "size": 100},
            {"name": "val_p1.zip", "size": 100},
        ]}
        with patch("downloaders.industreal.requests.get", return_value=response):
            with patch("downloaders.industreal.download_url") as download:
                self.assertEqual(main(["industreal", "--part", "train", "--list-files"]), 0)
                download.assert_not_called()

    def test_ikea_deduplicates_requested_packages(self):
        with patch("downloaders.ikea_asm.download_drive", return_value=[]) as download:
            self.assertEqual(main(["ikea_asm", "--source", "download", "--part", "annotations", "--part", "annotations", "--root", str(self.root)]), 0)
            self.assertEqual(download.call_count, 1)

    def test_direct_adapter_requires_an_explicit_file_link(self):
        self.assertEqual(main(["ha4m", "--root", str(self.root)]), 1)
        self.assertFalse((self.root / "HA4M").exists())

    def test_each_adapter_owns_its_cli_options(self):
        parser = build_parser()
        self.assertEqual(parser.parse_args(["assembly101", "--view", "fixed"]).view, "fixed")
        self.assertEqual(parser.parse_args(["industreal", "--part", "train"]).part, "train")
        with self.assertRaises(SystemExit):
            parser.parse_args(["industreal", "--view", "fixed"])

    def test_extraction_symlink_escape_is_rejected(self):
        dataset = self.root / "IndustReal"
        dataset.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        (dataset / "extracted").symlink_to(outside, target_is_directory=True)
        self.assertEqual(main(["extract", "missing.zip", "--name", "IndustReal", "--root", str(self.root)]), 1)
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
