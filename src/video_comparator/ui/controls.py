"""UI controls and widgets.

Responsibilities:
- Timeline slider
- Reverse/forward play, pause/stop
- Frame-step buttons
- Sync-offset slider + ±1 buttons
- Zoom controls (in/out/reset)
- Routes UI events to controllers
"""

import math
from typing import Callable, Optional

import wx

from video_comparator.common.types import PlaybackDirection, PlaybackState
from video_comparator.playback.playback_controller import PlaybackController
from video_comparator.render.video_pane import VideoPane
from video_comparator.sync.timeline_controller import TimelineController


class TimelineSlider:
    """Timeline slider widget with position display."""

    def __init__(
        self,
        parent: wx.Window,
        timeline_controller: TimelineController,
        on_position_changed: Optional[Callable[[], None]] = None,
    ) -> None:
        """Initialize timeline slider with parent and timeline controller.

        Args:
            parent: Parent wx.Window widget
            timeline_controller: TimelineController for position management
            on_position_changed: Optional callback invoked when user changes position (e.g. to request frames)
        """
        self.parent: wx.Window = parent
        self.timeline_controller: TimelineController = timeline_controller
        self._on_position_changed: Optional[Callable[[], None]] = on_position_changed
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
                style=wx.SL_HORIZONTAL,
            )
        else:
            self.slider.SetRange(min_milliseconds, max_milliseconds)

    def _on_slider_change(self, event: wx.CommandEvent) -> None:
        """Handle slider value change. Updates position, display, and requests frames at new position."""
        if self._updating_from_controller:
            return

        milliseconds = self.slider.GetValue()
        timestamp = milliseconds / 1000.0
        min_p, max_p = self.timeline_controller.get_effective_range()
        timestamp = max(min_p, min(timestamp, max_p))

        self.timeline_controller.set_position(timestamp)
        self._updating_from_controller = True
        try:
            self.slider.SetValue(int(round(timestamp * 1000)))
        finally:
            self._updating_from_controller = False
        self._update_position_display()
        if self._on_position_changed is not None:
            self._on_position_changed()

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
        """Update slider range (e.g. after loading a video). May move thumb to stay in range."""
        self._update_slider_range()
        self.update_position()

    def update_range_after_sync_offset_change(self) -> None:
        """Update time/frame labels after sync offset changes.

        Do not call ``SetRange``/``SetValue`` on the timeline slider: changing the wx range
        rescales the thumb even when the timeline time (``current_position``) is unchanged.
        Sync only affects which video-2 frame pairs with the current instant; the timeline
        thumb and range are updated on load (``update_range``) and by explicit seeks/steps.
        """
        self._update_position_display()

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
        on_sync_offset_changed: Optional[Callable[[], None]] = None,
    ) -> None:
        """Initialize sync controls with parent and timeline controller.

        Args:
            parent: Parent wx.Window widget
            timeline_controller: TimelineController for sync offset management
            min_offset_frames: Minimum sync offset in frames (default: -1000)
            max_offset_frames: Maximum sync offset in frames (default: 1000)
            on_sync_offset_changed: Optional callback after offset changes (slider or ±1)
        """
        self.parent: wx.Window = parent
        self.timeline_controller: TimelineController = timeline_controller
        self.min_offset_frames: int = min_offset_frames
        self.max_offset_frames: int = max_offset_frames
        self._on_sync_offset_changed: Optional[Callable[[], None]] = on_sync_offset_changed
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
        self._notify_sync_offset_changed()

    def _on_increment(self, event: wx.CommandEvent) -> None:
        """Handle +1 frame button click event.

        Args:
            event: wx.CommandEvent from button
        """
        self.timeline_controller.increment_sync_offset()
        self._update_slider_value()
        self._update_offset_display()
        self._notify_sync_offset_changed()

    def _on_decrement(self, event: wx.CommandEvent) -> None:
        """Handle -1 frame button click event.

        Args:
            event: wx.CommandEvent from button
        """
        self.timeline_controller.decrement_sync_offset()
        self._update_slider_value()
        self._update_offset_display()
        self._notify_sync_offset_changed()

    def _notify_sync_offset_changed(self) -> None:
        if self._on_sync_offset_changed is not None:
            self._on_sync_offset_changed()

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
    """Zoom control buttons with zoom level display."""

    ZOOM_FACTOR: float = VideoPane.ZOOM_STEP_FACTOR
    _UNIT_ZOOM_ABS_TOL: float = 1e-6
    _NON_UNIT_ZOOM_FOREGROUND = wx.Colour(200, 32, 32)

    @classmethod
    def is_unit_zoom(cls, zoom_level: float) -> bool:
        """True if ``zoom_level`` is exactly 1× within floating-point tolerance."""
        return math.isclose(zoom_level, 1.0, rel_tol=0.0, abs_tol=cls._UNIT_ZOOM_ABS_TOL)

    def __init__(
        self,
        parent: wx.Window,
        video_pane1: VideoPane,
        video_pane2: VideoPane,
        synchronized: bool = True,
    ) -> None:
        """Initialize zoom controls with parent and video panes.

        Args:
            parent: Parent wx.Window widget
            video_pane1: First VideoPane widget
            video_pane2: Second VideoPane widget
            synchronized: If True, zoom in/out buttons affect both panes; if False, only pane1.
                Reset Zoom always restores both panes to 1× and default pan; Reset Pan always centers both.
        """
        self.parent: wx.Window = parent
        self.video_pane1: VideoPane = video_pane1
        self.video_pane2: VideoPane = video_pane2
        self.synchronized: bool = synchronized

        self.zoom_in_button: wx.Button = wx.Button(parent, label="Zoom In")
        self.zoom_out_button: wx.Button = wx.Button(parent, label="Zoom Out")
        self.zoom_reset_button: wx.Button = wx.Button(parent, label="Reset Zoom")
        self.pan_reset_button: wx.Button = wx.Button(parent, label="Reset Pan")

        self.zoom_label: wx.StaticText = wx.StaticText(parent, label="Zoom: 1.00x")

        self.zoom_reset_button.SetToolTip(
            "Restore 1× zoom and centered pan on both videos (magnification and framing)."
        )
        self.pan_reset_button.SetToolTip(
            "Center pan only on both videos; magnification stays unchanged. Zoom adjustments may still imply pan shifts."
        )

        self.zoom_in_button.Bind(wx.EVT_BUTTON, self._on_zoom_in)
        self.zoom_out_button.Bind(wx.EVT_BUTTON, self._on_zoom_out)
        self.zoom_reset_button.Bind(wx.EVT_BUTTON, self._on_zoom_reset)
        self.pan_reset_button.Bind(wx.EVT_BUTTON, self._on_pan_reset)

        self._update_zoom_display()

    def _on_zoom_in(self, event: wx.CommandEvent) -> None:
        """Handle zoom in button click event.

        Args:
            event: wx.CommandEvent from button
        """
        self._apply_zoom(self.ZOOM_FACTOR)

    def _on_zoom_out(self, event: wx.CommandEvent) -> None:
        """Handle zoom out button click event.

        Args:
            event: wx.CommandEvent from button
        """
        self._apply_zoom(1.0 / self.ZOOM_FACTOR)

    def _on_zoom_reset(self, event: wx.CommandEvent) -> None:
        """Handle zoom reset button click event.

        Args:
            event: wx.CommandEvent from button
        """
        self.video_pane1.reset_zoom_pan()
        self.video_pane2.reset_zoom_pan()
        self._update_zoom_display()

    def _on_pan_reset(self, event: wx.CommandEvent) -> None:
        """Reset pan only on both panes (zoom unchanged)."""
        self.video_pane1.reset_pan_only()
        self.video_pane2.reset_pan_only()
        self._update_zoom_display()

    def _apply_zoom(self, zoom_factor: float) -> None:
        """Apply zoom factor to video pane(s).

        Args:
            zoom_factor: Multiplier for zoom level (>1.0 zooms in, <1.0 zooms out)
        """
        self.video_pane1.zoom_at_video_center(zoom_factor)

        if self.synchronized:
            self.video_pane2.zoom_at_video_center(zoom_factor)

        self._update_zoom_display()

    def _update_zoom_display(self) -> None:
        """Update the zoom level display label."""
        zoom1 = self.video_pane1.get_zoom_level()
        zoom2 = self.video_pane2.get_zoom_level()
        label_text = f"Zoom: {zoom1:.2f}x / {zoom2:.2f}x"
        self.zoom_label.SetLabel(label_text)
        app = wx.GetApp()
        normal = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT) if app is not None else wx.Colour(0, 0, 0)
        both_unit = self.is_unit_zoom(zoom1) and self.is_unit_zoom(zoom2)
        self.zoom_label.SetForegroundColour(normal if both_unit else self._NON_UNIT_ZOOM_FOREGROUND)
        self.zoom_reset_button.Enable(not both_unit)
        both_pan_default = self.video_pane1.is_default_pan() and self.video_pane2.is_default_pan()
        self.pan_reset_button.Enable(not both_pan_default)

    def update_zoom_display(self) -> None:
        """Update zoom display from video panes.

        This should be called when zoom changes externally (e.g., from mouse wheel).
        """
        self._update_zoom_display()

    def get_zoom_in_button(self) -> wx.Button:
        """Get the zoom in button widget for layout purposes.

        Returns:
            The wx.Button widget
        """
        return self.zoom_in_button

    def get_zoom_out_button(self) -> wx.Button:
        """Get the zoom out button widget for layout purposes.

        Returns:
            The wx.Button widget
        """
        return self.zoom_out_button

    def get_zoom_reset_button(self) -> wx.Button:
        """Get the zoom reset button widget for layout purposes.

        Returns:
            The wx.Button widget
        """
        return self.zoom_reset_button

    def get_pan_reset_button(self) -> wx.Button:
        """Return the Reset Pan button widget for layout purposes."""
        return self.pan_reset_button

    def get_zoom_label(self) -> wx.StaticText:
        """Get the zoom level display label widget for layout purposes.

        Returns:
            The wx.StaticText widget showing current zoom level
        """
        return self.zoom_label


