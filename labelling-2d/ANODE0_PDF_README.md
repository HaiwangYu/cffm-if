# Anode0 Frames to PDF Plotter

This script creates a multi-page PDF with 2D heatmaps of all `frame_anode0_plane*` datasets from the rebinned HDF5 file.

## Overview

The script:
1. **Loads all `frame_anode0_plane*` datasets** from the rebinned HDF5 file
2. **Extracts a specific region** for visualization:
   - Channels: from 0 to 50% of max (adjustable)
   - Time: from 80% of max to 100% (adjustable)
3. **Creates 2D heatmaps** for each frame showing detector activity
4. **Saves to multi-page PDF** with configurable plots per page

## Features

### Smart Region Selection
- **Channel range**: Focuses on lower half of channels (helps with visualization)
- **Time range**: Shows high-activity tail of the time window
- Both fractions are fully configurable

### Smart Color Scaling (Frame Type-Specific)

**For PID frames** (`*pid*`):
- **Discrete colormap**: Each unique PID gets a distinct color
- **0 = white** (no PID information)
- Other values cycle through distinct hues for easy differentiation

**For Track ID frames** (`*trackid*`):
- **Fixed 9-color palette**: Cycles through 9 distinct colors based on (trackID % 10)
- **0 = white** (no track information)
- **1-9**: Each maps to a distinct color (red, green, blue, yellow, magenta, cyan, orange, purple, light blue)
- **10+**: Values cycle back (trackID 10 → white, 11 → red, 12 → green, etc.)
- **Categorical labels**: Values treated as labels, not magnitude
- Each track visually distinguished by color without numeric labels

**For Continuous frames** (`gauss`, `charge`):
- **Continuous z-axis**: Linear scaling from 0 to max
- **Color gradient**: White → Green → Blue → Red
- **0 = white** (no signal/charge)
- Percentile-based (2-98%) normalization for dynamic range

**General**:
- **Negative value handling**:
  - **PID & Track ID frames**: Negative values preserved and shown
  - **Gauss & Charge frames**: Negative values clamped to 0 (ignored)
- Each plot independently scaled for clarity
- Color bar shows value range

### Multi-Page PDF
- Supports 1, 2, 3, 4, or 6 plots per page
- Automatic page breaks
- Page numbers in title
- High-quality output (14" x 10" pages)

## Usage

### Basic Usage
```bash
python3 plot_anode0_frames.py --rebinned-file g4-rebinned.h5
```
Creates `anode0_frames.pdf` with default settings (4 plots per page).

### Custom Output Name
```bash
python3 plot_anode0_frames.py \
  --rebinned-file g4-rebinned.h5 \
  --output my_anode0_analysis.pdf
```

### Adjust Region
```bash
python3 plot_anode0_frames.py \
  --rebinned-file g4-rebinned.h5 \
  --ch-max-frac 0.3 \
  --time-min-frac 0.7
```
Shows channels [0, 30% max] and time [70% max, 100% max].

### Change Plots per Page
```bash
python3 plot_anode0_frames.py \
  --rebinned-file g4-rebinned.h5 \
  --plots-per-page 6
```
Creates 3x2 grid of plots (6 per page).

### Full Example
```bash
python3 plot_anode0_frames.py \
  --rebinned-file g4-rebinned.h5 \
  --output anode0_detailed.pdf \
  --ch-max-frac 0.5 \
  --time-min-frac 0.8 \
  --plots-per-page 2
```

## Command Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--rebinned-file` | `g4-rebinned.h5` | Path to rebinned HDF5 file |
| `--output` | `anode0_frames.pdf` | Output PDF filename |
| `--ch-max-frac` | `0.5` | Channel range as fraction of max (0, 1] |
| `--time-min-frac` | `0.8` | Time start as fraction of max [0, 1) |
| `--plots-per-page` | `4` | Plots per page (1, 2, 3, 4, or 6) |

## Region Selection Details

