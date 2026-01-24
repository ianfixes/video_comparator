# Architecture

This document outlines the major subsystems for the video comparator. Each subsystem is isolated so it can be developed and tested independently.

## Stack Baseline
- GUI: wxPython (wx.Frame, wx.Panel, custom drawing with wx.PaintDC)
- Video decode: PyAV (FFmpeg) for frame-accurate seeking/decoding
- Data handling: NumPy for frame buffers and transforms
- Tests: pytest (unit + integration), mypy for types, black/isort for style
- Testing: wxPython components should be mocked in unit tests (no test fixtures available yet)

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
- test files available: `file_example_AVI_*.avi` files in `tests/sample_data/`
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
- autonomous background prefetching of frames
- integration with PrefillStrategy to protect frames from eviction
- race condition handling via request cancellation
#### Design
- FrameCache operates as an autonomous entity with its own background prefetch thread
- PlaybackController submits a fully-configured PrefillStrategy and a callback function to FrameCache
- FrameCache interface:
  1. Receives PrefillStrategy + callback from PlaybackController
  2. **Cancels all pending requests** when new request arrives (prevents race conditions)
  3. Generates first frame number from strategy (`generate_protected_frames`) and acquires it (cache hit or miss via VideoDecoder)
  4. Signals callback immediately with `FrameResult` object for the first frame
  5. **Queues remaining frames for background prefetch but pauses worker until sync signal**
  6. Background worker waits for `signal_sync_complete()` before processing queued frames
  7. Once sync signal received, continues fetching remaining frames from strategy generator in background thread until capacity reached
- **Synchronization with PlaybackController**:
  - After first frame callback, background prefetch worker pauses and waits for synchronization signal
  - PlaybackController calls `signal_sync_complete()` on both FrameCaches when both first frames have arrived
  - This ensures both videos are synchronized before any additional prefetching occurs
  - If new `request_prefill_frame()` arrives before sync completes, cancellation prevents old workers from continuing
- Consumed frames become the protected set (in priority order) that cannot be evicted
- Capacity is calculated based on available memory and frame size estimates
- FrameCache manages its own prefetch thread lifecycle and queue
- When new request arrives, FrameCache cancels all pending prefetch requests and starts new prefetch cycle
- Callbacks receive `FrameResult` objects that convey frame data or failure reasons
#### FrameResult Object
- `FrameResult` dataclass contains:
  - `frame_number: int` - The requested frame index
  - `frame: Optional[np.ndarray]` - The frame data (None if request failed)
  - `status: FrameRequestStatus` - Status enum indicating success or failure reason
  - `error: Optional[Exception]` - Exception object if status indicates an error
- `FrameRequestStatus` enum values:
  - `SUCCESS` - Frame successfully retrieved
  - `CANCELLED` - Request cancelled due to new request (race condition)
  - `DECODE_ERROR` - Frame decode failed
  - `SEEK_ERROR` - Frame seek failed
  - `OUT_OF_RANGE` - Frame index out of valid range
- Callbacks receive `FrameResult` instead of raw tuples, allowing proper error handling
#### External Interface
- `request_prefill_frame(strategy: PrefillStrategy, frame_callback: Callable[[FrameResult], None], decoder: VideoDecoder) -> None`
  - Sets the prefill strategy, callback, and decoder reference
  - **Cancels all pending requests** before starting new prefetch cycle
  - Triggers immediate frame fetch for first frame in strategy
  - Queues remaining frames for background prefetch but worker waits for sync signal
  - Callback receives `FrameResult` object immediately for first frame
  - Background worker processes queued frames only after `signal_sync_complete()` is called
- `signal_sync_complete() -> None`
  - Signals that synchronization is complete and background prefetch worker can proceed
  - Called by PlaybackController when both frame caches have delivered their first frames
  - If called after cancellation, has no effect (worker already cancelled)
