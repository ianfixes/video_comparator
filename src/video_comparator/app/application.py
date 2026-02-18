"""Main application class.

Responsibilities:
- Bootstrap the application
- Wire dependencies between subsystems
- Manage global event loop
- Handle top-level menu/toolbars
- Manage quitting lifecycle
"""

from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, Optional
from unittest.mock import MagicMock

import wx

from video_comparator.app.main_frame import MainFrame
from video_comparator.cache.frame_cache import FrameCache
from video_comparator.common.types import LayoutOrientation, ScalingMode
from video_comparator.config.settings import Settings
from video_comparator.config.settings_manager import SettingsManager
from video_comparator.decode.video_decoder import VideoDecoder
from video_comparator.errors.error_handler import ErrorHandler
from video_comparator.input.shortcut_manager import ShortcutManager
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
    ) -> None:
        """Initialize application with required dependencies.

        Args:
            settings_manager: Settings manager for loading/saving configuration
            error_handler: Error handler for displaying errors
        """
        self.settings_manager: SettingsManager = settings_manager
        self.error_handler: ErrorHandler = error_handler
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
        self.main_frame.Show()

    def _create_placeholder_metadata(self) -> VideoMetadata:
        """Create placeholder metadata for initial state.

        Returns:
            VideoMetadata with placeholder values
        """
        return VideoMetadata(
            file_path=None,
            duration=1.0,
            fps=30.0,
            width=1920,
            height=1080,
            pixel_format="yuv420p",
            total_frames=30,
            time_base=1.0 / 30.0,
        )

    def _on_frames_ready(self, result_video1: "FrameResult", result_video2: "FrameResult") -> None:
        """Handle frame callback from playback controller.

        Args:
            result_video1: FrameResult for video 1
            result_video2: FrameResult for video 2
        """
        if self.video_pane1 is not None and result_video1.frame is not None:
            self.video_pane1.set_frame(result_video1.frame)
        if self.video_pane2 is not None and result_video2.frame is not None:
            self.video_pane2.set_frame(result_video2.frame)

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
            self.main_frame.Layout()

    def _handle_zoom_in(self) -> None:
        """Handle zoom in command."""
        if self.video_pane1 is None or self.video_pane2 is None:
            return
        self.video_pane1.zoom_level *= 1.2
        self.video_pane2.zoom_level *= 1.2
        self.video_pane1.Refresh()
        self.video_pane2.Refresh()

    def _handle_zoom_out(self) -> None:
        """Handle zoom out command."""
        if self.video_pane1 is None or self.video_pane2 is None:
            return
        self.video_pane1.zoom_level /= 1.2
        self.video_pane2.zoom_level /= 1.2
        self.video_pane1.Refresh()
        self.video_pane2.Refresh()

    def _handle_zoom_reset(self) -> None:
        """Handle zoom reset command."""
        if self.video_pane1 is None or self.video_pane2 is None:
            return
        self.video_pane1.zoom_level = 1.0
        self.video_pane2.zoom_level = 1.0
        self.video_pane1.pan_x = 0.0
        self.video_pane1.pan_y = 0.0
        self.video_pane2.pan_x = 0.0
        self.video_pane2.pan_y = 0.0
        self.video_pane1.Refresh()
        self.video_pane2.Refresh()

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

        self.app.MainLoop()
        return 0

    def shutdown(self) -> None:
        """Shutdown the application and cleanup resources."""
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
