# TODO: Video Comparator Implementation Plan

This document outlines the implementation plan from lowest-level modules to highest-level modules. Each module should be completed and tested before dependent modules are implemented.

## Phase 1: Foundation (No Dependencies)

### ✅ Common Types (`common/types.py`)
- [x] Define `LayoutOrientation` enum
- [x] Define `ScalingMode` enum
- [x] Define `PlaybackState` enum (STOPPED, PLAYING, PAUSED)
- [ ] Define `FrameRequestStatus` enum (SUCCESS, CANCELLED, DECODE_ERROR, SEEK_ERROR, OUT_OF_RANGE)
- [ ] Define `FrameResult` dataclass (frame_number, frame, status, error)

**Unit Tests Required:**
- [x] Test FrameRequestStatus enum values
- [x] Test FrameResult initialization with success case
- [x] Test FrameResult initialization with error cases
- [x] Test FrameResult with None frame and status

---

## Phase 2: Data Structures

### Settings (`config/settings.py`)
- [x] Implement Settings class with all fields
- [x] Add validation for enum values
- [x] Add serialization/deserialization methods (for persistence)

**Unit Tests Required:**
- [x] Test Settings initialization with defaults
- [x] Test Settings initialization with custom values
- [x] Test Settings enum field validation
- [x] Test Settings serialization to dict/JSON
- [x] Test Settings deserialization from dict/JSON

### VideoMetadata (`media/video_metadata.py`)
- [x] Implement VideoMetadata class with all PyAV fields (duration, fps, width, height, pixel_format, total_frames, time_base)
- [x] Implement `dimensions` property
- [x] Add validation for metadata values (positive durations, fps, dimensions)

**Unit Tests Required:**
- [x] Test VideoMetadata initialization with valid data
- [x] Test `dimensions` property returns correct tuple
- [x] Test VideoMetadata validation (reject negative/zero values)
- [x] Test VideoMetadata with edge cases (very large dimensions, high fps)

### KeyBinding (`input/shortcut_manager.py`)
- [x] Implement KeyBinding class using wxPython key code constants (wx.WXK_*)
- [x] Add validation for key codes and modifiers (wx.MOD_*)

**Unit Tests Required:**
- [x] Test KeyBinding initialization with wxPython key codes
- [x] Test KeyBinding equality comparison
- [x] Test KeyBinding validation for valid/invalid key codes

---

## Phase 3: Utility Classes

### MetadataExtractor (`media/video_metadata.py`)
- [x] Implement PyAV container opening
- [x] Implement video stream detection
- [x] Implement metadata extraction (duration, fps, dimensions, pixel format, total frames, time_base)
- [x] Implement error handling for unsupported formats
- [x] Add support for multiple video streams (select first video stream)
- [x] Define per-class exceptions for metadata errors (e.g., `MetadataExtractionError`, `UnsupportedFormatError`, `NoVideoStreamError`)

**Unit Tests Required:**
- [x] Test metadata extraction from known test video file (from `tests/sample_data/`)
- [x] Test extraction of all required fields (duration, fps, width, height, pixel_format, total_frames, time_base)
- [x] Test error handling for missing file
- [x] Test error handling for unsupported format
- [x] Test error handling for file with no video stream
- [x] Test with videos of different formats (MP4, MKV, AVI)
- [x] Test with videos of different codecs (H.264, H.265, ProRes)

**Note:** Test video files are available in `tests/sample_data/` directory. Use `file_example_AVI_*.avi` files for testing.

### ScalingCalculator (`render/scaling_calculator.py`)
- [x] Implement `calculate_scale` method for independent mode
- [x] Implement `calculate_scale` method for match_larger mode
- [x] Implement aspect ratio preservation logic
- [x] Add coordinate transformation helpers (video space ↔ display space)

