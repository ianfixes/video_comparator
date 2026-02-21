"""Unit tests for PlaybackController class."""

import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import numpy as np

from video_comparator.cache.frame_cache import FrameCache
from video_comparator.cache.frame_result import FrameResult
from video_comparator.common.types import FrameRequestStatus, PlaybackState
from video_comparator.decode.video_decoder import DecodeError, SeekError, VideoDecoder
from video_comparator.errors.error_handler import ErrorHandler
from video_comparator.media.video_metadata import VideoMetadata
from video_comparator.playback.playback_controller import PlaybackController, PlaybackStateError, SynchronizationError
from video_comparator.sync.timeline_controller import TimelineController


class TestPlaybackController(unittest.TestCase):
    """Test cases for PlaybackController class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.metadata_30fps = VideoMetadata(
            file_path=Path("/test/video1.avi"),
            duration=10.0,
            fps=30.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=300,
            time_base=0.001,
        )

        self.metadata_24fps = VideoMetadata(
            file_path=Path("/test/video2.avi"),
            duration=10.0,
            fps=24.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=240,
            time_base=0.001,
        )

        self.timeline_controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        self.decoder_video1 = MagicMock(spec=VideoDecoder)
        self.decoder_video1.metadata = self.metadata_30fps
        self.decoder_video2 = MagicMock(spec=VideoDecoder)
        self.decoder_video2.metadata = self.metadata_24fps
        self.frame_cache_video1 = MagicMock(spec=FrameCache)
        self.frame_cache_video2 = MagicMock(spec=FrameCache)
        self.error_handler = MagicMock(spec=ErrorHandler)

    def test_initial_state_is_stopped(self) -> None:
        """Test initial state is STOPPED."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        self.assertEqual(controller.state, PlaybackState.STOPPED)

    def test_state_transition_stopped_to_playing(self) -> None:
        """Test state transition STOPPED → PLAYING."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        self.assertEqual(controller.state, PlaybackState.PLAYING)

    def test_state_transition_playing_to_paused(self) -> None:
        """Test state transition PLAYING → PAUSED."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        controller.pause()
        self.assertEqual(controller.state, PlaybackState.PAUSED)

    def test_state_transition_paused_to_playing(self) -> None:
        """Test state transition PAUSED → PLAYING."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        controller.pause()
        controller.play()
        self.assertEqual(controller.state, PlaybackState.PLAYING)

    def test_state_transition_playing_to_stopped(self) -> None:
        """Test state transition PLAYING → STOPPED."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        controller.stop()
        self.assertEqual(controller.state, PlaybackState.STOPPED)
        self.assertEqual(self.timeline_controller.current_position, 0.0)

    def test_state_transition_paused_to_stopped(self) -> None:
        """Test state transition PAUSED → STOPPED."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        controller.pause()
        controller.stop()
        self.assertEqual(controller.state, PlaybackState.STOPPED)
        self.assertEqual(self.timeline_controller.current_position, 0.0)

    def test_frame_step_forward_when_paused(self) -> None:
        """Test frame_step_forward when paused."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        controller.pause()
        initial_position = self.timeline_controller.current_position
        controller.frame_step_forward()
        self.assertGreater(self.timeline_controller.current_position, initial_position)

    def test_frame_step_forward_when_playing(self) -> None:
        """Test frame_step_forward when playing."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        initial_position = self.timeline_controller.current_position
        controller.frame_step_forward()
        self.assertGreater(self.timeline_controller.current_position, initial_position)

    def test_frame_step_backward_when_paused(self) -> None:
        """Test frame_step_backward when paused."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        self.timeline_controller.set_position(1.0)
        controller.pause()
        initial_position = self.timeline_controller.current_position
        controller.frame_step_backward()
        self.assertLess(self.timeline_controller.current_position, initial_position)

    def test_frame_step_backward_when_playing(self) -> None:
        """Test frame_step_backward when playing."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        self.timeline_controller.set_position(1.0)
        initial_position = self.timeline_controller.current_position
        controller.frame_step_backward()
        self.assertLess(self.timeline_controller.current_position, initial_position)

    def test_frame_step_forward_requests_correct_frames(self) -> None:
        """Test frame_step_forward requests correct frames via FrameCache."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        controller.frame_step_forward()

        self.frame_cache_video1.request_prefill_frame.assert_called()
        self.frame_cache_video2.request_prefill_frame.assert_called()

    def test_frame_step_backward_requests_correct_frames(self) -> None:
        """Test frame_step_backward requests correct frames via FrameCache."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        self.timeline_controller.set_position(1.0)
        controller.frame_step_backward()

        self.frame_cache_video1.request_prefill_frame.assert_called()
        self.frame_cache_video2.request_prefill_frame.assert_called()

    def test_play_maintains_lockstep_between_videos(self) -> None:
        """Test play() maintains lockstep between videos."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()

        self.frame_cache_video1.request_prefill_frame.assert_called()
        self.frame_cache_video2.request_prefill_frame.assert_called()

    def test_tick_loop_advances_both_videos_in_sync(self) -> None:
        """Test tick loop advances both videos in sync."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        initial_position = self.timeline_controller.current_position
        controller.tick(0.1)
        self.assertGreater(self.timeline_controller.current_position, initial_position)

    def test_playback_respects_sync_offsets(self) -> None:
        """Test playback respects sync offsets."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        self.timeline_controller.set_sync_offset(5)
        controller.play()

        frame_video1 = self.timeline_controller.get_resolved_frame_video1()
        frame_video2 = self.timeline_controller.get_resolved_frame_video2()
        self.assertEqual(frame_video2, frame_video1 + 5)

    def test_playback_speed_adjustment(self) -> None:
        """Test playback speed adjustment."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.set_playback_speed(2.0)
        self.assertEqual(controller.playback_speed, 2.0)

        controller.play()
        initial_position = self.timeline_controller.current_position
        controller.tick(0.1)
        delta = self.timeline_controller.current_position - initial_position
        self.assertAlmostEqual(delta, 0.2, places=5)

    def test_playback_speed_validation(self) -> None:
        """Test playback speed validation."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        with self.assertRaises(ValueError):
            controller.set_playback_speed(0.0)
        with self.assertRaises(ValueError):
            controller.set_playback_speed(-1.0)

    def test_edge_case_step_at_start_of_video(self) -> None:
        """Test edge case: step at start of video."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        self.timeline_controller.set_position(0.0)
        controller.frame_step_backward()
        self.assertEqual(self.timeline_controller.current_position, 0.0)

    def test_edge_case_step_at_end_of_video(self) -> None:
        """Test edge case: step at end of video."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        max_duration = min(self.metadata_30fps.duration, self.metadata_24fps.duration)
        self.timeline_controller.set_position(max_duration)
        initial_position = self.timeline_controller.current_position
        controller.frame_step_forward()
        self.assertEqual(self.timeline_controller.current_position, initial_position)

    def test_prefill_strategy_creation_for_each_video(self) -> None:
        """Test PrefillStrategy creation for each video."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()

        self.frame_cache_video1.request_prefill_frame.assert_called_once()
        self.frame_cache_video2.request_prefill_frame.assert_called_once()

        call1 = self.frame_cache_video1.request_prefill_frame.call_args
        call2 = self.frame_cache_video2.request_prefill_frame.call_args

        self.assertIsNotNone(call1)
        self.assertIsNotNone(call2)
        if call1 and call2:
            strategy1 = call1[0][0]
            strategy2 = call2[0][0]
            self.assertIsNotNone(strategy1)
            self.assertIsNotNone(strategy2)

    def test_prefill_strategy_updates_when_position_changes(self) -> None:
        """Test PrefillStrategy updates when position changes."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        self.frame_cache_video1.request_prefill_frame.reset_mock()
        self.frame_cache_video2.request_prefill_frame.reset_mock()

        controller.frame_step_forward()
        self.frame_cache_video1.request_prefill_frame.assert_called()
        self.frame_cache_video2.request_prefill_frame.assert_called()

    def test_prefill_strategy_handles_different_framerates(self) -> None:
        """Test PrefillStrategy handles different framerates correctly."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()

        frame_video1 = self.timeline_controller.get_resolved_frame_video1()
        frame_video2 = self.timeline_controller.get_resolved_frame_video2()

        self.assertIsNotNone(frame_video1)
        self.assertIsNotNone(frame_video2)

    def test_synchronization_both_frames_deliver_before_callback(self) -> None:
        """Test synchronization: both frame caches deliver first frames before user callback."""
        callback_results = []
        callback_lock = threading.Lock()

        def frame_callback(
            result1: FrameResult,
            result2: FrameResult,
            _t1: float,
            _f1: int,
            _t2: float,
            _f2: int,
        ) -> None:
            with callback_lock:
                callback_results.append((result1, result2))

        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
            frame_callback=frame_callback,
        )

        frame1 = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame2 = np.zeros((1080, 1920, 3), dtype=np.uint8)

        result1 = FrameResult(frame_number=0, frame=frame1, status=FrameRequestStatus.SUCCESS)
        result2 = FrameResult(frame_number=0, frame=frame2, status=FrameRequestStatus.SUCCESS)

        controller.play()

        callback_video1 = None
        callback_video2 = None

        def capture_callback_video1(result: FrameResult) -> None:
            nonlocal callback_video1
            callback_video1 = result
            controller._handle_frame_result(1, result)

        def capture_callback_video2(result: FrameResult) -> None:
            nonlocal callback_video2
            callback_video2 = result
            controller._handle_frame_result(2, result)

        call1 = self.frame_cache_video1.request_prefill_frame.call_args
        call2 = self.frame_cache_video2.request_prefill_frame.call_args

        if call1 and call2:
            callback1 = call1[0][1]
            callback2 = call2[0][1]

            callback1(result1)
            self.assertIsNone(callback_video1)
            self.assertEqual(len(callback_results), 0)

            callback2(result2)
            time.sleep(0.1)
            self.assertEqual(len(callback_results), 1)

    def test_signal_sync_complete_called_after_both_frames_arrive(self) -> None:
        """Test synchronization: signal_sync_complete() called on both caches after both first frames arrive."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )

        frame1 = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame2 = np.zeros((1080, 1920, 3), dtype=np.uint8)

        result1 = FrameResult(frame_number=0, frame=frame1, status=FrameRequestStatus.SUCCESS)
        result2 = FrameResult(frame_number=0, frame=frame2, status=FrameRequestStatus.SUCCESS)

        controller.play()

        call1 = self.frame_cache_video1.request_prefill_frame.call_args
        call2 = self.frame_cache_video2.request_prefill_frame.call_args

        if call1 and call2:
            callback1 = call1[0][1]
            callback2 = call2[0][1]

            callback1(result1)
            self.frame_cache_video1.signal_sync_complete.assert_not_called()
            self.frame_cache_video2.signal_sync_complete.assert_not_called()

            callback2(result2)
            time.sleep(0.1)
            self.frame_cache_video1.signal_sync_complete.assert_called_once()
            self.frame_cache_video2.signal_sync_complete.assert_called_once()

    def test_sync_signal_sent_even_when_one_video_has_error(self) -> None:
        """Test synchronization: sync signal sent even when one video has error."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )

        frame1 = np.zeros((1080, 1920, 3), dtype=np.uint8)
        error = DecodeError("Decode failed")

        result1 = FrameResult(frame_number=0, frame=frame1, status=FrameRequestStatus.SUCCESS)
        result2 = FrameResult(frame_number=0, frame=None, status=FrameRequestStatus.DECODE_ERROR, error=error)

        controller.play()

        call1 = self.frame_cache_video1.request_prefill_frame.call_args
        call2 = self.frame_cache_video2.request_prefill_frame.call_args

        if call1 and call2:
            callback1 = call1[0][1]
            callback2 = call2[0][1]

            callback1(result1)
            callback2(result2)
            time.sleep(0.1)

            self.frame_cache_video1.signal_sync_complete.assert_called_once()
            self.frame_cache_video2.signal_sync_complete.assert_called_once()
            self.error_handler.handle_error.assert_called_once_with(error)

    def test_cancelled_frame_result_status_handling(self) -> None:
        """Test CANCELLED FrameResult status handling (discarded)."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )

        result = FrameResult(frame_number=0, frame=None, status=FrameRequestStatus.CANCELLED)

        controller._handle_frame_result(1, result)

        self.frame_cache_video1.signal_sync_complete.assert_not_called()
        self.frame_cache_video2.signal_sync_complete.assert_not_called()

    def test_error_frame_result_status_handling(self) -> None:
        """Test error FrameResult status handling (ErrorHandler integration)."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )

        error = SeekError("Seek failed")
        result = FrameResult(frame_number=0, frame=None, status=FrameRequestStatus.SEEK_ERROR, error=error)

        controller._handle_frame_result(1, result)

        self.error_handler.handle_error.assert_called_once_with(error)

    def test_user_callback_receives_frame_result_objects(self) -> None:
        """Test user callback receives FrameResult objects for both videos."""
        callback_results = []

        def frame_callback(
            result1: FrameResult,
            result2: FrameResult,
            _t1: float,
            _f1: int,
            _t2: float,
            _f2: int,
        ) -> None:
            callback_results.append((result1, result2))

        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
            frame_callback=frame_callback,
        )

        frame1 = np.zeros((1080, 1920, 3), dtype=np.uint8)
        frame2 = np.zeros((1080, 1920, 3), dtype=np.uint8)

        result1 = FrameResult(frame_number=0, frame=frame1, status=FrameRequestStatus.SUCCESS)
        result2 = FrameResult(frame_number=0, frame=frame2, status=FrameRequestStatus.SUCCESS)

        controller.play()

        call1 = self.frame_cache_video1.request_prefill_frame.call_args
        call2 = self.frame_cache_video2.request_prefill_frame.call_args

        if call1 and call2:
            callback1 = call1[0][1]
            callback2 = call2[0][1]

            callback1(result1)
            callback2(result2)
            time.sleep(0.1)

            self.assertEqual(len(callback_results), 1)
            self.assertEqual(callback_results[0][0], result1)
            self.assertEqual(callback_results[0][1], result2)

    def test_tick_stops_at_end_of_video(self) -> None:
        """Test tick stops playback at end of video."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        controller.play()
        max_duration = min(self.metadata_30fps.duration, self.metadata_24fps.duration)
        self.timeline_controller.set_position(max_duration - 0.1)
        controller.tick(1.0)
        self.assertEqual(controller.state, PlaybackState.STOPPED)
        self.assertEqual(self.timeline_controller.current_position, max_duration)

    def test_tick_does_nothing_when_not_playing(self) -> None:
        """Test tick does nothing when not playing."""
        controller = PlaybackController(
            self.timeline_controller,
            self.decoder_video1,
            self.decoder_video2,
            self.frame_cache_video1,
            self.frame_cache_video2,
            self.error_handler,
        )
        initial_position = self.timeline_controller.current_position
        controller.tick(0.1)
        self.assertEqual(self.timeline_controller.current_position, initial_position)
