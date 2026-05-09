# TODO: Video Comparator Implementation Plan

This document outlines the implementation plan from lowest-level modules to highest-level modules. Each module should be completed and tested before dependent modules are implemented.

**UI layout:** See **UI_LAYOUT_DIAGRAM.md** for the canonical window and control-panel layout (hierarchy, sizers, row order).

## Phase 1: Foundation (No Dependencies)

### ✅ Common Types (`common/types.py`)
- [x] Define `LayoutOrientation` enum
- [x] Define `ScalingMode` enum
- [x] Define `PlaybackState` enum (STOPPED, PLAYING, PAUSED)
- [x] Define `FrameRequestStatus` enum (SUCCESS, CANCELLED, DECODE_ERROR, SEEK_ERROR, OUT_OF_RANGE)
- [x] Define `FrameResult` dataclass (frame_number, frame, status, error) - Note: Located in `cache/frame_result.py` due to numpy dependency

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
- [x] Implement VideoMetadata class with all PyAV fields (including sample/display aspect metadata needed for display geometry)
- [x] Implement `dimensions` property (coded raster dimensions: width, height)
- [x] Add companion display-geometry property/properties (e.g., `display_dimensions` and/or `display_aspect_ratio`) derived from coded size + SAR/DAR metadata
- [x] Add validation for metadata values (positive durations, fps, dimensions)
- [x] Add explicit metadata fields for coded dimensions vs display geometry (e.g., SAR numerator/denominator and/or derived display aspect ratio)

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
- [x] Implement metadata extraction (duration, fps, dimensions, pixel format, total frames, time_base, sample/display aspect metadata)
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
- [x] Implement `protected_frames() -> Dict[int, None]` method to reconstruct protected set
- [x] Implement `is_protected_frame(frame_num: int, protected_set: Dict[int, None]) -> bool` method
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
- [ ] Implement eviction policy so strategy-preferred frames take precedence and LRU is used only for surplus/tie-breaking.
- [ ] Use O(1)-style recency bookkeeping for LRU operations in hot paths (no list remove/scan for common access/update operations).
- [ ] Use incremental running memory accounting rather than full-cache memory summations on insert/evict path.
- [ ] Implement non-redundant frame-copy operations on hot cache/decode path while preserving frame-safety guarantees.
- [x] Align cache **`put`** semantics with Architecture.md **§ Cache key correctness**: duplicate presentation indices must not retain a permanently wrong bitmap (explicit replace, version stamp, or invalidate-on-redecode policy once decoder assigns PTS-backed indices).
- [x] Implement protected frame mechanism (frames from PrefillStrategy are not evicted)
- [x] Implement memory bounds checking and eviction
- [x] Implement frame retrieval by frame index
- [x] Implement cache invalidation
- [x] Implement `request_prefill_frame()` method (replaces old `set_prefill_strategy()`)
- [x] Implement generator consumption logic in `_ensure_protected_frames()`
  - [x] Consume frames from strategy generator until cache capacity reached
  - [x] Calculate capacity based on frame size estimates
  - [x] Store consumed frames as protected set
- [x] Add query methods for prefill logic (e.g., `get_missing_frames()`)
- [x] Refactor to autonomous prefetching entity:
  - [x] Implement `request_prefill_frame(strategy, callback, decoder)` interface
  - [x] Implement request cancellation mechanism (cancel all pending requests on new request)
  - [x] Implement immediate first frame fetch and callback invocation with `FrameResult`
  - [x] Implement background prefetch thread
  - [x] Implement prefetch queue management with cancellation support
  - [x] Implement strategy update and stale request cancellation
  - [x] Make cache operations thread-safe
  - [x] Handle race conditions: cancel pending requests when new request arrives
- [x] Implement synchronization mechanism:
  - [x] Add `signal_sync_complete()` method stub to FrameCache
  - [x] Modify background prefetch worker to wait for sync signal before processing queued frames
  - [x] Ensure worker can be cancelled even while waiting for sync signal
  - [x] Queue remaining frames after first frame but pause worker until sync signal
- [x] Add per-decoder locking so VideoDecoder is only used from one thread at a time when FrameCache calls decode (PyAV/FFmpeg not thread-safe; see Architecture.md § Decode Engine and § Frame Cache).
- [ ] Enforce strict task priority: UI-requested frame is always first in decode scheduling order.
- [ ] Implement cooperative reprioritization at decode-operation boundaries (no forced mid-operation thread interruption).
- [ ] Ensure strategy-preferred frame residency takes precedence over pure LRU eviction.
- [ ] Ensure lower-priority in-flight work cannot schedule follow-on work ahead of newly arrived higher-priority strategy work.
- [ ] Establish single cache insertion authority in FrameCache (eliminate duplicate insertion paths across decoder and cache layers).

