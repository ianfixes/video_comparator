# Architecture

This document outlines the major subsystems for the video comparator. Each subsystem is isolated so it can be developed and tested independently.

## Stack Baseline
- GUI: wxPython (wx.Frame, wx.Panel, custom drawing with wx.PaintDC)
- Video decode: PyAV (FFmpeg) for frame-accurate seeking/decoding
- Data handling: NumPy for frame buffers and transforms
- Tests: pytest (unit + integration), mypy for types, black/isort for style

## Subsystems

### 1) Application Shell & Composition
#### Responsibilities
- bootstrap
- dependency wiring
- global event loop
- top-level menu/toolbars
- quitting lifecycle.
#### Testability
- unit tests for wiring (mocks)
- smoke tests that instantiate the app without loading media.

### 2) Media Loading & Metadata
#### Responsibilities
- file selection
- validation
- probing via PyAV (duration, fps, dimensions, pixel format, total_frames, time_base)
- user-facing errors for unsupported formats.
#### Testability
- unit tests with known media samples from `tests/sample_data/`
- error-path tests for missing/invalid files.

### 3) Decode Engine (per video)
#### Responsibilities
- open containers
- frame-accurate seek (time- or frame-based)
- decode to NumPy arrays
- handle differing fps/timebases.
#### Testability
- unit tests on deterministic sample clips to assert decoded frame indices/timestamps
- test files from `tests/sample_data/` directory.

**Note:** Hardware acceleration is not implemented to keep dependencies simple.

### 4) Frame Cache & Prebuffer
#### Responsibilities
- LRU eviction policy with protected frame set
- memory bounds management
- frame storage and retrieval
- integration with PrefillStrategy to protect frames from eviction
#### Testability
- unit tests for cache hit/miss behavior and LRU eviction
- unit tests for protected frame behavior
- timing-free logic tests.

### 4a) Prefill Strategy
#### Responsibilities
- defines which frames should be protected from cache eviction
- generates frame numbers in priority order (does not need to know cache capacity)
- tracks how many frames were actually consumed by the cache
- can reconstruct the protected frame set based on consumed count
- swappable strategy pattern for different prefetching approaches
#### Design
- Strategies generate frames via `generate_protected_frames()` generator
- FrameCache consumes frames until it reaches capacity
- Strategy tracks consumed count via `_cacheable_frame_count`
- `protected_frames()` method reconstructs the protected set deterministically
- Frame order must be deterministic and consistent for reconstruction
- Strategies do not need to know cache capacity in advance
#### Creation & Lifecycle
- PrefillStrategy instances are created and updated by PlaybackController (not TimelineController)
- PlaybackController queries TimelineController for resolved frame numbers for each video
- Separate PrefillStrategy instances are created for each video's FrameCache
- Strategies are updated when position changes or playback state changes
#### Testability
- unit tests for protected frame calculation
- unit tests for different strategy implementations (ring buffer, predictive, etc.)
- unit tests for cacheable_frame_count tracking
- unit tests for protected_frames reconstruction

### 5) Sync & Timeline Controller
#### Responsibilities
- single source of truth for playback position and per-video sync offsets (slider and ±1 frame nudges)
- all seeks/steps go through this controller
- converts between wall-clock, timestamps, and frame indices
- provides resolved target frame/time to consumers.

#### Testability
- pure logic tests for offset math
- frame/time conversions
- layout-mode impacts on displayed sizes.

### 6) Playback & Stepping Controller
#### Responsibilities
- play/pause/stop state machine
- frame-step forward/backward even when paused
- drives tick events that request frames from the cache/decoder
- delegates position math to Sync
- maintains lockstep between videos respecting offsets
- creates and updates PrefillStrategy instances for each video's FrameCache
  - queries TimelineController for resolved frame numbers
  - creates separate PrefillStrategy instances per video (accounting for different framerates/offsets)
  - updates strategies when position or playback state changes
#### Testability
- unit tests on state transitions and emitted requests
- simulated tick tests without GUI
- tests for PrefillStrategy creation and updates

### 7) Render Layer (Video Panes)
#### Responsibilities
- draw frames into wx.Panel using wx.PaintDC
- apply zoom/pan transforms
- support two scaling modes (independent fit vs. match larger video)
- matched bounding boxes for comparison
- overlays for filename
- native dimensions
- playback time/frame
- zoom level
- maintain zoom/pan state across seeks/steps/layout changes
- mouse interactions:
  - mouse drag for panning
  - scroll wheel for zoom in/out
  - Shift-drag rectangle for zoom to region
#### Testability
- logic tests for transform math (pan/zoom/fit calculations)
- mouse event handling tests (drag, wheel, Shift-drag)
- golden-image tests optional via offscreen buffers.

### 8) Layout & Controls
#### Responsibilities
- toggle orientation (horizontal/vertical) and scaling mode (independent fit vs. match larger video)
- timeline slider
- play/pause/stop
- frame-step buttons
- sync-offset slider + ±1 buttons
- zoom controls (in/out/reset)
- layout mode toggle
- routes UI events to controllers.
#### Testability
- event wiring tests (signals -> controller calls)
- deterministic UI command tests with mocks.

### 9) Input & Shortcuts
#### Responsibilities
- keyboard shortcuts for
  - play/pause
  - step
  - zoom
  - sync nudge
  - layout toggle
- tooltip/help text
- optional shortcut customization
- unified dispatch so buttons and keys hit the same controller actions.
#### Testability
- keybinding maps are pure data
- unit tests ensure commands dispatch to controllers.
