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
    """Timeline slider widget with position display."""

    def __init__(
        self,
        parent: wx.Window,
        timeline_controller: TimelineController,
    ) -> None:
        """Initialize timeline slider with parent and timeline controller.

        Args:
            parent: Parent wx.Window widget
            timeline_controller: TimelineController for position management
        """
        self.parent: wx.Window = parent
        self.timeline_controller: TimelineController = timeline_controller
        self._updating_from_controller: bool = False

        max_duration = min(
            self.timeline_controller.metadata_video1.duration,
            self.timeline_controller.metadata_video2.duration,
        )
        max_milliseconds = int(max_duration * 1000)

        self.slider: wx.Slider = wx.Slider(
            parent,
            minValue=0,
            maxValue=max_milliseconds,
            value=0,
            style=wx.SL_HORIZONTAL | wx.SL_LABELS,
        )

        self.position_label: wx.StaticText = wx.StaticText(parent, label="00:00:00.000 / Frame 0")

        self.slider.Bind(wx.EVT_SLIDER, self._on_slider_change)

        self._update_position_display()

    def _on_slider_change(self, event: wx.CommandEvent) -> None:
        """Handle slider value change event.

        Args:
            event: wx.CommandEvent from slider
        """
        if self._updating_from_controller:
            return

        milliseconds = self.slider.GetValue()
        timestamp = milliseconds / 1000.0

        try:
            self.timeline_controller.set_position(timestamp)
            self._update_position_display()
        except Exception:
            pass

    def _update_position_display(self) -> None:
        """Update the position display label with current time and frame info."""
        position = self.timeline_controller.current_position
        frame1 = self.timeline_controller.get_resolved_frame_video1()
        frame2 = self.timeline_controller.get_resolved_frame_video2()

        hours = int(position // 3600)
        minutes = int((position % 3600) // 60)
        seconds = int(position % 60)
        milliseconds = int((position % 1) * 1000)

        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
        label_text = f"{time_str} / Frame {frame1} (V1), {frame2} (V2)"
        self.position_label.SetLabel(label_text)

    def update_position(self) -> None:
        """Update slider position and display from timeline controller.

        This should be called when the timeline position changes externally
        (e.g., from playback controller or frame stepping).
        """
        self._updating_from_controller = True
        try:
            position = self.timeline_controller.current_position
            milliseconds = int(position * 1000)
            max_milliseconds = self.slider.GetMax()
            milliseconds = min(milliseconds, max_milliseconds)
            self.slider.SetValue(milliseconds)
            self._update_position_display()
        finally:
            self._updating_from_controller = False

    def get_widget(self) -> wx.Slider:
        """Get the wx.Slider widget for layout purposes.

        Returns:
            The wx.Slider widget
        """
        return self.slider

    def get_position_label(self) -> wx.StaticText:
        """Get the position display label widget for layout purposes.

        Returns:
            The wx.StaticText widget showing current position
        """
        return self.position_label


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
