"""Unit tests for KeyBinding and ShortcutManager classes."""

import unittest
from typing import Callable
from unittest.mock import MagicMock

import wx

from video_comparator.input.shortcut_manager import KeyBinding, ShortcutManager


class TestKeyBinding(unittest.TestCase):
    """Test cases for KeyBinding class."""

    def test_equality_comparison_same(self) -> None:
        """Test KeyBinding equality comparison with identical bindings."""
        binding1 = KeyBinding(
            key_code=wx.WXK_SPACE,
            modifiers=wx.MOD_CONTROL,
            command="test_command",
            tooltip="Ctrl+Space - Test",
        )
        binding2 = KeyBinding(
            key_code=wx.WXK_SPACE,
            modifiers=wx.MOD_CONTROL,
            command="test_command",
            tooltip="Ctrl+Space - Test",
        )

        self.assertEqual(binding1, binding2)
        self.assertEqual(hash(binding1), hash(binding2))

    def test_equality_comparison_different(self) -> None:
        """Test KeyBinding equality comparison with different bindings."""
        binding1 = KeyBinding(
            key_code=wx.WXK_SPACE,
            modifiers=0,
            command="test_command",
            tooltip="Space - Test",
        )
        binding2 = KeyBinding(
            key_code=wx.WXK_RETURN,
            modifiers=0,
            command="test_command",
            tooltip="Return - Test",
        )

        self.assertNotEqual(binding1, binding2)

    def test_validation_negative_key_code(self) -> None:
        """Test KeyBinding validation rejects negative key_code."""
        with self.assertRaises(ValueError) as context:
            KeyBinding(
                key_code=-1,
                modifiers=0,
                command="test_command",
                tooltip="Test",
            )

        self.assertIn("key_code must be >= 0", str(context.exception))

    def test_validation_negative_modifiers(self) -> None:
        """Test KeyBinding validation rejects negative modifiers."""
        with self.assertRaises(ValueError) as context:
            KeyBinding(
                key_code=wx.WXK_SPACE,
                modifiers=-1,
                command="test_command",
                tooltip="Test",
            )

        self.assertIn("modifiers must be >= 0", str(context.exception))

    def test_validation_empty_command(self) -> None:
        """Test KeyBinding validation rejects empty command."""
        with self.assertRaises(ValueError) as context:
            KeyBinding(
                key_code=wx.WXK_SPACE,
                modifiers=0,
                command="",
                tooltip="Test",
            )

        self.assertIn("command cannot be empty", str(context.exception))

    def test_validation_empty_tooltip(self) -> None:
        """Test KeyBinding validation rejects empty tooltip."""
        with self.assertRaises(ValueError) as context:
            KeyBinding(
                key_code=wx.WXK_SPACE,
                modifiers=0,
                command="test_command",
                tooltip="",
            )

        self.assertIn("tooltip cannot be empty", str(context.exception))

    def test_matches_event_success(self) -> None:
        """Test KeyBinding matches_event returns True for matching event."""
        binding = KeyBinding(
            key_code=wx.WXK_SPACE,
            modifiers=wx.MOD_CONTROL,
            command="test_command",
            tooltip="Ctrl+Space - Test",
        )

        event = MagicMock()
        event.GetKeyCode.return_value = wx.WXK_SPACE
        event.GetUnicodeKey.return_value = 0
        event.GetModifiers.return_value = wx.MOD_CONTROL

        self.assertTrue(binding.matches_event(event))

    def test_matches_event_different_key(self) -> None:
        """Test KeyBinding matches_event returns False for different key."""
        binding = KeyBinding(
            key_code=wx.WXK_SPACE,
            modifiers=wx.MOD_CONTROL,
            command="test_command",
            tooltip="Ctrl+Space - Test",
        )

        event = MagicMock()
        event.GetKeyCode.return_value = wx.WXK_RETURN
        event.GetUnicodeKey.return_value = 0
        event.GetModifiers.return_value = wx.MOD_CONTROL

        self.assertFalse(binding.matches_event(event))

    def test_matches_event_different_modifiers(self) -> None:
        """Test KeyBinding matches_event returns False for different modifiers."""
        binding = KeyBinding(
            key_code=wx.WXK_SPACE,
            modifiers=wx.MOD_CONTROL,
            command="test_command",
            tooltip="Ctrl+Space - Test",
        )

        event = MagicMock()
        event.GetKeyCode.return_value = wx.WXK_SPACE
        event.GetUnicodeKey.return_value = 0
        event.GetModifiers.return_value = wx.MOD_SHIFT

        self.assertFalse(binding.matches_event(event))

    def test_matches_event_uses_unicode_when_keycode_is_zero(self) -> None:
        """CHAR_HOOK on macOS often leaves GetKeyCode() unset for punctuation and Space."""
        binding = KeyBinding(
            key_code=ord(","),
            modifiers=0,
            command="step_backward",
            tooltip="Comma",
        )
        event = MagicMock()
        event.GetKeyCode.return_value = 0
        event.GetUnicodeKey.return_value = ord(",")
        event.GetModifiers.return_value = 0
        self.assertTrue(binding.matches_event(event))

        binding_space = KeyBinding(
            key_code=wx.WXK_SPACE,
            modifiers=0,
            command="play_pause",
            tooltip="Space",
        )
        ev2 = MagicMock()
        ev2.GetKeyCode.return_value = 0
        ev2.GetUnicodeKey.return_value = 32
        ev2.GetModifiers.return_value = 0
        self.assertTrue(binding_space.matches_event(ev2))


