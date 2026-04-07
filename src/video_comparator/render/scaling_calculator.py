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

    @staticmethod
    def adjust_pan_for_zoom_at_anchor(
        pane_width: int,
        pane_height: int,
        video_width: int,
        video_height: int,
        base_scale: float,
        old_zoom: float,
        new_zoom: float,
        old_pan_x: float,
        old_pan_y: float,
        anchor_x: float,
        anchor_y: float,
    ) -> Tuple[float, float]:
        """Compute new pan so the video pixel under ``anchor`` stays fixed when zoom changes.

        Layout matches ``VideoPane`` rendering: the fitted bitmap is centered in the pane
        with optional ``pan`` offset, then scaled by ``base_scale * zoom``.
        """
        if old_zoom <= 0:
            raise ValueError("old_zoom must be positive")
        if video_width <= 0 or video_height <= 0:
            raise ValueError("video dimensions must be positive")
        sw0 = video_width * base_scale * old_zoom
        sh0 = video_height * base_scale * old_zoom
        sw1 = video_width * base_scale * new_zoom
        sh1 = video_height * base_scale * new_zoom
        draw_x0 = (pane_width - sw0) / 2.0 + old_pan_x
        draw_y0 = (pane_height - sh0) / 2.0 + old_pan_y
        ox = anchor_x - draw_x0
        oy = anchor_y - draw_y0
        ratio = new_zoom / old_zoom
        ox_new = ox * ratio
        oy_new = oy * ratio
        new_pan_x = anchor_x - (pane_width - sw1) / 2.0 - ox_new
        new_pan_y = anchor_y - (pane_height - sh1) / 2.0 - oy_new
        return (new_pan_x, new_pan_y)

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
