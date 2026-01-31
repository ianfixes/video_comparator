"""Media file loader and validator.

Responsibilities:
- File selection via dialogs
- File validation (existence, accessibility)
- User-facing errors for unsupported formats
"""

from pathlib import Path
from typing import Optional

import wx

from video_comparator.errors.error_handler import ErrorHandler
from video_comparator.media.video_metadata import (
    MetadataExtractionError,
    NoVideoStreamError,
    UnsupportedFormatError,
    VideoMetadata,
)


class MediaLoader:
    """Handles loading and validation of media files."""

    SUPPORTED_EXTENSIONS = [
        "*.avi",
        "*.mp4",
        "*.mkv",
        "*.mov",
        "*.m4v",
        "*.webm",
        "*.flv",
        "*.wmv",
        "*.mpeg",
        "*.mpg",
        "*.3gp",
    ]

    def __init__(
        self,
        error_handler: ErrorHandler,
    ) -> None:
        """Initialize media loader with error handler.

        Args:
            error_handler: Error handler for displaying user-facing errors
        """
        self.error_handler: ErrorHandler = error_handler

    def load_video_file(self, parent: Optional[wx.Window] = None) -> Optional[VideoMetadata]:
        """Load a video file via file selection dialog.

        This method:
        1. Shows a file selection dialog
        2. Validates the selected file (existence, accessibility, format)
        3. Extracts metadata using VideoMetadata.from_path
        4. Handles errors via ErrorHandler

        Args:
            parent: Optional wx.Window parent for the file dialog

        Returns:
            VideoMetadata if file was successfully loaded, None if user cancelled or error occurred
        """
        file_path = self._show_file_dialog(parent)
        if file_path is None:
            return None

        return self._validate_and_load_video_file(file_path)

    def load_video_file_from_path(self, file_path: Path) -> Optional[VideoMetadata]:
        """Load a video file from a given path.

        This method validates and loads a video file without showing a dialog.
        Useful for programmatic loading or testing.

        Args:
            file_path: Path to the video file

        Returns:
            VideoMetadata if file was successfully loaded, None if error occurred
        """
        return self._validate_and_load_video_file(file_path)

    def _validate_and_load_video_file(self, file_path: Path) -> Optional[VideoMetadata]:
        """
        Validate the video file (existence, readability, format), extract metadata, and handle errors.

        Args:
            file_path: Path to the video file

        Returns:
            VideoMetadata if file was successfully loaded, None if error occurred
        """
        if not self._validate_file_exists(file_path):
            return None

        if not self._validate_file_readable(file_path):
            return None

        try:
            metadata = VideoMetadata.from_path(file_path)
            return metadata
        except FileNotFoundError as e:
            self.error_handler.handle_error(e)
            return None
        except UnsupportedFormatError as e:
            self.error_handler.handle_error(e)
            return None
        except NoVideoStreamError as e:
            self.error_handler.handle_error(e)
            return None
        except MetadataExtractionError as e:
            self.error_handler.handle_error(e)
            return None

    def _show_file_dialog(self, parent: Optional[wx.Window] = None) -> Optional[Path]:
        """Show file selection dialog and return selected file path.

        Args:
            parent: Optional wx.Window parent for the dialog

        Returns:
            Path to selected file, or None if user cancelled
        """
        # list the supported extensions both individually and as a single string
        wildcard = (
            "Video files ("
            + "|".join(self.SUPPORTED_EXTENSIONS)
            + ")|"
            + "|".join(self.SUPPORTED_EXTENSIONS)
            + "|All files (*.*)|*.*"
        )

        dialog = wx.FileDialog(
            parent,
            message="Select a video file",
            defaultDir="",
            defaultFile="",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if dialog.ShowModal() == wx.ID_OK:
                return Path(dialog.GetPath())
        finally:
            dialog.Destroy()
        return None

    def _validate_file_exists(self, file_path: Path) -> bool:
        """Validate that the file exists.

        Args:
            file_path: Path to validate

        Returns:
            True if file exists, False otherwise (error handled via ErrorHandler)
        """
        if not file_path.exists():
            error = FileNotFoundError(f"Video file not found: {file_path}")
            self.error_handler.handle_error(error)
            return False
        return True

    def _validate_file_readable(self, file_path: Path) -> bool:
        """Validate that the file is readable.

        Args:
            file_path: Path to validate

        Returns:
            True if file is readable, False otherwise (error handled via ErrorHandler)
        """
        if not file_path.is_file():
            error: Exception = ValueError(f"Path is not a file: {file_path}")
            self.error_handler.handle_error(error)
            return False

        try:
            if not file_path.stat().st_mode & 0o444:
                error = PermissionError(f"File is not readable: {file_path}")
                self.error_handler.handle_error(error)
                return False
        except OSError as e:
            error = PermissionError(f"Cannot access file: {file_path}")
            error.__cause__ = e
            self.error_handler.handle_error(error)
            return False

        return True
