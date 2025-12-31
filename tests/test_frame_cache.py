"""Unit tests for FrameCache class."""

import unittest

import numpy as np

from video_comparator.cache.frame_cache import FrameCache
from video_comparator.cache.prefill_strategy import TrivialPrefillStrategy


class TestFrameCache(unittest.TestCase):
    """Test cases for FrameCache class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.cache = FrameCache(max_memory_mb=100)

    def _create_test_frame(self, width: int = 1920, height: int = 1080) -> np.ndarray:
        """Create a test frame array."""
        return np.zeros((height, width, 3), dtype=np.uint8)

    def test_cache_hit_when_frame_exists(self) -> None:
        """Test cache hit when frame exists."""
        frame = self._create_test_frame()
        self.cache.put(0, frame)
        result = self.cache.get(0)
        if result is None:
            return self.assertIsNotNone(result)  # fake out mypy
        np.testing.assert_array_equal(result, frame)

    def test_cache_miss_when_frame_does_not_exist(self) -> None:
        """Test cache miss when frame doesn't exist."""
        result = self.cache.get(0)
        self.assertIsNone(result)

    def test_cache_eviction_when_memory_exceeded(self) -> None:
        """Test cache eviction when memory limit exceeded."""
        frame = self._create_test_frame(width=3840, height=2160)
        frame_memory_mb = frame.nbytes / (1024 * 1024)

        cache = FrameCache(max_memory_mb=int(frame_memory_mb * 2.5))

        cache.put(0, frame)
        cache.put(1, frame)
        cache.put(2, frame)

        total_memory = cache._calculate_total_memory()
        self.assertLessEqual(total_memory, cache.max_memory_bytes)

    def test_cache_eviction_lru_order(self) -> None:
        """Test that LRU eviction removes least recently used frames."""
        frame = self._create_test_frame()
        frame_size = frame.nbytes
        max_memory_bytes = int(frame_size * 3.5)
        cache = FrameCache(max_memory_mb=int(max_memory_bytes / (1024 * 1024)), frame_size_estimate_bytes=frame_size)

        cache.put(0, frame)
        cache.put(1, frame)
        cache.put(2, frame)

        cache.get(0)
        cache.put(3, frame)

        self.assertIsNotNone(cache.get(0))
        self.assertIsNone(cache.get(1))
        self.assertIsNotNone(cache.get(2))
        self.assertIsNotNone(cache.get(3))

    def test_cache_invalidation_clears_all_frames(self) -> None:
        """Test cache invalidation clears all frames."""
        frame = self._create_test_frame()
        self.cache.put(0, frame)
        self.cache.put(1, frame)
        self.cache.put(2, frame)

        self.assertEqual(len(self.cache.cache), 3)

        self.cache.invalidate()

        self.assertEqual(len(self.cache.cache), 0)
        self.assertEqual(self.cache.num_entries(), 0)
        self.assertEqual(len(self.cache.access_order), 0)
        self.assertIsNone(self.cache.get(0))
        self.assertIsNone(self.cache.get(1))
        self.assertIsNone(self.cache.get(2))

    def test_cache_with_various_frame_sizes(self) -> None:
        """Test cache with various frame sizes."""
        small_frame = self._create_test_frame(width=640, height=480)
        medium_frame = self._create_test_frame(width=1920, height=1080)
        large_frame = self._create_test_frame(width=3840, height=2160)

        self.cache.put(0, small_frame)
        self.cache.put(1, medium_frame)
        self.cache.put(2, large_frame)

        self.assertIsNotNone(self.cache.get(0))
        self.assertIsNotNone(self.cache.get(1))
        self.assertIsNotNone(self.cache.get(2))

    def test_put_existing_frame_updates_access_order(self) -> None:
        """Test that putting an existing frame updates access order."""
        frame = self._create_test_frame()
        frame_size = frame.nbytes
        max_memory_bytes = int(frame_size * 3.5)
        cache = FrameCache(max_memory_mb=int(max_memory_bytes / (1024 * 1024)), frame_size_estimate_bytes=frame_size)

        cache.put(0, frame)
        cache.put(1, frame)
        cache.put(2, frame)

        cache.put(0, frame)
        cache.put(3, frame)

        self.assertIsNotNone(cache.get(0))
        self.assertIsNone(cache.get(1))
        self.assertIsNotNone(cache.get(2))
        self.assertIsNotNone(cache.get(3))

    def test_get_updates_access_order(self) -> None:
        """Test that getting a frame updates access order."""
        frame = self._create_test_frame()
        frame_size = frame.nbytes
        max_memory_bytes = int(frame_size * 3.5)
        cache = FrameCache(max_memory_mb=int(max_memory_bytes / (1024 * 1024)), frame_size_estimate_bytes=frame_size)

        cache.put(0, frame)
        cache.put(1, frame)
        cache.put(2, frame)

        cache.get(0)
        cache.put(3, frame)

        self.assertIsNotNone(cache.get(0))
        self.assertIsNone(cache.get(1))

    def test_calculate_frame_memory(self) -> None:
        """Test frame memory calculation."""
        frame = self._create_test_frame(width=1920, height=1080)
        expected_bytes = 1920 * 1080 * 3 * 1
        actual_bytes = self.cache._calculate_frame_memory(frame)
        self.assertEqual(actual_bytes, expected_bytes)

    def test_calculate_total_memory(self) -> None:
        """Test total memory calculation."""
        frame = self._create_test_frame()
        frame_bytes = self.cache._calculate_frame_memory(frame)

        self.cache.put(0, frame)
        self.cache.put(1, frame)
        self.cache.put(2, frame)

        total_bytes = self.cache._calculate_total_memory()
        self.assertEqual(total_bytes, frame_bytes * 3)

    def test_cache_size(self) -> None:
        """Test cache_size returns total bytes used."""
        frame = self._create_test_frame()
        frame_bytes = self.cache._calculate_frame_memory(frame)

        self.cache.put(0, frame)
        self.cache.put(1, frame)

        self.assertEqual(self.cache.cache_size(), frame_bytes * 2)

    def test_num_entries(self) -> None:
        """Test num_entries returns correct count."""
        frame = self._create_test_frame()
        self.assertEqual(self.cache.num_entries(), 0)

        self.cache.put(0, frame)
        self.assertEqual(self.cache.num_entries(), 1)

        self.cache.put(1, frame)
        self.assertEqual(self.cache.num_entries(), 2)

    def test_has_frame(self) -> None:
        """Test has_frame returns correct boolean."""
        frame = self._create_test_frame()
        self.assertFalse(self.cache.has_frame(0))

        self.cache.put(0, frame)
        self.assertTrue(self.cache.has_frame(0))
        self.assertFalse(self.cache.has_frame(1))

    def test_get_missing_frames(self) -> None:
        """Test get_missing_frames returns uncached frame indices."""
        frame = self._create_test_frame()
        self.cache.put(0, frame)
        self.cache.put(2, frame)

        missing = self.cache.get_missing_frames({0, 1, 2, 3})
        self.assertEqual(missing, {1, 3})

    def test_set_prefill_strategy(self) -> None:
        """Test set_prefill_strategy updates the strategy."""
        strategy = TrivialPrefillStrategy({1, 2, 3})
        self.cache.set_prefill_strategy(strategy)
        self.assertEqual(self.cache.prefill_strategy, strategy)
        self.assertIsNone(self.cache.protected_frames)

    def test_set_prefill_strategy_none(self) -> None:
        """Test set_prefill_strategy with None disables protection."""
        strategy = TrivialPrefillStrategy({1, 2, 3})
        self.cache.set_prefill_strategy(strategy)
        self.cache.set_prefill_strategy(None)
        self.assertIsNone(self.cache.prefill_strategy)
        self.assertIsNone(self.cache.protected_frames)

    def test_protected_frames_not_evicted(self) -> None:
        """Test that protected frames are not evicted even when memory limit is reached."""
        frame = self._create_test_frame()
        frame_size = frame.nbytes
        max_memory_bytes = int(frame_size * 3.5)
        cache = FrameCache(max_memory_mb=int(max_memory_bytes / (1024 * 1024)), frame_size_estimate_bytes=frame_size)

        strategy = TrivialPrefillStrategy({0, 1})
        cache.set_prefill_strategy(strategy)

        cache.put(0, frame)
        cache.put(1, frame)
        cache.put(2, frame)
        cache.put(3, frame)

        self.assertIsNotNone(cache.get(0))
        self.assertIsNotNone(cache.get(1))
        self.assertIsNone(cache.get(2))

    def test_protected_frames_lru_among_unprotected(self) -> None:
        """Test that LRU eviction works among unprotected frames."""
        frame = self._create_test_frame()
        frame_size = frame.nbytes
        max_memory_bytes = int(frame_size * 3.5)
        cache = FrameCache(max_memory_mb=int(max_memory_bytes / (1024 * 1024)), frame_size_estimate_bytes=frame_size)

        strategy = TrivialPrefillStrategy({0})
        cache.set_prefill_strategy(strategy)

        cache.put(0, frame)
        cache.put(1, frame)
        cache.put(2, frame)

        cache.get(1)
        cache.put(3, frame)

        self.assertIsNotNone(cache.get(0))
        self.assertIsNotNone(cache.get(1))
        self.assertIsNone(cache.get(2))
        self.assertIsNotNone(cache.get(3))

    def test_all_frames_protected_evicts_oldest(self) -> None:
        """Test that if all frames are protected, evicts least recently used anyway."""
        frame = self._create_test_frame()
        frame_size = frame.nbytes
        max_memory_bytes = int(frame_size * 3.5)
        cache = FrameCache(max_memory_mb=int(max_memory_bytes / (1024 * 1024)), frame_size_estimate_bytes=frame_size)

        strategy = TrivialPrefillStrategy({0, 1, 2})
        cache.set_prefill_strategy(strategy)

        cache.put(0, frame)
        cache.put(1, frame)
        cache.put(2, frame)

        cache.get(0)
        cache.put(3, frame)

        self.assertIsNotNone(cache.get(0))
        self.assertIsNone(cache.get(1))
        self.assertIsNotNone(cache.get(2))
        self.assertIsNotNone(cache.get(3))

    def test_protected_frames_reset_on_strategy_change(self) -> None:
        """Test that protected frames are reset when strategy changes."""
        frame = self._create_test_frame()
        frame_size = frame.nbytes
        cache = FrameCache(max_memory_mb=1, frame_size_estimate_bytes=frame_size)

        strategy1 = TrivialPrefillStrategy({0, 1})
        cache.set_prefill_strategy(strategy1)
        self.assertIsNone(cache.protected_frames)

        cache.put(0, frame)
        cache._ensure_protected_frames()
        self.assertEqual(cache.protected_frames, {0, 1})

        strategy2 = TrivialPrefillStrategy({2, 3})
        cache.set_prefill_strategy(strategy2)
        self.assertIsNone(cache.protected_frames)

        cache._ensure_protected_frames()
        self.assertEqual(cache.protected_frames, {2, 3})

    def test_num_free_entries_with_frames(self) -> None:
        """Test num_free_entries calculation with cached frames."""
        frame = self._create_test_frame()
        frame_size = frame.nbytes
        cache = FrameCache(max_memory_mb=100, frame_size_estimate_bytes=frame_size)

        cache.put(0, frame)
        cache.put(1, frame)

        free_entries = cache.num_free_entries()
        self.assertGreater(free_entries, 0)
        self.assertIsInstance(free_entries, int)

    def test_num_free_entries_empty_cache(self) -> None:
        """Test num_free_entries with empty cache."""
        frame_size = 1920 * 1080 * 3
        cache = FrameCache(max_memory_mb=100, frame_size_estimate_bytes=frame_size)

        free_entries = cache.num_free_entries()
        self.assertGreater(free_entries, 0)
        self.assertIsInstance(free_entries, int)

    def test_error_invalid_max_memory_mb_zero(self) -> None:
        """Test error handling: max_memory_mb is zero."""
        with self.assertRaises(ValueError) as context:
            FrameCache(max_memory_mb=0)
        self.assertIn("max_memory_mb must be > 0", str(context.exception))

    def test_error_invalid_max_memory_mb_negative(self) -> None:
        """Test error handling: max_memory_mb is negative."""
        with self.assertRaises(ValueError) as context:
            FrameCache(max_memory_mb=-1)
        self.assertIn("max_memory_mb must be > 0", str(context.exception))

    def test_error_invalid_frame_size_estimate_zero(self) -> None:
        """Test error handling: frame_size_estimate_bytes is zero."""
        with self.assertRaises(ValueError) as context:
            FrameCache(max_memory_mb=100, frame_size_estimate_bytes=0)
        self.assertIn("frame_size_estimate_bytes must be > 0", str(context.exception))

    def test_error_invalid_frame_size_estimate_negative(self) -> None:
        """Test error handling: frame_size_estimate_bytes is negative."""
        with self.assertRaises(ValueError) as context:
            FrameCache(max_memory_mb=100, frame_size_estimate_bytes=-1)
        self.assertIn("frame_size_estimate_bytes must be > 0", str(context.exception))
