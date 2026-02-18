"""Unit tests for Application class."""

import unittest
from unittest.mock import MagicMock, patch

import wx

from video_comparator.app.application import Application
from video_comparator.config.settings_manager import SettingsManager
from video_comparator.errors.error_handler import ErrorHandler


class TestApplication(unittest.TestCase):
    """Test cases for Application class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.settings_manager = MagicMock(spec=SettingsManager)
        self.settings_manager.load.return_value = MagicMock(
            layout_orientation=MagicMock(),
            scaling_mode=MagicMock(),
            shortcut_overrides={},
        )
        self.settings_manager.get_settings.return_value = MagicMock(shortcut_overrides={})
        self.error_handler = MagicMock(spec=ErrorHandler)
        self.error_handler.parent_window = None

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        if hasattr(self, "app") and self.app is not None:
            try:
                self.app.Destroy()
            except Exception:
                pass

    def test_initialization(self) -> None:
        """Test Application initialization."""
        app = Application(
            settings_manager=self.settings_manager,
            error_handler=self.error_handler,
        )
        self.assertEqual(app.settings_manager, self.settings_manager)
        self.assertEqual(app.error_handler, self.error_handler)
        self.assertIsNone(app.main_frame)

    def test_dependency_wiring_creates_all_subsystems(self) -> None:
        """Test dependency wiring creates all subsystems."""
        with patch("video_comparator.app.application.wx.App") as mock_app_class:
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            app = Application(
                settings_manager=self.settings_manager,
                error_handler=self.error_handler,
            )
            mock_video_pane = MagicMock()
            mock_layout_manager = MagicMock()
            mock_timeline_controller = MagicMock()
            with patch("video_comparator.app.application.VideoPane", return_value=mock_video_pane), patch(
                "video_comparator.app.application.LayoutManager", return_value=mock_layout_manager
            ), patch(
                "video_comparator.app.application.TimelineController", return_value=mock_timeline_controller
            ), patch(
                "video_comparator.app.application.PlaybackController"
            ), patch(
                "video_comparator.app.application.ControlPanel"
            ), patch(
                "video_comparator.app.application.ShortcutManager"
            ), patch(
                "video_comparator.app.application.MainFrame"
            ), patch(
                "video_comparator.app.application.wx.Panel"
            ):
                app.initialize()
                self.assertIsNotNone(app.video_pane1)
                self.assertIsNotNone(app.video_pane2)
                self.assertIsNotNone(app.layout_manager)
                self.assertIsNotNone(app.timeline_controller)

    def test_main_frame_is_created_and_shown(self) -> None:
        """Test MainFrame is created and shown."""
        with patch("video_comparator.app.application.wx.App") as mock_app_class:
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            app = Application(
                settings_manager=self.settings_manager,
                error_handler=self.error_handler,
            )
            mock_main_frame = MagicMock()
            mock_video_pane = MagicMock()
            with patch("video_comparator.app.application.VideoPane", return_value=mock_video_pane), patch(
                "video_comparator.app.application.LayoutManager"
            ), patch("video_comparator.app.application.TimelineController"), patch(
                "video_comparator.app.application.PlaybackController"
            ), patch(
                "video_comparator.app.application.ControlPanel"
            ), patch(
                "video_comparator.app.application.ShortcutManager"
            ), patch(
                "video_comparator.app.application.MainFrame", return_value=mock_main_frame
            ), patch(
                "video_comparator.app.application.wx.Panel"
            ), patch.object(
                mock_video_pane, "Reparent"
            ):
                app.initialize()
                self.assertEqual(app.main_frame, mock_main_frame)
                mock_main_frame.Show.assert_called_once()

    def test_application_can_start_without_loading_media(self) -> None:
        """Test application can start without loading media (smoke test)."""
        with patch("video_comparator.app.application.wx.App") as mock_app_class:
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            app = Application(
                settings_manager=self.settings_manager,
                error_handler=self.error_handler,
            )
            mock_video_pane = MagicMock()
            with patch("video_comparator.app.application.VideoPane", return_value=mock_video_pane), patch(
                "video_comparator.app.application.LayoutManager"
            ), patch("video_comparator.app.application.TimelineController"), patch(
                "video_comparator.app.application.PlaybackController"
            ), patch(
                "video_comparator.app.application.ControlPanel"
            ), patch(
                "video_comparator.app.application.ShortcutManager"
            ), patch(
                "video_comparator.app.application.MainFrame"
            ), patch(
                "video_comparator.app.application.wx.Panel"
            ), patch.object(
                mock_video_pane, "Reparent"
            ):
                app.initialize()
                self.assertIsNotNone(app.main_frame)

    def test_application_shutdown_cleanup(self) -> None:
        """Test application shutdown cleanup."""
        with patch("video_comparator.app.application.wx.App") as mock_app_class:
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            app = Application(
                settings_manager=self.settings_manager,
                error_handler=self.error_handler,
            )
            app.frame_cache_video1 = MagicMock()
            app.frame_cache_video2 = MagicMock()
            app.decoder_video1 = MagicMock()
            app.decoder_video2 = MagicMock()
            app.playback_controller = MagicMock()

            app.shutdown()

            app.frame_cache_video1.invalidate.assert_called_once()
            app.frame_cache_video2.invalidate.assert_called_once()
            app.decoder_video1.close.assert_called_once()
            app.decoder_video2.close.assert_called_once()
            app.playback_controller.stop.assert_called_once()
            self.settings_manager.save.assert_called_once()

    def test_settings_loading_on_startup(self) -> None:
        """Test settings loading on startup."""
        with patch("video_comparator.app.application.wx.App") as mock_app_class:
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            app = Application(
                settings_manager=self.settings_manager,
                error_handler=self.error_handler,
            )
            mock_video_pane = MagicMock()
            with patch("video_comparator.app.application.VideoPane", return_value=mock_video_pane), patch(
                "video_comparator.app.application.LayoutManager"
            ), patch("video_comparator.app.application.TimelineController"), patch(
                "video_comparator.app.application.PlaybackController"
            ), patch(
                "video_comparator.app.application.ControlPanel"
            ), patch(
                "video_comparator.app.application.ShortcutManager"
            ), patch(
                "video_comparator.app.application.MainFrame"
            ), patch(
                "video_comparator.app.application.wx.Panel"
            ), patch.object(
                mock_video_pane, "Reparent"
            ):
                app.initialize()
                self.settings_manager.load.assert_called_once()

    def test_error_handling_integration(self) -> None:
        """Test error handling integration."""
        with patch("video_comparator.app.application.wx.App") as mock_app_class:
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            app = Application(
                settings_manager=self.settings_manager,
                error_handler=self.error_handler,
            )
            mock_video_pane = MagicMock()
            mock_main_frame = MagicMock()
            with patch("video_comparator.app.application.VideoPane", return_value=mock_video_pane), patch(
                "video_comparator.app.application.LayoutManager"
            ), patch("video_comparator.app.application.TimelineController"), patch(
                "video_comparator.app.application.PlaybackController"
            ), patch(
                "video_comparator.app.application.ControlPanel"
            ), patch(
                "video_comparator.app.application.ShortcutManager"
            ), patch(
                "video_comparator.app.application.MainFrame", return_value=mock_main_frame
            ), patch(
                "video_comparator.app.application.wx.Panel"
            ), patch.object(
                mock_video_pane, "Reparent"
            ):
                app.initialize()
                self.assertEqual(self.error_handler.parent_window, mock_main_frame)

    def test_initialization_never_creates_panel_without_parent(self) -> None:
        """Test that initialization never creates wx.Panel with None as parent (macOS requirement).

        This test exposes the bug where wx.Panel(None) is called, which causes
        an assertion error on macOS. The test verifies that all Panel creations
        have a valid parent (not None).
        """
        with patch("video_comparator.app.application.wx.App") as mock_app_class:
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            app = Application(
                settings_manager=self.settings_manager,
                error_handler=self.error_handler,
            )

            panel_calls = []

            def track_panel_calls(*args, **kwargs):
                """Track all wx.Panel calls to verify parent is never None."""
                panel_calls.append((args, kwargs))
                if args and args[0] is None:
                    raise AssertionError(
                        "wx.Panel was called with None as parent, which causes "
                        "assertion error on macOS. All panels must have a valid parent."
                    )
                return MagicMock()

            mock_video_pane = MagicMock()
            mock_control_panel_widget = MagicMock()
            mock_control_panel = MagicMock()
            mock_control_panel.get_panel.return_value = mock_control_panel_widget

            with patch("video_comparator.app.application.VideoPane", return_value=mock_video_pane), patch(
                "video_comparator.app.application.LayoutManager"
            ), patch("video_comparator.app.application.TimelineController"), patch(
                "video_comparator.app.application.PlaybackController"
            ), patch(
                "video_comparator.app.application.ControlPanel", return_value=mock_control_panel
            ), patch(
                "video_comparator.app.application.ShortcutManager"
            ), patch(
                "video_comparator.app.application.MainFrame"
            ), patch(
                "video_comparator.app.application.wx.Panel", side_effect=track_panel_calls
            ), patch.object(
                mock_video_pane, "Reparent"
            ), patch.object(
                mock_control_panel_widget, "Reparent"
            ):
                app.initialize()

            # Verify that if any Panel was created, it was never with None as parent
            for args, kwargs in panel_calls:
                if args:
                    self.assertIsNotNone(
                        args[0],
                        "wx.Panel was called with None as parent. " "On macOS, all windows must have a valid parent.",
                    )
