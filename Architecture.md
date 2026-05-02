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
    - File
      - File > Open Video 1 / Open Video 2 trigger file chooser and load video for the corresponding pane;
    - View
      - View > Toggle Layout toggles orientation and refreshes layout
      - View > Toggle Scaling Mode toggles scaling mode (independent vs "match larger").
    - Help
- quitting lifecycle.
- **Playback timer**: A wx.Timer fires periodically (e.g. ~33 ms). When PlaybackController state is PLAYING, Application calls `tick(delta)` and updates the timeline slider so playback advances **forward or backward** per controller direction and panes refresh.
- **Timeline position change**: When the user changes the timeline position (e.g. slider drag), TimelineSlider invokes an optional callback; Application uses it to call PlaybackController.request_frames_at_current_position() so the video panes display the frame(s) at the new position.
#### Testability
- unit tests for wiring (mocks)
- smoke tests that instantiate the app without loading media.

### 2) Media Loading & Metadata
#### Responsibilities
- file selection
- validation
- probing via PyAV (duration, fps, coded dimensions, pixel format, total_frames, time_base, sample/display aspect metadata)
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
- surface all decoded work products to the caller (single target frame plus any intermediate frames decoded while satisfying that request)
- optimize for low latency to requested frame, not maximum background throughput.
#### Testability
- unit tests on deterministic sample clips to assert decoded frame indices/timestamps
- test files from `tests/sample_data/` directory.

**Note:** Hardware acceleration is not implemented to keep dependencies simple.

**Thread safety:** PyAV (and the underlying FFmpeg/libav libraries) do not support concurrent use of the same container or decoder from multiple threads. Decoding or seeking on a given VideoDecoder must be serialized (e.g. per-decoder locking in the caller). The main thread may decode the first frame while FrameCache’s prefetch worker later decodes additional frames for the same video; if both can call into the same decoder, access must be protected to avoid races and segfaults.

**Frame-accurate decode:** FFmpeg/PyAV container seek is keyframe-based: seeking lands on the nearest keyframe (I-frame) at or before the requested time, not on an arbitrary frame. To deliver the exact requested frame index, the decode engine must seek to that timestamp (keyframe), then **decode forward** from the keyframe until the decoded frame index matches the request, and return that frame. Returning only the first decoded frame after seek yields the keyframe repeatedly for all requests within that GOP (e.g. frames 0–249 identical if keyframe interval is 250).

**Decoder/Cache contract:** The decoder does not decide frame priority or retention policy. FrameCache chooses what to request and when. Decoder APIs may expose results either by return values or callbacks (implementation detail), but must make all decoded frames from a decode operation available to FrameCache so FrameCache can apply retention policy.

**Decoder locality policy:** For each request, decoder execution should prefer the lowest-latency operation relative to current decode cursor/container state. If the target frame is near current decode position, decode forward without a new seek; if far, perform seek+decode-forward from keyframe. This is a latency optimization policy owned by decoder execution, while request priority remains owned by FrameCache.

### 4) Frame Cache & Prebuffer
#### Responsibilities
- LRU eviction policy with protected frame set
- memory bounds management
- frame storage and retrieval
- autonomous background prefetching of frames
- integration with PrefillStrategy to protect frames from eviction
- race condition handling via request cancellation
- strict request prioritization so UI-requested frame is always first
- retention policy where strategy-preferred frames take precedence over pure LRU.
#### Design
- FrameCache operates as an autonomous entity with its own background prefetch thread
- PlaybackController submits a fully-configured PrefillStrategy and a callback function to FrameCache
- FrameCache is the scheduler and retention authority; decoder is an execution engine
- FrameCache interface:
  1. Receives PrefillStrategy + callback from PlaybackController
  2. **Cancels all pending requests** when new request arrives (prevents race conditions)
  3. Generates first frame number from strategy (`generate_protected_frames`) and acquires it first (cache hit or miss via VideoDecoder)
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
- Strategy-preferred frames always outrank non-strategy frames for residency decisions; LRU resolves ties/surplus among non-preferred frames
- Capacity is calculated based on available memory and frame size estimates
- FrameCache manages its own prefetch thread lifecycle and queue
- When new request arrives, FrameCache cancels all pending prefetch requests and starts new prefetch cycle
- Callbacks receive `FrameResult` objects that convey frame data or failure reasons
- **Decoder access:** The same VideoDecoder may be used from the main thread (first-frame fetch) and from the prefetch worker. Because PyAV/FFmpeg are not thread-safe, decode calls must be serialized per decoder (e.g. a lock in FrameCache around decode, or a per-decoder lock).
- **Priority and preemption model:** Use cooperative, low-complexity reprioritization. In-flight decode is not force-interrupted mid-operation; after each decode operation completes, FrameCache must immediately choose the current highest-priority task (with UI-requested frame first). This minimizes UI latency without adding extra thread-coordination complexity.
- **Cache population rule:** Any frame the decoder actually decodes for a FrameCache request must be offered to FrameCache for potential insertion. FrameCache may still evict/drop based on strategy and memory constraints.
- **Single insertion authority:** FrameCache is the sole cache writer. Decoder must not independently insert into cache; this prevents duplicate insertion paths and ambiguous ownership.
- **Hot-path complexity target:** Cache recency bookkeeping and membership checks should be O(1)-style operations in steady state. Memory accounting should be maintained incrementally (running totals) rather than repeatedly summing all cached frame sizes on each insert/evict path.
- **Copy minimization policy:** Frame copies in hot cache paths should be minimized while preserving safety/correctness. Avoid redundant copy chains across decode -> cache insert -> cache read when immutability guarantees already exist.
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
- optimizes for low latency of requested UI frame delivery over total cache-fill speed.
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
- **Resolved-time semantics:** `resolved_time_video1` and `resolved_time_video2` are per-video source times for the actually resolved display frames. With non-zero sync offset, these times should typically differ by approximately `offset / fps_video2` (subject to clamping/rounding at bounds), and must not collapse to identical values due to inverse-conversion cancellation.
- **Offset consistency invariant:** for video 2, `time -> frame -> time` and `frame -> time -> frame` mappings must preserve offset semantics consistently, including positive and negative offsets and boundary clamps.

