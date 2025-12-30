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
            (scale_x, scale_y) tuple - both values are equal to preserve aspect ratio

        Raises:
            ValueError: If video_size or display_size has invalid dimensions
            ValueError: If match_larger mode is used without reference_size
        """
        video_width, video_height = video_size
        display_width, display_height = display_size

        if video_width <= 0 or video_height <= 0:
            raise ValueError(f"video_size must have positive dimensions, got {video_size}")
        if display_width <= 0 or display_height <= 0:
            raise ValueError(f"display_size must have positive dimensions, got {display_size}")

        if scaling_mode == ScalingMode.INDEPENDENT:
            scale_x = display_width / video_width
            scale_y = display_height / video_height
            scale = min(scale_x, scale_y)
            return (scale, scale)
        elif scaling_mode == ScalingMode.MATCH_LARGER:
            if reference_size is None:
                raise ValueError("reference_size is required for MATCH_LARGER scaling mode")
            ref_width, ref_height = reference_size
            if ref_width <= 0 or ref_height <= 0:
                raise ValueError(f"reference_size must have positive dimensions, got {reference_size}")

            scale_x = ref_width / video_width
            scale_y = ref_height / video_height
            scale = min(scale_x, scale_y)
            return (scale, scale)
        else:
            raise ValueError(f"Unknown scaling mode: {scaling_mode}")

    def video_to_display(
        self,
        video_point: Tuple[float, float],
        scale: Tuple[float, float],
        pan_offset: Tuple[float, float] = (0.0, 0.0),
    ) -> Tuple[float, float]:
        """Transform coordinates from video space to display space.

        Args:
            video_point: (x, y) coordinates in video space
            scale: (scale_x, scale_y) scaling factors
            pan_offset: (offset_x, offset_y) pan offset in display space

        Returns:
            (x, y) coordinates in display space
        """
        x, y = video_point
        scale_x, scale_y = scale
        offset_x, offset_y = pan_offset
        return (x * scale_x + offset_x, y * scale_y + offset_y)

    def display_to_video(
        self,
        display_point: Tuple[float, float],
        scale: Tuple[float, float],
        pan_offset: Tuple[float, float] = (0.0, 0.0),
    ) -> Tuple[float, float]:
        """Transform coordinates from display space to video space.

        Args:
            display_point: (x, y) coordinates in display space
            scale: (scale_x, scale_y) scaling factors
            pan_offset: (offset_x, offset_y) pan offset in display space

        Returns:
            (x, y) coordinates in video space
        """
        x, y = display_point
        scale_x, scale_y = scale
        offset_x, offset_y = pan_offset
        return ((x - offset_x) / scale_x, (y - offset_y) / scale_y)
