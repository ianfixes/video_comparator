"""Video pane widget for rendering frames.

Responsibilities:
- Draw frames into wx.Panel using wx.PaintDC
- Apply zoom/pan transforms
- Support two scaling modes (independent fit vs. match larger video)
- Matched bounding boxes for comparison
- Overlays for filename, native dimensions, playback time/frame, zoom level
- Maintain zoom/pan state across seeks/steps/layout changes
"""

from typing import Optional, Tuple

import numpy as np
import wx

from video_comparator.common.types import ScalingMode
from video_comparator.media.metadata import VideoMetadata
from video_comparator.render.scaling import ScalingCalculator


class VideoPane:
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
        self.parent: wx.Window = parent
        self.scaling_calculator: ScalingCalculator = scaling_calculator
        self.metadata: Optional[VideoMetadata] = metadata
        self.current_frame: Optional[np.ndarray] = None
        self.zoom_level: float = 1.0
        self.pan_x: float = 0.0
        self.pan_y: float = 0.0
        self.scaling_mode: ScalingMode = ScalingMode.INDEPENDENT
        self.display_size: Tuple[int, int] = (0, 0)
