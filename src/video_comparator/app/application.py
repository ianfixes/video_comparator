"""Main application class.

Responsibilities:
- Bootstrap the application
- Wire dependencies between subsystems
- Manage global event loop
- Handle top-level menu/toolbars
- Manage quitting lifecycle
"""

import time
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Optional
from unittest.mock import MagicMock

import numpy as np
import wx

from video_comparator.app.main_frame import MainFrame
from video_comparator.cache.frame_cache import FrameCache
from video_comparator.common.types import LayoutOrientation, ScalingMode
from video_comparator.config.settings import Settings
from video_comparator.config.settings_manager import SettingsManager
from video_comparator.decode.video_decoder import VideoDecoder
from video_comparator.errors.error_handler import ErrorHandler
from video_comparator.input.shortcut_manager import ShortcutManager
from video_comparator.media.media_loader import MediaLoader
from video_comparator.media.video_metadata import VideoMetadata
from video_comparator.playback.playback_controller import PlaybackController
from video_comparator.render.scaling_calculator import ScalingCalculator
from video_comparator.render.video_pane import VideoPane
from video_comparator.sync.timeline_controller import TimelineController
from video_comparator.ui.controls import ControlPanel
from video_comparator.ui.layout_manager import LayoutManager

if TYPE_CHECKING:
    from video_comparator.cache.frame_result import FrameResult


