"""Video decoder engine.

Responsibilities:
- Open video containers via PyAV
- Frame-accurate seek (time- or frame-based)
- Decode frames to NumPy arrays
- Handle differing fps/timebases
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional, Type, cast

import av
import numpy as np

from video_comparator.media.video_metadata import VideoMetadata

if TYPE_CHECKING:
    from video_comparator.cache.frame_cache import FrameCache


class DecodeError(Exception):
    """Base exception for video decoding errors."""


class SeekError(DecodeError):
    """Raised when a seek operation fails."""


class UnsupportedFormatError(DecodeError):
    """Raised when a video format is not supported for decoding."""


@dataclass(frozen=True)
class DecodeOperationResult:
    """Represents a decode operation output for a single target request."""

    requested_frame: np.ndarray
    decoded_frames: list[tuple[int, np.ndarray]]


class VideoDecoder:
    """Decodes video frames from a video file."""

    def __init__(
        self,
        metadata: VideoMetadata,
        frame_cache: Optional["FrameCache"] = None,
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
        self.frame_cache: Optional["FrameCache"] = frame_cache
        self._container: Optional[Any] = None
        self._video_stream: Optional[Any] = None
        self._first_frame_pts: Optional[int] = None
        self._decode_cursor_frame_index: Optional[int] = None
        self._decode_forward_window_frames = 24

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
            self._first_frame_pts = None
            self._decode_cursor_frame_index = None

    def _stream_pts_for_frame_index(self, frame_index: int) -> int:
        """Return PTS in stream time_base units for the given 0-based frame index."""
        if self._video_stream is None or self._video_stream.time_base is None:
            time_base = self.metadata.time_base
            start_time = 0
        else:
            time_base = float(self._video_stream.time_base)
            start_time = int(self._video_stream.start_time) if self._video_stream.start_time is not None else 0
        time_seconds = frame_index / self.metadata.fps
        return start_time + int(time_seconds / time_base)

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

        timestamp_pts = self._stream_pts_for_frame_index(frame_index)

        try:
            if self._container is not None:
                self._container.seek(timestamp_pts, stream=self._video_stream)
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

        if self._video_stream is not None and self._video_stream.time_base is not None:
            time_base = float(self._video_stream.time_base)
            start_time = int(self._video_stream.start_time) if self._video_stream.start_time is not None else 0
            timestamp_pts = start_time + int(timestamp_seconds / time_base)
        else:
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

        return self.decode_frame_operation(frame_index).requested_frame

    def decode_frame_operation(self, frame_index: int) -> DecodeOperationResult:
        """Decode a target frame and expose all decoded frames up to that target."""
        if frame_index < 0 or frame_index >= self.metadata.total_frames:
            raise ValueError(f"Frame index {frame_index} out of range [0, {self.metadata.total_frames - 1}]")

        self._ensure_open()

        should_seek = (
            self._decode_cursor_frame_index is None
            or frame_index <= self._decode_cursor_frame_index
            or frame_index - self._decode_cursor_frame_index > self._decode_forward_window_frames
        )
        if should_seek:
            self.seek_to_frame(frame_index)

        try:
            if self._container is not None and self._video_stream is not None:
                decode_index: Optional[int] = self._decode_cursor_frame_index if not should_seek else None
                last_decodable_frame: Any = None
                decoded_frames: list[tuple[int, np.ndarray]] = []
                for frame in self._container.decode(self._video_stream):  # type: ignore
                    if not hasattr(frame, "to_ndarray"):
                        continue
                    last_decodable_frame = frame
                    if decode_index is None:
                        if self._first_frame_pts is None and frame.pts is not None:
                            self._first_frame_pts = int(frame.pts)
                        pts_index = self._frame_index_from_pts(frame)
                        decode_index = pts_index if pts_index >= 0 else 0
                        if decode_index > frame_index and frame_index > 0:
                            decode_index = frame_index - 1
                    else:
                        decode_index += 1
                    if decode_index > frame_index:
                        break
                    frame_array = cast(np.ndarray, frame.to_ndarray(format="rgb24"))
                    decoded_frames.append((decode_index, frame_array))
                    if decode_index == frame_index:
                        self._decode_cursor_frame_index = frame_index
                        return DecodeOperationResult(requested_frame=frame_array, decoded_frames=decoded_frames)
                if frame_index == self.metadata.total_frames - 1 and last_decodable_frame is not None:
                    frame_array = cast(np.ndarray, last_decodable_frame.to_ndarray(format="rgb24"))
                    decoded_frames.append((frame_index, frame_array))
                    self._decode_cursor_frame_index = frame_index
                    return DecodeOperationResult(requested_frame=frame_array, decoded_frames=decoded_frames)
        except av.AVError as e:
            raise DecodeError(f"Failed to decode frame {frame_index}") from e
        except AssertionError as e:
            if "not open" in str(e).lower():
                raise DecodeError(f"Failed to decode frame {frame_index}") from e
            raise
        except Exception as e:
            raise DecodeError(f"Failed to decode frame {frame_index}") from e

        raise DecodeError(f"No frame found at index {frame_index}")

    def _frame_index_from_pts(self, frame: Any) -> int:
        """Compute 0-based frame index from a decoded frame's presentation time."""
        if frame.pts is not None and self._video_stream is not None and self._video_stream.time_base is not None:
            time_base = float(self._video_stream.time_base)
            base = self._first_frame_pts
            if base is None:
                base = int(self._video_stream.start_time) if self._video_stream.start_time is not None else 0
            time_seconds = (int(frame.pts) - base) * time_base
        elif getattr(frame, "time", None) is not None:
            time_seconds = float(frame.time)
        else:
            return -1
        return int(round(time_seconds * self.metadata.fps))

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