### Channel Dimension
- **Full range**: 0 to N_channels
- **Default (50%)**: 0 to N_channels/2
- **Useful for**: Focusing on specific CRU or wire plane section

Examples:
- `--ch-max-frac 0.25`: Show only first quarter
- `--ch-max-frac 1.0`: Show all channels
- `--ch-max-frac 0.33`: Show one-third

### Time Dimension
- **Full range**: 0 to N_ticks
- **Default (80% start)**: 0.8 * N_ticks to N_ticks
- **Useful for**: Focusing on high-activity tail of event

Examples:
- `--time-min-frac 0.5`: Show second half of time window
- `--time-min-frac 0.9`: Show last 10% (most concentrated activity)
- `--time-min-frac 0.0`: Show entire time window

## Output Description

Each PDF page contains:
- **Page title**: "Anode0 Frames - Page N"
- **Multiple 2D heatmaps**: One per frame type
- **Frame names as titles**: e.g., "frame_anode0_plane0_gauss"
- **Colorbars**: Show value ranges for each plot
- **Axes labels**: Channel (x-axis) and Time Tick (y-axis)

### Color Scale Details

#### PID Frames (discrete categorical)
- **White**: No PID (value = 0)
- **Distinct colors**: Each unique PID gets its own color
- **Legend**: Shows color-to-PID mapping (top-left of plot)
- Makes it easy to identify different particle types at a glance
- **Value labels**: Legend displays the actual PID number for each color
- Useful for counting simultaneous particle species
- **Negative values**: Treated same as positive (mapped to distinct colors)

#### Track ID Frames (discrete categorical with fixed color palette)
- **White**: No track (value = 0)
- **Fixed 9-color palette**: Red, Green, Blue, Yellow, Magenta, Cyan, Orange, Purple, Light Blue
- **Color assignment**: trackID % 10 determines which color
  - trackID 1 → Red, 2 → Green, 3 → Blue, ..., 9 → Light Blue
  - trackID 10 → White (cycles back), 11 → Red, 12 → Green, etc.
- **No legend**: Colors distinguish tracks visually without value labels
- **Important**: TrackID treated as categorical labels, not magnitude
  - The actual number value is irrelevant (100 vs 1000000)
  - What matters is identifying which track is which
  - Fixed colors provide consistent visual differentiation
- **Useful for**: Quickly identifying different particle tracks in a region
- **Negative values**: Treated same as positive (|trackID| % 10)

#### Gauss & Charge Frames (continuous linear)
- **White**: No signal/charge (0)
- **Green**: Low signal (10-30% range)
- **Blue**: Medium signal (30-70% range)
- **Red**: High signal (70-100% range, peaks)

The **White → Green → Blue → Red** progression makes it easy to:
- Identify zero-signal regions (white background)
- See signal strength increasing smoothly
- Distinguish low, medium, and high occupancy regions
- Spot peaks and activity clusters

## What to Look For

### Gauss Frame
- Baseline ionization signal from detector response
- **White regions**: No signal (noise floor, baseline)
- **Green regions**: Weak ionization signal
- **Blue regions**: Medium ionization (typical particle crossings)
- **Red peaks**: Strong ionization (dense particle clusters, stopping particles)
- Coherent **blue-red** structures in time indicate particle tracks
- **Horizontal patterns**: Dead/noisy channels or grounding issues

### Track ID Frames
- Shows which particle/track deposited charge
- **White regions**: No track information (trackID = 0, gaps between particles)
- **Colored regions**: TrackID mapped to color using (trackID % 10)
- **Discrete horizontal bands**: Different tracks with constant IDs in time
- **Fixed color scheme**:
  - 1-9 map to distinct colors (red, green, blue, yellow, magenta, cyan, orange, purple, light blue)
  - 10, 20, 30, ... appear as white (same as trackID 0)
  - 11, 21, 31, ... appear as red, etc.
- **Important**: Treat colors as labels, not magnitude
  - Each color position represents a track entity
  - Colors don't indicate "bigger" or "smaller" values
  - Different colors make it easy to distinguish between different tracks
  - Useful for identifying which particles left which tracks
