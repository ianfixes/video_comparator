"""Main entry point for the Video Comparator application."""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from video_comparator.app.application import Application
from video_comparator.config.settings_manager import SettingsManager
from video_comparator.errors.error_handler import ErrorHandler


@dataclass(frozen=True)
class StartupOptions:
    """Parsed CLI startup options."""

    video_paths: list[Path]
    sync_offset_frames: int


def parse_startup_options(argv: list[str]) -> StartupOptions:
    """Parse startup options for initial media and sync offset."""
    parser = argparse.ArgumentParser(prog="video-comparator")
    parser.add_argument("video1", nargs="?", type=Path, help="Path to load into pane 1")
    parser.add_argument("video2", nargs="?", type=Path, help="Path to load into pane 2")
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        metavar="FRAMES",
        help="Initial sync offset in frames for video 2",
    )
    args = parser.parse_args(argv)
    video_paths = [path for path in (args.video1, args.video2) if path is not None]
    return StartupOptions(video_paths=video_paths, sync_offset_frames=args.offset)


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for the application.

    Command-line arguments:
    - Up to two optional positional video paths to load on launch
    - Optional --offset signed integer sync offset (frames) for video 2

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    settings_manager = SettingsManager()
    error_handler = ErrorHandler()

    try:
        startup_options = parse_startup_options(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if code != 0:
            error_handler.handle_error(ValueError("Invalid command-line arguments. Use --help for usage details."))
        return code

    app = Application(
        settings_manager=settings_manager,
        error_handler=error_handler,
        initial_video_paths=startup_options.video_paths if startup_options.video_paths else None,
        initial_sync_offset_frames=startup_options.sync_offset_frames,
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
