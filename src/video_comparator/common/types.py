"""Common type definitions and enums."""

from enum import Enum, auto


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


class PlaybackDirection(Enum):
    """Timeline direction while playing (continuous playback)."""

    FORWARD = "forward"
    REVERSE = "reverse"


class FrameRequestStatus(Enum):
    """Enum representing the status of a frame request, as produced by FrameCache."""

    SUCCESS = auto()  # Frame successfully retrieved and decoded.
    CANCELLED = auto()  # Request was cancelled (e.g., due to a new strategy request, race condition).
    DECODE_ERROR = auto()  # Frame decode failed.
    SEEK_ERROR = auto()  # Seeking to the frame failed.
    OUT_OF_RANGE = auto()  # Frame index requested is out of valid range.
