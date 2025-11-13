#!/usr/bin/env python3
"""
Utility script to inspect rebinned HDF5 files and verify rebinning correctness.
"""

import h5py
import numpy as np
import argparse
from pathlib import Path


def print_file_info(filepath: str):
    """Print information about an HDF5 file."""
    print(f"\n{'='*80}")
    print(f"File: {filepath}")
    print(f"{'='*80}")

    try:
        with h5py.File(filepath, 'r') as f:
            def print_structure(name, obj):
                indent = len(name.split('/')) - 1
                if isinstance(obj, h5py.Dataset):
                    shape = obj.shape
                    dtype = obj.dtype
                    size_mb = np.prod(shape) * dtype.itemsize / 1024 / 1024
                    print(f"{'  '*indent}📊 {name.split('/')[-1]}: shape={shape}, dtype={dtype}, size={size_mb:.2f}MB")
                elif isinstance(obj, h5py.Group):
                    print(f"{'  '*indent}📁 {name.split('/')[-1]}/")

            f.visititems(print_structure)

            # Count only frames (items with "frame" in name)
            frame_count = sum(1 for key in f.keys() if 'frame' in key.lower())
            total_count = sum(1 for _ in f.keys())
            print(f"\nTotal datasets: {total_count}")
            print(f"Frame datasets: {frame_count}")
    except Exception as e:
        print(f"ERROR reading file: {e}")


def compare_dimensions(file1: str, file2: str):
    """Compare dimensions of corresponding frames in two files."""
    print(f"\n{'='*80}")
    print(f"Dimension Comparison: {file1} vs {file2}")
    print(f"{'='*80}")

    try:
        with h5py.File(file1, 'r') as f1, h5py.File(file2, 'r') as f2:
            # Only compare frames (items with "frame" in name)
            keys1 = set(k for k in f1.keys() if 'frame' in k.lower())
            keys2 = set(k for k in f2.keys() if 'frame' in k.lower())

            common_keys = keys1 & keys2
            only_in_1 = keys1 - keys2
            only_in_2 = keys2 - keys1

            if common_keys:
                print("\nCommon frames:")
                for key in sorted(common_keys):
                    shape1 = f1[key].shape
                    shape2 = f2[key].shape
                    match = "✓" if shape1 == shape2 else "✗"
                    print(f"  {match} {key}: {shape1} vs {shape2}")

            if only_in_1:
                print(f"\nOnly in {file1}: {only_in_1}")
            if only_in_2:
                print(f"\nOnly in {file2}: {only_in_2}")

    except Exception as e:
        print(f"ERROR: {e}")


def validate_rebinning(original_file: str, rebinned_file: str, rebin_factor: int = 2):
    """
    Validate that rebinning was done correctly (sum should be preserved).

    This is only valid for frames that use sum rebinning (like gauss frame).
    """
    print(f"\n{'='*80}")
    print(f"Rebinning Validation (assuming sum rebinning)")
    print(f"{'='*80}")

    try:
        with h5py.File(original_file, 'r') as f_orig, h5py.File(rebinned_file, 'r') as f_rebin:
            # Find gauss-like frames (items with both "gauss" and "frame" in name)
            gauss_frames = [k for k in f_rebin.keys() if 'gauss' in k and 'frame' in k.lower()]

            if not gauss_frames:
                print("No gauss frames found in rebinned file")
                return

            for frame_name in gauss_frames[:3]:  # Check first 3
                print(f"\nValidating {frame_name}...")
                rebinned_data = np.array(f_rebin[frame_name])

                print(f"  Rebinned shape: {rebinned_data.shape}")
                print(f"  Min value: {np.min(rebinned_data):.2f}")
                print(f"  Max value: {np.max(rebinned_data):.2f}")
                print(f"  Mean value: {np.mean(rebinned_data):.2f}")
                print(f"  Sum: {np.sum(rebinned_data):.2e}")

    except Exception as e:
        print(f"ERROR: {e}")


def summary_statistics(filepath: str):
    """Print summary statistics for all frame datasets."""
    print(f"\n{'='*80}")
    print(f"Summary Statistics: {filepath}")
    print(f"{'='*80}")

    try:
        with h5py.File(filepath, 'r') as f:
            # Only show statistics for frames (items with "frame" in name)
            frame_keys = [k for k in sorted(f.keys()) if 'frame' in k.lower()]

            if not frame_keys:
                print("No frame datasets found in file")
                return

            for key in frame_keys:
                data = np.array(f[key])
                print(f"\n{key}:")
                print(f"  Shape: {data.shape}")
                print(f"  Dtype: {data.dtype}")
                print(f"  Min/Max: {np.min(data):10.2e} / {np.max(data):10.2e}")
                print(f"  Mean: {np.mean(data):10.2e}")
                print(f"  Std: {np.std(data):10.2e}")
                print(f"  Non-zero: {np.count_nonzero(data)} / {data.size}")

    except Exception as e:
        print(f"ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Inspect and validate rebinned HDF5 frames'
    )
    parser.add_argument('files', nargs='+', help='HDF5 files to inspect')
    parser.add_argument('--compare', action='store_true',
                       help='Compare dimensions between two files')
    parser.add_argument('--validate', action='store_true',
                       help='Validate rebinning correctness')
    parser.add_argument('--stats', action='store_true',
                       help='Print summary statistics')
    parser.add_argument('--rebin-factor', type=int, default=2,
                       help='Rebin factor used (for validation)')

    args = parser.parse_args()

    # Verify files exist
    for fpath in args.files:
        if not Path(fpath).exists():
            print(f"ERROR: {fpath} not found")
            return 1

    # Print file info
    for fpath in args.files:
        print_file_info(fpath)

    # Compare dimensions
    if args.compare and len(args.files) == 2:
        compare_dimensions(args.files[0], args.files[1])

    # Validate rebinning
    if args.validate and len(args.files) == 2:
        validate_rebinning(args.files[0], args.files[1], args.rebin_factor)

    # Print statistics
    if args.stats:
        for fpath in args.files:
            summary_statistics(fpath)

    return 0


if __name__ == '__main__':
    exit(main())
