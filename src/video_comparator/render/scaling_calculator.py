"""Scaling and transform calculations.

Responsibilities:
- Transform math for pan/zoom/fit calculations
- Scaling mode logic (independent fit vs. match larger video)
- Coordinate transformations between video space and display space
"""

from typing import Optional, Tuple

from video_comparator.common.types import ScalingMode


class ScalingCalculator:
    """Calculates scaling and transform matrices for video display."""

    def __init__(self) -> None:
        """Initialize scaling calculator."""
        pass

    def calculate_scale(
        self,
        video_size: Tuple[int, int],
        display_size: Tuple[int, int],
        scaling_mode: ScalingMode,
        reference_size: Optional[Tuple[int, int]] = None,
    ) -> Tuple[float, float]:
        """Calculate scale factors for video display.

        Args:
            video_size: (width, height) of video
            display_size: (width, height) of display area
            scaling_mode: ScalingMode enum value
            reference_size: Optional reference size for match_larger mode

        Returns:
            (scale_x, scale_y) tuple
        """
        return (1.0, 1.0)  # TODO: Implement actual scaling logic
