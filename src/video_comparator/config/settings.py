"""Configuration and settings management.

Responsibilities:
- Persist recent files
- Last layout preferences
- Zoom defaults
- Shortcut overrides
- Keep optional to avoid startup fragility
"""

from typing import List, Optional

from video_comparator.common.types import LayoutOrientation, ScalingMode


class Settings:
    """Application settings data structure."""

    def __init__(
        self,
        recent_files: List[str],
        layout_orientation: LayoutOrientation,
        scaling_mode: ScalingMode,
        default_zoom: float,
        shortcut_overrides: dict,
    ) -> None:
        """Initialize settings with provided values."""
        self.recent_files: List[str] = recent_files
        self.layout_orientation: LayoutOrientation = layout_orientation
        self.scaling_mode: ScalingMode = scaling_mode
        self.default_zoom: float = default_zoom
        self.shortcut_overrides: dict = shortcut_overrides
