
# Specification: Video Comparison GUI Tool

## Overview

This software project aims to deliver a cross-platform graphical user interface (GUI) application enabling detailed, side-by-side visual comparison of two video files. The primary user group includes those evaluating video encoding quality, emphasizing high-fidelity, frame-accurate display with support for zooming and close inspection for expert, frame-by-frame analysis.

---

## Functional Requirements

1. **Cross-Platform GUI**
   - The application shall be built using a cross-platform GUI toolkit, preferably GNU-based (e.g., Qt, GTK, wxWidgets), to ensure compatibility with at least OSX and Linux desktops.
   - The application must not depend on platform-specific video decoders, and should use well-supported open-source video processing libraries (such as FFmpeg or GStreamer).

2. **Dual Video Display**
   - The application shall allow the user to load two independent video files.
   - Both videos shall be displayed simultaneously, in a side-by-side or stacked configuration.
   - Users must be able to toggle the layout between vertical (top/bottom) and horizontal (left/right) split.
   - Each video pane should display the same current frame (after sync adjustments).
   - Both videos must be scaled to fit inside a common, matched bounding box, ensuring a visually consistent area for comparison, regardless of source dimensions.
   - Each video's native dimensions must be displayed in text.
   - The system must permit zooming in both panes to analyze specific regions of the videos in more detail.

3. **Timeline Navigation**
   - There must be a slider at the bottom of the window representing the timeline of the videos.
   - Dragging or clicking the slider moves both videos to the specified timestamp/frame, keeping them synchronized (with applicable sync offsets).
   - The current playback time/frame should be displayed for each video.

4. **Frame-by-Frame Control**
   - Hotkeys and on-screen buttons must allow users to skip forward or backward a single frame in both videos simultaneously.
   - Frame-step hotkeys/buttons should work even when the videos are paused.

5. **Playback Control**
   - There must be play, pause, and stop controls to start or stop both videos simultaneously and in sync.
   - Playback should maintain synchronization between both videos (within the configured sync settings).

6. **Sync Adjustment Controls for Second Video**
   - The second video must feature at the top:
     - A slider for rough adjustment of sync offset relative to the first video (expressed in frames, positive or negative).
     - "+" and "-" buttons for precise adjustment: shifting the second video's position by one frame forward or backward.
   - The effective sync offset must be visually indicated.

7. **Zoom and Region Inspection**
   - The application must provide controls and/or hotkeys to zoom in and out on the video display area, as well as to reset zoom to default.
   - Users must be able to use the mouse (click-and-drag or similar) to pan the zoomed region within each video pane for detailed area inspection.
   - Zoom must be supported independently or synchronously for each video pane, allowing detailed comparison.
   - The zoom state (level and pan position) must remain consistent during video playback, frame stepping, and when seeking the timeline.
   - The zoom feature must not interfere with video synchronization or performance.
   - Tooltips and UI labels must clarify the functionality and shortcuts for zoom and pan actions.

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
    - Each pane should display video filename, resolution, native video dimensions, and playback time/frame.
    - Tooltips and labels should clarify the purpose of all controls, including zoom and pan features.
    - Keyboard shortcuts must be documented and customizable if possible.
    - UI should clearly indicate the current zoom level and allow resetting the view easily.

12. **Error Handling**
    - Graceful handling of unsupported formats, missing codecs, or video loading errors.
    - Clear error messages and user guidance.

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
