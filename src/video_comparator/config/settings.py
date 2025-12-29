"""Configuration and settings management.

Responsibilities:
- Persist recent files
- Last layout preferences
- Zoom defaults
- Shortcut overrides
- Keep optional to avoid startup fragility
"""

from typing import Any, Dict, List

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
        """Initialize settings with provided values.

        Args:
            recent_files: List of recently opened file paths
            layout_orientation: LayoutOrientation enum value
            scaling_mode: ScalingMode enum value
            default_zoom: Default zoom level (must be > 0)
            shortcut_overrides: Dictionary of shortcut command -> key binding overrides

        Raises:
            ValueError: If enum values are invalid or default_zoom <= 0
        """
        self._validate_enum(layout_orientation, LayoutOrientation, "layout_orientation")
        self._validate_enum(scaling_mode, ScalingMode, "scaling_mode")

        if default_zoom <= 0:
            raise ValueError(f"default_zoom must be > 0, got {default_zoom}")

        self.recent_files: List[str] = recent_files
        self.layout_orientation: LayoutOrientation = layout_orientation
        self.scaling_mode: ScalingMode = scaling_mode
        self.default_zoom: float = default_zoom
        self.shortcut_overrides: dict = shortcut_overrides

    @staticmethod
    def _validate_enum(value: Any, enum_class: type, field_name: str) -> None:
        """Validate that a value is a valid enum member.

        Args:
            value: Value to validate
            enum_class: Enum class to validate against
            field_name: Name of the field for error messages

        Raises:
            ValueError: If value is not a valid enum member
        """
        if not isinstance(value, enum_class):
            raise ValueError(f"{field_name} must be a {enum_class.__name__}, got {type(value).__name__}")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize settings to a dictionary.

        Returns:
            Dictionary representation of settings suitable for JSON serialization
        """
        return {
            "recent_files": self.recent_files,
            "layout_orientation": self.layout_orientation.value,
            "scaling_mode": self.scaling_mode.value,
            "default_zoom": self.default_zoom,
            "shortcut_overrides": self.shortcut_overrides,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        """Deserialize settings from a dictionary.

        Args:
            data: Dictionary containing settings data

        Returns:
            Settings instance

        Raises:
            ValueError: If enum values are invalid or data is malformed
        """
        try:
            layout_orientation_str = data.get("layout_orientation", "horizontal")
            scaling_mode_str = data.get("scaling_mode", "independent")

            try:
                layout_orientation = LayoutOrientation(layout_orientation_str)
            except ValueError:
                raise ValueError(
                    f"Invalid layout_orientation: {layout_orientation_str}. "
                    f"Must be one of: {[e.value for e in LayoutOrientation]}"
                )

            try:
                scaling_mode = ScalingMode(scaling_mode_str)
            except ValueError:
                raise ValueError(
                    f"Invalid scaling_mode: {scaling_mode_str}. " f"Must be one of: {[e.value for e in ScalingMode]}"
                )

            return cls(
                recent_files=data.get("recent_files", []),
                layout_orientation=layout_orientation,
                scaling_mode=scaling_mode,
                default_zoom=data.get("default_zoom", 1.0),
                shortcut_overrides=data.get("shortcut_overrides", {}),
            )
        except KeyError as e:
            raise ValueError(f"Missing required setting: {e}")
        except TypeError as e:
            raise ValueError(f"Invalid setting data type: {e}")
