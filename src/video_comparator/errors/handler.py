"""Error handling and user messaging.

Responsibilities:
- User-friendly errors for load/decoder failures
- Unsupported formats and missing codecs
- Non-blocking dialogs
- Logging hooks for diagnostics
- Explicit feedback when media load fails
"""

from typing import Optional

import wx


class ErrorDialog:
    """Displays error messages to the user."""

    def __init__(self, parent: wx.Window, title: str, message: str) -> None:
        """Initialize error dialog with parent window, title, and message.

        Args:
            parent: wx.Window parent widget (typically wx.Frame or wx.Panel)
            title: Dialog title
            message: Error message to display
        """
        self.parent: wx.Window = parent
        self.title: str = title
        self.message: str = message


class ErrorHandler:
    """Handles errors and displays user-friendly messages."""

    def __init__(self, parent_window: Optional[wx.Window] = None, enable_logging: bool = True) -> None:
        """Initialize error handler with optional parent window and logging flag.

        Args:
            parent_window: Optional wx.Window parent (typically wx.Frame) for dialogs
            enable_logging: Whether to enable logging for errors
        """
        self.parent_window: Optional[wx.Window] = parent_window
        self.enable_logging: bool = enable_logging
