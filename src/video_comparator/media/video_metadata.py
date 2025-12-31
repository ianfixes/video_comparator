"""Video metadata extraction and management.

Responsibilities:
- Probing via PyAV (duration, fps, dimensions, pixel format)
- Metadata caching and access
- Format detection
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import av


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

    def __post_init__(self) -> None:
        """Validate metadata values."""
        if self.duration <= 0:
            raise ValueError(f"duration must be > 0, got {self.duration}")
        if self.fps <= 0:
            raise ValueError(f"fps must be > 0, got {self.fps}")
        if self.width <= 0:
            raise ValueError(f"width must be > 0, got {self.width}")
        if self.height <= 0:
            raise ValueError(f"height must be > 0, got {self.height}")
        if not self.pixel_format:
            raise ValueError("pixel_format cannot be empty")
        if self.total_frames <= 0:
            raise ValueError(f"total_frames must be > 0, got {self.total_frames}")
        if self.time_base <= 0:
            raise ValueError(f"time_base must be > 0, got {self.time_base}")

    @property
    def dimensions(self) -> Tuple[int, int]:
        """Return video dimensions as (width, height) tuple."""
        return (self.width, self.height)

    @classmethod
    def from_path(cls, file_path: Path) -> "VideoMetadata":
        """Extract metadata from a video file.

        Args:
            file_path: Path to the video file

        Returns:
            VideoMetadata object with extracted metadata

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the file has no video stream or cannot be opened
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")

        try:
            container = av.open(str(file_path.absolute()))
        except av.AVError as e:
            raise ValueError(f"Failed to open video file: {file_path}") from e

        try:
            video_stream = None
            for stream in container.streams.video:
                video_stream = stream
                break

            if video_stream is None:
                raise ValueError(f"No video stream found in file: {file_path}")

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
            )
        finally:
            container.close()
