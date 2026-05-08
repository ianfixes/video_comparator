"""Playback and stepping controller.

Responsibilities:
- Play/pause/stop state machine with forward/reverse continuous playback
- Frame-step forward/backward even when paused
- Drives tick events that request frames from the cache/decoder
- Delegates position math to Sync controller
- Maintains lockstep between videos respecting offsets
- Creates and updates PrefillStrategy instances for frame caches
"""

import threading
from typing import Callable, Iterator, Optional, Tuple

from video_comparator.cache.frame_cache import FrameCache, print_framedebug
from video_comparator.cache.frame_result import FrameResult
from video_comparator.cache.prefill_strategy import PrefillStrategy, TrivialPrefillStrategy
from video_comparator.common.types import FrameRequestStatus, PlaybackDirection, PlaybackState
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
        decoder_video1: Optional[VideoDecoder],
        decoder_video2: Optional[VideoDecoder],
        frame_cache_video1: FrameCache,
        frame_cache_video2: FrameCache,
        error_handler: ErrorHandler,
        frame_callback: Optional[Callable[[FrameResult, FrameResult, float, int, float, int], None]] = None,
    ) -> None:
        """Initialize playback controller with timeline, decoders, and caches.

        At least one of decoder_video1 or decoder_video2 must be non-None for single- or dual-video playback.

        Args:
            timeline_controller: Timeline controller for position and sync management
            decoder_video1: Decoder for the first video (None if only video 2 loaded)
            decoder_video2: Decoder for the second video (None if only video 1 loaded)
            frame_cache_video1: Frame cache for the first video
            frame_cache_video2: Frame cache for the second video
            error_handler: Error handler for displaying errors
            frame_callback: Optional callback(result_v1, result_v2, time_v1, frame_v1, time_v2, frame_v2) when frames are ready
        """
        self.timeline_controller: TimelineController = timeline_controller
        self.decoder_video1: Optional[VideoDecoder] = decoder_video1
        self.decoder_video2: Optional[VideoDecoder] = decoder_video2
        self.frame_cache_video1: FrameCache = frame_cache_video1
        self.frame_cache_video2: FrameCache = frame_cache_video2
        self.error_handler: ErrorHandler = error_handler
        self.frame_callback: Optional[
            Callable[[FrameResult, FrameResult, float, int, float, int], None]
        ] = frame_callback
        self.state: PlaybackState = PlaybackState.STOPPED
        self.playback_direction: PlaybackDirection = PlaybackDirection.FORWARD
        self.playback_speed: float = 1.0
        self._prefill_strategy_video1: Optional[PrefillStrategy] = None
        self._prefill_strategy_video2: Optional[PrefillStrategy] = None
        self._last_position: float = -1.0

        self._sync_lock = threading.Lock()
        self._pending_result_video1: Optional[FrameResult] = None
        self._pending_result_video2: Optional[FrameResult] = None

    def play(self) -> None:
        """Start or resume playback.

        From STOPPED, direction is forward. From PAUSED, the previous playback direction is kept.
        """
        if self.state == PlaybackState.STOPPED:
            self.playback_direction = PlaybackDirection.FORWARD
        self._transition_to_playing()

    def play_forward(self) -> None:
        """Play forward; if already playing in reverse, switches direction without moving the timeline."""
        prev_direction = self.playback_direction
        self.playback_direction = PlaybackDirection.FORWARD
        self._transition_to_playing()
        if self.state == PlaybackState.PLAYING and prev_direction != PlaybackDirection.FORWARD:
            self._last_position = -1.0
            self._request_frames()

    def play_reverse(self) -> None:
        """Play in reverse; if already playing forward, switches direction without moving the timeline."""
        prev_direction = self.playback_direction
        self.playback_direction = PlaybackDirection.REVERSE
        self._transition_to_playing()
        if self.state == PlaybackState.PLAYING and prev_direction != PlaybackDirection.REVERSE:
            self._last_position = -1.0
            self._request_frames()

    def _transition_to_playing(self) -> None:
        """Enter PLAYING from STOPPED or PAUSED, or keep PLAYING (e.g. after direction change)."""
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
            self.playback_direction = PlaybackDirection.FORWARD
            self.timeline_controller.set_position(0.0)
            self._update_prefill_strategies()
        elif self.state == PlaybackState.STOPPED:
            pass
        else:
            raise PlaybackStateError(f"Invalid state transition from {self.state} to STOPPED")

    def shutdown(self) -> None:
        """Quiesce playback state for application teardown without requesting frames."""
        self.state = PlaybackState.STOPPED
        self.playback_direction = PlaybackDirection.FORWARD
        self._last_position = -1.0
        with self._sync_lock:
            self._pending_result_video1 = None
            self._pending_result_video2 = None

    def _get_max_duration(self) -> float:
        """Return effective max timeline duration (handles one or two videos)."""
        _, max_position = self.timeline_controller.get_effective_range()
        return max_position

    def frame_step_forward(self) -> None:
        """Step forward one frame in both videos."""
        current_time = self.timeline_controller.current_position
        fps_video1 = self.timeline_controller.metadata_video1.fps
        frame_duration = 1.0 / fps_video1

        new_time = current_time + (frame_duration * self.playback_speed)
        max_duration = self._get_max_duration()
        new_time = min(new_time, max_duration)

        print_framedebug("Step forward requested: position %.3f -> %.3f" % (current_time, new_time))
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
        min_duration, max_duration = self.timeline_controller.get_effective_range()
        step = delta_time * self.playback_speed

        if self.playback_direction == PlaybackDirection.FORWARD:
            new_time = current_time + step
            if new_time >= max_duration:
                new_time = max_duration
                self.state = PlaybackState.STOPPED
        else:
            new_time = current_time - step
            if new_time <= min_duration:
                new_time = min_duration
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

        frames_video1 = self._generate_protected_frame_sequence(
            frame_video1, self.timeline_controller.metadata_video1, self.playback_direction
        )
        frames_video2 = self._generate_protected_frame_sequence(
            frame_video2, self.timeline_controller.metadata_video2, self.playback_direction
        )

        self._prefill_strategy_video1 = TrivialPrefillStrategy(frames_video1)
        self._prefill_strategy_video2 = TrivialPrefillStrategy(frames_video2)

        print_framedebug(
            "PlaybackController: requesting frames at position %.3f "
            "frame_v1=%d frame_v2=%d" % (current_position, frame_video1, frame_video2)
        )

        with self._sync_lock:
            self._pending_result_video1 = None
            self._pending_result_video2 = None

        placeholder = FrameResult(0, None, FrameRequestStatus.SUCCESS, None)
        only_video1 = self.decoder_video2 is None
        only_video2 = self.decoder_video1 is None

        if self.decoder_video1 is not None:
            self.frame_cache_video1.request_prefill_frame(
                self._prefill_strategy_video1,
                lambda result: self._handle_frame_result(1, result),
                self.decoder_video1,
            )
        if self.decoder_video2 is not None:
            self.frame_cache_video2.request_prefill_frame(
                self._prefill_strategy_video2,
                lambda result: self._handle_frame_result(2, result),
                self.decoder_video2,
            )

        if only_video1:
            self._handle_frame_result(2, placeholder)
        elif only_video2:
            self._handle_frame_result(1, placeholder)

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
        print_framedebug(
            "PlaybackController: frame result received video_id=%d "
            "frame_number=%d status=%s has_frame=%s"
            % (
                video_id,
                result.frame_number,
                result.status.name,
                result.frame is not None,
            )
        )
        if result.status == FrameRequestStatus.CANCELLED:
            print_framedebug("PlaybackController: frame discarded (cancelled)")
            return

        if result.status != FrameRequestStatus.SUCCESS and result.error is not None:
            self.error_handler.handle_error(self._annotate_error_with_video_context(video_id, result.error))

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
                    time_v1 = self.timeline_controller.get_resolved_time_video1()
                    frame_v1 = self.timeline_controller.get_resolved_frame_video1()
                    time_v2 = self.timeline_controller.get_resolved_time_video2()
                    frame_v2 = self.timeline_controller.get_resolved_frame_video2()
                    print_framedebug(
                        "PlaybackController: invoking frame_callback " "frame_v1=%d frame_v2=%d" % (frame_v1, frame_v2)
                    )
                    self.frame_callback(result1, result2, time_v1, frame_v1, time_v2, frame_v2)

                if self.decoder_video1 is not None:
                    self.frame_cache_video1.signal_sync_complete()
                if self.decoder_video2 is not None:
                    self.frame_cache_video2.signal_sync_complete()

    def _annotate_error_with_video_context(self, video_id: int, error: Exception) -> Exception:
        """Attach decoder identity context (video slot and file) to frame errors."""
        decoder = self.decoder_video1 if video_id == 1 else self.decoder_video2
        file_path = None
        if decoder is not None and decoder.metadata.file_path is not None:
            file_path = decoder.metadata.file_path.name
        decoder_label = f"video {video_id}"
        if file_path is not None:
            decoder_label = f"{decoder_label} ({file_path})"
        annotated_message = f"{decoder_label}: {error}"
        try:
            return error.__class__(annotated_message)
        except Exception:
            return Exception(annotated_message)

    def _generate_protected_frame_sequence(
        self,
        current_frame: int,
        metadata: VideoMetadata,
        direction: PlaybackDirection,
    ) -> Iterator[int]:
        """Generate a sequence of frame indices to protect around the current frame.

        The current (display) frame is yielded first so the frame cache delivers
        it as the "first" frame to the callback. Remaining frames are for prefetch.

        When playing in reverse, prefetch prioritizes frames before the current frame first
        (decoder still seeks/decodes forward from keyframes as usual).

        Args:
            current_frame: Current frame index (display frame; must be first)
            metadata: VideoMetadata for the video
            direction: Active playback direction for prefetch ordering

        Yields:
            Frame indices in priority order (forward: current, ahead, behind; reverse: current, behind, ahead)
        """
        lookahead = 10
        lookbehind = 5

        end_frame = min(metadata.total_frames - 1, current_frame + lookahead)
        start_frame = max(0, current_frame - lookbehind)

        yield current_frame
        if direction == PlaybackDirection.FORWARD:
            for frame_idx in range(current_frame + 1, end_frame + 1):
                yield frame_idx
            for frame_idx in range(current_frame - 1, start_frame - 1, -1):
                yield frame_idx
        else:
            for frame_idx in range(current_frame - 1, start_frame - 1, -1):
                yield frame_idx
            for frame_idx in range(current_frame + 1, end_frame + 1):
                yield frame_idx

    def set_playback_speed(self, speed: float) -> None:
        """Set playback speed multiplier.

        Args:
            speed: Playback speed (1.0 = normal, 2.0 = 2x, 0.5 = 0.5x, etc.)
        """
        if speed <= 0:
            raise ValueError(f"Playback speed must be > 0, got {speed}")
        self.playback_speed = speed
