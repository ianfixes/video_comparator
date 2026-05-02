"""Video pane widget for rendering frames.

Responsibilities:
- Draw frames into wx.Panel using wx.PaintDC
- Apply zoom/pan transforms
- Support two scaling modes (independent fit vs. match larger video)
- Matched bounding boxes for comparison
- Overlays for filename, native dimensions, playback time/frame, zoom level
- Maintain zoom/pan state across seeks/steps/layout changes
- Mouse interactions: drag to pan, scroll wheel to zoom, Shift-drag rectangle to zoom to region
"""

import math
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np
import wx

from video_comparator.common.types import ScalingMode
from video_comparator.media.video_metadata import VideoMetadata
from video_comparator.render.scaling_calculator import ScalingCalculator


class _VideoPaneFileDropTarget(wx.FileDropTarget):
    """Accepts file drops from the OS; highlights the pane while dragging."""

    def __init__(self, pane: "VideoPane") -> None:
        super().__init__()
        self._pane = pane

    def OnEnter(self, x: int, y: int, defResult: int) -> int:
        if self._pane._on_files_dropped is None:
            return wx.DragNone  # type: ignore[attr-defined, no-any-return]
        self._pane._set_drop_highlight(True)
        self._pane.Refresh()
        return wx.DragCopy  # type: ignore[attr-defined, no-any-return]

    def OnLeave(self) -> None:
        self._pane._set_drop_highlight(False)
        self._pane.Refresh()

    def OnDropFiles(self, x: int, y: int, filenames: List[str]) -> bool:
        self._pane._set_drop_highlight(False)
        self._pane.Refresh()
        return self._pane._deliver_dropped_files(filenames)


class RenderingError(Exception):
    """Base exception for rendering errors."""


class FrameConversionError(RenderingError):
    """Raised when frame conversion to wx.Bitmap fails."""


