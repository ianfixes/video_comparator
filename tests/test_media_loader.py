"""Unit tests for MediaLoader class."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import wx

from video_comparator.errors.error_handler import ErrorHandler
from video_comparator.media.media_loader import MediaLoader
from video_comparator.media.video_metadata import (
    MetadataExtractionError,
    NoVideoStreamError,
    UnsupportedFormatError,
    VideoMetadata,
)


class TestMediaLoader(unittest.TestCase):
    """Test cases for MediaLoader class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.error_handler = MagicMock(spec=ErrorHandler)
        self.loader = MediaLoader(self.error_handler)
        self.sample_data_dir = Path(__file__).parent / "sample_data"

    def test_file_selection_dialog_creates_file_dialog(self) -> None:
        """Test file selection dialog creates wx.FileDialog with correct parameters."""
        parent = MagicMock(spec=wx.Window)

        with patch("video_comparator.media.media_loader.wx.FileDialog") as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.ShowModal.return_value = wx.ID_CANCEL
            mock_dialog_class.return_value = mock_dialog

            result = self.loader._show_file_dialog(parent)

            mock_dialog_class.assert_called_once()
            call_args = mock_dialog_class.call_args
            self.assertEqual(call_args[0][0], parent)
            self.assertEqual(call_args[1]["message"], "Select a video file")
            self.assertEqual(call_args[1]["style"], wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
            mock_dialog.ShowModal.assert_called_once()
            mock_dialog.Destroy.assert_called_once()
            self.assertIsNone(result)

    def test_file_selection_dialog_returns_path_on_ok(self) -> None:
        """Test file selection dialog returns path when user clicks OK."""
        parent = MagicMock(spec=wx.Window)
        test_path = "/test/path/video.avi"

        with patch("video_comparator.media.media_loader.wx.FileDialog") as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.ShowModal.return_value = wx.ID_OK
            mock_dialog.GetPath.return_value = test_path
            mock_dialog_class.return_value = mock_dialog

            result = self.loader._show_file_dialog(parent)

            self.assertEqual(result, Path(test_path))
            mock_dialog.GetPath.assert_called_once()

    def test_file_selection_dialog_returns_none_on_cancel(self) -> None:
        """Test file selection dialog returns None when user cancels."""
        parent = MagicMock(spec=wx.Window)

        with patch("video_comparator.media.media_loader.wx.FileDialog") as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.ShowModal.return_value = wx.ID_CANCEL
            mock_dialog_class.return_value = mock_dialog

            result = self.loader._show_file_dialog(parent)

            self.assertIsNone(result)

    def test_validate_file_exists_with_existing_file(self) -> None:
        """Test file validation with existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            try:
                result = self.loader._validate_file_exists(tmp_path)
                self.assertTrue(result)
                self.error_handler.handle_error.assert_not_called()
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

    def test_validate_file_exists_with_missing_file(self) -> None:
        """Test file validation with missing file (error handling)."""
        missing_path = Path("/nonexistent/file.avi")
        result = self.loader._validate_file_exists(missing_path)
        self.assertFalse(result)
        self.error_handler.handle_error.assert_called_once()
        error = self.error_handler.handle_error.call_args[0][0]
        self.assertIsInstance(error, FileNotFoundError)

    def test_validate_file_readable_with_readable_file(self) -> None:
        """Test file validation with readable file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            try:
                result = self.loader._validate_file_readable(tmp_path)
                self.assertTrue(result)
                self.error_handler.handle_error.assert_not_called()
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

    def test_validate_file_readable_with_directory(self) -> None:
        """Test file validation with directory (error handling)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            result = self.loader._validate_file_readable(dir_path)
            self.assertFalse(result)
            self.error_handler.handle_error.assert_called_once()
            error = self.error_handler.handle_error.call_args[0][0]
            self.assertIsInstance(error, ValueError)

    def test_metadata_extraction_integration(self) -> None:
        """Test metadata extraction integration."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        with patch.object(self.loader, "_show_file_dialog", return_value=avi_file):
            with patch.object(self.loader, "_validate_file_exists", return_value=True):
                with patch.object(self.loader, "_validate_file_readable", return_value=True):
                    metadata = self.loader.load_video_file()

                    self.assertIsNotNone(metadata)
                    if metadata is not None:
                        self.assertIsInstance(metadata, VideoMetadata)
                        self.assertEqual(metadata.file_path, avi_file)

    def test_error_handling_for_files_with_no_video_stream(self) -> None:
        """Test error handling for files with no video stream."""
        with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            try:
                with patch.object(self.loader, "_show_file_dialog", return_value=tmp_path):
                    with patch.object(self.loader, "_validate_file_exists", return_value=True):
                        with patch.object(self.loader, "_validate_file_readable", return_value=True):
                            with patch("video_comparator.media.media_loader.VideoMetadata.from_path") as mock_from_path:
                                mock_from_path.side_effect = NoVideoStreamError("No video stream found")
                                metadata = self.loader.load_video_file()

                                self.assertIsNone(metadata)
                                self.error_handler.handle_error.assert_called()
                                error = self.error_handler.handle_error.call_args[0][0]
                                self.assertIsInstance(error, NoVideoStreamError)
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

    def test_successful_load_returns_video_metadata(self) -> None:
        """Test successful load returns VideoMetadata."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = self.loader.load_video_file_from_path(avi_file)

        self.assertIsNotNone(metadata)
        if metadata is not None:
            self.assertIsInstance(metadata, VideoMetadata)
            self.assertEqual(metadata.file_path, avi_file)
            self.assertGreater(metadata.duration, 0)
            self.assertGreater(metadata.fps, 0)
            self.assertGreater(metadata.width, 0)
            self.assertGreater(metadata.height, 0)

    def test_load_video_file_cancelled_returns_none(self) -> None:
        """Test load_video_file returns None when user cancels dialog."""
        with patch.object(self.loader, "_show_file_dialog", return_value=None):
            metadata = self.loader.load_video_file()
            self.assertIsNone(metadata)
            self.error_handler.handle_error.assert_not_called()

    def test_load_video_file_from_path_with_missing_file(self) -> None:
        """Test load_video_file_from_path with missing file."""
        missing_path = Path("/nonexistent/file.avi")
        metadata = self.loader.load_video_file_from_path(missing_path)
        self.assertIsNone(metadata)
        self.error_handler.handle_error.assert_called_once()

    def test_load_video_file_from_path_with_unreadable_file(self) -> None:
        """Test load_video_file_from_path with unreadable file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            metadata = self.loader.load_video_file_from_path(dir_path)
            self.assertIsNone(metadata)
            self.error_handler.handle_error.assert_called()

    def test_load_video_file_from_path_with_unsupported_format(self) -> None:
        """Test load_video_file_from_path with unsupported format."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            try:
                metadata = self.loader.load_video_file_from_path(tmp_path)
                self.assertIsNone(metadata)
                self.error_handler.handle_error.assert_called()
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()

    def test_load_video_file_handles_metadata_extraction_error(self) -> None:
        """Test load_video_file handles MetadataExtractionError."""
        test_path = Path("/test/video.avi")

        with patch.object(self.loader, "_show_file_dialog", return_value=test_path):
            with patch.object(self.loader, "_validate_file_exists", return_value=True):
                with patch.object(self.loader, "_validate_file_readable", return_value=True):
                    with patch("video_comparator.media.media_loader.VideoMetadata.from_path") as mock_from_path:
                        mock_from_path.side_effect = MetadataExtractionError("Extraction failed")
                        metadata = self.loader.load_video_file()

                        self.assertIsNone(metadata)
                        self.error_handler.handle_error.assert_called()
                        error = self.error_handler.handle_error.call_args[0][0]
                        self.assertIsInstance(error, MetadataExtractionError)

    def test_load_video_file_handles_file_not_found_error(self) -> None:
        """Test load_video_file handles FileNotFoundError from metadata extraction."""
        test_path = Path("/test/video.avi")

        with patch.object(self.loader, "_show_file_dialog", return_value=test_path):
            with patch.object(self.loader, "_validate_file_exists", return_value=True):
                with patch.object(self.loader, "_validate_file_readable", return_value=True):
                    with patch("video_comparator.media.media_loader.VideoMetadata.from_path") as mock_from_path:
                        mock_from_path.side_effect = FileNotFoundError("File not found")
                        metadata = self.loader.load_video_file()

                        self.assertIsNone(metadata)
                        self.error_handler.handle_error.assert_called()
                        error = self.error_handler.handle_error.call_args[0][0]
                        self.assertIsInstance(error, FileNotFoundError)

    def test_load_video_file_handles_unsupported_format_error(self) -> None:
        """Test load_video_file handles UnsupportedFormatError from metadata extraction."""
        test_path = Path("/test/video.avi")

        with patch.object(self.loader, "_show_file_dialog", return_value=test_path):
            with patch.object(self.loader, "_validate_file_exists", return_value=True):
                with patch.object(self.loader, "_validate_file_readable", return_value=True):
                    with patch("video_comparator.media.media_loader.VideoMetadata.from_path") as mock_from_path:
                        mock_from_path.side_effect = UnsupportedFormatError("Format not supported")
                        metadata = self.loader.load_video_file()

                        self.assertIsNone(metadata)
                        self.error_handler.handle_error.assert_called()
                        error = self.error_handler.handle_error.call_args[0][0]
                        self.assertIsInstance(error, UnsupportedFormatError)

    def test_is_plausible_video_path_accepts_known_suffixes(self) -> None:
        """Known video extensions are accepted case-insensitively."""
        self.assertTrue(self.loader.is_plausible_video_path(Path("clip.MP4")))
        self.assertTrue(self.loader.is_plausible_video_path(Path("/a/b.avi")))
        self.assertTrue(self.loader.is_plausible_video_path(Path("x.mkv")))

    def test_is_plausible_video_path_rejects_non_video_suffix(self) -> None:
        """Non-video extensions are rejected before opening the file."""
        self.assertFalse(self.loader.is_plausible_video_path(Path("notes.txt")))
        self.assertFalse(self.loader.is_plausible_video_path(Path("data.pdf")))