**Design Notes:**
- FrameCache operates as an autonomous entity with its own background prefetch thread
- External interface: `request_prefill_frame(strategy: PrefillStrategy, frame_callback: Callable[[FrameResult], None], decoder: VideoDecoder)`
- Behavior:
  1. Receives PrefillStrategy + callback + decoder from PlaybackController
  2. **Cancels all pending requests** when new request arrives (prevents race conditions)
  3. Generates first frame number from strategy and acquires it (cache hit or miss via VideoDecoder)
  4. Signals callback immediately with `FrameResult` object for first frame
  5. Queues remaining frames for background prefetch but worker waits for sync signal
  6. Background worker processes queued frames only after `signal_sync_complete()` is called
- **Synchronization**: Background prefetch worker pauses after first frame callback and waits for `signal_sync_complete()` from PlaybackController before processing queued frames. This ensures both videos are synchronized before additional prefetching occurs.
- Consumed frames become the protected set that cannot be evicted
- Capacity is calculated based on available memory and frame size estimates
- FrameCache manages its own prefetch thread lifecycle and queue
- When strategy is updated, FrameCache cancels stale prefetch requests and starts new prefetch cycle
- Callbacks receive `FrameResult` objects that convey frame data or failure reasons (SUCCESS, CANCELLED, DECODE_ERROR, SEEK_ERROR, OUT_OF_RANGE)
- Cache is the scheduler/retention authority; decoder is the decode execution engine.
- Any frame decoded while satisfying a cache request must be surfaced back to cache for retention decisions.
- Implementation detail (callback vs return values) is flexible as long as all decoded work is surfaced to cache.
- **Indexing risk:** Regression coverage should still add **long-GOP / B-frame** fixtures (see VideoDecoder tests); AVI-only tests alone do not prove PTS reordering paths.

**Unit Tests Required:**
- [x] Test cache hit when frame exists
- [x] Test cache miss when frame doesn't exist
- [ ] Test cache eviction when max_memory_mb exceeded with strategy-first residency and LRU tie-breaking for non-strategy/surplus frames.
- [x] Test protected frames are not evicted even when cache is full
- [x] Test cache invalidation clears all frames
- [x] Test cache with various frame sizes
- [x] Test query methods return correct missing frames
- [x] Test generator consumption stops at capacity
- [x] Test callback invocation with first frame (immediate) using FrameResult
- [x] Test background prefetching of remaining frames with FrameResult objects
- [x] Test strategy update cancels stale prefetch requests
- [x] Test race condition handling: new request cancels pending requests
- [x] Test FrameResult with CANCELLED status for cancelled requests
- [x] Test FrameResult with error statuses (DECODE_ERROR, SEEK_ERROR, OUT_OF_RANGE)
- [x] Test thread safety of cache operations
- [x] Test prefetch queue management with cancellation
- [x] Test prefetch thread lifecycle (start/stop/cleanup)
- [x] Test synchronization: background worker waits for sync signal before processing queued frames
- [x] Test synchronization: worker can be cancelled while waiting for sync signal
- [x] Test `signal_sync_complete()` allows worker to proceed with queued frames
- [x] Test `signal_sync_complete()` has no effect if called after cancellation

### VideoDecoder (`decode/video_decoder.py`)
- [x] Implement PyAV container opening from file path
- [x] Implement video stream selection
- [x] Implement frame-accurate seek by frame index
- [x] Implement frame-accurate seek by timestamp
- [x] Implement frame decoding to NumPy array
- [x] Implement frame format conversion (PyAV → NumPy → wx.Bitmap compatible)
- [x] Implement error handling for decode failures
- [ ] Implement decoder/cache integration contract: decoder surfaces all decoded frames from each decode operation; FrameCache decides retention/eviction.
- [x] Define per-class exceptions for decode errors (e.g., `DecodeError`, `SeekError`, `UnsupportedFormatError`)
- [x] Implement **presentation-correct** indexing for every decoded picture: map each frame to the agreed **0-based presentation index** using PTS/stream `time_base` + presentation-time floor (demux min), including after keyframe seek + decode-forward — **do not** rely on decode-order `decode_index += 1` as the sole labeling rule for long-GOP/B-frame streams (see Architecture.md § Presentation index vs decode order).
- [ ] Enforce monotonic presentation delivery for playback requests (forward non-decreasing, reverse non-increasing) so decoder emission-order quirks cannot produce visible forward/back jitter even when per-frame timestamp mapping exists.
- [ ] Re-verify seek-then-decode-forward and near-EOF fallback against the monotonic delivery model so returned/displayed frames and surfaced intermediates remain both correctly indexed and temporally stable.
- [x] Implement near-EOF fallback for decode requests at/near stream tail (retry/clamp to nearest decodable trailing frame; do not broaden to non-tail failures)

**Note:** Hardware acceleration is not implemented to keep dependencies simple.

