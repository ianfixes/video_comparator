"""Consistency checks: same presentation index via seek vs sequential decode, and cache eviction.

Seek PTS targets use the same presentation-floor anchor as frame index assignment so
direct seek and sequential forward decode agree for the same logical index.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Iterator, List, Optional

import numpy as np

from video_comparator.cache.frame_cache import FrameCache
from video_comparator.cache.frame_result import FrameResult
from video_comparator.cache.prefill_strategy import TrivialPrefillStrategy
from video_comparator.common.types import FrameRequestStatus
from video_comparator.decode.video_decoder import VideoDecoder
from video_comparator.media.video_metadata import VideoMetadata


def _iter_frames(start: int, end_inclusive: int) -> Iterator[int]:
    for i in range(start, end_inclusive + 1):
        yield i


class TestDecodeFrameIndexConsistency(unittest.TestCase):
    """Decode-path invariants for frame-index → pixels mapping."""

    sample_data_dir = Path(__file__).parent / "sample_data"

    @classmethod
    def _first_existing_video(cls) -> Optional[Path]:
        candidates: List[str] = [
            "file_example_AVI_480_750kB.avi",
            "file_example_AVI_640_800kB.avi",
            "file_example_AVI_480_750kB_24fps_with_1s_black.mp4",
            "demo1_60p_Original.mp4",
        ]
        for name in candidates:
            path = cls.sample_data_dir / name
            if path.is_file():
                return path
        return None

    @classmethod
    def _first_existing_avi(cls) -> Optional[Path]:
        for name in ("file_example_AVI_480_750kB.avi", "file_example_AVI_640_800kB.avi"):
            path = cls.sample_data_dir / name
            if path.is_file():
                return path
        return None

    @classmethod
    def _metadata_or_skip(cls) -> VideoMetadata:
        path = cls._first_existing_video()
        if path is None:
            raise unittest.SkipTest("No sample video under tests/sample_data for consistency tests")
        return VideoMetadata.from_path(path)

    @classmethod
    def _avi_metadata_or_skip(cls) -> VideoMetadata:
        """AVI sample used for strict seek-vs-walk equality (see module docstring)."""
        path = cls._first_existing_avi()
        if path is None:
            raise unittest.SkipTest(
                "No AVI sample under tests/sample_data; skip strict seek-vs-sequential pixel equality"
            )
        return VideoMetadata.from_path(path)

    def test_frame_zero_direct_matches_sequential(self) -> None:
        """Index 0: seek-only decoder vs walk from start must match (baseline invariant)."""
        metadata = self._avi_metadata_or_skip()
        if metadata.total_frames < 1:
            self.skipTest("Need at least one frame")
        direct = self._decode_direct(metadata, 0)
        sequential = self._decode_sequential_from_start(metadata, 0)
        np.testing.assert_array_equal(direct, sequential)

    def test_direct_seek_matches_sequential_forward_decode(self) -> None:
        """Fresh seek decode(frame) must match walking 0..frame on one decoder (forward path)."""
        metadata = self._avi_metadata_or_skip()
        total = metadata.total_frames
        if total < 3:
            self.skipTest("Need at least 3 frames")

        targets = [0, 1, min(12, total - 2), min(30, total - 2)]
        targets = sorted(set(t for t in targets if 0 <= t < total))

        for frame_index in targets:
            with self.subTest(frame_index=frame_index):
                direct = self._decode_direct(metadata, frame_index)
                sequential = self._decode_sequential_from_start(metadata, frame_index)
                np.testing.assert_array_equal(
                    direct,
                    sequential,
                    err_msg=f"direct vs sequential mismatch at frame_index={frame_index}",
                )

    def test_repeated_decode_same_index_same_decoder(self) -> None:
        """Two decode_frame(n) calls on one decoder must return identical pixels."""
        metadata = self._metadata_or_skip()
        frame_index = min(7, metadata.total_frames - 1)
        decoder = VideoDecoder(metadata)
        try:
            first = decoder.decode_frame(frame_index)
            second = decoder.decode_frame(frame_index)
        finally:
            decoder.close()
        np.testing.assert_array_equal(first, second)

    def test_seek_backward_then_redo_index_matches_fresh_decoder(self) -> None:
        """After decoding a later frame, jumping backward must reproduce the same pixels as a fresh decoder."""
        metadata = self._metadata_or_skip()
        total = metadata.total_frames
        hi = min(20, total - 1)
        lo = min(3, hi - 1)
        if lo < 0 or hi <= lo:
            self.skipTest("Not enough frames for backward seek test")

        decoder = VideoDecoder(metadata)
        try:
            decoder.decode_frame(hi)
            after_backward = decoder.decode_frame(lo)
        finally:
            decoder.close()

        fresh = self._decode_direct(metadata, lo)
        np.testing.assert_array_equal(fresh, after_backward)

    def test_frame_cache_invalidate_then_redeliver_same_pixels(self) -> None:
        """Cache miss vs hit-after-evict must store the same bitmap for the same index."""
        metadata = self._metadata_or_skip()
        frame_index = min(9, metadata.total_frames - 2)
        decoder = VideoDecoder(metadata)
        cache = FrameCache(max_memory_mb=50)
        try:
            first = self._fetch_once_through_cache(cache, decoder, frame_index)
            self.assertEqual(first.status, FrameRequestStatus.SUCCESS)
            self.assertIsNotNone(first.frame)
            assert first.frame is not None
            reference = first.frame.copy()

            cache.invalidate()

            second = self._fetch_once_through_cache(cache, decoder, frame_index)
            self.assertEqual(second.status, FrameRequestStatus.SUCCESS)
            self.assertIsNotNone(second.frame)
            assert second.frame is not None
            np.testing.assert_array_equal(reference, second.frame)
        finally:
            decoder.close()
            cache.close()

    @staticmethod
    def _decode_direct(metadata: VideoMetadata, frame_index: int) -> np.ndarray:
        dec = VideoDecoder(metadata)
        try:
            return dec.decode_frame(frame_index).copy()
        finally:
            dec.close()

    @staticmethod
    def _decode_sequential_from_start(metadata: VideoMetadata, frame_index: int) -> np.ndarray:
        dec = VideoDecoder(metadata)
        try:
            last: Optional[np.ndarray] = None
            for i in range(frame_index + 1):
                last = dec.decode_frame(i)
            assert last is not None
            return last.copy()
        finally:
            dec.close()

    @staticmethod
    def _fetch_once_through_cache(cache: FrameCache, decoder: VideoDecoder, frame_index: int) -> FrameResult:
        results: List[FrameResult] = []

        def cb(result: FrameResult) -> None:
            results.append(result)

        strategy = TrivialPrefillStrategy(_iter_frames(frame_index, frame_index))
        cache.request_prefill_frame(strategy, cb, decoder)
        assert len(results) == 1
        return results[0]
