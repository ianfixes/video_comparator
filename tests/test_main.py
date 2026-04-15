"""Unit tests for command-line parsing and main entrypoint."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from video_comparator.__main__ import main, parse_startup_options


class TestCliParsing(unittest.TestCase):
    """Tests for CLI argument parsing semantics."""

    def test_parser_accepts_zero_one_and_two_positional_videos(self) -> None:
        """Parser accepts 0, 1, and 2 positional paths."""
        no_videos = parse_startup_options([])
        one_video = parse_startup_options(["/video1.mp4"])
        two_videos = parse_startup_options(["/video1.mp4", "/video2.mp4"])

        self.assertEqual(no_videos.video_paths, [])
        self.assertEqual(one_video.video_paths, [Path("/video1.mp4")])
        self.assertEqual(two_videos.video_paths, [Path("/video1.mp4"), Path("/video2.mp4")])

    def test_parser_rejects_three_or_more_positional_videos(self) -> None:
        """Parser rejects 3+ positional paths with usage error."""
        with self.assertRaises(SystemExit) as ctx:
            parse_startup_options(["a.mp4", "b.mp4", "c.mp4"])
        self.assertEqual(ctx.exception.code, 2)

    def test_parser_accepts_offset_zero_positive_and_negative(self) -> None:
        """Parser accepts signed integer offset values."""
        zero = parse_startup_options(["--offset", "0"])
        positive = parse_startup_options(["--offset", "5"])
        negative = parse_startup_options(["--offset", "-7"])

        self.assertEqual(zero.sync_offset_frames, 0)
        self.assertEqual(positive.sync_offset_frames, 5)
        self.assertEqual(negative.sync_offset_frames, -7)

    def test_parser_rejects_non_integer_offset(self) -> None:
        """Parser rejects non-integer offset values."""
        with self.assertRaises(SystemExit) as ctx:
            parse_startup_options(["--offset", "abc"])
        self.assertEqual(ctx.exception.code, 2)


class TestMainEntrypoint(unittest.TestCase):
    """Tests for main() wiring of CLI options to app startup."""

    @patch("video_comparator.__main__.Application")
    @patch("video_comparator.__main__.ErrorHandler")
    @patch("video_comparator.__main__.SettingsManager")
    def test_main_wires_initial_videos_and_offset_to_application(
        self,
        mock_settings_manager_cls: MagicMock,
        mock_error_handler_cls: MagicMock,
        mock_app_cls: MagicMock,
    ) -> None:
        """main() passes parsed startup options to Application constructor."""
        mock_app = MagicMock()
        mock_app.run.return_value = 0
        mock_app_cls.return_value = mock_app

        exit_code = main(["/video1.mp4", "/video2.mp4", "--offset", "-9"])

        self.assertEqual(exit_code, 0)
        mock_settings_manager_cls.assert_called_once()
        mock_error_handler_cls.assert_called_once()
        mock_app_cls.assert_called_once()
        kwargs = mock_app_cls.call_args.kwargs
        self.assertEqual(kwargs["initial_video_paths"], [Path("/video1.mp4"), Path("/video2.mp4")])
        self.assertEqual(kwargs["initial_sync_offset_frames"], -9)
        mock_app.initialize.assert_called_once()
        mock_app.run.assert_called_once()
        mock_app.shutdown.assert_called_once()

    @patch("video_comparator.__main__.Application")
    @patch("video_comparator.__main__.ErrorHandler")
    @patch("video_comparator.__main__.SettingsManager")
    def test_main_surfaces_parse_errors_through_error_handler(
        self,
        mock_settings_manager_cls: MagicMock,
        mock_error_handler_cls: MagicMock,
        mock_app_cls: MagicMock,
    ) -> None:
        """Invalid CLI args return parse exit code and trigger error handling."""
        error_handler = MagicMock()
        mock_error_handler_cls.return_value = error_handler

        exit_code = main(["/video1.mp4", "/video2.mp4", "/video3.mp4"])

        self.assertEqual(exit_code, 2)
        mock_settings_manager_cls.assert_called_once()
        mock_error_handler_cls.assert_called_once()
        mock_app_cls.assert_not_called()
        error_handler.handle_error.assert_called_once()