**Unit Tests Required:**
- [x] Test container opening with valid video file
- [x] Test container opening with invalid file (error handling)
- [x] Test video stream detection and selection
- [ ] Test frame-accurate seek by frame index (verify exact frame returned for **presentation** index after refactor; extend beyond all-I/short-GOP fixtures as needed)
- [ ] Test frame-accurate seek by timestamp (verify correct presentation frame for timestamp after refactor)
- [x] Test frame decoding returns NumPy array with correct shape
- [x] Test frame decoding returns correct pixel format
- [x] Test seek to first frame
- [x] Test seek to last frame
- [x] Test seek to middle frame
- [x] Test seek with videos of different framerates
- [x] Test decode error handling (corrupted frame, unsupported codec)
- [ ] Test decoder/cache integration contract: decode operations surface target plus intermediate decoded frames to FrameCache for retention decisions — **must assert correct presentation index per surfaced raster**, not only pixel inequality between successive requests.
- [ ] Test that successive presentation indices decode to distinct content where expected — add **long-GOP / B-frame reordering** sample(s) so ordering bugs are not masked by simple AVI-only coverage.
- [ ] Add regression test: during forward playback ticks, video-2 displayed presentation index/time never regresses unless user performs explicit seek/step/reverse action.
- [x] Expose decode operation results so FrameCache can receive all decoded frames from a request (target + intermediates), using API shape that best matches PyAV container behavior.
- [x] Keep decoder free of cache prioritization/retention policy decisions.
- [x] Add decoder locality optimization policy: choose decode-forward from current cursor for nearby targets and seek+decode-forward for distant targets, prioritizing UI request latency.

**Performance Acceptance Criteria (Cache/Decoder Priority):**
- [ ] For each UI frame request, the requested frame is delivered before any lower-priority prefetch frame from the same request cycle.
- [ ] New high-priority requests supersede older lower-priority queued work at the next decode boundary.
- [x] Decoder work contributes decoded frames back to FrameCache for retention decisions.
- [ ] Throughput optimization does not override the primary objective: minimize UI request-to-frame latency.
- [x] Verify single-writer cache contract with tests after FrameCache **duplicate-key / overwrite** policy is implemented (decoder does not write cache directly; FrameCache performs authoritative insertion; **exactly-once vs deliberate replace** semantics documented in Architecture.md § Cache key correctness).
- [x] Add targeted performance tests for cache hot paths to guard against O(n) regression in recency updates and insertion/eviction accounting.

### TimelineController (`sync/timeline_controller.py`)
- [x] Implement current position tracking (in seconds)
- [x] Implement sync offset tracking (in frames, can be negative)
- [x] Implement frame-to-time conversion for video 1
- [x] Implement frame-to-time conversion for video 2 (with offset)
- [x] Implement time-to-frame conversion for video 1
- [x] Implement time-to-frame conversion for video 2 (with offset)
- [x] Implement position setting (seek)
- [x] Implement sync offset adjustment (set, increment, decrement)
- [ ] Implement resolved frame/time calculation for both videos (ensure video2 resolved time reflects sync offset semantics and does not cancel offset via round-trip conversion)
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
- [ ] Test resolved time calculation for both videos, including non-zero offsets where resolved times are expected to differ between panes
- [ ] Fix mixed-framerate offset-time consistency bug: ensure `resolved_time_video2` preserves video2-frame offset semantics across timeline progression (no offset cancellation via round-trip conversion)
- [x] Add regression-spec test (expected failure for current bug): with video1=29 fps, video2=24 fps, offset `+24` maintains approximately `+1.0 s` pane-2 lead as timeline advances
- [ ] After fix, convert the mixed-framerate regression test from expected-failure to passing assertion and keep it permanently
- [x] Test with videos of different framerates (e.g., 24fps vs 30fps)
- [x] Test edge cases (position at start, position at end, large offsets)

---

## Phase 5: Controllers

### PlaybackController (`playback/playback_controller.py`)
- [x] Use PlaybackState enum from `common/types.py`
- [x] Implement state machine (STOPPED → PLAYING → PAUSED → STOPPED)
- [x] Implement play() method
- [x] Implement pause() method
- [x] Implement stop() method
- [x] Implement frame_step_forward() method
- [x] Implement frame_step_backward() method
- [x] Implement tick/update loop for playback
- [x] Implement frame request delegation via FrameCache (no direct decoder calls)
- [x] Implement lockstep synchronization (both videos advance together)
- [x] Integrate with TimelineController for position math
- [x] Integrate with FrameCaches (decoders accessed via FrameCache)
- [x] Create and update PrefillStrategy instances for each video's FrameCache
  - [x] Query TimelineController for resolved frame numbers for both videos
  - [x] Create separate PrefillStrategy instances per video (accounting for different framerates/offsets)
  - [x] Submit strategies to FrameCache via `request_prefill_frame(strategy, callback, decoder)` every time position changes
  - [x] Provide frame callbacks that receive `FrameResult` objects from FrameCache
  - [x] Handle FrameResult statuses appropriately (SUCCESS, CANCELLED, errors)
  - [x] Update strategies when position changes or playback state changes
