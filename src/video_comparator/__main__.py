"""Main entry point for the Video Comparator application."""

import sys
from pathlib import Path

from video_comparator.app.application import Application
from video_comparator.config.settings_manager import SettingsManager
from video_comparator.errors.error_handler import ErrorHandler


def _parse_video_paths(args: list[str]) -> list[Path]:
    """Parse first two non-option positional args as video file paths."""
    paths: list[Path] = []
    for a in args:
        if a.startswith("-"):
            continue
        paths.append(Path(a))
        if len(paths) >= 2:
            break
    return paths


def main() -> int:
    """Main entry point for the application.

    Command-line arguments: first and second (optional) are paths to video files to load on launch.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    settings_manager = SettingsManager()
    error_handler = ErrorHandler()
    initial_paths = _parse_video_paths(sys.argv[1:])

    app = Application(
        settings_manager=settings_manager,
        error_handler=error_handler,
        initial_video_paths=initial_paths if initial_paths else None,
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
