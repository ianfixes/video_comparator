"""Video decoder engine.

Responsibilities:
- Open video containers via PyAV
- Frame-accurate seek (time- or frame-based)
- Decode frames to NumPy arrays
- Handle differing fps/timebases
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
    ) -> None:
        """Initialize video decoder with metadata and optional cache."""
        self.metadata: VideoMetadata = metadata
        self.frame_cache: Optional[FrameCache] = frame_cache
        self.container = None  # PyAV container
        self.video_stream = None  # PyAV video stream
