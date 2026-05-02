"""Keyboard shortcuts manager.

Responsibilities:
- Keyboard shortcuts for play/pause, step, zoom, sync nudge, layout toggle
- Tooltip/help text
- Optional shortcut customization
- Unified dispatch so buttons and keys hit the same controller actions
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional

import wx  # type: ignore


@dataclass(frozen=True, eq=True)
class KeyBinding:
    """Represents a key binding configuration.

    Uses wxPython key code constants (wx.WXK_*) and modifier constants (wx.MOD_*).
    """

    key_code: int
    modifiers: int
    command: str
    tooltip: str

    def __post_init__(self) -> None:
        """Validate key binding values."""
        if self.key_code < 0:
            raise ValueError(f"key_code must be >= 0, got {self.key_code}")
        if self.modifiers < 0:
            raise ValueError(f"modifiers must be >= 0, got {self.modifiers}")
        if not self.command:
            raise ValueError("command cannot be empty")
        if not self.tooltip:
            raise ValueError("tooltip cannot be empty")

    def matches_event(self, event: wx.KeyEvent) -> bool:
        """Check if this binding matches a keyboard event.

        Args:
            event: wx.KeyEvent to check

        Returns:
            True if the event matches this binding
        """
        return event.GetKeyCode() == self.key_code and event.GetModifiers() == self.modifiers


class ShortcutManager:
    """Manages keyboard shortcuts and command dispatch."""

    def __init__(
        self,
        command_handlers: Dict[str, Callable],
        custom_bindings: Optional[Dict[str, KeyBinding]] = None,
    ) -> None:
        """Initialize shortcut manager with command handlers and custom bindings.

        Args:
            command_handlers: Dictionary mapping command names to handler functions
            custom_bindings: Optional dictionary of command -> KeyBinding overrides
        """
        self.command_handlers: Dict[str, Callable] = command_handlers
        self.custom_bindings: Dict[str, KeyBinding] = custom_bindings or {}
        self.default_bindings: Dict[str, KeyBinding] = self._create_default_bindings()
        self._active_bindings: Dict[str, KeyBinding] = self._merge_bindings()

    def _create_default_bindings(self) -> Dict[str, KeyBinding]:
        """Create default key bindings for common commands.

        Returns:
            Dictionary of command name -> KeyBinding
        """
        return {
            "play_pause": KeyBinding(
                key_code=wx.WXK_SPACE,
                modifiers=0,
                command="play_pause",
                tooltip="Space - Play/Pause",
            ),
            "play_reverse": KeyBinding(
                key_code=ord(","),
                modifiers=0,
                command="play_reverse",
                tooltip="Comma - Reverse Play",
            ),
            "play_forward": KeyBinding(
                key_code=ord("."),
                modifiers=0,
                command="play_forward",
                tooltip="Period - Forward Play",
            ),
            "stop": KeyBinding(
                key_code=ord("S"),
                modifiers=wx.MOD_CONTROL,
                command="stop",
                tooltip="Ctrl+S - Stop",
            ),
            "step_forward": KeyBinding(
                key_code=wx.WXK_RIGHT,
                modifiers=0,
                command="step_forward",
                tooltip="Right Arrow - Step Forward",
            ),
            "step_backward": KeyBinding(
                key_code=wx.WXK_LEFT,
                modifiers=0,
                command="step_backward",
                tooltip="Left Arrow - Step Backward",
            ),
            "zoom_in": KeyBinding(
                key_code=ord("+"),
                modifiers=0,
                command="zoom_in",
                tooltip="+ - Zoom In",
            ),
            "zoom_out": KeyBinding(
                key_code=ord("-"),
                modifiers=0,
                command="zoom_out",
                tooltip="- - Zoom Out",
            ),
            "zoom_reset": KeyBinding(
                key_code=ord("0"),
                modifiers=0,
                command="zoom_reset",
                tooltip="0 - Reset Zoom",
            ),
            "sync_nudge_forward": KeyBinding(
                key_code=wx.WXK_UP,
                modifiers=wx.MOD_SHIFT,
                command="sync_nudge_forward",
                tooltip="Shift+Up - Sync Nudge Forward",
            ),
            "sync_nudge_backward": KeyBinding(
                key_code=wx.WXK_DOWN,
                modifiers=wx.MOD_SHIFT,
                command="sync_nudge_backward",
                tooltip="Shift+Down - Sync Nudge Backward",
            ),
            "toggle_layout": KeyBinding(
                key_code=ord("L"),
                modifiers=wx.MOD_CONTROL,
                command="toggle_layout",
                tooltip="Ctrl+L - Toggle Layout",
            ),
            "toggle_scaling": KeyBinding(
                key_code=ord("M"),
                modifiers=wx.MOD_CONTROL | wx.MOD_SHIFT,
                command="toggle_scaling",
                tooltip="Ctrl+Shift+M - Toggle Scaling Mode",
            ),
        }

    def _merge_bindings(self) -> Dict[str, KeyBinding]:
        """Merge default and custom bindings, with custom taking precedence.

        Returns:
            Dictionary of command name -> KeyBinding (merged)
        """
        merged = self.default_bindings.copy()
        merged.update(self.custom_bindings)
        return merged

    def register_binding(self, command: str, binding: KeyBinding) -> None:
        """Register or update a key binding.

        Args:
            command: Command name
            binding: KeyBinding to register
        """
        self.custom_bindings[command] = binding
        self._active_bindings = self._merge_bindings()

    def handle_key_event(self, event: wx.KeyEvent) -> bool:
        """Handle a keyboard event and dispatch to appropriate command handler.

        Args:
            event: wx.KeyEvent to handle

        Returns:
            True if the event was handled, False otherwise
        """
        for binding in self._active_bindings.values():
            if binding.matches_event(event):
                if binding.command in self.command_handlers:
                    handler = self.command_handlers[binding.command]
                    handler()
                    event.Skip()
                    return True
        return False

    def get_tooltip_text(self, command: str) -> Optional[str]:
        """Get tooltip text for a command.

        Args:
            command: Command name

        Returns:
            Tooltip text if command exists, None otherwise
        """
        binding = self._active_bindings.get(command)
        return binding.tooltip if binding else None

    def get_all_tooltips(self) -> Dict[str, str]:
        """Get tooltip text for all registered commands.

        Returns:
            Dictionary of command name -> tooltip text
        """
        return {cmd: binding.tooltip for cmd, binding in self._active_bindings.items()}
