"""Media file loader and validator.

Responsibilities:
- File selection via dialogs
- File validation (existence, accessibility)
- User-facing errors for unsupported formats
"""

from video_comparator.errors.error_handler import ErrorHandler


class MediaLoader:
    """Handles loading and validation of media files."""

    def __init__(
        self,
        error_handler: ErrorHandler,
    ) -> None:
        """Initialize media loader with error handler and metadata extractor."""
        self.error_handler: ErrorHandler = error_handler
