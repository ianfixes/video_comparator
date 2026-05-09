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
        self._presentation_floor_seconds: Optional[float] = None
        self._reorder_guard_frames = 8
        #: Last presentation frame index returned by ``decode_frame_operation`` (``None`` if none yet).
        self._decode_cursor_frame_index: Optional[int] = None

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

        self._presentation_floor_seconds = self._probe_presentation_floor_seconds()

    def close(self) -> None:
        """Close the video container and release resources."""
        if self._container is not None:
            self._container.close()
            self._container = None
            self._video_stream = None
            self._presentation_floor_seconds = None
            self._decode_cursor_frame_index = None

    def _probe_presentation_floor_seconds(self) -> float:
        """Minimum presentation timestamp (seconds) on the video stream from packet PTS.

        Many containers shift the first picture away from t=0 while metadata still uses
        0-based UI frame indices; subtracting this floor maps absolute timestamps to those
        indices. Uses demux-only traversal (no full decode).
        """
        assert self._container is not None and self._video_stream is not None
        vs = self._video_stream
        mn: Optional[float] = None
        for pkt in self._container.demux(vs):  # type: ignore[arg-type]
            if pkt.pts is None:
                continue
            tb = float(vs.time_base)
            st = int(vs.start_time) if vs.start_time is not None else 0
            sec = (int(pkt.pts) - st) * tb
            mn = sec if mn is None else min(mn, sec)
        start_pts = int(vs.start_time) if vs.start_time is not None else 0
        try:
            self._container.seek(start_pts, stream=vs)
        except av.AVError:
            try:
                self._container.seek(0)
            except av.AVError:
                pass
        return mn if mn is not None else 0.0

    def _stream_pts_for_frame_index(self, frame_index: int) -> int:
        """Return PTS in stream time_base units for the given 0-based frame index.

        Uses the same presentation timeline as ``_index_from_seconds`` (metadata fps grid
        anchored at ``_presentation_floor_seconds``) so seek targets match frames labeled
        during forward decode.
        """
        if self._video_stream is None or self._video_stream.time_base is None:
            time_base = self.metadata.time_base
            start_time = 0
        else:
            time_base = float(self._video_stream.time_base)
            start_time = int(self._video_stream.start_time) if self._video_stream.start_time is not None else 0
        floor = self._presentation_floor_seconds if self._presentation_floor_seconds is not None else 0.0
        presentation_seconds = floor + frame_index / self.metadata.fps
        return start_time + int(presentation_seconds / time_base)

    def _seek_to_frame_internal(self, frame_index: int) -> None:
        """Seek container to ``frame_index`` without touching the sequential decode cursor."""
        if frame_index < 0 or frame_index >= self.metadata.total_frames:
            raise ValueError(f"Frame index {frame_index} out of range [0, {self.metadata.total_frames - 1}]")

        self._ensure_open()

        timestamp_pts = self._stream_pts_for_frame_index(frame_index)

        try:
            if self._container is not None:
                self._container.seek(timestamp_pts, stream=self._video_stream)
        except av.AVError as e:
            if frame_index == 0 and self._container is not None:
                try:
                    # Some containers reject stream-scoped seek for the first frame.
                    # Fall back to absolute container start for frame 0.
                    self._container.seek(0)
                    return
                except av.AVError:
                    pass
            raise SeekError(f"Failed to seek to frame {frame_index}") from e

    def seek_to_frame(self, frame_index: int) -> None:
        """Seek to a specific frame index.

        Clears the sequential decode cursor so the next ``decode_frame`` cannot assume
        the stream is positioned immediately after the last decoded frame.

        Args:
            frame_index: Frame index to seek to (0-based)

        Raises:
            ValueError: If frame_index is out of range
            SeekError: If seek fails
        """
        self._seek_to_frame_internal(frame_index)
        self._decode_cursor_frame_index = None

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
        """Decode a target frame and expose all decoded frames up to that target.

        Two positioning modes, both keyed by the same presentation index (``_index_from_seconds``):

        - **Random / gap / backward:** ``_seek_to_frame_internal`` then decode until the
          exact ``frame_index`` is present (no mis-labeled nearest-neighbour fallback).
        - **Strictly consecutive forward:** if the last returned index was ``frame_index-1``,
          continue decoding without a seek for performance; if the exact index does not
          appear (reorder / edge), fall back to seek + decode once.
        """
        if frame_index < 0 or frame_index >= self.metadata.total_frames:
            raise ValueError(f"Frame index {frame_index} out of range [0, {self.metadata.total_frames - 1}]")

        self._ensure_open()

        cursor = self._decode_cursor_frame_index
        forward_only = cursor is not None and frame_index == cursor + 1

        if not forward_only:
            self._seek_to_frame_internal(frame_index)

        try:
            result = self._gather_decode_for_frame_index(frame_index)
            if result is None and forward_only:
                self._seek_to_frame_internal(frame_index)
                result = self._gather_decode_for_frame_index(frame_index)
            if result is None:
                raise DecodeError(f"No frame found at index {frame_index}")
            self._decode_cursor_frame_index = frame_index
            return result
        except av.AVError as e:
            raise DecodeError(f"Failed to decode frame {frame_index}") from e
        except AssertionError as e:
            if "not open" in str(e).lower():
                raise DecodeError(f"Failed to decode frame {frame_index}") from e
            raise
        except DecodeError:
            raise
        except Exception as e:
            raise DecodeError(f"Failed to decode frame {frame_index}") from e

    def _gather_decode_for_frame_index(self, frame_index: int) -> Optional[DecodeOperationResult]:
        """Decode from current stream position until ``frame_index`` is resolved or give up."""
        if self._container is None or self._video_stream is None:
            return None

        last_decodable_frame: Any = None
        candidates: list[tuple[float, int, np.ndarray]] = []
        max_steps = max(self.metadata.total_frames, 1) + 256
        steps = 0
        target_found_at_step: Optional[int] = None
        for frame in self._container.decode(self._video_stream):  # type: ignore
            steps += 1
            if steps > max_steps:
                break
            if not hasattr(frame, "to_ndarray"):
                continue
            last_decodable_frame = frame
            seconds = self._presentation_seconds(frame)
            if seconds is None:
                continue
            pres_idx = self._index_from_seconds(seconds)
            if pres_idx < 0:
                continue
            frame_array = cast(np.ndarray, frame.to_ndarray(format="rgb24"))
            candidates.append((seconds, pres_idx, frame_array))
            if pres_idx == frame_index and target_found_at_step is None:
                target_found_at_step = steps
            if target_found_at_step is not None and steps - target_found_at_step >= self._reorder_guard_frames:
                break

        by_index: dict[int, tuple[float, np.ndarray]] = {}
        for seconds, pres_idx, frame_array in candidates:
            existing = by_index.get(pres_idx)
            if existing is None or seconds < existing[0]:
                by_index[pres_idx] = (seconds, frame_array)

        if frame_index in by_index:
            requested_frame = by_index[frame_index][1]
            decoded_frames = [(idx, by_index[idx][1]) for idx in sorted(by_index) if idx != frame_index]
            decoded_frames.append((frame_index, requested_frame))
            return DecodeOperationResult(requested_frame=requested_frame, decoded_frames=decoded_frames)

        if frame_index == self.metadata.total_frames - 1 and last_decodable_frame is not None:
            frame_array = cast(np.ndarray, last_decodable_frame.to_ndarray(format="rgb24"))
            tail_idx = self._presentation_frame_index(last_decodable_frame)
            if tail_idx < 0:
                tail_idx = frame_index
            tail_idx = max(0, min(tail_idx, self.metadata.total_frames - 1))
            decoded_frames = [(idx, by_index[idx][1]) for idx in sorted(by_index)]
            if not decoded_frames or decoded_frames[-1][0] != tail_idx:
                decoded_frames.append((tail_idx, frame_array))
            else:
                decoded_frames[-1] = (tail_idx, frame_array)
            return DecodeOperationResult(requested_frame=frame_array, decoded_frames=decoded_frames)

        return None

    def _presentation_frame_index(self, frame: Any) -> int:
        """Map a decoded video frame to a 0-based presentation frame index.

        Uses PTS/time_base relative to ``stream.start_time`` when available; falls back
        to ``frame.time`` only if PTS is missing. Truncation (not rounding) aligns CFR
        clips with metadata ``fps`` so the first tick maps to frame 0.

        This avoids counting packets in decode order (wrong under B-frame reordering).
        Returns -1 only when no usable timestamp exists.
        """
        seconds = self._presentation_seconds(frame)
        if seconds is None:
            return -1
        idx = self._index_from_seconds(seconds)
        if idx < 0:
            return 0
        if idx >= self.metadata.total_frames:
            return self.metadata.total_frames - 1
        return idx

    def _presentation_seconds(self, frame: Any) -> Optional[float]:
        """Return presentation seconds for a decoded frame, if available."""
        vs = self._video_stream
        if vs is None:
            return None

        if frame.pts is not None and vs.time_base is not None:
            tb = float(vs.time_base)
            start_pts = int(vs.start_time) if vs.start_time is not None else 0
            seconds = (int(frame.pts) - start_pts) * tb
            if seconds == seconds:
                return max(0.0, seconds)

        time_attr = getattr(frame, "time", None)
        if time_attr is not None and not isinstance(time_attr, bool):
            try:
                candidate = float(time_attr)
            except (TypeError, ValueError):
                return None
            if candidate == candidate:
                return max(0.0, candidate)
        return None

    def _index_from_seconds(self, seconds: float) -> int:
        """Convert presentation seconds to 0-based UI frame index."""
        floor = self._presentation_floor_seconds if self._presentation_floor_seconds is not None else 0.0
        adjusted = seconds - floor
        if adjusted < 0:
            adjusted = 0.0
        return int(adjusted * self.metadata.fps + 1e-9)

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