#### Testability
- pure logic tests for offset math
- frame/time conversions
- layout-mode impacts on displayed sizes.

### 6) Playback & Stepping Controller
#### Responsibilities
- play/pause/stop state machine extended with **playback direction**: continuous playback advances timeline toward **maximum** or **minimum** via periodic `tick()` (mirror existing speed/`playback_speed` semantics); reverse playback clamps/stops at timeline **start** analogous to forward at **end**.
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
- **Displayed frame metadata correctness:** callback time/frame metadata used by overlays must correspond to the delivered frame results for that callback cycle (not stale/advanced timeline state from a later moment).
- **Step/play continuity:** after pause + frame-step (+/-) + play, playback should continue from the stepped position without discontinuous jumps to an unrelated timestamp — **including** after switching between reverse play and forward play from pause or mid-playback as specified.
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
- **Single-video mode**: PlaybackController may be created with decoder_video2 (or decoder_video1) as None when only one video is loaded. Only the loaded video's FrameCache receives request_prefill_frame(). A placeholder FrameResult (frame=None, status=SUCCESS) is used for the missing side so the frame callback is invoked with (result1, result2) and the UI updates only the loaded pane; effective timeline duration is that of the loaded video.
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
- display aspect-aware presentation (honor SAR/DAR so anamorphic sources are not stretched)
- playback time/frame
- zoom level
- overlay time/frame text reflects the actual frame currently displayed in that pane, including per-video sync offsets
- maintain zoom/pan state across seeks/steps/layout changes
- reset zoom/pan for a pane when a new video is loaded into that pane (and both panes when synchronized-zoom mode requires matched factors); wire from Application/media load path into `VideoPane` / control-panel zoom display
- expose **pan-only** reset (zoom unchanged), distinct from `reset_zoom_pan()` / full view reset, for the **Reset Pan** control
- mouse interactions:
  - mouse drag for panning
  - scroll wheel for zoom in/out
  - Shift-drag rectangle for zoom to region
- **Empty state**: Clicking the "no video loaded" overlay (or empty pane) opens the file chooser for that pane so the user can load a video by clicking where it will appear.
#### Testability
- logic tests for transform math (pan/zoom/fit calculations)
- mouse event handling tests (drag, wheel, Shift-drag)
- golden-image tests optional via offscreen buffers.

### 8) Layout & Controls
#### Responsibilities
- toggle orientation (horizontal/vertical) and scaling mode (independent fit vs. match larger video), wired to View menu and/or shortcuts
- timeline slider (optional on_position_changed callback so Application can request frames when user seeks)
- play (**forward** and **reverse**, captions `◀ Play` / `▶ Play` per Specification §5); pause/stop; **both direction-specific play buttons enabled only when at least one video is loaded**
- frame-step buttons
- sync-offset slider + ±1 buttons; **sync controls enabled only when both videos are loaded**
- zoom controls: zoom in/out; **Reset Zoom** (full zoom+pan restore — enabled only when any pane zoom ≠ 1× per §7); **Reset Pan** to the right of the zoom label (pan-only — enabled when either pane pan ≠ default centered); zoom level label foreground turns **red** vs default text colour when any displayed zoom factor is not exactly 1× (see Specification §7); refresh enabled states whenever zoom/pan changes or displays update
- layout mode toggle
- routes UI events to controllers.
#### Testability
- event wiring tests (signals -> controller calls)
- deterministic UI command tests with mocks.

### 9) Input & Shortcuts
#### Responsibilities
- keyboard shortcuts for
  - play/pause (extend documentation when implementing reverse vs forward shortcuts — distinct bindings recommended if shortcuts remain parity with toolbar)
  - step
  - zoom
  - sync nudge
  - layout toggle
  - (optional / future) **Reset Zoom** and **Reset Pan** if shortcuts are extended beyond toolbar parity with Specification §7
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
