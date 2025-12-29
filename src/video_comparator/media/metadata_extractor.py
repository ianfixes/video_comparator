"""Video metadata extraction and management.

Responsibilities:
- Probing via PyAV (duration, fps, dimensions, pixel format)
- Metadata caching and access
- Format detection
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class VideoMetadata:
    """Stores and provides access to video metadata."""

    file_path: str
    duration: float
    fps: float
    width: int
    height: int
    pixel_format: str
    total_frames: int
    time_base: float

    @property
    def dimensions(self) -> Tuple[int, int]:
        """Return video dimensions as (width, height) tuple."""
        return (self.width, self.height)


class MetadataExtractor:
    """Extracts metadata from video files using PyAV."""

    def __init__(self) -> None:
        """Initialize metadata extractor."""
        pass
