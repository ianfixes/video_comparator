"""Unit tests for LayoutManager class."""

import unittest
from unittest.mock import MagicMock, patch

import wx

from video_comparator.common.types import LayoutOrientation, ScalingMode
from video_comparator.render.scaling_calculator import ScalingCalculator
from video_comparator.render.video_pane import VideoPane
from video_comparator.ui.layout_manager import LayoutManager


class TestLayoutManager(unittest.TestCase):
    """Test cases for LayoutManager class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.parent = MagicMock(spec=wx.Window)
        self.calculator = ScalingCalculator()

        with patch("video_comparator.render.video_pane.wx.Panel.__init__", return_value=None), patch.object(
            VideoPane, "Bind", return_value=None
        ), patch.object(VideoPane, "GetSize", return_value=wx.Size(400, 300)), patch.object(
            VideoPane, "Refresh", return_value=None
        ), patch.object(
            VideoPane, "CaptureMouse", return_value=None
        ), patch.object(
            VideoPane, "ReleaseMouse", return_value=None
        ), patch.object(
            VideoPane, "HasCapture", return_value=False
        ):
            self.pane1 = VideoPane(self.parent, self.calculator)
            self.pane2 = VideoPane(self.parent, self.calculator)

        patch.object(self.pane1, "Refresh", return_value=None).start()
        patch.object(self.pane2, "Refresh", return_value=None).start()
        self.addCleanup(patch.stopall)

        self.layout_manager = LayoutManager(self.pane1, self.pane2)

    def test_initial_orientation_horizontal(self) -> None:
        """Test initial orientation is horizontal."""
        self.assertEqual(self.layout_manager.orientation, LayoutOrientation.HORIZONTAL)

    def test_initial_scaling_mode_independent(self) -> None:
        """Test initial scaling mode is independent."""
        self.assertEqual(self.layout_manager.scaling_mode, ScalingMode.INDEPENDENT)

    def test_toggle_orientation_horizontal_to_vertical(self) -> None:
        """Test orientation toggle horizontal → vertical."""
        self.assertEqual(self.layout_manager.orientation, LayoutOrientation.HORIZONTAL)

        new_orientation = self.layout_manager.toggle_orientation()

        self.assertEqual(new_orientation, LayoutOrientation.VERTICAL)
        self.assertEqual(self.layout_manager.orientation, LayoutOrientation.VERTICAL)

    def test_toggle_orientation_vertical_to_horizontal(self) -> None:
        """Test orientation toggle vertical → horizontal."""
        self.layout_manager.orientation = LayoutOrientation.VERTICAL

        new_orientation = self.layout_manager.toggle_orientation()

        self.assertEqual(new_orientation, LayoutOrientation.HORIZONTAL)
        self.assertEqual(self.layout_manager.orientation, LayoutOrientation.HORIZONTAL)

    def test_toggle_scaling_mode_independent_to_match_larger(self) -> None:
        """Test scaling mode toggle independent → match_larger."""
        self.assertEqual(self.layout_manager.scaling_mode, ScalingMode.INDEPENDENT)

        new_mode = self.layout_manager.toggle_scaling_mode()

        self.assertEqual(new_mode, ScalingMode.MATCH_LARGER)
        self.assertEqual(self.layout_manager.scaling_mode, ScalingMode.MATCH_LARGER)

    def test_toggle_scaling_mode_match_larger_to_independent(self) -> None:
        """Test scaling mode toggle match_larger → independent."""
        self.layout_manager.scaling_mode = ScalingMode.MATCH_LARGER

        new_mode = self.layout_manager.toggle_scaling_mode()

        self.assertEqual(new_mode, ScalingMode.INDEPENDENT)
        self.assertEqual(self.layout_manager.scaling_mode, ScalingMode.INDEPENDENT)

    def test_set_orientation(self) -> None:
        """Test set_orientation method."""
        self.layout_manager.set_orientation(LayoutOrientation.VERTICAL)

        self.assertEqual(self.layout_manager.orientation, LayoutOrientation.VERTICAL)

    def test_set_orientation_no_change(self) -> None:
        """Test set_orientation doesn't update if same value."""
        original_orientation = self.layout_manager.orientation

        with patch.object(self.layout_manager, "_update_layout") as mock_update:
            self.layout_manager.set_orientation(original_orientation)

            mock_update.assert_not_called()

    def test_set_scaling_mode(self) -> None:
        """Test set_scaling_mode method."""
        self.layout_manager.set_scaling_mode(ScalingMode.MATCH_LARGER)

        self.assertEqual(self.layout_manager.scaling_mode, ScalingMode.MATCH_LARGER)

    def test_set_scaling_mode_no_change(self) -> None:
        """Test set_scaling_mode doesn't update if same value."""
        original_mode = self.layout_manager.scaling_mode

        with patch.object(self.layout_manager, "_update_layout") as mock_update:
            self.layout_manager.set_scaling_mode(original_mode)

            mock_update.assert_not_called()

    def test_calculate_pane_sizes_horizontal_layout(self) -> None:
        """Test pane sizing for horizontal layout."""
        self.layout_manager.orientation = LayoutOrientation.HORIZONTAL

        pane1_size, pane2_size = self.layout_manager.calculate_pane_sizes(800, 600)

        self.assertEqual(pane1_size, (400, 600))
        self.assertEqual(pane2_size, (400, 600))

    def test_calculate_pane_sizes_vertical_layout(self) -> None:
        """Test pane sizing for vertical layout."""
        self.layout_manager.orientation = LayoutOrientation.VERTICAL

        pane1_size, pane2_size = self.layout_manager.calculate_pane_sizes(800, 600)

        self.assertEqual(pane1_size, (800, 300))
        self.assertEqual(pane2_size, (800, 300))

    def test_calculate_pane_sizes_invalid_dimensions(self) -> None:
        """Test calculate_pane_sizes raises error for invalid dimensions."""
        with self.assertRaises(ValueError):
            self.layout_manager.calculate_pane_sizes(0, 600)

        with self.assertRaises(ValueError):
            self.layout_manager.calculate_pane_sizes(800, 0)

        with self.assertRaises(ValueError):
            self.layout_manager.calculate_pane_sizes(-100, 600)

    def test_calculate_matched_bounding_box_pane1_larger(self) -> None:
        """Test matched bounding box calculation when pane1 is larger."""
        pane1_size = (400, 300)
        pane2_size = (300, 200)

        matched_size = self.layout_manager.calculate_matched_bounding_box(pane1_size, pane2_size)

        self.assertEqual(matched_size, pane1_size)

    def test_calculate_matched_bounding_box_pane2_larger(self) -> None:
        """Test matched bounding box calculation when pane2 is larger."""
        pane1_size = (300, 200)
        pane2_size = (400, 300)

        matched_size = self.layout_manager.calculate_matched_bounding_box(pane1_size, pane2_size)

        self.assertEqual(matched_size, pane2_size)

    def test_calculate_matched_bounding_box_equal_sizes(self) -> None:
        """Test matched bounding box calculation when panes are equal size."""
        pane1_size = (400, 300)
        pane2_size = (400, 300)

        matched_size = self.layout_manager.calculate_matched_bounding_box(pane1_size, pane2_size)

        self.assertEqual(matched_size, pane1_size)

    def test_calculate_matched_bounding_box_different_aspect_ratios(self) -> None:
        """Test matched bounding box with different aspect ratios."""
        pane1_size = (400, 200)
        pane2_size = (300, 300)

        matched_size = self.layout_manager.calculate_matched_bounding_box(pane1_size, pane2_size)

        self.assertEqual(matched_size, pane2_size)

    def test_update_layout_independent_mode(self) -> None:
        """Test update_layout in independent mode."""
        self.layout_manager.scaling_mode = ScalingMode.INDEPENDENT

        with patch.object(self.pane1, "set_scaling_mode") as mock_set1, patch.object(
            self.pane2, "set_scaling_mode"
        ) as mock_set2, patch.object(self.pane1, "set_display_size") as mock_display1, patch.object(
            self.pane2, "set_display_size"
        ) as mock_display2:
            self.layout_manager.update_layout(800, 600)

            mock_set1.assert_called_once_with(ScalingMode.INDEPENDENT)
            mock_set2.assert_called_once_with(ScalingMode.INDEPENDENT)
            mock_display1.assert_called_once_with((0, 0))
            mock_display2.assert_called_once_with((0, 0))

    def test_update_layout_match_larger_mode(self) -> None:
        """Test update_layout in match_larger mode."""
        self.layout_manager.scaling_mode = ScalingMode.MATCH_LARGER
        self.layout_manager.orientation = LayoutOrientation.HORIZONTAL

        with patch.object(self.pane1, "set_scaling_mode") as mock_set1, patch.object(
            self.pane2, "set_scaling_mode"
        ) as mock_set2, patch.object(self.pane1, "set_display_size") as mock_display1, patch.object(
            self.pane2, "set_display_size"
        ) as mock_display2:
            self.layout_manager.update_layout(800, 600)

            mock_set1.assert_called_once_with(ScalingMode.MATCH_LARGER)
            mock_set2.assert_called_once_with(ScalingMode.MATCH_LARGER)
            mock_display1.assert_called_once_with((400, 600))
            mock_display2.assert_called_once_with((400, 600))

    def test_update_layout_propagates_to_video_panes(self) -> None:
        """Test layout updates propagate to VideoPanes."""
        with patch.object(self.pane1, "set_scaling_mode") as mock_set1, patch.object(
            self.pane2, "set_scaling_mode"
        ) as mock_set2, patch.object(self.pane1, "set_display_size"), patch.object(self.pane2, "set_display_size"):
            self.layout_manager.update_layout(800, 600)

            mock_set1.assert_called_once()
            mock_set2.assert_called_once()

    def test_update_layout_invalid_dimensions(self) -> None:
        """Test update_layout raises error for invalid dimensions."""
        with self.assertRaises(ValueError):
            self.layout_manager.update_layout(0, 600)

        with self.assertRaises(ValueError):
            self.layout_manager.update_layout(800, 0)
