"""Layout manager for video panes.

Responsibilities:
- Toggle orientation (horizontal/vertical)
- Toggle scaling mode (independent fit vs. match larger video)
- Manage pane sizing and positioning
"""

from typing import Tuple

from video_comparator.common.types import LayoutOrientation, ScalingMode
from video_comparator.render.video_pane import VideoPane


class LayoutManager:
    """Manages the layout of video panes and controls."""

    def __init__(
        self,
        video_pane1: VideoPane,
        video_pane2: VideoPane,
        orientation: LayoutOrientation = LayoutOrientation.HORIZONTAL,
        scaling_mode: ScalingMode = ScalingMode.INDEPENDENT,
    ) -> None:
        """Initialize layout manager with video panes, orientation, and scaling mode.

        Args:
            video_pane1: First video pane widget
            video_pane2: Second video pane widget
            orientation: Initial layout orientation (default: HORIZONTAL)
            scaling_mode: Initial scaling mode (default: INDEPENDENT)
        """
        self.video_pane1: VideoPane = video_pane1
        self.video_pane2: VideoPane = video_pane2
        self.orientation: LayoutOrientation = orientation
        self.scaling_mode: ScalingMode = scaling_mode

    def toggle_orientation(self) -> LayoutOrientation:
        """Toggle between horizontal and vertical orientation.

        Returns:
            The new orientation after toggling
        """
        self.orientation = (
            LayoutOrientation.VERTICAL
            if self.orientation == LayoutOrientation.HORIZONTAL
            else LayoutOrientation.HORIZONTAL
        )
        self._update_layout()
        return self.orientation

    def toggle_scaling_mode(self) -> ScalingMode:
        """Toggle between independent and match_larger scaling modes.

        Returns:
            The new scaling mode after toggling
        """
        self.scaling_mode = (
            ScalingMode.MATCH_LARGER if self.scaling_mode == ScalingMode.INDEPENDENT else ScalingMode.INDEPENDENT
        )
        self._update_layout()
        return self.scaling_mode

    def set_orientation(self, orientation: LayoutOrientation) -> None:
        """Set the layout orientation.

        Args:
            orientation: LayoutOrientation enum value
        """
        if self.orientation != orientation:
            self.orientation = orientation
            self._update_layout()

    def set_scaling_mode(self, scaling_mode: ScalingMode) -> None:
        """Set the scaling mode.

        Args:
            scaling_mode: ScalingMode enum value
        """
        if self.scaling_mode != scaling_mode:
            self.scaling_mode = scaling_mode
            self._update_layout()

    def calculate_pane_sizes(
        self, container_width: int, container_height: int
    ) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Calculate the size for each video pane based on orientation.

        Args:
            container_width: Total width of the container
            container_height: Total height of the container

        Returns:
            Tuple of ((pane1_width, pane1_height), (pane2_width, pane2_height))

        Raises:
            ValueError: If container dimensions are invalid
        """
        if container_width <= 0 or container_height <= 0:
            raise ValueError(f"Container dimensions must be positive, got ({container_width}, {container_height})")

        if self.orientation == LayoutOrientation.HORIZONTAL:
            pane_width = container_width // 2
            pane_height = container_height
            return ((pane_width, pane_height), (pane_width, pane_height))
        else:
            pane_width = container_width
            pane_height = container_height // 2
            return ((pane_width, pane_height), (pane_width, pane_height))

    def calculate_matched_bounding_box(
        self, pane1_size: Tuple[int, int], pane2_size: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Calculate matched bounding box size for match_larger scaling mode.

        When in match_larger mode, both videos should be displayed at the same size.
        This method calculates the size that both panes should use, which is the
        size of the larger pane.

        Args:
            pane1_size: (width, height) of first pane
            pane2_size: (width, height) of second pane

        Returns:
            (width, height) tuple representing the matched bounding box size
        """
        pane1_width, pane1_height = pane1_size
        pane2_width, pane2_height = pane2_size

        pane1_area = pane1_width * pane1_height
        pane2_area = pane2_width * pane2_height

        if pane1_area >= pane2_area:
            return pane1_size
        else:
            return pane2_size

    def update_layout(self, container_width: int, container_height: int) -> None:
        """Update the layout of video panes based on current settings.

        This method:
        1. Calculates pane sizes based on orientation
        2. Calculates matched bounding box if in match_larger mode
        3. Updates both VideoPanes with new scaling mode and display sizes

        Args:
            container_width: Total width of the container
            container_height: Total height of the container

        Raises:
            ValueError: If container dimensions are invalid
        """
        pane1_size, pane2_size = self.calculate_pane_sizes(container_width, container_height)

        if self.scaling_mode == ScalingMode.MATCH_LARGER:
            matched_size = self.calculate_matched_bounding_box(pane1_size, pane2_size)
            self.video_pane1.set_display_size(matched_size)
            self.video_pane2.set_display_size(matched_size)
        else:
            self.video_pane1.set_display_size((0, 0))
            self.video_pane2.set_display_size((0, 0))

        self.video_pane1.set_scaling_mode(self.scaling_mode)
        self.video_pane2.set_scaling_mode(self.scaling_mode)

    def _update_layout(self) -> None:
        """Internal method to update layout when orientation or scaling mode changes.

        This method updates the scaling mode on both panes immediately.
        The actual pane sizing will be handled by the parent container (e.g., MainFrame)
        when it calls update_layout() with the container dimensions.
        """
        self.video_pane1.set_scaling_mode(self.scaling_mode)
        self.video_pane2.set_scaling_mode(self.scaling_mode)

        if self.scaling_mode == ScalingMode.MATCH_LARGER:
            try:
                pane1_size = self.video_pane1.GetSize()
                pane2_size = self.video_pane2.GetSize()

                if pane1_size.IsFullySpecified() and pane2_size.IsFullySpecified():
                    pane1_tuple = (pane1_size.GetWidth(), pane1_size.GetHeight())
                    pane2_tuple = (pane2_size.GetWidth(), pane2_size.GetHeight())
                    matched_size = self.calculate_matched_bounding_box(pane1_tuple, pane2_tuple)
                    self.video_pane1.set_display_size(matched_size)
                    self.video_pane2.set_display_size(matched_size)
            except Exception:
                pass
        else:
            self.video_pane1.set_display_size((0, 0))
            self.video_pane2.set_display_size((0, 0))