class TestShortcutManager(unittest.TestCase):
    """Test cases for ShortcutManager class."""

    def test_default_key_bindings_registered(self) -> None:
        """Test default key bindings are registered."""
        handlers = {
            "play_pause": lambda: None,
            "play_pause_reverse": lambda: None,
            "seek_backward_10s": lambda: None,
            "seek_forward_10s": lambda: None,
            "stop": lambda: None,
            "step_forward": lambda: None,
            "step_backward": lambda: None,
            "zoom_in": lambda: None,
            "zoom_out": lambda: None,
            "zoom_reset": lambda: None,
            "sync_nudge_forward": lambda: None,
            "sync_nudge_backward": lambda: None,
            "toggle_layout": lambda: None,
            "toggle_scaling": lambda: None,
        }
        manager = ShortcutManager(command_handlers=handlers)

        expected_commands = {
            "play_pause",
            "play_pause_reverse",
            "seek_backward_10s",
            "seek_forward_10s",
            "stop",
            "step_forward",
            "step_backward",
            "zoom_in",
            "zoom_out",
            "zoom_reset",
            "sync_nudge_forward",
            "sync_nudge_backward",
            "toggle_layout",
            "toggle_scaling",
        }

        self.assertEqual(set(manager.default_bindings.keys()), expected_commands)
        self.assertEqual(set(manager._active_bindings.keys()), expected_commands)

    def test_key_press_dispatches_to_correct_handler(self) -> None:
        """Test key press dispatches to correct command handler."""
        handler_called = False

        def test_handler() -> None:
            nonlocal handler_called
            handler_called = True

        handlers = {"test_command": test_handler}
        manager = ShortcutManager(command_handlers=handlers)

        # Register a test binding
        test_binding = KeyBinding(
            key_code=wx.WXK_SPACE,
            modifiers=0,
            command="test_command",
            tooltip="Space - Test",
        )
        manager.register_binding("test_command", test_binding)

        # Create mock event
        event = MagicMock()
        event.GetKeyCode.return_value = wx.WXK_SPACE
        event.GetModifiers.return_value = 0

        result = manager.handle_key_event(event)

        self.assertTrue(handler_called)
        self.assertTrue(result)

    def test_key_press_no_handler_returns_false(self) -> None:
        """Test key press with no matching handler returns False."""
        handlers: dict[str, Callable] = {}
        manager = ShortcutManager(command_handlers=handlers)

        event = MagicMock()
        event.GetKeyCode.return_value = wx.WXK_SPACE
        event.GetModifiers.return_value = 0

        result = manager.handle_key_event(event)

        self.assertFalse(result)

    def test_custom_bindings_override_defaults(self) -> None:
        """Test custom bindings override defaults."""
        handlers = {"play_pause": lambda: None}
        custom_binding = KeyBinding(
            key_code=wx.WXK_RETURN,
            modifiers=0,
            command="play_pause",
            tooltip="Return - Play/Pause (Custom)",
        )
        custom_bindings = {"play_pause": custom_binding}

        manager = ShortcutManager(command_handlers=handlers, custom_bindings=custom_bindings)

        # Check that custom binding is active
        active_binding = manager._active_bindings["play_pause"]
        self.assertEqual(active_binding.key_code, wx.WXK_RETURN)
        self.assertEqual(active_binding.tooltip, "Return - Play/Pause (Custom)")

        # Check that default binding is different
        default_binding = manager.default_bindings["play_pause"]
        self.assertNotEqual(active_binding.key_code, default_binding.key_code)

    def test_register_binding_updates_active_bindings(self) -> None:
        """Test register_binding updates active bindings."""
        handlers = {"test_command": lambda: None}
        manager = ShortcutManager(command_handlers=handlers)

        new_binding = KeyBinding(
            key_code=wx.WXK_RETURN,
            modifiers=0,
            command="test_command",
            tooltip="Return - Test",
        )

        manager.register_binding("test_command", new_binding)

        self.assertEqual(manager._active_bindings["test_command"], new_binding)
        self.assertEqual(manager.custom_bindings["test_command"], new_binding)

    def test_tooltip_generation_single_command(self) -> None:
        """Test tooltip generation for a single command."""
        handlers: dict[str, Callable] = {"play_pause": lambda: None}
        manager = ShortcutManager(command_handlers=handlers)

        tooltip = manager.get_tooltip_text("play_pause")

        self.assertIsNotNone(tooltip)
        if tooltip is not None:
            self.assertIn("Space", tooltip)

    def test_tooltip_generation_nonexistent_command(self) -> None:
        """Test tooltip generation returns None for nonexistent command."""
        handlers: dict[str, Callable] = {}
        manager = ShortcutManager(command_handlers=handlers)

        tooltip = manager.get_tooltip_text("nonexistent_command")

        self.assertIsNone(tooltip)

    def test_tooltip_generation_all_commands(self) -> None:
        """Test tooltip generation for all commands."""
        handlers: dict[str, Callable] = {
            "play_pause": lambda: None,
            "stop": lambda: None,
            "step_forward": lambda: None,
        }
        manager = ShortcutManager(command_handlers=handlers)

        all_tooltips = manager.get_all_tooltips()

        self.assertIsInstance(all_tooltips, dict)
        self.assertIn("play_pause", all_tooltips)
        self.assertIn("stop", all_tooltips)
        self.assertIn("step_forward", all_tooltips)
        self.assertIsInstance(all_tooltips["play_pause"], str)
        self.assertGreater(len(all_tooltips["play_pause"]), 0)

    def test_keyboard_event_handling_with_modifiers(self) -> None:
        """Test keyboard event handling with modifier keys."""
        handler_called = False

        def test_handler() -> None:
            nonlocal handler_called
            handler_called = True

        handlers = {"stop": test_handler}
        manager = ShortcutManager(command_handlers=handlers)

        # Stop is bound to Ctrl+S by default
        event = MagicMock()
        event.GetKeyCode.return_value = ord("S")
        event.GetModifiers.return_value = wx.MOD_CONTROL

        result = manager.handle_key_event(event)

        self.assertTrue(handler_called)
        self.assertTrue(result)

    def test_modifier_key_combinations_ctrl(self) -> None:
        """Test modifier key combinations with Ctrl."""
        handler_called = False

        def test_handler() -> None:
            nonlocal handler_called
            handler_called = True

        handlers = {"toggle_layout": test_handler}
        manager = ShortcutManager(command_handlers=handlers)

        # Toggle layout is bound to Ctrl+L by default
        event = MagicMock()
        event.GetKeyCode.return_value = ord("L")
        event.GetModifiers.return_value = wx.MOD_CONTROL

        result = manager.handle_key_event(event)

        self.assertTrue(handler_called)
        self.assertTrue(result)

    def test_modifier_key_combinations_shift(self) -> None:
        """Test modifier key combinations with Shift."""
        handler_called = False

        def test_handler() -> None:
            nonlocal handler_called
            handler_called = True

        handlers = {"play_pause_reverse": test_handler}
        manager = ShortcutManager(command_handlers=handlers)

        event = MagicMock()
        event.GetKeyCode.return_value = wx.WXK_SPACE
        event.GetModifiers.return_value = wx.MOD_SHIFT

        result = manager.handle_key_event(event)

        self.assertTrue(handler_called)
        self.assertTrue(result)

    def test_modifier_key_combinations_no_match(self) -> None:
        """Test modifier key combinations that don't match."""
        handlers = {"play_pause": lambda: None}
        manager = ShortcutManager(command_handlers=handlers)

        # Play/pause is bound to Space with no modifiers
        # Try with Ctrl modifier - should not match
        event = MagicMock()
        event.GetKeyCode.return_value = wx.WXK_SPACE
        event.GetModifiers.return_value = wx.MOD_CONTROL

        result = manager.handle_key_event(event)

        self.assertFalse(result)
