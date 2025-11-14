#!/usr/bin/env python3
"""Quick inspection of HDF5 file contents."""

import h5py
import sys

if len(sys.argv) < 2:
    print("Usage: python3 quick_inspect.py <h5_file>")
    sys.exit(1)

h5file = sys.argv[1]

print(f"Inspecting: {h5file}\n")

with h5py.File(h5file, 'r') as f:
    print("Root level keys:")
    for key in list(f.keys())[:20]:  # Show first 20
        item = f[key]
        if isinstance(item, h5py.Dataset):
            print(f"  Dataset: {key} - shape {item.shape}, dtype {item.dtype}")
        elif isinstance(item, h5py.Group):
            print(f"  Group: {key}/")
            for subkey in list(item.keys())[:5]:  # Show first 5 items in group
                subitem = item[subkey]
                if isinstance(subitem, h5py.Dataset):
                    print(f"    Dataset: {subkey} - shape {subitem.shape}")

    total_keys = len(f.keys())
    if total_keys > 20:
        print(f"\n  ... and {total_keys - 20} more items")

    # Look for frame-related datasets
    print("\nFrame datasets found:")
    frame_keys = [k for k in f.keys() if 'frame' in k.lower()]
    for key in frame_keys[:10]:
        item = f[key]
        print(f"  {key}: shape {item.shape}")

    if len(frame_keys) > 10:
        print(f"  ... and {len(frame_keys) - 10} more")

    print(f"\nTotal frame datasets: {len(frame_keys)}")