**Unit Tests Required:**
- [x] Test independent scaling mode with various video/display size combinations
- [x] Test match_larger scaling mode with reference size
- [x] Test aspect ratio preservation in both modes
- [x] Test edge cases (very small/large videos, square videos, extreme aspect ratios)
- [x] Test coordinate transformations (video to display, display to video)
- [x] Test scaling with identical video and display sizes

### ErrorDialog (`errors/error_dialog.py`)
- [x] Implement wx.MessageDialog wrapper
- [x] Implement dialog display/show method
- [x] Implement dialog result handling

**Unit Tests Required:**
- [x] Test ErrorDialog initialization
- [x] Test ErrorDialog display (mock wx.MessageDialog)
- [x] Test dialog result handling

### ErrorHandler (`errors/error_handler.py`)
- [x] Implement error message formatting
- [x] Integrate with ErrorDialog for GUI display (warning level, configurable to info)
- [x] Implement console logging (info level, configurable to debug)
- [x] Implement GUI log viewer (scrollable, warning level, configurable to info)

**Unit Tests Required:**
- [x] Test error message formatting for different error types
- [x] Test ErrorHandler integration with ErrorDialog
- [x] Test console logging at info level
- [x] Test console logging at debug level
- [x] Test GUI log viewer at warning level
- [x] Test GUI log viewer at info level
- [x] Test error handling with and without parent window

---

## Phase 4: Core Logic (Low-Level Dependencies)

### PrefillStrategy (`cache/prefill_strategy.py`)
- [x] Implement PrefillStrategy ABC with abstract methods
- [x] Implement `generate_protected_frames() -> Generator[int, None, None]` generator method
- [x] Implement `_generate_protected_frames()` abstract method for subclasses
- [x] Implement `cacheable_frame_count` property to track consumed frames
- [x] Implement `protected_frames() -> Set[int]` method to reconstruct protected set
- [x] Implement `is_protected_frame(frame_num: int, protected_set: Set[int]) -> bool` method
- [x] Implement `FramesNotGeneratedError` exception for error handling
- [x] Implement TrivialPrefillStrategy with iterator-based initialization (temporary implementation)

**Design Notes:**
- `TrivialPrefillStrategy` is a temporary implementation for testing. The final strategy implementation is TBD and may add additional methods to accept data relevant to the caching strategy (e.g., current position, playback direction, video metadata).
- `generate_protected_frames()` is expected to be called every time the position changes to regenerate the protected frame set.

**Unit Tests Required:**
- [x] Test TrivialPrefillStrategy generates frames in order
- [x] Test `generate_protected_frames` yields all frames
- [x] Test `cacheable_frame_count` tracks consumed frames
- [x] Test `protected_frames` returns consumed frames set
- [x] Test `protected_frames` raises error if not generated
- [x] Test `protected_frames` respects cache capacity limit
- [x] Test `is_protected_frame` returns True for frames in protected set
- [x] Test `is_protected_frame` returns False for frames not in protected set

### FrameCache (`cache/frame_cache.py`)
- [x] Implement frame storage (Dict[int, np.ndarray])
- [x] Implement cache hit/miss logic
- [x] Implement LRU eviction policy
- [x] Implement protected frame mechanism (frames from PrefillStrategy are not evicted)
- [x] Implement memory bounds checking and eviction
- [x] Implement frame retrieval by frame index
- [x] Implement cache invalidation
- [x] Implement `set_prefill_strategy()` method (basic version)
- [x] Implement generator consumption logic in `_ensure_protected_frames()`
  - [x] Consume frames from strategy generator until cache capacity reached
  - [x] Calculate capacity based on frame size estimates
  - [x] Store consumed frames as protected set
