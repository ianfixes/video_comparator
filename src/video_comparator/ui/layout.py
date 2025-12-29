"""Layout manager for video panes.

Responsibilities:
- Toggle orientation (horizontal/vertical)
- Toggle scaling mode (independent fit vs. match larger video)
- Manage pane sizing and positioning
"""

from typing import Optional

from video_comparator.common.types import LayoutOrientation, ScalingMode
from video_comparator.render.video_pane import VideoPane


class LayoutManager:
    """Manages the layout of video panes and controls."""

    def __init__(
        self,
        video_pane1: VideoPane,
        video_pane2: VideoPane,
        orientation: LayoutOrientation = LayoutOrientation.HORIZONTAL,
        scaling_mode: ScalingMode = ScalingMode.INDEPENDENT,
    ) -> None:
        """Initialize layout manager with video panes, orientation, and scaling mode."""
        self.video_pane1: VideoPane = video_pane1
        self.video_pane2: VideoPane = video_pane2
        self.orientation: LayoutOrientation = orientation
        self.scaling_mode: ScalingMode = scaling_mode
