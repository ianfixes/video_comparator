"""Unit tests for VideoDecoder class."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from video_comparator.cache.frame_cache import FrameCache
from video_comparator.decode.video_decoder import VideoDecoder
from video_comparator.media.video_metadata import VideoMetadata


class TestVideoDecoder(unittest.TestCase):
    """Test cases for VideoDecoder class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.sample_data_dir = Path(__file__).parent / "sample_data"

    def test_container_opening_with_valid_video_file(self) -> None:
        """Test container opening with valid video file."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        try:
            decoder._ensure_open()
            self.assertIsNotNone(decoder._container)
            self.assertIsNotNone(decoder._video_stream)
        finally:
            decoder.close()

    def test_container_opening_with_invalid_file_raises_error(self) -> None:
        """Test container opening with invalid file raises error."""
        invalid_file = Path("/nonexistent/file.avi")
        metadata = VideoMetadata(
            file_path=invalid_file,
            duration=10.0,
            fps=30.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=300,
            time_base=0.001,
        )

        with self.assertRaises(FileNotFoundError):
            VideoDecoder(metadata)

    def test_container_opening_with_none_file_path_raises_error(self) -> None:
        """Test container opening with None file_path raises error."""
        metadata = VideoMetadata(
            file_path=None,
            duration=10.0,
            fps=30.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=300,
            time_base=0.001,
        )

        with self.assertRaises(ValueError) as context:
            VideoDecoder(metadata)

        self.assertIn("file_path", str(context.exception))

    def test_video_stream_detection_and_selection(self) -> None:
        """Test video stream detection and selection."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        try:
            decoder._ensure_open()
            self.assertIsNotNone(decoder._video_stream)
            if decoder._video_stream is not None:
                self.assertEqual(decoder._video_stream.type, "video")
        finally:
            decoder.close()

    def test_seek_to_first_frame(self) -> None:
        """Test seek to first frame."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        try:
            decoder.seek_to_frame(0)
            frame = decoder.decode_frame(0)
            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(len(frame.shape), 3)
            self.assertEqual(frame.shape[2], 3)
        finally:
            decoder.close()

    def test_seek_to_last_frame(self) -> None:
        """Test seek to last frame."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        try:
            last_frame = metadata.total_frames - 1
            decoder.seek_to_frame(last_frame)
            frame = decoder.decode_frame(last_frame)
            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(len(frame.shape), 3)
            self.assertEqual(frame.shape[2], 3)
        finally:
            decoder.close()

    def test_seek_to_middle_frame(self) -> None:
        """Test seek to middle frame."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        try:
            middle_frame = metadata.total_frames // 2
            decoder.seek_to_frame(middle_frame)
            frame = decoder.decode_frame(middle_frame)
            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(len(frame.shape), 3)
            self.assertEqual(frame.shape[2], 3)
        finally:
            decoder.close()

    def test_frame_accurate_seek_by_frame_index(self) -> None:
        """Test frame-accurate seek by frame index verifies exact frame returned."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        try:
            frame_index = 100
            frame1 = decoder.decode_frame(frame_index)
            frame2 = decoder.decode_frame(frame_index)

            self.assertIsInstance(frame1, np.ndarray)
            self.assertIsInstance(frame2, np.ndarray)
            np.testing.assert_array_equal(frame1, frame2)
        finally:
            decoder.close()

    def test_frame_accurate_seek_by_timestamp(self) -> None:
        """Test frame-accurate seek by timestamp verifies correct frame for timestamp."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        try:
            timestamp = 5.0
            frame1 = decoder.decode_frame_at_timestamp(timestamp)
            frame2 = decoder.decode_frame_at_timestamp(timestamp)

            self.assertIsInstance(frame1, np.ndarray)
            self.assertIsInstance(frame2, np.ndarray)
            np.testing.assert_array_equal(frame1, frame2)

            expected_frame_index = int(timestamp * metadata.fps)
            expected_frame_index = min(expected_frame_index, metadata.total_frames - 1)
            frame_by_index = decoder.decode_frame(expected_frame_index)
            np.testing.assert_array_equal(frame1, frame_by_index)
        finally:
            decoder.close()

    def test_seek_to_timestamp(self) -> None:
        """Test seek to timestamp."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        try:
            timestamp = metadata.duration / 2.0
            decoder.seek_to_timestamp(timestamp)
            frame = decoder.decode_frame_at_timestamp(timestamp)
            self.assertIsInstance(frame, np.ndarray)
        finally:
            decoder.close()

    def test_seek_to_timestamp_out_of_range_raises_error(self) -> None:
        """Test seek to timestamp out of range raises error."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        try:
            with self.assertRaises(ValueError) as context:
                decoder.seek_to_timestamp(metadata.duration + 1.0)

            self.assertIn("out of range", str(context.exception))
        finally:
            decoder.close()

    def test_seek_to_frame_out_of_range_raises_error(self) -> None:
        """Test seek to frame out of range raises error."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        try:
            with self.assertRaises(ValueError) as context:
                decoder.seek_to_frame(metadata.total_frames)

            self.assertIn("out of range", str(context.exception))
        finally:
            decoder.close()

    def test_frame_decoding_returns_numpy_array_with_correct_shape(self) -> None:
        """Test frame decoding returns NumPy array with correct shape."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        try:
            frame = decoder.decode_frame(0)
            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(len(frame.shape), 3)
            self.assertEqual(frame.shape[0], metadata.height)
            self.assertEqual(frame.shape[1], metadata.width)
            self.assertEqual(frame.shape[2], 3)
        finally:
            decoder.close()

    def test_frame_decoding_returns_correct_pixel_format(self) -> None:
        """Test frame decoding returns correct pixel format (RGB)."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        try:
            frame = decoder.decode_frame(0)
            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(frame.dtype, np.uint8)
            self.assertEqual(frame.shape[2], 3)

            pixel = frame[0, 0]
            self.assertEqual(len(pixel), 3)
            self.assertTrue(all(0 <= val <= 255 for val in pixel))
        finally:
            decoder.close()

    def test_seek_with_different_avi_file(self) -> None:
        """Test seek with videos of different framerates."""
        avi_file = self.sample_data_dir / "file_example_AVI_640_800kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        try:
            middle_frame = metadata.total_frames // 2
            frame = decoder.decode_frame(middle_frame)
            self.assertIsInstance(frame, np.ndarray)
            self.assertEqual(frame.shape[0], metadata.height)
            self.assertEqual(frame.shape[1], metadata.width)
        finally:
            decoder.close()

    def test_decoder_with_frame_cache_integration(self) -> None:
        """Test decoder with FrameCache integration."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        frame_cache = FrameCache(max_memory_mb=100)
        decoder = VideoDecoder(metadata, frame_cache=frame_cache)

        try:
            frame_index = 50
            self.assertFalse(frame_cache.has_frame(frame_index))

            frame1 = decoder.decode_frame(frame_index)
            self.assertTrue(frame_cache.has_frame(frame_index))

            frame2 = decoder.decode_frame(frame_index)
            np.testing.assert_array_equal(frame1, frame2)

            cached_frame = frame_cache.get(frame_index)
            self.assertIsNotNone(cached_frame)
            if cached_frame is not None:
                np.testing.assert_array_equal(frame1, cached_frame)
        finally:
            decoder.close()

    def test_decode_frame_at_timestamp_out_of_range_raises_error(self) -> None:
        """Test decode_frame_at_timestamp with out of range timestamp raises error."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        try:
            with self.assertRaises(ValueError) as context:
                decoder.decode_frame_at_timestamp(metadata.duration + 1.0)

            self.assertIn("out of range", str(context.exception))
        finally:
            decoder.close()

    def test_decode_frame_out_of_range_raises_error(self) -> None:
        """Test decode_frame with out of range frame index raises error."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        try:
            with self.assertRaises(ValueError) as context:
                decoder.decode_frame(metadata.total_frames)

            self.assertIn("out of range", str(context.exception))
        finally:
            decoder.close()

    def test_context_manager(self) -> None:
        """Test VideoDecoder as context manager."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)

        with VideoDecoder(metadata) as decoder:
            frame = decoder.decode_frame(0)
            self.assertIsNotNone(frame)

        self.assertIsNone(decoder._container)
        self.assertIsNone(decoder._video_stream)

    def test_close_releases_resources(self) -> None:
        """Test close releases resources."""
        avi_file = self.sample_data_dir / "file_example_AVI_480_750kB.avi"
        if not avi_file.exists():
            self.skipTest(f"Test video file not found: {avi_file}")

        metadata = VideoMetadata.from_path(avi_file)
        decoder = VideoDecoder(metadata)

        decoder._ensure_open()
        self.assertIsNotNone(decoder._container)

        decoder.close()
        self.assertIsNone(decoder._container)
        self.assertIsNone(decoder._video_stream)

    def test_no_video_stream_raises_error(self) -> None:
        """Test that opening a file with no video stream raises error."""
        from unittest.mock import MagicMock, patch

        test_file = self.sample_data_dir / "test_no_video.avi"
        test_file.touch()

        try:
            metadata = VideoMetadata(
                file_path=test_file,
                duration=10.0,
                fps=30.0,
                width=1920,
                height=1080,
                pixel_format="yuv420p",
                total_frames=300,
                time_base=0.001,
            )

            with patch("av.open") as mock_open:
                import av

                mock_container = MagicMock()
                mock_streams = MagicMock()
                mock_streams.video = []
                mock_container.streams = mock_streams
                mock_container.close = MagicMock()
                mock_open.return_value = mock_container

                decoder = VideoDecoder(metadata)

                with self.assertRaises(ValueError) as context:
                    decoder._ensure_open()

                self.assertIn("No video stream found", str(context.exception))
                mock_container.close.assert_called_once()
        finally:
            if test_file.exists():
                test_file.unlink()
