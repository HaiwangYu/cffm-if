# Frame Rebinning Script

This script performs intelligent rebinning of the output frames from `g4-rec.h5` and `g4-tru.h5` files.

## Overview

The script:
1. **Loads only frame datasets** from both HDF5 files (items with "frame" in their names) and verifies they have matching dimensions
   - Ignores other datasets that may have different dimensions
2. **Separates channels** into 8 anodes (CRUs), with 3 planes per anode (ProtoDUNE-VD geometry)
   - Each anode is a single CRU with U, V, W planes
3. **Rebins data separately** for each plane independently
4. **Handles different frame types**:
   - `g4-rec.h5`: `frame_gauss` is rebinned by **summing** values
   - `g4-tru.h5`: Track-based frames are rebinned by tracking **1st and 2nd** contributions based on charge

### Important: Frame Selection
The script **only loads datasets with "frame" in their name** to ensure all loaded data has consistent dimensions. This filters out any auxiliary data that might have different shapes.

## Rebinning Logic

### For g4-rec.h5 (gauss frame)
- When multiple pixels are combined into one rebinned pixel, **all values are summed**

### For g4-tru.h5 (track-based frames)
For each rebinned bin:
1. Collect **all contributions** (both "1st" and "2nd") from the small bins it contains
2. **Group by value** (trackID/PID) and **sum their charges**
   - If the same track/PID appears in multiple small bins, their charges are combined
3. Sort by combined charge (descending)
4. Assign:
   - **1st**: The track/PID with biggest combined charge
   - **2nd**: The track/PID with 2nd biggest combined charge

This correctly handles cases where the same track appears across multiple small bins within a rebinned pixel, ensuring proper 1st/2nd ranking based on total charge contribution.

## Usage

### Basic Usage (default parameters)
```bash
python3 rebin_frames.py
```
Assumes:
- Input: `g4-rec.h5`, `g4-tru.h5` in current directory
- Output: `g4-rebinned.h5`
- Rebin factors: 2x2 (channel × time)

### Custom Rebin Factors
```bash
python3 rebin_frames.py --rebin-time 4 --rebin-channel 2
```
- Rebin by 2 in channel dimension
- Rebin by 4 in time dimension

### Custom File Paths
```bash
python3 rebin_frames.py \
  --rec-file /path/to/g4-rec.h5 \
  --tru-file /path/to/g4-tru.h5 \
  --output /path/to/output.h5 \
  --rebin-time 2 \
  --rebin-channel 2
```

## Output Structure

The rebinned HDF5 file contains datasets named like:
```
anode{i}_plane{j}_{frame_type}
anode{i}_plane{j}_{frame_type}_1st
anode{i}_plane{j}_{frame_type}_2nd
```

Where:
- `i` = anode ID (0-7), each anode is a CRU
- `j` = plane ID (0-2), representing U/V/W wire planes
- `{frame_type}` = one of: `gauss`, `orig_trackid`, `orig_pid`, `current_pid`, `charge`

### Example Output Datasets
```
anode0_plane0_gauss       (Anode 0, U plane - gauss frame)
anode0_plane1_gauss       (Anode 0, V plane - gauss frame)
anode0_plane2_gauss       (Anode 0, W plane - gauss frame)
anode0_plane0_orig_trackid_1st
anode0_plane0_orig_trackid_2nd
anode1_plane0_gauss       (Anode 1, U plane)
... (for all 8 anodes × 3 planes)
```

Total: 8 anodes × 3 planes × 9 frame types = 216 datasets per rebinned file
(9 frame types: gauss + 4 × 2 extended labels)

## Channel Grouping (ProtoDUNE-VD)

The script uses the ProtoDUNE-VD channel grouping:

### Anode Structure
- **8 anodes** total (IDs 0-7), **each anode IS a CRU** (Charge Readout Unit)
- Anode mapping:
  - Anode 0: CRP 0, CRU0
  - Anode 1: CRP 0, CRU1
  - Anode 2: CRP 1, CRU0
  - Anode 3: CRP 1, CRU1
  - Anode 4: CRP 2, CRU0
  - Anode 5: CRP 2, CRU1
  - Anode 6: CRP 3, CRU0
  - Anode 7: CRP 3, CRU1

### CRU Details
Each CRU has unique channel ranges per wire plane:
- **CRU0** (even anodes: 0, 2, 4, 6):
  - U plane: channels 0-476
  - V plane: channels 952-1428
  - W plane: channels 1904-2488
- **CRU1** (odd anodes: 1, 3, 5, 7):
  - U plane: channels 476-951
  - V plane: channels 1428-1903
  - W plane: channels 2488-3071

### Plane Structure
Each anode (CRU) has 3 planes: U, V, W wire planes.

**For even anodes (0, 2, 4, 6) - CRU0:**
- **Plane 0 (U)**: channels 0-476
- **Plane 1 (V)**: channels 952-1428
- **Plane 2 (W)**: channels 1904-2488

**For odd anodes (1, 3, 5, 7) - CRU1:**
- **Plane 0 (U)**: channels 476-951
- **Plane 1 (V)**: channels 1428-1903
- **Plane 2 (W)**: channels 2488-3071

All channels are offset by `3072 * crp` to map to the correct CRP, where `crp = anode_id // 2`.

## Important Notes

1. **Dimension Requirements**: All frames must have the same (n_channels, n_ticks) dimensions
2. **Rebin Factors**: Should divide evenly into the original dimensions for best results
3. **Memory**: The script loads entire frames into memory. For very large files, consider processing per-anode separately
4. **Data Types**: Integer frames (trackid, pid) are preserved; float frames (charge) use sum rebinning

## Example Complete Workflow

```bash
# Run the core labeling code (generates g4-rec.h5 and g4-tru.h5)
wire-cell -c wcls-labelling2d.jsonnet

# Rebin with 2x2 factors
python3 rebin_frames.py \
  --rebin-time 2 \
  --rebin-channel 2 \
  --output g4-rebinned-2x2.h5

# Rebin with 4x4 factors
python3 rebin_frames.py \
  --rebin-time 4 \
  --rebin-channel 4 \
  --output g4-rebinned-4x4.h5
```

## Troubleshooting

### Error: "Dimension mismatch"
- Check that all frames in both files have the same shape
- Verify the frame data was generated correctly

### Error: "File not found"
- Ensure g4-rec.h5 and g4-tru.h5 exist in the current directory or specify correct paths

### Memory issues
- Reduce the number of frames to process at once
- Process per-anode separately
- Use a machine with more RAM

## Dependencies

```bash
pip install h5py numpy
```

Both are standard data science libraries available in most Python installations.
