"""Unit tests for FrameCache."""

import unittest
from unittest.mock import MagicMock

import numpy as np

from video_comparator.cache.frame_cache import FrameCache
from video_comparator.common.types import FrameRequestStatus
from video_comparator.decode.video_decoder import DecodeError, DecodeOperationResult, VideoDecoder


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

    def test_put_replaces_existing_frame_updates_memory_and_pixels(self) -> None:
        """Duplicate presentation keys must replace stale bitmaps (Architecture cache key correctness)."""
        frame_cache = FrameCache(max_memory_mb=10)
        a = np.zeros((4, 4, 3), dtype=np.uint8)
        b = np.ones((4, 4, 3), dtype=np.uint8)
        frame_cache.put(3, a)
        size_one = frame_cache.cache_size()
        frame_cache.put(3, b)
        self.assertEqual(frame_cache.cache_size(), size_one)
        cached = frame_cache.get(3)
        assert cached is not None
        np.testing.assert_array_equal(cached, b)

    def test_fetch_frame_sync_tail_decode_fallback_returns_nearest_decodable_frame(self) -> None:
        """Near-EOF decode miss should fall back to a trailing decodable frame without error."""
        frame_cache = FrameCache(max_memory_mb=10)
        decoder = MagicMock()
        decoder.metadata = MagicMock()
        decoder.metadata.total_frames = 100
        frame_cache._current_decoder_metadata_total_frames = 100
        target = 99
        fallback = 98
        fallback_frame = np.ones((2, 2, 3), dtype=np.uint8)

        def decode_side_effect(frame_index: int) -> DecodeOperationResult:
            if frame_index == target:
                raise DecodeError("Failed to decode frame 99")
            if frame_index == fallback:
                return DecodeOperationResult(
                    requested_frame=fallback_frame, decoded_frames=[(fallback, fallback_frame)]
                )
            raise AssertionError(f"Unexpected frame index {frame_index}")

        decoder.decode_frame_operation.side_effect = decode_side_effect

        result = frame_cache._fetch_frame_sync(target, decoder, is_prefetch=False)

        self.assertEqual(result.status, FrameRequestStatus.SUCCESS)
        self.assertIsNone(result.error)
        self.assertIsNotNone(result.frame)
        if result.frame is None:
            self.fail("tail fallback should return a frame")
        np.testing.assert_array_equal(result.frame, fallback_frame)
        self.assertEqual(decoder.decode_frame_operation.call_args_list[0].args[0], target)
        self.assertEqual(decoder.decode_frame_operation.call_args_list[1].args[0], fallback)

    def test_fetch_frame_sync_non_tail_decode_error_is_not_suppressed(self) -> None:
        """Decode errors away from EOF should still surface as DECODE_ERROR."""
        frame_cache = FrameCache(max_memory_mb=10)
        decoder = MagicMock()
        decoder.metadata = MagicMock()
        decoder.metadata.total_frames = 100
        frame_cache._current_decoder_metadata_total_frames = 100
        decoder.decode_frame_operation.side_effect = DecodeError("middle decode failure")

        result = frame_cache._fetch_frame_sync(50, decoder, is_prefetch=False)

        self.assertEqual(result.status, FrameRequestStatus.DECODE_ERROR)
        self.assertIsInstance(result.error, DecodeError)