- 1st vs 2nd comparison shows energy dominance hierarchy
- **Note**: Negative values treated same as positive (|trackID| % 10)

### PID Frames
- Shows particle type identification (electron, photon, proton, etc.)
- **White regions**: No PID information (value = 0)
- **Distinct colors for each value**: Each unique PID gets its own hue
- Each colored band represents a specific particle type
- Should **overlap spatially** with high-signal regions in gauss/charge frames
- Width of colored region shows particle track extent
- Multiple colors at same time = multiple particle species
- **Negative values**: Displayed with distinct colors (treated like positive values)

### Charge Frames
- Direct energy deposit values from simulation
- **White**: Zero charge regions
- **Green-Blue**: Low-to-medium charge deposits
- **Red peaks**: Maximum charge (ionization hotspots)
- Similar spatial pattern to gauss but shows absolute energy
- 1st vs 2nd charge comparison shows energy splitting:
  - Both **red** = single dominant particle
  - **Red + Blue**: Secondary particle contribution
  - **White + colored**: Gaps indicating dead zones

## Example Workflow

```bash
# Step 1: Generate rebinned data
python3 rebin_frames.py --output g4-rebinned.h5

# Step 2: Create overview plots
python3 plot_anode0_frames.py \
  --rebinned-file g4-rebinned.h5 \
  --output anode0_overview.pdf

# Step 3: Zoom in on interesting region
python3 plot_anode0_frames.py \
  --rebinned-file g4-rebinned.h5 \
  --output anode0_zoom.pdf \
  --ch-max-frac 0.25 \
  --time-min-frac 0.85 \
  --plots-per-page 2

# Step 4: View PDF
display anode0_overview.pdf
```

## Performance Notes

- **Fast generation**: < 10 seconds for typical file
- **Memory efficient**: Loads one frame at a time
- **PDF size**: ~2-5 MB depending on complexity
- **Quality**: 150 DPI equivalent, suitable for printing

## Troubleshooting

### No frames found
- Check that rebinned file was created successfully
- Verify file contains `frame_anode0_plane*` datasets
- Use inspect option to check file contents

### Plots look empty/flat
- Try adjusting `--time-min-frac` to capture more activity
- Increase `--ch-max-frac` to show more channels
- Check that source data has signal

### PDF is very large
- Reduce `--plots-per-page` to decrease figure complexity
- Use `--ch-max-frac` to show fewer channels
- Consider splitting into multiple files for different regions

## Modifying the Script

### Change normalization percentiles (continuous frames only)
Edit the `plot_frame()` method in the continuous frame section:
```python
# Current: 2nd to 98th percentile (excludes 1% outliers)
vmax = np.percentile(data[data > 0], 98)

# More aggressive (1% to 99%):
vmax = np.percentile(data[data > 0], 99)

# Minimal clipping (5% to 95%):
vmax = np.percentile(data[data > 0], 95)

# Full range (no clipping):
vmax = data_max
```

### Change continuous color gradient
Modify the `create_white_zero_colormap()` method:

```python
# Current: White -> Green -> Blue -> Red
colors_list = [
    (1.0, 1.0, 1.0),    # white
    (0.5, 1.0, 0.5),    # light green
    (0.0, 1.0, 0.0),    # green
    (0.0, 0.5, 1.0),    # blue
    (0.0, 0.0, 1.0),    # darker blue
    (1.0, 0.0, 0.0),    # red
]

# Alternative: White -> Yellow -> Red
colors_list = [
    (1.0, 1.0, 1.0),    # white
    (1.0, 1.0, 0.0),    # yellow
    (1.0, 0.5, 0.0),    # orange
    (1.0, 0.0, 0.0),    # red
]

# Alternative: White -> Purple
colors_list = [
    (1.0, 1.0, 1.0),    # white
    (1.0, 0.5, 1.0),    # light purple
    (0.5, 0.0, 1.0),    # purple
    (0.0, 0.0, 0.5),    # dark purple
]
```

