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

from typing import Optional, Tuple

import numpy as np
import wx

from video_comparator.common.types import ScalingMode
from video_comparator.media.video_metadata import VideoMetadata
from video_comparator.render.scaling_calculator import ScalingCalculator


class RenderingError(Exception):
    """Base exception for rendering errors."""


class FrameConversionError(RenderingError):
    """Raised when frame conversion to wx.Bitmap fails."""


class VideoPane(wx.Panel):
    """Custom wx.Panel for rendering video frames with zoom/pan."""

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

        # Cached bitmap for current frame
        self._cached_bitmap: Optional[wx.Bitmap] = None

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
        zoom_factor = 1.1 if rotation > 0 else 1.0 / 1.1

        # Get mouse position in video coordinates for zoom center
        p = event.GetPosition()
        mouse_pos = self._wx_point_to_tuple(p)
        self._zoom_at_point(mouse_pos, zoom_factor)

    def _zoom_at_point(self, point: Tuple[int, int], zoom_factor: float) -> None:
        """Zoom in/out centered at a specific point.

        Args:
            point: Screen coordinates (x, y) where zoom should be centered
            zoom_factor: Multiplier for zoom level (>1.0 zooms in, <1.0 zooms out)
        """
        old_zoom = self.zoom_level
        new_zoom = old_zoom * zoom_factor

        # Constrain zoom level to reasonable bounds
        min_zoom = 0.1
        max_zoom = 10.0
        new_zoom = max(min_zoom, min(max_zoom, new_zoom))

        if new_zoom == old_zoom:
            return

        # Adjust pan to keep the point under the mouse fixed during zoom
        # This ensures the pixel under the cursor stays under the cursor when zooming
        # Formula: new_pan = mouse_pos - (mouse_pos - old_pan) * zoom_ratio
        # This maintains the visual position of the point under the mouse
        px, py = point
        self.pan_x = px - (px - self.pan_x) * (new_zoom / old_zoom)
        self.pan_y = py - (py - self.pan_y) * (new_zoom / old_zoom)

        self.zoom_level = new_zoom
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

        # Constrain zoom level
        min_zoom = 0.1
        max_zoom = 10.0
        new_zoom = max(min_zoom, min(max_zoom, new_zoom))

        # Center the selection
        self.pan_x = x + width / 2 - pane_width / (2 * new_zoom)
        self.pan_y = y + height / 2 - pane_height / (2 * new_zoom)

        self.zoom_level = new_zoom
        self.Refresh()

    def _on_paint(self, event: wx.PaintEvent) -> None:
        """Handle paint event to render the video frame."""
        dc = wx.PaintDC(self)
        self._render_frame(dc)
        if self.is_shift_dragging and self.selection_rect is not None:
            self._draw_selection_rect(dc)

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

        if self.current_frame is None or self.metadata is None:
            self._draw_empty_state(dc, pane_width, pane_height)
            return

        try:
            # Calculate base scale for fitting video to display
            video_size = self.metadata.dimensions
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

            # Calculate drawing position (centered with pan)
            # Centering: place scaled video in middle of pane
            # Pan: offset from center based on user drag interactions
            # All coordinates are in display space (panel pixels)
            draw_x = (pane_width - scaled_width) // 2 + int(pan_offset_x)
            draw_y = (pane_height - scaled_height) // 2 + int(pan_offset_y)

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

    def _draw_empty_state(self, dc: wx.DC, width: int, height: int) -> None:
        """Draw empty state when no frame is available.

        Args:
            dc: Device context for drawing
            width: Panel width
            height: Panel height
        """
        dc.SetTextForeground(wx.Colour(128, 128, 128))
        dc.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        text = "No video loaded"
        text_extent = dc.GetTextExtent(text)
        text_width = text_extent[0] if text_extent[0] is not None else 0
        text_height = text_extent[1] if text_extent[1] is not None else 0
        dc.DrawText(text, (width - text_width) // 2, (height - text_height) // 2)

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
            overlay_lines.append(f"File: {self.metadata.file_path.name}")
        overlay_lines.append(f"Dimensions: {self.metadata.width}x{self.metadata.height}")
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
