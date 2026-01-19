"""Playback and stepping controller.

Responsibilities:
- Play/pause/stop state machine
- Frame-step forward/backward even when paused
- Drives tick events that request frames from the cache/decoder
- Delegates position math to Sync controller
- Maintains lockstep between videos respecting offsets
"""

from typing import Optional

from video_comparator.cache.frame_cache import FrameCache
from video_comparator.common.types import PlaybackState
from video_comparator.decode.video_decoder import VideoDecoder
from video_comparator.sync.timeline_controller import TimelineController


class PlaybackController:
    """Controls video playback and frame stepping."""

    def __init__(
        self,
        timeline_controller: TimelineController,
        decoder_video1: VideoDecoder,
        decoder_video2: VideoDecoder,
        frame_cache_video1: FrameCache,
        frame_cache_video2: FrameCache,
    ) -> None:
        """Initialize playback controller with timeline, decoders, and optional caches."""
        self.timeline_controller: TimelineController = timeline_controller
        self.decoder_video1: VideoDecoder = decoder_video1
        self.decoder_video2: VideoDecoder = decoder_video2
        self.frame_cache_video1: FrameCache = frame_cache_video1
        self.frame_cache_video2: FrameCache = frame_cache_video2
        self.state: PlaybackState = PlaybackState.STOPPED
        self.playback_speed: float = 1.0
