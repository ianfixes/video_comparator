"""Unit tests for ErrorHandler class."""

import logging
import unittest
from unittest.mock import MagicMock, patch

import wx

from video_comparator.errors.error_handler import ErrorHandler, LogEntry


class TestErrorHandler(unittest.TestCase):
    """Test cases for ErrorHandler class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.parent_window = MagicMock(spec=wx.Window)

    def test_error_message_formatting(self) -> None:
        """Test error message formatting."""
        handler = ErrorHandler(self.parent_window, enable_logging=False)
        error = FileNotFoundError("Video file not found: test.mp4")
        message = handler._format_message(error)
        self.assertIn("Error (FileNotFoundError)", message)
        self.assertIn("test.mp4", message)

    def test_handle_error_shows_dialog_with_parent(self) -> None:
        """Test that handle_error shows dialog when parent window exists."""
        with patch("video_comparator.errors.error_handler.ErrorDialog") as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.show.return_value = wx.ID_OK
            mock_dialog_class.return_value = mock_dialog

            handler = ErrorHandler(self.parent_window, enable_logging=False)
            error = FileNotFoundError("File not found")
            handler.handle_error(error, level=logging.ERROR)

            mock_dialog_class.assert_called_once()
            mock_dialog.show.assert_called_once()
            call_args = mock_dialog_class.call_args
            self.assertEqual(call_args[0][0], self.parent_window)

    def test_handle_error_no_dialog_without_parent(self) -> None:
        """Test that handle_error does not show dialog without parent window."""
        with patch("video_comparator.errors.error_handler.ErrorDialog") as mock_dialog_class:
            handler = ErrorHandler(parent_window=None, enable_logging=False)
            error = FileNotFoundError("File not found")
            handler.handle_error(error, level=logging.ERROR)

            mock_dialog_class.assert_not_called()

    def test_handle_error_dialog_style_error_level(self) -> None:
        """Test that error level uses ERROR dialog style."""
        with patch("video_comparator.errors.error_handler.ErrorDialog") as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.show.return_value = wx.ID_OK
            mock_dialog_class.return_value = mock_dialog

            handler = ErrorHandler(self.parent_window, enable_logging=False)
            error = FileNotFoundError("File not found")
            handler.handle_error(error, level=logging.ERROR)

            mock_dialog.show.assert_called_once()
            call_args = mock_dialog.show.call_args
            self.assertEqual(call_args[1]["style"], wx.OK | wx.ICON_ERROR)

    def test_handle_error_dialog_style_warning_level(self) -> None:
        """Test that warning level uses WARNING dialog style."""
        with patch("video_comparator.errors.error_handler.ErrorDialog") as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.show.return_value = wx.ID_OK
            mock_dialog_class.return_value = mock_dialog

            handler = ErrorHandler(self.parent_window, enable_logging=False, gui_log_level=logging.WARNING)
            error = FileNotFoundError("File not found")
            handler.handle_error(error, level=logging.WARNING)

            mock_dialog.show.assert_called_once()
            call_args = mock_dialog.show.call_args
            self.assertEqual(call_args[1]["style"], wx.OK | wx.ICON_WARNING)

    def test_handle_error_dialog_style_info_level(self) -> None:
        """Test that info level uses INFORMATION dialog style."""
        with patch("video_comparator.errors.error_handler.ErrorDialog") as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.show.return_value = wx.ID_OK
            mock_dialog_class.return_value = mock_dialog

            handler = ErrorHandler(self.parent_window, enable_logging=False, gui_log_level=logging.INFO)
            error = FileNotFoundError("File not found")
            handler.handle_error(error, level=logging.INFO)

            mock_dialog.show.assert_called_once()
            call_args = mock_dialog.show.call_args
            self.assertEqual(call_args[1]["style"], wx.OK | wx.ICON_INFORMATION)

    def test_console_logging_info_level(self) -> None:
        """Test console logging at info level."""
        with patch("video_comparator.errors.error_handler.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            handler = ErrorHandler(parent_window=None, enable_logging=True, console_log_level=logging.INFO)
            error = FileNotFoundError("File not found")
            handler.handle_error(error, level=logging.INFO)

            mock_logger.info.assert_called_once()

    def test_console_logging_debug_level(self) -> None:
        """Test console logging at debug level."""
        with patch("video_comparator.errors.error_handler.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            handler = ErrorHandler(parent_window=None, enable_logging=True, console_log_level=logging.DEBUG)
            error = FileNotFoundError("File not found")
            handler.handle_error(error, level=logging.DEBUG)

            mock_logger.debug.assert_called_once()

    def test_console_logging_below_threshold(self) -> None:
        """Test that console logging respects log level threshold."""
        with patch("video_comparator.errors.error_handler.logging.getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            handler = ErrorHandler(parent_window=None, enable_logging=True, console_log_level=logging.WARNING)
            error = FileNotFoundError("File not found")
            handler.handle_error(error, level=logging.INFO)

            mock_logger.info.assert_not_called()

    def test_gui_log_viewer_warning_level(self) -> None:
        """Test GUI log viewer at warning level."""
        handler = ErrorHandler(parent_window=None, enable_logging=False, gui_log_level=logging.WARNING)
        error = FileNotFoundError("File not found")
        handler.handle_error(error, level=logging.WARNING)

        entries = handler.get_log_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].level, logging.WARNING)
        self.assertIsInstance(entries[0], LogEntry)

    def test_gui_log_viewer_info_level(self) -> None:
        """Test GUI log viewer at info level."""
        handler = ErrorHandler(parent_window=None, enable_logging=False, gui_log_level=logging.INFO)
        error = FileNotFoundError("File not found")
        handler.handle_error(error, level=logging.INFO)

        entries = handler.get_log_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].level, logging.INFO)

    def test_gui_log_viewer_below_threshold(self) -> None:
        """Test that GUI log viewer respects log level threshold."""
        handler = ErrorHandler(parent_window=None, enable_logging=False, gui_log_level=logging.WARNING)
        error = FileNotFoundError("File not found")
        handler.handle_error(error, level=logging.INFO)

        entries = handler.get_log_entries()
        self.assertEqual(len(entries), 0)

    def test_gui_log_viewer_multiple_entries(self) -> None:
        """Test GUI log viewer stores multiple entries."""
        handler = ErrorHandler(parent_window=None, enable_logging=False)
        handler.handle_error(FileNotFoundError("Error 1"), level=logging.ERROR)
        handler.handle_error(ValueError("Error 2"), level=logging.WARNING)

        entries = handler.get_log_entries()
        self.assertEqual(len(entries), 2)
        self.assertIn("Error 1", entries[0].message)
        self.assertIn("Error 2", entries[1].message)

    def test_get_log_entries_with_min_level_filter(self) -> None:
        """Test get_log_entries with minimum level filter."""
        handler = ErrorHandler(parent_window=None, enable_logging=False)
        handler.handle_error(FileNotFoundError("Error 1"), level=logging.ERROR)
        handler.handle_error(ValueError("Error 2"), level=logging.WARNING)
        handler.handle_error(RuntimeError("Error 3"), level=logging.INFO)

        entries = handler.get_log_entries(min_level=logging.WARNING)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].level, logging.ERROR)
        self.assertEqual(entries[1].level, logging.WARNING)

    def test_clear_log_entries(self) -> None:
        """Test clearing log entries."""
        handler = ErrorHandler(parent_window=None, enable_logging=False)
        handler.handle_error(FileNotFoundError("Error 1"), level=logging.ERROR)
        handler.handle_error(ValueError("Error 2"), level=logging.WARNING)

        self.assertEqual(len(handler.get_log_entries()), 2)

        handler.clear_log_entries()
        self.assertEqual(len(handler.get_log_entries()), 0)

    def test_log_entry_has_timestamp(self) -> None:
        """Test that log entries have timestamps."""
        handler = ErrorHandler(parent_window=None, enable_logging=False)
        handler.handle_error(FileNotFoundError("Error"), level=logging.ERROR)

        entries = handler.get_log_entries()
        self.assertEqual(len(entries), 1)
        self.assertIsNotNone(entries[0].timestamp)

    def test_handle_error_with_logging_disabled(self) -> None:
        """Test that handle_error does not log when logging is disabled."""
        handler = ErrorHandler(parent_window=None, enable_logging=False)
        error = FileNotFoundError("File not found")
        handler.handle_error(error, level=logging.ERROR)

        self.assertIsNone(handler.logger)
