"""Unit tests for ScalingCalculator class."""

import unittest

from video_comparator.common.types import ScalingMode
from video_comparator.render.scaling_calculator import ScalingCalculator


class TestScalingCalculator(unittest.TestCase):
    """Test cases for ScalingCalculator class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.calculator = ScalingCalculator()

    def test_independent_scaling_landscape_video_fits_width(self) -> None:
        """Test independent mode: landscape video fits to display width."""
        video_size = (1920, 1080)
        display_size = (800, 600)
        scale_x, scale_y = self.calculator.calculate_scale(video_size, display_size, ScalingMode.INDEPENDENT)
        self.assertEqual(scale_x, scale_y)
        self.assertAlmostEqual(scale_x, 800 / 1920, places=5)
        scaled_width = 1920 * scale_x
        scaled_height = 1080 * scale_y
        self.assertLessEqual(scaled_width, 800)
        self.assertLessEqual(scaled_height, 600)

    def test_independent_scaling_portrait_video_fits_height(self) -> None:
        """Test independent mode: portrait video fits to display height."""
        video_size = (1080, 1920)
        display_size = (800, 600)
        scale_x, scale_y = self.calculator.calculate_scale(video_size, display_size, ScalingMode.INDEPENDENT)
        self.assertEqual(scale_x, scale_y)
        self.assertAlmostEqual(scale_x, 600 / 1920, places=5)
        scaled_width = 1080 * scale_x
        scaled_height = 1920 * scale_y
        self.assertLessEqual(scaled_width, 800)
        self.assertLessEqual(scaled_height, 600)

    def test_independent_scaling_square_video(self) -> None:
        """Test independent mode: square video fits to smaller display dimension."""
        video_size = (1000, 1000)
        display_size = (800, 600)
        scale_x, scale_y = self.calculator.calculate_scale(video_size, display_size, ScalingMode.INDEPENDENT)
        self.assertEqual(scale_x, scale_y)
        self.assertAlmostEqual(scale_x, 600 / 1000, places=5)

    def test_independent_scaling_identical_sizes(self) -> None:
        """Test independent mode: video and display have identical sizes."""
        video_size = (1920, 1080)
        display_size = (1920, 1080)
        scale_x, scale_y = self.calculator.calculate_scale(video_size, display_size, ScalingMode.INDEPENDENT)
        self.assertEqual(scale_x, 1.0)
        self.assertEqual(scale_y, 1.0)

    def test_independent_scaling_video_smaller_than_display(self) -> None:
        """Test independent mode: video is smaller than display."""
        video_size = (640, 480)
        display_size = (1920, 1080)
        scale_x, scale_y = self.calculator.calculate_scale(video_size, display_size, ScalingMode.INDEPENDENT)
        self.assertEqual(scale_x, scale_y)
        self.assertAlmostEqual(scale_x, 1080 / 480, places=5)

    def test_independent_scaling_extreme_aspect_ratio_wide(self) -> None:
        """Test independent mode: very wide video (ultrawide)."""
        video_size = (3840, 1080)
        display_size = (1920, 1080)
        scale_x, scale_y = self.calculator.calculate_scale(video_size, display_size, ScalingMode.INDEPENDENT)
        self.assertEqual(scale_x, scale_y)
        self.assertAlmostEqual(scale_x, 1920 / 3840, places=5)

    def test_independent_scaling_extreme_aspect_ratio_tall(self) -> None:
        """Test independent mode: very tall video."""
        video_size = (1080, 3840)
        display_size = (1920, 1080)
        scale_x, scale_y = self.calculator.calculate_scale(video_size, display_size, ScalingMode.INDEPENDENT)
        self.assertEqual(scale_x, scale_y)
        self.assertAlmostEqual(scale_x, 1080 / 3840, places=5)

    def test_match_larger_scaling_matches_reference_width(self) -> None:
        """Test match_larger mode: video matches reference width."""
        video_size = (1920, 1080)
        reference_size = (800, 600)
        display_size = (1000, 1000)
        scale_x, scale_y = self.calculator.calculate_scale(
            video_size, display_size, ScalingMode.MATCH_LARGER, reference_size
        )
        self.assertEqual(scale_x, scale_y)
        self.assertAlmostEqual(scale_x, 800 / 1920, places=5)

    def test_match_larger_scaling_matches_reference_height(self) -> None:
        """Test match_larger mode: video matches reference height."""
        video_size = (1080, 1920)
        reference_size = (600, 800)
        display_size = (1000, 1000)
        scale_x, scale_y = self.calculator.calculate_scale(
            video_size, display_size, ScalingMode.MATCH_LARGER, reference_size
        )
        self.assertEqual(scale_x, scale_y)
        self.assertAlmostEqual(scale_x, 800 / 1920, places=5)

    def test_match_larger_scaling_square_video(self) -> None:
        """Test match_larger mode: square video matches square reference."""
        video_size = (1000, 1000)
        reference_size = (500, 500)
        display_size = (1000, 1000)
        scale_x, scale_y = self.calculator.calculate_scale(
            video_size, display_size, ScalingMode.MATCH_LARGER, reference_size
        )
        self.assertEqual(scale_x, scale_y)
        self.assertAlmostEqual(scale_x, 0.5, places=5)

    def test_match_larger_scaling_identical_to_reference(self) -> None:
        """Test match_larger mode: video size matches reference size."""
        video_size = (1920, 1080)
        reference_size = (1920, 1080)
        display_size = (2000, 2000)
        scale_x, scale_y = self.calculator.calculate_scale(
            video_size, display_size, ScalingMode.MATCH_LARGER, reference_size
        )
        self.assertEqual(scale_x, 1.0)
        self.assertEqual(scale_y, 1.0)

    def test_aspect_ratio_preserved_independent(self) -> None:
        """Test that aspect ratio is preserved in independent mode."""
        video_size = (1920, 1080)
        display_size = (800, 600)
        scale_x, scale_y = self.calculator.calculate_scale(video_size, display_size, ScalingMode.INDEPENDENT)
        self.assertEqual(scale_x, scale_y)
        scaled_width = 1920 * scale_x
        scaled_height = 1080 * scale_y
        aspect_ratio = scaled_width / scaled_height
        expected_aspect = 1920 / 1080
        self.assertAlmostEqual(aspect_ratio, expected_aspect, places=5)

    def test_aspect_ratio_preserved_match_larger(self) -> None:
        """Test that aspect ratio is preserved in match_larger mode."""
        video_size = (1920, 1080)
        reference_size = (800, 600)
        display_size = (1000, 1000)
        scale_x, scale_y = self.calculator.calculate_scale(
            video_size, display_size, ScalingMode.MATCH_LARGER, reference_size
        )
        self.assertEqual(scale_x, scale_y)
        scaled_width = 1920 * scale_x
        scaled_height = 1080 * scale_y
        aspect_ratio = scaled_width / scaled_height
        expected_aspect = 1920 / 1080
        self.assertAlmostEqual(aspect_ratio, expected_aspect, places=5)

    def test_error_invalid_video_size_zero_width(self) -> None:
        """Test error handling: video width is zero."""
        with self.assertRaises(ValueError) as context:
            self.calculator.calculate_scale((0, 1080), (800, 600), ScalingMode.INDEPENDENT)
        self.assertIn("video_size", str(context.exception))

    def test_error_invalid_video_size_zero_height(self) -> None:
        """Test error handling: video height is zero."""
        with self.assertRaises(ValueError) as context:
            self.calculator.calculate_scale((1920, 0), (800, 600), ScalingMode.INDEPENDENT)
        self.assertIn("video_size", str(context.exception))

    def test_error_invalid_display_size_zero_width(self) -> None:
        """Test error handling: display width is zero."""
        with self.assertRaises(ValueError) as context:
            self.calculator.calculate_scale((1920, 1080), (0, 600), ScalingMode.INDEPENDENT)
        self.assertIn("display_size", str(context.exception))

    def test_error_invalid_display_size_zero_height(self) -> None:
        """Test error handling: display height is zero."""
        with self.assertRaises(ValueError) as context:
            self.calculator.calculate_scale((1920, 1080), (800, 0), ScalingMode.INDEPENDENT)
        self.assertIn("display_size", str(context.exception))

    def test_error_match_larger_missing_reference(self) -> None:
        """Test error handling: match_larger mode without reference_size."""
        with self.assertRaises(ValueError) as context:
            self.calculator.calculate_scale((1920, 1080), (800, 600), ScalingMode.MATCH_LARGER)
        self.assertIn("reference_size", str(context.exception))

    def test_error_match_larger_invalid_reference_zero_width(self) -> None:
        """Test error handling: reference_size has zero width."""
        with self.assertRaises(ValueError) as context:
            self.calculator.calculate_scale(
                (1920, 1080),
                (800, 600),
                ScalingMode.MATCH_LARGER,
                reference_size=(0, 600),
            )
        self.assertIn("reference_size", str(context.exception))

    def test_error_match_larger_invalid_reference_zero_height(self) -> None:
        """Test error handling: reference_size has zero height."""
        with self.assertRaises(ValueError) as context:
            self.calculator.calculate_scale(
                (1920, 1080),
                (800, 600),
                ScalingMode.MATCH_LARGER,
                reference_size=(800, 0),
            )
        self.assertIn("reference_size", str(context.exception))

    def test_video_to_display_no_pan(self) -> None:
        """Test coordinate transformation: video to display without pan."""
        video_point = (100.0, 200.0)
        scale = (2.0, 2.0)
        display_point = self.calculator.video_to_display(video_point, scale)
        self.assertEqual(display_point, (200.0, 400.0))

    def test_video_to_display_with_pan(self) -> None:
        """Test coordinate transformation: video to display with pan offset."""
        video_point = (100.0, 200.0)
        scale = (2.0, 2.0)
        pan_offset = (50.0, 75.0)
        display_point = self.calculator.video_to_display(video_point, scale, pan_offset)
        self.assertEqual(display_point, (250.0, 475.0))

    def test_video_to_display_different_scales(self) -> None:
        """Test coordinate transformation: different x and y scales."""
        video_point = (100.0, 200.0)
        scale = (2.0, 3.0)
        display_point = self.calculator.video_to_display(video_point, scale)
        self.assertEqual(display_point, (200.0, 600.0))

    def test_display_to_video_no_pan(self) -> None:
        """Test coordinate transformation: display to video without pan."""
        display_point = (200.0, 400.0)
        scale = (2.0, 2.0)
        video_point = self.calculator.display_to_video(display_point, scale)
        self.assertEqual(video_point, (100.0, 200.0))

    def test_display_to_video_with_pan(self) -> None:
        """Test coordinate transformation: display to video with pan offset."""
        display_point = (250.0, 475.0)
        scale = (2.0, 2.0)
        pan_offset = (50.0, 75.0)
        video_point = self.calculator.display_to_video(display_point, scale, pan_offset)
        self.assertEqual(video_point, (100.0, 200.0))

    def test_display_to_video_different_scales(self) -> None:
        """Test coordinate transformation: different x and y scales."""
        display_point = (200.0, 600.0)
        scale = (2.0, 3.0)
        video_point = self.calculator.display_to_video(display_point, scale)
        self.assertEqual(video_point, (100.0, 200.0))

    def test_coordinate_round_trip(self) -> None:
        """Test coordinate transformation round trip: video -> display -> video."""
        original_point = (123.45, 678.90)
        scale = (1.5, 2.5)
        pan_offset = (10.0, 20.0)
        display_point = self.calculator.video_to_display(original_point, scale, pan_offset)
        round_trip_point = self.calculator.display_to_video(display_point, scale, pan_offset)
        self.assertAlmostEqual(round_trip_point[0], original_point[0], places=5)
        self.assertAlmostEqual(round_trip_point[1], original_point[1], places=5)

    def test_coordinate_round_trip_reverse(self) -> None:
        """Test coordinate transformation round trip: display -> video -> display."""
        original_point = (123.45, 678.90)
        scale = (1.5, 2.5)
        pan_offset = (10.0, 20.0)
        video_point = self.calculator.display_to_video(original_point, scale, pan_offset)
        round_trip_point = self.calculator.video_to_display(video_point, scale, pan_offset)
        self.assertAlmostEqual(round_trip_point[0], original_point[0], places=5)
        self.assertAlmostEqual(round_trip_point[1], original_point[1], places=5)

    def test_very_small_video(self) -> None:
        """Test edge case: very small video dimensions."""
        video_size = (1, 1)
        display_size = (1920, 1080)
        scale_x, scale_y = self.calculator.calculate_scale(video_size, display_size, ScalingMode.INDEPENDENT)
        self.assertEqual(scale_x, scale_y)
        self.assertAlmostEqual(scale_x, 1080.0, places=5)

    def test_very_large_video(self) -> None:
        """Test edge case: very large video dimensions."""
        video_size = (7680, 4320)
        display_size = (1920, 1080)
        scale_x, scale_y = self.calculator.calculate_scale(video_size, display_size, ScalingMode.INDEPENDENT)
        self.assertEqual(scale_x, scale_y)
        self.assertAlmostEqual(scale_x, 1080 / 4320, places=5)

    def test_very_small_display(self) -> None:
        """Test edge case: very small display dimensions."""
        video_size = (1920, 1080)
        display_size = (1, 1)
        scale_x, scale_y = self.calculator.calculate_scale(video_size, display_size, ScalingMode.INDEPENDENT)
        self.assertEqual(scale_x, scale_y)
        self.assertAlmostEqual(scale_x, 1 / 1920, places=5)