- [x] Add query methods for prefill logic (e.g., `get_missing_frames()`)
- [ ] Refactor to autonomous prefetching entity:
  - [ ] Implement `request_prefill_frame(strategy, callback, decoder)` interface
  - [ ] Implement request cancellation mechanism (cancel all pending requests on new request)
  - [ ] Implement immediate first frame fetch and callback invocation with `FrameResult`
  - [ ] Implement background prefetch thread
  - [ ] Implement prefetch queue management with cancellation support
  - [ ] Implement strategy update and stale request cancellation
  - [ ] Make cache operations thread-safe
  - [ ] Handle race conditions: cancel pending requests when new request arrives

**Design Notes:**
- FrameCache operates as an autonomous entity with its own background prefetch thread
- External interface: `set_prefill_strategy(strategy: PrefillStrategy, frame_callback: Callable[[int, np.ndarray], None], decoder: VideoDecoder)`
- Behavior:
  1. Receives PrefillStrategy + callback + decoder from PlaybackController
  2. Generates first frame number from strategy and acquires it (cache hit or miss)
  3. Signals callback immediately with (frame_number, frame) tuple
  4. Continues fetching remaining frames from strategy generator in background until capacity reached
- Consumed frames become the protected set that cannot be evicted
- Capacity is calculated based on available memory and frame size estimates
- FrameCache manages its own prefetch thread lifecycle and queue
- When strategy is updated, FrameCache cancels stale prefetch requests and starts new prefetch cycle

**Unit Tests Required:**
- [x] Test cache hit when frame exists
- [x] Test cache miss when frame doesn't exist
- [x] Test cache eviction when max_memory_mb exceeded (LRU, skipping protected frames)
- [x] Test protected frames are not evicted even when cache is full
- [x] Test cache invalidation clears all frames
- [x] Test cache with various frame sizes
- [x] Test `set_prefill_strategy()` updates protected frame set
- [x] Test query methods return correct missing frames
- [x] Test generator consumption stops at capacity
- [ ] Test callback invocation with first frame (immediate) using FrameResult
- [ ] Test background prefetching of remaining frames with FrameResult objects
- [ ] Test strategy update cancels stale prefetch requests
- [ ] Test race condition handling: new request cancels pending requests
- [ ] Test FrameResult with CANCELLED status for cancelled requests
- [ ] Test FrameResult with error statuses (DECODE_ERROR, SEEK_ERROR, OUT_OF_RANGE)
- [ ] Test thread safety of cache operations
- [ ] Test prefetch queue management with cancellation
- [ ] Test prefetch thread lifecycle (start/stop/cleanup)

### VideoDecoder (`decode/video_decoder.py`)
- [x] Implement PyAV container opening from file path
- [x] Implement video stream selection
- [x] Implement frame-accurate seek by frame index
- [x] Implement frame-accurate seek by timestamp
- [x] Implement frame decoding to NumPy array
- [x] Implement frame format conversion (PyAV → NumPy → wx.Bitmap compatible)
- [x] Implement error handling for decode failures
- [x] Integrate with FrameCache (optional)
- [x] Define per-class exceptions for decode errors (e.g., `DecodeError`, `SeekError`, `UnsupportedFormatError`)

**Note:** Hardware acceleration is not implemented to keep dependencies simple.

**Unit Tests Required:**
- [x] Test container opening with valid video file
- [x] Test container opening with invalid file (error handling)
- [x] Test video stream detection and selection
- [x] Test frame-accurate seek by frame index (verify exact frame returned)
- [x] Test frame-accurate seek by timestamp (verify correct frame for timestamp)
- [x] Test frame decoding returns NumPy array with correct shape
- [x] Test frame decoding returns correct pixel format
- [x] Test seek to first frame
- [x] Test seek to last frame
- [x] Test seek to middle frame
- [x] Test seek with videos of different framerates
- [x] Test decode error handling (corrupted frame, unsupported codec)
- [x] Test decoder with FrameCache integration

