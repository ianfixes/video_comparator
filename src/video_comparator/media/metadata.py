"""Video metadata extraction and management.

Responsibilities:
- Probing via PyAV (duration, fps, dimensions, pixel format)
- Metadata caching and access
- Format detection
"""

from typing import Optional, Tuple


class VideoMetadata:
    """Stores and provides access to video metadata."""

    def __init__(
        self,
        file_path: str,
        duration: float,
        fps: float,
        width: int,
        height: int,
        pixel_format: str,
        total_frames: int,
        time_base: float,
    ) -> None:
        """Initialize video metadata with extracted information."""
        self.file_path: str = file_path
        self.duration: float = duration
        self.fps: float = fps
        self.width: int = width
        self.height: int = height
        self.pixel_format: str = pixel_format
        self.total_frames: int = total_frames
        self.time_base: float = time_base

    @property
    def dimensions(self) -> Tuple[int, int]:
        """Return video dimensions as (width, height) tuple."""
        return (self.width, self.height)


class MetadataExtractor:
    """Extracts metadata from video files using PyAV."""

    def __init__(self) -> None:
        """Initialize metadata extractor."""
        pass
