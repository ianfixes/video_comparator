"""Frame cache with prebuffering.

Responsibilities:
- Small ring buffer ahead/behind current position to minimize seek latency
- Eviction policy
- Memory bounds management
"""

from typing import Dict, Optional

import numpy as np


class FrameCache:
    """Caches decoded video frames for fast access."""

    def __init__(self, max_frames: int = 10, max_memory_mb: int = 100) -> None:
        """Initialize frame cache with size and memory limits."""
        self.max_frames: int = max_frames
        self.max_memory_mb: int = max_memory_mb
        self.cache: Dict[int, np.ndarray] = {}
        self.current_position: int = 0
