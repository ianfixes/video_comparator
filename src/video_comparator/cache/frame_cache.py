"""Threaded frame cache with autonomous prefetching.

Responsibilities:
- Frame storage and retrieval (thread-safe)
- LRU eviction policy (thread-safe)
- Memory bounds management (thread-safe)
- Autonomous background prefetching with request cancellation
- Integration with PrefillStrategy to protect frames from eviction
"""

import queue
import threading
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional, Set, TextIO, Tuple

import numpy as np

from video_comparator.cache.frame_result import FrameResult
from video_comparator.cache.prefill_strategy import PrefillStrategy
from video_comparator.common.shell import get_env_bool, vd_debug_print
from video_comparator.common.types import FrameRequestStatus
from video_comparator.decode.video_decoder import DecodeError, SeekError, VideoDecoder

DEBUG_FORCE_UNIQUE_FRAMES = get_env_bool("DEBUG_FORCE_UNIQUE_FRAMES")
DEBUG_UNIQUE_FRACTION = 4
DEBUG_SKIP_CACHE_ENTIRELY = get_env_bool("DEBUG_SKIP_CACHE_ENTIRELY")
DEBUG_PRINT_FRAMEDEBUG = get_env_bool("DEBUG_PRINT_FRAMEDEBUG")


def print_framedebug(
    *args: Any, sep: str = " ", end: str = "\n", file: Optional[TextIO] = None, flush: bool = False
) -> None:
    if DEBUG_PRINT_FRAMEDEBUG:
        vd_debug_print("[FrameDebug]", *args, sep=sep, end=end, file=file, flush=flush)