- [x] Implement frame callback handling to coordinate frame display
- [x] Implement synchronization mechanism to ensure both frame caches deliver first frames before display
- [x] Implement `signal_sync_complete()` call to both FrameCaches after both first frames arrive
- [x] Ensure sync signal is sent even if one video has error (error frame passed to callback)
- [x] Integrate with ErrorHandler for error reporting
- [x] Suppress user-facing error dialog for successful tail-fallback frame clamps; only unresolved post-fallback decode failures should be surfaced
- [x] Define per-class exceptions for playback errors (e.g., `PlaybackStateError`, `SynchronizationError`)

### Reverse playback (Specification §5)
- [x] Track **playback direction** (forward vs reverse) while `PLAYING`; `tick(delta)` advances timeline toward **max** or **min** using existing speed semantics; at timeline **start** in reverse, clamp/stop in line with how forward playback stops at **end**.
- [x] Entry points: e.g. `play_forward()` / `play_reverse()` or `play(direction=…)`; pressing the opposite play control while already `PLAYING` switches direction **without** jumping timeline position (Specification §5).
- [x] PrefillStrategy / FrameCache: verify frame fetch remains correct when timeline moves backward (prefetch may remain forward-biased initially — document limitations if any).

**Unit Tests Required:**
- [x] Test initial state is STOPPED
- [x] Test state transition STOPPED → PLAYING
- [x] Test state transition PLAYING → PAUSED
- [x] Test state transition PAUSED → PLAYING
- [x] Test state transition PLAYING → STOPPED
- [x] Test state transition PAUSED → STOPPED
- [x] Test frame_step_forward when paused
- [x] Test frame_step_forward when playing
- [x] Test frame_step_backward when paused
- [x] Test frame_step_backward when playing
- [x] Test frame_step_forward requests correct frames via FrameCache (with offset)
- [x] Test frame_step_backward requests correct frames via FrameCache (with offset)
- [x] Test play() maintains lockstep between videos
- [x] Test tick loop advances both videos in sync
- [x] Test playback respects sync offsets
- [x] Test playback with FrameCache integration
- [x] Test playback speed adjustment
- [x] Test edge cases (step at start of video, step at end of video)
- [x] Test PrefillStrategy creation for each video
- [x] Test `generate_protected_frames()` is called on position changes
- [x] Test PrefillStrategy updates when playback state changes
- [x] Test PrefillStrategy handles different framerates correctly
- [x] Test synchronization: both frame caches deliver first frames before user callback
- [x] Test synchronization: `signal_sync_complete()` called on both caches after both first frames arrive
- [x] Test synchronization: sync signal sent even when one video has error
- [x] Test CANCELLED FrameResult status handling (discarded)
- [x] Test error FrameResult status handling (ErrorHandler integration)
- [x] Add regression test: tail decode miss near EOF (e.g. requested last frame undecodable) falls back to nearest decodable frame without showing ErrorHandler dialog
- [x] Test user callback receives FrameResult objects for both videos
- [ ] Ensure callback overlay metadata (time/frame) is derived from delivered frame results for that callback cycle, not from potentially advanced timeline state
- [x] Test pause -> frame-step (+/-) -> play continuity: playback resumes from stepped timestamp without discontinuous jump
- [x] Test reverse `tick()` decreases timeline position while preserving dual-video sync semantics
- [x] Test reverse playback boundary at timeline start (clamp/stop behaviour)
- [x] Test switching reverse ↔ forward during `PLAYING` does not discontinuously jump timeline position

---

## Phase 6: Media Loading

### MediaLoader (`media/media_loader.py`)
- [x] Implement file selection dialog (wx.FileDialog)
- [x] Implement file validation (existence, accessibility, readable)
- [x] Implement file format validation (basic extension check)
- [x] Integrate with MetadataExtractor for probing
- [x] Integrate with ErrorHandler for user-facing errors
- [x] Return VideoMetadata on successful load

**Unit Tests Required:**
- [x] Test file selection dialog (mock wx.FileDialog)
- [x] Test file validation with existing file
- [x] Test file validation with missing file (error handling)
- [x] Test file validation with unreadable file (error handling)
- [x] Test metadata extraction integration
- [x] Test error handling for unsupported formats
- [x] Test error handling for files with no video stream
- [x] Test successful load returns VideoMetadata

---

## Phase 7: Rendering

### VideoPane (`render/video_pane.py`)
- [x] Implement wx.Panel subclass
- [x] Implement OnPaint event handler
- [x] Implement frame rendering using wx.PaintDC
- [x] Implement zoom transform application, scale about the **center** of the displayed video region in the pane by default
- [x] Implement pan transform application
- [x] Implement scaling mode support (independent vs match_larger)
- [x] Implement matched bounding box calculation
- [x] Implement overlay rendering (filename, dimensions, time/frame, zoom level)
- [x] Extend filename overlay line to include file size in friendly units (B, kB, MB, GB)
- [x] Extend dimensions overlay line to include FPS
- [x] Handle click on "no video loaded" overlay to open file chooser for that video pane
- [x] Implement mouse event handlers:
  - [x] Mouse drag (click-and-drag) for panning the zoomed region
  - [x] Mouse wheel scroll for zooming in/out - scale about the **point under the cursor** (adjust pan so that pixel stays fixed in video space while zoom changes).
  - [x] Shift-drag rectangle selection for zooming to a specific region
