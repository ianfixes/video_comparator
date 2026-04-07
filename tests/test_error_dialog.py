"""Unit tests for ErrorDialog class."""

import unittest
from unittest.mock import MagicMock, patch

import wx

from video_comparator.errors.error_dialog import ErrorDialog


class TestErrorDialog(unittest.TestCase):
    """Test cases for ErrorDialog class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.parent = MagicMock(spec=wx.Window)
        self.title = "Test Error"
        self.message = "This is a test error message"

    def test_show_creates_message_dialog(self) -> None:
        """Test that show() creates a wx.MessageDialog with correct parameters."""
        with patch("video_comparator.errors.error_dialog.wx.MessageDialog") as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.ShowModal.return_value = wx.ID_OK
            mock_dialog_class.return_value = mock_dialog

            dialog = ErrorDialog(self.parent, self.title, self.message)
            result = dialog.show()

            mock_dialog_class.assert_called_once_with(self.parent, self.message, self.title, wx.OK | wx.ICON_ERROR)
            mock_dialog.ShowModal.assert_called_once()
            mock_dialog.Destroy.assert_called_once()
            self.assertEqual(result, wx.ID_OK)

    def test_show_returns_dialog_result(self) -> None:
        """Test that show() returns the dialog result code."""
        with patch("video_comparator.errors.error_dialog.wx.MessageDialog") as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.ShowModal.return_value = wx.ID_CANCEL
            mock_dialog_class.return_value = mock_dialog

            dialog = ErrorDialog(self.parent, self.title, self.message)
            result = dialog.show()

            self.assertEqual(result, wx.ID_CANCEL)

    def test_show_with_custom_style(self) -> None:
        """Test that show() accepts custom style flags."""
        with patch("video_comparator.errors.error_dialog.wx.MessageDialog") as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.ShowModal.return_value = wx.ID_YES
            mock_dialog_class.return_value = mock_dialog

            dialog = ErrorDialog(self.parent, self.title, self.message)
            custom_style = wx.YES_NO | wx.ICON_WARNING
            result = dialog.show(style=custom_style)

            mock_dialog_class.assert_called_once_with(self.parent, self.message, self.title, custom_style)
            self.assertEqual(result, wx.ID_YES)

    def test_show_destroys_dialog_after_modal(self) -> None:
        """Test that dialog is destroyed after ShowModal returns."""
        with patch("video_comparator.errors.error_dialog.wx.MessageDialog") as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.ShowModal.return_value = wx.ID_OK
            mock_dialog_class.return_value = mock_dialog

            dialog = ErrorDialog(self.parent, self.title, self.message)
            dialog.show()

            mock_dialog.ShowModal.assert_called_once()
            mock_dialog.Destroy.assert_called_once()

    def test_show_destroys_dialog_even_on_exception(self) -> None:
        """Test that dialog is destroyed even if ShowModal raises an exception."""
        with patch("video_comparator.errors.error_dialog.wx.MessageDialog") as mock_dialog_class:
            mock_dialog = MagicMock()
            mock_dialog.ShowModal.side_effect = RuntimeError("Test exception")
            mock_dialog_class.return_value = mock_dialog

            dialog = ErrorDialog(self.parent, self.title, self.message)

            with self.assertRaises(RuntimeError):
                dialog.show()

            mock_dialog.Destroy.assert_called_once()

    def test_show_with_different_result_codes(self) -> None:
        """Test show() with various dialog result codes."""
        result_codes = [wx.ID_OK, wx.ID_CANCEL, wx.ID_YES, wx.ID_NO]
        for result_code in result_codes:
            with patch("video_comparator.errors.error_dialog.wx.MessageDialog") as mock_dialog_class:
                mock_dialog = MagicMock()
                mock_dialog.ShowModal.return_value = result_code
                mock_dialog_class.return_value = mock_dialog

                dialog = ErrorDialog(self.parent, self.title, self.message)
                result = dialog.show()

                self.assertEqual(result, result_code)
