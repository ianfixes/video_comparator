"""Unit tests for FrameCache."""

import unittest
from unittest.mock import MagicMock

import numpy as np

from video_comparator.cache.frame_cache import FrameCache
from video_comparator.decode.video_decoder import DecodeOperationResult, VideoDecoder


class TestFrameCache(unittest.TestCase):
    """Tests for decoder/cache integration and cache bookkeeping."""

    def test_decode_operation_frames_inserted_by_cache_once(self) -> None:
        """FrameCache should insert decoded intermediates and target frames."""
        frame_cache = FrameCache(max_memory_mb=10)
        decoder = MagicMock(spec=VideoDecoder)
        frame_a = np.zeros((2, 2, 3), dtype=np.uint8)
        frame_b = np.ones((2, 2, 3), dtype=np.uint8)
        decoder.decode_frame_operation.return_value = DecodeOperationResult(
            requested_frame=frame_b,
            decoded_frames=[(4, frame_a), (5, frame_b)],
        )

        status, error = frame_cache._attempt_to_cache_frame(5, decoder)

        self.assertIsNone(error)
        self.assertTrue(frame_cache.has_frame(4))
        self.assertTrue(frame_cache.has_frame(5))
        self.assertEqual(status.name, "SUCCESS")
        decoder.decode_frame_operation.assert_called_once_with(5)

    def test_cache_size_tracks_insertion_and_eviction_incrementally(self) -> None:
        """cache_size should reflect insertions and evictions correctly."""
        frame_cache = FrameCache(max_memory_mb=1)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame_bytes = frame.nbytes

        frame_cache.put(0, frame)
        self.assertEqual(frame_cache.cache_size(), frame_bytes)

        frame_cache.put(1, frame)
        self.assertEqual(frame_cache.cache_size(), frame_bytes * 2)

        for idx in range(2, 80):
            frame_cache.put(idx, frame)

        self.assertLessEqual(frame_cache.cache_size(), frame_cache.max_memory_bytes)
