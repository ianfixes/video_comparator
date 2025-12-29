"""Keyboard shortcuts manager.

Responsibilities:
- Keyboard shortcuts for play/pause, step, zoom, sync nudge, layout toggle
- Tooltip/help text
- Optional shortcut customization
- Unified dispatch so buttons and keys hit the same controller actions
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass
class KeyBinding:
    """Represents a key binding configuration."""

    key_code: int
    modifiers: int
    command: str
    tooltip: str


class ShortcutManager:
    """Manages keyboard shortcuts and command dispatch."""

    def __init__(
        self,
        command_handlers: Dict[str, Callable],
        custom_bindings: Dict[str, KeyBinding],
    ) -> None:
        """Initialize shortcut manager with command handlers and custom bindings."""
        self.command_handlers: Dict[str, Callable] = command_handlers
        self.custom_bindings: Dict[str, KeyBinding] = custom_bindings
        self.default_bindings: Dict[str, KeyBinding] = {}