### TimelineController (`sync/timeline_controller.py`)
- [x] Implement current position tracking (in seconds)
- [x] Implement sync offset tracking (in frames, can be negative)
- [x] Implement frame-to-time conversion for video 1
- [x] Implement frame-to-time conversion for video 2 (with offset)
- [x] Implement time-to-frame conversion for video 1
- [x] Implement time-to-frame conversion for video 2 (with offset)
- [x] Implement position setting (seek)
- [x] Implement sync offset adjustment (set, increment, decrement)
- [x] Implement resolved frame/time calculation for both videos
- [x] Handle differing framerates between videos
- [x] Define per-class exceptions for timeline errors (e.g., `InvalidPositionError`, `OutOfRangeError`)

**Unit Tests Required:**
- [x] Test initial position is 0.0
- [x] Test initial sync offset is 0
- [x] Test frame-to-time conversion for video 1 (various framerates)
- [x] Test frame-to-time conversion for video 2 with positive offset
- [x] Test frame-to-time conversion for video 2 with negative offset
- [x] Test time-to-frame conversion for video 1
- [x] Test time-to-frame conversion for video 2 with offset
- [x] Test position setting updates current position
- [x] Test sync offset setting
- [x] Test sync offset increment (+1 frame)
- [x] Test sync offset decrement (-1 frame)
- [x] Test resolved frame calculation for video 1
- [x] Test resolved frame calculation for video 2 (with offset)
- [x] Test resolved time calculation for both videos
- [x] Test with videos of different framerates (e.g., 24fps vs 30fps)
- [x] Test edge cases (position at start, position at end, large offsets)

---

## Phase 5: Controllers

### PlaybackController (`playback/playback_controller.py`)
- [ ] Use PlaybackState enum from `common/types.py`
- [ ] Implement state machine (STOPPED → PLAYING → PAUSED → STOPPED)
- [ ] Implement play() method
- [ ] Implement pause() method
- [ ] Implement stop() method
- [ ] Implement frame_step_forward() method
- [ ] Implement frame_step_backward() method
- [ ] Implement tick/update loop for playback
- [ ] Implement frame request delegation to decoders
- [ ] Implement lockstep synchronization (both videos advance together)
- [ ] Integrate with TimelineController for position math
- [ ] Integrate with VideoDecoders for frame retrieval
- [ ] Integrate with FrameCaches
- [ ] Create and update PrefillStrategy instances for each video's FrameCache
  - [ ] Query TimelineController for resolved frame numbers for both videos
  - [ ] Create separate PrefillStrategy instances per video (accounting for different framerates/offsets)
  - [ ] Submit strategies to FrameCache via `request_prefill_frame(strategy, callback, decoder)` every time position changes
  - [ ] Provide frame callbacks that receive `FrameResult` objects from FrameCache
  - [ ] Handle FrameResult statuses appropriately (SUCCESS, CANCELLED, errors)
  - [ ] Update strategies when position changes or playback state changes
- [ ] Implement frame callback handling to coordinate frame display
- [ ] Define per-class exceptions for playback errors (e.g., `PlaybackStateError`, `SynchronizationError`)

**Unit Tests Required:**
- [ ] Test initial state is STOPPED
- [ ] Test state transition STOPPED → PLAYING
- [ ] Test state transition PLAYING → PAUSED
- [ ] Test state transition PAUSED → PLAYING
- [ ] Test state transition PLAYING → STOPPED
- [ ] Test state transition PAUSED → STOPPED
- [ ] Test frame_step_forward when paused
- [ ] Test frame_step_forward when playing
- [ ] Test frame_step_backward when paused
- [ ] Test frame_step_backward when playing
- [ ] Test frame_step_forward requests correct frames from decoders (with offset)
- [ ] Test frame_step_backward requests correct frames from decoders (with offset)
- [ ] Test play() maintains lockstep between videos
- [ ] Test tick loop advances both videos in sync
- [ ] Test playback respects sync offsets
- [ ] Test playback with FrameCache integration
- [ ] Test playback speed adjustment
- [ ] Test edge cases (step at start of video, step at end of video)
- [ ] Test PrefillStrategy creation for each video
- [ ] Test `generate_protected_frames()` is called on position changes
- [ ] Test PrefillStrategy updates when playback state changes
- [ ] Test PrefillStrategy handles different framerates correctly