- [x] Implement zoom state persistence across seeks/steps
- [x] When a new video is loaded into this pane (replacement or first load via Application `_apply_loaded_video`, including menu / empty-pane click / drag-drop / CLI path), reset **this pane's** zoom factor and pan to defaults (1× and centered/default pan). When zoom is **synchronized** across panes, loading into either pane shall reset **both** panes so factors stay matched (Specification §7).
- [x] Integrate with ScalingCalculator
- [x] Integrate with VideoMetadata for overlay info
- [x] Define per-class exceptions for rendering errors (e.g., `RenderingError`)

**Unit Tests Required:**
- [x] Test VideoPane initialization (mock wx.Panel)
- [x] Test frame rendering with valid frame (mock wx.PaintDC)
- [x] Test frame rendering with None frame (empty state)
- [x] Test zoom transform application (various zoom levels)
- [x] Test pan transform application (various pan positions)
- [x] Test independent scaling mode rendering
- [x] Test match_larger scaling mode rendering
- [x] Test matched bounding box calculation
- [x] Test overlay text rendering (mock wx.PaintDC)
- [x] Test overlay filename line includes friendly file size when metadata has file path/size
- [x] Test overlay dimensions line includes FPS value
- [x] Test mouse drag pan interaction (mock mouse events)
- [x] Test mouse wheel zoom in/out (mock wheel events)
- [x] Test Shift-drag rectangle selection and zoom to region (mock mouse events)
- [x] Test zoom state persistence after seek
- [x] Test zoom state persistence after frame step
- [x] Test coordinate transformations (screen to video space)
- [x] Test edge cases (very large zoom, extreme pan positions)
- [x] Test zoom anchor: button zoom leaves **center** of video region stable; wheel zoom leaves **cursor** point stable (logic tests on pan/zoom math)
- [x] Test zoom/pan reset when pane receives a loaded video (mock load path / `set_metadata` / explicit reset hook as implemented)
- [x] Test synchronized-zoom mode: loading into either pane resets zoom/pan on **both** panes
- [x] Implement **pan-only** reset API on `VideoPane` (clear `pan_x` / `pan_y` to default centered alignment, leave `zoom_level` unchanged; refresh / notify similarly to zoom change hooks so controls update)
- [x] Unit tests: pan-only reset leaves zoom unchanged; default pan predicate matches renderer convention used by enable/disable logic

**Note:** wxPython components should be mocked in unit tests. Use context manager-based mocking (e.g., `unittest.mock.patch`) rather than decorators.

---

## Phase 8: UI Components

### LayoutManager (`ui/layout_manager.py`)
- [x] Implement orientation toggle (horizontal ↔ vertical)
- [x] Implement scaling mode toggle (independent ↔ match_larger)
- [x] Implement pane sizing calculation for horizontal layout
- [x] Implement pane sizing calculation for vertical layout
- [x] Implement matched bounding box calculation
- [x] Integrate with VideoPane widgets for layout updates

**Unit Tests Required:**
- [x] Test initial orientation (horizontal)
- [x] Test initial scaling mode (independent)
- [x] Test orientation toggle horizontal → vertical
- [x] Test orientation toggle vertical → horizontal
- [x] Test scaling mode toggle independent → match_larger
- [x] Test scaling mode toggle match_larger → independent
- [x] Test pane sizing for horizontal layout
- [x] Test pane sizing for vertical layout
- [x] Test matched bounding box calculation
- [x] Test layout updates propagate to VideoPanes

### TimelineSlider (`ui/controls.py`)
- [x] Implement wx.Slider widget wrapper
- [x] Implement slider value change handler
- [x] Implement timeline range calculation (0 to max duration)
- [x] Integrate with TimelineController for position updates
- [x] Implement position display (current time/frame)

**Unit Tests Required:**
- [x] Test TimelineSlider initialization
- [x] Test slider range calculation from video metadata
- [x] Test slider value change triggers TimelineController seek
- [x] Test position display updates correctly
- [x] Test slider with videos of different durations

### SyncControls (`ui/controls.py`)
- [x] Implement sync offset slider widget
- [x] Implement +1 frame button
- [x] Implement -1 frame button
- [x] Implement offset display
- [x] Integrate with TimelineController for offset updates
- [x] **Sync offset → display refresh:** When the user changes sync offset (slider or ±1 buttons), request and show updated frames **immediately** while playback is **paused** or **stopped**. While playback is **playing**, do **not** issue a separate immediate refresh from the control handler; let the next tick / playback-driven frame request apply the new offset (avoid racing the playback timer).