class FrameCache:
    """Thread-safe frame cache with autonomous background prefetching."""

    _prefetch_coordination_semaphore: Optional[threading.Semaphore] = None
    _prefetch_coordination_lock = threading.Lock()
    _TAIL_FALLBACK_MAX_BACKTRACK_FRAMES = 2

    def __init__(
        self,
        max_memory_mb: int = 100,
        frame_size_estimate_bytes: Optional[int] = None,
        prefetch_coordination_semaphore: Optional[threading.Semaphore] = None,
    ) -> None:
        """Initialize threaded frame cache with size and memory limits.

        Args:
            max_memory_mb: Maximum memory usage in megabytes
            frame_size_estimate_bytes: Optional estimate of frame size in bytes
        """
        if max_memory_mb <= 0:
            raise ValueError(f"max_memory_mb must be > 0, got {max_memory_mb}")

        if frame_size_estimate_bytes is not None and frame_size_estimate_bytes <= 0:
            raise ValueError(f"frame_size_estimate_bytes must be > 0, got {frame_size_estimate_bytes}")

        self.max_memory_bytes: int = max_memory_mb * 1024 * 1024
        self.frame_size_estimate_bytes: Optional[int] = frame_size_estimate_bytes

        self._cache: Dict[int, np.ndarray] = {}
        self._access_order: OrderedDict[int, None] = OrderedDict()
        self._protected_frames: List[int] = []
        self._protected_frames_set: Set[int] = set()
        self._frame_sizes: Dict[int, int] = {}
        self._current_memory_bytes = 0
        self._lock = threading.Lock()

        if prefetch_coordination_semaphore is not None:
            self._prefetch_semaphore = prefetch_coordination_semaphore
        else:
            with FrameCache._prefetch_coordination_lock:
                if FrameCache._prefetch_coordination_semaphore is None:
                    FrameCache._prefetch_coordination_semaphore = threading.Semaphore(2)
                self._prefetch_semaphore = FrameCache._prefetch_coordination_semaphore

        self._prefetch_queue: queue.Queue[Optional[int]] = queue.Queue()
        self._cancellation_event = threading.Event()
        self._sync_event = threading.Event()
        self._prefetch_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._decoder_lock = threading.Lock()

        self._current_strategy: Optional[PrefillStrategy] = None
        self._current_callback: Optional[Callable[[FrameResult], None]] = None
        self._current_decoder: Optional[VideoDecoder] = None
        self._current_decoder_metadata_total_frames: int = 0

    def get(self, frame_index: int) -> Optional[np.ndarray]:
        """Retrieve a frame from cache (thread-safe).

        Args:
            frame_index: Frame index to retrieve

        Returns:
            Frame array if found in cache, None otherwise
        """
        with self._lock:
            if frame_index in self._cache:
                self._update_access_order(frame_index)
                return self._cache[frame_index].copy()
        return None

    def put(self, frame_index: int, frame: np.ndarray) -> None:
        """Store a frame in cache (thread-safe).

        If an entry already exists for ``frame_index``, it is replaced so a corrected
        decode cannot leave a stale bitmap stuck under that presentation index.
        """
        with self._lock:
            stored = frame.copy()
            if frame_index in self._cache:
                old_size = self._frame_sizes.get(frame_index, 0)
                new_size = self._calculate_frame_memory(stored)
                self._cache[frame_index] = stored
                self._frame_sizes[frame_index] = new_size
                self._current_memory_bytes += new_size - old_size
                self._update_access_order(frame_index)
                return

            self._evict_if_needed(stored)
            self._cache[frame_index] = stored
            frame_size = self._calculate_frame_memory(stored)
            self._frame_sizes[frame_index] = frame_size
            self._current_memory_bytes += frame_size
            self._access_order[frame_index] = None

    def request_prefill_frame(
        self,
        strategy: PrefillStrategy,
        frame_callback: Callable[[FrameResult], None],
        decoder: VideoDecoder,
    ) -> None:
        """Request prefetching of frames according to strategy.

        This method:
        1. Cancels all pending prefetch requests
        2. Captures the full strategy frame set (for overlap detection)
        3. Fetches the first frame immediately and calls callback
        4. Starts background prefetching of remaining frames

        Args:
            strategy: PrefillStrategy defining which frames to prefetch
            frame_callback: Callback function that receives FrameResult objects
            decoder: VideoDecoder to use for decoding frames
        """
        with self._lock:
            self._cancel_pending_requests()

            self._current_strategy = strategy
            self._current_callback = frame_callback
            self._current_decoder = decoder
            self._current_decoder_metadata_total_frames = decoder.metadata.total_frames

            protected_frames_list: List[int] = []
            frame_generator = strategy.generate_protected_frames()

            for frame_num in frame_generator:
                protected_frames_list.append(frame_num)

            self._protected_frames = protected_frames_list
            self._protected_frames_set = set(protected_frames_list)

        if not protected_frames_list:
            return

        self._sync_event.clear()
        first_frame_num = protected_frames_list[0]
        print_framedebug(
            "FrameCache: request received for first_frame=%d "
            "(total %d frames in request)" % (first_frame_num, len(protected_frames_list))
        )
        first_result = self._fetch_frame_sync(first_frame_num, decoder, False)
        print_framedebug(
            "FrameCache: first frame fulfilled frame_number=%d "
            "status=%s has_frame=%s"
            % (
                first_result.frame_number,
                first_result.status.name,
                first_result.frame is not None,
            )
        )
        frame_callback(first_result)
        print_framedebug("FrameCache: cache callback invoked")

        self._start_prefetch_thread_if_needed()

        for frame_num in protected_frames_list[1:]:
            if self._cancellation_event.is_set():
                break
            self._prefetch_queue.put(frame_num)

        self._prefetch_queue.put(None)

    def invalidate(self) -> None:
        """Clear all cached frames (thread-safe)."""
        with self._lock:
            self._cache.clear()
            self._access_order = OrderedDict()
            self._protected_frames.clear()
            self._protected_frames_set.clear()
            self._frame_sizes.clear()
            self._current_memory_bytes = 0

    def prepare_for_decoder_close(self) -> None:
        """Stop the prefetch thread before closing the paired VideoDecoder (reload path).

        Does not set the permanent shutdown flag; a new request_prefill_frame can start
        a fresh worker thread afterward.
        """
        self._cancellation_event.set()
        self._sync_event.set()
        while True:
            try:
                self._prefetch_queue.get_nowait()
            except queue.Empty:
                break
        if self._prefetch_thread is not None and self._prefetch_thread.is_alive():
            self._prefetch_queue.put(None)
            self._prefetch_thread.join(timeout=15.0)
        self._prefetch_thread = None
        with self._lock:
            self._current_decoder = None
            self._current_callback = None
        self._cancellation_event.clear()
        self._sync_event.clear()

    def close(self) -> None:
        """Permanent shutdown: stop prefetch and clear cache (call before process exit)."""
        self._shutdown_event.set()
        self._sync_event.set()
        with self._lock:
            self._current_decoder = None
            self._current_callback = None
            self._current_strategy = None
        while True:
            try:
                self._prefetch_queue.get_nowait()
            except queue.Empty:
                break
        if self._prefetch_thread is not None and self._prefetch_thread.is_alive():
            self._prefetch_queue.put(None)
            self._prefetch_thread.join(timeout=15.0)
        self._prefetch_thread = None
        self.invalidate()

    def signal_sync_complete(self) -> None:
        """Signal that synchronization is complete and background prefetch worker can proceed.

        This method is called by PlaybackController when both frame caches have delivered
        their first frames. The background prefetch worker waits for this signal before
        processing queued frames, ensuring both videos are synchronized before any
        additional prefetching occurs.

        If called after cancellation (new request arrived), this has no effect as the
        worker has already been cancelled.
        """
        if not self._cancellation_event.is_set():
            self._sync_event.set()

    def _cancel_pending_requests(self) -> None:
        """Cancel all pending prefetch requests."""
        self._cancellation_event.set()
        self._sync_event.set()
        while not self._prefetch_queue.empty():
            try:
                self._prefetch_queue.get_nowait()
            except queue.Empty:
                break
        self._cancellation_event.clear()
        self._sync_event.clear()

    def _start_prefetch_thread_if_needed(self) -> None:
        """Start the background prefetch thread if not already running."""
        if self._prefetch_thread is not None and self._prefetch_thread.is_alive():
            return

        self._prefetch_thread = threading.Thread(target=self._prefetch_worker, daemon=True)
        self._prefetch_thread.start()

    def _prefetch_worker(self) -> None:
        """Background worker thread that processes prefetch queue."""
        while not self._shutdown_event.is_set():
            if not self._sync_event.is_set():
                if not self._sync_event.wait(timeout=0.1):
                    continue

            try:
                frame_num = self._prefetch_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if frame_num is None:
                break

            if self._cancellation_event.is_set():
                continue

            with self._lock:
                decoder = self._current_decoder
                callback = self._current_callback

            if decoder is None or callback is None:
                continue

            self._prefetch_semaphore.acquire()
            try:
                result = self._fetch_frame_sync(frame_num, decoder, True)
            finally:
                self._prefetch_semaphore.release()

            if self._cancellation_event.is_set():
                continue

            # Prefetched frames are only stored in cache; do not invoke the
            # callback. The callback is only for the first frame (delivered
            # synchronously in request_prefill_frame).
            if result.status == FrameRequestStatus.CANCELLED:
                continue
            # SUCCESS: frame already put in cache by _fetch_frame_sync
            # Error statuses: drop; first-frame errors were reported synchronously

    def debug_mark_frame_unique(self, frame: np.ndarray, frame_index: int = 0) -> np.ndarray:
        """Return a copy of the frame with the top-left ninth filled with random pixels.

        The modified region is the intersection of the top third and left third of the
        frame, so each returned frame is visually unique for debugging (e.g. to rule
        out identical decoded frames).

        Args:
            frame: Cached frame array, shape (height, width, 3), dtype uint8.
            frame_index: Optional; if provided, used to seed RNG so the same index
                always gets the same marker (deterministic per frame).

        Returns:
            A copy of the frame with the top-left region overwritten by random RGB.
        """
        out = np.ascontiguousarray(frame.copy())
        h, w = out.shape[0], out.shape[1]
        top_third_h = max(1, h // DEBUG_UNIQUE_FRACTION)
        left_third_w = max(1, w // DEBUG_UNIQUE_FRACTION)
        rng = np.random.default_rng(frame_index)
        out[0:top_third_h, 0:left_third_w, :] = rng.integers(0, 256, (top_third_h, left_third_w, 3), dtype=np.uint8)
        return out

    def _attempt_to_cache_frame(
        self, frame_index: int, decoder: VideoDecoder
    ) -> Tuple[FrameRequestStatus, Optional[Exception]]:
        try:
            with self._decoder_lock:
                decode_result = decoder.decode_frame_operation(frame_index)
            for decoded_frame_index, decoded_frame in decode_result.decoded_frames:
                self.put(decoded_frame_index, decoded_frame)
            return FrameRequestStatus.SUCCESS, None
        except SeekError as e:
            return FrameRequestStatus.SEEK_ERROR, e
        except DecodeError as e:
            return FrameRequestStatus.DECODE_ERROR, e
        except ValueError as e:
            if "out of range" in str(e).lower():
                return FrameRequestStatus.OUT_OF_RANGE, e
            return FrameRequestStatus.DECODE_ERROR, e

    def _fetch_frame_sync(self, frame_index: int, decoder: VideoDecoder, is_prefetch: bool) -> FrameResult:
        """Fetch a frame synchronously, handling all error cases.

        Args:
            frame_index: Frame index to fetch
            decoder: VideoDecoder to use

        Returns:
            FrameResult with appropriate status
        """
        if frame_index < 0 or frame_index >= self._current_decoder_metadata_total_frames:
            return FrameResult(
                frame_number=frame_index,
                frame=None,
                status=FrameRequestStatus.OUT_OF_RANGE,
                error=ValueError(f"Frame index {frame_index} out of range"),
            )

        dec_status: FrameRequestStatus = FrameRequestStatus.SUCCESS
        dec_err: Optional[Exception] = None

        if not self.has_frame(frame_index) or DEBUG_SKIP_CACHE_ENTIRELY:
            if not is_prefetch:
                print_framedebug("CACHE MISS")
            dec_status, dec_err = self._attempt_to_cache_frame(frame_index, decoder)

            if dec_status != FrameRequestStatus.SUCCESS:
                fallback_frame = self._try_tail_decode_fallback(frame_index, dec_status, decoder)
                if fallback_frame is not None:
                    return FrameResult(
                        frame_number=frame_index,
                        frame=self.debug_mark_frame_unique(fallback_frame, frame_index)
                        if DEBUG_FORCE_UNIQUE_FRAMES
                        else fallback_frame,
                        status=FrameRequestStatus.SUCCESS,
                        error=None,
                    )
                return FrameResult(
                    frame_number=frame_index,
                    frame=None,
                    status=dec_status,
                    error=dec_err,
                )

        cached_frame = self.get(frame_index)
        if cached_frame is None:
            raise ValueError("It's not my fault!  cache says it filled but it didn't")

        if self._cancellation_event.is_set():
            return FrameResult(
                frame_number=frame_index,
                frame=None,
                status=FrameRequestStatus.CANCELLED,
                error=None,
            )

        return FrameResult(
            frame_number=frame_index,
            frame=self.debug_mark_frame_unique(cached_frame, frame_index)
            if DEBUG_FORCE_UNIQUE_FRAMES
            else cached_frame,
            status=FrameRequestStatus.SUCCESS,
            error=None,
        )

    def _try_tail_decode_fallback(
        self, frame_index: int, dec_status: FrameRequestStatus, decoder: VideoDecoder
    ) -> Optional[np.ndarray]:
        """For near-EOF decode misses, clamp to nearest decodable trailing frame."""
        if dec_status != FrameRequestStatus.DECODE_ERROR:
            return None
        tail_start = self._current_decoder_metadata_total_frames - 1 - self._TAIL_FALLBACK_MAX_BACKTRACK_FRAMES
        if frame_index < max(0, tail_start):
            return None

        lowest_candidate = max(0, frame_index - self._TAIL_FALLBACK_MAX_BACKTRACK_FRAMES)
        for candidate in range(frame_index - 1, lowest_candidate - 1, -1):
            if self.has_frame(candidate):
                cached = self.get(candidate)
                if cached is not None:
                    return cached
                continue
            status, _err = self._attempt_to_cache_frame(candidate, decoder)
            if status != FrameRequestStatus.SUCCESS:
                continue
            cached = self.get(candidate)
            if cached is not None:
                return cached
        return None

    def _update_access_order(self, frame_index: int) -> None:
        """Update LRU access order for a frame (must be called with lock held).

        Args:
            frame_index: Frame index that was accessed
        """
        if frame_index in self._access_order:
            self._access_order.move_to_end(frame_index)
        else:
            self._access_order[frame_index] = None

    def _evict_if_needed(self, new_frame: np.ndarray) -> None:
        """Evict frames if cache limits are exceeded, using LRU but skipping protected frames (must be called with lock held).

        If all frames are protected and capacity is exceeded, evicts the lowest priority
        (last in sequence) protected frames.

        Args:
            new_frame: New frame being added (for memory calculation)
        """
        new_frame_memory = self._calculate_frame_memory(new_frame)

        while self._current_memory_bytes + new_frame_memory > self.max_memory_bytes:
            if not self._access_order:
                break

            oldest_frame_index = self._find_evictable_frame()
            if oldest_frame_index is None:
                oldest_frame_index = self._find_lowest_priority_protected_frame()
                if oldest_frame_index is None:
                    break

            self._remove_cached_frame(oldest_frame_index)

    def _find_evictable_frame(self) -> Optional[int]:
        """Find the least recently used frame that is not protected (must be called with lock held).

        Returns:
            Frame index to evict, or None if all frames are protected
        """
        if not self._access_order:
            return None
        for frame_index in self._access_order:
            if frame_index not in self._protected_frames_set:
                return frame_index
        return None

    def _find_lowest_priority_protected_frame(self) -> Optional[int]:
        """Find the lowest priority protected frame (last in sequence) that is in cache (must be called with lock held).

        Returns:
            Frame index to evict, or None if no protected frames are cached
        """
        for frame_index in reversed(self._protected_frames):
            if frame_index in self._cache:
                return frame_index
        return None

    def _calculate_frame_memory(self, frame: np.ndarray) -> int:
        """Calculate memory usage of a frame in bytes.

        Args:
            frame: Frame array

        Returns:
            Memory usage in bytes
        """
        return frame.nbytes

    def _calculate_total_memory(self) -> int:
        """Calculate total memory usage of cached frames in bytes (must be called with lock held).

        Returns:
            Total memory usage in bytes
        """
        return self._current_memory_bytes

    def _remove_cached_frame(self, frame_index: int) -> None:
        """Remove a frame and all related bookkeeping (must be called with lock held)."""
        if frame_index in self._cache:
            del self._cache[frame_index]
        if frame_index in self._access_order:
            del self._access_order[frame_index]
        frame_size = self._frame_sizes.pop(frame_index, 0)
        self._current_memory_bytes = max(0, self._current_memory_bytes - frame_size)
        if frame_index in self._protected_frames_set:
            self._protected_frames_set.remove(frame_index)
            self._protected_frames = [idx for idx in self._protected_frames if idx != frame_index]

    def num_entries(self) -> int:
        """Return the number of frames currently stored in the cache (thread-safe)."""
        with self._lock:
            return len(self._cache)

    def cache_size(self) -> int:
        """Return the total space used by the cache in bytes (thread-safe)."""
        with self._lock:
            return self._current_memory_bytes

    def num_free_entries(self) -> int:
        """Return the number of additional frames that can be inserted before exceeding memory limit (thread-safe).

        This estimate is based on the current available bytes and the average size of cached frames.
        If no frames are cached, returns float('inf').
        """
        with self._lock:
            total_bytes_used = self._calculate_total_memory()
            available_bytes = self.max_memory_bytes - total_bytes_used

            if self._cache:
                avg_frame_bytes = total_bytes_used / len(self._cache)
            else:
                denominator = self.frame_size_estimate_bytes or self.max_memory_bytes
                avg_frame_bytes = available_bytes / denominator

            return int(available_bytes // avg_frame_bytes)

    def get_missing_frames(self, frame_indices: Set[int]) -> Set[int]:
        """Get frame indices that are not currently cached (thread-safe).

        Args:
            frame_indices: Set of frame indices to check

        Returns:
            Set of frame indices that are not in the cache
        """
        with self._lock:
            return frame_indices - set(self._cache.keys())

    def has_frame(self, frame_index: int) -> bool:
        """Check if a frame is currently cached (thread-safe).

        Args:
            frame_index: Frame index to check

        Returns:
            True if the frame is cached, False otherwise
        """
        with self._lock:
            return frame_index in self._cache
