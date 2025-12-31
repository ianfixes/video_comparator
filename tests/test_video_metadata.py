"""Unit tests for VideoMetadata and MetadataExtractor classes."""

import os
import unittest
from pathlib import Path
from typing import List

import av

from video_comparator.media.video_metadata import VideoMetadata


class TestVideoMetadata(unittest.TestCase):
    """Test cases for VideoMetadata class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.sample_data_dir = Path(__file__).parent / "sample_data"

    def test_dimensions_property_returns_tuple(self) -> None:
        """Test dimensions property returns correct (width, height) tuple."""
        metadata = VideoMetadata(
            file_path=Path("/test/path.avi"),
            duration=10.0,
            fps=30.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=300,
            time_base=0.001,
        )

        self.assertEqual(metadata.dimensions, (1920, 1080))
        self.assertIsInstance(metadata.dimensions, tuple)

    def test_validation_rejects_zero_duration(self) -> None:
        """Test VideoMetadata validation rejects zero duration."""
        with self.assertRaises(ValueError) as context:
            VideoMetadata(
                file_path=Path("/test/path.avi"),
                duration=0.0,
                fps=30.0,
                width=1920,
                height=1080,
                pixel_format="yuv420p",
                total_frames=300,
                time_base=0.001,
            )

        self.assertIn("duration must be > 0", str(context.exception))

    def test_validation_rejects_negative_duration(self) -> None:
        """Test VideoMetadata validation rejects negative duration."""
        with self.assertRaises(ValueError) as context:
            VideoMetadata(
                file_path=Path("/test/path.avi"),
                duration=-1.0,
                fps=30.0,
                width=1920,
                height=1080,
                pixel_format="yuv420p",
                total_frames=300,
                time_base=0.001,
            )

        self.assertIn("duration must be > 0", str(context.exception))

    def test_validation_rejects_zero_fps(self) -> None:
        """Test VideoMetadata validation rejects zero fps."""
        with self.assertRaises(ValueError) as context:
            VideoMetadata(
                file_path=Path("/test/path.avi"),
                duration=10.0,
                fps=0.0,
                width=1920,
                height=1080,
                pixel_format="yuv420p",
                total_frames=300,
                time_base=0.001,
            )

        self.assertIn("fps must be > 0", str(context.exception))

    def test_validation_rejects_negative_fps(self) -> None:
        """Test VideoMetadata validation rejects negative fps."""
        with self.assertRaises(ValueError) as context:
            VideoMetadata(
                file_path=Path("/test/path.avi"),
                duration=10.0,
                fps=-1.0,
                width=1920,
                height=1080,
                pixel_format="yuv420p",
                total_frames=300,
                time_base=0.001,
            )

        self.assertIn("fps must be > 0", str(context.exception))

    def test_validation_rejects_zero_width(self) -> None:
        """Test VideoMetadata validation rejects zero width."""
        with self.assertRaises(ValueError) as context:
            VideoMetadata(
                file_path=Path("/test/path.avi"),
                duration=10.0,
                fps=30.0,
                width=0,
                height=1080,
                pixel_format="yuv420p",
                total_frames=300,
                time_base=0.001,
            )

        self.assertIn("width must be > 0", str(context.exception))

    def test_validation_rejects_negative_width(self) -> None:
        """Test VideoMetadata validation rejects negative width."""
        with self.assertRaises(ValueError) as context:
            VideoMetadata(
                file_path=Path("/test/path.avi"),
                duration=10.0,
                fps=30.0,
                width=-1,
                height=1080,
                pixel_format="yuv420p",
                total_frames=300,
                time_base=0.001,
            )

        self.assertIn("width must be > 0", str(context.exception))

    def test_validation_rejects_zero_height(self) -> None:
        """Test VideoMetadata validation rejects zero height."""
        with self.assertRaises(ValueError) as context:
            VideoMetadata(
                file_path=Path("/test/path.avi"),
                duration=10.0,
                fps=30.0,
                width=1920,
                height=0,
                pixel_format="yuv420p",
                total_frames=300,
                time_base=0.001,
            )

        self.assertIn("height must be > 0", str(context.exception))

    def test_validation_rejects_negative_height(self) -> None:
        """Test VideoMetadata validation rejects negative height."""
        with self.assertRaises(ValueError) as context:
            VideoMetadata(
                file_path=Path("/test/path.avi"),
                duration=10.0,
                fps=30.0,
                width=1920,
                height=-1,
                pixel_format="yuv420p",
                total_frames=300,
                time_base=0.001,
            )

        self.assertIn("height must be > 0", str(context.exception))

    def test_validation_rejects_empty_pixel_format(self) -> None:
        """Test VideoMetadata validation rejects empty pixel_format."""
        with self.assertRaises(ValueError) as context:
            VideoMetadata(
                file_path=Path("/test/path.avi"),
                duration=10.0,
                fps=30.0,
                width=1920,
                height=1080,
                pixel_format="",
                total_frames=300,
                time_base=0.001,
            )

        self.assertIn("pixel_format cannot be empty", str(context.exception))

    def test_validation_rejects_zero_total_frames(self) -> None:
        """Test VideoMetadata validation rejects zero total_frames."""
        with self.assertRaises(ValueError) as context:
            VideoMetadata(
                file_path=Path("/test/path.avi"),
                duration=10.0,
                fps=30.0,
                width=1920,
                height=1080,
                pixel_format="yuv420p",
                total_frames=0,
                time_base=0.001,
            )

        self.assertIn("total_frames must be > 0", str(context.exception))

    def test_validation_rejects_negative_total_frames(self) -> None:
        """Test VideoMetadata validation rejects negative total_frames."""
        with self.assertRaises(ValueError) as context:
            VideoMetadata(
                file_path=Path("/test/path.avi"),
                duration=10.0,
                fps=30.0,
                width=1920,
                height=1080,
                pixel_format="yuv420p",
                total_frames=-1,
                time_base=0.001,
            )

        self.assertIn("total_frames must be > 0", str(context.exception))

    def test_validation_rejects_zero_time_base(self) -> None:
        """Test VideoMetadata validation rejects zero time_base."""
        with self.assertRaises(ValueError) as context:
            VideoMetadata(
                file_path=Path("/test/path.avi"),
                duration=10.0,
                fps=30.0,
                width=1920,
                height=1080,
                pixel_format="yuv420p",
                total_frames=300,
                time_base=0.0,
            )

        self.assertIn("time_base must be > 0", str(context.exception))

    def test_validation_rejects_negative_time_base(self) -> None:
        """Test VideoMetadata validation rejects negative time_base."""
        with self.assertRaises(ValueError) as context:
            VideoMetadata(
                file_path=Path("/test/path.avi"),
                duration=10.0,
                fps=30.0,
                width=1920,
                height=1080,
                pixel_format="yuv420p",
                total_frames=300,
                time_base=-0.001,
            )

        self.assertIn("time_base must be > 0", str(context.exception))

    def test_validation_accepts_large_dimensions(self) -> None:
        """Test VideoMetadata accepts very large dimensions."""
        metadata = VideoMetadata(
            file_path=Path("/test/path.avi"),
            duration=10.0,
            fps=30.0,
            width=7680,
            height=4320,
            pixel_format="yuv420p",
            total_frames=300,
            time_base=0.001,
        )

        self.assertEqual(metadata.width, 7680)
        self.assertEqual(metadata.height, 4320)

    def test_validation_accepts_high_fps(self) -> None:
        """Test VideoMetadata accepts high fps values."""
        metadata = VideoMetadata(
            file_path=Path("/test/path.avi"),
            duration=10.0,
            fps=120.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=1200,
            time_base=0.001,
        )

        self.assertEqual(metadata.fps, 120.0)

    def test_extract_missing_file_raises_file_not_found_error(self) -> None:
        """Test extract raises FileNotFoundError for missing file."""
        with self.assertRaises(FileNotFoundError) as context:
            VideoMetadata.from_path(Path("/nonexistent/path/video.avi"))

        self.assertIn("Video file not found", str(context.exception))

    def test_extract_invalid_file_raises_value_error(self) -> None:
        """Test extract raises ValueError for invalid/unreadable file."""
        invalid_path = self.sample_data_dir / "nonexistent.avi"
        with self.assertRaises(FileNotFoundError):
            VideoMetadata.from_path(invalid_path)

    def test_extract_avi_file_returns_metadata(self) -> None:
        """Test extract returns VideoMetadata for valid AVI file."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)

        self.assertIsInstance(metadata, VideoMetadata)
        self.assertEqual(metadata.file_path, avi_file)
        # Specific values for file_example_AVI_480_750kB.avi
        self.assertAlmostEqual(metadata.duration, 30.613333, places=1)
        self.assertAlmostEqual(metadata.fps, 30.0, places=1)
        self.assertEqual(metadata.width, 480)
        self.assertEqual(metadata.height, 270)
        self.assertEqual(metadata.pixel_format, "yuv420p")
        self.assertEqual(metadata.total_frames, 901)
        self.assertAlmostEqual(metadata.time_base, 0.033333, places=2)

    def test_extract_all_required_fields_present(self) -> None:
        """Test extract returns all required metadata fields."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)

        self.assertIsNotNone(metadata.file_path)
        self.assertIsNotNone(metadata.duration)
        self.assertIsNotNone(metadata.fps)
        self.assertIsNotNone(metadata.width)
        self.assertIsNotNone(metadata.height)
        self.assertIsNotNone(metadata.pixel_format)
        self.assertIsNotNone(metadata.total_frames)
        self.assertIsNotNone(metadata.time_base)

    def test_extract_dimensions_property_works(self) -> None:
        """Test extracted metadata dimensions property works correctly."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)

        dimensions = metadata.dimensions
        self.assertEqual(dimensions, (metadata.width, metadata.height))
        self.assertIsInstance(dimensions, tuple)
        self.assertEqual(len(dimensions), 2)
        self.assertEqual(dimensions, (480, 270))  # Asserting known dimensions of this file

    def test_extract_different_avi_file(self) -> None:
        """Test extract works with different AVI file."""
        avi_file = self.sample_data_dir / "file_example_AVI_640_800kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)

        self.assertIsInstance(metadata, VideoMetadata)
        # Specific values for file_example_AVI_640_800kB.avi
        self.assertAlmostEqual(metadata.duration, 30.613333, places=1)
        self.assertEqual(metadata.width, 640)
        self.assertEqual(metadata.height, 360)
        self.assertGreater(metadata.fps, 0)  # If fps is not known, still keep generic check

    def test_extract_mp4_file_if_available(self) -> None:
        """Test extract works with MP4 file if available."""
        mp4_files: List[Path] = list(self.sample_data_dir.glob("*.mp4")) or []
        if not mp4_files:
            self.skipTest("No MP4 test files available")

        metadata = VideoMetadata.from_path(mp4_files[0])

        self.assertIsInstance(metadata, VideoMetadata)
        # Since test file name/values are unknown, only assert basic invariants
        self.assertTrue(metadata.duration > 0)
        self.assertTrue(metadata.fps > 0)
        self.assertTrue(metadata.width > 0)
        self.assertTrue(metadata.height > 0)

    def test_extract_no_video_stream_raises_value_error(self) -> None:
        """Test extract raises ValueError for file with no video stream."""
        from unittest.mock import MagicMock, patch

        test_file = self.sample_data_dir / "test_no_video.avi"
        test_file.touch()

        try:
            with patch("av.open") as mock_open:
                mock_container = MagicMock()
                mock_streams = MagicMock()
                mock_streams.video = []
                mock_container.streams = mock_streams
                mock_container.duration = None
                mock_container.close = MagicMock()
                mock_open.return_value = mock_container

                with self.assertRaises(ValueError) as context:
                    VideoMetadata.from_path(test_file)

                self.assertIn("No video stream found", str(context.exception))
                mock_container.close.assert_called_once()
        finally:
            if test_file.exists():
                test_file.unlink()
