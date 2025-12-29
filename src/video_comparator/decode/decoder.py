"""Video decoder engine.

Responsibilities:
- Open video containers via PyAV
- Frame-accurate seek (time- or frame-based)
- Decode frames to NumPy arrays
- Handle differing fps/timebases
- Optional hardware acceleration flags
"""

from typing import Optional

import numpy as np

from video_comparator.cache.frame_cache import FrameCache
from video_comparator.media.metadata import VideoMetadata


class VideoDecoder:
    """Decodes video frames from a video file."""

    def __init__(
        self,
        metadata: VideoMetadata,
        frame_cache: Optional[FrameCache] = None,
        hardware_accel: bool = False,
    ) -> None:
        """Initialize video decoder with metadata, optional cache, and hardware acceleration flag."""
        self.metadata: VideoMetadata = metadata
        self.frame_cache: Optional[FrameCache] = frame_cache
        self.hardware_accel: bool = hardware_accel
        self.container = None  # PyAV container
        self.video_stream = None  # PyAV video stream