---

## Phase 6: Media Loading

### MediaLoader (`media/media_loader.py`)
- [ ] Implement file selection dialog (wx.FileDialog)
- [ ] Implement file validation (existence, accessibility, readable)
- [ ] Implement file format validation (basic extension check)
- [ ] Integrate with MetadataExtractor for probing
- [ ] Integrate with ErrorHandler for user-facing errors
- [ ] Return VideoMetadata on successful load

**Unit Tests Required:**
- [ ] Test file selection dialog (mock wx.FileDialog)
- [ ] Test file validation with existing file
- [ ] Test file validation with missing file (error handling)
- [ ] Test file validation with unreadable file (error handling)
- [ ] Test metadata extraction integration
- [ ] Test error handling for unsupported formats
- [ ] Test error handling for files with no video stream
- [ ] Test successful load returns VideoMetadata

---

## Phase 7: Rendering

### VideoPane (`render/video_pane.py`)
- [ ] Implement wx.Panel subclass
- [ ] Implement OnPaint event handler
- [ ] Implement frame rendering using wx.PaintDC
- [ ] Implement zoom transform application
- [ ] Implement pan transform application
- [ ] Implement scaling mode support (independent vs match_larger)
- [ ] Implement matched bounding box calculation
- [ ] Implement overlay rendering (filename, dimensions, time/frame, zoom level)
- [ ] Implement mouse event handlers:
  - [ ] Mouse drag (click-and-drag) for panning the zoomed region
  - [ ] Mouse wheel scroll for zooming in/out
  - [ ] Shift-drag rectangle selection for zooming to a specific region
- [ ] Implement zoom state persistence across seeks/steps
- [ ] Integrate with ScalingCalculator
- [ ] Integrate with VideoMetadata for overlay info
- [ ] Define per-class exceptions for rendering errors (e.g., `RenderingError`)

**Unit Tests Required:**
- [ ] Test VideoPane initialization (mock wx.Panel)
- [ ] Test frame rendering with valid frame (mock wx.PaintDC)
- [ ] Test frame rendering with None frame (empty state)
- [ ] Test zoom transform application (various zoom levels)
- [ ] Test pan transform application (various pan positions)
- [ ] Test independent scaling mode rendering
- [ ] Test match_larger scaling mode rendering
- [ ] Test matched bounding box calculation
- [ ] Test overlay text rendering (mock wx.PaintDC)
- [ ] Test mouse drag pan interaction (mock mouse events)
- [ ] Test mouse wheel zoom in/out (mock wheel events)
- [ ] Test Shift-drag rectangle selection and zoom to region (mock mouse events)
- [ ] Test zoom state persistence after seek
- [ ] Test zoom state persistence after frame step
- [ ] Test coordinate transformations (screen to video space)
- [ ] Test edge cases (very large zoom, extreme pan positions)

**Note:** wxPython components should be mocked in unit tests. Use context manager-based mocking (e.g., `unittest.mock.patch`) rather than decorators.

---

## Phase 8: UI Components

### LayoutManager (`ui/layout_manager.py`)
- [ ] Implement orientation toggle (horizontal ↔ vertical)
- [ ] Implement scaling mode toggle (independent ↔ match_larger)
- [ ] Implement pane sizing calculation for horizontal layout
- [ ] Implement pane sizing calculation for vertical layout
- [ ] Implement matched bounding box calculation
- [ ] Integrate with VideoPane widgets for layout updates

