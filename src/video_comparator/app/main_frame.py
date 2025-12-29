"""Main application window frame.

Responsibilities:
- Top-level wx.Frame container
- Menu bar and toolbar setup
- Window lifecycle management
"""

from typing import Optional

import wx

from video_comparator.input.shortcuts import ShortcutManager
from video_comparator.ui.controls import ControlPanel
from video_comparator.ui.layout import LayoutManager


class MainFrame:
    """Main application window frame."""

    def __init__(
        self,
        layout_manager: LayoutManager,
        control_panel: ControlPanel,
        shortcut_manager: ShortcutManager,
        parent: Optional[wx.Window] = None,
    ) -> None:
        """Initialize main frame with parent and required subsystems.

        Args:
            layout_manager: Manages layout of video panes
            control_panel: Container for playback and control widgets
            shortcut_manager: Manages keyboard shortcuts
            parent: Optional wx.Window parent (typically None for top-level frame)
        """
        self.parent: Optional[wx.Window] = parent
        self.layout_manager: LayoutManager = layout_manager
        self.control_panel: ControlPanel = control_panel
        self.shortcut_manager: ShortcutManager = shortcut_manager
