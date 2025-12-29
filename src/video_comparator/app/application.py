"""Main application class.

Responsibilities:
- Bootstrap the application
- Wire dependencies between subsystems
- Manage global event loop
- Handle top-level menu/toolbars
- Manage quitting lifecycle
"""

from typing import Optional

from video_comparator.app.main_frame import MainFrame
from video_comparator.config.settings_manager import SettingsManager
from video_comparator.errors.handler import ErrorHandler
from video_comparator.input.shortcuts import ShortcutManager


class Application:
    """Main application entry point and dependency container."""

    def __init__(
        self,
        settings_manager: SettingsManager,
        error_handler: ErrorHandler,
        shortcut_manager: ShortcutManager,
    ) -> None:
        """Initialize application with required dependencies."""
        self.settings_manager: SettingsManager = settings_manager
        self.error_handler: ErrorHandler = error_handler
        self.shortcut_manager: ShortcutManager = shortcut_manager
        self.main_frame: Optional[MainFrame] = None
