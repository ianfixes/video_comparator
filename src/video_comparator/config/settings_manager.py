import json
import os
from pathlib import Path
from typing import Optional

from video_comparator.common.types import LayoutOrientation, ScalingMode
from video_comparator.config.settings import Settings


class SettingsManager:
    """Manages application settings and persistence."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize settings manager with optional config file path.

        Args:
            config_path: Optional path to settings file. If None, uses default
                location: ~/.config/video_comparator/settings.json
        """
        if config_path is None:
            config_path = self._get_default_config_path()
        self.config_path: str = config_path
        self.settings: Settings = self._create_default_settings()

    @staticmethod
    def _get_default_config_path() -> str:
        """Get default configuration file path.

        Returns:
            Path to default settings file following XDG config directory spec
        """
        home = Path.home()
        config_dir = home / ".config" / "video_comparator"
        return str(config_dir / "settings.json")

    @staticmethod
    def _create_default_settings() -> Settings:
        """Create default settings instance.

        Returns:
            Settings instance with default values
        """
        return Settings(
            recent_files=[],
            layout_orientation=LayoutOrientation.HORIZONTAL,
            scaling_mode=ScalingMode.INDEPENDENT,
            default_zoom=1.0,
            shortcut_overrides={},
        )

    def load(self) -> Settings:
        """Load settings from file.

        If the file doesn't exist or is corrupted, returns default settings
        without raising an exception.

        Returns:
            Settings instance loaded from file or defaults if file is missing/corrupted
        """
        if not os.path.exists(self.config_path):
            self.settings = self._create_default_settings()
            return self.settings

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.settings = Settings.from_dict(data)
            return self.settings
        except (OSError, json.JSONDecodeError, ValueError) as e:
            self.settings = self._create_default_settings()
            return self.settings

    def save(self) -> None:
        """Save current settings to file.

        Creates parent directories if they don't exist.
        Raises OSError if file cannot be written.
        """
        config_file = Path(self.config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)

        data = self.settings.to_dict()
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_settings(self) -> Settings:
        """Get current settings instance.

        Returns:
            Current Settings instance
        """
        return self.settings

    def update_settings(self, settings: Settings) -> None:
        """Update current settings.

        Args:
            settings: New Settings instance to use
        """
        self.settings = settings
