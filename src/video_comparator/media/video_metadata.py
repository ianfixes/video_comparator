"""Video metadata extraction and management.

Responsibilities:
- Probing via PyAV (duration, fps, dimensions, pixel format)
- Metadata caching and access
- Format detection
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Tuple

import av


class MetadataExtractionError(Exception):
    """Base exception for metadata extraction errors."""


class UnsupportedFormatError(MetadataExtractionError):
    """Raised when a video file format is not supported or cannot be opened."""


class NoVideoStreamError(MetadataExtractionError):
    """Raised when a file has no video stream."""


@dataclass
class VideoMetadata:
    """Stores and provides access to video metadata."""

    file_path: Optional[Path]
    duration: float
    fps: float
    width: int
    height: int
    pixel_format: str
    total_frames: int
    time_base: float
    sample_aspect_ratio_num: int = 1
    sample_aspect_ratio_den: int = 1

    def __post_init__(self) -> None:
        """Validate metadata values.

        When file_path is None (placeholder for no video loaded), duration and
        total_frames may be 0; otherwise they must be positive.
        """
        if self.file_path is not None:
            if self.duration <= 0:
                raise ValueError(f"duration must be > 0, got {self.duration}")
            if self.total_frames <= 0:
                raise ValueError(f"total_frames must be > 0, got {self.total_frames}")
        if self.fps <= 0:
            raise ValueError(f"fps must be > 0, got {self.fps}")
        if self.width <= 0:
            raise ValueError(f"width must be > 0, got {self.width}")
        if self.height <= 0:
            raise ValueError(f"height must be > 0, got {self.height}")
        if not self.pixel_format:
            raise ValueError("pixel_format cannot be empty")
        if self.time_base <= 0:
            raise ValueError(f"time_base must be > 0, got {self.time_base}")
        if self.sample_aspect_ratio_num <= 0:
            raise ValueError(f"sample_aspect_ratio_num must be > 0, got {self.sample_aspect_ratio_num}")
        if self.sample_aspect_ratio_den <= 0:
            raise ValueError(f"sample_aspect_ratio_den must be > 0, got {self.sample_aspect_ratio_den}")

    @property
    def dimensions(self) -> Tuple[int, int]:
        """Return coded raster dimensions as (width, height)."""
        return (self.width, self.height)

    @property
    def display_dimensions(self) -> Tuple[int, int]:
        """Return display dimensions adjusted by sample aspect ratio."""
        display_width = int(round(self.width * self.sample_aspect_ratio_num / self.sample_aspect_ratio_den))
        return (max(1, display_width), self.height)

    @property
    def display_aspect_ratio(self) -> float:
        """Return effective display aspect ratio (DAR)."""
        display_width, display_height = self.display_dimensions
        return display_width / display_height

    @staticmethod
    def _parse_aspect_ratio(value: Any) -> Tuple[int, int]:
        """Parse FFmpeg/PyAV aspect ratio value into positive numerator/denominator."""
        if value is None:
            return (1, 1)
        num = getattr(value, "numerator", None)
        den = getattr(value, "denominator", None)
        if num is None or den is None:
            return (1, 1)
        num_i = int(num)
        den_i = int(den)
        if num_i <= 0 or den_i <= 0:
            return (1, 1)
        return (num_i, den_i)

    @classmethod
    def from_path(cls, file_path: Path) -> "VideoMetadata":
        """Extract metadata from a video file.

        Args:
            file_path: Path to the video file

        Returns:
            VideoMetadata object with extracted metadata

        Raises:
            FileNotFoundError: If the file does not exist
            UnsupportedFormatError: If the file format is not supported or cannot be opened
            NoVideoStreamError: If the file has no video stream
            MetadataExtractionError: For other metadata extraction errors
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")

        try:
            container = av.open(str(file_path.absolute()))
        except av.AVError as e:
            raise UnsupportedFormatError(f"Failed to open video file: {file_path}") from e

        try:
            video_stream = None
            for stream in container.streams.video:
                video_stream = stream
                break

            if video_stream is None:
                raise NoVideoStreamError(f"No video stream found in file: {file_path}")

            duration_seconds = float(container.duration) / av.time_base if container.duration else 0.0
            if duration_seconds <= 0 and video_stream.duration is not None and video_stream.time_base is not None:
                duration_seconds = float(video_stream.duration * video_stream.time_base)

            fps = float(video_stream.average_rate) if video_stream.average_rate else 0.0
            if fps <= 0 and video_stream.frames > 0 and duration_seconds > 0:
                fps = float(video_stream.frames) / duration_seconds

            if video_stream.time_base is None:
                raise ValueError(f"Video stream has no time_base in file: {file_path}")
            time_base = float(video_stream.time_base)

            total_frames = video_stream.frames
            if total_frames <= 0 and duration_seconds > 0 and fps > 0:
                total_frames = int(duration_seconds * fps)

            pixel_format = video_stream.codec_context.pix_fmt or "unknown"
            width = video_stream.codec_context.width
            height = video_stream.codec_context.height
            sample_aspect_ratio_num, sample_aspect_ratio_den = cls._parse_aspect_ratio(
                getattr(video_stream, "sample_aspect_ratio", None)
            )
            if sample_aspect_ratio_num == 1 and sample_aspect_ratio_den == 1:
                sample_aspect_ratio_num, sample_aspect_ratio_den = cls._parse_aspect_ratio(
                    getattr(video_stream.codec_context, "sample_aspect_ratio", None)
                )

            if width is None or width <= 0:
                raise ValueError(f"Invalid video width: {width}")
            if height is None or height <= 0:
                raise ValueError(f"Invalid video height: {height}")

            return cls(
                file_path=file_path,
                duration=duration_seconds,
                fps=fps,
                width=width,
                height=height,
                pixel_format=pixel_format,
                total_frames=total_frames,
                time_base=time_base,
                sample_aspect_ratio_num=sample_aspect_ratio_num,
                sample_aspect_ratio_den=sample_aspect_ratio_den,
            )
        finally:
            container.close()
