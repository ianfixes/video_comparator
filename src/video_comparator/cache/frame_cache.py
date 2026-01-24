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
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Set

import numpy as np

from video_comparator.cache.frame_result import FrameResult
from video_comparator.cache.prefill_strategy import PrefillStrategy
from video_comparator.common.types import FrameRequestStatus

if TYPE_CHECKING:
    from video_comparator.decode.video_decoder import DecodeError, SeekError, VideoDecoder


class FrameCache:
    """Thread-safe frame cache with autonomous background prefetching."""

    _prefetch_coordination_semaphore: Optional[threading.Semaphore] = None
    _prefetch_coordination_lock = threading.Lock()

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
        self._access_order: List[int] = []
        self._protected_frames: List[int] = []
        self._protected_frames_set: Set[int] = set()
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
        self._prefetch_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

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

        Args:
            frame_index: Frame index
            frame: Frame array to store
        """
        with self._lock:
            if frame_index in self._cache:
                self._update_access_order(frame_index)
                return

            self._evict_if_needed(frame)
            self._cache[frame_index] = frame.copy()
            self._access_order.append(frame_index)

    def request_prefill_frame(
        self,
        strategy: PrefillStrategy,
        frame_callback: Callable[[FrameResult], None],
        decoder: "VideoDecoder",
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

        first_frame_num = protected_frames_list[0]
        first_result = self._fetch_frame_sync(first_frame_num, decoder)
        frame_callback(first_result)

        if first_result.status != FrameRequestStatus.SUCCESS:
            return

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
            self._access_order.clear()
            self._protected_frames.clear()
            self._protected_frames_set.clear()

    def close(self) -> None:
        """Shutdown the cache and stop background prefetching."""
        self._shutdown_event.set()
        self._cancel_pending_requests()

        if self._prefetch_thread is not None and self._prefetch_thread.is_alive():
            self._prefetch_queue.put(None)
            self._prefetch_thread.join(timeout=5.0)

    def signal_sync_complete(self) -> None:
        """Signal that synchronization is complete and background prefetch worker can proceed.

        This method is called by PlaybackController when both frame caches have delivered
        their first frames. The background prefetch worker waits for this signal before
        processing queued frames, ensuring both videos are synchronized before any
        additional prefetching occurs.

        If called after cancellation (new request arrived), this has no effect as the
        worker has already been cancelled.
        """
        pass

    def _cancel_pending_requests(self) -> None:
        """Cancel all pending prefetch requests."""
        self._cancellation_event.set()
        while not self._prefetch_queue.empty():
            try:
                self._prefetch_queue.get_nowait()
            except queue.Empty:
                break
        self._cancellation_event.clear()

    def _start_prefetch_thread_if_needed(self) -> None:
        """Start the background prefetch thread if not already running."""
        if self._prefetch_thread is not None and self._prefetch_thread.is_alive():
            return

        self._prefetch_thread = threading.Thread(target=self._prefetch_worker, daemon=True)
        self._prefetch_thread.start()

    def _prefetch_worker(self) -> None:
        """Background worker thread that processes prefetch queue."""
        while not self._shutdown_event.is_set():
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
                result = self._fetch_frame_sync(frame_num, decoder)
            finally:
                self._prefetch_semaphore.release()

            if self._cancellation_event.is_set():
                continue

            if result.status == FrameRequestStatus.SUCCESS:
                if not self._cancellation_event.is_set() and callback is not None:
                    callback(result)
            elif result.status == FrameRequestStatus.CANCELLED:
                continue
            else:
                if not self._cancellation_event.is_set() and callback is not None:
                    callback(result)

    def _fetch_frame_sync(self, frame_index: int, decoder: "VideoDecoder") -> FrameResult:
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

        cached_frame = self.get(frame_index)
        if cached_frame is not None:
            return FrameResult(
                frame_number=frame_index,
                frame=cached_frame,
                status=FrameRequestStatus.SUCCESS,
                error=None,
            )

        try:
            frame = decoder.decode_frame(frame_index)
            self.put(frame_index, frame)
            if self._cancellation_event.is_set():
                return FrameResult(
                    frame_number=frame_index,
                    frame=None,
                    status=FrameRequestStatus.CANCELLED,
                    error=None,
                )
            return FrameResult(
                frame_number=frame_index,
                frame=frame,
                status=FrameRequestStatus.SUCCESS,
                error=None,
            )
        except SeekError as e:
            return FrameResult(
                frame_number=frame_index,
                frame=None,
                status=FrameRequestStatus.SEEK_ERROR,
                error=e,
            )
        except DecodeError as e:
            return FrameResult(
                frame_number=frame_index,
                frame=None,
                status=FrameRequestStatus.DECODE_ERROR,
                error=e,
            )
        except ValueError as e:
            if "out of range" in str(e).lower():
                return FrameResult(
                    frame_number=frame_index,
                    frame=None,
                    status=FrameRequestStatus.OUT_OF_RANGE,
                    error=e,
                )
            return FrameResult(
                frame_number=frame_index,
                frame=None,
                status=FrameRequestStatus.DECODE_ERROR,
                error=e,
            )

    def _update_access_order(self, frame_index: int) -> None:
        """Update LRU access order for a frame (must be called with lock held).

        Args:
            frame_index: Frame index that was accessed
        """
        if frame_index in self._access_order:
            self._access_order.remove(frame_index)
        self._access_order.append(frame_index)

    def _evict_if_needed(self, new_frame: np.ndarray) -> None:
        """Evict frames if cache limits are exceeded, using LRU but skipping protected frames (must be called with lock held).

        If all frames are protected and capacity is exceeded, evicts the lowest priority
        (last in sequence) protected frames.

        Args:
            new_frame: New frame being added (for memory calculation)
        """
        new_frame_memory = self._calculate_frame_memory(new_frame)

        while self._calculate_total_memory() + new_frame_memory > self.max_memory_bytes:
            if not self._access_order:
                break

            oldest_frame_index = self._find_evictable_frame()
            if oldest_frame_index is None:
                oldest_frame_index = self._find_lowest_priority_protected_frame()
                if oldest_frame_index is None:
                    break

            if oldest_frame_index in self._cache:
                del self._cache[oldest_frame_index]
            if oldest_frame_index in self._access_order:
                self._access_order.remove(oldest_frame_index)
            if oldest_frame_index in self._protected_frames_set:
                self._protected_frames.remove(oldest_frame_index)
                self._protected_frames_set.remove(oldest_frame_index)

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
        return sum(self._calculate_frame_memory(frame) for frame in self._cache.values())

    def num_entries(self) -> int:
        """Return the number of frames currently stored in the cache (thread-safe)."""
        with self._lock:
            return len(self._cache)

    def cache_size(self) -> int:
        """Return the total space used by the cache in bytes (thread-safe)."""
        with self._lock:
            return sum(self._calculate_frame_memory(frame) for frame in self._cache.values())

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
