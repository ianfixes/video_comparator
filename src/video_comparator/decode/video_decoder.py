"""Video decoder engine.

Responsibilities:
- Open video containers via PyAV
- Frame-accurate seek (time- or frame-based)
- Decode frames to NumPy arrays
- Handle differing fps/timebases
"""

from typing import Any, Optional, Type

import av
import numpy as np

from video_comparator.cache.frame_cache import FrameCache
from video_comparator.media.video_metadata import VideoMetadata


class DecodeError(Exception):
    """Base exception for video decoding errors."""


class SeekError(DecodeError):
    """Raised when a seek operation fails."""


class UnsupportedFormatError(DecodeError):
    """Raised when a video format is not supported for decoding."""


class VideoDecoder:
    """Decodes video frames from a video file."""

    def __init__(
        self,
        metadata: VideoMetadata,
        frame_cache: Optional[FrameCache] = None,
    ) -> None:
        """Initialize video decoder with metadata and optional cache.

        Args:
            metadata: VideoMetadata containing file path and video properties
            frame_cache: Optional FrameCache for caching decoded frames
        """
        if metadata.file_path is None:
            raise ValueError("VideoMetadata must have a file_path")
        if not metadata.file_path.exists():
            raise FileNotFoundError(f"Video file not found: {metadata.file_path}")

        self.metadata: VideoMetadata = metadata
        self.frame_cache: Optional[FrameCache] = frame_cache
        self._container: Optional[Any] = None
        self._video_stream: Optional[Any] = None

    def _ensure_open(self) -> None:
        """Open container and select video stream if not already open."""
        if self._container is not None:
            return

        try:
            if self.metadata.file_path is not None:
                self._container = av.open(str(self.metadata.file_path.absolute()))
        except av.AVError as e:
            raise UnsupportedFormatError(f"Failed to open video file: {self.metadata.file_path}") from e

        self._video_stream = None
        if self._container is not None:
            for stream in self._container.streams.video:
                self._video_stream = stream
                break

        if self._video_stream is None:
            self.close()
            raise UnsupportedFormatError(f"No video stream found in file: {self.metadata.file_path}")

    def close(self) -> None:
        """Close the video container and release resources."""
        if self._container is not None:
            self._container.close()
            self._container = None
            self._video_stream = None

    def seek_to_frame(self, frame_index: int) -> None:
        """Seek to a specific frame index.

        Args:
            frame_index: Frame index to seek to (0-based)

        Raises:
            ValueError: If frame_index is out of range
            SeekError: If seek fails
        """
        if frame_index < 0 or frame_index >= self.metadata.total_frames:
            raise ValueError(f"Frame index {frame_index} out of range [0, {self.metadata.total_frames - 1}]")

        self._ensure_open()

        timestamp_seconds = frame_index / self.metadata.fps
        timestamp_pts = int(timestamp_seconds / self.metadata.time_base)

        try:
            if self._container is not None:
                self._container.seek(timestamp_pts, stream=self._video_stream)  # type: ignore
        except av.AVError as e:
            raise SeekError(f"Failed to seek to frame {frame_index}") from e

    def seek_to_timestamp(self, timestamp_seconds: float) -> None:
        """Seek to a specific timestamp.

        Args:
            timestamp_seconds: Timestamp in seconds

        Raises:
            ValueError: If timestamp is out of range
            SeekError: If seek fails
        """
        if timestamp_seconds < 0.0 or timestamp_seconds > self.metadata.duration:
            raise ValueError(f"Timestamp {timestamp_seconds} out of range [0.0, {self.metadata.duration}]")

        self._ensure_open()

        timestamp_pts = int(timestamp_seconds / self.metadata.time_base)

        try:
            if self._container is not None:
                self._container.seek(timestamp_pts, stream=self._video_stream)  # type: ignore
        except av.AVError as e:
            raise SeekError(f"Failed to seek to timestamp {timestamp_seconds}") from e

    def decode_frame(self, frame_index: int) -> np.ndarray:
        """Decode a specific frame by index.

        Args:
            frame_index: Frame index to decode (0-based)

        Returns:
            NumPy array of shape (height, width, 3) in RGB format

        Raises:
            ValueError: If frame_index is out of range
            DecodeError: If decode fails
        """
        if frame_index < 0 or frame_index >= self.metadata.total_frames:
            raise ValueError(f"Frame index {frame_index} out of range [0, {self.metadata.total_frames - 1}]")

        if self.frame_cache is not None:
            cached_frame = self.frame_cache.get(frame_index)
            if cached_frame is not None:
                return cached_frame

        self._ensure_open()

        self.seek_to_frame(frame_index)

        try:
            if self._container is not None:
                for frame in self._container.decode(self._video_stream):  # type: ignore
                    if hasattr(frame, "to_ndarray"):
                        frame_array: np.ndarray = frame.to_ndarray(format="rgb24")  # type: ignore
                        if self.frame_cache is not None:
                            self.frame_cache.put(frame_index, frame_array)
                        return frame_array
        except (av.AVError, Exception) as e:
            raise DecodeError(f"Failed to decode frame {frame_index}") from e

        raise DecodeError(f"No frame found at index {frame_index}")

    def decode_frame_at_timestamp(self, timestamp_seconds: float) -> np.ndarray:
        """Decode a frame at a specific timestamp.

        Args:
            timestamp_seconds: Timestamp in seconds

        Returns:
            NumPy array of shape (height, width, 3) in RGB format

        Raises:
            ValueError: If timestamp is out of range
            ValueError: If decode fails
        """
        if timestamp_seconds < 0.0 or timestamp_seconds > self.metadata.duration:
            raise ValueError(f"Timestamp {timestamp_seconds} out of range [0.0, {self.metadata.duration}]")

        frame_index = int(timestamp_seconds * self.metadata.fps)
        frame_index = min(frame_index, self.metadata.total_frames - 1)

        return self.decode_frame(frame_index)

    def __enter__(self) -> "VideoDecoder":
        """Context manager entry."""
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[Any]
    ) -> None:
        """Context manager exit."""
        self.close()
