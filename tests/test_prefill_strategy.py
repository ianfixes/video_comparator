"""Unit tests for PrefillStrategy classes."""

import unittest
from typing import Set

from video_comparator.cache.prefill_strategy import PrefillStrategy, TrivialPrefillStrategy


class TestPrefillStrategy(unittest.TestCase):
    """Test cases for PrefillStrategy ABC."""

    def test_abc_cannot_be_instantiated(self) -> None:
        """Test that PrefillStrategy ABC cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            PrefillStrategy()  # type: ignore


class TestTrivialPrefillStrategy(unittest.TestCase):
    """Test cases for TrivialPrefillStrategy class."""

    def test_generate_protected_frames_yields_all_frames(self) -> None:
        """Test that generate_protected_frames yields all frames in sorted order."""
        protected = {3, 1, 2, 5, 4}
        strategy = TrivialPrefillStrategy(iter(protected))
        result = list(strategy.generate_protected_frames())

        self.assertEqual(result, [1, 2, 3, 4, 5])
        self.assertEqual(len(result), len(protected))

    def test_generate_protected_frames_empty_set(self) -> None:
        """Test generate_protected_frames with empty set."""
        strategy = TrivialPrefillStrategy(iter(set()))
        result = list(strategy.generate_protected_frames())

        self.assertEqual(result, [])
        self.assertIsInstance(result, list)

    def test_generate_protected_frames_large_set(self) -> None:
        """Test generate_protected_frames with large set of frames."""
        protected = set(range(1000))
        strategy = TrivialPrefillStrategy(iter(protected))
        result = list(strategy.generate_protected_frames())

        self.assertEqual(result, list(range(1000)))
        self.assertEqual(len(result), 1000)

    def test_generate_protected_frames_is_iterator(self) -> None:
        """Test that generate_protected_frames returns an iterator."""
        strategy = TrivialPrefillStrategy(iter({1, 2, 3}))
        generator = strategy.generate_protected_frames()

        self.assertTrue(hasattr(generator, "__iter__"))
        self.assertTrue(hasattr(generator, "__next__"))

        first = next(generator)
        self.assertEqual(first, 1)

    def test_is_protected_frame_returns_true_for_protected(self) -> None:
        """Test is_protected_frame returns True for frames in protected set."""
        strategy = TrivialPrefillStrategy(iter({1, 2, 3, 5, 8}))
        list(strategy.generate_protected_frames())

        self.assertTrue(strategy.is_protected_frame(1, set()))
        self.assertTrue(strategy.is_protected_frame(2, set()))
        self.assertTrue(strategy.is_protected_frame(3, set()))
        self.assertTrue(strategy.is_protected_frame(5, set()))
        self.assertTrue(strategy.is_protected_frame(8, set()))

    def test_is_protected_frame_returns_false_for_unprotected(self) -> None:
        """Test is_protected_frame returns False for frames not in protected set."""
        strategy = TrivialPrefillStrategy(iter({1, 2, 3}))
        list(strategy.generate_protected_frames())

        self.assertFalse(strategy.is_protected_frame(0, set()))
        self.assertFalse(strategy.is_protected_frame(4, set()))
        self.assertFalse(strategy.is_protected_frame(10, set()))
        self.assertFalse(strategy.is_protected_frame(-1, set()))

    def test_is_protected_frame_empty_set(self) -> None:
        """Test is_protected_frame with empty protected set."""
        strategy = TrivialPrefillStrategy(iter(set()))
        list(strategy.generate_protected_frames())

        self.assertFalse(strategy.is_protected_frame(0, set()))
        self.assertFalse(strategy.is_protected_frame(1, set()))
        self.assertFalse(strategy.is_protected_frame(100, set()))

    def test_is_protected_frame_consistency_with_generator(self) -> None:
        """Test that is_protected_frame is consistent with generate_protected_frames."""
        protected = {10, 20, 30, 40, 50}
        strategy = TrivialPrefillStrategy(iter(protected))
        protected_set: Set[int] = set(strategy.generate_protected_frames())

        for frame_num in range(100):
            expected = frame_num in protected_set
            actual = strategy.is_protected_frame(frame_num, set())
            self.assertEqual(actual, expected, f"Frame {frame_num} should have protection={expected}")

    def test_cacheable_frame_count_tracks_consumed_frames(self) -> None:
        """Test that cacheable_frame_count tracks how many frames were consumed."""
        strategy = TrivialPrefillStrategy(iter([1, 2, 3, 4, 5]))
        self.assertIsNone(strategy.cacheable_frame_count)

        generator = strategy.generate_protected_frames()
        frame1 = next(generator)
        self.assertEqual(strategy.cacheable_frame_count, 1)
        self.assertEqual(frame1, 1)

        frame2 = next(generator)
        self.assertEqual(strategy.cacheable_frame_count, 2)
        self.assertEqual(frame2, 2)

        remaining = list(generator)
        self.assertEqual(strategy.cacheable_frame_count, 5)
        self.assertEqual(remaining, [3, 4, 5])

    def test_protected_frames_returns_consumed_frames(self) -> None:
        """Test that protected_frames returns the set of consumed frames."""
        strategy = TrivialPrefillStrategy(iter([1, 2, 3, 4, 5]))
        list(strategy.generate_protected_frames())

        protected = strategy.protected_frames()
        self.assertEqual(protected, {1, 2, 3, 4, 5})
        self.assertEqual(len(protected), 5)

    def test_protected_frames_raises_error_if_not_generated(self) -> None:
        """Test that protected_frames raises error if generate_protected_frames not called."""
        strategy = TrivialPrefillStrategy(iter([1, 2, 3]))

        with self.assertRaises(PrefillStrategy.FramesNotGeneratedError):
            strategy.protected_frames()

        with self.assertRaises(PrefillStrategy.FramesNotGeneratedError):
            strategy.is_protected_frame(1, set())

    def test_protected_frames_respects_cache_capacity_limit(self) -> None:
        """Test that protected_frames only includes frames up to cache capacity."""
        strategy = TrivialPrefillStrategy(iter(range(100)))
        generator = strategy.generate_protected_frames()

        consumed = []
        for i, frame_num in enumerate(generator):
            consumed.append(frame_num)
            if i >= 4:
                break

        protected = strategy.protected_frames()
        self.assertEqual(len(protected), 5)
        self.assertEqual(protected, set(range(5)))
