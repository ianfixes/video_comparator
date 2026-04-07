"""Main application window frame.

Responsibilities:
- Top-level wx.Frame container
- Menu bar and toolbar setup
- Window lifecycle management
"""

from typing import Callable, Optional

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
        self._video_container: Optional[wx.Panel] = None
        self._main_frame_layout_initialized: bool = False

        self._create_menu_bar()
        if not defer_layout:
            self._create_layout()
        self._bind_events()

    def _create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menubar = wx.MenuBar()

        file_menu = wx.Menu()
        self._open_item1 = file_menu.Append(wx.ID_OPEN, "&Open Video 1...\tCtrl+O", "Open first video file")
        self._open_item2 = file_menu.Append(wx.ID_ANY, "Open Video &2...\tCtrl+Shift+O", "Open second video file")
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, "E&xit\tCtrl+Q", "Exit the application")

        view_menu = wx.Menu()
        self._toggle_layout_item = view_menu.Append(
            wx.ID_ANY, "Toggle &Layout\tCtrl+L", "Toggle between horizontal and vertical layout"
        )
        self._toggle_scaling_item = view_menu.Append(
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

    def set_menu_handlers(
        self,
        on_open_video_1: Optional[Callable[[], None]] = None,
        on_open_video_2: Optional[Callable[[], None]] = None,
        on_toggle_layout: Optional[Callable[[], None]] = None,
        on_toggle_scaling: Optional[Callable[[], None]] = None,
    ) -> None:
        """Bind File and View menu items to the given callbacks.

        Args:
            on_open_video_1: Called when File → Open Video 1 is selected
            on_open_video_2: Called when File → Open Video 2 is selected
            on_toggle_layout: Called when View → Toggle Layout is selected
            on_toggle_scaling: Called when View → Toggle Scaling Mode is selected
        """
        if on_open_video_1 is not None:
            self.Bind(wx.EVT_MENU, lambda e: on_open_video_1(), self._open_item1)
        if on_open_video_2 is not None:
            self.Bind(wx.EVT_MENU, lambda e: on_open_video_2(), self._open_item2)
        if on_toggle_layout is not None:
            self.Bind(wx.EVT_MENU, lambda e: on_toggle_layout(), self._toggle_layout_item)
        if on_toggle_scaling is not None:
            self.Bind(wx.EVT_MENU, lambda e: on_toggle_scaling(), self._toggle_scaling_item)

    @staticmethod
    def _detach_window_from_sizer(window: wx.Window) -> None:
        """Remove ``window`` from its current sizer if any.

        Required before re-adding to a new sizer; wx asserts if a window still has
        ``m_containingSizer`` set when ``Sizer.Add`` is called.
        """
        containing = window.GetContainingSizer()
        if containing is not None:
            containing.Detach(window)

    def _create_layout(self) -> None:
        """Create or refresh the window layout using sizers.

        The video area uses a single persistent :class:`wx.Panel` as container. Calling this
        repeatedly (e.g. when toggling horizontal/vertical orientation) only replaces the
        inner sizer on that panel. Creating a new container each time would orphan the old
        panel as a child of the frame without a sizer, which on many platforms shows as a
        small stray widget at the top-left.
        """
        if self._video_container is None:
            self._video_container = wx.Panel(self)

        video_sizer = wx.BoxSizer(
            wx.HORIZONTAL if self.layout_manager.orientation == LayoutOrientation.HORIZONTAL else wx.VERTICAL
        )

        video_pane1 = self.layout_manager.video_pane1
        video_pane2 = self.layout_manager.video_pane2

        self._detach_window_from_sizer(video_pane1)
        self._detach_window_from_sizer(video_pane2)

        video_pane1.Reparent(self._video_container)
        video_pane2.Reparent(self._video_container)

        video_sizer.Add(video_pane1, proportion=1, flag=wx.EXPAND)
        video_sizer.Add(video_pane2, proportion=1, flag=wx.EXPAND)

        self._video_container.SetSizer(video_sizer)

        if not self._main_frame_layout_initialized:
            main_sizer = wx.BoxSizer(wx.VERTICAL)
            main_sizer.Add(self._video_container, proportion=1, flag=wx.EXPAND)
            control_panel_widget = self.control_panel.get_panel()
            main_sizer.Add(control_panel_widget, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)
            self.SetSizer(main_sizer)
            self._main_frame_layout_initialized = True

        self.Layout()

    def update_layout(self) -> None:
        """Update the window layout with current components.

        This method should be called after components (layout_manager, control_panel)
        have been updated to refresh the layout.
        """
        self._create_layout()
        if self.GetSizer() is not None:
            size = self.GetClientSize()
            self.layout_manager.update_layout(size.GetWidth(), size.GetHeight())

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
