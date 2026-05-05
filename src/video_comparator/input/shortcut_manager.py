"""Keyboard shortcuts manager.

Responsibilities:
- Keyboard shortcuts per Specification / README (playback, ±10 s seek, frame step, sync, zoom chords)
- Tooltip/help text
- Optional shortcut customization
- Unified dispatch so buttons and keys hit the same controller actions

Set environment variable ``VIDEO_COMPARATOR_DEBUG_KEYS=1`` to log raw key event fields to stderr
(``GetKeyCode``, ``GetUnicodeKey``, modifiers, event type) for diagnosing platform-specific delivery.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import wx  # type: ignore

_MODIFIER_MASK = wx.MOD_SHIFT | wx.MOD_CONTROL | wx.MOD_ALT | wx.MOD_RAW_CONTROL
if hasattr(wx, "MOD_META"):
    _MODIFIER_MASK |= wx.MOD_META

# wxPython uses different raw values per platform (e.g. on macOS ``MOD_SHIFT`` is often ``4``,
# not ``1``). Key bindings must always use ``wx.MOD_*`` constants, never hard-coded integers.


def _describe_modifiers(mods: int) -> str:
    """Human-readable modifier names for debug logs (uses current platform's ``wx.MOD_*`` bits)."""
    m = mods & _MODIFIER_MASK
    if m == 0:
        return "none"
    parts: list[str] = []
    for name, bit in (
        ("SHIFT", wx.MOD_SHIFT),
        ("CTRL", wx.MOD_CONTROL),
        ("ALT", wx.MOD_ALT),
        ("RAW_CTRL", wx.MOD_RAW_CONTROL),
        ("META", getattr(wx, "MOD_META", 0)),
    ):
        if bit and (m & bit) == bit:
            parts.append(name)
    return "+".join(parts) if parts else repr(m)


def _describe_logical_key(code: int) -> str:
    """Best-effort label for debug logs."""
    if code == wx.WXK_SPACE:
        return "SPACE"
    if code == wx.WXK_LEFT:
        return "LEFT"
    if code == wx.WXK_RIGHT:
        return "RIGHT"
    wxk_shift = getattr(wx, "WXK_SHIFT", None)
    if wxk_shift is not None and code == wxk_shift:
        return "WXK_SHIFT(alone)"
    if 32 <= code <= 126:
        return repr(chr(code))
    return repr(code)


def key_event_logical_key_code(event: wx.KeyEvent) -> int:
    """Resolve the key to match against ``KeyBinding.key_code``.

    ``EVT_CHAR_HOOK`` on macOS (and some Linux builds) often leaves ``GetKeyCode()`` at 0 for
    printable keys and Space while ``GetUnicodeKey()`` holds the ASCII/Unicode value. Navigation
    keys (arrows, etc.) still use ``GetKeyCode()`` with ``WXK_*`` constants.
    """
    kc = event.GetKeyCode()
    wxk_none = getattr(wx, "WXK_NONE", 0)
    if isinstance(kc, int) and kc not in (0, wxk_none):
        return kc
    uk = event.GetUnicodeKey()
    if isinstance(uk, int) and uk != 0:
        return uk
    return kc if isinstance(kc, int) else 0


def _debug_log_key_event(event: wx.KeyEvent) -> None:
    """Log key event fields when ``VIDEO_COMPARATOR_DEBUG_KEYS`` is set (non-empty ``1``/``true``)."""
    flag = os.environ.get("VIDEO_COMPARATOR_DEBUG_KEYS", "").strip().lower()
    if flag not in ("1", "true", "yes", "on"):
        return
    kc = event.GetKeyCode()
    uk = event.GetUnicodeKey()
    mods = event.GetModifiers()
    et = event.GetEventType()
    raw = event.GetRawKeyCode() if hasattr(event, "GetRawKeyCode") else None
    uni_mode = getattr(event, "IsKeyInUnicodeMode", lambda: None)
    try:
        um = uni_mode() if callable(uni_mode) else None
    except Exception:
        um = None
    lg = key_event_logical_key_code(event)
    print(
        "[VIDEO_COMPARATOR_DEBUG_KEYS] "
        f"event_type={et} logical_key={lg}({_describe_logical_key(lg)}) "
        f"GetKeyCode()={kc!r} GetUnicodeKey()={uk!r} "
        f"mods_raw={mods!r} mods_masked={mods & _MODIFIER_MASK!r} ({_describe_modifiers(mods)}) "
        f"GetRawKeyCode()={raw!r} IsKeyInUnicodeMode={um!r}",
        file=sys.stderr,
        flush=True,
    )


@dataclass(frozen=True, eq=True)
class KeyBinding:
    """Represents a key binding configuration.

    Uses wxPython key code constants (wx.WXK_*) and modifier constants (wx.MOD_*).
    Matching uses :func:`key_event_logical_key_code` so Space/punctuation work with ``EVT_CHAR_HOOK``.
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
        if key_event_logical_key_code(event) != self.key_code:
            return False
        actual = event.GetModifiers() & _MODIFIER_MASK
        return actual == self.modifiers


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
                tooltip="Space — pause / unpause forward / start forward",
            ),
            "play_pause_reverse": KeyBinding(
                key_code=wx.WXK_SPACE,
                modifiers=wx.MOD_SHIFT,
                command="play_pause_reverse",
                tooltip="Shift+Space — unpause reverse / start reverse / toggle direction while playing",
            ),
            "seek_backward_10s": KeyBinding(
                key_code=wx.WXK_LEFT,
                modifiers=0,
                command="seek_backward_10s",
                tooltip="Left Arrow — seek −10 seconds",
            ),
            "seek_forward_10s": KeyBinding(
                key_code=wx.WXK_RIGHT,
                modifiers=0,
                command="seek_forward_10s",
                tooltip="Right Arrow — seek +10 seconds",
            ),
            "stop": KeyBinding(
                key_code=ord("S"),
                modifiers=wx.MOD_CONTROL,
                command="stop",
                tooltip="Ctrl+S - Stop",
            ),
            "step_forward": KeyBinding(
                key_code=ord("."),
                modifiers=0,
                command="step_forward",
                tooltip="Period — step forward one frame",
            ),
            "step_backward": KeyBinding(
                key_code=ord(","),
                modifiers=0,
                command="step_backward",
                tooltip="Comma — step backward one frame",
            ),
            "zoom_in": KeyBinding(
                key_code=ord("]"),
                modifiers=wx.MOD_CONTROL,
                command="zoom_in",
                tooltip="Ctrl+] — Zoom In",
            ),
            "zoom_out": KeyBinding(
                key_code=ord("["),
                modifiers=wx.MOD_CONTROL,
                command="zoom_out",
                tooltip="Ctrl+[ — Zoom Out",
            ),
            "zoom_reset": KeyBinding(
                key_code=ord("0"),
                modifiers=0,
                command="zoom_reset",
                tooltip="0 - Reset Zoom",
            ),
            "sync_nudge_forward": KeyBinding(
                key_code=ord("="),
                modifiers=0,
                command="sync_nudge_forward",
                tooltip="= — sync offset +1 frame (both videos loaded)",
            ),
            "sync_nudge_backward": KeyBinding(
                key_code=ord("-"),
                modifiers=0,
                command="sync_nudge_backward",
                tooltip="- — sync offset −1 frame (both videos loaded)",
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
        _debug_log_key_event(event)
        for binding in self._active_bindings.values():
            if binding.matches_event(event):
                if binding.command in self.command_handlers:
                    handler = self.command_handlers[binding.command]
                    handler()
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
