"""Unit tests for PrefillStrategy classes."""

import unittest

from video_comparator.cache.prefill_strategy import PrefillStrategy, TrivialPrefillStrategy


class TestPrefillStrategy(unittest.TestCase):
    """Test cases for PrefillStrategy ABC."""

    def test_abc_cannot_be_instantiated(self) -> None:
        """Test that PrefillStrategy ABC cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            PrefillStrategy()  # type: ignore


class TestTrivialPrefillStrategy(unittest.TestCase):
    """Test cases for TrivialPrefillStrategy class."""

    def test_get_protected_frames_returns_copy(self) -> None:
        """Test that get_protected_frames returns a copy of the protected set."""
        protected = {1, 2, 3}
        strategy = TrivialPrefillStrategy(protected)
        result = strategy.get_protected_frames()

        self.assertEqual(result, protected)
        self.assertIsNot(result, protected)

        result.add(4)
        result2 = strategy.get_protected_frames()
        self.assertNotIn(4, result2)
        self.assertEqual(result2, protected)

    def test_get_protected_frames_empty_set(self) -> None:
        """Test get_protected_frames with empty set."""
        strategy = TrivialPrefillStrategy(set())
        result = strategy.get_protected_frames()

        self.assertEqual(result, set())
        self.assertIsInstance(result, set)

    def test_get_protected_frames_large_set(self) -> None:
        """Test get_protected_frames with large set of frames."""
        protected = set(range(1000))
        strategy = TrivialPrefillStrategy(protected)
        result = strategy.get_protected_frames()

        self.assertEqual(result, protected)
        self.assertEqual(len(result), 1000)

    def test_is_protected_frame_returns_true_for_protected(self) -> None:
        """Test is_protected_frame returns True for frames in protected set."""
        strategy = TrivialPrefillStrategy({1, 2, 3, 5, 8})

        self.assertTrue(strategy.is_protected_frame(1))
        self.assertTrue(strategy.is_protected_frame(2))
        self.assertTrue(strategy.is_protected_frame(3))
        self.assertTrue(strategy.is_protected_frame(5))
        self.assertTrue(strategy.is_protected_frame(8))

    def test_is_protected_frame_returns_false_for_unprotected(self) -> None:
        """Test is_protected_frame returns False for frames not in protected set."""
        strategy = TrivialPrefillStrategy({1, 2, 3})

        self.assertFalse(strategy.is_protected_frame(0))
        self.assertFalse(strategy.is_protected_frame(4))
        self.assertFalse(strategy.is_protected_frame(10))
        self.assertFalse(strategy.is_protected_frame(-1))

    def test_is_protected_frame_empty_set(self) -> None:
        """Test is_protected_frame with empty protected set."""
        strategy = TrivialPrefillStrategy(set())

        self.assertFalse(strategy.is_protected_frame(0))
        self.assertFalse(strategy.is_protected_frame(1))
        self.assertFalse(strategy.is_protected_frame(100))

    def test_is_protected_frame_consistency_with_get_protected_frames(self) -> None:
        """Test that is_protected_frame is consistent with get_protected_frames."""
        protected = {10, 20, 30, 40, 50}
        strategy = TrivialPrefillStrategy(protected)

        protected_set = strategy.get_protected_frames()

        for frame_num in range(100):
            expected = frame_num in protected_set
            actual = strategy.is_protected_frame(frame_num)
            self.assertEqual(actual, expected, f"Frame {frame_num} should have protection={expected}")
