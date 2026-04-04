"""Timeline and synchronization controller.

Responsibilities:
- Single source of truth for playback position and per-video sync offsets
- All seeks/steps go through this controller
- Converts between wall-clock, timestamps, and frame indices
- Provides resolved target frame/time to consumers
"""

from typing import Tuple

from video_comparator.media.video_metadata import VideoMetadata


class TimelineError(Exception):
    """Base exception for timeline controller errors."""


class InvalidPositionError(TimelineError):
    """Raised when a position is invalid or out of range."""


class OutOfRangeError(TimelineError):
    """Raised when a position or frame is out of the valid range."""


class TimelineController:
    """Manages timeline position and synchronization offsets."""

    def __init__(
        self,
        metadata_video1: VideoMetadata,
        metadata_video2: VideoMetadata,
    ) -> None:
        """Initialize timeline controller with metadata for both videos.

        Args:
            metadata_video1: Metadata for the first video
            metadata_video2: Metadata for the second video
        """
        self.metadata_video1: VideoMetadata = metadata_video1
        self.metadata_video2: VideoMetadata = metadata_video2
        self.current_position: float = 0.0  # Timeline position in seconds
        self.sync_offset_frames: int = 0  # Offset for video2 in frames (can be negative)

    def frame_to_time_video1(self, frame_index: int) -> float:
        """Convert frame index to timestamp for video 1.

        Args:
            frame_index: Frame index (0-based)

        Returns:
            Timestamp in seconds
        """
        return frame_index / self.metadata_video1.fps

    def frame_to_time_video2(self, frame_index: int) -> float:
        """Convert frame index to timestamp for video 2, accounting for sync offset.

        Args:
            frame_index: Frame index (0-based)

        Returns:
            Timestamp in seconds
        """
        adjusted_frame = frame_index - self.sync_offset_frames
        return adjusted_frame / self.metadata_video2.fps

    def time_to_frame_video1(self, timestamp: float) -> int:
        """Convert timestamp to frame index for video 1.

        Args:
            timestamp: Timestamp in seconds

        Returns:
            Frame index (0-based)
        """
        frame = int(timestamp * self.metadata_video1.fps)
        return max(0, min(frame, self.metadata_video1.total_frames - 1))

    def time_to_frame_video2(self, timestamp: float) -> int:
        """Convert timestamp to frame index for video 2, accounting for sync offset.

        Args:
            timestamp: Timestamp in seconds

        Returns:
            Frame index (0-based)
        """
        frame = int(timestamp * self.metadata_video2.fps) + self.sync_offset_frames
        return max(0, min(frame, self.metadata_video2.total_frames - 1))

    def get_effective_range(self) -> Tuple[float, float]:
        """Get the effective timeline range accounting for sync offsets.

        The range represents the maximum navigable timeline positions. When sync offsets
        are present, the range may extend beyond the shorter video's duration to cover
        the full overlap region. When only one video is loaded (other has duration 0),
        the range is that video's duration.

        Returns:
            Tuple of (min_position, max_position) in seconds
        """
        d1 = self.metadata_video1.duration
        d2 = self.metadata_video2.duration
        min_position = 0.0

        if d1 <= 0 or d2 <= 0:
            max_position = max(d1, d2)
            return (min_position, max_position)

        offset_time = self.sync_offset_frames / self.metadata_video2.fps
        if self.sync_offset_frames < 0:
            max_pos_video2 = d2 - offset_time
            max_position = max(d1, max_pos_video2)
        elif self.sync_offset_frames > 0:
            max_position = min(d1, d2 - offset_time)
        else:
            max_position = min(d1, d2)

        return (min_position, max_position)

    def set_position(self, timestamp: float) -> None:
        """Set the current timeline position.

        Args:
            timestamp: Timestamp in seconds

        Raises:
            InvalidPositionError: If timestamp is out of valid range
        """
        min_position, max_position = self.get_effective_range()
        if timestamp < min_position or timestamp > max_position:
            raise InvalidPositionError(f"Position {timestamp} out of range [{min_position}, {max_position}]")
        self.current_position = timestamp

    def set_metadata_video1(self, metadata: VideoMetadata) -> None:
        """Set metadata for video 1 (e.g. after loading a file).

        Args:
            metadata: VideoMetadata for the first video
        """
        self.metadata_video1 = metadata

    def set_metadata_video2(self, metadata: VideoMetadata) -> None:
        """Set metadata for video 2 (e.g. after loading a file).

        Args:
            metadata: VideoMetadata for the second video
        """
        self.metadata_video2 = metadata

    def set_sync_offset(self, offset_frames: int) -> None:
        """Set the sync offset for video 2.

        Args:
            offset_frames: Offset in frames (can be negative)
        """
        self.sync_offset_frames = offset_frames

    def clamp_current_position_to_effective_range(self) -> None:
        """Clamp ``current_position`` to ``get_effective_range()`` (no exception)."""
        min_position, max_position = self.get_effective_range()
        self.current_position = max(min_position, min(self.current_position, max_position))

    def increment_sync_offset(self) -> None:
        """Increment the sync offset for video 2 by one frame."""
        self.sync_offset_frames += 1

    def decrement_sync_offset(self) -> None:
        """Decrement the sync offset for video 2 by one frame."""
        self.sync_offset_frames -= 1

    def get_resolved_frame_video1(self) -> int:
        """Get the resolved frame index for video 1 at current position.

        Returns:
            Frame index (0-based)
        """
        return self.time_to_frame_video1(self.current_position)

    def get_resolved_frame_video2(self) -> int:
        """Get the resolved frame index for video 2 at current position.

        Returns:
            Frame index (0-based)
        """
        return self.time_to_frame_video2(self.current_position)

    def get_resolved_time_video1(self) -> float:
        """Get the resolved timestamp for video 1 at current position.

        Returns:
            Timestamp in seconds
        """
        return self.current_position

    def get_resolved_time_video2(self) -> float:
        """Get the resolved timestamp for video 2 at current position.

        Returns:
            Timestamp in seconds
        """
        frame = self.get_resolved_frame_video2()
        return self.frame_to_time_video2(frame)

    def get_resolved_frames(self) -> Tuple[int, int]:
        """Get resolved frame indices for both videos.

        Returns:
            Tuple of (frame_video1, frame_video2)
        """
        return (self.get_resolved_frame_video1(), self.get_resolved_frame_video2())

    def get_resolved_times(self) -> Tuple[float, float]:
        """Get resolved timestamps for both videos.

        Returns:
            Tuple of (time_video1, time_video2)
        """
        return (self.get_resolved_time_video1(), self.get_resolved_time_video2())
