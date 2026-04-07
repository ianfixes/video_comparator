# User Workflow → Subsystem Mapping

This captures the primary user workflow and the subsystems responsible for each step. Each step should be testable via controllers (logic) and, where applicable, UI event bindings.

1) Load a video file into each of the 2 panes
- Media Loading & Metadata: file selection, probing, validation, user-facing errors.
- Decode Engine: open containers, prepare streams.
- Frame Cache: optional prebuffer near start position.
- Application Shell: coordinates UI flow.

2) Drag the time slider to a clear transition (both videos)
- Sync & Timeline Controller: single source of truth for position; applies offsets.
- Playback & Stepping Controller: issues seeks via Sync.
- Frame Cache: prebuffer around the new position.
- Decode Engine: seek/decode requested frames.

3) Adjust timing of the second video to align to the same frame as the first
- Sync & Timeline Controller: per-video offset math (slider, ±1 frame).
- Playback & Stepping Controller: applies resolved positions from Sync.
- Frame Cache: serves frames after offset adjustments.

4) Step forward/back a few frames to confirm alignment
- Playback & Stepping Controller: frame-step logic (paused or playing).
- Sync & Timeline Controller: resolves target frame/time with offsets.
- Frame Cache: supplies frames for rapid stepping.

5) Drag the time slider to another important area
- Sync & Timeline Controller: handles seek target.
- Playback & Stepping Controller: performs the seek.
- Frame Cache: rebuffer around target.
- Decode Engine: seek/decode as needed.

6) Zoom into a specific area to inspect clarity
- Render Layer: zoom/pan transforms, matched bounding boxes, overlays.
- Layout & Controls: zoom UI actions (in/out/reset).
- Input & Shortcuts: hotkeys for zoom/pan.

7) Step forward/back while inspecting the zoomed area
- Playback & Stepping Controller: step/play ticks.
- Sync & Timeline Controller: resolves positions per offset.
- Render Layer: preserves zoom/pan across seeks/steps.
- Frame Cache: provides frames for responsive stepping.
