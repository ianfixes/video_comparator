from typing import Optional

from video_comparator.common.types import LayoutOrientation, ScalingMode
from video_comparator.config.settings import Settings


class SettingsManager:
    """Manages application settings and persistence."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize settings manager with optional config file path."""
        self.config_path: Optional[str] = config_path
        self.settings: Settings = Settings(
            recent_files=[],
            layout_orientation=LayoutOrientation.HORIZONTAL,
            scaling_mode=ScalingMode.INDEPENDENT,
            default_zoom=1.0,
            shortcut_overrides={},
        )