class Application:
    """Main application entry point and dependency container."""

    def __init__(
        self,
        settings_manager: SettingsManager,
        error_handler: ErrorHandler,
        initial_video_paths: Optional[List[Path]] = None,
    ) -> None:
        """Initialize application with required dependencies.

        Args:
            settings_manager: Settings manager for loading/saving configuration
            error_handler: Error handler for displaying errors
            initial_video_paths: Optional list of paths (max 2) to load on launch; first=video1, second=video2
        """
        self.settings_manager: SettingsManager = settings_manager
        self.error_handler: ErrorHandler = error_handler
        self._initial_video_paths: List[Path] = list(initial_video_paths)[:2] if initial_video_paths else []
        self.app: Optional[wx.App] = None
        self.main_frame: Optional[MainFrame] = None

        self.scaling_calculator: ScalingCalculator = ScalingCalculator()
        self.video_pane1: Optional[VideoPane] = None
        self.video_pane2: Optional[VideoPane] = None
        self.layout_manager: Optional[LayoutManager] = None
        self.timeline_controller: Optional[TimelineController] = None
        self.playback_controller: Optional[PlaybackController] = None
        self.control_panel: Optional[ControlPanel] = None
        self.shortcut_manager: Optional[ShortcutManager] = None

        self.decoder_video1: Optional[VideoDecoder] = None
        self.decoder_video2: Optional[VideoDecoder] = None
        self.frame_cache_video1: Optional[FrameCache] = None
        self.frame_cache_video2: Optional[FrameCache] = None

        self.metadata_video1: Optional[VideoMetadata] = None
        self.metadata_video2: Optional[VideoMetadata] = None

        self.media_loader: MediaLoader = MediaLoader(error_handler)
        self._playback_timer: Optional[wx.Timer] = None
        self._last_tick_time: float = 0.0

    def initialize(self) -> None:
        """Initialize the application and create all subsystems."""
        if self.app is None:
            self.app = wx.App(False)

        settings = self.settings_manager.load()

        self._create_main_frame_early()
        self._create_video_panes()
        self._create_layout_manager(settings)
        self._create_controllers(settings)
        self._create_control_panel()
        self._create_shortcut_manager()
        self._finalize_main_frame()

    def _create_main_frame_early(self) -> None:
        """Create MainFrame early so it can serve as parent for child widgets.

        MainFrame is created with temporary/dummy components initially,
        then properly configured in _finalize_main_frame().
        """
        if self.app is None:
            raise RuntimeError("wx.App must be initialized before creating main frame")

        from video_comparator.common.types import LayoutOrientation, ScalingMode
        from video_comparator.input.shortcut_manager import ShortcutManager
        from video_comparator.ui.controls import ControlPanel
        from video_comparator.ui.layout_manager import LayoutManager

        dummy_layout_manager = LayoutManager(
            MagicMock(), MagicMock(), LayoutOrientation.HORIZONTAL, ScalingMode.INDEPENDENT
        )
        dummy_control_panel = MagicMock(spec=ControlPanel)
        dummy_shortcut_manager = MagicMock(spec=ShortcutManager)

        self.main_frame = MainFrame(
            layout_manager=dummy_layout_manager,
            control_panel=dummy_control_panel,
            shortcut_manager=dummy_shortcut_manager,
            defer_layout=True,
        )

    def _create_video_panes(self) -> None:
        """Create video pane widgets."""
        if self.app is None:
            raise RuntimeError("wx.App must be initialized before creating video panes")
        if self.main_frame is None:
            raise RuntimeError("MainFrame must be created before creating video panes")

        self.video_pane1 = VideoPane(self.main_frame, self.scaling_calculator)
        self.video_pane2 = VideoPane(self.main_frame, self.scaling_calculator)

    def _create_layout_manager(self, settings: Settings) -> None:
        """Create layout manager with video panes.

        Args:
            settings: Application settings
        """
        if self.video_pane1 is None or self.video_pane2 is None:
            raise RuntimeError("Video panes must be created before layout manager")

        self.layout_manager = LayoutManager(
            self.video_pane1,
            self.video_pane2,
            orientation=settings.layout_orientation,
            scaling_mode=settings.scaling_mode,
        )

    def _create_controllers(self, settings: Settings) -> None:
        """Create timeline and playback controllers.

        Args:
            settings: Application settings
        """
        if self.metadata_video1 is None or self.metadata_video2 is None:
            self.metadata_video1 = self._create_placeholder_metadata()
            self.metadata_video2 = self._create_placeholder_metadata()

        self.timeline_controller = TimelineController(self.metadata_video1, self.metadata_video2)

        if self.decoder_video1 is None or self.decoder_video2 is None:
            self.decoder_video1 = None
            self.decoder_video2 = None

        if self.frame_cache_video1 is None:
            self.frame_cache_video1 = FrameCache(max_memory_mb=100)
        if self.frame_cache_video2 is None:
            self.frame_cache_video2 = FrameCache(max_memory_mb=100)

        if self.decoder_video1 is not None and self.decoder_video2 is not None:
            self.playback_controller = PlaybackController(
                timeline_controller=self.timeline_controller,
                decoder_video1=self.decoder_video1,
                decoder_video2=self.decoder_video2,
                frame_cache_video1=self.frame_cache_video1,
                frame_cache_video2=self.frame_cache_video2,
                error_handler=self.error_handler,
                frame_callback=self._on_frames_ready,
            )

    def _create_control_panel(self) -> None:
        """Create control panel widget."""
        if self.video_pane1 is None or self.video_pane2 is None:
            raise RuntimeError("Video panes must be created before control panel")

        if self.timeline_controller is None:
            raise RuntimeError("Timeline controller must be created before control panel")

        if self.app is None:
            raise RuntimeError("wx.App must be initialized before creating control panel")
        if self.main_frame is None:
            raise RuntimeError("MainFrame must be created before creating control panel")

        if self.playback_controller is not None:
            self.control_panel = ControlPanel(
                parent=self.main_frame,
                playback_controller=self.playback_controller,
                timeline_controller=self.timeline_controller,
                video_pane1=self.video_pane1,
                video_pane2=self.video_pane2,
                on_timeline_position_changed=self._on_timeline_position_changed,
            )
        else:
            from video_comparator.common.types import PlaybackState

            mock_playback_controller = MagicMock()
            mock_playback_controller.state = PlaybackState.STOPPED
            self.control_panel = ControlPanel(
                parent=self.main_frame,
                playback_controller=mock_playback_controller,
                timeline_controller=self.timeline_controller,
                video_pane1=self.video_pane1,
                video_pane2=self.video_pane2,
                on_timeline_position_changed=self._on_timeline_position_changed,
            )

    def _create_shortcut_manager(self) -> None:
        """Create shortcut manager with command handlers."""
        command_handlers: Dict[str, Callable] = {}

        if self.playback_controller is not None:
            command_handlers["play_pause"] = self._handle_play_pause
            command_handlers["stop"] = self._handle_stop
            command_handlers["step_forward"] = self._handle_step_forward
            command_handlers["step_backward"] = self._handle_step_backward

        if self.layout_manager is not None:
            command_handlers["toggle_layout"] = self._handle_toggle_layout
            command_handlers["toggle_scaling"] = self._handle_toggle_scaling

        if self.video_pane1 is not None and self.video_pane2 is not None:
            command_handlers["zoom_in"] = self._handle_zoom_in
            command_handlers["zoom_out"] = self._handle_zoom_out
            command_handlers["zoom_reset"] = self._handle_zoom_reset

        if self.timeline_controller is not None:
            command_handlers["sync_nudge_forward"] = self._handle_sync_nudge_forward
            command_handlers["sync_nudge_backward"] = self._handle_sync_nudge_backward

        settings = self.settings_manager.get_settings()
        custom_bindings = None
        if settings.shortcut_overrides:
            from video_comparator.input.shortcut_manager import KeyBinding

            custom_bindings = {}
            for command, binding_dict in settings.shortcut_overrides.items():
                custom_bindings[command] = KeyBinding(**binding_dict)

        self.shortcut_manager = ShortcutManager(
            command_handlers=command_handlers,
            custom_bindings=custom_bindings,
        )

    def _finalize_main_frame(self) -> None:
        """Finalize MainFrame setup with all components and show it."""
        if self.layout_manager is None:
            raise RuntimeError("Layout manager must be created before finalizing main frame")
        if self.control_panel is None:
            raise RuntimeError("Control panel must be created before finalizing main frame")
        if self.shortcut_manager is None:
            raise RuntimeError("Shortcut manager must be created before finalizing main frame")
        if self.main_frame is None:
            raise RuntimeError("MainFrame must be created before finalizing")

        self.main_frame.layout_manager = self.layout_manager
        self.main_frame.control_panel = self.control_panel
        self.main_frame.shortcut_manager = self.shortcut_manager

        self.main_frame.update_layout()
        self.error_handler.parent_window = self.main_frame

        self.main_frame.set_menu_handlers(
            on_open_video_1=self._handle_open_video_1,
            on_open_video_2=self._handle_open_video_2,
            on_toggle_layout=self._handle_toggle_layout,
            on_toggle_scaling=self._handle_toggle_scaling,
        )
        if self.video_pane1 is not None:
            self.video_pane1.set_on_request_open_file(self._handle_open_video_1)
        if self.video_pane2 is not None:
            self.video_pane2.set_on_request_open_file(self._handle_open_video_2)

        self._update_control_panel_load_state()
        self._create_playback_timer()
        self.main_frame.Show()
        self._load_initial_videos()

    def _load_initial_videos(self) -> None:
        """Load videos from command-line paths if any were provided."""
        for i, path in enumerate(self._initial_video_paths):
            slot = i + 1
            metadata = self.media_loader.load_video_file_from_path(path)
            if metadata is not None:
                self._apply_loaded_video(slot, metadata)

    def _create_placeholder_metadata(self) -> VideoMetadata:
        """Create placeholder metadata for initial state (no video loaded).

        Duration and total_frames are 0 so timeline range is (0, 0) until a
        video is loaded; when one is loaded, range is that video's duration.
        """
        return VideoMetadata(
            file_path=None,
            duration=0.0,
            fps=1.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=0,
            time_base=1.0,
        )

    def _on_frames_ready(
        self,
        result_video1: "FrameResult",
        result_video2: "FrameResult",
        time_v1: float,
        frame_v1: int,
        time_v2: float,
        frame_v2: int,
    ) -> None:
        """Handle frame callback from playback controller.

        Defers pane updates to the next event loop iteration via wx.CallAfter so
        that Refresh() is processed correctly (avoids blank panes when called from
        timer or step handlers).

        Args:
            result_video1: FrameResult for video 1
            result_video2: FrameResult for video 2
            time_v1: Resolved time for video 1 (seconds)
            frame_v1: Resolved frame index for video 1
            time_v2: Resolved time for video 2 (seconds)
            frame_v2: Resolved frame index for video 2
        """
        has1 = result_video1.frame is not None
        has2 = result_video2.frame is not None
        print(
            "[FrameDebug] Application: frames_ready received frame_v1=%d frame_v2=%d "
            "has_frame1=%s has_frame2=%s status1=%s status2=%s"
            % (
                frame_v1,
                frame_v2,
                has1,
                has2,
                result_video1.status.name,
                result_video2.status.name,
            )
        )
        if not has1 or not has2:
            print(
                "[FrameDebug] Application: frame discarded before render (missing): "
                "video1=%s video2=%s" % (not has1, not has2)
            )
        frame1 = result_video1.frame.copy() if result_video1.frame is not None else None
        frame2 = result_video2.frame.copy() if result_video2.frame is not None else None
        wx.CallAfter(
            self._apply_frames_to_panes,
            frame1,
            frame2,
            time_v1,
            frame_v1,
            time_v2,
            frame_v2,
        )

    def _apply_frames_to_panes(
        self,
        frame1: Optional[np.ndarray],
        frame2: Optional[np.ndarray],
        time_v1: float,
        frame_v1: int,
        time_v2: float,
        frame_v2: int,
    ) -> None:
        """Set frame data and playback info on video panes (must run on main thread)."""
        shape1 = frame1.shape if frame1 is not None else None
        shape2 = frame2.shape if frame2 is not None else None
        print(
            "[FrameDebug] Application: rendering to panes frame_v1=%d frame_v2=%d "
            "pane1=%s pane2=%s" % (frame_v1, frame_v2, shape1, shape2)
        )
        if self.video_pane1 is not None:
            self.video_pane1.set_frame(frame1)
            self.video_pane1.set_playback_info(time_v1, frame_v1)
        if self.video_pane2 is not None:
            self.video_pane2.set_frame(frame2)
            self.video_pane2.set_playback_info(time_v2, frame_v2)

    def _on_timeline_position_changed(self) -> None:
        """Called when user changes timeline position (e.g. slider drag). Request frames at new position."""
        if self.playback_controller is not None:
            self.playback_controller.request_frames_at_current_position()

    def _create_playback_timer(self) -> None:
        """Create and bind the playback advance timer (call tick when playing)."""
        if self.main_frame is None or not isinstance(self.main_frame, wx.EvtHandler):
            return
        self._playback_timer = wx.Timer(self.main_frame)
        self.main_frame.Bind(wx.EVT_TIMER, self._on_playback_timer, self._playback_timer)

    def _on_playback_timer(self, event: wx.TimerEvent) -> None:
        """Advance playback when playing and update timeline slider."""
        from video_comparator.common.types import PlaybackState

        if self.playback_controller is None:
            return
        if self.playback_controller.state != PlaybackState.PLAYING:
            return
        now = time.perf_counter()
        if self._last_tick_time > 0:
            delta = now - self._last_tick_time
            self.playback_controller.tick(delta)
        self._last_tick_time = now
        if self.control_panel is not None and self.control_panel.timeline_slider is not None:
            self.control_panel.timeline_slider.update_position()
        if self.control_panel is not None:
            self.control_panel.update_button_states()

    def _handle_play_pause(self) -> None:
        """Handle play/pause command."""
        if self.playback_controller is None:
            return
        from video_comparator.common.types import PlaybackState

        if self.playback_controller.state == PlaybackState.PLAYING:
            self.playback_controller.pause()
        else:
            self.playback_controller.play()
        if self.control_panel is not None:
            self.control_panel.update_button_states()

    def _handle_stop(self) -> None:
        """Handle stop command."""
        if self.playback_controller is None:
            return
        self.playback_controller.stop()
        if self.control_panel is not None:
            self.control_panel.update_button_states()

    def _handle_step_forward(self) -> None:
        """Handle step forward command."""
        if self.playback_controller is None:
            return
        self.playback_controller.frame_step_forward()
        if self.control_panel is not None:
            self.control_panel.update_button_states()

    def _handle_step_backward(self) -> None:
        """Handle step backward command."""
        if self.playback_controller is None:
            return
        self.playback_controller.frame_step_backward()
        if self.control_panel is not None:
            self.control_panel.update_button_states()

    def _handle_toggle_layout(self) -> None:
        """Handle toggle layout command."""
        if self.layout_manager is None:
            return
        self.layout_manager.toggle_orientation()
        if self.main_frame is not None:
            self.main_frame.update_layout()

    def _handle_zoom_in(self) -> None:
        """Handle zoom in command."""
        if self.video_pane1 is None or self.video_pane2 is None:
            return
        zf = VideoPane.ZOOM_STEP_FACTOR
        self.video_pane1.zoom_at_video_center(zf)
        self.video_pane2.zoom_at_video_center(zf)
        if self.control_panel is not None:
            self.control_panel.zoom_controls.update_zoom_display()

    def _handle_zoom_out(self) -> None:
        """Handle zoom out command."""
        if self.video_pane1 is None or self.video_pane2 is None:
            return
        zf = 1.0 / VideoPane.ZOOM_STEP_FACTOR
        self.video_pane1.zoom_at_video_center(zf)
        self.video_pane2.zoom_at_video_center(zf)
        if self.control_panel is not None:
            self.control_panel.zoom_controls.update_zoom_display()

    def _handle_zoom_reset(self) -> None:
        """Handle zoom reset command."""
        if self.video_pane1 is None or self.video_pane2 is None:
            return
        self.video_pane1.reset_zoom_pan()
        self.video_pane2.reset_zoom_pan()
        if self.control_panel is not None:
            self.control_panel.zoom_controls.update_zoom_display()

    def _handle_toggle_scaling(self) -> None:
        """Handle toggle scaling mode command."""
        if self.layout_manager is None:
            return
        self.layout_manager.toggle_scaling_mode()

    def _update_control_panel_load_state(self) -> None:
        """Update control panel play/sync enabled state from current video load state."""
        if self.control_panel is None:
            return
        has_v1 = self.metadata_video1 is not None and self.metadata_video1.file_path is not None
        has_v2 = self.metadata_video2 is not None and self.metadata_video2.file_path is not None
        self.control_panel.update_load_state(has_v1, has_v2)

    def _handle_open_video_1(self) -> None:
        """Open file chooser and load video 1."""
        if self.main_frame is None:
            return
        metadata = self.media_loader.load_video_file(self.main_frame)
        if metadata is None:
            return
        self._apply_loaded_video(1, metadata)

    def _handle_open_video_2(self) -> None:
        """Open file chooser and load video 2."""
        if self.main_frame is None:
            return
        metadata = self.media_loader.load_video_file(self.main_frame)
        if metadata is None:
            return
        self._apply_loaded_video(2, metadata)

    def _apply_loaded_video(self, slot: int, metadata: VideoMetadata) -> None:
        """Apply loaded metadata to the given slot (1 or 2) and update decoders/caches/UI."""
        from video_comparator.decode.video_decoder import VideoDecoder

        if metadata.file_path is None:
            return
        if self.timeline_controller is None or self.frame_cache_video1 is None or self.frame_cache_video2 is None:
            return

        if slot == 1:
            if self.decoder_video1 is not None:
                self.decoder_video1.close()
            if self.frame_cache_video1 is not None:
                self.frame_cache_video1.invalidate()
            self.metadata_video1 = metadata
            self.decoder_video1 = VideoDecoder(metadata)
            if self.frame_cache_video1 is None:
                self.frame_cache_video1 = FrameCache(max_memory_mb=100)
            else:
                self.frame_cache_video1.invalidate()
            self.timeline_controller.set_metadata_video1(metadata)
            if self.video_pane1 is not None:
                self.video_pane1.set_metadata(metadata)
        else:
            if self.decoder_video2 is not None:
                self.decoder_video2.close()
            if self.frame_cache_video2 is not None:
                self.frame_cache_video2.invalidate()
            self.metadata_video2 = metadata
            self.decoder_video2 = VideoDecoder(metadata)
            if self.frame_cache_video2 is None:
                self.frame_cache_video2 = FrameCache(max_memory_mb=100)
            else:
                self.frame_cache_video2.invalidate()
            self.timeline_controller.set_metadata_video2(metadata)
            if self.video_pane2 is not None:
                self.video_pane2.set_metadata(metadata)

        if self.control_panel is not None and self.control_panel.timeline_slider is not None:
            self.control_panel.timeline_slider.update_range()

        if (
            self.decoder_video1 is not None or self.decoder_video2 is not None
        ) and self.timeline_controller is not None:
            self.playback_controller = PlaybackController(
                timeline_controller=self.timeline_controller,
                decoder_video1=self.decoder_video1,
                decoder_video2=self.decoder_video2,
                frame_cache_video1=self.frame_cache_video1,
                frame_cache_video2=self.frame_cache_video2,
                error_handler=self.error_handler,
                frame_callback=self._on_frames_ready,
            )
            if self.control_panel is not None:
                self.control_panel.set_playback_controller(self.playback_controller)
            self.timeline_controller.set_position(0.0)
            self.playback_controller.request_frames_at_current_position()
            if self.control_panel is not None and self.control_panel.timeline_slider is not None:
                self.control_panel.timeline_slider.update_position()

        self._update_control_panel_load_state()
        if self.main_frame is not None and self.layout_manager is not None:
            self.layout_manager.update_layout(
                self.main_frame.GetClientSize().GetWidth(),
                self.main_frame.GetClientSize().GetHeight(),
            )

    def _handle_sync_nudge_forward(self) -> None:
        """Handle sync nudge forward command."""
        if self.timeline_controller is None:
            return
        self.timeline_controller.increment_sync_offset()

    def _handle_sync_nudge_backward(self) -> None:
        """Handle sync nudge backward command."""
        if self.timeline_controller is None:
            return
        self.timeline_controller.decrement_sync_offset()

    def run(self) -> int:
        """Run the application main event loop.

        Returns:
            Exit code (0 for success)
        """
        if self.app is None:
            raise RuntimeError("wx.App must be initialized before running application")

        if self._playback_timer is not None:
            self._playback_timer.Start(33)
        self.app.MainLoop()
        return 0

    def shutdown(self) -> None:
        """Shutdown the application and cleanup resources."""
        if self._playback_timer is not None:
            self._playback_timer.Stop()
        if self.playback_controller is not None:
            self.playback_controller.stop()

        if self.frame_cache_video1 is not None:
            self.frame_cache_video1.invalidate()
        if self.frame_cache_video2 is not None:
            self.frame_cache_video2.invalidate()

        if self.decoder_video1 is not None:
            self.decoder_video1.close()
        if self.decoder_video2 is not None:
            self.decoder_video2.close()

        settings = self.settings_manager.get_settings()
        self.settings_manager.save()
