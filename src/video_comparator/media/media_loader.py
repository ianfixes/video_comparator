"""Media file loader and validator.

Responsibilities:
- File selection via dialogs
- File validation (existence, accessibility)
- User-facing errors for unsupported formats
"""

from video_comparator.errors.error_handler import ErrorHandler
from video_comparator.media.metadata_extractor import MetadataExtractor


class MediaLoader:
    """Handles loading and validation of media files."""

    def __init__(
        self,
        error_handler: ErrorHandler,
        metadata_extractor: MetadataExtractor,
    ) -> None:
        """Initialize media loader with error handler and metadata extractor."""
        self.error_handler: ErrorHandler = error_handler
        self.metadata_extractor: MetadataExtractor = metadata_extractor
