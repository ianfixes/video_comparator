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

        self._update_slider_range()

        self.position_label: wx.StaticText = wx.StaticText(parent, label="00:00:00.000 / Frame 0")

        self.slider.Bind(wx.EVT_SLIDER, self._on_slider_change)

        self._update_position_display()

    def _update_slider_range(self) -> None:
        """Update slider range based on effective timeline range."""
        min_position, max_position = self.timeline_controller.get_effective_range()
        min_milliseconds = int(min_position * 1000)
        max_milliseconds = int(max_position * 1000)

        if not hasattr(self, "slider"):
            self.slider: wx.Slider = wx.Slider(
                self.parent,
                minValue=min_milliseconds,
                maxValue=max_milliseconds,
                value=min_milliseconds,
                style=wx.SL_HORIZONTAL | wx.SL_LABELS,
            )
        else:
            self.slider.SetRange(min_milliseconds, max_milliseconds)

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
            min_milliseconds = self.slider.GetMin()
            max_milliseconds = self.slider.GetMax()
            milliseconds = max(min_milliseconds, min(milliseconds, max_milliseconds))
            self.slider.SetValue(milliseconds)
            self._update_position_display()
        finally:
            self._updating_from_controller = False

    def update_range(self) -> None:
        """Update slider range when sync offset changes.

        This should be called when the sync offset is modified.
        """
        self._update_slider_range()
        self.update_position()

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
        min_offset_frames: int = -1000,
        max_offset_frames: int = 1000,
    ) -> None:
        """Initialize sync controls with parent and timeline controller.

        Args:
            parent: Parent wx.Window widget
            timeline_controller: TimelineController for sync offset management
            min_offset_frames: Minimum sync offset in frames (default: -1000)
            max_offset_frames: Maximum sync offset in frames (default: 1000)
        """
        self.parent: wx.Window = parent
        self.timeline_controller: TimelineController = timeline_controller
        self.min_offset_frames: int = min_offset_frames
        self.max_offset_frames: int = max_offset_frames
        self._updating_from_controller: bool = False

        self.offset_slider: wx.Slider = wx.Slider(
            parent,
            minValue=min_offset_frames,
            maxValue=max_offset_frames,
            value=0,
            style=wx.SL_HORIZONTAL | wx.SL_LABELS,
        )

        self.increment_button: wx.Button = wx.Button(parent, label="+1")
        self.decrement_button: wx.Button = wx.Button(parent, label="-1")

        self.offset_label: wx.StaticText = wx.StaticText(parent, label="Offset: 0 frames")

        self.offset_slider.Bind(wx.EVT_SLIDER, self._on_slider_change)
        self.increment_button.Bind(wx.EVT_BUTTON, self._on_increment)
        self.decrement_button.Bind(wx.EVT_BUTTON, self._on_decrement)

        self._update_offset_display()

    def _on_slider_change(self, event: wx.CommandEvent) -> None:
        """Handle offset slider value change event.

        Args:
            event: wx.CommandEvent from slider
        """
        if self._updating_from_controller:
            return

        offset_frames = self.offset_slider.GetValue()
        self.timeline_controller.set_sync_offset(offset_frames)
        self._update_offset_display()

    def _on_increment(self, event: wx.CommandEvent) -> None:
        """Handle +1 frame button click event.

        Args:
            event: wx.CommandEvent from button
        """
        self.timeline_controller.increment_sync_offset()
        self._update_slider_value()
        self._update_offset_display()

    def _on_decrement(self, event: wx.CommandEvent) -> None:
        """Handle -1 frame button click event.

        Args:
            event: wx.CommandEvent from button
        """
        self.timeline_controller.decrement_sync_offset()
        self._update_slider_value()
        self._update_offset_display()

    def _update_slider_value(self) -> None:
        """Update slider value from timeline controller."""
        self._updating_from_controller = True
        try:
            offset_frames = self.timeline_controller.sync_offset_frames
            offset_frames = max(self.min_offset_frames, min(offset_frames, self.max_offset_frames))
            self.offset_slider.SetValue(offset_frames)
        finally:
            self._updating_from_controller = False

    def _update_offset_display(self) -> None:
        """Update the offset display label with current sync offset."""
        offset_frames = self.timeline_controller.sync_offset_frames
        label_text = f"Offset: {offset_frames:+d} frames"
        self.offset_label.SetLabel(label_text)

    def update_offset(self) -> None:
        """Update controls from timeline controller.

        This should be called when the sync offset changes externally.
        """
        self._update_slider_value()
        self._update_offset_display()

    def get_offset_slider(self) -> wx.Slider:
        """Get the offset slider widget for layout purposes.

        Returns:
            The wx.Slider widget
        """
        return self.offset_slider

    def get_increment_button(self) -> wx.Button:
        """Get the +1 button widget for layout purposes.

        Returns:
            The wx.Button widget
        """
        return self.increment_button

    def get_decrement_button(self) -> wx.Button:
        """Get the -1 button widget for layout purposes.

        Returns:
            The wx.Button widget
        """
        return self.decrement_button

    def get_offset_label(self) -> wx.StaticText:
        """Get the offset display label widget for layout purposes.

        Returns:
            The wx.StaticText widget showing current offset
        """
        return self.offset_label


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
