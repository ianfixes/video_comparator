"""Unit tests for UI controls."""

import unittest
from unittest.mock import MagicMock, patch

import wx

from video_comparator.media.video_metadata import VideoMetadata
from video_comparator.sync.timeline_controller import TimelineController
from video_comparator.ui.controls import TimelineSlider


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
