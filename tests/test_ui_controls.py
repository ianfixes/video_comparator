"""Unit tests for UI controls."""

import unittest
from unittest.mock import MagicMock, patch

import wx

from video_comparator.cache.frame_cache import FrameCache
from video_comparator.cache.frame_result import FrameRequestStatus, FrameResult
from video_comparator.common.types import PlaybackState
from video_comparator.decode.video_decoder import VideoDecoder
from video_comparator.errors.error_handler import ErrorHandler
from video_comparator.media.video_metadata import VideoMetadata
from video_comparator.playback.playback_controller import PlaybackController
from video_comparator.render.video_pane import VideoPane
from video_comparator.sync.timeline_controller import TimelineController
from video_comparator.ui.controls import ControlPanel, SyncControls, TimelineSlider, ZoomControls


class TestTimelineSlider(unittest.TestCase):
    """Test cases for TimelineSlider class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.parent = MagicMock(spec=wx.Window)
        self.metadata1 = VideoMetadata(
            file_path=None,
            duration=10.0,
            fps=30.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=300,
            time_base=1.0 / 30.0,
        )
        self.metadata2 = VideoMetadata(
            file_path=None,
            duration=12.0,
            fps=25.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=300,
            time_base=1.0 / 25.0,
        )
        self.timeline_controller = TimelineController(self.metadata1, self.metadata2)

    def test_initialization(self) -> None:
        """Test TimelineSlider initialization."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.StaticText"
        ) as mock_static_text_class:
            mock_slider = MagicMock()
            mock_slider.GetMax.return_value = 10000
            mock_slider.GetValue.return_value = 0
            mock_slider_class.return_value = mock_slider
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            slider = TimelineSlider(self.parent, self.timeline_controller)

            self.assertEqual(slider.parent, self.parent)
            self.assertEqual(slider.timeline_controller, self.timeline_controller)
            mock_slider_class.assert_called_once()
            call_args = mock_slider_class.call_args
            self.assertEqual(call_args[0][0], self.parent)
            self.assertEqual(call_args[1]["minValue"], 0)
            self.assertEqual(call_args[1]["maxValue"], 10000)
            self.assertEqual(call_args[1]["value"], 0)
            mock_static_text_class.assert_called_once()
            mock_slider.Bind.assert_called_once()

    def test_slider_range_calculation_from_video_metadata(self) -> None:
        """Test slider range calculation from video metadata."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.StaticText"
        ):
            mock_slider = MagicMock()
            mock_slider.GetMax.return_value = 10000
            mock_slider.GetValue.return_value = 0
            mock_slider_class.return_value = mock_slider

            slider = TimelineSlider(self.parent, self.timeline_controller)

            call_args = mock_slider_class.call_args
            max_duration = min(self.metadata1.duration, self.metadata2.duration)
            expected_max_milliseconds = int(max_duration * 1000)
            self.assertEqual(call_args[1]["maxValue"], expected_max_milliseconds)

    def test_update_range_after_sync_offset_change_preserves_playhead(self) -> None:
        """Sync offset must not move the timeline wx slider; only labels refresh."""
        self.timeline_controller.set_position(9.5)
        self.timeline_controller.set_sync_offset(75)

        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.StaticText"
        ) as mock_static_text_class:
            mock_slider = MagicMock()
            mock_slider.GetMax.return_value = 9000
            mock_slider.GetMin.return_value = 0
            mock_slider.GetValue.return_value = 9500
            mock_slider_class.return_value = mock_slider
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            slider = TimelineSlider(self.parent, self.timeline_controller)
            mock_slider.reset_mock()

            slider.update_range_after_sync_offset_change()

            self.assertEqual(self.timeline_controller.current_position, 9.5)
            mock_slider.SetRange.assert_not_called()
            mock_slider.SetValue.assert_not_called()
            mock_static_text.SetLabel.assert_called()

    def test_slider_value_change_triggers_timeline_controller_seek(self) -> None:
        """Test slider value change triggers TimelineController seek."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.StaticText"
        ) as mock_static_text_class:
            mock_slider = MagicMock()
            mock_slider.GetMax.return_value = 10000
            mock_slider.GetValue.return_value = 5000
            mock_slider_class.return_value = mock_slider
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            slider = TimelineSlider(self.parent, self.timeline_controller)

            mock_event = MagicMock()
            slider._on_slider_change(mock_event)

            self.assertEqual(self.timeline_controller.current_position, 5.0)
            mock_static_text.SetLabel.assert_called()

    def test_position_display_updates_correctly(self) -> None:
        """Test position display updates correctly."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.StaticText"
        ) as mock_static_text_class:
            mock_slider = MagicMock()
            mock_slider.GetMax.return_value = 10000
            mock_slider.GetValue.return_value = 0
            mock_slider_class.return_value = mock_slider
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            slider = TimelineSlider(self.parent, self.timeline_controller)

            self.timeline_controller.set_position(2.5)
            slider._update_position_display()

            mock_static_text.SetLabel.assert_called()
            call_args = mock_static_text.SetLabel.call_args[0][0]
            self.assertIn("00:00:02", call_args)
            self.assertIn("Frame", call_args)
            self.assertIn("V1", call_args)
            self.assertIn("V2", call_args)

    def test_slider_with_videos_of_different_durations(self) -> None:
        """Test slider with videos of different durations."""
        metadata_short = VideoMetadata(
            file_path=None,
            duration=5.0,
            fps=30.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=150,
            time_base=1.0 / 30.0,
        )
        metadata_long = VideoMetadata(
            file_path=None,
            duration=20.0,
            fps=30.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=600,
            time_base=1.0 / 30.0,
        )
        timeline_controller = TimelineController(metadata_short, metadata_long)

        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.StaticText"
        ):
            mock_slider = MagicMock()
            mock_slider.GetMax.return_value = 5000
            mock_slider.GetValue.return_value = 0
            mock_slider_class.return_value = mock_slider

            slider = TimelineSlider(self.parent, timeline_controller)

            call_args = mock_slider_class.call_args
            max_duration = min(metadata_short.duration, metadata_long.duration)
            expected_max_milliseconds = int(max_duration * 1000)
            self.assertEqual(call_args[1]["maxValue"], expected_max_milliseconds)

    def test_update_position_updates_slider_and_display(self) -> None:
        """Test update_position updates slider and display."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.StaticText"
        ) as mock_static_text_class:
            mock_slider = MagicMock()
            mock_slider.GetMin.return_value = 0
            mock_slider.GetMax.return_value = 10000
            mock_slider.GetValue.return_value = 0
            mock_slider_class.return_value = mock_slider
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            slider = TimelineSlider(self.parent, self.timeline_controller)

            self.timeline_controller.set_position(3.5)
            slider.update_position()

            mock_slider.SetValue.assert_called_once_with(3500)
            mock_static_text.SetLabel.assert_called()

    def test_update_position_clamps_to_max_duration(self) -> None:
        """Test update_position clamps to max duration."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.StaticText"
        ) as mock_static_text_class:
            mock_slider = MagicMock()
            mock_slider.GetMin.return_value = 0
            mock_slider.GetMax.return_value = 10000
            mock_slider.GetValue.return_value = 0
            mock_slider_class.return_value = mock_slider
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            slider = TimelineSlider(self.parent, self.timeline_controller)

            self.timeline_controller.current_position = 15.0
            slider.update_position()

            mock_slider.SetValue.assert_called_once_with(10000)

    def test_slider_change_does_not_trigger_when_updating_from_controller(self) -> None:
        """Test slider change does not trigger when updating from controller."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.StaticText"
        ) as mock_static_text_class:
            mock_slider = MagicMock()
            mock_slider.GetMax.return_value = 10000
            mock_slider.GetValue.return_value = 5000
            mock_slider_class.return_value = mock_slider
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            slider = TimelineSlider(self.parent, self.timeline_controller)
            initial_position = self.timeline_controller.current_position

            slider._updating_from_controller = True
            mock_event = MagicMock()
            slider._on_slider_change(mock_event)

            self.assertEqual(self.timeline_controller.current_position, initial_position)

    def test_get_widget_returns_slider(self) -> None:
        """Test get_widget returns the slider widget."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.StaticText"
        ):
            mock_slider = MagicMock()
            mock_slider.GetMax.return_value = 10000
            mock_slider.GetValue.return_value = 0
            mock_slider_class.return_value = mock_slider

            slider = TimelineSlider(self.parent, self.timeline_controller)

            self.assertEqual(slider.get_widget(), mock_slider)

    def test_get_position_label_returns_label(self) -> None:
        """Test get_position_label returns the position label widget."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.StaticText"
        ) as mock_static_text_class:
            mock_slider = MagicMock()
            mock_slider.GetMax.return_value = 10000
            mock_slider.GetValue.return_value = 0
            mock_slider_class.return_value = mock_slider
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            slider = TimelineSlider(self.parent, self.timeline_controller)

            self.assertEqual(slider.get_position_label(), mock_static_text)

    def test_position_display_format_includes_time_and_frames(self) -> None:
        """Test position display format includes time and frames."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.StaticText"
        ) as mock_static_text_class:
            mock_slider = MagicMock()
            mock_slider.GetMax.return_value = 10000
            mock_slider.GetValue.return_value = 0
            mock_slider_class.return_value = mock_slider
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            slider = TimelineSlider(self.parent, self.timeline_controller)

            self.timeline_controller.set_position(1.5)
            slider._update_position_display()

            call_args = mock_static_text.SetLabel.call_args[0][0]
            self.assertIn(":", call_args)
            self.assertIn("Frame", call_args)
            self.assertIn("V1", call_args)
            self.assertIn("V2", call_args)


class TestSyncControls(unittest.TestCase):
    """Test cases for SyncControls class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.parent = MagicMock(spec=wx.Window)
        self.metadata1 = VideoMetadata(
            file_path=None,
            duration=10.0,
            fps=30.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=300,
            time_base=1.0 / 30.0,
        )
        self.metadata2 = VideoMetadata(
            file_path=None,
            duration=12.0,
            fps=25.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=300,
            time_base=1.0 / 25.0,
        )
        self.timeline_controller = TimelineController(self.metadata1, self.metadata2)

    def test_initialization(self) -> None:
        """Test SyncControls initialization."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.Button"
        ) as mock_button_class, patch("video_comparator.ui.controls.wx.StaticText") as mock_static_text_class:
            mock_slider = MagicMock()
            mock_slider.GetValue.return_value = 0
            mock_slider_class.return_value = mock_slider
            mock_button = MagicMock()
            mock_button_class.return_value = mock_button
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            controls = SyncControls(self.parent, self.timeline_controller)

            self.assertEqual(controls.parent, self.parent)
            self.assertEqual(controls.timeline_controller, self.timeline_controller)
            mock_slider_class.assert_called_once()
            self.assertEqual(mock_button_class.call_count, 2)
            mock_static_text_class.assert_called_once()
            mock_slider.Bind.assert_called_once()
            self.assertEqual(mock_button.Bind.call_count, 2)

    def test_offset_slider_updates_timeline_controller(self) -> None:
        """Test offset slider updates TimelineController."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.Button"
        ), patch("video_comparator.ui.controls.wx.StaticText"):
            mock_slider = MagicMock()
            mock_slider.GetValue.return_value = 50
            mock_slider_class.return_value = mock_slider

            controls = SyncControls(self.parent, self.timeline_controller)

            mock_event = MagicMock()
            controls._on_slider_change(mock_event)

            self.assertEqual(self.timeline_controller.sync_offset_frames, 50)

    def test_increment_button_increments_offset(self) -> None:
        """Test +1 button increments offset."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.Button"
        ), patch("video_comparator.ui.controls.wx.StaticText"):
            mock_slider = MagicMock()
            mock_slider.GetValue.return_value = 0
            mock_slider.GetMin.return_value = -1000
            mock_slider.GetMax.return_value = 1000
            mock_slider_class.return_value = mock_slider

            controls = SyncControls(self.parent, self.timeline_controller)
            initial_offset = self.timeline_controller.sync_offset_frames

            mock_event = MagicMock()
            controls._on_increment(mock_event)

            self.assertEqual(self.timeline_controller.sync_offset_frames, initial_offset + 1)
            mock_slider.SetValue.assert_called()

    def test_decrement_button_decrements_offset(self) -> None:
        """Test -1 button decrements offset."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.Button"
        ), patch("video_comparator.ui.controls.wx.StaticText"):
            mock_slider = MagicMock()
            mock_slider.GetValue.return_value = 0
            mock_slider.GetMin.return_value = -1000
            mock_slider.GetMax.return_value = 1000
            mock_slider_class.return_value = mock_slider

            controls = SyncControls(self.parent, self.timeline_controller)
            initial_offset = self.timeline_controller.sync_offset_frames

            mock_event = MagicMock()
            controls._on_decrement(mock_event)

            self.assertEqual(self.timeline_controller.sync_offset_frames, initial_offset - 1)
            mock_slider.SetValue.assert_called()

    def test_offset_display_shows_current_offset(self) -> None:
        """Test offset display shows current offset."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.Button"
        ), patch("video_comparator.ui.controls.wx.StaticText") as mock_static_text_class:
            mock_slider = MagicMock()
            mock_slider.GetValue.return_value = 0
            mock_slider_class.return_value = mock_slider
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            controls = SyncControls(self.parent, self.timeline_controller)

            self.timeline_controller.set_sync_offset(25)
            controls._update_offset_display()

            mock_static_text.SetLabel.assert_called()
            call_args = mock_static_text.SetLabel.call_args[0][0]
            self.assertIn("Offset", call_args)
            self.assertIn("25", call_args)
            self.assertIn("frames", call_args)

    def test_offset_display_shows_negative_offset(self) -> None:
        """Test offset display shows negative offset correctly."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.Button"
        ), patch("video_comparator.ui.controls.wx.StaticText") as mock_static_text_class:
            mock_slider = MagicMock()
            mock_slider.GetValue.return_value = 0
            mock_slider_class.return_value = mock_slider
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            controls = SyncControls(self.parent, self.timeline_controller)

            self.timeline_controller.set_sync_offset(-30)
            controls._update_offset_display()

            call_args = mock_static_text.SetLabel.call_args[0][0]
            self.assertIn("-30", call_args)

    def test_offset_range_limits(self) -> None:
        """Test offset range limits."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.Button"
        ), patch("video_comparator.ui.controls.wx.StaticText"):
            mock_slider = MagicMock()
            mock_slider.GetValue.return_value = 0
            mock_slider.GetMin.return_value = -500
            mock_slider.GetMax.return_value = 500
            mock_slider_class.return_value = mock_slider

            controls = SyncControls(
                self.parent, self.timeline_controller, min_offset_frames=-500, max_offset_frames=500
            )

            call_args = mock_slider_class.call_args
            self.assertEqual(call_args[1]["minValue"], -500)
            self.assertEqual(call_args[1]["maxValue"], 500)

    def test_update_offset_updates_slider_and_display(self) -> None:
        """Test update_offset updates slider and display."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.Button"
        ), patch("video_comparator.ui.controls.wx.StaticText") as mock_static_text_class:
            mock_slider = MagicMock()
            mock_slider.GetValue.return_value = 0
            mock_slider.GetMin.return_value = -1000
            mock_slider.GetMax.return_value = 1000
            mock_slider_class.return_value = mock_slider
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            controls = SyncControls(self.parent, self.timeline_controller)

            self.timeline_controller.set_sync_offset(75)
            controls.update_offset()

            mock_slider.SetValue.assert_called_once_with(75)
            mock_static_text.SetLabel.assert_called()

    def test_update_offset_clamps_to_range(self) -> None:
        """Test update_offset clamps to range limits."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.Button"
        ), patch("video_comparator.ui.controls.wx.StaticText"):
            mock_slider = MagicMock()
            mock_slider.GetValue.return_value = 0
            mock_slider.GetMin.return_value = -1000
            mock_slider.GetMax.return_value = 1000
            mock_slider_class.return_value = mock_slider

            controls = SyncControls(self.parent, self.timeline_controller)

            self.timeline_controller.sync_offset_frames = 1500
            controls.update_offset()

            mock_slider.SetValue.assert_called_once_with(1000)

    def test_slider_change_does_not_trigger_when_updating_from_controller(self) -> None:
        """Test slider change does not trigger when updating from controller."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.Button"
        ), patch("video_comparator.ui.controls.wx.StaticText"):
            mock_slider = MagicMock()
            mock_slider.GetValue.return_value = 50
            mock_slider_class.return_value = mock_slider

            controls = SyncControls(self.parent, self.timeline_controller)
            initial_offset = self.timeline_controller.sync_offset_frames

            controls._updating_from_controller = True
            mock_event = MagicMock()
            controls._on_slider_change(mock_event)

            self.assertEqual(self.timeline_controller.sync_offset_frames, initial_offset)

    def test_sync_offset_callback_invoked_on_slider_change(self) -> None:
        """Changing the offset slider invokes on_sync_offset_changed."""
        callback = MagicMock()
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.Button"
        ), patch("video_comparator.ui.controls.wx.StaticText"):
            mock_slider = MagicMock()
            mock_slider.GetValue.return_value = 10
            mock_slider_class.return_value = mock_slider

            controls = SyncControls(self.parent, self.timeline_controller, on_sync_offset_changed=callback)
            mock_event = MagicMock()
            controls._on_slider_change(mock_event)

            callback.assert_called_once()

    def test_sync_offset_callback_invoked_on_increment(self) -> None:
        """+1 invokes on_sync_offset_changed."""
        callback = MagicMock()
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.Button"
        ), patch("video_comparator.ui.controls.wx.StaticText"):
            mock_slider = MagicMock()
            mock_slider.GetValue.return_value = 0
            mock_slider_class.return_value = mock_slider

            controls = SyncControls(self.parent, self.timeline_controller, on_sync_offset_changed=callback)
            mock_event = MagicMock()
            controls._on_increment(mock_event)

            callback.assert_called_once()

    def test_sync_offset_callback_invoked_on_decrement(self) -> None:
        """-1 invokes on_sync_offset_changed."""
        callback = MagicMock()
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.Button"
        ), patch("video_comparator.ui.controls.wx.StaticText"):
            mock_slider = MagicMock()
            mock_slider.GetValue.return_value = 0
            mock_slider_class.return_value = mock_slider

            controls = SyncControls(self.parent, self.timeline_controller, on_sync_offset_changed=callback)
            mock_event = MagicMock()
            controls._on_decrement(mock_event)

            callback.assert_called_once()

    def test_get_widgets_return_correct_widgets(self) -> None:
        """Test getter methods return correct widgets."""
        with patch("video_comparator.ui.controls.wx.Slider") as mock_slider_class, patch(
            "video_comparator.ui.controls.wx.Button"
        ) as mock_button_class, patch("video_comparator.ui.controls.wx.StaticText") as mock_static_text_class:
            mock_slider = MagicMock()
            mock_slider.GetValue.return_value = 0
            mock_slider_class.return_value = mock_slider
            mock_button = MagicMock()
            mock_button_class.return_value = mock_button
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            controls = SyncControls(self.parent, self.timeline_controller)

            self.assertEqual(controls.get_offset_slider(), mock_slider)
            self.assertEqual(controls.get_increment_button(), mock_button)
            self.assertEqual(controls.get_decrement_button(), mock_button)
            self.assertEqual(controls.get_offset_label(), mock_static_text)


