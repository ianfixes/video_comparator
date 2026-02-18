"""Unit tests for SettingsManager class."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

from video_comparator.common.types import LayoutOrientation, ScalingMode
from video_comparator.config.settings import Settings
from video_comparator.config.settings_manager import SettingsManager


class TestSettingsManager(unittest.TestCase):
    """Test cases for SettingsManager class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_config_path = os.path.join(self.temp_dir, "test_settings.json")

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_initialization_with_custom_path(self) -> None:
        """Test SettingsManager initialization with custom config path."""
        manager = SettingsManager(config_path=self.test_config_path)

        self.assertEqual(manager.config_path, self.test_config_path)
        self.assertIsInstance(manager.settings, Settings)

    def test_initialization_with_default_path(self) -> None:
        """Test SettingsManager initialization uses default config path."""
        manager = SettingsManager()

        self.assertIsNotNone(manager.config_path)
        self.assertIn(".config", manager.config_path)
        self.assertIn("video_comparator", manager.config_path)
        self.assertIn("settings.json", manager.config_path)
        self.assertIsInstance(manager.settings, Settings)

    def test_default_settings_creation(self) -> None:
        """Test default settings creation."""
        manager = SettingsManager(config_path=self.test_config_path)

        settings = manager.get_settings()
        self.assertEqual(settings.recent_files, [])
        self.assertEqual(settings.layout_orientation, LayoutOrientation.HORIZONTAL)
        self.assertEqual(settings.scaling_mode, ScalingMode.INDEPENDENT)
        self.assertEqual(settings.default_zoom, 1.0)
        self.assertEqual(settings.shortcut_overrides, {})

    def test_load_from_valid_file(self) -> None:
        """Test settings loading from valid file."""
        data = {
            "recent_files": ["/path/to/video1.mp4", "/path/to/video2.mkv"],
            "layout_orientation": "vertical",
            "scaling_mode": "match_larger",
            "default_zoom": 2.5,
            "shortcut_overrides": {"play": "Space"},
        }

        with open(self.test_config_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        manager = SettingsManager(config_path=self.test_config_path)
        settings = manager.load()

        self.assertEqual(settings.recent_files, ["/path/to/video1.mp4", "/path/to/video2.mkv"])
        self.assertEqual(settings.layout_orientation, LayoutOrientation.VERTICAL)
        self.assertEqual(settings.scaling_mode, ScalingMode.MATCH_LARGER)
        self.assertEqual(settings.default_zoom, 2.5)
        self.assertEqual(settings.shortcut_overrides, {"play": "Space"})

    def test_load_from_missing_file_uses_defaults(self) -> None:
        """Test settings loading from missing file uses defaults."""
        manager = SettingsManager(config_path=self.test_config_path)
        settings = manager.load()

        self.assertEqual(settings.recent_files, [])
        self.assertEqual(settings.layout_orientation, LayoutOrientation.HORIZONTAL)
        self.assertEqual(settings.scaling_mode, ScalingMode.INDEPENDENT)
        self.assertEqual(settings.default_zoom, 1.0)
        self.assertEqual(settings.shortcut_overrides, {})

    def test_load_from_corrupted_file_uses_defaults(self) -> None:
        """Test settings loading from corrupted JSON file uses defaults."""
        with open(self.test_config_path, "w", encoding="utf-8") as f:
            f.write("invalid json content {")

        manager = SettingsManager(config_path=self.test_config_path)
        settings = manager.load()

        self.assertEqual(settings.recent_files, [])
        self.assertEqual(settings.layout_orientation, LayoutOrientation.HORIZONTAL)
        self.assertEqual(settings.scaling_mode, ScalingMode.INDEPENDENT)
        self.assertEqual(settings.default_zoom, 1.0)

    def test_load_from_file_with_invalid_enum_uses_defaults(self) -> None:
        """Test settings loading from file with invalid enum values uses defaults."""
        data = {
            "layout_orientation": "invalid_orientation",
            "scaling_mode": "invalid_mode",
        }

        with open(self.test_config_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        manager = SettingsManager(config_path=self.test_config_path)
        settings = manager.load()

        self.assertEqual(settings.layout_orientation, LayoutOrientation.HORIZONTAL)
        self.assertEqual(settings.scaling_mode, ScalingMode.INDEPENDENT)

    def test_load_from_file_with_invalid_zoom_uses_defaults(self) -> None:
        """Test settings loading from file with invalid zoom uses defaults."""
        data = {
            "layout_orientation": "horizontal",
            "scaling_mode": "independent",
            "default_zoom": -1.0,
        }

        with open(self.test_config_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        manager = SettingsManager(config_path=self.test_config_path)
        settings = manager.load()

        self.assertEqual(settings.default_zoom, 1.0)

    def test_save_to_file(self) -> None:
        """Test settings saving to file."""
        manager = SettingsManager(config_path=self.test_config_path)
        manager.settings = Settings(
            recent_files=["/path/to/video1.mp4"],
            layout_orientation=LayoutOrientation.VERTICAL,
            scaling_mode=ScalingMode.MATCH_LARGER,
            default_zoom=2.0,
            shortcut_overrides={"play": "Space"},
        )

        manager.save()

        self.assertTrue(os.path.exists(self.test_config_path))

        with open(self.test_config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["recent_files"], ["/path/to/video1.mp4"])
        self.assertEqual(data["layout_orientation"], "vertical")
        self.assertEqual(data["scaling_mode"], "match_larger")
        self.assertEqual(data["default_zoom"], 2.0)
        self.assertEqual(data["shortcut_overrides"], {"play": "Space"})

    def test_save_creates_parent_directories(self) -> None:
        """Test settings save creates parent directories if they don't exist."""
        nested_path = os.path.join(self.temp_dir, "nested", "dir", "settings.json")
        manager = SettingsManager(config_path=nested_path)

        manager.save()

        self.assertTrue(os.path.exists(nested_path))

    def test_settings_validation_on_load(self) -> None:
        """Test settings validation on load."""
        data = {
            "layout_orientation": "horizontal",
            "scaling_mode": "independent",
            "default_zoom": 0.0,
        }

        with open(self.test_config_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        manager = SettingsManager(config_path=self.test_config_path)
        settings = manager.load()

        self.assertEqual(settings.default_zoom, 1.0)

    def test_enum_value_deserialization(self) -> None:
        """Test enum value deserialization from file."""
        for layout_orientation in LayoutOrientation:
            for scaling_mode in ScalingMode:
                data = {
                    "layout_orientation": layout_orientation.value,
                    "scaling_mode": scaling_mode.value,
                }

                with open(self.test_config_path, "w", encoding="utf-8") as f:
                    json.dump(data, f)

                manager = SettingsManager(config_path=self.test_config_path)
                settings = manager.load()

                self.assertEqual(settings.layout_orientation, layout_orientation)
                self.assertEqual(settings.scaling_mode, scaling_mode)

    def test_get_settings_returns_current_settings(self) -> None:
        """Test get_settings returns current settings instance."""
        manager = SettingsManager(config_path=self.test_config_path)
        settings1 = manager.get_settings()
        settings2 = manager.get_settings()

        self.assertIs(settings1, settings2)

    def test_update_settings(self) -> None:
        """Test update_settings updates current settings."""
        manager = SettingsManager(config_path=self.test_config_path)
        new_settings = Settings(
            recent_files=["/new/path.mp4"],
            layout_orientation=LayoutOrientation.VERTICAL,
            scaling_mode=ScalingMode.MATCH_LARGER,
            default_zoom=3.0,
            shortcut_overrides={"pause": "P"},
        )

        manager.update_settings(new_settings)

        self.assertIs(manager.get_settings(), new_settings)
        self.assertEqual(manager.get_settings().recent_files, ["/new/path.mp4"])
        self.assertEqual(manager.get_settings().layout_orientation, LayoutOrientation.VERTICAL)

    def test_round_trip_save_and_load(self) -> None:
        """Test settings can be saved and loaded without loss."""
        manager = SettingsManager(config_path=self.test_config_path)
        original_settings = Settings(
            recent_files=["/path/to/video1.mp4", "/path/to/video2.mkv"],
            layout_orientation=LayoutOrientation.VERTICAL,
            scaling_mode=ScalingMode.MATCH_LARGER,
            default_zoom=2.5,
            shortcut_overrides={"play": "Space", "pause": "P"},
        )

        manager.update_settings(original_settings)
        manager.save()

        new_manager = SettingsManager(config_path=self.test_config_path)
        loaded_settings = new_manager.load()

        self.assertEqual(loaded_settings.recent_files, original_settings.recent_files)
        self.assertEqual(loaded_settings.layout_orientation, original_settings.layout_orientation)
        self.assertEqual(loaded_settings.scaling_mode, original_settings.scaling_mode)
        self.assertEqual(loaded_settings.default_zoom, original_settings.default_zoom)
        self.assertEqual(loaded_settings.shortcut_overrides, original_settings.shortcut_overrides)
