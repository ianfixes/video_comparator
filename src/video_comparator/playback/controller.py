"""Playback and stepping controller.

Responsibilities:
- Play/pause/stop state machine
- Frame-step forward/backward even when paused
- Drives tick events that request frames from the cache/decoder
- Delegates position math to Sync controller
- Maintains lockstep between videos respecting offsets
"""

from enum import Enum
from typing import Optional

from video_comparator.cache.frame_cache import FrameCache
from video_comparator.decode.decoder import VideoDecoder
from video_comparator.sync.timeline import TimelineController


class PlaybackState(Enum):
    """Playback state enumeration."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class PlaybackController:
    """Controls video playback and frame stepping."""

    def __init__(
        self,
        timeline_controller: TimelineController,
        decoder_video1: VideoDecoder,
        decoder_video2: VideoDecoder,
        frame_cache_video1: Optional[FrameCache] = None,
        frame_cache_video2: Optional[FrameCache] = None,
    ) -> None:
        """Initialize playback controller with timeline, decoders, and optional caches."""
        self.timeline_controller: TimelineController = timeline_controller
        self.decoder_video1: VideoDecoder = decoder_video1
        self.decoder_video2: VideoDecoder = decoder_video2
        self.frame_cache_video1: Optional[FrameCache] = frame_cache_video1
        self.frame_cache_video2: Optional[FrameCache] = frame_cache_video2
        self.state: PlaybackState = PlaybackState.STOPPED
        self.playback_speed: float = 1.0
