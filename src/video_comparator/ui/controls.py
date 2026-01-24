"""UI controls and widgets.

Responsibilities:
- Timeline slider
- Play/pause/stop buttons
- Frame-step buttons
- Sync-offset slider + ±1 buttons
- Zoom controls (in/out/reset)
- Routes UI events to controllers
"""

from typing import Optional

import wx

from video_comparator.playback.playback_controller import PlaybackController
from video_comparator.render.video_pane import VideoPane
from video_comparator.sync.timeline_controller import TimelineController


class TimelineSlider:
    """Timeline slider widget."""

    def __init__(
        self,
        parent: wx.Window,
        timeline_controller: TimelineController,
    ) -> None:
        """Initialize timeline slider with parent and timeline controller."""
        self.parent: wx.Window = parent
        self.timeline_controller: TimelineController = timeline_controller


class SyncControls:
    """Sync offset adjustment controls."""

    def __init__(
        self,
        parent: wx.Window,
        timeline_controller: TimelineController,
    ) -> None:
        """Initialize sync controls with parent and timeline controller."""
        self.parent: wx.Window = parent
        self.timeline_controller: TimelineController = timeline_controller


class ZoomControls:
    """Zoom control buttons."""

    def __init__(
        self,
        parent: wx.Window,
        video_pane1: VideoPane,
        video_pane2: VideoPane,
    ) -> None:
        """Initialize zoom controls with parent and video panes."""
        self.parent: wx.Window = parent
        self.video_pane1: VideoPane = video_pane1
        self.video_pane2: VideoPane = video_pane2


class ControlPanel:
    """Container for playback and control widgets."""

    def __init__(
        self,
        parent: wx.Window,
        playback_controller: PlaybackController,
        timeline_controller: TimelineController,
        video_pane1: VideoPane,
        video_pane2: VideoPane,
    ) -> None:
        """Initialize control panel with parent, controllers, and video panes."""
        self.parent: wx.Window = parent
        self.playback_controller: PlaybackController = playback_controller
        self.timeline_controller: TimelineController = timeline_controller
        self.timeline_slider: Optional[TimelineSlider] = None
        self.sync_controls: Optional[SyncControls] = None
        self.zoom_controls: Optional[ZoomControls] = None