**Unit Tests Required:**
- [x] Test SyncControls initialization
- [x] Test offset slider updates TimelineController
- [x] Test +1 button increments offset
- [x] Test -1 button decrements offset
- [x] Test offset display shows current offset
- [x] Test offset range limits (if any)
- [x] Test (or integration test): offset change triggers frame refresh when not playing; defers to playback when playing (mock `PlaybackState`)
- [x] Test `on_sync_offset_changed` invoked from slider / ±1 handlers

### ZoomControls (`ui/controls.py`)
- [x] Implement zoom in button
- [x] Implement zoom out button
- [x] Implement zoom reset button
- [x] Implement zoom level display
- [x] Zoom label styling: use **red** foreground when any zoom factor shown in the label is not exactly 1×; use default `StaticText` foreground when every displayed factor is exactly 1× (independent vs synchronized modes per Specification §7). Update colors whenever `_update_zoom_display` / theme changes as needed.
- [x] Integrate with VideoPane widgets for zoom updates
- [x] **Zoom anchor:** Button-driven zoom should use **center** anchoring; implementation lives primarily in `VideoPane` / `ScalingCalculator` (see Phase 7 — Zoom anchor).

**Unit Tests Required:**
- [x] Test ZoomControls initialization
- [x] Test zoom in button increases zoom level
- [x] Test zoom out button decreases zoom level
- [x] Test zoom reset button returns to 1.0
- [x] Test zoom updates both VideoPanes (if synchronized)
- [x] Test zoom updates individual VideoPane (if independent)
- [x] Test zoom level display updates correctly
- [x] Test zoom label color: default when zoom is exactly 1× (both panes independent and synchronized cases); red when either pane (independent) or shared factor (synchronized) differs from 1×
- [x] **Reset Zoom** button: **disabled** when both panes' zoom factors are exactly 1× (same tolerance as `ZoomControls.is_unit_zoom` / label semantics); **enabled** otherwise; wired to existing full reset (`reset_zoom_pan` behaviour including synchronized pane pairing)
- [x] **Reset Pan** button: placed **to the right** of the zoom level `StaticText` (see `UI_LAYOUT_DIAGRAM.md` Row 4); **disabled** when **both** panes are at default pan (centered); **enabled** when **either** pane pan differs from default; invokes pan-only reset on **both** panes; tooltip clarifies it does **not** change magnification (Specification §7)
- [x] Centralize refresh of zoom **label** (text + colour) **and** both buttons' enabled states whenever zoom or pan changes (pane callbacks, load-path resets, button handlers — avoid stale grey state)
- [x] Tests: Reset Zoom enabled/disabled vs mocked pane zoom levels; Reset Pan enabled/disabled vs mocked pane pan positions; handler calls `reset_pan_only` / equivalent on both panes without altering zoom

### ControlPanel (`ui/controls.py`)
- [x] Implement container widget (wx.Panel)
- [x] Implement play/pause/stop buttons
- [x] **Dual-direction play (Specification §5 / `UI_LAYOUT_DIAGRAM.md` Row 2):** add **Reverse Play** (`◀ Play`, U+25C0 + space + `Play`; fallback `< Play`) immediately **left** of **Forward Play**; rename existing Play to **`▶ Play`** (U+25B6 + space + `Play`; fallback `> Play`). Row order: reverse play, forward play, pause, stop, step backward, step forward.
- [x] Wire Reverse Play / Forward Play to PlaybackController; `_update_button_states` enables **both** when ≥1 video loaded; while `PLAYING`, reflect active direction (disable or de-emphasize inactive play per Specification §5).
- [x] Implement frame-step forward/backward buttons
- [x] Integrate TimelineSlider, SyncControls, ZoomControls
- [x] Implement ControlPanel layout per UI_LAYOUT_DIAGRAM.md (`_create_layout()`: vertical BoxSizer, rows for timeline slider+label, playback buttons, sync slider+buttons+label, zoom buttons+label)
- [x] Extend zoom controls row layout per updated `UI_LAYOUT_DIAGRAM.md`: zoom buttons + zoom label + **Reset Pan** (horizontal spacing consistent with existing controls); expose getter if tests/layout need it
- [x] Integrate with PlaybackController for button actions
- [x] Implement button event wiring
- [x] Enable play button only when at least one video is loaded (disabled when no videos loaded)
- [x] Enable sync (frame offset) controls only when both videos are loaded (disabled when fewer than 2 videos)

**Unit Tests Required:**
- [x] Test ControlPanel initialization
- [x] Test forward play button invokes `PlaybackController.play_forward()`
- [x] Test reverse play button invokes `PlaybackController.play_reverse()`
- [x] Test pause button triggers PlaybackController.pause()
- [x] Test stop button triggers PlaybackController.stop()
- [x] Test frame-step forward button triggers step_forward()
- [x] Test frame-step backward button triggers step_backward()
- [x] Test all controls are properly wired
- [x] Test button states update with playback state

---

## Phase 9: Input Handling

