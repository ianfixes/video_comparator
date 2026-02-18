"""Main entry point for the Video Comparator application."""

import sys

import wx

from video_comparator.app.application import Application
from video_comparator.config.settings_manager import SettingsManager
from video_comparator.errors.error_handler import ErrorHandler


def main() -> int:
    """Main entry point for the application.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    settings_manager = SettingsManager()
    error_handler = ErrorHandler()

    app = Application(
        settings_manager=settings_manager,
        error_handler=error_handler,
    )

    try:
        app.initialize()
        return app.run()
    except Exception as e:
        error_handler.handle_error(e)
        return 1
    finally:
        app.shutdown()


if __name__ == "__main__":
    sys.exit(main())
