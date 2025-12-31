"""Prefill strategy for frame cache.

Responsibilities:
- Define which frames should be protected from cache eviction
- Provide protected frame set based on prediction logic
- Swappable strategy pattern for different prefetching approaches
"""

from abc import ABC, abstractmethod
from typing import Set


class PrefillStrategy(ABC):
    """Abstract base class for prefill strategies.

    Prefill strategies define which frames should be protected from eviction
    in the frame cache. The strategy is updated when the target frame changes,
    and the cache uses it to determine which frames to preserve during LRU eviction.
    """

    @abstractmethod
    def get_protected_frames(self) -> Set[int]:
        """Get the set of frame indices that should be protected from eviction.

        Returns:
            Set of frame indices that should not be evicted from the cache
        """
        pass

    @abstractmethod
    def is_protected_frame(self, frame_num: int) -> bool:
        """Check if a specific frame should be protected from eviction.

        Args:
            frame_num: Frame index to check

        Returns:
            True if the frame should be protected, False otherwise
        """
        pass


class TrivialPrefillStrategy(PrefillStrategy):
    """Trivial prefill strategy that takes the set of frames as input."""

    def __init__(self, protected_frames: Set[int]) -> None:
        self.protected_frames = protected_frames

    def get_protected_frames(self) -> Set[int]:
        """Get the set of frame indices that should be protected from eviction."""
        return set(self.protected_frames)

    def is_protected_frame(self, frame_num: int) -> bool:
        """Check if a specific frame should be protected from eviction."""
        return frame_num in self.protected_frames