### ShortcutManager (`input/shortcut_manager.py`)
- [x] Add distinct default shortcuts for **reverse play** vs **forward play** when implementing dual-direction playback (keeping pause/stop parity); update tooltip/help strings accordingly.
- [x] **Reconcile defaults with `Specification.md` §11:** **Space** / **Shift+Space** play semantics; **←/→** ±10 s timeline seek (not frame step); **comma** / **period** frame step (not continuous play); **minus** / **equals** sync ±1; zoom on **Ctrl+[** / **Ctrl+]** per §7.
- [x] **Focus / routing:** **`MainFrame`** uses **`EVT_CHAR_HOOK`** so **`ShortcutManager`** runs before focused children consume keys.
- [x] Implement default key bindings
- [x] Implement key binding registration
- [x] Implement command dispatch to handlers
- [x] Implement keyboard event handling (`EVT_CHAR_HOOK` on main frame → `ShortcutManager`)
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
- [x] Implement settings file path resolution
- [x] Implement settings loading from file (JSON or similar)
- [x] Implement settings saving to file
- [x] Implement default settings creation
- [x] Implement settings validation on load
- [x] Handle missing/corrupted settings file gracefully

**Unit Tests Required:**
- [x] Test SettingsManager initialization
- [x] Test default settings creation
- [x] Test settings loading from valid file
- [x] Test settings loading from missing file (uses defaults)
- [x] Test settings loading from corrupted file (error handling)
- [x] Test settings saving to file
- [x] Test settings validation on load
- [x] Test enum value deserialization

---

## Phase 11: Application Shell

### MainFrame (`app/main_frame.py`)
- [x] Implement wx.Frame subclass
- [x] Implement menu bar creation
- [x] Wire File menu: Open Video 1 / Open Video 2 trigger file chooser and load video for that pane
- [ ] Wire File menu: Close Videos unloads both videos, resets both panes to empty defaults, and resets timeline/sync sliders to 0
- [x] Wire View menu: Toggle Layout menu item toggles layout orientation and refreshes frame layout
- [x] Wire View menu: Toggle Scaling Mode menu item toggles scaling mode (independent ↔ match larger)
- [x] Implement toolbar creation (if needed)
- [x] Implement window layout (sizers)
- [x] Integrate LayoutManager for video pane layout
- [x] Integrate ControlPanel
- [x] Integrate ShortcutManager
- [x] Implement window close handler
- [x] Implement window resize handler

**Unit Tests Required:**
- [x] Test MainFrame initialization
- [x] Test menu bar creation
- [ ] Test File menu includes Close Videos and dispatches to close/reset callback
- [x] Test window layout contains all components
- [x] Regression: repeated `_create_layout` reuses one video container panel (avoids orphan `wx.Panel` widgets that break layout on toggle)
- [x] Test window close handler
- [x] Test window resize updates layout
- [x] Test integration with LayoutManager
- [x] Test integration with ControlPanel
- [x] Test integration with ShortcutManager

### Application (`app/application.py`)
- [x] Implement wx.App subclass or wrapper
- [x] Implement dependency wiring (create all subsystems)
- [x] Implement MainFrame creation and display
- [x] On startup, after showing the main frame, request foreground activation (e.g. `Raise()` / `RaiseLater()` per wxWidgets guidance so the window reliably comes forward on macOS/Linux where `Show()` alone is insufficient). Accept that the OS may still refuse focus in edge launch contexts.
- [x] Implement application initialization
- [x] Implement application shutdown/cleanup
- [x] Implement main event loop
- [x] Integrate SettingsManager for loading settings
- [x] Integrate ErrorHandler for global error handling
- [x] After a successful video load into slot 1 or 2, trigger pane zoom/pan reset per Specification §7 / Architecture (delegate to `VideoPane` or shared helper; ensure CLI/drop/menu paths all hit this)
- [ ] Implement Close Videos handler that unloads both media slots, resets both panes, restores timeline position + sync offset to 0, and refreshes "no video loaded" control states

**Unit Tests Required:**
- [x] Test Application initialization
- [x] Test dependency wiring creates all subsystems
- [x] Test MainFrame is created and shown
- [x] Test finalize/startup calls foreground helpers on the main frame after `Show()` (mock `MainFrame`: assert `Raise` or equivalent is invoked as wired)
- [x] Test application can start without loading media (smoke test)
- [x] Test application shutdown cleanup
- [x] Test settings loading on startup
- [x] Test error handling integration
- [x] Test `_apply_loaded_video` (or equivalent) invokes zoom/pan reset for the loaded pane(s) consistent with independent vs synchronized zoom mode
- [ ] Test Close Videos clears both loaded videos, resets both panes, restores timeline/sync sliders to 0, and updates controls/menu state accordingly