class VideoPane(wx.Panel):
    """Custom wx.Panel for rendering video frames with zoom/pan."""

    _PAN_ORIGIN_ABS_TOL: float = 1e-6
    MIN_ZOOM: float = 0.1
    MAX_ZOOM: float = 10.0
    ZOOM_STEP_FACTOR: float = 1.1
    _FILE_SIZE_UNITS: Tuple[str, ...] = ("B", "kB", "MB", "GB")

    def __init__(
        self,
        parent: wx.Window,
        scaling_calculator: ScalingCalculator,
        metadata: Optional[VideoMetadata] = None,
    ) -> None:
        """Initialize video pane with parent widget, scaling calculator, and optional metadata.

        Args:
            parent: wx.Window parent widget (typically wx.Panel or wx.Frame)
            scaling_calculator: Calculator for scaling transforms
            metadata: Optional video metadata (can be set later when video is loaded)
        """
        super().__init__(parent)
        self.scaling_calculator: ScalingCalculator = scaling_calculator
        self.metadata: Optional[VideoMetadata] = metadata
        self.current_frame: Optional[np.ndarray] = None
        self.zoom_level: float = 1.0
        self.pan_x: float = 0.0
        self.pan_y: float = 0.0
        self.scaling_mode: ScalingMode = ScalingMode.INDEPENDENT
        self.display_size: Tuple[int, int] = (0, 0)
        self.current_time: float = 0.0
        self.current_frame_index: int = 0

        # Mouse interaction state
        self.is_dragging: bool = False
        self.drag_start_pos: Optional[Tuple[int, int]] = None
        self.selection_rect: Optional[Tuple[int, int, int, int]] = None
        self.is_shift_dragging: bool = False

        # Drag-and-drop: highlight while OS drag hovers over pane
        self._drop_highlight: bool = False

        # Cached bitmap for current frame
        self._cached_bitmap: Optional[wx.Bitmap] = None

        # Optional callback when user clicks on empty pane to open file (e.g. load video)
        self._on_request_open_file: Optional[Callable[[], None]] = None

        # Optional callback when user drops filesystem paths (first path is used)
        self._on_files_dropped: Optional[Callable[[Sequence[str]], None]] = None
        # Optional callback invoked when zoom level changes
        self._on_zoom_changed: Optional[Callable[[], None]] = None

        self._file_drop_target = _VideoPaneFileDropTarget(self)
        self.SetDropTarget(self._file_drop_target)

        # Bind mouse events
        self.Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_left_up)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self._on_mouse_wheel)
        self.Bind(wx.EVT_PAINT, self._on_paint)

    def _wx_point_to_tuple(self, p: wx.Point) -> Tuple[int, int]:
        """Convert a wx.Point (or compatible object) to a tuple of ints."""
        return (int(p.x), int(p.y))

    def _wx_size_to_tuple(self, sz: wx.Size) -> Tuple[int, int]:
        """Convert a wx.Size (or compatible object) to a tuple of ints."""
        return (int(sz.GetWidth()), int(sz.GetHeight()))

    def _on_left_down(self, event: wx.MouseEvent) -> None:
        """Handle left mouse button down event."""
        if not event.ShiftDown() and self.metadata is None and self._on_request_open_file is not None:
            self._on_request_open_file()
            return
        if event.ShiftDown():
            self.is_shift_dragging = True
            self.selection_rect = None
        else:
            self.is_dragging = True
        p = event.GetPosition()
        self.drag_start_pos = self._wx_point_to_tuple(p)
        self.CaptureMouse()

    def _on_left_up(self, event: wx.MouseEvent) -> None:
        """Handle left mouse button up event."""
        if self.HasCapture():
            self.ReleaseMouse()

        if self.is_shift_dragging and self.selection_rect is not None:
            self._zoom_to_selection_rect()
            self.is_shift_dragging = False
            self.selection_rect = None
        elif self.is_dragging:
            self.is_dragging = False
            self._notify_zoom_changed()

        self.drag_start_pos = None
        self.Refresh()

    def _on_motion(self, event: wx.MouseEvent) -> None:
        """Handle mouse motion event."""
        if not event.Dragging():
            return

        p = event.GetPosition()
        current_pos = self._wx_point_to_tuple(p)

        if self.is_shift_dragging and self.drag_start_pos is not None:
            # Draw selection rectangle
            x1, y1 = self.drag_start_pos
            x2, y2 = current_pos
            self.selection_rect = (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            self.Refresh()
        elif self.is_dragging and self.drag_start_pos is not None:
            # Pan the view
            # Mouse movement is in display coordinates (pixels)
            # Divide by zoom_level to maintain consistent pan speed regardless of zoom
            # pan_x/pan_y are stored in display coordinates for simplicity
            dx = current_pos[0] - self.drag_start_pos[0]
            dy = current_pos[1] - self.drag_start_pos[1]
            self.pan_x += dx / self.zoom_level
            self.pan_y += dy / self.zoom_level
            self.drag_start_pos = current_pos
            self.Refresh()

    def _on_mouse_wheel(self, event: wx.MouseEvent) -> None:
        """Handle mouse wheel scroll event for zooming."""
        rotation = event.GetWheelRotation()
        z = self.ZOOM_STEP_FACTOR
        zoom_factor = z if rotation > 0 else 1.0 / z

        p = event.GetPosition()
        mouse_pos = self._wx_point_to_tuple(p)
        self._zoom_at_point(mouse_pos, zoom_factor)

    def zoom_at_video_center(self, zoom_factor: float) -> None:
        """Zoom about the center of the fitted video rectangle (includes current pan)."""
        sz = self.GetSize()
        pw, ph = self._wx_size_to_tuple(sz)
        cx = pw / 2.0 + self.pan_x
        cy = ph / 2.0 + self.pan_y
        self._zoom_at_point((cx, cy), zoom_factor)

    def _zoom_at_point(self, point: Tuple[float, float], zoom_factor: float) -> None:
        """Zoom in/out while keeping the video pixel under ``point`` fixed in panel space.

        Args:
            point: Panel coordinates (x, y) of the zoom anchor
            zoom_factor: Multiplier for zoom level (>1.0 zooms in, <1.0 zooms out)
        """
        old_zoom = self.zoom_level
        new_zoom = old_zoom * zoom_factor
        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, new_zoom))

        if new_zoom == old_zoom:
            return

        px, py = float(point[0]), float(point[1])

        if self.metadata is None:
            self.pan_x = px - (px - self.pan_x) * (new_zoom / old_zoom)
            self.pan_y = py - (py - self.pan_y) * (new_zoom / old_zoom)
            self.zoom_level = new_zoom
            self._notify_zoom_changed()
            self.Refresh()
            return

        sz = self.GetSize()
        pane_width, pane_height = self._wx_size_to_tuple(sz)
        if pane_width <= 0 or pane_height <= 0:
            self.zoom_level = new_zoom
            self._notify_zoom_changed()
            self.Refresh()
            return

        video_size = self.metadata.display_dimensions
        reference_size = self.display_size if self.scaling_mode == ScalingMode.MATCH_LARGER else None
        try:
            base_scale_x, base_scale_y = self.scaling_calculator.calculate_scale(
                video_size, (pane_width, pane_height), self.scaling_mode, reference_size
            )
        except ValueError:
            self.zoom_level = new_zoom
            self._notify_zoom_changed()
            self.Refresh()
            return

        base_scale = base_scale_x
        vw, vh = video_size
        new_pan_x, new_pan_y = self.scaling_calculator.adjust_pan_for_zoom_at_anchor(
            pane_width,
            pane_height,
            vw,
            vh,
            base_scale,
            old_zoom,
            new_zoom,
            self.pan_x,
            self.pan_y,
            px,
            py,
        )
        self.pan_x = new_pan_x
        self.pan_y = new_pan_y
        self.zoom_level = new_zoom
        self._notify_zoom_changed()
        self.Refresh()

    def _zoom_to_selection_rect(self) -> None:
        """Zoom to fit the selected rectangle region."""
        if self.selection_rect is None or self.metadata is None:
            return

        x, y, width, height = self.selection_rect

        if width <= 0 or height <= 0:
            return

        # Calculate zoom level needed to fit selection
        sz = self.GetSize()
        pane_width, pane_height = self._wx_size_to_tuple(sz)
        zoom_x = pane_width / width if width > 0 else self.zoom_level
        zoom_y = pane_height / height if height > 0 else self.zoom_level
        new_zoom = min(zoom_x, zoom_y)

        new_zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, new_zoom))

        # Center the selection
        self.pan_x = x + width / 2 - pane_width / (2 * new_zoom)
        self.pan_y = y + height / 2 - pane_height / (2 * new_zoom)

        self.zoom_level = new_zoom
        self._notify_zoom_changed()
        self.Refresh()

    def _on_paint(self, event: wx.PaintEvent) -> None:
        """Handle paint event to render the video frame."""
        dc = wx.PaintDC(self)
        self._render_frame(dc)
        if self.is_shift_dragging and self.selection_rect is not None:
            self._draw_selection_rect(dc)
        if self._drop_highlight:
            self._draw_drop_highlight(dc)

    def _render_frame(self, dc: wx.DC) -> None:
        """Render the current frame with zoom/pan transforms.

        Args:
            dc: Device context for drawing
        """
        sz = self.GetSize()
        pane_width, pane_height = self._wx_size_to_tuple(sz)

        if pane_width <= 0 or pane_height <= 0:
            return

        # Clear background
        dc.SetBackground(wx.Brush(wx.Colour(0, 0, 0)))
        dc.Clear()

        if self.metadata is None:
            self._draw_empty_state(dc, pane_width, pane_height)
            return

        if self.current_frame is None:
            self._draw_loaded_no_frame_state(dc, pane_width, pane_height)
            return

        try:
            # Calculate base scale for fitting video to display
            video_size = self.metadata.display_dimensions
            reference_size = self.display_size if self.scaling_mode == ScalingMode.MATCH_LARGER else None
            base_scale_x, base_scale_y = self.scaling_calculator.calculate_scale(
                video_size, (pane_width, pane_height), self.scaling_mode, reference_size
            )

            # Apply zoom level
            scale_x = base_scale_x * self.zoom_level
            scale_y = base_scale_y * self.zoom_level

            # Calculate scaled video dimensions
            scaled_width = int(video_size[0] * scale_x)
            scaled_height = int(video_size[1] * scale_y)

            # Convert frame to bitmap if needed
            if self._cached_bitmap is None:
                self._cached_bitmap = self._frame_to_bitmap(self.current_frame)

            # Pan offset is stored in display coordinates (pixels in the panel)
            # This allows pan to work consistently regardless of zoom level
            pan_offset_x = self.pan_x
            pan_offset_y = self.pan_y

            # Centered fit + pan (float pan; round once for pixel placement)
            draw_x = int(round((pane_width - scaled_width) / 2.0 + pan_offset_x))
            draw_y = int(round((pane_height - scaled_height) / 2.0 + pan_offset_y))

            # Create scaled bitmap
            # Note: wx.Bitmap cannot be scaled directly; must convert to wx.Image first
            # wx.Image.Scale() returns a new wx.Image, which we then convert back to wx.Bitmap
            if scaled_width > 0 and scaled_height > 0:
                scaled_bitmap = wx.Bitmap(self._cached_bitmap)
                scaled_bitmap = wx.Bitmap(scaled_bitmap.ConvertToImage().Scale(scaled_width, scaled_height))
                # DrawBitmap() uses display coordinates (pixels in the panel)
                # draw_x, draw_y are in display space, accounting for centering and pan offset
                dc.DrawBitmap(scaled_bitmap, draw_x, draw_y, False)

            # Draw overlays
            self._draw_overlays(dc, pane_width, pane_height)

        except Exception as e:
            raise RenderingError(f"Failed to render frame: {e}") from e

    def _frame_to_bitmap(self, frame: np.ndarray) -> wx.Bitmap:
        """Convert numpy array frame to wx.Bitmap.

        Data format requirements:
        - Input: NumPy array of shape (height, width, 3) in RGB format, dtype uint8
        - wx.Image.SetData() expects: contiguous bytes in row-major order, RGB interleaved
        - NumPy array layout: (height, width, 3) means [row][col][R,G,B] - already row-major
        - tobytes() produces bytes in row-major order: row0_col0_R, row0_col0_G, row0_col0_B, row0_col1_R, ...

        Args:
            frame: NumPy array of shape (height, width, 3) in RGB format

        Returns:
            wx.Bitmap object

        Raises:
            FrameConversionError: If conversion fails
        """
        try:
            height, width, channels = frame.shape
            if channels != 3:
                raise FrameConversionError(f"Expected 3 channels (RGB), got {channels}")

            # Convert to uint8 if needed (wx.Image expects 0-255 byte values)
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)

            # wx.Image.SetData() requires C_CONTIGUOUS memory layout (row-major, no gaps)
            # This ensures the bytes are laid out sequentially in memory without padding
            # If the array is a view or slice, it may not be contiguous
            if not frame.flags["C_CONTIGUOUS"]:
                frame = np.ascontiguousarray(frame)

            # Create wx.Image from RGB data
            # Note: wx.Image constructor takes (width, height) but frame is (height, width, 3)
            image = wx.Image(width, height)
            # SetData() expects raw bytes in RGB format, row-major order
            # tobytes() produces exactly this: all bytes from the array in row-major order
            image.SetData(frame.tobytes())
            return wx.Bitmap(image)
        except Exception as e:
            raise FrameConversionError(f"Failed to convert frame to bitmap: {e}") from e

    def _draw_drop_highlight(self, dc: wx.DC) -> None:
        """Draw a border while a file drag hovers over the pane."""
        sz = self.GetSize()
        w, h = self._wx_size_to_tuple(sz)
        if w <= 0 or h <= 0:
            return
        dc.SetPen(wx.Pen(wx.Colour(80, 160, 255), 3, wx.PENSTYLE_SOLID))
        dc.SetBrush(wx.Brush(wx.Colour(0, 0, 0), wx.BRUSHSTYLE_TRANSPARENT))
        dc.DrawRectangle(1, 1, w - 2, h - 2)

    def _draw_empty_state(self, dc: wx.DC, width: int, height: int) -> None:
        """Draw empty state when no video is loaded.

        Args:
            dc: Device context for drawing
            width: Panel width
            height: Panel height
        """
        dc.SetTextForeground(wx.Colour(128, 128, 128))
        dc.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        text = "No video loaded — click or drop a file"
        text_extent = dc.GetTextExtent(text)
        text_width = text_extent[0] if text_extent[0] is not None else 0
        text_height = text_extent[1] if text_extent[1] is not None else 0
        dc.DrawText(text, (width - text_width) // 2, (height - text_height) // 2)

    def _draw_loaded_no_frame_state(self, dc: wx.DC, width: int, height: int) -> None:
        """Draw state when video is loaded but no frame is available yet (e.g. only one pane loaded).

        Args:
            dc: Device context for drawing
            width: Panel width
            height: Panel height
        """
        dc.SetTextForeground(wx.Colour(160, 160, 160))
        dc.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        lines = []
        if self.metadata is not None and self.metadata.file_path is not None:
            lines.append(self.metadata.file_path.name)
        if self.metadata is not None:
            display_width, display_height = self.metadata.display_dimensions
            if (display_width, display_height) == self.metadata.dimensions:
                lines.append(f"{self.metadata.width}x{self.metadata.height}")
            else:
                lines.append(
                    f"{self.metadata.width}x{self.metadata.height} " f"(display {display_width}x{display_height})"
                )
        lines.append("Load the other video to compare")
        y = (height - len(lines) * 18) // 2
        for line in lines:
            if not line:
                continue
            text_extent = dc.GetTextExtent(line)
            text_width = text_extent[0] if text_extent[0] is not None else 0
            dc.DrawText(line, (width - text_width) // 2, y)
            y += 18

    @classmethod
    def _format_file_size(cls, size_bytes: int) -> str:
        """Format file size into friendly units (B, kB, MB, GB)."""
        size = float(size_bytes)
        unit_index = 0
        while size >= 1024.0 and unit_index < len(cls._FILE_SIZE_UNITS) - 1:
            size /= 1024.0
            unit_index += 1
        unit = cls._FILE_SIZE_UNITS[unit_index]
        if unit_index == 0:
            return f"{int(size)} {unit}"
        return f"{size:.1f} {unit}"

    @classmethod
    def _build_file_overlay_line(cls, path: Optional[Path]) -> Optional[str]:
        """Build overlay file line with friendly size when available."""
        if not hasattr(path, "name") or path is None:
            return None
        line = f"File: {path.name}"
        try:
            size_bytes = int(path.stat().st_size)
        except (OSError, ValueError, TypeError, AttributeError):
            return line
        return f"{line} ({cls._format_file_size(size_bytes)})"

    def _draw_overlays(self, dc: wx.DC, width: int, height: int) -> None:
        """Draw overlay information (filename, dimensions, time/frame, zoom level).

        Args:
            dc: Device context for drawing
            width: Panel width
            height: Panel height
        """
        if self.metadata is None:
            return

        dc.SetTextForeground(wx.Colour(255, 255, 255))
        dc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))

        overlay_lines = []
        if self.metadata.file_path is not None:
            file_line = self._build_file_overlay_line(self.metadata.file_path)
            if file_line is not None:
                overlay_lines.append(file_line)
        display_width, display_height = self.metadata.display_dimensions
        if (display_width, display_height) == self.metadata.dimensions:
            overlay_lines.append(
                f"Dimensions: {self.metadata.width}x{self.metadata.height} @ {self.metadata.fps:.3f} fps"
            )
        else:
            overlay_lines.append(
                f"Dimensions: {self.metadata.width}x{self.metadata.height} "
                f"(display {display_width}x{display_height}) @ {self.metadata.fps:.3f} fps"
            )
        overlay_lines.append(f"Time: {self.current_time:.3f}s / Frame: {self.current_frame_index}")
        overlay_lines.append(f"Zoom: {self.zoom_level:.2f}x")

        y_offset = 5
        for line in overlay_lines:
            dc.DrawText(line, 5, y_offset)
            line_extent = dc.GetTextExtent(line)
            line_height = line_extent[1] if line_extent[1] is not None else 0
            y_offset += line_height + 2

    def _draw_selection_rect(self, dc: wx.DC) -> None:
        """Draw selection rectangle for shift-drag zoom.

        Args:
            dc: Device context for drawing
        """
        if self.selection_rect is None:
            return

        x, y, w, h = self.selection_rect
        dc.SetPen(wx.Pen(wx.Colour(255, 255, 0), 2, wx.PENSTYLE_DOT))
        dc.SetBrush(wx.Brush(wx.Colour(255, 255, 0, 64)))
        dc.DrawRectangle(x, y, w, h)

    def set_frame(self, frame: Optional[np.ndarray]) -> None:
        """Set the current frame to display.

        Args:
            frame: NumPy array of shape (height, width, 3) in RGB format, or None for empty state
        """
        self.current_frame = frame
        self._cached_bitmap = None
        self.Refresh()

    def set_metadata(self, metadata: Optional[VideoMetadata]) -> None:
        """Set video metadata.

        Args:
            metadata: VideoMetadata object, or None to clear
        """
        self.metadata = metadata
        self._cached_bitmap = None
        self.Refresh()

    def set_on_request_open_file(self, callback: Optional[Callable[[], None]]) -> None:
        """Set callback invoked when user clicks on the pane while no video is loaded.

        Args:
            callback: Callable with no arguments, or None to clear
        """
        self._on_request_open_file = callback

    def set_on_files_dropped(self, callback: Optional[Callable[[Sequence[str]], None]]) -> None:
        """Set callback invoked when the user drops filesystem paths onto the pane.

        The first path is typically used. Same load path as File → Open for this pane.

        Args:
            callback: Callable receiving a sequence of path strings, or None to disable
        """
        self._on_files_dropped = callback

    def set_on_zoom_changed(self, callback: Optional[Callable[[], None]]) -> None:
        """Set callback invoked whenever this pane's zoom level changes."""
        self._on_zoom_changed = callback

    def _set_drop_highlight(self, active: bool) -> None:
        self._drop_highlight = active

    def _notify_zoom_changed(self) -> None:
        """Invoke the zoom-changed callback if configured."""
        if self._on_zoom_changed is not None:
            self._on_zoom_changed()

    def _deliver_dropped_files(self, filenames: Sequence[str]) -> bool:
        """Apply a drop of path strings. Returns True if the drop was handled."""
        if not self._on_files_dropped or not filenames:
            return False
        self._on_files_dropped(filenames)
        return True

    def set_scaling_mode(self, mode: ScalingMode) -> None:
        """Set scaling mode.

        Args:
            mode: ScalingMode enum value
        """
        self.scaling_mode = mode
        self.Refresh()

    def set_display_size(self, size: Tuple[int, int]) -> None:
        """Set display size for match_larger scaling mode.

        Args:
            size: (width, height) tuple
        """
        self.display_size = size
        self.Refresh()

    def set_playback_info(self, time: float, frame_index: int) -> None:
        """Set current playback time and frame index for overlay display.

        Args:
            time: Current playback time in seconds
            frame_index: Current frame index
        """
        self.current_time = time
        self.current_frame_index = frame_index
        self.Refresh()

    def reset_zoom_pan(self) -> None:
        """Reset zoom and pan to default values."""
        self.zoom_level = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._notify_zoom_changed()
        self.Refresh()

    @classmethod
    def is_default_pan_xy(cls, pan_x: float, pan_y: float) -> bool:
        """True if pan offsets match the default centered alignment."""
        return math.isclose(pan_x, 0.0, rel_tol=0.0, abs_tol=cls._PAN_ORIGIN_ABS_TOL) and math.isclose(
            pan_y, 0.0, rel_tol=0.0, abs_tol=cls._PAN_ORIGIN_ABS_TOL
        )

    def is_default_pan(self) -> bool:
        """True if this pane's pan is at the default centered position."""
        return self.is_default_pan_xy(self.pan_x, self.pan_y)

    def reset_pan_only(self) -> None:
        """Reset pan to default without changing zoom level."""
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._notify_zoom_changed()
        self.Refresh()

    def get_zoom_level(self) -> float:
        """Get current zoom level.

        Returns:
            Current zoom level
        """
        return self.zoom_level

    def get_pan_position(self) -> Tuple[float, float]:
        """Get current pan position.

        Returns:
            (pan_x, pan_y) tuple
        """
        return (self.pan_x, self.pan_y)