### Change legend appearance (PID frames only)
Edit the legend creation in `plot_frame()` for PID frames:
```python
# Current: legend in upper left with black edges
ax.legend(legend_patches, legend_labels, loc='upper left', fontsize=8,
         framealpha=0.9, title='Value', title_fontsize=8)

# Alternative: legend in upper right
ax.legend(legend_patches, legend_labels, loc='upper right', fontsize=8,
         framealpha=0.9, title='Value', title_fontsize=8)

# Alternative: legend in lower right with transparency
ax.legend(legend_patches, legend_labels, loc='lower right', fontsize=8,
         framealpha=0.7, title='Value', title_fontsize=8, fancybox=True, shadow=True)
```

Note: TrackID frames do not use legends - they use distinct colors to differentiate tracks visually.

### Understanding TrackID color mapping
TrackID frames use a fixed 9-color palette with modulo-based mapping:
```
Color mapping (trackID % 10):
- 0 → white (no track)
- 1 → red
- 2 → green
- 3 → blue
- 4 → yellow
- 5 → magenta
- 6 → cyan
- 7 → orange
- 8 → purple
- 9 → light blue
```

Example: If your data contains trackID values like 101, 102, 103:
- 101 % 10 = 1 → **red**
- 102 % 10 = 2 → **green**
- 103 % 10 = 3 → **blue**

Note: If you have trackID 10, 20, 30, they will appear white like trackID 0.

### Change TrackID color palette
Edit the `create_trackid_colormap()` method to use different colors:
```python
# Current: white, red, green, blue, yellow, magenta, cyan, orange, purple, light blue
colors = [
    (1.0, 1.0, 1.0),    # 0: white (no track)
    (1.0, 0.0, 0.0),    # 1: red
    (0.0, 1.0, 0.0),    # 2: green
    (0.0, 0.0, 1.0),    # 3: blue
    (1.0, 1.0, 0.0),    # 4: yellow
    (1.0, 0.0, 1.0),    # 5: magenta
    (0.0, 1.0, 1.0),    # 6: cyan
    (1.0, 0.5, 0.0),    # 7: orange
    (0.5, 0.0, 1.0),    # 8: purple
    (0.0, 0.5, 1.0),    # 9: light blue
]
```

### Change PID discrete colormap strategy
Edit the `create_discrete_pid_colormap()` method to use different colors:
```python
# Change the HSV to RGB conversion range or use matplotlib built-in colors
# For example, use a fixed color list:
colors = [
    (1.0, 1.0, 1.0),    # white for 0
    (1.0, 0.0, 0.0),    # red
    (0.0, 1.0, 0.0),    # green
    (0.0, 0.0, 1.0),    # blue
    (1.0, 1.0, 0.0),    # yellow
    (1.0, 0.0, 1.0),    # magenta
    (0.0, 1.0, 1.0),    # cyan
]
```

### Change figure size
Edit the `save_to_pdf()` method:
```python
fig, axes = plt.subplots(rows, cols, figsize=(16, 12))  # Larger
fig, axes = plt.subplots(rows, cols, figsize=(10, 8))   # Smaller
```

## Dependencies

```bash
pip install h5py numpy matplotlib
```

All standard libraries - should be available in any Python environment with scientific packages.

## Frame Names

The script automatically finds and plots all datasets matching:
```
frame_anode0_plane0_*
frame_anode0_plane1_*
frame_anode0_plane2_*
```

Typical frame names:
- `frame_anode0_plane0_gauss`
- `frame_anode0_plane0_orig_trackid_1st`
- `frame_anode0_plane0_orig_pid_1st`
- `frame_anode0_plane0_current_pid_1st`
- `frame_anode0_plane0_charge_1st`
- `frame_anode0_plane0_orig_trackid_2nd`
- ... (similar for plane1 and plane2)

Each plane is processed independently.
