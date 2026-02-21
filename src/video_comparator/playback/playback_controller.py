"""Playback and stepping controller.

Responsibilities:
- Play/pause/stop state machine
- Frame-step forward/backward even when paused
- Drives tick events that request frames from the cache/decoder
- Delegates position math to Sync controller
- Maintains lockstep between videos respecting offsets
- Creates and updates PrefillStrategy instances for frame caches
"""

import threading
from typing import Callable, Iterator, Optional, Tuple

from video_comparator.cache.frame_cache import FrameCache
from video_comparator.cache.frame_result import FrameResult
from video_comparator.cache.prefill_strategy import PrefillStrategy, TrivialPrefillStrategy
from video_comparator.common.types import FrameRequestStatus, PlaybackState
from video_comparator.decode.video_decoder import VideoDecoder
from video_comparator.errors.error_handler import ErrorHandler
from video_comparator.media.video_metadata import VideoMetadata
from video_comparator.sync.timeline_controller import TimelineController


class PlaybackError(Exception):
    """Base exception for playback controller errors."""


class PlaybackStateError(PlaybackError):
    """Raised when an invalid playback state transition is attempted."""


class SynchronizationError(PlaybackError):
    """Raised when video synchronization fails."""


class PlaybackController:
    """Controls video playback and frame stepping."""

    def __init__(
        self,
        timeline_controller: TimelineController,
        decoder_video1: VideoDecoder,
        decoder_video2: VideoDecoder,
        frame_cache_video1: FrameCache,
        frame_cache_video2: FrameCache,
        error_handler: ErrorHandler,
        frame_callback: Optional[Callable[[FrameResult, FrameResult], None]] = None,
    ) -> None:
        """Initialize playback controller with timeline, decoders, and caches.

        Args:
            timeline_controller: Timeline controller for position and sync management
            decoder_video1: Decoder for the first video
            decoder_video2: Decoder for the second video
            frame_cache_video1: Frame cache for the first video
            frame_cache_video2: Frame cache for the second video
            error_handler: Error handler for displaying errors
            frame_callback: Optional callback function(result_video1, result_video2) called when frames are ready
        """
        self.timeline_controller: TimelineController = timeline_controller
        self.decoder_video1: VideoDecoder = decoder_video1
        self.decoder_video2: VideoDecoder = decoder_video2
        self.frame_cache_video1: FrameCache = frame_cache_video1
        self.frame_cache_video2: FrameCache = frame_cache_video2
        self.error_handler: ErrorHandler = error_handler
        self.frame_callback: Optional[Callable[[FrameResult, FrameResult], None]] = frame_callback
        self.state: PlaybackState = PlaybackState.STOPPED
        self.playback_speed: float = 1.0
        self._prefill_strategy_video1: Optional[PrefillStrategy] = None
        self._prefill_strategy_video2: Optional[PrefillStrategy] = None
        self._last_position: float = -1.0

        self._sync_lock = threading.Lock()
        self._pending_result_video1: Optional[FrameResult] = None
        self._pending_result_video2: Optional[FrameResult] = None

    def play(self) -> None:
        """Start or resume playback."""
        if self.state == PlaybackState.STOPPED:
            self.state = PlaybackState.PLAYING
            self._update_prefill_strategies()
        elif self.state == PlaybackState.PAUSED:
            self.state = PlaybackState.PLAYING
        elif self.state == PlaybackState.PLAYING:
            pass
        else:
            raise PlaybackStateError(f"Invalid state transition from {self.state} to PLAYING")

    def pause(self) -> None:
        """Pause playback."""
        if self.state == PlaybackState.PLAYING:
            self.state = PlaybackState.PAUSED
        elif self.state == PlaybackState.PAUSED:
            pass
        else:
            raise PlaybackStateError(f"Invalid state transition from {self.state} to PAUSED")

    def stop(self) -> None:
        """Stop playback and reset to beginning."""
        if self.state in (PlaybackState.PLAYING, PlaybackState.PAUSED):
            self.state = PlaybackState.STOPPED
            self.timeline_controller.set_position(0.0)
            self._update_prefill_strategies()
        elif self.state == PlaybackState.STOPPED:
            pass
        else:
            raise PlaybackStateError(f"Invalid state transition from {self.state} to STOPPED")

    def frame_step_forward(self) -> None:
        """Step forward one frame in both videos."""
        current_frame_video1 = self.timeline_controller.get_resolved_frame_video1()
        current_time = self.timeline_controller.current_position
        fps_video1 = self.timeline_controller.metadata_video1.fps
        frame_duration = 1.0 / fps_video1

        new_time = current_time + (frame_duration * self.playback_speed)
        max_duration = min(
            self.timeline_controller.metadata_video1.duration,
            self.timeline_controller.metadata_video2.duration,
        )
        new_time = min(new_time, max_duration)

        self.timeline_controller.set_position(new_time)
        self._request_frames()

    def frame_step_backward(self) -> None:
        """Step backward one frame in both videos."""
        current_time = self.timeline_controller.current_position
        fps_video1 = self.timeline_controller.metadata_video1.fps
        frame_duration = 1.0 / fps_video1

        new_time = current_time - (frame_duration * self.playback_speed)
        new_time = max(0.0, new_time)

        self.timeline_controller.set_position(new_time)
        self._request_frames()

    def tick(self, delta_time: float) -> None:
        """Advance playback by delta_time seconds.

        This method should be called periodically (e.g., from a GUI timer) to advance playback.

        Args:
            delta_time: Time elapsed since last tick in seconds
        """
        if self.state != PlaybackState.PLAYING:
            return

        current_time = self.timeline_controller.current_position
        max_duration = min(
            self.timeline_controller.metadata_video1.duration,
            self.timeline_controller.metadata_video2.duration,
        )

        new_time = current_time + (delta_time * self.playback_speed)
        if new_time >= max_duration:
            new_time = max_duration
            self.state = PlaybackState.STOPPED

        self.timeline_controller.set_position(new_time)
        self._request_frames()

    def request_frames_at_current_position(self) -> None:
        """Request frames for the current timeline position (e.g. after loading videos)."""
        self._last_position = -1.0
        self._request_frames()

    def _request_frames(self) -> None:
        """Request current frames from frame caches using prefill strategies."""
        self._update_prefill_strategies()

    def _update_prefill_strategies(self) -> None:
        """Update PrefillStrategy instances for both frame caches based on current position."""
        current_position = self.timeline_controller.current_position

        if current_position == self._last_position:
            return

        self._last_position = current_position

        frame_video1 = self.timeline_controller.get_resolved_frame_video1()
        frame_video2 = self.timeline_controller.get_resolved_frame_video2()

        frames_video1 = self._generate_protected_frame_sequence(frame_video1, self.timeline_controller.metadata_video1)
        frames_video2 = self._generate_protected_frame_sequence(frame_video2, self.timeline_controller.metadata_video2)

        self._prefill_strategy_video1 = TrivialPrefillStrategy(frames_video1)
        self._prefill_strategy_video2 = TrivialPrefillStrategy(frames_video2)

        with self._sync_lock:
            self._pending_result_video1 = None
            self._pending_result_video2 = None

        self.frame_cache_video1.request_prefill_frame(
            self._prefill_strategy_video1,
            lambda result: self._handle_frame_result(1, result),
            self.decoder_video1,
        )
        self.frame_cache_video2.request_prefill_frame(
            self._prefill_strategy_video2,
            lambda result: self._handle_frame_result(2, result),
            self.decoder_video2,
        )

    def _handle_frame_result(self, video_id: int, result: FrameResult) -> None:
        """Handle a frame result from one of the frame caches.

        This method synchronizes both frame results and calls the user callback
        only when both first frames have arrived. It handles CANCELLED and error
        statuses appropriately. After both frames arrive, it signals both frame
        caches that synchronization is complete.

        Args:
            video_id: 1 for video1, 2 for video2
            result: FrameResult from the frame cache
        """
        if result.status == FrameRequestStatus.CANCELLED:
            return

        if result.status != FrameRequestStatus.SUCCESS and result.error is not None:
            self.error_handler.handle_error(result.error)

        with self._sync_lock:
            if video_id == 1:
                self._pending_result_video1 = result
            else:
                self._pending_result_video2 = result

            if self._pending_result_video1 is not None and self._pending_result_video2 is not None:
                result1 = self._pending_result_video1
                result2 = self._pending_result_video2
                self._pending_result_video1 = None
                self._pending_result_video2 = None

                if self.frame_callback is not None:
                    self.frame_callback(result1, result2)

                self.frame_cache_video1.signal_sync_complete()
                self.frame_cache_video2.signal_sync_complete()

    def _generate_protected_frame_sequence(self, current_frame: int, metadata: VideoMetadata) -> Iterator[int]:
        """Generate a sequence of frame indices to protect around the current frame.

        Args:
            current_frame: Current frame index
            metadata: VideoMetadata for the video

        Yields:
            Frame indices in priority order
        """
        lookahead = 10
        lookbehind = 5

        start_frame = max(0, current_frame - lookbehind)
        end_frame = min(metadata.total_frames - 1, current_frame + lookahead)

        for frame_idx in range(start_frame, end_frame + 1):
            yield frame_idx

    def set_playback_speed(self, speed: float) -> None:
        """Set playback speed multiplier.

        Args:
            speed: Playback speed (1.0 = normal, 2.0 = 2x, 0.5 = 0.5x, etc.)
        """
        if speed <= 0:
            raise ValueError(f"Playback speed must be > 0, got {speed}")
        self.playback_speed = speed
