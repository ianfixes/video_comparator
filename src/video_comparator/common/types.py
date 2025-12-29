"""Common type definitions and enums."""

from enum import Enum


class LayoutOrientation(Enum):
    """Layout orientation options."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class ScalingMode(Enum):
    """Video scaling mode options."""

    INDEPENDENT = "independent"
    MATCH_LARGER = "match_larger"


class PlaybackState(Enum):
    """Playback state options."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
