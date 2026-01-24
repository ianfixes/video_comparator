"""Unit tests for FrameRequestStatus and FrameResult classes."""

import unittest

import numpy as np

from video_comparator.cache.frame_result import FrameResult
from video_comparator.common.types import FrameRequestStatus
from video_comparator.decode.video_decoder import DecodeError, SeekError


class TestFrameRequestStatus(unittest.TestCase):
    """Test cases for FrameRequestStatus enum."""

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values exist and are accessible."""
        expected_values = {
            "SUCCESS",
            "CANCELLED",
            "DECODE_ERROR",
            "SEEK_ERROR",
            "OUT_OF_RANGE",
        }
        actual_values = {status.name for status in FrameRequestStatus}
        self.assertEqual(expected_values, actual_values)

    def test_enum_values_are_unique(self) -> None:
        """Test that all enum values are unique."""
        values = [
            FrameRequestStatus.SUCCESS,
            FrameRequestStatus.CANCELLED,
            FrameRequestStatus.DECODE_ERROR,
            FrameRequestStatus.SEEK_ERROR,
            FrameRequestStatus.OUT_OF_RANGE,
        ]
        unique_values = set(values)
        self.assertEqual(len(values), len(unique_values))

    def test_enum_can_be_compared(self) -> None:
        """Test that enum values can be compared for equality."""
        self.assertEqual(FrameRequestStatus.SUCCESS, FrameRequestStatus.SUCCESS)
        self.assertNotEqual(FrameRequestStatus.SUCCESS, FrameRequestStatus.CANCELLED)


class TestFrameResult(unittest.TestCase):
    """Test cases for FrameResult dataclass."""

    def test_initialization_with_success_case(self) -> None:
        """Test FrameResult initialization with success case."""
        frame_number = 42
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        status = FrameRequestStatus.SUCCESS

        result = FrameResult(frame_number=frame_number, frame=frame, status=status)

        self.assertEqual(result.frame_number, frame_number)
        if result.frame is None:
            return self.assertIsNotNone(result.frame)  # This construct appeases mypy
        np.testing.assert_array_equal(result.frame, frame)
        self.assertEqual(result.status, FrameRequestStatus.SUCCESS)
        self.assertIsNone(result.error)

    def test_initialization_with_cancelled_status(self) -> None:
        """Test FrameResult initialization with CANCELLED status."""
        frame_number = 10
        status = FrameRequestStatus.CANCELLED

        result = FrameResult(frame_number=frame_number, frame=None, status=status)

        self.assertEqual(result.frame_number, frame_number)
        self.assertIsNone(result.frame)
        self.assertEqual(result.status, FrameRequestStatus.CANCELLED)
        self.assertIsNone(result.error)

    def test_initialization_with_decode_error(self) -> None:
        """Test FrameResult initialization with DECODE_ERROR status."""
        frame_number = 5
        status = FrameRequestStatus.DECODE_ERROR
        error = DecodeError("Failed to decode frame")

        result = FrameResult(frame_number=frame_number, frame=None, status=status, error=error)

        self.assertEqual(result.frame_number, frame_number)
        self.assertIsNone(result.frame)
        self.assertEqual(result.status, FrameRequestStatus.DECODE_ERROR)
        self.assertIsNotNone(result.error)
        self.assertIsInstance(result.error, DecodeError)
        self.assertEqual(str(result.error), "Failed to decode frame")

    def test_initialization_with_seek_error(self) -> None:
        """Test FrameResult initialization with SEEK_ERROR status."""
        frame_number = 100
        status = FrameRequestStatus.SEEK_ERROR
        error = SeekError("Failed to seek to frame")

        result = FrameResult(frame_number=frame_number, frame=None, status=status, error=error)

        self.assertEqual(result.frame_number, frame_number)
        self.assertIsNone(result.frame)
        self.assertEqual(result.status, FrameRequestStatus.SEEK_ERROR)
        self.assertIsNotNone(result.error)
        self.assertIsInstance(result.error, SeekError)
        self.assertEqual(str(result.error), "Failed to seek to frame")

    def test_initialization_with_out_of_range(self) -> None:
        """Test FrameResult initialization with OUT_OF_RANGE status."""
        frame_number = 9999
        status = FrameRequestStatus.OUT_OF_RANGE
        error = ValueError("Frame index out of range")

        result = FrameResult(frame_number=frame_number, frame=None, status=status, error=error)

        self.assertEqual(result.frame_number, frame_number)
        self.assertIsNone(result.frame)
        self.assertEqual(result.status, FrameRequestStatus.OUT_OF_RANGE)
        self.assertIsNotNone(result.error)
        self.assertIsInstance(result.error, ValueError)

    def test_initialization_with_none_frame_and_success_status(self) -> None:
        """Test FrameResult with None frame but SUCCESS status (edge case)."""
        frame_number = 0
        status = FrameRequestStatus.SUCCESS

        result = FrameResult(frame_number=frame_number, frame=None, status=status)

        self.assertEqual(result.frame_number, frame_number)
        self.assertIsNone(result.frame)
        self.assertEqual(result.status, FrameRequestStatus.SUCCESS)
        self.assertIsNone(result.error)

    def test_initialization_with_frame_and_error_status(self) -> None:
        """Test FrameResult with frame data but error status (edge case)."""
        frame_number = 1
        frame = np.ones((720, 1280, 3), dtype=np.uint8)
        status = FrameRequestStatus.DECODE_ERROR
        error = DecodeError("Partial decode failure")

        result = FrameResult(frame_number=frame_number, frame=frame, status=status, error=error)

        self.assertEqual(result.frame_number, frame_number)
        if result.frame is None:
            return self.assertIsNotNone(result.frame)  # This construct appeases mypy
        np.testing.assert_array_equal(result.frame, frame)
        self.assertEqual(result.status, FrameRequestStatus.DECODE_ERROR)
        self.assertIsNotNone(result.error)

    def test_dataclass_is_frozen(self) -> None:
        """Test that FrameResult is frozen (immutable)."""
        from dataclasses import FrozenInstanceError

        frame_number = 10
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        status = FrameRequestStatus.SUCCESS

        result = FrameResult(frame_number=frame_number, frame=frame, status=status)

        with self.assertRaises(FrozenInstanceError):
            result.frame_number = 20  # type: ignore # we're literally testing the frozenness of the dataclass

    def test_all_status_values_can_be_used(self) -> None:
        """Test that all FrameRequestStatus values can be used in FrameResult."""
        frame_number = 5
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        for status in FrameRequestStatus:
            result = FrameResult(frame_number=frame_number, frame=frame, status=status)
            self.assertEqual(result.status, status)
            self.assertEqual(result.frame_number, frame_number)
