"""Unit tests for Settings class."""

import json
import unittest
from typing import Any, Dict

from video_comparator.common.types import LayoutOrientation, ScalingMode
from video_comparator.config.settings import Settings


class TestSettings(unittest.TestCase):
    """Test cases for Settings class."""

    def test_enum_field_validation_layout_orientation(self) -> None:
        """Test Settings rejects invalid layout_orientation enum values."""
        with self.assertRaises(ValueError) as context:
            Settings(
                recent_files=[],
                layout_orientation="invalid",  # type: ignore
                scaling_mode=ScalingMode.INDEPENDENT,
                default_zoom=1.0,
                shortcut_overrides={},
            )

        self.assertIn("layout_orientation", str(context.exception))
        self.assertIn("LayoutOrientation", str(context.exception))

    def test_enum_field_validation_scaling_mode(self) -> None:
        """Test Settings rejects invalid scaling_mode enum values."""
        with self.assertRaises(ValueError) as context:
            Settings(
                recent_files=[],
                layout_orientation=LayoutOrientation.HORIZONTAL,
                scaling_mode="invalid",  # type: ignore
                default_zoom=1.0,
                shortcut_overrides={},
            )

        self.assertIn("scaling_mode", str(context.exception))
        self.assertIn("ScalingMode", str(context.exception))

    def test_default_zoom_validation_positive(self) -> None:
        """Test Settings accepts positive default_zoom values."""
        settings = Settings(
            recent_files=[],
            layout_orientation=LayoutOrientation.HORIZONTAL,
            scaling_mode=ScalingMode.INDEPENDENT,
            default_zoom=0.1,
            shortcut_overrides={},
        )
        self.assertEqual(settings.default_zoom, 0.1)

    def test_default_zoom_validation_zero(self) -> None:
        """Test Settings rejects zero default_zoom."""
        with self.assertRaises(ValueError) as context:
            Settings(
                recent_files=[],
                layout_orientation=LayoutOrientation.HORIZONTAL,
                scaling_mode=ScalingMode.INDEPENDENT,
                default_zoom=0.0,
                shortcut_overrides={},
            )

        self.assertIn("default_zoom must be > 0", str(context.exception))

    def test_default_zoom_validation_negative(self) -> None:
        """Test Settings rejects negative default_zoom."""
        with self.assertRaises(ValueError) as context:
            Settings(
                recent_files=[],
                layout_orientation=LayoutOrientation.HORIZONTAL,
                scaling_mode=ScalingMode.INDEPENDENT,
                default_zoom=-1.0,
                shortcut_overrides={},
            )

        self.assertIn("default_zoom must be > 0", str(context.exception))

    def test_serialization_to_dict(self) -> None:
        """Test Settings serialization to dictionary."""
        settings = Settings(
            recent_files=["/path/to/video1.mp4"],
            layout_orientation=LayoutOrientation.VERTICAL,
            scaling_mode=ScalingMode.MATCH_LARGER,
            default_zoom=2.0,
            shortcut_overrides={"play": "Space"},
        )

        result = settings.to_dict()

        self.assertEqual(result["recent_files"], ["/path/to/video1.mp4"])
        self.assertEqual(result["layout_orientation"], "vertical")
        self.assertEqual(result["scaling_mode"], "match_larger")
        self.assertEqual(result["default_zoom"], 2.0)
        self.assertEqual(result["shortcut_overrides"], {"play": "Space"})

    def test_serialization_to_dict_json_compatible(self) -> None:
        """Test Settings serialization produces JSON-compatible dictionary."""
        settings = Settings(
            recent_files=["/path/to/video1.mp4"],
            layout_orientation=LayoutOrientation.HORIZONTAL,
            scaling_mode=ScalingMode.INDEPENDENT,
            default_zoom=1.5,
            shortcut_overrides={"play": "Space"},
        )

        result = settings.to_dict()

        # Should be JSON serializable without errors
        json_str = json.dumps(result)
        self.assertIsInstance(json_str, str)

        # Should be JSON deserializable
        loaded = json.loads(json_str)
        self.assertEqual(loaded["layout_orientation"], "horizontal")
        self.assertEqual(loaded["scaling_mode"], "independent")

    def test_deserialization_from_dict(self) -> None:
        """Test Settings deserialization from dictionary."""
        data = {
            "recent_files": ["/path/to/video1.mp4"],
            "layout_orientation": "vertical",
            "scaling_mode": "match_larger",
            "default_zoom": 2.0,
            "shortcut_overrides": {"play": "Space"},
        }

        settings = Settings.from_dict(data)

        self.assertEqual(settings.recent_files, ["/path/to/video1.mp4"])
        self.assertEqual(settings.layout_orientation, LayoutOrientation.VERTICAL)
        self.assertEqual(settings.scaling_mode, ScalingMode.MATCH_LARGER)
        self.assertEqual(settings.default_zoom, 2.0)
        self.assertEqual(settings.shortcut_overrides, {"play": "Space"})

    def test_deserialization_from_dict_with_defaults(self) -> None:
        """Test Settings deserialization uses defaults for missing fields."""
        data: Dict[str, Any] = {}

        settings = Settings.from_dict(data)

        self.assertEqual(settings.recent_files, [])
        self.assertEqual(settings.layout_orientation, LayoutOrientation.HORIZONTAL)
        self.assertEqual(settings.scaling_mode, ScalingMode.INDEPENDENT)
        self.assertEqual(settings.default_zoom, 1.0)
        self.assertEqual(settings.shortcut_overrides, {})

    def test_deserialization_invalid_layout_orientation(self) -> None:
        """Test Settings deserialization rejects invalid layout_orientation."""
        data = {
            "layout_orientation": "invalid",
            "scaling_mode": "independent",
        }

        with self.assertRaises(ValueError) as context:
            Settings.from_dict(data)

        self.assertIn("Invalid layout_orientation", str(context.exception))
        self.assertIn("invalid", str(context.exception))

    def test_deserialization_invalid_scaling_mode(self) -> None:
        """Test Settings deserialization rejects invalid scaling_mode."""
        data = {
            "layout_orientation": "horizontal",
            "scaling_mode": "invalid",
        }

        with self.assertRaises(ValueError) as context:
            Settings.from_dict(data)

        self.assertIn("Invalid scaling_mode", str(context.exception))
        self.assertIn("invalid", str(context.exception))

    def test_round_trip_serialization(self) -> None:
        """Test Settings can be serialized and deserialized without loss."""
        original = Settings(
            recent_files=["/path/to/video1.mp4", "/path/to/video2.mkv"],
            layout_orientation=LayoutOrientation.VERTICAL,
            scaling_mode=ScalingMode.MATCH_LARGER,
            default_zoom=3.0,
            shortcut_overrides={"play": "Space", "pause": "P"},
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = Settings.from_dict(data)

        # Verify all fields match
        self.assertEqual(restored.recent_files, original.recent_files)
        self.assertEqual(restored.layout_orientation, original.layout_orientation)
        self.assertEqual(restored.scaling_mode, original.scaling_mode)
        self.assertEqual(restored.default_zoom, original.default_zoom)
        self.assertEqual(restored.shortcut_overrides, original.shortcut_overrides)

    def test_deserialization_all_enum_values(self) -> None:
        """Test Settings deserialization accepts all valid enum values."""
        for layout_orientation in LayoutOrientation:
            for scaling_mode in ScalingMode:
                data = {
                    "layout_orientation": layout_orientation.value,
                    "scaling_mode": scaling_mode.value,
                }

                settings = Settings.from_dict(data)
                self.assertEqual(settings.layout_orientation, layout_orientation)
                self.assertEqual(settings.scaling_mode, scaling_mode)