class ControlPanel:
    """Container for playback and control widgets."""

    def __init__(
        self,
        parent: wx.Window,
        playback_controller: PlaybackController,
        timeline_controller: TimelineController,
        video_pane1: VideoPane,
        video_pane2: VideoPane,
        on_timeline_position_changed: Optional[Callable[[], None]] = None,
        on_sync_offset_changed: Optional[Callable[[], None]] = None,
    ) -> None:
        """Initialize control panel with parent, controllers, and video panes.

        Args:
            parent: Parent wx.Window widget
            playback_controller: PlaybackController for playback control
            timeline_controller: TimelineController for timeline management
            video_pane1: First VideoPane widget
            video_pane2: Second VideoPane widget
            on_timeline_position_changed: Optional callback when user changes timeline (e.g. slider drag)
            on_sync_offset_changed: Optional callback when user changes sync offset (slider or ±1)
        """
        self.parent: wx.Window = parent
        self.playback_controller: PlaybackController = playback_controller
        self.timeline_controller: TimelineController = timeline_controller

        self.panel: wx.Panel = wx.Panel(parent)

        self.play_reverse_button: wx.Button = wx.Button(self.panel, label="◀ Play")
        self.play_forward_button: wx.Button = wx.Button(self.panel, label="▶ Play")
        self.pause_button: wx.Button = wx.Button(self.panel, label="Pause")
        self.stop_button: wx.Button = wx.Button(self.panel, label="Stop")
        self.step_forward_button: wx.Button = wx.Button(self.panel, label="Step Forward")
        self.step_backward_button: wx.Button = wx.Button(self.panel, label="Step Backward")

        self.play_reverse_button.SetToolTip("Play backward in time (comma). If glyphs fail: < Play. Pause with Space.")
        self.play_forward_button.SetToolTip("Play forward in time (period). If glyphs fail: > Play. Pause with Space.")

        self.play_reverse_button.Bind(wx.EVT_BUTTON, self._on_play_reverse)
        self.play_forward_button.Bind(wx.EVT_BUTTON, self._on_play_forward)
        self.pause_button.Bind(wx.EVT_BUTTON, self._on_pause)
        self.stop_button.Bind(wx.EVT_BUTTON, self._on_stop)
        self.step_forward_button.Bind(wx.EVT_BUTTON, self._on_step_forward)
        self.step_backward_button.Bind(wx.EVT_BUTTON, self._on_step_backward)

        self.timeline_slider: TimelineSlider = TimelineSlider(
            self.panel, timeline_controller, on_position_changed=on_timeline_position_changed
        )
        self.sync_controls: SyncControls = SyncControls(
            self.panel, timeline_controller, on_sync_offset_changed=on_sync_offset_changed
        )
        self.zoom_controls: ZoomControls = ZoomControls(self.panel, video_pane1, video_pane2)

        self._has_video1: bool = False
        self._has_video2: bool = False

        self._create_layout()
        self._update_button_states()
        self._update_sync_controls_state()

    def _create_layout(self) -> None:
        """Create the control panel layout per UI_LAYOUT_DIAGRAM.md.

        Vertical BoxSizer with rows: timeline slider+label, playback buttons,
        sync slider+buttons+label, zoom buttons+label. Sliders expand horizontally;
        buttons and labels use natural size.
        """
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Row 1: Timeline Slider (vertical: slider then position label)
        timeline_row = wx.BoxSizer(wx.VERTICAL)
        timeline_row.Add(
            self.timeline_slider.get_widget(),
            proportion=1,
            flag=wx.EXPAND,
        )
        timeline_row.Add(self.timeline_slider.get_position_label(), flag=wx.TOP, border=4)
        main_sizer.Add(timeline_row, flag=wx.EXPAND)

        # Row 2: Playback Controls (horizontal)
        playback_row = wx.BoxSizer(wx.HORIZONTAL)
        playback_row.Add(self.play_reverse_button)
        playback_row.Add(self.play_forward_button, flag=wx.LEFT, border=8)
        playback_row.Add(self.pause_button, flag=wx.LEFT, border=8)
        playback_row.Add(self.stop_button, flag=wx.LEFT, border=8)
        playback_row.Add(self.step_backward_button, flag=wx.LEFT, border=8)
        playback_row.Add(self.step_forward_button, flag=wx.LEFT, border=8)
        main_sizer.Add(playback_row, flag=wx.TOP, border=12)

        # Row 3: Sync Controls (vertical: slider then buttons+label)
        sync_row = wx.BoxSizer(wx.VERTICAL)
        sync_row.Add(
            self.sync_controls.offset_slider,
            proportion=1,
            flag=wx.EXPAND,
        )
        sync_buttons_row = wx.BoxSizer(wx.HORIZONTAL)
        sync_buttons_row.Add(self.sync_controls.decrement_button)
        sync_buttons_row.Add(self.sync_controls.increment_button, flag=wx.LEFT, border=8)
        sync_buttons_row.Add(self.sync_controls.offset_label, flag=wx.LEFT, border=12)
        sync_row.Add(sync_buttons_row, flag=wx.TOP, border=4)
        main_sizer.Add(sync_row, flag=wx.TOP | wx.EXPAND, border=12)

        # Row 4: Zoom Controls (horizontal)
        zoom_row = wx.BoxSizer(wx.HORIZONTAL)
        zoom_row.Add(self.zoom_controls.get_zoom_in_button())
        zoom_row.Add(self.zoom_controls.get_zoom_out_button(), flag=wx.LEFT, border=8)
        zoom_row.Add(self.zoom_controls.get_zoom_reset_button(), flag=wx.LEFT, border=8)
        zoom_row.Add(self.zoom_controls.get_zoom_label(), flag=wx.LEFT, border=12)
        zoom_row.Add(self.zoom_controls.get_pan_reset_button(), flag=wx.LEFT, border=8)
        main_sizer.Add(zoom_row, flag=wx.TOP, border=12)

        self.panel.SetSizer(main_sizer)

    def _on_play_forward(self, event: wx.CommandEvent) -> None:
        """Handle forward play button click."""
        self.playback_controller.play_forward()
        self._update_button_states()

    def _on_play_reverse(self, event: wx.CommandEvent) -> None:
        """Handle reverse play button click."""
        self.playback_controller.play_reverse()
        self._update_button_states()

    def _on_pause(self, event: wx.CommandEvent) -> None:
        """Handle pause button click event.

        Args:
            event: wx.CommandEvent from button
        """
        self.playback_controller.pause()
        self._update_button_states()

    def _on_stop(self, event: wx.CommandEvent) -> None:
        """Handle stop button click event.

        Args:
            event: wx.CommandEvent from button
        """
        self.playback_controller.stop()
        self._update_button_states()
        if self.timeline_slider:
            self.timeline_slider.update_position()

    def _on_step_forward(self, event: wx.CommandEvent) -> None:
        """Handle step forward button click event.

        Args:
            event: wx.CommandEvent from button
        """
        self.playback_controller.frame_step_forward()
        if self.timeline_slider:
            self.timeline_slider.update_position()

    def _on_step_backward(self, event: wx.CommandEvent) -> None:
        """Handle step backward button click event.

        Args:
            event: wx.CommandEvent from button
        """
        self.playback_controller.frame_step_backward()
        if self.timeline_slider:
            self.timeline_slider.update_position()

    def _update_button_states(self) -> None:
        """Update button enabled/disabled states based on playback state and load state."""
        has_any_video = self._has_video1 or self._has_video2
        state = self.playback_controller.state

        if not has_any_video:
            self.play_reverse_button.Enable(False)
            self.play_forward_button.Enable(False)
        elif state != PlaybackState.PLAYING:
            self.play_reverse_button.Enable(True)
            self.play_forward_button.Enable(True)
        elif self.playback_controller.playback_direction == PlaybackDirection.REVERSE:
            self.play_reverse_button.Enable(False)
            self.play_forward_button.Enable(True)
        else:
            self.play_reverse_button.Enable(True)
            self.play_forward_button.Enable(False)

        self.pause_button.Enable(state == PlaybackState.PLAYING)
        self.stop_button.Enable(has_any_video and state != PlaybackState.STOPPED)

    def _update_sync_controls_state(self) -> None:
        """Enable or disable sync controls based on whether both videos are loaded."""
        enabled = self._has_video1 and self._has_video2
        self.sync_controls.offset_slider.Enable(enabled)
        self.sync_controls.increment_button.Enable(enabled)
        self.sync_controls.decrement_button.Enable(enabled)

    def update_button_states(self) -> None:
        """Update button states from playback controller.

        This should be called when playback state changes externally.
        """
        self._update_button_states()

    def update_load_state(self, has_video1: bool, has_video2: bool) -> None:
        """Update play and sync control states based on which videos are loaded.

        Play button is enabled when at least one video is loaded.
        Sync (frame offset) controls are enabled only when both videos are loaded.

        Args:
            has_video1: True if video 1 is loaded
            has_video2: True if video 2 is loaded
        """
        self._has_video1 = has_video1
        self._has_video2 = has_video2
        self._update_button_states()
        self._update_sync_controls_state()

    def set_playback_controller(self, playback_controller: PlaybackController) -> None:
        """Replace the playback controller (e.g. when both videos become loaded).

        Args:
            playback_controller: New PlaybackController instance
        """
        self.playback_controller = playback_controller
        self._update_button_states()

    def get_panel(self) -> wx.Panel:
        """Get the panel widget for layout purposes.

        Returns:
            The wx.Panel widget
        """
        return self.panel

    def get_play_reverse_button(self) -> wx.Button:
        """Return the reverse play button widget."""
        return self.play_reverse_button

    def get_play_forward_button(self) -> wx.Button:
        """Return the forward play button widget."""
        return self.play_forward_button

    def get_pause_button(self) -> wx.Button:
        """Get the pause button widget.

        Returns:
            The wx.Button widget
        """
        return self.pause_button

    def get_stop_button(self) -> wx.Button:
        """Get the stop button widget.

        Returns:
            The wx.Button widget
        """
        return self.stop_button

    def get_step_forward_button(self) -> wx.Button:
        """Get the step forward button widget.

        Returns:
            The wx.Button widget
        """
        return self.step_forward_button

    def get_step_backward_button(self) -> wx.Button:
        """Get the step backward button widget.

        Returns:
            The wx.Button widget
        """
        return self.step_backward_button
