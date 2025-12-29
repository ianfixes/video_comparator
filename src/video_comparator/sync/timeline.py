"""Timeline and synchronization controller.

Responsibilities:
- Single source of truth for playback position and per-video sync offsets
- All seeks/steps go through this controller
- Converts between wall-clock, timestamps, and frame indices
- Provides resolved target frame/time to consumers
"""

from typing import Optional, Tuple

from video_comparator.media.metadata import VideoMetadata


class TimelineController:
    """Manages timeline position and synchronization offsets."""

    def __init__(
        self,
        metadata_video1: VideoMetadata,
        metadata_video2: VideoMetadata,
    ) -> None:
        """Initialize timeline controller with metadata for both videos."""
        self.metadata_video1: VideoMetadata = metadata_video1
        self.metadata_video2: VideoMetadata = metadata_video2
        self.current_position: float = 0.0  # Timeline position in seconds
        self.sync_offset_frames: int = 0  # Offset for video2 in frames (can be negative)
