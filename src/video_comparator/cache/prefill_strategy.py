"""Prefill strategy for frame cache.

Responsibilities:
- Define which frames should be protected from cache eviction
- Generate frame numbers in priority order (does not need to know cache size)
- Swappable strategy pattern for different prefetching approaches
"""

from abc import ABC, abstractmethod
from typing import Dict, Generator, Iterator, Optional


class PrefillStrategy(ABC):
    """Abstract base class for prefill strategies.

    Prefill strategies generate frame numbers in priority order. The FrameCache
    consumes frames from the generator until it reaches capacity, and those
    consumed frames become the protected set. This design allows strategies to
    focus on priority ordering without needing to know cache capacity in advance.
    """

    class FramesNotGeneratedError(Exception):
        """Exception raised when protected frames have not been generated yet."""

    _cacheable_frame_count: Optional[int] = None

    @property
    def cacheable_frame_count(self) -> Optional[int]:
        """Read-only access to the number of cacheable frames."""
        return self._cacheable_frame_count

    @abstractmethod
    def _generate_protected_frames(self) -> Generator[int, None, None]:
        """Generate frame indices in priority order for protection.

        Yields frame indices in order of priority (most important first).
        The FrameCache will consume frames until it reaches capacity.
        Strategies do not need to know or respect cache capacity.

        Frame order must be deterministic and consistent.

        Yields:
            Frame indices in priority order
        """
        pass

    def generate_protected_frames(self) -> Generator[int, None, None]:
        """
        Generate frame indices in priority order for protection.
        The FrameCache will consume frames until it reaches capacity.
        Strategies do not need to know or respect cache capacity.

        Frame order must be deterministic and consistent.

        Yields:
            Frame indices in priority order
        """
        self._cacheable_frame_count = 0

        for frame_num in self._generate_protected_frames():
            self._cacheable_frame_count += 1
            yield frame_num

    def _protected_frames(self) -> Dict[int, None]:
        """
        Return the set of protected frames.
        Implemented as a dict to guarantee deterministic order, as Python does not guarantee order of sets.
        """
        if self._cacheable_frame_count is None:
            raise self.FramesNotGeneratedError()

        # Naive/safe implementation: generate them again since it's deterministic
        return dict.fromkeys(
            x for i, x in enumerate(self._generate_protected_frames()) if i < self._cacheable_frame_count
        )

    def protected_frames(self) -> Dict[int, None]:
        """
        Return the set of protected frames if it has been generated
        """
        if self._cacheable_frame_count is None:
            raise self.FramesNotGeneratedError()

        # Naive/safe implementation: generate them again since it's deterministic
        return self._protected_frames()

    def is_protected_frame(self, frame_num: int) -> bool:
        """Check if a specific frame is in the protected set.

        This is a convenience method. The actual protected set is determined
        by FrameCache consuming frames from generate_protected_frames().

        Args:
            frame_num: Frame index to check
            protected_set: The set of protected frames (from FrameCache)

        Returns:
            True if the frame is in the protected set, False otherwise
        """
        if self._cacheable_frame_count is None:
            raise self.FramesNotGeneratedError()
        # Naive/safe implementation: generate a set every time
        return frame_num in self.protected_frames()


class TrivialPrefillStrategy(PrefillStrategy):
    """Trivial prefill strategy that yields frames from a provided sequence."""

    def __init__(self, frame_sequence: Iterator[int]) -> None:
        """
        Initialize with a sequence of frame indices, preserving insertion order and uniqueness.

        Args:
            frame_sequence: Iterable of frame indices (any order, may have duplicates)
        """
        self.frame_sequence: Dict[int, None] = dict.fromkeys(frame_sequence)

    def _generate_protected_frames(self) -> Generator[int, None, None]:
        """Generate frame indices from the provided sequence."""
        yield from self.frame_sequence.keys()

    def _protected_frames(self) -> Dict[int, None]:
        """Return the set of protected frames."""
        if self._cacheable_frame_count is None:
            raise self.FramesNotGeneratedError()

        frame_keys = list(self.frame_sequence.keys())
        return dict.fromkeys(frame_keys[: self._cacheable_frame_count])
