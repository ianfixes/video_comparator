# Contributing

## Setting up the environment

Use `poetry`: `poetry install`.

## Technology Stack

### Core Framework: Python + wxPython (wxWidgets)

**Rationale:**
- **Cross-platform support**: Native compatibility with macOS and Linux (and Windows if needed)
- **Minimal dependencies**: No Xcode or complex build tools required - installs via pip/poetry
- **Frame-accurate display control**: Custom `wx.Panel` with `wx.PaintDC` provides pixel-perfect control over zoom and pan operations via transform matrices
- **Native look and feel**: Uses platform-native widgets for consistent user experience
- **Mature ecosystem**: Well-documented, stable, and actively maintained
- **Performance**: Rendering handled by wxWidgets C++ backend, ensuring smooth display operations

### Video Decoding: FFmpeg via PyAV

**Rationale:**
- **Frame-accurate seeking**: Essential requirement - FFmpeg provides precise frame-level seeking capabilities
- **Format support**: Comprehensive support for common formats (MP4, MKV, AVI, ProRes, H.264, H.265)
- **Hardware acceleration**: Optional support via FFmpeg's hardware acceleration backends
- **Python integration**: PyAV provides clean Python bindings to FFmpeg's libavcodec/libavformat

### Image Processing: NumPy

**Rationale:**
- **Frame data manipulation**: Efficient handling of decoded video frames as arrays
- **Interoperability**: Seamless conversion between PyAV frame data and wxPython image formats (wx.Bitmap)
- **Performance**: NumPy operations are optimized C implementations

## Architecture Overview

The application follows a modular architecture:

```
┌─────────────────────────────────────┐
│  GUI Layer: wxPython (wxWidgets)    │
│  - wx.Frame, wx.Panel               │
│  - Custom video pane widgets        │
│  - Standard controls (sliders, etc.)│
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│  Video Processing: PyAV (FFmpeg)    │
│  - Frame-accurate decoding          │
│  - Frame-accurate seeking           │
│  - Format support                   │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│  Image Processing: NumPy            │
│  - Frame data manipulation          │
│  - Scaling/transformation           │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│  Display: wx.Bitmap                 │
│  - Hardware-accelerated rendering   │
│  - Zoom/pan via custom PaintDC      │
└─────────────────────────────────────┘
```

## Key Design Principles

1. **Frame Accuracy First**: The application prioritizes precise frame selection and display over raw processing speed. Frame decoding and rendering are handled by optimized C/C++ libraries (FFmpeg and wxWidgets), while Python orchestrates the control logic.

2. **Exact Display Control**: Using wxPython's `wx.PaintDC` with transform matrices in custom `wx.Panel` widgets, the application can display any portion of any frame at any zoom level with pixel-level precision.

3. **Modular Design**: The architecture separates concerns (decoding, display, control) to enable future extensibility (e.g., quality metrics, annotation tools).

## Dependencies

See `pyproject.toml` for complete dependency specifications. Key dependencies:

- **wxPython**: wxWidgets Python bindings for cross-platform GUI (no Xcode required)
- **av** (PyAV): FFmpeg Python bindings for video decoding
- **numpy**: Frame data manipulation and array operations

## Development Setup

This project uses Poetry for dependency management. To set up the development environment:

```bash
poetry install
```

## Requirements

- Python 3.9 or higher
- FFmpeg libraries (installed system-wide or via package manager)
- wxWidgets runtime libraries (included with wxPython package)

## Keyboard shortcuts (defaults)

Bindings match **`Specification.md`** (§§3–7, §11). The main window handles **`EVT_CHAR_HOOK`** so shortcuts run before focused children (video panes, sliders, etc.) consume keys.

| Key | Action |
|-----|--------|
| **Space** | Play/pause: pauses when playing; **unpause always forward**; from stopped (with media), start forward |
| **Shift+Space** | From **paused**: unpause **always reverse**; from **stopped**: start reverse; while **playing**, toggles direction (forward ↔ reverse) |
| **← / →** | Seek timeline **10 seconds** backward / forward (clamped) |
| **.** (period) | Step **forward** one frame |
| **,** (comma) | Step **backward** one frame |
| **−** (minus) | Sync offset **−1** frame (when both videos loaded) |
| **=** (equals) | Sync offset **+1** frame (when both videos loaded) |

Other defaults: **Ctrl+S** Stop, **Ctrl+L** layout, **Ctrl+Shift+M** scaling, **Ctrl+[** / **Ctrl+]** zoom out/in, **0** reset zoom (see `Architecture.md` §9).

## Testing

The project uses pytest for unit and integration tests. Test files are located in the `tests/` directory.

### Test Data

Test video files are available in `tests/sample_data/`:
- `file_example_AVI_*.avi` files for testing video decoding and metadata extraction

### Testing wxPython Components

wxPython components should be mocked in unit tests. No test fixtures are currently available for wxPython widgets. Consider using context manager-based mocking (e.g., `unittest.mock.patch`) rather than decorators, following the project's testing conventions.

### Running Tests

Run the validation script to execute all linting and tests:

```bash
./validate.sh
```

This runs:
- `isort` for import sorting
- `black` for code formatting
- `mypy` for type checking
- `pytest` for unit and integration tests
