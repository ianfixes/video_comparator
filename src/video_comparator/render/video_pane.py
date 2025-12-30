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

        # Mouse interaction state
        self.is_dragging: bool = False
        self.drag_start_pos: Optional[Tuple[int, int]] = None
        self.selection_rect: Optional[Tuple[int, int, int, int]] = None
        self.is_shift_dragging: bool = False

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

        # Adjust pan to keep the point under the mouse fixed
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
        # TODO: Implement frame rendering with zoom/pan transforms
        # TODO: Draw selection rectangle if is_shift_dragging
        pass
