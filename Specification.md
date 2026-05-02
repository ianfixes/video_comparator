
# Specification: Video Comparison GUI Tool

## Overview

This software project aims to deliver a cross-platform graphical user interface (GUI) application enabling detailed, side-by-side visual comparison of two video files. The primary user group includes those evaluating video encoding quality, emphasizing high-fidelity, frame-accurate display with support for zooming and close inspection for expert, frame-by-frame analysis.

---

## Functional Requirements

1. **Cross-Platform GUI**
   - The application shall be built using a cross-platform GUI toolkit, preferably GNU-based (e.g., Qt, GTK, wxWidgets), to ensure compatibility with at least OSX and Linux desktops.
   - The application must not depend on platform-specific video decoders, and should use well-supported open-source video processing libraries (such as FFmpeg or GStreamer).
   - On normal startup, the main window shall request activation and come to the foreground (receive keyboard focus where the OS allows). Platform policies may prevent activation in some contexts (e.g. launching from certain terminals or background services); the implementation should follow wxWidgets best practices for raising the frame after `Show()`.

2. **Dual Video Display**
   - The application shall allow the user to load two independent video files.
   - Loading shall be available via **File > Open Video 1** and **File > Open Video 2** (or equivalent shortcuts). Each menu item opens a file chooser and loads the selected file into the corresponding pane.
   - Clicking the empty video pane (or the "no video loaded" placeholder text) shall open the file chooser for that pane, so users can load a video by clicking where it will appear.
   - Both videos shall be displayed simultaneously, in a side-by-side or stacked configuration.
   - Users must be able to toggle the layout between vertical (top/bottom) and horizontal (left/right) split (e.g. via **View > Toggle Layout** and keyboard shortcut).
   - Each video pane should display the same current frame (after sync adjustments).
   - Both videos are displayed within matched bounding boxes, ensuring that the comparison area is visually consistent, regardless of original dimensions.
   - If the source dimensions differ, users can toggle between two modes (e.g. via **View → Toggle Scaling Mode**):
     1. Each video scaled to fill its own bounding box (preserving aspect ratio).
     2. The larger video fills the box, and the smaller video is scaled proportionally to the displayed size of the larger one.
   - Each video's native dimensions must be displayed in text.
   - Display geometry must honor stream/display aspect metadata. For sources with non-square pixels (anamorphic content), rendering must use display aspect ratio semantics (e.g., SAR/DAR) rather than coded raster dimensions alone.
   - The system must permit zooming in both panes to analyze specific regions of the videos in more detail.

3. **Timeline Navigation**
   - There must be a slider at the bottom of the window representing the timeline of the videos.
   - Dragging or clicking the slider moves both videos to the specified timestamp/frame, keeping them synchronized (with applicable sync offsets).
   - When the user changes the timeline position (e.g. by dragging the slider), the application shall request and display the frame(s) at the new position.
   - The current playback time/frame should be displayed for each video.

4. **Frame-by-Frame Control**
   - Hotkeys and on-screen buttons must allow users to skip forward or backward a single frame in both videos simultaneously.
   - Frame-step hotkeys/buttons should work even when the videos are paused.

5. **Playback Control**
   - There must be play, pause, and stop controls to start or stop both videos simultaneously and in sync.
   - The **play** button shall be enabled only when at least one video is loaded; it shall be disabled when no video is loaded.
   - When only one video is loaded, that video shall still be playable (play, pause, stop, frame step, and timeline seek).
   - Playback should maintain synchronization between both videos (within the configured sync settings).

6. **Sync Adjustment Controls for Second Video**
   - Sync adjustment controls (slider and +/-1 frame buttons) shall be enabled only when **both** videos are loaded; they shall be disabled when fewer than two videos are loaded.
   - The second video must feature at the top:
     - A slider for rough adjustment of sync offset relative to the first video (expressed in frames, positive or negative).
     - "+" and "-" buttons for precise adjustment: shifting the second video's position by one frame forward or backward.
   - The effective sync offset must be visually indicated.