- `get(frame_index: int) -> Optional[np.ndarray]` - Synchronous frame retrieval (existing)
- `put(frame_index: int, frame: np.ndarray) -> None` - Frame storage (existing)
#### Testability
- unit tests for cache hit/miss behavior and LRU eviction
- unit tests for protected frame behavior
- unit tests for generator consumption until capacity
- unit tests for callback invocation with correct frame numbers
- unit tests for background prefetching behavior
- unit tests for strategy update and prefetch cancellation
- thread safety tests for concurrent cache operations

### 4a) Prefill Strategy
#### Responsibilities
- defines which frames should be protected from cache eviction
- generates frame numbers in priority order (does not need to know cache capacity)
- tracks how many frames were actually consumed by the cache
- can reconstruct the protected frame set based on consumed count
- swappable strategy pattern for different prefetching approaches
#### Design
- Strategies generate frames via `generate_protected_frames()` generator
- FrameCache consumes frames from the generator until it reaches capacity
- Strategy tracks consumed count via `_cacheable_frame_count`
- `protected_frames()` method reconstructs the protected set deterministically
- Frame order must be deterministic and consistent for reconstruction
- Strategies do not need to know cache capacity in advance
- **Note:** `TrivialPrefillStrategy` is a temporary implementation for testing. The final strategy implementation is TBD and may add additional methods to accept data relevant to the caching strategy (e.g., current position, playback direction, video metadata).
#### Creation & Lifecycle
- PrefillStrategy instances are created and updated by PlaybackController (not TimelineController)
- PlaybackController queries TimelineController for resolved frame numbers for each video
- Separate PrefillStrategy instances are created for each video's FrameCache
- **`generate_protected_frames()` is called every time the position changes** to regenerate the protected frame set
- Strategies may be updated when position changes or playback state changes
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
  - submits strategies to FrameCache via `request_prefill_frame()` with callback
  - updates strategies when position or playback state changes
- provides frame callbacks that receive `FrameResult` objects from FrameCache
- coordinates frame display via callbacks (does not directly manage prefetching)
- synchronizes both frame caches to ensure both first frames arrive before display
#### Design
- PlaybackController creates PrefillStrategy instances based on current position
- Submits strategy + callback + decoder to FrameCache via `request_prefill_frame()` for both videos
- FrameCache handles immediate frame fetch for first frame, then queues remaining frames
- **Synchronization mechanism**: Uses thread-safe pending results pattern to coordinate both frame caches
  - Each frame cache callback stores its result in a thread-safe pending results structure
  - When both first frames have arrived, PlaybackController:
    1. Invokes user callback with both `FrameResult` objects
    2. Calls `signal_sync_complete()` on both FrameCaches to allow background prefetching to proceed
  - This ensures both videos are synchronized before any additional prefetching occurs
  - Background workers in FrameCache wait for sync signal before processing queued frames
- **Error handling**:
  - CANCELLED results are discarded (early return)
  - Error results (DECODE_ERROR, SEEK_ERROR, OUT_OF_RANGE) are logged via ErrorHandler
  - User callback receives FrameResult objects, allowing UI to display blank/error frames when needed
  - If one video has an error and the other succeeds, sync signal is still sent (error frame is passed to callback)
- Handles race conditions: when position changes rapidly, old requests are cancelled and new ones initiated
#### Testability
- unit tests on state transitions and emitted requests
- simulated tick tests without GUI
- tests for PrefillStrategy creation and updates
- tests verifying strategies are submitted to FrameCache on position changes
- tests for callback invocation with correct frame data

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

## Error Handling

Each subsystem should define per-class exceptions that match its responsibilities:
- **Media Loading**: Exceptions for file validation, format errors, missing codecs
- **Decode Engine**: Exceptions for decode failures, seek errors, unsupported formats
- **Frame Cache**: Exceptions for cache capacity errors, invalid frame indices
- **Prefill Strategy**: Exceptions for strategy-specific errors (e.g., `FramesNotGeneratedError`)
- **Timeline Controller**: Exceptions for invalid positions, out-of-range seeks
- **Playback Controller**: Exceptions for playback state errors, synchronization failures

Exceptions should be caught at appropriate boundaries and passed to `ErrorHandler` for user-friendly display. Lower-level exceptions may be wrapped in higher-level exceptions to provide context.
