# Video Comparator UI Layout Diagram

## Overall Structure

```
┌───────────────────────────────────────────────────────────────┐
│                         MainFrame                             │
│                      (wx.Frame - Top Level)                   │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              video_container (wx.Panel)                  │ │
│  │                                                          │ │
│  │  ┌──────────────────┐  ┌──────────────────┐              │ │
│  │  │   VideoPane 1    │  │   VideoPane 2    │              │ │
│  │  │  (Video Display) │  │  (Video Display) │              │ │
│  │  │                  │  │                  │              │ │
│  │  │  - Frame render  │  │  - Frame render  │              │ │
│  │  │  - Zoom/Pan      │  │  - Zoom/Pan      │              │ │
│  │  │  - Overlays      │  │  - Overlays      │              │ │
│  │  └──────────────────┘  └──────────────────┘              │ │
│  │                                                          │ │
│  │  Layout: Horizontal (side-by-side) or                    │ │
│  │          Vertical (top/bottom) based on orientation      │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │          ControlPanel (wx.Panel)                         │ │
│  │                                                          │ │
│  │  Row 1: Timeline Slider                                  │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │         Timeline Slider (horizontal)               │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  Position Label: "00:00:00.000 / Frame 0 (V1), 0"  │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  │                                                          │ │
│  │  Row 2: Playback Controls                                │ │
│  │  ┌─────────┐ ┌──────┐ ┌───────┐ ┌─────────┐ ┌───────┐    │ │
│  │  │ Step -1 │ │ Play │ │ Pause │ │ Step +1 │ │ Stop  │    │ │
│  │  └─────────┘ └──────┘ └───────┘ └─────────┘ └───────┘    │ │
│  │                                                          │ │
│  │  Row 3: Sync Controls (for Video 2)                      │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  Sync Offset Slider (horizontal)                   │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  │  ┌──────┐ ┌──────┐ ┌──────────────────────────────────┐  │ │
│  │  │  -1  │ │  +1  │ │  Offset Label: "Offset: 0 frames"│  │ │
│  │  └──────┘ └──────┘ └──────────────────────────────────┘  │ │
│  │                                                          │ │
│  │  Row 4: Zoom Controls                                    │ │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌────────┐     │ │
│  │  │ Zoom In  │ │ Zoom Out │ │ Reset Zoom │ │ Zoom:  │     │ │
│  │  │          │ │          │ │            │ │ 1.00x  │     │ │
│  │  └──────────┘ └──────────┘ └────────────┘ └────────┘     │ │
│  │                                                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Layout Hierarchy

```
MainFrame (wx.Frame)
│
├── Main Sizer (wx.BoxSizer - VERTICAL)
│   │
│   ├── video_container (wx.Panel) - proportion=1, flag=EXPAND
│   │   │
│   │   └── Video Sizer (wx.BoxSizer - HORIZONTAL or VERTICAL)
│   │       │
│   │       ├── VideoPane 1 - proportion=1, flag=EXPAND
│   │       │
│   │       └── VideoPane 2 - proportion=1, flag=EXPAND
│   │
│   └── ControlPanel.panel (wx.Panel) - proportion=0, flag=EXPAND|ALL, border=5
│       │
│       └── Control Panel Sizer (wx.BoxSizer - VERTICAL)
│           │
│           ├── Timeline Slider Row (wx.BoxSizer - VERTICAL)
│           │   ├── Timeline Slider (wx.Slider) - proportion=1, flag=EXPAND
│           │   └── Position Label (wx.StaticText)
│           │
│           ├── Playback Controls Row (wx.BoxSizer - HORIZONTAL)
│           │   ├── Play Button
│           │   ├── Pause Button
│           │   ├── Stop Button
│           │   ├── Step Backward Button
│           │   └── Step Forward Button
│           │
│           ├── Sync Controls Row (wx.BoxSizer - VERTICAL)
│           │   ├── Sync Offset Slider (wx.Slider) - proportion=1, flag=EXPAND
│           │   └── Sync Buttons Row (wx.BoxSizer - HORIZONTAL)
│           │       ├── Decrement Button (-1)
│           │       ├── Increment Button (+1)
│           │       └── Offset Label (wx.StaticText)
│           │
│           └── Zoom Controls Row (wx.BoxSizer - HORIZONTAL)
│               ├── Zoom In Button
│               ├── Zoom Out Button
│               ├── Reset Zoom Button
│               └── Zoom Label (wx.StaticText)
```

## Key Layout Principles

1. **MainFrame** uses a vertical BoxSizer
   - Video container takes most space (proportion=1, EXPAND)
   - Control panel takes minimal space (proportion=0, no EXPAND)

2. **Video Container** uses horizontal or vertical BoxSizer based on orientation
   - Both VideoPanes get equal space (proportion=1, EXPAND)

3. **Control Panel** uses a vertical BoxSizer with multiple rows:
   - Each row is a horizontal BoxSizer for related controls
   - Rows are stacked vertically
   - Proper spacing and borders between sections

4. **Widget Sizing**:
   - Video panes: Expand to fill available space
   - Buttons: Natural size (no expansion)
   - Sliders: Expand horizontally (proportion=1, flag=EXPAND)
   - Labels: Natural size

## Current Problem

The `ControlPanel` class creates all widgets but **never sets up a sizer** to lay them out. This causes all widgets to overlap at position (0,0) with default sizes.

## Solution

Add a `_create_layout()` method to `ControlPanel` that:
1. Creates a vertical BoxSizer for the main panel
2. Creates horizontal BoxSizers for each row of controls
3. Adds widgets to their respective rows
4. Adds rows to the main sizer
5. Sets the sizer on the panel