7. **Zoom and Region Inspection**
   - The application must provide controls and/or hotkeys to zoom in and out on the video display area, as well as to reset zoom to default.
   - Mouse interactions for zoom and pan:
     - **Mouse drag**: Clicking and dragging the mouse within a video pane must pan the zoomed region, allowing users to inspect different areas of the frame.
     - **Scroll wheel**: Scrolling the mouse wheel over a video pane must zoom in (scroll up) or zoom out (scroll down) on that pane.
     - **Shift-drag rectangle**: Holding Shift while clicking and dragging must draw a selection rectangle, and releasing the mouse must zoom to fit the selected region.
   - Zoom must be supported independently or synchronously for each video pane, allowing detailed comparison.
   - The zoom state (level and pan position) must remain consistent during video playback, frame stepping, and when seeking the timeline.
   - When a video file is successfully loaded into a pane (including via **File → Open**, click-to-open on an empty pane, drag-and-drop, or CLI startup paths), **that pane's** zoom factor and pan position shall reset to their defaults (1× zoom and default centered pan for the renderer). If zoom is **synchronized** across both panes, loading a new file into either pane shall reset zoom and pan for **both** panes so magnifications stay aligned.
   - The zoom feature must not interfere with video synchronization or performance.
   - Tooltips and UI labels must clarify the functionality and shortcuts for zoom and pan actions.
   - The zoom level label in the control panel shall use **red** foreground text whenever **any** zoom factor shown in that label is **not exactly** 1×, and default/neutral foreground (e.g. standard window text colour) when **every** displayed factor is exactly 1× — regardless of synchronized vs independent zoom mode.
   - The **Reset Zoom** button shall be **enabled** only when at least one pane's zoom factor is **not exactly** 1× (same numerical notion of “exactly 1×” as for the label); it shall be **disabled** when **both** panes are exactly 1×. Its action restores **both** zoom (to 1×) **and** pan (to each pane's default centered alignment) for every pane it affects — consistent with synchronized vs independent zoom behaviour already used for zoom operations.
   - A **Reset Pan** button shall appear **immediately to the right** of the zoom level label. It shall be **disabled** when **both** panes are at their default pan position (“properly centered” in renderer coordinates); **enabled** when **either** pane's pan differs from that default. When invoked, it resets **only** panning — **not** zoom — on **both** panes (zoom level unchanged), restoring each pane's pan to its default centered alignment.
   - **Interaction note (non-normative):** Zoom operations (e.g. scaling about the cursor or fitting a region) may change pan components as part of maintaining anchor semantics. This specification does **not** require normalizing or splitting those effects; users rely on **Reset Zoom** to restore both zoom and pan, and **Reset Pan** to correct pan only without changing magnification.

---

## Additional Requirements & Considerations

8. **Frame Accuracy**
   - The application must ensure precise, frame-accurate seeking and display for both videos.
   - The timeline and frame step operations must account for differences in framerate or timestamp precision between source files.

9. **Performance**
   - The tool should pre-buffer frames as needed to minimize seek latency.
   - It should support hardware acceleration if available but remain functional via software decoding.
   - Zoom operations should be smooth and low-latency, even during playback.

10. **Supported Formats**
    - The application must support a range of commonly used video formats (e.g., .mp4, .mkv, .avi, ProRes, H.264, H.265), depending on backend capabilities.

11. **User Interface and Usability**
    - Each pane should display video filename, coded resolution, display dimensions/aspect context (when non-square pixel metadata is present), and playback time/frame.
    - Tooltips and labels should clarify the purpose of all controls, including zoom and pan features.
    - Keyboard shortcuts must be documented and customizable if possible.
    - UI should clearly indicate the current zoom level and allow resetting the view easily (including non-default zoom called out via label coloring per §7, **Reset Zoom** / **Reset Pan** enablement per §7, and tooltips that distinguish “reset magnification + pan” from “reset pan only”).

12. **Error Handling**
    - Graceful handling of unsupported formats, missing codecs, or video loading errors.
    - Clear error messages and user guidance.
    - Each subsystem defines per-class exceptions matching its responsibilities:
      - Media Loading: file validation, format errors, missing codecs
      - Decode Engine: decode failures, seek errors, unsupported formats
      - Frame Cache: cache capacity errors, invalid frame indices
      - Prefill Strategy: strategy-specific errors (e.g., frames not generated)
      - Timeline Controller: invalid positions, out-of-range seeks
      - Playback Controller: playback state errors, synchronization failures
    - Exceptions are caught at appropriate boundaries and displayed via ErrorHandler with user-friendly messages.

13. **Project Extensibility**
    - The GUI and backend should be designed for modularity, allowing future expansion (e.g., annotation tools, quality metrics overlays, multi-video support).

---

## Out of Scope

- Automated/computed video quality metrics (PSNR, SSIM, VMAF) are not required in this version, but the design should allow for future integration.
- Support for Windows is not a requirement, though should not be blocked by the design.

---

## End Goal

At completion, users will be able to:
- Load two video files.
- Align them accurately.
- Step through individual or sequences of frames.
- Visually compare corresponding frames at any timestamp, with adjustable sync for imperfect sources.
- Inspect fine detail in both videos via zoom and pan controls, with both videos scaled to equal presentation area for direct visual comparison.
- Use a responsive and intuitive interface suited for expert video quality evaluation.
