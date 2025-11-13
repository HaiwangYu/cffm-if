# Rebinned Channel Plotting Script

This script creates 1D time projection plots for specific channels from the rebinned HDF5 file.

## Overview

For each requested channel:
1. **Determines the anode and plane** based on channel geometry
2. **Loads all frame types** from the rebinned file
3. **Extracts 1D time projection** (time series for that channel)
4. **Creates two overlapping plots**:
   - **Plot 1: 1st Contributions** - shows `orig_trackid_1st`, `orig_pid_1st`, `current_pid_1st`, `charge_1st` with gauss as reference
   - **Plot 2: 2nd Contributions** - shows `orig_trackid_2nd`, `orig_pid_2nd`, `current_pid_2nd`, `charge_2nd` with gauss as reference

## Features

### Smart Normalization
- Each frame is **independently normalized** to [0, 1] using min-max scaling
- This allows overlapping plots to show all frames clearly without one dominating
- Gauss frame uses thicker line and higher z-order for visibility

### Channel to Anode/Plane Mapping
Automatically determines:
- **Anode ID** (0-7): From CRP (Common Readout Plane)
- **Plane ID** (0-2): From wire type (U, V, W)
- **Channel index**: Local index within the plane

### Color Coding
- **Gauss**: Black (thicker line, reference)
- **1st contributions**: Red variants (red, green, blue, orange)
- **2nd contributions**: Dark variants (darkred, darkgreen, darkblue, darkorange)

## Usage

### Basic Usage
```bash
python3 plot_rebinned_channels.py --channels 100 200 300
```
Plots channels 100, 200, and 300 from `g4-rebinned.h5` in current directory.

### Custom Rebinned File
```bash
python3 plot_rebinned_channels.py \
  --rebinned-file /path/to/g4-rebinned.h5 \
  --channels 1000 2000 3000
```

### With Output Prefix
```bash
python3 plot_rebinned_channels.py \
  --channels 100 200 300 \
  --output-prefix my_analysis
```
Creates files: `my_analysis_channel100.png`, `my_analysis_channel200.png`, etc.

## Channel Number Reference

### Channel Format
Channels are numbered based on the detector layout:
```
channel = 3072 * crp + channel_in_crp
```

Where:
- **CRP** (0-3): Common Readout Plane
  - CRP 0: Channels 0-3071
  - CRP 1: Channels 3072-6143
  - CRP 2: Channels 6144-9215
  - CRP 3: Channels 9216-12287

- **Channel in CRP** (0-3071):
  - U plane CRU0: 0-476
  - U plane CRU1: 476-951
  - V plane CRU0: 952-1428
  - V plane CRU1: 1428-1903
  - W plane CRU0: 1904-2488
  - W plane CRU1: 2488-3071

### Example Channel Maps
```
Channel 100 → CRP 0, CRU0 U plane, local ch 100
Channel 500 → CRP 0, CRU1 U plane, local ch 24
Channel 1000 → CRP 0, CRU0 V plane, local ch 48
Channel 3100 → CRP 1, CRU0 U plane, local ch 28
```

## Output Files

For each channel, creates a PNG file with:
- **Top plot**: 1st contributions with gauss reference
- **Bottom plot**: 2nd contributions with gauss reference
- Each frame properly labeled and colored
- Time tick on x-axis, normalized value (0-1) on y-axis
- Legends showing frame names

## Example Workflow

```bash
# Step 1: Rebin the data
python3 rebin_frames.py \
  --rebin-time 2 \
  --rebin-channel 2 \
  --output g4-rebinned.h5

# Step 2: Inspect some channels
python3 plot_rebinned_channels.py \
  --rebinned-file g4-rebinned.h5 \
  --channels 100 500 1000 2000 \
  --output-prefix analysis1

# Step 3: View generated plots
display analysis1_channel100.png
display analysis1_channel500.png
...
```

## What to Look For

### Gauss Frame
- Baseline/reference signal
- Should be smooth and continuous
- Use to identify high-activity regions

### Track ID Frames
- Should follow similar pattern to gauss but with discrete values
- Different tracks will show as different horizontal plateaus

### PID Frames
- Shows particle identification
- Discrete integer values
- Should correlate with regions of high charge

### Charge Frames
- Continuous values showing energy deposit
- Should correlate strongly with gauss frame
- Helps identify which deposits are 1st vs 2nd

### 1st vs 2nd Comparison
- 1st contributions usually dominate high-charge regions
- 2nd contributions appear where multiple particles contribute
- Gaps indicate single-particle regions
- Overlaps show multi-particle collision sites

## Troubleshooting

### "Frame not found" warnings
- Check that rebinned file was created with `save_extended_labels: true`
- Verify the rebinning script included the frame type

### Channels appear flat/empty
- Channel may not have any signal
- Try channels in different regions
- Check that the channel number is valid (< 12288)

### Low contrast/hard to see
- Frames are independently normalized - this is intentional
- Try zooming into specific time ranges
- Modify the script to focus on non-zero regions if needed

## Modifying the Script

### Change colors
Edit the `colors` dictionary in `plot_channel()` method.

### Change normalization
Replace `normalize_data()` calls with alternative scaling (e.g., log scale, percentile-based).

### Add more frames
Extend `first_frames` and `second_frames` lists in `plot_channel()`.

### Change plot style
Modify matplotlib parameters (DPI, figure size, line widths, etc.) in the plotting calls.

## Dependencies

```bash
pip install h5py numpy matplotlib
```

## Performance Notes

- Fast for single channels (< 1s per plot)
- Loading file is done once, then closed after all plots
- Memory efficient (only loads one channel at a time)
- Suitable for analyzing 100+ channels in batch mode