class TestZoomControls(unittest.TestCase):
    """Test cases for ZoomControls class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.parent = MagicMock(spec=wx.Window)
        from video_comparator.render.scaling_calculator import ScalingCalculator

        scaling_calculator = ScalingCalculator()
        self.panel_patcher = patch("video_comparator.render.video_pane.wx.Panel.__init__", return_value=None)
        self.bind_patcher = patch.object(VideoPane, "Bind", return_value=None)
        self.getsize_patcher = patch.object(VideoPane, "GetSize", return_value=wx.Size(800, 600))
        self.refresh_patcher = patch.object(VideoPane, "Refresh", return_value=None)
        self.capture_patcher = patch.object(VideoPane, "CaptureMouse", return_value=None)
        self.release_patcher = patch.object(VideoPane, "ReleaseMouse", return_value=None)
        self.hascapture_patcher = patch.object(VideoPane, "HasCapture", return_value=False)

        self.panel_patcher.start()
        self.bind_patcher.start()
        self.getsize_patcher.start()
        self.refresh_patcher.start()
        self.capture_patcher.start()
        self.release_patcher.start()
        self.hascapture_patcher.start()

        zoom_metadata = VideoMetadata(
            file_path=None,
            duration=10.0,
            fps=30.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=300,
            time_base=1.0 / 30.0,
        )
        self.video_pane1 = VideoPane(self.parent, scaling_calculator, zoom_metadata)
        self.video_pane2 = VideoPane(self.parent, scaling_calculator, zoom_metadata)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.hascapture_patcher.stop()
        self.release_patcher.stop()
        self.capture_patcher.stop()
        self.refresh_patcher.stop()
        self.getsize_patcher.stop()
        self.bind_patcher.stop()
        self.panel_patcher.stop()

    def test_initialization(self) -> None:
        """Test ZoomControls initialization."""
        with patch("video_comparator.ui.controls.wx.Button") as mock_button_class, patch(
            "video_comparator.ui.controls.wx.StaticText"
        ) as mock_static_text_class:
            mock_button = MagicMock()
            mock_button_class.return_value = mock_button
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            controls = ZoomControls(self.parent, self.video_pane1, self.video_pane2)

            self.assertEqual(controls.parent, self.parent)
            self.assertEqual(controls.video_pane1, self.video_pane1)
            self.assertEqual(controls.video_pane2, self.video_pane2)
            self.assertTrue(controls.synchronized)
            self.assertEqual(mock_button_class.call_count, 3)
            self.assertEqual(mock_static_text_class.call_count, 1)

    def test_initialization_with_independent_mode(self) -> None:
        """Test ZoomControls initialization with independent mode."""
        with patch("video_comparator.ui.controls.wx.Button"), patch("video_comparator.ui.controls.wx.StaticText"):
            controls = ZoomControls(self.parent, self.video_pane1, self.video_pane2, synchronized=False)

            self.assertFalse(controls.synchronized)

    def test_zoom_in_button_increases_zoom_level(self) -> None:
        """Test zoom in button increases zoom level."""
        with patch("video_comparator.ui.controls.wx.Button"), patch("video_comparator.ui.controls.wx.StaticText"):
            controls = ZoomControls(self.parent, self.video_pane1, self.video_pane2)
            initial_zoom = self.video_pane1.get_zoom_level()

            mock_event = MagicMock()
            controls._on_zoom_in(mock_event)

            new_zoom = self.video_pane1.get_zoom_level()
            self.assertGreater(new_zoom, initial_zoom)

    def test_zoom_out_button_decreases_zoom_level(self) -> None:
        """Test zoom out button decreases zoom level."""
        with patch("video_comparator.ui.controls.wx.Button"), patch("video_comparator.ui.controls.wx.StaticText"):
            controls = ZoomControls(self.parent, self.video_pane1, self.video_pane2)
            self.video_pane1.zoom_level = 2.0
            initial_zoom = self.video_pane1.get_zoom_level()

            mock_event = MagicMock()
            controls._on_zoom_out(mock_event)

            new_zoom = self.video_pane1.get_zoom_level()
            self.assertLess(new_zoom, initial_zoom)

    def test_zoom_reset_button_returns_to_one(self) -> None:
        """Test zoom reset button returns to 1.0."""
        with patch("video_comparator.ui.controls.wx.Button"), patch("video_comparator.ui.controls.wx.StaticText"):
            controls = ZoomControls(self.parent, self.video_pane1, self.video_pane2)
            self.video_pane1.zoom_level = 3.5
            self.video_pane2.zoom_level = 3.5

            mock_event = MagicMock()
            controls._on_zoom_reset(mock_event)

            self.assertEqual(self.video_pane1.get_zoom_level(), 1.0)
            self.assertEqual(self.video_pane2.get_zoom_level(), 1.0)

    def test_zoom_updates_both_video_panes_when_synchronized(self) -> None:
        """Test zoom updates both VideoPanes when synchronized."""
        with patch("video_comparator.ui.controls.wx.Button"), patch("video_comparator.ui.controls.wx.StaticText"):
            controls = ZoomControls(self.parent, self.video_pane1, self.video_pane2, synchronized=True)
            initial_zoom1 = self.video_pane1.get_zoom_level()
            initial_zoom2 = self.video_pane2.get_zoom_level()

            mock_event = MagicMock()
            controls._on_zoom_in(mock_event)

            new_zoom1 = self.video_pane1.get_zoom_level()
            new_zoom2 = self.video_pane2.get_zoom_level()
            self.assertGreater(new_zoom1, initial_zoom1)
            self.assertGreater(new_zoom2, initial_zoom2)

    def test_zoom_updates_individual_video_pane_when_independent(self) -> None:
        """Test zoom updates individual VideoPane when independent."""
        with patch("video_comparator.ui.controls.wx.Button"), patch("video_comparator.ui.controls.wx.StaticText"):
            controls = ZoomControls(self.parent, self.video_pane1, self.video_pane2, synchronized=False)
            initial_zoom1 = self.video_pane1.get_zoom_level()
            initial_zoom2 = self.video_pane2.get_zoom_level()

            mock_event = MagicMock()
            controls._on_zoom_in(mock_event)

            new_zoom1 = self.video_pane1.get_zoom_level()
            new_zoom2 = self.video_pane2.get_zoom_level()
            self.assertGreater(new_zoom1, initial_zoom1)
            self.assertEqual(new_zoom2, initial_zoom2)

    def test_zoom_level_display_updates_correctly(self) -> None:
        """Test zoom level display updates correctly."""
        with patch("video_comparator.ui.controls.wx.Button"), patch(
            "video_comparator.ui.controls.wx.StaticText"
        ) as mock_static_text_class:
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            controls = ZoomControls(self.parent, self.video_pane1, self.video_pane2)
            self.video_pane1.zoom_level = 2.5
            self.video_pane2.zoom_level = 3.0

            controls._update_zoom_display()

            mock_static_text.SetLabel.assert_called()
            call_args = mock_static_text.SetLabel.call_args[0][0]
            self.assertIn("Zoom", call_args)
            self.assertIn("2.50", call_args)
            self.assertIn("3.00", call_args)
            self.assertIn("x", call_args)
            self.assertEqual(call_args, "Zoom: 2.50x / 3.00x")

    def test_zoom_level_display_shows_both_values_when_synchronized(self) -> None:
        """Test zoom level display shows both values when synchronized."""
        with patch("video_comparator.ui.controls.wx.Button"), patch(
            "video_comparator.ui.controls.wx.StaticText"
        ) as mock_static_text_class:
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            controls = ZoomControls(self.parent, self.video_pane1, self.video_pane2, synchronized=True)
            self.video_pane1.zoom_level = 1.5
            self.video_pane2.zoom_level = 1.5
            controls._update_zoom_display()

            call_args = mock_static_text.SetLabel.call_args[0][0]
            self.assertIn("1.50", call_args)
            self.assertEqual(call_args.count("1.50"), 2)
            self.assertEqual(call_args, "Zoom: 1.50x / 1.50x")

    def test_zoom_level_display_shows_both_values_when_independent(self) -> None:
        """Test zoom level display shows both values when independent."""
        with patch("video_comparator.ui.controls.wx.Button"), patch(
            "video_comparator.ui.controls.wx.StaticText"
        ) as mock_static_text_class:
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            controls = ZoomControls(self.parent, self.video_pane1, self.video_pane2, synchronized=False)
            self.video_pane1.zoom_level = 2.0
            self.video_pane2.zoom_level = 1.0
            controls._update_zoom_display()

            call_args = mock_static_text.SetLabel.call_args[0][0]
            self.assertIn("2.00", call_args)
            self.assertIn("1.00", call_args)
            self.assertEqual(call_args, "Zoom: 2.00x / 1.00x")

    def test_get_widgets_return_correct_widgets(self) -> None:
        """Test getter methods return correct widgets."""
        with patch("video_comparator.ui.controls.wx.Button") as mock_button_class, patch(
            "video_comparator.ui.controls.wx.StaticText"
        ) as mock_static_text_class:
            mock_button = MagicMock()
            mock_button_class.return_value = mock_button
            mock_static_text = MagicMock()
            mock_static_text_class.return_value = mock_static_text

            controls = ZoomControls(self.parent, self.video_pane1, self.video_pane2)

            self.assertEqual(controls.get_zoom_in_button(), mock_button)
            self.assertEqual(controls.get_zoom_out_button(), mock_button)
            self.assertEqual(controls.get_zoom_reset_button(), mock_button)
            self.assertEqual(controls.get_zoom_label(), mock_static_text)


class TestControlPanel(unittest.TestCase):
    """Test cases for ControlPanel class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.parent = MagicMock(spec=wx.Window)
        self.metadata1 = VideoMetadata(
            file_path=None,
            duration=10.0,
            fps=30.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=300,
            time_base=1.0 / 30.0,
        )
        self.metadata2 = VideoMetadata(
            file_path=None,
            duration=12.0,
            fps=25.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=300,
            time_base=1.0 / 25.0,
        )
        self.timeline_controller = TimelineController(self.metadata1, self.metadata2)

        self.decoder1 = MagicMock(spec=VideoDecoder)
        self.decoder2 = MagicMock(spec=VideoDecoder)
        self.frame_cache1 = MagicMock(spec=FrameCache)
        self.frame_cache2 = MagicMock(spec=FrameCache)
        self.error_handler = MagicMock(spec=ErrorHandler)

        self.playback_controller = PlaybackController(
            self.timeline_controller,
            self.decoder1,
            self.decoder2,
            self.frame_cache1,
            self.frame_cache2,
            self.error_handler,
        )

        from video_comparator.render.scaling_calculator import ScalingCalculator

        scaling_calculator = ScalingCalculator()
        self.panel_patcher = patch("video_comparator.render.video_pane.wx.Panel.__init__", return_value=None)
        self.bind_patcher = patch.object(VideoPane, "Bind", return_value=None)
        self.getsize_patcher = patch.object(VideoPane, "GetSize", return_value=wx.Size(800, 600))
        self.refresh_patcher = patch.object(VideoPane, "Refresh", return_value=None)
        self.capture_patcher = patch.object(VideoPane, "CaptureMouse", return_value=None)
        self.release_patcher = patch.object(VideoPane, "ReleaseMouse", return_value=None)
        self.hascapture_patcher = patch.object(VideoPane, "HasCapture", return_value=False)

        self.panel_patcher.start()
        self.bind_patcher.start()
        self.getsize_patcher.start()
        self.refresh_patcher.start()
        self.capture_patcher.start()
        self.release_patcher.start()
        self.hascapture_patcher.start()

        zoom_metadata = VideoMetadata(
            file_path=None,
            duration=10.0,
            fps=30.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=300,
            time_base=1.0 / 30.0,
        )
        self.video_pane1 = VideoPane(self.parent, scaling_calculator, zoom_metadata)
        self.video_pane2 = VideoPane(self.parent, scaling_calculator, zoom_metadata)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.hascapture_patcher.stop()
        self.release_patcher.stop()
        self.capture_patcher.stop()
        self.refresh_patcher.stop()
        self.getsize_patcher.stop()
        self.bind_patcher.stop()
        self.panel_patcher.stop()

    def test_initialization(self) -> None:
        """Test ControlPanel initialization."""
        with patch("video_comparator.ui.controls.ControlPanel._create_layout"), patch(
            "video_comparator.ui.controls.wx.Panel"
        ) as mock_panel_class, patch("video_comparator.ui.controls.wx.Button") as mock_button_class, patch(
            "video_comparator.ui.controls.TimelineSlider"
        ), patch(
            "video_comparator.ui.controls.SyncControls"
        ), patch(
            "video_comparator.ui.controls.ZoomControls"
        ):
            mock_panel = MagicMock()
            mock_panel_class.return_value = mock_panel
            mock_button = MagicMock()
            mock_button_class.return_value = mock_button

            control_panel = ControlPanel(
                self.parent,
                self.playback_controller,
                self.timeline_controller,
                self.video_pane1,
                self.video_pane2,
            )

            self.assertEqual(control_panel.parent, self.parent)
            self.assertEqual(control_panel.playback_controller, self.playback_controller)
            self.assertEqual(control_panel.timeline_controller, self.timeline_controller)
            mock_panel_class.assert_called_once_with(self.parent)
            self.assertEqual(mock_button_class.call_count, 5)
            self.assertIsNotNone(control_panel.timeline_slider)
            self.assertIsNotNone(control_panel.sync_controls)
            self.assertIsNotNone(control_panel.zoom_controls)

    def test_play_button_triggers_playback_controller_play(self) -> None:
        """Test play button triggers PlaybackController.play()."""
        with patch("video_comparator.ui.controls.ControlPanel._create_layout"), patch(
            "video_comparator.ui.controls.wx.Panel"
        ), patch("video_comparator.ui.controls.wx.Button"), patch("video_comparator.ui.controls.TimelineSlider"), patch(
            "video_comparator.ui.controls.SyncControls"
        ), patch(
            "video_comparator.ui.controls.ZoomControls"
        ):
            control_panel = ControlPanel(
                self.parent,
                self.playback_controller,
                self.timeline_controller,
                self.video_pane1,
                self.video_pane2,
            )

            mock_event = MagicMock()
            control_panel._on_play(mock_event)

            self.assertEqual(self.playback_controller.state, PlaybackState.PLAYING)

    def test_pause_button_triggers_playback_controller_pause(self) -> None:
        """Test pause button triggers PlaybackController.pause()."""
        with patch("video_comparator.ui.controls.ControlPanel._create_layout"), patch(
            "video_comparator.ui.controls.wx.Panel"
        ), patch("video_comparator.ui.controls.wx.Button"), patch("video_comparator.ui.controls.TimelineSlider"), patch(
            "video_comparator.ui.controls.SyncControls"
        ), patch(
            "video_comparator.ui.controls.ZoomControls"
        ):
            control_panel = ControlPanel(
                self.parent,
                self.playback_controller,
                self.timeline_controller,
                self.video_pane1,
                self.video_pane2,
            )

            self.playback_controller.play()
            mock_event = MagicMock()
            control_panel._on_pause(mock_event)

            self.assertEqual(self.playback_controller.state, PlaybackState.PAUSED)

    def test_stop_button_triggers_playback_controller_stop(self) -> None:
        """Test stop button triggers PlaybackController.stop()."""
        with patch("video_comparator.ui.controls.ControlPanel._create_layout"), patch(
            "video_comparator.ui.controls.wx.Panel"
        ), patch("video_comparator.ui.controls.wx.Button"), patch(
            "video_comparator.ui.controls.TimelineSlider"
        ) as mock_timeline_slider_class, patch(
            "video_comparator.ui.controls.SyncControls"
        ), patch(
            "video_comparator.ui.controls.ZoomControls"
        ):
            mock_timeline_slider = MagicMock()
            mock_timeline_slider_class.return_value = mock_timeline_slider

            control_panel = ControlPanel(
                self.parent,
                self.playback_controller,
                self.timeline_controller,
                self.video_pane1,
                self.video_pane2,
            )

            self.playback_controller.play()
            mock_event = MagicMock()
            control_panel._on_stop(mock_event)

            self.assertEqual(self.playback_controller.state, PlaybackState.STOPPED)
            mock_timeline_slider.update_position.assert_called_once()

    def test_frame_step_forward_button_triggers_step_forward(self) -> None:
        """Test frame-step forward button triggers step_forward()."""
        with patch("video_comparator.ui.controls.ControlPanel._create_layout"), patch(
            "video_comparator.ui.controls.wx.Panel"
        ), patch("video_comparator.ui.controls.wx.Button"), patch(
            "video_comparator.ui.controls.TimelineSlider"
        ) as mock_timeline_slider_class, patch(
            "video_comparator.ui.controls.SyncControls"
        ), patch(
            "video_comparator.ui.controls.ZoomControls"
        ):
            mock_timeline_slider = MagicMock()
            mock_timeline_slider_class.return_value = mock_timeline_slider

            control_panel = ControlPanel(
                self.parent,
                self.playback_controller,
                self.timeline_controller,
                self.video_pane1,
                self.video_pane2,
            )

            initial_position = self.timeline_controller.current_position
            mock_event = MagicMock()
            control_panel._on_step_forward(mock_event)

            self.assertGreater(self.timeline_controller.current_position, initial_position)
            mock_timeline_slider.update_position.assert_called_once()

    def test_frame_step_backward_button_triggers_step_backward(self) -> None:
        """Test frame-step backward button triggers step_backward()."""
        with patch("video_comparator.ui.controls.ControlPanel._create_layout"), patch(
            "video_comparator.ui.controls.wx.Panel"
        ), patch("video_comparator.ui.controls.wx.Button"), patch(
            "video_comparator.ui.controls.TimelineSlider"
        ) as mock_timeline_slider_class, patch(
            "video_comparator.ui.controls.SyncControls"
        ), patch(
            "video_comparator.ui.controls.ZoomControls"
        ):
            mock_timeline_slider = MagicMock()
            mock_timeline_slider_class.return_value = mock_timeline_slider

            control_panel = ControlPanel(
                self.parent,
                self.playback_controller,
                self.timeline_controller,
                self.video_pane1,
                self.video_pane2,
            )

            self.timeline_controller.set_position(5.0)
            initial_position = self.timeline_controller.current_position
            mock_event = MagicMock()
            control_panel._on_step_backward(mock_event)

            self.assertLess(self.timeline_controller.current_position, initial_position)
            mock_timeline_slider.update_position.assert_called_once()

    def test_all_controls_are_properly_wired(self) -> None:
        """Test all controls are properly wired."""
        with patch("video_comparator.ui.controls.ControlPanel._create_layout"), patch(
            "video_comparator.ui.controls.wx.Panel"
        ) as mock_panel_class, patch("video_comparator.ui.controls.wx.Button") as mock_button_class, patch(
            "video_comparator.ui.controls.TimelineSlider"
        ), patch(
            "video_comparator.ui.controls.SyncControls"
        ), patch(
            "video_comparator.ui.controls.ZoomControls"
        ):
            mock_panel = MagicMock()
            mock_panel_class.return_value = mock_panel
            mock_button = MagicMock()
            mock_button_class.return_value = mock_button

            control_panel = ControlPanel(
                self.parent,
                self.playback_controller,
                self.timeline_controller,
                self.video_pane1,
                self.video_pane2,
            )

            self.assertEqual(mock_button.Bind.call_count, 5)

    def test_button_states_update_with_playback_state(self) -> None:
        """Test button states update with playback state."""
        with patch("video_comparator.ui.controls.ControlPanel._create_layout"), patch(
            "video_comparator.ui.controls.wx.Panel"
        ), patch("video_comparator.ui.controls.wx.Button") as mock_button_class, patch(
            "video_comparator.ui.controls.TimelineSlider"
        ), patch(
            "video_comparator.ui.controls.SyncControls"
        ), patch(
            "video_comparator.ui.controls.ZoomControls"
        ):
            mock_play_button = MagicMock()
            mock_pause_button = MagicMock()
            mock_stop_button = MagicMock()
            mock_button_class.side_effect = [
                mock_play_button,
                mock_pause_button,
                mock_stop_button,
                MagicMock(),
                MagicMock(),
            ]

            control_panel = ControlPanel(
                self.parent,
                self.playback_controller,
                self.timeline_controller,
                self.video_pane1,
                self.video_pane2,
            )
            control_panel.update_load_state(True, True)

            self.assertEqual(self.playback_controller.state, PlaybackState.STOPPED)
            control_panel._update_button_states()

            mock_play_button.Enable.assert_called_with(True)
            mock_pause_button.Enable.assert_called_with(False)
            mock_stop_button.Enable.assert_called_with(False)

            mock_play_button.reset_mock()
            mock_pause_button.reset_mock()
            mock_stop_button.reset_mock()

            self.playback_controller.play()
            control_panel._update_button_states()

            mock_play_button.Enable.assert_called_with(False)
            mock_pause_button.Enable.assert_called_with(True)
            mock_stop_button.Enable.assert_called_with(True)