**Unit Tests Required:**
- [ ] Test initial orientation (horizontal)
- [ ] Test initial scaling mode (independent)
- [ ] Test orientation toggle horizontal → vertical
- [ ] Test orientation toggle vertical → horizontal
- [ ] Test scaling mode toggle independent → match_larger
- [ ] Test scaling mode toggle match_larger → independent
- [ ] Test pane sizing for horizontal layout
- [ ] Test pane sizing for vertical layout
- [ ] Test matched bounding box calculation
- [ ] Test layout updates propagate to VideoPanes

### TimelineSlider (`ui/controls.py`)
- [ ] Implement wx.Slider widget wrapper
- [ ] Implement slider value change handler
- [ ] Implement timeline range calculation (0 to max duration)
- [ ] Integrate with TimelineController for position updates
- [ ] Implement position display (current time/frame)

**Unit Tests Required:**
- [ ] Test TimelineSlider initialization
- [ ] Test slider range calculation from video metadata
- [ ] Test slider value change triggers TimelineController seek
- [ ] Test position display updates correctly
- [ ] Test slider with videos of different durations

### SyncControls (`ui/controls.py`)
- [ ] Implement sync offset slider widget
- [ ] Implement +1 frame button
- [ ] Implement -1 frame button
- [ ] Implement offset display
- [ ] Integrate with TimelineController for offset updates

**Unit Tests Required:**
- [ ] Test SyncControls initialization
- [ ] Test offset slider updates TimelineController
- [ ] Test +1 button increments offset
- [ ] Test -1 button decrements offset
- [ ] Test offset display shows current offset
- [ ] Test offset range limits (if any)

### ZoomControls (`ui/controls.py`)
- [ ] Implement zoom in button
- [ ] Implement zoom out button
- [ ] Implement zoom reset button
- [ ] Implement zoom level display
- [ ] Integrate with VideoPane widgets for zoom updates

**Unit Tests Required:**
- [ ] Test ZoomControls initialization
- [ ] Test zoom in button increases zoom level
- [ ] Test zoom out button decreases zoom level
- [ ] Test zoom reset button returns to 1.0
- [ ] Test zoom updates both VideoPanes (if synchronized)
- [ ] Test zoom updates individual VideoPane (if independent)
- [ ] Test zoom level display updates correctly

### ControlPanel (`ui/controls.py`)
- [ ] Implement container widget (wx.Panel)
- [ ] Implement play/pause/stop buttons
- [ ] Implement frame-step forward/backward buttons
- [ ] Integrate TimelineSlider, SyncControls, ZoomControls
- [ ] Integrate with PlaybackController for button actions
- [ ] Implement button event wiring

**Unit Tests Required:**
- [ ] Test ControlPanel initialization
- [ ] Test play button triggers PlaybackController.play()
- [ ] Test pause button triggers PlaybackController.pause()
- [ ] Test stop button triggers PlaybackController.stop()
- [ ] Test frame-step forward button triggers step_forward()
- [ ] Test frame-step backward button triggers step_backward()
- [ ] Test all controls are properly wired
- [ ] Test button states update with playback state

---

## Phase 9: Input Handling

### ShortcutManager (`input/shortcut_manager.py`)
- [x] Implement default key bindings
- [x] Implement key binding registration
- [x] Implement command dispatch to handlers
- [x] Implement keyboard event handling (wx.EVT_KEY_DOWN)
- [x] Implement tooltip/help text generation
- [x] Implement custom binding override support

**Unit Tests Required:**
- [x] Test ShortcutManager initialization
- [x] Test default key bindings are registered
- [x] Test key press dispatches to correct command handler
- [x] Test command handler receives correct command
- [x] Test custom bindings override defaults
- [x] Test tooltip generation for all commands
- [x] Test keyboard event handling (mock wx events)
- [x] Test modifier key combinations (Ctrl, Alt, Shift)

---

## Phase 10: Configuration

### SettingsManager (`config/settings_manager.py`)
- [ ] Implement settings file path resolution
- [ ] Implement settings loading from file (JSON or similar)
- [ ] Implement settings saving to file
- [ ] Implement default settings creation
- [ ] Implement settings validation on load
- [ ] Handle missing/corrupted settings file gracefully

