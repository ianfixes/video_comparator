"""Error handling and user messaging.

Responsibilities:
- User-friendly errors for load/decoder failures
- Unsupported formats and missing codecs
- Non-blocking dialogs
- Logging hooks for diagnostics
- Explicit feedback when media load fails
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import wx

from video_comparator.errors.error_dialog import ErrorDialog


@dataclass
class LogEntry:
    """Represents a log entry in the GUI log viewer."""

    timestamp: datetime
    level: int
    message: str


class ErrorHandler:
    """Handles errors and displays user-friendly messages."""

    def __init__(
        self,
        parent_window: Optional[wx.Window] = None,
        enable_logging: bool = True,
        console_log_level: int = logging.INFO,
        gui_log_level: int = logging.WARNING,
    ) -> None:
        """Initialize error handler with optional parent window and logging configuration.

        Args:
            parent_window: Optional wx.Window parent (typically wx.Frame) for dialogs
            enable_logging: Whether to enable logging for errors
            console_log_level: Minimum log level for console output (default: INFO)
            gui_log_level: Minimum log level for GUI display (default: WARNING)
        """
        self.parent_window: Optional[wx.Window] = parent_window
        self.enable_logging: bool = enable_logging
        self.console_log_level: int = console_log_level
        self.gui_log_level: int = gui_log_level
        self.log_entries: List[LogEntry] = []
        self.logger: Optional[logging.Logger] = logging.getLogger(__name__) if enable_logging else None

    def handle_error(
        self,
        error: Exception,
        level: int = logging.ERROR,
    ) -> None:
        """Handle an error by formatting, logging, and displaying it.

        Args:
            error: Exception to handle
            level: Log level (default: ERROR)
        """
        message = self._format_message(error)

        if self.enable_logging:
            self._log_to_console(message, level)

        if level >= self.gui_log_level:
            self._add_to_log_viewer(message, level)
            if self.parent_window is not None:
                self._show_dialog(message, level)

    def _format_message(self, error: Exception) -> str:
        """Format error message for user display.

        Args:
            error: Exception to format

        Returns:
            Formatted error message
        """
        error_type = type(error).__name__
        error_message = str(error)
        return f"Error ({error_type}): {error_message}"

    def _log_to_console(self, message: str, level: int) -> None:
        """Log error to console if level meets threshold.

        Args:
            message: Error message
            level: Log level
        """
        if self.logger is not None and level >= self.console_log_level:
            if level >= logging.ERROR:
                self.logger.error(message)
            elif level >= logging.WARNING:
                self.logger.warning(message)
            elif level >= logging.INFO:
                self.logger.info(message)
            elif level >= logging.DEBUG:
                self.logger.debug(message)

    def _show_dialog(self, message: str, level: int) -> None:
        """Show error dialog to user.

        Args:
            message: Error message to display
            level: Log level (determines dialog icon)
        """
        if self.parent_window is None:
            return

        if level >= logging.ERROR:
            style = wx.OK | wx.ICON_ERROR
            title = "Error"
        elif level >= logging.WARNING:
            style = wx.OK | wx.ICON_WARNING
            title = "Warning"
        else:
            style = wx.OK | wx.ICON_INFORMATION
            title = "Information"

        dialog = ErrorDialog(self.parent_window, title, message)
        dialog.show(style=style)

    def _add_to_log_viewer(self, message: str, level: int) -> None:
        """Add error to GUI log viewer.

        Args:
            message: Error message
            level: Log level
        """
        if level >= self.gui_log_level:
            entry = LogEntry(
                timestamp=datetime.now(),
                level=level,
                message=message,
            )
            self.log_entries.append(entry)

    def get_log_entries(self, min_level: Optional[int] = None) -> List[LogEntry]:
        """Get log entries from the GUI log viewer.

        Args:
            min_level: Optional minimum log level filter

        Returns:
            List of log entries
        """
        if min_level is None:
            return self.log_entries.copy()
        return [entry for entry in self.log_entries if entry.level >= min_level]

    def clear_log_entries(self) -> None:
        """Clear all log entries from the GUI log viewer."""
        self.log_entries.clear()
