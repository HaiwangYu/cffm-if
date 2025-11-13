#!/usr/bin/env python3
"""
Script to rebin frames from g4-rec.h5 and g4-tru.h5 files.

For g4-rec.h5:
  - frame_gauss: sum of values during rebinning

For g4-tru.h5:
  - For each rebinned bin, track the 1st and 2nd contributions
  - 1st contribution: the one with biggest charge
  - 2nd contribution: the one with 2nd biggest charge
"""

import h5py
import numpy as np
import argparse
from pathlib import Path
from typing import Dict, List, Tuple


class AnodesChannelGrouping:
    """Handle channel grouping for 8 anodes (ProtoDUNE-VD style)."""

    @staticmethod
    def get_anode_channels(n: int) -> np.ndarray:
        """
        Get channels for anode n (0-7).
        Based on the provided channel grouping formula.
        """
        crp = (n - n % 2) // 2
        cru0 = np.concatenate([
            np.arange(0, 476),
            np.arange(952, 1428),
            np.arange(1904, 2488)
        ])
        cru1 = np.concatenate([
            np.arange(476, 952),
            np.arange(1428, 1904),
            np.arange(2488, 3072)
        ])

        if n % 2 == 0:
            channels = cru0
        else:
            channels = cru1

        return channels + 3072 * crp

    @staticmethod
    def get_all_anodes_channels() -> Dict[int, np.ndarray]:
        """Get channel grouping for all 8 anodes."""
        return {n: AnodesChannelGrouping.get_anode_channels(n) for n in range(8)}

    @staticmethod
    def get_anode_planes(anode_id: int) -> Dict[int, np.ndarray]:
        """
        Each anode IS a CRU. Return the 3 planes (U, V, W) for this CRU.

        Anode mapping:
        - Anode 0,1 belong to CRP 0 (Anode 0=CRU0, Anode 1=CRU1)
        - Anode 2,3 belong to CRP 1 (Anode 2=CRU0, Anode 3=CRU1)
        - Anode 4,5 belong to CRP 2 (Anode 4=CRU0, Anode 5=CRU1)
        - Anode 6,7 belong to CRP 3 (Anode 6=CRU0, Anode 7=CRU1)

        Channel ranges per CRU:
        - CRU0: U (0-476), V (952-1428), W (1904-2488)
        - CRU1: U (476-951), V (1428-1903), W (2488-3071)
        """
        crp = anode_id // 2
        cru_idx = anode_id % 2
        base_offset = 3072 * crp

        if cru_idx == 0:
            # CRU0 planes
            u = np.arange(0, 476) + base_offset
            v = np.arange(952, 1428) + base_offset
            w = np.arange(1904, 2488) + base_offset
        else:  # cru_idx == 1
            # CRU1 planes
            u = np.arange(476, 951) + base_offset
            v = np.arange(1428, 1903) + base_offset
            w = np.arange(2488, 3071) + base_offset

        return {
            0: np.sort(u),
            1: np.sort(v),
            2: np.sort(w)
        }


