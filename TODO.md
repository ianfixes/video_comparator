# TODO: Video Comparator Implementation Plan

This document outlines the implementation plan from lowest-level modules to highest-level modules. Each module should be completed and tested before dependent modules are implemented.

## Phase 1: Foundation (No Dependencies)

### ✅ Common Types (`common/types.py`)
- [x] Define `LayoutOrientation` enum
- [x] Define `ScalingMode` enum

**Unit Tests Required:**
None, these are trivial.

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

### VideoMetadata (`media/metadata.py`)
- [ ] Implement VideoMetadata class
- [ ] Implement `dimensions` property
- [ ] Add validation for metadata values (positive durations, fps, dimensions)

**Unit Tests Required:**
- [ ] Test VideoMetadata initialization with valid data
- [ ] Test `dimensions` property returns correct tuple
- [ ] Test VideoMetadata validation (reject negative/zero values)
- [ ] Test VideoMetadata with edge cases (very large dimensions, high fps)

### KeyBinding (`input/shortcuts.py`)
- [ ] Implement KeyBinding class
- [ ] Add validation for key codes and modifiers

**Unit Tests Required:**
- [ ] Test KeyBinding initialization
- [ ] Test KeyBinding equality comparison
- [ ] Test KeyBinding validation

---

## Phase 3: Utility Classes

### MetadataExtractor (`media/metadata.py`)
- [ ] Implement PyAV container opening
- [ ] Implement video stream detection
- [ ] Implement metadata extraction (duration, fps, dimensions, pixel format, total frames, time_base)
- [ ] Implement error handling for unsupported formats
- [ ] Add support for multiple video streams (select first video stream)

**Unit Tests Required:**
- [ ] Test metadata extraction from known test video file
- [ ] Test extraction of all required fields (duration, fps, width, height, pixel_format, total_frames, time_base)
- [ ] Test error handling for missing file
- [ ] Test error handling for unsupported format
- [ ] Test error handling for file with no video stream
- [ ] Test with videos of different formats (MP4, MKV, AVI)
- [ ] Test with videos of different codecs (H.264, H.265, ProRes)

### ScalingCalculator (`render/scaling.py`)
- [ ] Implement `calculate_scale` method for independent mode
- [ ] Implement `calculate_scale` method for match_larger mode
- [ ] Implement aspect ratio preservation logic
- [ ] Add coordinate transformation helpers (video space ↔ display space)

**Unit Tests Required:**
- [ ] Test independent scaling mode with various video/display size combinations
- [ ] Test match_larger scaling mode with reference size
- [ ] Test aspect ratio preservation in both modes
- [ ] Test edge cases (very small/large videos, square videos, extreme aspect ratios)
- [ ] Test coordinate transformations (video to display, display to video)
- [ ] Test scaling with identical video and display sizes

### ErrorDialog (`errors/handler.py`)
- [ ] Implement wx.MessageDialog wrapper
- [ ] Implement dialog display/show method
- [ ] Implement dialog result handling

**Unit Tests Required:**
- [ ] Test ErrorDialog initialization
- [ ] Test ErrorDialog display (mock wx.MessageDialog)
- [ ] Test dialog result handling

### ErrorHandler (`errors/handler.py`)
- [ ] Implement error message formatting
- [ ] Implement error categorization (load errors, decode errors, format errors)
- [ ] Integrate with ErrorDialog for display
- [ ] Implement logging integration (if enabled)

**Unit Tests Required:**
- [ ] Test error message formatting for different error types
- [ ] Test error categorization
- [ ] Test ErrorHandler integration with ErrorDialog
- [ ] Test logging when enabled
- [ ] Test no logging when disabled
- [ ] Test error handling with and without parent window

---

## Phase 4: Core Logic (Low-Level Dependencies)

### FrameCache (`cache/frame_cache.py`)
- [ ] Implement frame storage (Dict[int, np.ndarray])
- [ ] Implement cache hit/miss logic
- [ ] Implement ring buffer with ahead/behind current position
- [ ] Implement eviction policy (LRU or FIFO)
- [ ] Implement memory bounds checking and eviction
- [ ] Implement frame retrieval by frame index
- [ ] Implement cache invalidation

**Unit Tests Required:**
- [ ] Test cache hit when frame exists
- [ ] Test cache miss when frame doesn't exist
- [ ] Test cache eviction when max_frames exceeded
- [ ] Test cache eviction when max_memory_mb exceeded
- [ ] Test ring buffer maintains frames ahead/behind current position
- [ ] Test cache invalidation clears all frames
- [ ] Test cache with various frame sizes
- [ ] Test cache with rapid position changes

