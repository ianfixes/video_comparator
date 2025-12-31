"""Frame cache with LRU eviction and protected frames.

Responsibilities:
- Frame storage and retrieval
- LRU eviction policy
- Memory bounds management
- Integration with PrefillStrategy to protect frames from eviction
"""

import math
from typing import Dict, List, Optional, Set

import numpy as np

from video_comparator.cache.prefill_strategy import PrefillStrategy
from video_comparator.media.video_metadata import VideoMetadata


class FrameCache:
    """Caches decoded video frames for fast access."""

    def __init__(
        self,
        max_memory_mb: int = 100,
        frame_size_estimate_bytes: Optional[int] = None,
    ) -> None:
        """Initialize frame cache with size and memory limits.

        Args:
            max_frames: Maximum number of frames to cache
            max_memory_mb: Maximum memory usage in megabytes
        """
        if max_memory_mb <= 0:
            raise ValueError(f"max_memory_mb must be > 0, got {max_memory_mb}")

        if frame_size_estimate_bytes is not None and frame_size_estimate_bytes <= 0:
            raise ValueError(f"frame_size_estimate_bytes must be > 0, got {frame_size_estimate_bytes}")

        self.max_memory_bytes: int = max_memory_mb * 1024 * 1024
        self.frame_size_estimate_bytes: Optional[int] = frame_size_estimate_bytes
        self.cache: Dict[int, np.ndarray] = {}
        self.access_order: List[int] = []
        self.prefill_strategy: Optional[PrefillStrategy] = None
        self.protected_frames: Optional[Set[int]] = None

    def get(self, frame_index: int) -> Optional[np.ndarray]:
        """Retrieve a frame from cache.

        Args:
            frame_index: Frame index to retrieve

        Returns:
            Frame array if found in cache, None otherwise
        """
        if frame_index in self.cache:
            self._update_access_order(frame_index)
            return self.cache[frame_index]
        return None

    def put(self, frame_index: int, frame: np.ndarray) -> None:
        """Store a frame in cache.

        Args:
            frame_index: Frame index
            frame: Frame array to store
        """
        if frame_index in self.cache:
            self._update_access_order(frame_index)
            return

        self._evict_if_needed(frame)
        self.cache[frame_index] = frame
        self.access_order.append(frame_index)

    def set_prefill_strategy(self, strategy: Optional[PrefillStrategy]) -> None:
        """Set the prefill strategy that defines protected frames.

        Args:
            strategy: PrefillStrategy instance, or None to disable protection
        """
        self.prefill_strategy = strategy
        self.protected_frames = None  # reset the protected frames set

    def invalidate(self) -> None:
        """Clear all cached frames."""
        self.cache.clear()
        self.access_order.clear()

    def _ensure_protected_frames(self) -> None:
        """Ensure the protected frames set is initialized."""
        if self.protected_frames is None:
            self.protected_frames = (
                set() if self.prefill_strategy is None else self.prefill_strategy.get_protected_frames()
            )

    def _update_access_order(self, frame_index: int) -> None:
        """Update LRU access order for a frame.

        Args:
            frame_index: Frame index that was accessed
        """
        if frame_index in self.access_order:
            self.access_order.remove(frame_index)
        self.access_order.append(frame_index)

    def _evict_if_needed(self, new_frame: np.ndarray) -> None:
        """Evict frames if cache limits are exceeded, using LRU but skipping protected frames.

        Args:
            new_frame: New frame being added (for memory calculation)
        """
        new_frame_memory = self._calculate_frame_memory(new_frame)

        while self._calculate_total_memory() + new_frame_memory > self.max_memory_bytes:
            if not self.access_order:
                break

            oldest_frame_index = self._find_evictable_frame()
            if oldest_frame_index is None:
                break

            if oldest_frame_index in self.cache:
                del self.cache[oldest_frame_index]
            if oldest_frame_index in self.access_order:
                self.access_order.remove(oldest_frame_index)

    def _get_protected_frames(self) -> Set[int]:
        """Get the set of protected frames from the prefill strategy.

        Returns:
            Set of protected frame indices, empty if no strategy is set
        """
        return set() if self.prefill_strategy is None else self.prefill_strategy.get_protected_frames()

    def _find_evictable_frame(self) -> Optional[int]:
        """Find the least recently used frame that is not protected.

        Args:
            protected_frames: Set of frame indices that should not be evicted

        Returns:
            Frame index to evict, or None if all frames are protected
        """
        self._ensure_protected_frames()
        if not self.access_order:
            return None
        for frame_index in self.access_order:
            if frame_index not in self.protected_frames:  # type: ignore
                return frame_index
        # All frames are protected; evict the least recently used one anyway
        return self.access_order[0]

    def _calculate_frame_memory(self, frame: np.ndarray) -> int:
        """Calculate memory usage of a frame in bytes.

        Args:
            frame: Frame array

        Returns:
            Memory usage in bytes
        """
        return frame.nbytes

    def _calculate_total_memory(self) -> int:
        """Calculate total memory usage of cached frames in bytes.

        Returns:
            Total memory usage in bytes
        """
        return sum(self._calculate_frame_memory(frame) for frame in self.cache.values())

    def num_entries(self) -> int:
        """Return the number of frames currently stored in the cache."""
        return len(self.cache)

    def cache_size(self) -> int:
        """Return the total space used by the cache in bytes."""
        return sum(self._calculate_frame_memory(frame) for frame in self.cache.values())

    def num_free_entries(self) -> int:
        """Return the number of additional frames that can be inserted before exceeding memory limit.

        This estimate is based on the current available bytes and the average size of cached frames.
        If no frames are cached, returns float('inf').
        """
        total_bytes_used = self.cache_size()
        available_bytes = self.max_memory_bytes - total_bytes_used

        if self.cache:
            avg_frame_bytes = total_bytes_used / len(self.cache)
        else:
            denominator = self.frame_size_estimate_bytes or self.max_memory_bytes
            avg_frame_bytes = available_bytes / denominator

        return int(available_bytes // avg_frame_bytes)

    def get_missing_frames(self, frame_indices: Set[int]) -> Set[int]:
        """Get frame indices that are not currently cached.

        Args:
            frame_indices: Set of frame indices to check

        Returns:
            Set of frame indices that are not in the cache
        """
        return frame_indices - set(self.cache.keys())

    def has_frame(self, frame_index: int) -> bool:
        """Check if a frame is currently cached.

        Args:
            frame_index: Frame index to check

        Returns:
            True if the frame is cached, False otherwise
        """
        return frame_index in self.cache