**Unit Tests Required:**
- [ ] Test SettingsManager initialization
- [ ] Test default settings creation
- [ ] Test settings loading from valid file
- [ ] Test settings loading from missing file (uses defaults)
- [ ] Test settings loading from corrupted file (error handling)
- [ ] Test settings saving to file
- [ ] Test settings validation on load
- [ ] Test enum value deserialization

---

## Phase 11: Application Shell

### MainFrame (`app/main_frame.py`)
- [ ] Implement wx.Frame subclass
- [ ] Implement menu bar creation
- [ ] Implement toolbar creation (if needed)
- [ ] Implement window layout (sizers)
- [ ] Integrate LayoutManager for video pane layout
- [ ] Integrate ControlPanel
- [ ] Integrate ShortcutManager
- [ ] Implement window close handler
- [ ] Implement window resize handler

**Unit Tests Required:**
- [ ] Test MainFrame initialization
- [ ] Test menu bar creation
- [ ] Test window layout contains all components
- [ ] Test window close handler
- [ ] Test window resize updates layout
- [ ] Test integration with LayoutManager
- [ ] Test integration with ControlPanel
- [ ] Test integration with ShortcutManager

### Application (`app/application.py`)
- [ ] Implement wx.App subclass or wrapper
- [ ] Implement dependency wiring (create all subsystems)
- [ ] Implement MainFrame creation and display
- [ ] Implement application initialization
- [ ] Implement application shutdown/cleanup
- [ ] Implement main event loop
- [ ] Integrate SettingsManager for loading settings
- [ ] Integrate ErrorHandler for global error handling

**Unit Tests Required:**
- [ ] Test Application initialization
- [ ] Test dependency wiring creates all subsystems
- [ ] Test MainFrame is created and shown
- [ ] Test application can start without loading media (smoke test)
- [ ] Test application shutdown cleanup
- [ ] Test settings loading on startup
- [ ] Test error handling integration

---

## Phase 12: Integration & End-to-End

### Integration Tests
- [ ] Test complete workflow: load two videos → align → step through frames
- [ ] Test complete workflow: load videos → zoom → pan → step
- [ ] Test complete workflow: load videos → change layout → verify display
- [ ] Test complete workflow: load videos → adjust sync → verify alignment
- [ ] Test error scenarios: load invalid file → verify error message
- [ ] Test error scenarios: load unsupported format → verify error message
- [ ] Test performance: rapid frame stepping with large videos
- [ ] Test performance: zoom/pan operations during playback

### Documentation
- [ ] Write user documentation (how to use the application)
- [ ] Document keyboard shortcuts
- [ ] Write developer documentation (architecture overview)
- [ ] Document extension points for future features

### Polish
- [ ] Add tooltips to all UI controls
- [ ] Add status bar with helpful information
- [ ] Add about dialog
- [ ] Verify cross-platform compatibility (macOS, Linux)
- [ ] Performance optimization pass
- [ ] UI/UX refinement

---

## Testing Strategy Summary

Each module should have:
1. **Unit tests** for all public methods and edge cases
2. **Integration tests** with real dependencies (where feasible)
3. **Mock-based tests** for external dependencies (wxPython, PyAV)
4. **Error path tests** for all error conditions
5. **Edge case tests** for boundary conditions

Test files should be in `tests/` directory mirroring the source structure.

### Testing wxPython Components

- wxPython components should be mocked in unit tests
- No test fixtures are currently available for wxPython widgets
- Use context manager-based mocking (e.g., `unittest.mock.patch`) rather than decorators, following the project's testing conventions
- Consider third-party libraries for wxPython mocking if needed (open to suggestions)

### Test Data

- Test video files are available in `tests/sample_data/`
- Use `file_example_AVI_*.avi` files for testing video decoding and metadata extraction
