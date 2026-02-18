"""Main application window frame.

Responsibilities:
- Top-level wx.Frame container
- Menu bar and toolbar setup
- Window lifecycle management
"""

from typing import Optional

import wx

from video_comparator.common.types import LayoutOrientation
from video_comparator.input.shortcut_manager import ShortcutManager
from video_comparator.ui.controls import ControlPanel
from video_comparator.ui.layout_manager import LayoutManager


class MainFrame(wx.Frame):
    """Main application window frame."""

    def __init__(
        self,
        layout_manager: LayoutManager,
        control_panel: ControlPanel,
        shortcut_manager: ShortcutManager,
        parent: Optional[wx.Window] = None,
        defer_layout: bool = False,
    ) -> None:
        """Initialize main frame with parent and required subsystems.

        Args:
            layout_manager: Manages layout of video panes
            control_panel: Container for playback and control widgets
            shortcut_manager: Manages keyboard shortcuts
            parent: Optional wx.Window parent (typically None for top-level frame)
            defer_layout: If True, skip layout creation (for use with temporary components)
        """
        super().__init__(parent, title="Video Comparator", size=(1200, 800))
        self.layout_manager: LayoutManager = layout_manager
        self.control_panel: ControlPanel = control_panel
        self.shortcut_manager: ShortcutManager = shortcut_manager

        self._create_menu_bar()
        if not defer_layout:
            self._create_layout()
        self._bind_events()

    def _create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menubar = wx.MenuBar()

        file_menu = wx.Menu()
        open_item1 = file_menu.Append(wx.ID_OPEN, "&Open Video 1...\tCtrl+O", "Open first video file")
        open_item2 = file_menu.Append(wx.ID_ANY, "Open Video &2...\tCtrl+Shift+O", "Open second video file")
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, "E&xit\tCtrl+Q", "Exit the application")

        view_menu = wx.Menu()
        toggle_layout_item = view_menu.Append(
            wx.ID_ANY, "Toggle &Layout\tCtrl+L", "Toggle between horizontal and vertical layout"
        )
        toggle_scaling_item = view_menu.Append(
            wx.ID_ANY, "Toggle &Scaling Mode", "Toggle between independent and match larger scaling"
        )

        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, "&About", "About Video Comparator")

        menubar.Append(file_menu, "&File")
        menubar.Append(view_menu, "&View")
        menubar.Append(help_menu, "&Help")

        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self._on_exit, exit_item)
        self.Bind(wx.EVT_MENU, self._on_about, about_item)

    def _create_layout(self) -> None:
        """Create the window layout using sizers."""
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        video_container = wx.Panel(self)
        video_sizer = wx.BoxSizer(
            wx.HORIZONTAL if self.layout_manager.orientation == LayoutOrientation.HORIZONTAL else wx.VERTICAL
        )

        video_pane1 = self.layout_manager.video_pane1
        video_pane2 = self.layout_manager.video_pane2

        video_pane1.Reparent(video_container)
        video_pane2.Reparent(video_container)

        video_sizer.Add(video_pane1, proportion=1, flag=wx.EXPAND)
        video_sizer.Add(video_pane2, proportion=1, flag=wx.EXPAND)

        video_container.SetSizer(video_sizer)
        main_sizer.Add(video_container, proportion=1, flag=wx.EXPAND)

        control_panel_widget = self.control_panel.get_panel()
        main_sizer.Add(control_panel_widget, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        self.SetSizer(main_sizer)
        self.Layout()

    def update_layout(self) -> None:
        """Update the window layout with current components.

        This method should be called after components (layout_manager, control_panel)
        have been updated to refresh the layout.
        """
        self._create_layout()

    def _bind_events(self) -> None:
        """Bind window events."""
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_SIZE, self._on_resize)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

    def _on_close(self, event: wx.CloseEvent) -> None:
        """Handle window close event.

        Args:
            event: wx.CloseEvent
        """
        self.Destroy()

    def _on_resize(self, event: wx.SizeEvent) -> None:
        """Handle window resize event.

        Args:
            event: wx.SizeEvent
        """
        if self.GetSizer():
            size = self.GetClientSize()
            self.layout_manager.update_layout(size.GetWidth(), size.GetHeight())
        event.Skip()

    def _on_key_down(self, event: wx.KeyEvent) -> None:
        """Handle keyboard events and dispatch to ShortcutManager.

        Args:
            event: wx.KeyEvent
        """
        if not self.shortcut_manager.handle_key_event(event):
            event.Skip()

    def _on_exit(self, event: wx.CommandEvent) -> None:
        """Handle exit menu item.

        Args:
            event: wx.CommandEvent
        """
        self.Close()

    def _on_about(self, event: wx.CommandEvent) -> None:
        """Handle about menu item.

        Args:
            event: wx.CommandEvent
        """
        wx.MessageBox(
            "Video Comparator\nA frame-accurate video comparison tool\nVersion 1.0.0",
            "About Video Comparator",
            wx.OK | wx.ICON_INFORMATION,
        )
