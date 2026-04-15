"""Unit tests for VideoPane class."""

import unittest
import warnings
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import wx

from video_comparator.common.types import ScalingMode
from video_comparator.media.video_metadata import VideoMetadata
from video_comparator.render.scaling_calculator import ScalingCalculator
from video_comparator.render.video_pane import FrameConversionError, RenderingError, VideoPane


@contextmanager
def create_video_pane(parent, calculator, metadata=None):
    """Context manager to create a VideoPane with proper mocking."""
    with patch("video_comparator.render.video_pane.wx.Panel.__init__", return_value=None), patch.object(
        VideoPane, "Bind", return_value=None
    ), patch.object(VideoPane, "GetSize", return_value=wx.Size(800, 600)), patch.object(
        VideoPane, "Refresh", return_value=None
    ), patch.object(
        VideoPane, "SetDropTarget", return_value=None
    ), patch.object(
        VideoPane, "CaptureMouse", return_value=None
    ), patch.object(
        VideoPane, "ReleaseMouse", return_value=None
    ), patch.object(
        VideoPane, "HasCapture", return_value=False
    ):
        pane = VideoPane(parent, calculator, metadata)
        yield pane


class TestVideoPane(unittest.TestCase):
    """Test cases for VideoPane class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.parent = MagicMock(spec=wx.Window)
        self.scaling_calculator = ScalingCalculator()
        self.metadata = VideoMetadata(
            file_path=Path("test_video.mp4"),
            duration=10.0,
            fps=30.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=300,
            time_base=1.0 / 90000.0,
        )
        self.panel_patcher = patch("video_comparator.render.video_pane.wx.Panel.__init__", return_value=None)
        self.bind_patcher = patch.object(VideoPane, "Bind", return_value=None)
        self.refresh_patcher = patch.object(VideoPane, "Refresh", return_value=None)
        self.setdrop_patcher = patch.object(VideoPane, "SetDropTarget", return_value=None)
        self.panel_patcher.start()
        self.bind_patcher.start()
        self.refresh_patcher.start()
        self.setdrop_patcher.start()
        self.pane = VideoPane(self.parent, self.scaling_calculator, self.metadata)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.setdrop_patcher.stop()
        self.refresh_patcher.stop()
        self.bind_patcher.stop()
        self.panel_patcher.stop()

    def test_initialization(self) -> None:
        """Test VideoPane initialization."""
        parent = MagicMock(spec=wx.Window)
        calculator = ScalingCalculator()
        with create_video_pane(parent, calculator) as pane:
            self.assertEqual(pane.scaling_calculator, calculator)
            self.assertIsNone(pane.metadata)
            self.assertIsNone(pane.current_frame)
            self.assertEqual(pane.zoom_level, 1.0)
            self.assertEqual(pane.pan_x, 0.0)
            self.assertEqual(pane.pan_y, 0.0)
            self.assertEqual(pane.scaling_mode, ScalingMode.INDEPENDENT)
            self.assertEqual(pane.display_size, (0, 0))

    def test_initialization_with_metadata(self) -> None:
        """Test VideoPane initialization with metadata."""
        parent = MagicMock(spec=wx.Window)
        calculator = ScalingCalculator()
        metadata = VideoMetadata(
            file_path=Path("test.mp4"),
            duration=5.0,
            fps=24.0,
            width=1280,
            height=720,
            pixel_format="yuv420p",
            total_frames=120,
            time_base=1.0 / 90000.0,
        )
        with create_video_pane(parent, calculator, metadata) as pane:
            self.assertEqual(pane.metadata, metadata)

    def test_frame_rendering_with_valid_frame(self) -> None:
        """Test frame rendering with valid frame."""
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.pane.set_frame(frame)

        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            with patch.object(self.pane, "_frame_to_bitmap") as mock_convert:
                mock_bitmap = MagicMock()
                mock_convert.return_value = mock_bitmap

                mock_dc = MagicMock()
                mock_dc.GetTextExtent.return_value = (100, 20)
                with patch("video_comparator.render.video_pane.wx.Colour") as mock_colour_class, patch(
                    "video_comparator.render.video_pane.wx.Font"
                ) as mock_font_class, patch("video_comparator.render.video_pane.wx.Brush") as mock_brush_class, patch(
                    "video_comparator.render.video_pane.wx.Bitmap"
                ) as mock_bitmap_class:
                    mock_colour_class.return_value = MagicMock()
                    mock_font_class.return_value = MagicMock()
                    mock_brush_class.return_value = MagicMock()
                    mock_bitmap_class.return_value = MagicMock()
                    mock_image = MagicMock()
                    mock_bitmap.ConvertToImage.return_value = mock_image
                    mock_image.Scale.return_value = MagicMock()

                    self.pane._render_frame(mock_dc)

                    mock_convert.assert_called_once()
                    mock_dc.Clear.assert_called_once()
                    mock_dc.DrawBitmap.assert_called()

    def test_frame_rendering_with_none_frame(self) -> None:
        """Test frame rendering with None frame (empty state)."""
        self.pane.set_frame(None)

        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            mock_dc = MagicMock()
            mock_dc.GetTextExtent.return_value = (100, 20)
            with patch("video_comparator.render.video_pane.wx.Colour") as mock_colour_class, patch(
                "video_comparator.render.video_pane.wx.Font"
            ) as mock_font_class, patch("video_comparator.render.video_pane.wx.Brush") as mock_brush_class:
                mock_colour_class.return_value = MagicMock()
                mock_font_class.return_value = MagicMock()
                mock_brush_class.return_value = MagicMock()

                self.pane._render_frame(mock_dc)

                mock_dc.Clear.assert_called_once()
                mock_dc.DrawText.assert_called()
                mock_dc.DrawBitmap.assert_not_called()

    def test_frame_rendering_without_metadata(self) -> None:
        """Test frame rendering without metadata shows empty state."""
        parent = MagicMock(spec=wx.Window)
        calculator = ScalingCalculator()
        with create_video_pane(parent, calculator, None) as pane:
            frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
            pane.set_frame(frame)

            mock_dc = MagicMock()
            mock_dc.GetTextExtent.return_value = (100, 20)
            with patch("video_comparator.render.video_pane.wx.Colour") as mock_colour_class, patch(
                "video_comparator.render.video_pane.wx.Font"
            ) as mock_font_class, patch("video_comparator.render.video_pane.wx.Brush") as mock_brush_class:
                mock_colour_class.return_value = MagicMock()
                mock_font_class.return_value = MagicMock()
                mock_brush_class.return_value = MagicMock()

                pane._render_frame(mock_dc)

                mock_dc.DrawText.assert_called()

    def test_zoom_transform_application(self) -> None:
        """Test zoom transform application."""
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.pane.set_frame(frame)
        self.pane.zoom_level = 2.0

        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            with patch.object(self.pane, "_frame_to_bitmap") as mock_convert:
                mock_bitmap = MagicMock()
                mock_image = MagicMock()
                mock_scaled_image = MagicMock()
                mock_image.Scale.return_value = mock_scaled_image
                mock_convert.return_value = mock_bitmap

                mock_dc = MagicMock()
                mock_dc.GetTextExtent.return_value = (100, 20)
                with patch("video_comparator.render.video_pane.wx.Colour") as mock_colour_class, patch(
                    "video_comparator.render.video_pane.wx.Font"
                ) as mock_font_class, patch("video_comparator.render.video_pane.wx.Brush") as mock_brush_class, patch(
                    "video_comparator.render.video_pane.wx.Bitmap"
                ) as mock_bitmap_class:
                    mock_colour_class.return_value = MagicMock()
                    mock_font_class.return_value = MagicMock()
                    mock_brush_class.return_value = MagicMock()

                    new_bitmap_mock = MagicMock()
                    new_bitmap_mock.ConvertToImage.return_value = mock_image

                    def bitmap_side_effect(arg):
                        if arg == mock_bitmap:
                            return new_bitmap_mock
                        return MagicMock()

                    mock_bitmap_class.side_effect = bitmap_side_effect

                    self.pane._render_frame(mock_dc)

                    new_bitmap_mock.ConvertToImage.assert_called()
                    mock_image.Scale.assert_called()

    def test_pan_transform_application(self) -> None:
        """Test pan transform application."""
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.pane.set_frame(frame)
        self.pane.pan_x = 50.0
        self.pane.pan_y = 30.0

        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            with patch.object(self.pane, "_frame_to_bitmap") as mock_convert:
                mock_bitmap = MagicMock()
                mock_image = MagicMock()
                mock_bitmap.ConvertToImage.return_value = mock_image
                mock_image.Scale.return_value = MagicMock()
                mock_convert.return_value = mock_bitmap

                mock_dc = MagicMock()
                mock_dc.GetTextExtent.return_value = (100, 20)
                with patch("video_comparator.render.video_pane.wx.Colour") as mock_colour_class, patch(
                    "video_comparator.render.video_pane.wx.Font"
                ) as mock_font_class, patch("video_comparator.render.video_pane.wx.Brush") as mock_brush_class, patch(
                    "video_comparator.render.video_pane.wx.Bitmap"
                ) as mock_bitmap_class:
                    mock_colour_class.return_value = MagicMock()
                    mock_font_class.return_value = MagicMock()
                    mock_brush_class.return_value = MagicMock()
                    mock_bitmap_class.return_value = MagicMock()

                    self.pane._render_frame(mock_dc)

                    call_args = mock_dc.DrawBitmap.call_args
                    self.assertIsNotNone(call_args)
                    draw_x, draw_y = call_args[0][1:3]
                    self.assertGreater(draw_x, 0)
                    self.assertGreater(draw_y, 0)

    def test_independent_scaling_mode_rendering(self) -> None:
        """Test independent scaling mode rendering."""
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.pane.set_frame(frame)
        self.pane.set_scaling_mode(ScalingMode.INDEPENDENT)

        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            with patch.object(self.pane.scaling_calculator, "calculate_scale") as mock_calc:
                mock_calc.return_value = (0.4, 0.4)

                with patch.object(self.pane, "_frame_to_bitmap") as mock_convert:
                    mock_bitmap = MagicMock()
                    mock_image = MagicMock()
                    mock_bitmap.ConvertToImage.return_value = mock_image
                    mock_image.Scale.return_value = MagicMock()
                    mock_convert.return_value = mock_bitmap

                    mock_dc = MagicMock()
                    mock_dc.GetTextExtent.return_value = (100, 20)
                    with patch("video_comparator.render.video_pane.wx.Colour") as mock_colour_class, patch(
                        "video_comparator.render.video_pane.wx.Font"
                    ) as mock_font_class, patch(
                        "video_comparator.render.video_pane.wx.Brush"
                    ) as mock_brush_class, patch(
                        "video_comparator.render.video_pane.wx.Bitmap"
                    ) as mock_bitmap_class:
                        mock_colour_class.return_value = MagicMock()
                        mock_font_class.return_value = MagicMock()
                        mock_brush_class.return_value = MagicMock()
                        mock_bitmap_class.return_value = MagicMock()

                        self.pane._render_frame(mock_dc)

                        mock_calc.assert_called_once_with((1920, 1080), (800, 600), ScalingMode.INDEPENDENT, None)

    def test_match_larger_scaling_mode_rendering(self) -> None:
        """Test match_larger scaling mode rendering."""
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.pane.set_frame(frame)
        self.pane.set_scaling_mode(ScalingMode.MATCH_LARGER)
        self.pane.set_display_size((2560, 1440))

        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            with patch.object(self.pane.scaling_calculator, "calculate_scale") as mock_calc:
                mock_calc.return_value = (1.33, 1.33)

                with patch.object(self.pane, "_frame_to_bitmap") as mock_convert:
                    mock_bitmap = MagicMock()
                    mock_image = MagicMock()
                    mock_bitmap.ConvertToImage.return_value = mock_image
                    mock_image.Scale.return_value = MagicMock()
                    mock_convert.return_value = mock_bitmap

                    mock_dc = MagicMock()
                    mock_dc.GetTextExtent.return_value = (100, 20)
                    with patch("video_comparator.render.video_pane.wx.Colour") as mock_colour_class, patch(
                        "video_comparator.render.video_pane.wx.Font"
                    ) as mock_font_class, patch(
                        "video_comparator.render.video_pane.wx.Brush"
                    ) as mock_brush_class, patch(
                        "video_comparator.render.video_pane.wx.Bitmap"
                    ) as mock_bitmap_class:
                        mock_colour_class.return_value = MagicMock()
                        mock_font_class.return_value = MagicMock()
                        mock_brush_class.return_value = MagicMock()
                        mock_bitmap_class.return_value = MagicMock()

                        self.pane._render_frame(mock_dc)

                        mock_calc.assert_called_once_with(
                            (1920, 1080), (800, 600), ScalingMode.MATCH_LARGER, (2560, 1440)
                        )

    def test_overlay_text_rendering(self) -> None:
        """Test overlay text rendering."""
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.pane.set_frame(frame)
        self.pane.set_playback_info(5.5, 165)

        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            with patch.object(self.pane, "_frame_to_bitmap") as mock_convert:
                mock_bitmap = MagicMock()
                mock_image = MagicMock()
                mock_bitmap.ConvertToImage.return_value = mock_image
                mock_image.Scale.return_value = MagicMock()
                mock_convert.return_value = mock_bitmap

                mock_dc = MagicMock()
                mock_dc.GetTextExtent.return_value = (100, 20)
                with patch("video_comparator.render.video_pane.wx.Colour") as mock_colour_class, patch(
                    "video_comparator.render.video_pane.wx.Font"
                ) as mock_font_class, patch("video_comparator.render.video_pane.wx.Brush") as mock_brush_class, patch(
                    "video_comparator.render.video_pane.wx.Bitmap"
                ) as mock_bitmap_class:
                    mock_colour_class.return_value = MagicMock()
                    mock_font_class.return_value = MagicMock()
                    mock_brush_class.return_value = MagicMock()
                    mock_bitmap_class.return_value = MagicMock()

                    self.pane._render_frame(mock_dc)

                    self.assertGreater(mock_dc.DrawText.call_count, 0)
                    draw_text_calls = [str(call) for call in mock_dc.DrawText.call_args_list]
                    self.assertTrue(any("1920x1080" in str(call) for call in draw_text_calls))
                    self.assertTrue(any("5.5" in str(call) for call in draw_text_calls))
                    self.assertTrue(any("165" in str(call) for call in draw_text_calls))

    def test_mouse_drag_pan_interaction(self) -> None:
        """Test mouse drag pan interaction."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=DeprecationWarning)
            mock_event = MagicMock(spec=wx.MouseEvent)
        mock_event.Dragging.return_value = True
        mock_event.GetPosition.return_value = wx.Point(100, 50)
        mock_event.shiftDown.return_value = False

        self.pane.drag_start_pos = (50, 25)
        self.pane.is_dragging = True
        self.pane.pan_x = 0.0
        self.pane.pan_y = 0.0
        self.pane.zoom_level = 1.0

        with patch.object(self.pane, "Refresh") as mock_refresh:
            self.pane._on_motion(mock_event)

            self.assertEqual(self.pane.pan_x, 50.0)
            self.assertEqual(self.pane.pan_y, 25.0)
            mock_refresh.assert_called_once()

    def test_mouse_wheel_zoom_in_out(self) -> None:
        """Test mouse wheel zoom in/out."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=DeprecationWarning)
            mock_event = MagicMock(spec=wx.MouseEvent)
        mock_event.GetWheelRotation.return_value = 120
        mock_event.GetPosition.return_value = wx.Point(400, 300)

        self.pane.zoom_level = 1.0
        self.pane.pan_x = 0.0
        self.pane.pan_y = 0.0

        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            with patch.object(self.pane, "Refresh") as mock_refresh:
                self.pane._on_mouse_wheel(mock_event)

                self.assertGreater(self.pane.zoom_level, 1.0)
                mock_refresh.assert_called_once()

        mock_event.GetWheelRotation.return_value = -120
        self.pane.zoom_level = 2.0

        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            with patch.object(self.pane, "Refresh") as mock_refresh:
                self.pane._on_mouse_wheel(mock_event)

                self.assertLess(self.pane.zoom_level, 2.0)
                mock_refresh.assert_called_once()

    def test_zoom_change_callback_invoked_on_mouse_wheel(self) -> None:
        """Mouse wheel zoom notifies zoom-change callback for UI label refresh."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=DeprecationWarning)
            mock_event = MagicMock(spec=wx.MouseEvent)
        mock_event.GetWheelRotation.return_value = 120
        mock_event.GetPosition.return_value = wx.Point(400, 300)
        on_zoom_changed = MagicMock()
        self.pane.set_on_zoom_changed(on_zoom_changed)

        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            with patch.object(self.pane, "Refresh"):
                self.pane._on_mouse_wheel(mock_event)

        on_zoom_changed.assert_called_once()

    def test_zoom_anchor_video_center_preserves_pan(self) -> None:
        """Button-style zoom about the video center should not drift pan."""
        self.pane.pan_x = 12.5
        self.pane.pan_y = -7.25
        self.pane.zoom_level = 1.5
        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            self.pane.zoom_at_video_center(VideoPane.ZOOM_STEP_FACTOR)
        self.assertAlmostEqual(self.pane.pan_x, 12.5, places=5)
        self.assertAlmostEqual(self.pane.pan_y, -7.25, places=5)

    def test_zoom_anchor_wheel_preserves_video_sample_under_cursor(self) -> None:
        """Wheel zoom keeps the video-space sample under the anchor fixed."""
        calc = self.scaling_calculator
        vw, vh = 1920, 1080
        pw, ph = 800, 600
        bs = calc.calculate_scale((vw, vh), (pw, ph), ScalingMode.INDEPENDENT)[0]
        self.pane.pan_x = 11.0
        self.pane.pan_y = -22.0
        self.pane.zoom_level = 1.0
        anchor_x = 150.0
        anchor_y = 275.0
        z_old = self.pane.zoom_level
        sw0 = vw * bs * z_old
        sh0 = vh * bs * z_old
        dx0 = (pw - sw0) / 2.0 + self.pane.pan_x
        dy0 = (ph - sh0) / 2.0 + self.pane.pan_y
        sx = (anchor_x - dx0) / (bs * z_old)
        sy = (anchor_y - dy0) / (bs * z_old)
        with patch.object(self.pane, "GetSize", return_value=wx.Size(pw, ph)):
            self.pane._zoom_at_point((anchor_x, anchor_y), VideoPane.ZOOM_STEP_FACTOR)
        z1 = self.pane.zoom_level
        sw1 = vw * bs * z1
        sh1 = vh * bs * z1
        dx1 = (pw - sw1) / 2.0 + self.pane.pan_x
        dy1 = (ph - sh1) / 2.0 + self.pane.pan_y
        self.assertAlmostEqual((anchor_x - dx1) / (bs * z1), sx, places=5)
        self.assertAlmostEqual((anchor_y - dy1) / (bs * z1), sy, places=5)

    def test_shift_drag_rectangle_selection_and_zoom_to_region(self) -> None:
        """Test Shift-drag rectangle selection and zoom to region."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=DeprecationWarning)
            mock_event = MagicMock(spec=wx.MouseEvent)
        mock_event.Dragging.return_value = True
        mock_event.GetPosition.return_value = wx.Point(200, 150)
        mock_event.shiftDown.return_value = True

        self.pane.drag_start_pos = (100, 50)
        self.pane.is_shift_dragging = True

        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            with patch.object(self.pane, "Refresh") as mock_refresh:
                self.pane._on_motion(mock_event)

                self.assertIsNotNone(self.pane.selection_rect)
                mock_refresh.assert_called_once()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=DeprecationWarning)
            mock_event_up = MagicMock(spec=wx.MouseEvent)
        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            with patch.object(self.pane, "Refresh") as mock_refresh:
                self.pane._zoom_to_selection_rect()

                self.assertGreater(self.pane.zoom_level, 0.0)
                mock_refresh.assert_called_once()

    def test_zoom_state_persistence_after_seek(self) -> None:
        """Test zoom state persistence after seek."""
        self.pane.zoom_level = 2.5
        self.pane.pan_x = 100.0
        self.pane.pan_y = 50.0

        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.pane.set_frame(frame)

        self.assertEqual(self.pane.zoom_level, 2.5)
        self.assertEqual(self.pane.pan_x, 100.0)
        self.assertEqual(self.pane.pan_y, 50.0)

    def test_zoom_state_persistence_after_frame_step(self) -> None:
        """Test zoom state persistence after frame step."""
        self.pane.zoom_level = 1.5
        self.pane.pan_x = 25.0
        self.pane.pan_y = 15.0

        frame1 = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.pane.set_frame(frame1)
        self.pane.set_playback_info(1.0, 30)

        frame2 = np.ones((1080, 1920, 3), dtype=np.uint8) * 128
        self.pane.set_frame(frame2)
        self.pane.set_playback_info(1.033, 31)

        self.assertEqual(self.pane.zoom_level, 1.5)
        self.assertEqual(self.pane.pan_x, 25.0)
        self.assertEqual(self.pane.pan_y, 15.0)

    def test_coordinate_transformations_screen_to_video_space(self) -> None:
        """Test coordinate transformations (screen to video space)."""
        self.pane.zoom_level = 2.0
        self.pane.pan_x = 50.0
        self.pane.pan_y = 30.0

        display_point = (400, 300)
        scale = (0.5, 0.5)
        pan_offset = (self.pane.pan_x, self.pane.pan_y)

        video_point = self.pane.scaling_calculator.display_to_video(display_point, scale, pan_offset)

        self.assertIsInstance(video_point, tuple)
        self.assertEqual(len(video_point), 2)

    def test_edge_case_very_large_zoom(self) -> None:
        """Test edge case: very large zoom."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=DeprecationWarning)
            mock_event = MagicMock(spec=wx.MouseEvent)
        mock_event.GetWheelRotation.return_value = 10000
        mock_event.GetPosition.return_value = wx.Point(400, 300)

        self.pane.zoom_level = 1.0

        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            with patch.object(self.pane, "Refresh"):
                for _ in range(100):
                    self.pane._on_mouse_wheel(mock_event)

                self.assertLessEqual(self.pane.zoom_level, 10.0)

    def test_edge_case_extreme_pan_positions(self) -> None:
        """Test edge case: extreme pan positions."""
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.pane.set_frame(frame)
        self.pane.pan_x = 10000.0
        self.pane.pan_y = -5000.0

        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            with patch.object(self.pane, "_frame_to_bitmap") as mock_convert:
                mock_bitmap = MagicMock()
                mock_image = MagicMock()
                mock_bitmap.ConvertToImage.return_value = mock_image
                mock_image.Scale.return_value = MagicMock()
                mock_convert.return_value = mock_bitmap

                mock_dc = MagicMock()
                mock_dc.GetTextExtent.return_value = (100, 20)
                with patch("video_comparator.render.video_pane.wx.Colour") as mock_colour_class, patch(
                    "video_comparator.render.video_pane.wx.Font"
                ) as mock_font_class, patch("video_comparator.render.video_pane.wx.Brush") as mock_brush_class, patch(
                    "video_comparator.render.video_pane.wx.Bitmap"
                ) as mock_bitmap_class:
                    mock_colour_class.return_value = MagicMock()
                    mock_font_class.return_value = MagicMock()
                    mock_brush_class.return_value = MagicMock()
                    mock_bitmap_class.return_value = MagicMock()

                    self.pane._render_frame(mock_dc)

                    mock_dc.DrawBitmap.assert_called()

    def test_set_frame(self) -> None:
        """Test set_frame method."""
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.pane.set_frame(frame)

        self.assertIsNotNone(self.pane.current_frame)
        if self.pane.current_frame is not None:
            np.testing.assert_array_equal(self.pane.current_frame, frame)

    def test_set_frame_none(self) -> None:
        """Test set_frame with None."""
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.pane.set_frame(frame)
        self.pane.set_frame(None)

        self.assertIsNone(self.pane.current_frame)

    def test_set_metadata(self) -> None:
        """Test set_metadata method."""
        new_metadata = VideoMetadata(
            file_path=Path("new_video.mp4"),
            duration=20.0,
            fps=25.0,
            width=1280,
            height=720,
            pixel_format="yuv420p",
            total_frames=500,
            time_base=1.0 / 90000.0,
        )
        self.pane.set_metadata(new_metadata)

        self.assertEqual(self.pane.metadata, new_metadata)

    def test_set_scaling_mode(self) -> None:
        """Test set_scaling_mode method."""
        self.pane.set_scaling_mode(ScalingMode.MATCH_LARGER)
        self.assertEqual(self.pane.scaling_mode, ScalingMode.MATCH_LARGER)

        self.pane.set_scaling_mode(ScalingMode.INDEPENDENT)
        self.assertEqual(self.pane.scaling_mode, ScalingMode.INDEPENDENT)

    def test_set_display_size(self) -> None:
        """Test set_display_size method."""
        self.pane.set_display_size((2560, 1440))
        self.assertEqual(self.pane.display_size, (2560, 1440))

    def test_set_playback_info(self) -> None:
        """Test set_playback_info method."""
        self.pane.set_playback_info(10.5, 315)
        self.assertEqual(self.pane.current_time, 10.5)
        self.assertEqual(self.pane.current_frame_index, 315)

    def test_reset_zoom_pan(self) -> None:
        """Test reset_zoom_pan method."""
        self.pane.zoom_level = 3.0
        self.pane.pan_x = 100.0
        self.pane.pan_y = 50.0

        self.pane.reset_zoom_pan()

        self.assertEqual(self.pane.zoom_level, 1.0)
        self.assertEqual(self.pane.pan_x, 0.0)
        self.assertEqual(self.pane.pan_y, 0.0)

    def test_get_zoom_level(self) -> None:
        """Test get_zoom_level method."""
        self.pane.zoom_level = 2.5
        self.assertEqual(self.pane.get_zoom_level(), 2.5)

    def test_get_pan_position(self) -> None:
        """Test get_pan_position method."""
        self.pane.pan_x = 75.0
        self.pane.pan_y = 25.0
        pan_pos = self.pane.get_pan_position()

        self.assertEqual(pan_pos, (75.0, 25.0))

    def test_frame_to_bitmap_conversion(self) -> None:
        """Test frame to bitmap conversion."""
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        with patch("video_comparator.render.video_pane.wx.Image") as mock_image_class:
            mock_image = MagicMock()
            mock_image_class.return_value = mock_image
            mock_bitmap = MagicMock(spec=wx.Bitmap)
            with patch("video_comparator.render.video_pane.wx.Bitmap", return_value=mock_bitmap):
                bitmap = self.pane._frame_to_bitmap(frame)

                self.assertIsNotNone(bitmap)
                mock_image_class.assert_called_once_with(200, 100)
                mock_image.SetData.assert_called_once()

    def test_frame_to_bitmap_conversion_invalid_channels(self) -> None:
        """Test frame to bitmap conversion with invalid channel count."""
        frame = np.zeros((100, 200, 4), dtype=np.uint8)

        with self.assertRaises(FrameConversionError):
            self.pane._frame_to_bitmap(frame)

    def test_frame_to_bitmap_conversion_non_uint8(self) -> None:
        """Test frame to bitmap conversion with non-uint8 dtype."""
        frame = np.zeros((100, 200, 3), dtype=np.float32)
        with patch("video_comparator.render.video_pane.wx.Image") as mock_image_class:
            mock_image = MagicMock()
            mock_image_class.return_value = mock_image
            mock_bitmap = MagicMock(spec=wx.Bitmap)
            with patch("video_comparator.render.video_pane.wx.Bitmap", return_value=mock_bitmap):
                bitmap = self.pane._frame_to_bitmap(frame)

                self.assertIsNotNone(bitmap)

    def test_draw_selection_rect(self) -> None:
        """Test drawing selection rectangle."""
        self.pane.selection_rect = (100, 50, 200, 150)

        mock_dc = MagicMock()
        with patch("video_comparator.render.video_pane.wx.Pen") as mock_pen_class, patch(
            "video_comparator.render.video_pane.wx.Colour"
        ) as mock_colour_class, patch("video_comparator.render.video_pane.wx.Brush") as mock_brush_class:
            mock_pen = MagicMock()
            mock_pen_class.return_value = mock_pen
            mock_colour_class.return_value = MagicMock()
            mock_brush_class.return_value = MagicMock()

            self.pane._draw_selection_rect(mock_dc)

            mock_dc.SetPen.assert_called_once()
            mock_dc.SetBrush.assert_called_once()
            mock_dc.DrawRectangle.assert_called_once_with(100, 50, 200, 150)

    def test_draw_selection_rect_none(self) -> None:
        """Test drawing selection rectangle when None."""
        self.pane.selection_rect = None

        mock_dc = MagicMock(spec=wx.PaintDC)
        self.pane._draw_selection_rect(mock_dc)

        mock_dc.DrawRectangle.assert_not_called()

    def test_on_paint_calls_render_frame(self) -> None:
        """Test that OnPaint calls _render_frame."""
        mock_event = MagicMock(spec=wx.PaintEvent)

        with patch("video_comparator.render.video_pane.wx.PaintDC") as mock_dc_class:
            mock_dc = MagicMock()
            mock_dc_class.return_value = mock_dc

            with patch.object(self.pane, "_render_frame") as mock_render:
                self.pane._on_paint(mock_event)

                mock_render.assert_called_once_with(mock_dc)

    def test_on_paint_draws_selection_rect_when_shift_dragging(self) -> None:
        """Test that OnPaint draws selection rectangle when shift-dragging."""
        mock_event = MagicMock(spec=wx.PaintEvent)
        self.pane.is_shift_dragging = True
        self.pane.selection_rect = (100, 50, 200, 150)

        with patch("video_comparator.render.video_pane.wx.PaintDC") as mock_dc_class:
            mock_dc = MagicMock()
            mock_dc_class.return_value = mock_dc

            with patch.object(self.pane, "_render_frame"):
                with patch.object(self.pane, "_draw_selection_rect") as mock_draw:
                    self.pane._on_paint(mock_event)

                    mock_draw.assert_called_once_with(mock_dc)

    def test_rendering_error_on_exception(self) -> None:
        """Test that RenderingError is raised on rendering exception."""
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.pane.set_frame(frame)

        with patch.object(self.pane, "GetSize", return_value=wx.Size(800, 600)):
            with patch.object(self.pane, "_frame_to_bitmap", side_effect=Exception("Test error")):
                mock_dc = MagicMock()
                with patch("video_comparator.render.video_pane.wx.Colour") as mock_colour_class, patch(
                    "video_comparator.render.video_pane.wx.Brush"
                ) as mock_brush_class:
                    mock_colour_class.return_value = MagicMock()
                    mock_brush_class.return_value = MagicMock()

                    with self.assertRaises(RenderingError):
                        self.pane._render_frame(mock_dc)

    def test_deliver_dropped_files_invokes_callback(self) -> None:
        """Dropped paths are forwarded to the callback (same entry point as menu open wiring)."""
        received: list[str] = []
        self.pane.set_on_files_dropped(lambda paths: received.extend(paths))
        ok = self.pane._deliver_dropped_files(["/a/b.mp4"])
        self.assertTrue(ok)
        self.assertEqual(received, ["/a/b.mp4"])

    def test_deliver_dropped_files_without_callback_returns_false(self) -> None:
        """Without a handler, drops are not consumed."""
        self.pane.set_on_files_dropped(None)
        ok = self.pane._deliver_dropped_files(["/a.mp4"])
        self.assertFalse(ok)

    def test_deliver_dropped_files_empty_returns_false(self) -> None:
        """Empty filename list does not invoke the callback."""
        received: list[str] = []
        self.pane.set_on_files_dropped(lambda paths: received.extend(paths))
        ok = self.pane._deliver_dropped_files([])
        self.assertFalse(ok)
        self.assertEqual(received, [])
