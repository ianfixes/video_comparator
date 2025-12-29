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