### Entry Point / CLI (`__main__.py` and app startup wiring)
- [x] Implement command-line parsing with `argparse` (no custom parser)
- [x] Support up to two optional positional video path arguments in order (`video1`, `video2`)
- [x] Validate positional argument count with `argparse` `nargs`/usage semantics (0, 1, or 2 allowed; >2 rejected with usage error)
- [x] Add `--offset` argument parsed as signed integer frame offset (positive/negative supported)
- [x] Apply parsed `--offset` value to timeline/controller sync offset during startup initialization
- [x] When one positional video is provided, auto-load it into pane 1 at startup
- [x] When two positional videos are provided, auto-load both panes at startup in argument order
- [x] When both videos and `--offset` are provided, startup state reflects all arguments: both videos loaded and sync offset controls/slider positioned to the parsed offset
- [x] Route CLI-driven video loads through the same validation/load path as menu/drag-drop to avoid duplicated logic
- [x] Surface CLI load/parse errors through existing error handling flow with clear user-facing messages

**Unit Tests Required:**
- [x] Test `argparse` parser accepts 0, 1, and 2 positional video arguments
- [x] Test parser rejects 3+ positional video arguments with usage error
- [x] Test parser accepts `--offset 0`, positive, and negative integer values
- [x] Test parser rejects non-integer `--offset` values
- [x] Test startup with one positional video calls pane-1 load path
- [x] Test startup with two positional videos calls pane-1 and pane-2 load paths in order
- [x] Test startup with two positional videos plus `--offset` sets sync offset in controller and updates slider/display state
- [x] Test startup continues to support normal launch with no positional videos and default offset

### Drag and drop (video files onto panes)
- [x] Enable drag-and-drop on each `VideoPane` (e.g. `wx.FileDropTarget` or `wx.DropTarget` with file URL/text) so users can drop video files from the OS file manager
- [x] Route a drop on pane 1 vs pane 2 to the same load path as **File → Open Video 1/2** (reuse `MediaLoader` / `_apply_loaded_video` logic; avoid duplicating validation)
- [x] Accept only plausible video paths (extension and/or sniffing); show errors via `ErrorHandler` for invalid or unreadable drops
- [x] Optional: visual affordance when the pointer drags over a pane (e.g. highlight or cursor) and ignore drops on the wrong widget
- [x] Document behavior in tooltips or help (which pane receives which slot)

**Unit Tests Required:**
- [x] Drop handler resolves the target pane (1 vs 2) and invokes the same load entry point as menu open (mock `MediaLoader` / application callback)
- [x] Reject or no-op non-file payloads without crashing; invalid paths surface errors without leaving panes inconsistent

---

## Phase 12: Integration & End-to-End

### Integration Tests
- [ ] Drag and drop: drop a supported video onto each pane → correct pane loads and displays; unsupported file shows error
- [ ] Sync offset: changing slider/±1 while **paused** updates both panes immediately; changing while **playing** does not glitch or double-refresh (offset applies via playback path)
- [ ] Overlay correctness with offset: with non-zero sync offset, pane 1 and pane 2 overlay times/frames reflect different resolved source positions as expected (within rounding/clamp tolerance)
- [ ] Aspect-ratio correctness: anamorphic/non-square-pixel source displays with correct widescreen geometry (no vertical stretch)
- [ ] Playback continuity: pause -> step one frame -> play does not jump to an unrelated timestamp on either pane
- [ ] Reverse play: timeline moves backward in sync; boundary at start; toggle forward ↔ reverse without position glitch
- [ ] CLI startup: launch with `video1 video2 --offset N` loads both videos and initializes sync offset slider/display to `N` before first interaction
- [ ] Zoom: button zoom keeps **center** fixed; wheel zoom keeps **cursor** point fixed
- [ ] Zoom: after loading or replacing a video in a pane, that pane shows 1× default pan (both panes if synchronized zoom); label colour matches non-1× state; **Reset Zoom** / **Reset Pan** enabled states match §7 after load and after arbitrary zoom/pan gestures
- [ ] Test complete workflow: load two videos → align → step through frames
- [ ] Test complete workflow: load videos → zoom → pan → step
- [ ] Test complete workflow: load videos → change layout → verify display
- [ ] Test complete workflow: load videos → adjust sync → verify alignment
- [ ] Test complete workflow: load one video → play, pause, step, seek via slider (single-video playback)
- [ ] Test timeline slider: dragging slider requests and displays frame at new position (panes do not go blank)
- [ ] Test playback: when Play is active, video panes update (timer-driven tick; panes do not go blank)
- [ ] Test error scenarios: load invalid file → verify error message
- [ ] Test error scenarios: load unsupported format → verify error message
- [ ] Test performance: rapid frame stepping with large videos
- [ ] Test performance: zoom/pan operations during playback

### Documentation
- [ ] Write user documentation (how to use the application)
- [x] Document keyboard shortcuts (**normative:** `Specification.md` §§3–7 & §11 table; **quick reference:** `README.md`; **engineering:** `Architecture.md` §9 — implementation still pending)
- [ ] Write developer documentation (architecture overview)
- [ ] Document extension points for future features

### Polish
- [x] Drag-and-drop onto video panes (see Phase 11: Drag and drop)
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
