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

    def show(self, style: int = wx.OK | wx.ICON_ERROR) -> int:
        """Display the error dialog and return the user's response.

        Args:
            style: Dialog style flags (default: wx.OK | wx.ICON_ERROR)

        Returns:
            Dialog result code (e.g., wx.ID_OK, wx.ID_CANCEL)
        """
        dialog = wx.MessageDialog(self.parent, self.message, self.title, style)
        try:
            result = dialog.ShowModal()
            return result
        finally:
            dialog.Destroy()
