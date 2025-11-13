# Detector Frame Analysis Pipeline

This directory contains tools for extracting, rebinning, and visualizing detector frame data from LArSoft simulations.

## Quick Start Workflow

```bash
# 1. Generate extended track information frames
lar -n 1 -c wcls-labelling2d.fcl -s xuyang.root --no-output

# 2. Rebin frames from output HDF5 files
python3 rebin_frames.py --rebin-time 2 --rebin-channel 2

# 3. Create PDF visualization
python3 plot_anode0_frames.py --rebinned-file g4-rebinned.h5 --output anode0_frames.pdf

# 4. (Optional) Plot 1D channel projections
python3 plot_rebinned_channels.py --channels 100 200 300
```

## Scripts

### `rebin_frames.py`
Rebins frame data from `g4-rec.h5` and `g4-tru.h5` with intelligent track contribution ranking.

**Usage:**
```bash
python3 rebin_frames.py [--rebin-time 2] [--rebin-channel 2] [--output g4-rebinned.h5]
```

**Details:** See [REBIN_README.md](REBIN_README.md)

### `plot_anode0_frames.py`
Creates multi-page PDF with 2D heatmaps of all anode0 frame types (gauss, trackID, PID, charge).

**Usage:**
```bash
python3 plot_anode0_frames.py --rebinned-file g4-rebinned.h5 \
  --output anode0_frames.pdf \
  --ch-max-frac 0.5 \
  --time-min-frac 0.8 \
  --plots-per-page 4
```

**Details:** See [ANODE0_PDF_README.md](ANODE0_PDF_README.md)

### `plot_rebinned_channels.py`
Plots 1D time projections for specific channels with 1st and 2nd contribution overlays.

**Usage:**
```bash
python3 plot_rebinned_channels.py --channels 100 200 300 --output-prefix my_channels

# Inspect file structure
python3 plot_rebinned_channels.py --inspect
```

**Details:** See [PLOT_README.md](PLOT_README.md)

### `quick_inspect.py`
Quick inspection of HDF5 file contents.

**Usage:**
```bash
python3 quick_inspect.py g4-rebinned.h5
```

## Output Files

- `g4-rec.h5`: Reconstructed frame data (gauss)
- `g4-tru.h5`: Truth frame data (trackID, PID, charge)
- `g4-rebinned.h5`: Rebinned and processed frames
- `anode0_frames.pdf`: 2D visualization heatmaps
- `rebinned_channel*.png`: 1D channel projection plots


