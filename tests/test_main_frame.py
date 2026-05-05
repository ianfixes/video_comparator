"""Unit tests for MainFrame class."""

import unittest
import warnings
from unittest.mock import MagicMock, patch

import wx

from video_comparator.app.main_frame import MainFrame
from video_comparator.common.types import LayoutOrientation
from video_comparator.input.shortcut_manager import ShortcutManager
from video_comparator.ui.controls import ControlPanel
from video_comparator.ui.layout_manager import LayoutManager


class TestMainFrame(unittest.TestCase):
    """Test cases for MainFrame class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.video_pane1 = MagicMock()
        self.video_pane2 = MagicMock()
        self.layout_manager = MagicMock(spec=LayoutManager)
        self.layout_manager.orientation = LayoutOrientation.HORIZONTAL
        self.layout_manager.video_pane1 = self.video_pane1
        self.layout_manager.video_pane2 = self.video_pane2
        self.layout_manager.update_layout = MagicMock()

        self.control_panel = MagicMock(spec=ControlPanel)
        self.control_panel_panel = MagicMock(spec=wx.Panel)
        self.control_panel.get_panel.return_value = self.control_panel_panel

        self.shortcut_manager = MagicMock(spec=ShortcutManager)
        self.shortcut_manager.handle_key_event.return_value = False

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        pass

    def test_initialization(self) -> None:
        """Test MainFrame initialization."""
        with patch("video_comparator.app.main_frame.wx.Frame.__init__", return_value=None), patch.object(
            MainFrame, "_create_menu_bar"
        ), patch.object(MainFrame, "_create_layout"), patch.object(MainFrame, "_bind_events"):
            frame = MainFrame(
                layout_manager=self.layout_manager,
                control_panel=self.control_panel,
                shortcut_manager=self.shortcut_manager,
            )
            self.assertEqual(frame.layout_manager, self.layout_manager)
            self.assertEqual(frame.control_panel, self.control_panel)
            self.assertEqual(frame.shortcut_manager, self.shortcut_manager)

    def test_menu_bar_creation(self) -> None:
        """Test menu bar creation."""
        mock_menubar = MagicMock()
        mock_menubar.GetMenuCount.return_value = 3
        mock_set_menubar = MagicMock()
        with patch("video_comparator.app.main_frame.wx.Frame.__init__", return_value=None), patch(
            "video_comparator.app.main_frame.wx.MenuBar", return_value=mock_menubar
        ), patch("video_comparator.app.main_frame.wx.Menu"), patch.object(MainFrame, "_create_layout"), patch.object(
            MainFrame, "_bind_events"
        ), patch.object(
            MainFrame, "SetMenuBar", mock_set_menubar
        ), patch.object(
            MainFrame, "Bind"
        ), patch.object(
            MainFrame, "GetMenuBar", return_value=mock_menubar
        ):
            frame = MainFrame(
                layout_manager=self.layout_manager,
                control_panel=self.control_panel,
                shortcut_manager=self.shortcut_manager,
            )
            frame._create_menu_bar()
            self.assertGreaterEqual(mock_set_menubar.call_count, 1)

    def test_window_layout_contains_all_components(self) -> None:
        """Test window layout contains all components."""
        mock_sizer = MagicMock()
        mock_sizer.GetItemCount.return_value = 2
        mock_video_container = MagicMock()
        mock_set_sizer = MagicMock()
        with patch("video_comparator.app.main_frame.wx.Frame.__init__", return_value=None), patch(
            "video_comparator.app.main_frame.wx.Panel", return_value=mock_video_container
        ), patch("video_comparator.app.main_frame.wx.BoxSizer", return_value=mock_sizer), patch.object(
            MainFrame, "_create_menu_bar"
        ), patch.object(
            MainFrame, "_bind_events"
        ), patch.object(
            MainFrame, "SetSizer", mock_set_sizer
        ), patch.object(
            MainFrame, "Layout"
        ), patch.object(
            MainFrame, "GetSizer", return_value=mock_sizer
        ):
            frame = MainFrame(
                layout_manager=self.layout_manager,
                control_panel=self.control_panel,
                shortcut_manager=self.shortcut_manager,
            )
            frame._create_layout()
            self.assertGreaterEqual(mock_set_sizer.call_count, 1)
            self.assertIsNotNone(frame.GetSizer())

    def test_create_layout_reuses_video_container(self) -> None:
        """Repeated _create_layout must not allocate a new wx.Panel for the video area each time."""
        mock_video_container = MagicMock()
        mock_sizer = MagicMock()
        mock_set_sizer = MagicMock()
        with patch("video_comparator.app.main_frame.wx.Frame.__init__", return_value=None), patch(
            "video_comparator.app.main_frame.wx.Panel", return_value=mock_video_container
        ) as mock_panel_class, patch(
            "video_comparator.app.main_frame.wx.BoxSizer", return_value=mock_sizer
        ), patch.object(
            MainFrame, "_create_menu_bar"
        ), patch.object(
            MainFrame, "_bind_events"
        ), patch.object(
            MainFrame, "SetSizer", mock_set_sizer
        ), patch.object(
            MainFrame, "Layout"
        ), patch.object(
            MainFrame, "GetSizer", return_value=mock_sizer
        ), patch.object(
            MainFrame, "GetClientSize", return_value=wx.Size(800, 600)
        ):
            frame = MainFrame(
                layout_manager=self.layout_manager,
                control_panel=self.control_panel,
                shortcut_manager=self.shortcut_manager,
                defer_layout=True,
            )
            mock_panel_class.reset_mock()
            frame._create_layout()
            frame._create_layout()
            mock_panel_class.assert_called_once()

    def test_window_close_handler_skips_event(self) -> None:
        """Close handler should defer destruction to default processing."""
        with patch("video_comparator.app.main_frame.wx.Frame.__init__", return_value=None), patch.object(
            MainFrame, "_create_menu_bar"
        ), patch.object(MainFrame, "_create_layout"), patch.object(MainFrame, "_bind_events"):
            frame = MainFrame(
                layout_manager=self.layout_manager,
                control_panel=self.control_panel,
                shortcut_manager=self.shortcut_manager,
            )
            close_event = MagicMock(spec=wx.CloseEvent)
            frame._on_close(close_event)
            close_event.Skip.assert_called_once()

    def test_window_close_invokes_on_close_request_callback(self) -> None:
        """MainFrame should delegate close handling to the application callback first."""
        with patch("video_comparator.app.main_frame.wx.Frame.__init__", return_value=None), patch.object(
            MainFrame, "_create_menu_bar"
        ), patch.object(MainFrame, "_create_layout"), patch.object(MainFrame, "_bind_events"):
            on_close = MagicMock()
            frame = MainFrame(
                layout_manager=self.layout_manager,
                control_panel=self.control_panel,
                shortcut_manager=self.shortcut_manager,
                on_close_request=on_close,
            )
            close_event = MagicMock(spec=wx.CloseEvent)
            close_event.GetSkipped.return_value = False
            frame._on_close(close_event)
            on_close.assert_called_once_with(close_event)
            close_event.Skip.assert_called_once()

    def test_window_resize_updates_layout(self) -> None:
        """Test window resize updates layout."""
        layout_manager = MagicMock(spec=LayoutManager)
        layout_manager.orientation = LayoutOrientation.HORIZONTAL
        mock_sizer = MagicMock()
        mock_get_sizer = MagicMock(return_value=mock_sizer)
        mock_get_client_size = MagicMock(return_value=wx.Size(800, 600))
        with patch("video_comparator.app.main_frame.wx.Frame.__init__", return_value=None), patch.object(
            MainFrame, "_create_menu_bar"
        ), patch.object(MainFrame, "_bind_events"), patch.object(MainFrame, "GetSizer", mock_get_sizer), patch.object(
            MainFrame, "GetClientSize", mock_get_client_size
        ), patch.object(
            MainFrame, "_create_layout"
        ):
            frame = MainFrame(
                layout_manager=layout_manager,
                control_panel=self.control_panel,
                shortcut_manager=self.shortcut_manager,
            )
            size_event = MagicMock()
            size_event.Skip = MagicMock()
            frame._on_resize(size_event)
            layout_manager.update_layout.assert_called_once_with(800, 600)
            size_event.Skip.assert_called_once()

    def test_integration_with_layout_manager(self) -> None:
        """Test integration with LayoutManager."""
        with patch("video_comparator.app.main_frame.wx.Frame.__init__", return_value=None), patch.object(
            MainFrame, "_create_menu_bar"
        ), patch.object(MainFrame, "_create_layout"), patch.object(MainFrame, "_bind_events"):
            frame = MainFrame(
                layout_manager=self.layout_manager,
                control_panel=self.control_panel,
                shortcut_manager=self.shortcut_manager,
            )
            self.assertEqual(frame.layout_manager, self.layout_manager)

    def test_integration_with_control_panel(self) -> None:
        """Test integration with ControlPanel."""
        with patch("video_comparator.app.main_frame.wx.Frame.__init__", return_value=None), patch.object(
            MainFrame, "_create_menu_bar"
        ), patch.object(MainFrame, "_create_layout"), patch.object(MainFrame, "_bind_events"):
            frame = MainFrame(
                layout_manager=self.layout_manager,
                control_panel=self.control_panel,
                shortcut_manager=self.shortcut_manager,
            )
            self.assertEqual(frame.control_panel, self.control_panel)

    def test_integration_with_shortcut_manager(self) -> None:
        """Test integration with ShortcutManager."""
        with patch("video_comparator.app.main_frame.wx.Frame.__init__", return_value=None), patch.object(
            MainFrame, "_create_menu_bar"
        ), patch.object(MainFrame, "_create_layout"), patch.object(MainFrame, "_bind_events"):
            frame = MainFrame(
                layout_manager=self.layout_manager,
                control_panel=self.control_panel,
                shortcut_manager=self.shortcut_manager,
            )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=DeprecationWarning)
                key_event = MagicMock(spec=wx.KeyEvent)
                frame._on_char_hook(key_event)
            self.shortcut_manager.handle_key_event.assert_called_once_with(key_event)
