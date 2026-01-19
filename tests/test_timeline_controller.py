"""Unit tests for TimelineController class."""

import unittest
from pathlib import Path

from video_comparator.media.video_metadata import VideoMetadata
from video_comparator.sync.timeline_controller import InvalidPositionError, TimelineController


class TestTimelineController(unittest.TestCase):
    """Test cases for TimelineController class."""

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

    def test_initial_position_is_zero(self) -> None:
        """Test initial position is 0.0."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        self.assertEqual(controller.current_position, 0.0)

    def test_initial_sync_offset_is_zero(self) -> None:
        """Test initial sync offset is 0."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        self.assertEqual(controller.sync_offset_frames, 0)

    def test_frame_to_time_conversion_video1_30fps(self) -> None:
        """Test frame-to-time conversion for video 1 at 30fps."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        self.assertAlmostEqual(controller.frame_to_time_video1(0), 0.0)
        self.assertAlmostEqual(controller.frame_to_time_video1(30), 1.0)
        self.assertAlmostEqual(controller.frame_to_time_video1(150), 5.0)
        self.assertAlmostEqual(controller.frame_to_time_video1(300), 10.0)

    def test_frame_to_time_conversion_video1_24fps(self) -> None:
        """Test frame-to-time conversion for video 1 at 24fps."""
        controller = TimelineController(self.metadata_24fps, self.metadata_30fps)
        self.assertAlmostEqual(controller.frame_to_time_video1(0), 0.0)
        self.assertAlmostEqual(controller.frame_to_time_video1(24), 1.0)
        self.assertAlmostEqual(controller.frame_to_time_video1(120), 5.0)
        self.assertAlmostEqual(controller.frame_to_time_video1(240), 10.0)

    def test_frame_to_time_conversion_video2_with_positive_offset(self) -> None:
        """Test frame-to-time conversion for video 2 with positive offset."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        controller.set_sync_offset(5)

        frame = 5
        expected_time = (frame - 5) / 24.0
        self.assertAlmostEqual(controller.frame_to_time_video2(frame), expected_time)

        frame = 29
        expected_time = (frame - 5) / 24.0
        self.assertAlmostEqual(controller.frame_to_time_video2(frame), expected_time)

    def test_frame_to_time_conversion_video2_with_negative_offset(self) -> None:
        """Test frame-to-time conversion for video 2 with negative offset."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        controller.set_sync_offset(-3)

        frame = 0
        expected_time = (frame - (-3)) / 24.0
        self.assertAlmostEqual(controller.frame_to_time_video2(frame), expected_time)

        frame = 24
        expected_time = (frame - (-3)) / 24.0
        self.assertAlmostEqual(controller.frame_to_time_video2(frame), expected_time)

    def test_time_to_frame_conversion_video1_30fps(self) -> None:
        """Test time-to-frame conversion for video 1 at 30fps."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        self.assertEqual(controller.time_to_frame_video1(0.0), 0)
        self.assertEqual(controller.time_to_frame_video1(1.0), 30)
        self.assertEqual(controller.time_to_frame_video1(5.0), 150)
        self.assertEqual(controller.time_to_frame_video1(10.0), 299)

    def test_time_to_frame_conversion_video1_24fps(self) -> None:
        """Test time-to-frame conversion for video 1 at 24fps."""
        controller = TimelineController(self.metadata_24fps, self.metadata_30fps)
        self.assertEqual(controller.time_to_frame_video1(0.0), 0)
        self.assertEqual(controller.time_to_frame_video1(1.0), 24)
        self.assertEqual(controller.time_to_frame_video1(5.0), 120)
        self.assertEqual(controller.time_to_frame_video1(10.0), 239)

    def test_time_to_frame_conversion_video2_with_positive_offset(self) -> None:
        """Test time-to-frame conversion for video 2 with positive offset."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        controller.set_sync_offset(5)

        timestamp = 0.0
        expected_frame = int(timestamp * 24.0) + 5
        self.assertEqual(controller.time_to_frame_video2(timestamp), expected_frame)

        timestamp = 1.0
        expected_frame = int(timestamp * 24.0) + 5
        self.assertEqual(controller.time_to_frame_video2(timestamp), expected_frame)

    def test_time_to_frame_conversion_video2_with_negative_offset(self) -> None:
        """Test time-to-frame conversion for video 2 with negative offset."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        controller.set_sync_offset(-3)

        timestamp = 0.0
        calculated_frame = int(timestamp * 24.0) + (-3)
        expected_frame = max(0, min(calculated_frame, self.metadata_24fps.total_frames - 1))
        self.assertEqual(controller.time_to_frame_video2(timestamp), expected_frame)

        timestamp = 1.0
        calculated_frame = int(timestamp * 24.0) + (-3)
        expected_frame = max(0, min(calculated_frame, self.metadata_24fps.total_frames - 1))
        self.assertEqual(controller.time_to_frame_video2(timestamp), expected_frame)

    def test_position_setting_updates_current_position(self) -> None:
        """Test position setting updates current position."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        self.assertEqual(controller.current_position, 0.0)

        controller.set_position(5.0)
        self.assertEqual(controller.current_position, 5.0)

        controller.set_position(7.5)
        self.assertEqual(controller.current_position, 7.5)

    def test_position_setting_out_of_range_raises_error(self) -> None:
        """Test position setting with out of range value raises error."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)

        with self.assertRaises(InvalidPositionError) as context:
            controller.set_position(-1.0)

        self.assertIn("out of range", str(context.exception))

        with self.assertRaises(InvalidPositionError) as context:
            controller.set_position(11.0)

        self.assertIn("out of range", str(context.exception))

    def test_sync_offset_setting(self) -> None:
        """Test sync offset setting."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        self.assertEqual(controller.sync_offset_frames, 0)

        controller.set_sync_offset(5)
        self.assertEqual(controller.sync_offset_frames, 5)

        controller.set_sync_offset(-10)
        self.assertEqual(controller.sync_offset_frames, -10)

        controller.set_sync_offset(0)
        self.assertEqual(controller.sync_offset_frames, 0)

    def test_sync_offset_increment(self) -> None:
        """Test sync offset increment (+1 frame)."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        self.assertEqual(controller.sync_offset_frames, 0)

        controller.increment_sync_offset()
        self.assertEqual(controller.sync_offset_frames, 1)

        controller.increment_sync_offset()
        self.assertEqual(controller.sync_offset_frames, 2)

    def test_sync_offset_decrement(self) -> None:
        """Test sync offset decrement (-1 frame)."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        self.assertEqual(controller.sync_offset_frames, 0)

        controller.decrement_sync_offset()
        self.assertEqual(controller.sync_offset_frames, -1)

        controller.decrement_sync_offset()
        self.assertEqual(controller.sync_offset_frames, -2)

    def test_resolved_frame_calculation_video1(self) -> None:
        """Test resolved frame calculation for video 1."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        controller.set_position(5.0)

        resolved_frame = controller.get_resolved_frame_video1()
        expected_frame = controller.time_to_frame_video1(5.0)
        self.assertEqual(resolved_frame, expected_frame)
        self.assertEqual(resolved_frame, 150)

    def test_resolved_frame_calculation_video2_with_offset(self) -> None:
        """Test resolved frame calculation for video 2 with offset."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        controller.set_position(5.0)
        controller.set_sync_offset(10)

        resolved_frame = controller.get_resolved_frame_video2()
        expected_frame = controller.time_to_frame_video2(5.0)
        self.assertEqual(resolved_frame, expected_frame)

    def test_resolved_time_calculation_video1(self) -> None:
        """Test resolved time calculation for video 1."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        controller.set_position(5.0)

        resolved_time = controller.get_resolved_time_video1()
        self.assertEqual(resolved_time, 5.0)

    def test_resolved_time_calculation_video2(self) -> None:
        """Test resolved time calculation for video 2."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        controller.set_position(5.0)
        controller.set_sync_offset(10)

        resolved_time = controller.get_resolved_time_video2()
        resolved_frame = controller.get_resolved_frame_video2()
        expected_time = controller.frame_to_time_video2(resolved_frame)
        self.assertAlmostEqual(resolved_time, expected_time)

    def test_resolved_times_both_videos(self) -> None:
        """Test resolved time calculation for both videos."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        controller.set_position(5.0)

        times = controller.get_resolved_times()
        self.assertEqual(len(times), 2)
        self.assertEqual(times[0], 5.0)
        self.assertIsInstance(times[1], float)

    def test_resolved_frames_both_videos(self) -> None:
        """Test resolved frame calculation for both videos."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        controller.set_position(5.0)

        frames = controller.get_resolved_frames()
        self.assertEqual(len(frames), 2)
        self.assertIsInstance(frames[0], int)
        self.assertIsInstance(frames[1], int)

    def test_different_framerates_24fps_vs_30fps(self) -> None:
        """Test with videos of different framerates (24fps vs 30fps)."""
        controller = TimelineController(self.metadata_24fps, self.metadata_30fps)
        controller.set_position(5.0)

        frame1 = controller.get_resolved_frame_video1()
        frame2 = controller.get_resolved_frame_video2()

        self.assertEqual(frame1, 120)  # 5.0 * 24
        self.assertEqual(frame2, 150)  # 5.0 * 30

    def test_edge_case_position_at_start(self) -> None:
        """Test edge case: position at start."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        controller.set_position(0.0)

        frame1 = controller.get_resolved_frame_video1()
        frame2 = controller.get_resolved_frame_video2()

        self.assertEqual(frame1, 0)
        self.assertEqual(frame2, 0)

    def test_edge_case_position_at_end(self) -> None:
        """Test edge case: position at end."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        controller.set_position(10.0)

        frame1 = controller.get_resolved_frame_video1()
        frame2 = controller.get_resolved_frame_video2()

        self.assertEqual(frame1, 299)
        self.assertEqual(frame2, 239)

    def test_edge_case_large_positive_offset(self) -> None:
        """Test edge case: large positive offset."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        controller.set_sync_offset(100)
        controller.set_position(5.0)

        frame2 = controller.get_resolved_frame_video2()
        self.assertGreaterEqual(frame2, 0)
        self.assertLessEqual(frame2, self.metadata_24fps.total_frames - 1)

    def test_edge_case_large_negative_offset(self) -> None:
        """Test edge case: large negative offset."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        controller.set_sync_offset(-100)
        controller.set_position(5.0)

        frame2 = controller.get_resolved_frame_video2()
        self.assertGreaterEqual(frame2, 0)
        self.assertLessEqual(frame2, self.metadata_24fps.total_frames - 1)

    def test_time_to_frame_clamps_to_valid_range(self) -> None:
        """Test time-to-frame conversion clamps to valid frame range."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)

        frame = controller.time_to_frame_video1(100.0)
        self.assertEqual(frame, 299)

        frame = controller.time_to_frame_video1(-10.0)
        self.assertEqual(frame, 0)

    def test_time_to_frame_video2_clamps_to_valid_range(self) -> None:
        """Test time-to-frame conversion for video 2 clamps to valid range."""
        controller = TimelineController(self.metadata_30fps, self.metadata_24fps)
        controller.set_sync_offset(1000)

        frame = controller.time_to_frame_video2(10.0)
        self.assertLessEqual(frame, self.metadata_24fps.total_frames - 1)
        self.assertGreaterEqual(frame, 0)

    def test_position_with_different_durations(self) -> None:
        """Test position setting with videos of different durations."""
        metadata_short = VideoMetadata(
            file_path=Path("/test/short.avi"),
            duration=5.0,
            fps=30.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=150,
            time_base=0.001,
        )

        controller = TimelineController(metadata_short, self.metadata_30fps)

        controller.set_position(5.0)
        self.assertEqual(controller.current_position, 5.0)

        with self.assertRaises(InvalidPositionError):
            controller.set_position(6.0)