### VideoDecoder (`decode/decoder.py`)
- [ ] Implement PyAV container opening from file path
- [ ] Implement video stream selection
- [ ] Implement frame-accurate seek by frame index
- [ ] Implement frame-accurate seek by timestamp
- [ ] Implement frame decoding to NumPy array
- [ ] Implement frame format conversion (PyAV → NumPy → wx.Bitmap compatible)
- [ ] Implement hardware acceleration detection and usage
- [ ] Implement error handling for decode failures
- [ ] Integrate with FrameCache (optional)

**Unit Tests Required:**
- [ ] Test container opening with valid video file
- [ ] Test container opening with invalid file (error handling)
- [ ] Test video stream detection and selection
- [ ] Test frame-accurate seek by frame index (verify exact frame returned)
- [ ] Test frame-accurate seek by timestamp (verify correct frame for timestamp)
- [ ] Test frame decoding returns NumPy array with correct shape
- [ ] Test frame decoding returns correct pixel format
- [ ] Test seek to first frame
- [ ] Test seek to last frame
- [ ] Test seek to middle frame
- [ ] Test seek with videos of different framerates
- [ ] Test decode error handling (corrupted frame, unsupported codec)
- [ ] Test hardware acceleration flag (mock if needed)
- [ ] Test decoder with FrameCache integration

### TimelineController (`sync/timeline.py`)
- [ ] Implement current position tracking (in seconds)
- [ ] Implement sync offset tracking (in frames, can be negative)
- [ ] Implement frame-to-time conversion for video 1
- [ ] Implement frame-to-time conversion for video 2 (with offset)
- [ ] Implement time-to-frame conversion for video 1
- [ ] Implement time-to-frame conversion for video 2 (with offset)
- [ ] Implement position setting (seek)
- [ ] Implement sync offset adjustment (set, increment, decrement)
- [ ] Implement resolved frame/time calculation for both videos
- [ ] Handle differing framerates between videos

**Unit Tests Required:**
- [ ] Test initial position is 0.0
- [ ] Test initial sync offset is 0
- [ ] Test frame-to-time conversion for video 1 (various framerates)
- [ ] Test frame-to-time conversion for video 2 with positive offset
- [ ] Test frame-to-time conversion for video 2 with negative offset
- [ ] Test time-to-frame conversion for video 1
- [ ] Test time-to-frame conversion for video 2 with offset
- [ ] Test position setting updates current position
- [ ] Test sync offset setting
- [ ] Test sync offset increment (+1 frame)
- [ ] Test sync offset decrement (-1 frame)
- [ ] Test resolved frame calculation for video 1
- [ ] Test resolved frame calculation for video 2 (with offset)
- [ ] Test resolved time calculation for both videos
- [ ] Test with videos of different framerates (e.g., 24fps vs 30fps)
- [ ] Test edge cases (position at start, position at end, large offsets)

---

## Phase 5: Controllers

### PlaybackController (`playback/controller.py`)
- [ ] Implement PlaybackState enum usage
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
- [ ] Integrate with FrameCaches (optional)

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

---

## Phase 6: Media Loading

### MediaLoader (`media/loader.py`)
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
- [ ] Implement mouse event handlers for pan (click-and-drag)
- [ ] Implement zoom state persistence across seeks/steps
- [ ] Integrate with ScalingCalculator
- [ ] Integrate with VideoMetadata for overlay info

**Unit Tests Required:**
- [ ] Test VideoPane initialization
- [ ] Test frame rendering with valid frame
- [ ] Test frame rendering with None frame (empty state)
- [ ] Test zoom transform application (various zoom levels)
- [ ] Test pan transform application (various pan positions)
- [ ] Test independent scaling mode rendering
- [ ] Test match_larger scaling mode rendering
- [ ] Test matched bounding box calculation
- [ ] Test overlay text rendering (mock wx.PaintDC)
- [ ] Test mouse pan interaction (mock mouse events)
- [ ] Test zoom state persistence after seek
- [ ] Test zoom state persistence after frame step
- [ ] Test coordinate transformations (screen to video space)
- [ ] Test edge cases (very large zoom, extreme pan positions)

---

## Phase 8: UI Components

### LayoutManager (`ui/layout.py`)
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

### ShortcutManager (`input/shortcuts.py`)
- [ ] Implement default key bindings
- [ ] Implement key binding registration
- [ ] Implement command dispatch to handlers
- [ ] Implement keyboard event handling (wx.EVT_KEY_DOWN)
- [ ] Implement tooltip/help text generation
- [ ] Implement custom binding override support

**Unit Tests Required:**
- [ ] Test ShortcutManager initialization
- [ ] Test default key bindings are registered
- [ ] Test key press dispatches to correct command handler
- [ ] Test command handler receives correct command
- [ ] Test custom bindings override defaults
- [ ] Test tooltip generation for all commands
- [ ] Test keyboard event handling (mock wx events)
- [ ] Test modifier key combinations (Ctrl, Alt, Shift)

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