class FrameRebinner:
    """Handle rebinning of frame data."""

    def __init__(self, rebin_time: int = 2, rebin_channel: int = 2):
        """
        Initialize rebinner with rebin factors.

        Args:
            rebin_time: Rebin factor in time dimension
            rebin_channel: Rebin factor in channel dimension
        """
        self.rebin_time = rebin_time
        self.rebin_channel = rebin_channel

    @staticmethod
    def rebin_sum(data: np.ndarray, rebin_time: int, rebin_channel: int) -> np.ndarray:
        """
        Rebin data by summing values.

        Args:
            data: (n_channels, n_ticks) array
            rebin_time: rebin factor in time
            rebin_channel: rebin factor in channel

        Returns:
            Rebinned array
        """
        n_ch, n_ticks = data.shape

        # Rebin channels
        n_ch_new = n_ch // rebin_channel
        n_ticks_new = n_ticks // rebin_time

        # Reshape and sum
        data_ch = data[:n_ch_new*rebin_channel, :].reshape(n_ch_new, rebin_channel, n_ticks)
        data_ch = np.sum(data_ch, axis=1)

        # Rebin time
        data_rebin = data_ch[:, :n_ticks_new*rebin_time].reshape(n_ch_new, n_ticks_new, rebin_time)
        data_rebin = np.sum(data_rebin, axis=2)

        return data_rebin

    @staticmethod
    def rebin_track_first_second(
        data_1st: np.ndarray,
        data_2nd: np.ndarray,
        charge_1st: np.ndarray,
        charge_2nd: np.ndarray,
        rebin_time: int,
        rebin_channel: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Rebin track data by keeping track of 1st and 2nd contributions.
        For each rebinned bin, select the 1st and 2nd based on biggest charge.

        Args:
            data_1st: (n_channels, n_ticks) array of 1st contribution
            data_2nd: (n_channels, n_ticks) array of 2nd contribution
            charge_1st: (n_channels, n_ticks) array of charges for 1st
            charge_2nd: (n_channels, n_ticks) array of charges for 2nd
            rebin_time: rebin factor in time
            rebin_channel: rebin factor in channel

        Returns:
            (rebinned_data_1st, rebinned_data_2nd) where each is (n_ch_new, n_ticks_new)
        """
        n_ch, n_ticks = data_1st.shape
        n_ch_new = n_ch // rebin_channel
        n_ticks_new = n_ticks // rebin_time

        # Initialize output arrays
        out_1st = np.zeros((n_ch_new, n_ticks_new), dtype=data_1st.dtype)
        out_2nd = np.zeros((n_ch_new, n_ticks_new), dtype=data_2nd.dtype)

        # Rebin
        for i_ch in range(n_ch_new):
            ch_start = i_ch * rebin_channel
            ch_end = min(ch_start + rebin_channel, n_ch)

            for i_tick in range(n_ticks_new):
                tick_start = i_tick * rebin_time
                tick_end = min(tick_start + rebin_time, n_ticks)

                # Collect all 1st and 2nd contributions in this bin
                contributions = []

                for ch in range(ch_start, ch_end):
                    for tick in range(tick_start, tick_end):
                        if charge_1st[ch, tick] > 0:
                            contributions.append((charge_1st[ch, tick], data_1st[ch, tick]))
                        if charge_2nd[ch, tick] > 0:
                            contributions.append((charge_2nd[ch, tick], data_2nd[ch, tick]))

                if len(contributions) > 0:
                    # Sort by charge descending
                    contributions.sort(key=lambda x: x[0], reverse=True)
                    out_1st[i_ch, i_tick] = contributions[0][1]
                    if len(contributions) > 1:
                        out_2nd[i_ch, i_tick] = contributions[1][1]

        return out_1st, out_2nd


class HDF5FrameProcessor:
    """Handle loading, processing, and saving HDF5 frame files."""

    def __init__(self, rec_file: str, tru_file: str, rebin_time: int, rebin_channel: int):
        """
        Initialize processor.

        Args:
            rec_file: Path to g4-rec.h5
            tru_file: Path to g4-tru.h5
            rebin_time: Rebin factor in time
            rebin_channel: Rebin factor in channel
        """
        self.rec_file = rec_file
        self.tru_file = tru_file
        self.rebin_time = rebin_time
        self.rebin_channel = rebin_channel
        self.rebinner = FrameRebinner(rebin_time, rebin_channel)

    @staticmethod
    def load_frame(h5file: h5py.File, frame_name: str) -> np.ndarray:
        """Load a frame from HDF5 file."""
        return np.array(h5file[f'/1/{frame_name}'])

    @staticmethod
    def verify_dimensions(frames: Dict[str, np.ndarray]) -> bool:
        """Verify all frames have the same dimensions."""
        if not frames:
            return True

        first_shape = None
        for name, data in frames.items():
            if first_shape is None:
                first_shape = data.shape
            elif data.shape != first_shape:
                print(f"ERROR: {name} has shape {data.shape}, expected {first_shape}")
                return False

        return True

    def process(self, output_file: str):
        """
        Process and rebin the frame files.

        Args:
            output_file: Path to save rebinned data
        """
        print(f"Loading frames from {self.rec_file} and {self.tru_file}...")

        # Load all frames (only items with "frame" in the name)
        frames_rec = {}
        frames_tru = {}

        with h5py.File(self.rec_file, 'r') as f:
            if '/1' in f:
                for key in f['/1'].keys():
                    # Only load frames (skip other items with different dimensions)
                    if 'frame' in key.lower():
                        # Strip "frame_" prefix for easier processing
                        clean_key = key.replace('frame_', '', 1) if key.startswith('frame_') else key
                        frames_rec[clean_key] = self.load_frame(f, key)
                        if clean_key != key:
                            print(f"  Loaded: {key} -> {clean_key}")

        with h5py.File(self.tru_file, 'r') as f:
            if '/1' in f:
                for key in f['/1'].keys():
                    # Only load frames (skip other items with different dimensions)
                    if 'frame' in key.lower():
                        # Strip "frame_" prefix for easier processing
                        clean_key = key.replace('frame_', '', 1) if key.startswith('frame_') else key
                        frames_tru[clean_key] = self.load_frame(f, key)
                        if clean_key != key:
                            print(f"  Loaded: {key} -> {clean_key}")

        print(f"Loaded {len(frames_rec)} frames from g4-rec.h5: {list(frames_rec.keys())}")
        print(f"Loaded {len(frames_tru)} frames from g4-tru.h5: {list(frames_tru.keys())}")

        # Verify dimensions
        all_frames = {**frames_rec, **frames_tru}
        if not self.verify_dimensions(all_frames):
            print("ERROR: Dimension mismatch!")
            return False

        n_channels, n_ticks = list(all_frames.values())[0].shape
        print(f"Frame dimensions: {n_channels} channels x {n_ticks} ticks")

        # Get anode/plane grouping
        anode_grouping = AnodesChannelGrouping.get_all_anodes_channels()

        print(f"\nRebinning with factors: time={self.rebin_time}, channel={self.rebin_channel}")

        # Rebin per anode per plane
        rebinned_data = {}

        for anode_id in range(8):
            planes = AnodesChannelGrouping.get_anode_planes(anode_id)
            cru_id = anode_id // 2
            cru_idx = anode_id % 2

            for plane_id in range(3):
                plane_channels = planes[plane_id]
                # Map plane IDs to wire plane types (U, V, W)
                plane_type = ['U', 'V', 'W'][plane_id]
                print(f"\nProcessing Anode {anode_id} (CRP{cru_id}_CRU{cru_idx}), Plane {plane_id} ({plane_type}: {len(plane_channels)} channels)")

                # Extract data for this plane
                plane_key = f"anode{anode_id}_plane{plane_id}"

                # For g4-rec.h5
                if 'frame_gauss' in frames_rec:
                    data = frames_rec['frame_gauss'][plane_channels, :]
                    rebinned = self.rebinner.rebin_sum(data, self.rebin_time, self.rebin_channel)
                    rebinned_data[f"{plane_key}_gauss"] = rebinned

                # For g4-tru.h5 - process each type of data
                processed_frames = set()

                # Handle orig_trackid
                if 'orig_trackid_1st' in frames_tru:
                    charge_1st = frames_tru['charge_1st'][plane_channels, :]
                    charge_2nd = frames_tru['charge_2nd'][plane_channels, :]
                    data_1st = frames_tru['orig_trackid_1st'][plane_channels, :]
                    data_2nd = frames_tru['orig_trackid_2nd'][plane_channels, :]
                    out_1st, out_2nd = self.rebinner.rebin_track_first_second(
                        data_1st, data_2nd, charge_1st, charge_2nd,
                        self.rebin_time, self.rebin_channel
                    )
                    rebinned_data[f"{plane_key}_orig_trackid_1st"] = out_1st
                    rebinned_data[f"{plane_key}_orig_trackid_2nd"] = out_2nd
                    processed_frames.add('orig_trackid_1st')
                    processed_frames.add('orig_trackid_2nd')

                # Handle orig_pid
                if 'orig_pid_1st' in frames_tru:
                    charge_1st = frames_tru['charge_1st'][plane_channels, :]
                    charge_2nd = frames_tru['charge_2nd'][plane_channels, :]
                    data_1st = frames_tru['orig_pid_1st'][plane_channels, :]
                    data_2nd = frames_tru['orig_pid_2nd'][plane_channels, :]
                    out_1st, out_2nd = self.rebinner.rebin_track_first_second(
                        data_1st, data_2nd, charge_1st, charge_2nd,
                        self.rebin_time, self.rebin_channel
                    )
                    rebinned_data[f"{plane_key}_orig_pid_1st"] = out_1st
                    rebinned_data[f"{plane_key}_orig_pid_2nd"] = out_2nd
                    processed_frames.add('orig_pid_1st')
                    processed_frames.add('orig_pid_2nd')

                # Handle current_pid
                if 'current_pid_1st' in frames_tru:
                    charge_1st = frames_tru['charge_1st'][plane_channels, :]
                    charge_2nd = frames_tru['charge_2nd'][plane_channels, :]
                    data_1st = frames_tru['current_pid_1st'][plane_channels, :]
                    data_2nd = frames_tru['current_pid_2nd'][plane_channels, :]
                    out_1st, out_2nd = self.rebinner.rebin_track_first_second(
                        data_1st, data_2nd, charge_1st, charge_2nd,
                        self.rebin_time, self.rebin_channel
                    )
                    rebinned_data[f"{plane_key}_current_pid_1st"] = out_1st
                    rebinned_data[f"{plane_key}_current_pid_2nd"] = out_2nd
                    processed_frames.add('current_pid_1st')
                    processed_frames.add('current_pid_2nd')

                # Handle charge
                if 'charge_1st' in frames_tru:
                    charge_1st = frames_tru['charge_1st'][plane_channels, :]
                    charge_2nd = frames_tru['charge_2nd'][plane_channels, :]
                    rebinned_1st = self.rebinner.rebin_sum(charge_1st, self.rebin_time, self.rebin_channel)
                    rebinned_2nd = self.rebinner.rebin_sum(charge_2nd, self.rebin_time, self.rebin_channel)
                    rebinned_data[f"{plane_key}_charge_1st"] = rebinned_1st
                    rebinned_data[f"{plane_key}_charge_2nd"] = rebinned_2nd
                    processed_frames.add('charge_1st')
                    processed_frames.add('charge_2nd')

        # Save rebinned data
        print(f"\nSaving rebinned data to {output_file}...")
        with h5py.File(output_file, 'w') as f:
            for key, data in rebinned_data.items():
                # Add "frame_" prefix to output dataset names
                output_key = f"frame_{key}" if not key.startswith('frame_') else key
                f.create_dataset(output_key, data=data, compression='gzip', compression_opts=2)

        print(f"Saved {len(rebinned_data)} rebinned frames")
        print(f"Output datasets: {sorted([f'frame_{k}' if not k.startswith('frame_') else k for k in rebinned_data.keys()])}")
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Rebin frames from g4-rec.h5 and g4-tru.h5 files'
    )
    parser.add_argument('--rec-file', default='g4-rec.h5',
                       help='Path to g4-rec.h5')
    parser.add_argument('--tru-file', default='g4-tru.h5',
                       help='Path to g4-tru.h5')
    parser.add_argument('--rebin-time', type=int, default=2,
                       help='Rebin factor for time dimension')
    parser.add_argument('--rebin-channel', type=int, default=2,
                       help='Rebin factor for channel dimension')
    parser.add_argument('--output', default='g4-rebinned.h5',
                       help='Output file for rebinned data')

    args = parser.parse_args()

    # Verify input files exist
    for fpath in [args.rec_file, args.tru_file]:
        if not Path(fpath).exists():
            print(f"ERROR: {fpath} not found")
            return 1

    processor = HDF5FrameProcessor(
        args.rec_file, args.tru_file,
        args.rebin_time, args.rebin_channel
    )

    success = processor.process(args.output)
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
