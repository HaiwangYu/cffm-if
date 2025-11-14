#!/usr/bin/env python3
"""
Script to plot 1D time projections of rebinned frames for specific channels.

Creates visualizations showing 1st and 2nd contributions with gauss frame as reference.
"""

import h5py
import numpy as np
import argparse
from pathlib import Path
from typing import Tuple, Dict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


class RebinnedChannelPlotter:
    """Plot 1D projections of rebinned frame data for specific channels."""

    def __init__(self, rebinned_file: str):
        """
        Initialize plotter with rebinned HDF5 file.

        Args:
            rebinned_file: Path to g4-rebinned.h5 file
        """
        self.rebinned_file = rebinned_file
        self.h5f = None

    def __enter__(self):
        self.h5f = h5py.File(self.rebinned_file, 'r')
        return self

    def __exit__(self, *args):
        if self.h5f:
            self.h5f.close()

    def inspect_file(self):
        """Inspect and print available datasets in the HDF5 file."""
        print(f"\n{'='*80}")
        print(f"Inspecting HDF5 File: {self.rebinned_file}")
        print(f"{'='*80}")

        # List all keys at root level
        all_keys = list(self.h5f.keys())
        print(f"\nTotal datasets in file: {len(all_keys)}")

        # Find frame datasets
        frame_keys = [k for k in all_keys if 'frame' in k.lower() or 'anode' in k.lower()]
        print(f"Frame-related datasets: {len(frame_keys)}")

        if frame_keys:
            print("\nSample datasets:")
            for key in frame_keys[:10]:
                item = self.h5f[key]
                if isinstance(item, h5py.Dataset):
                    print(f"  {key}: shape {item.shape}, dtype {item.dtype}")

            if len(frame_keys) > 10:
                print(f"  ... and {len(frame_keys) - 10} more")

        # Check for groups
        group_keys = [k for k in all_keys if isinstance(self.h5f[k], h5py.Group)]
        if group_keys:
            print(f"\nGroups found: {group_keys}")
            for gkey in group_keys[:3]:
                print(f"  {gkey}/: {len(self.h5f[gkey].keys())} items")

    @staticmethod
    def determine_anode_plane(channel: int) -> Tuple[int, int, int]:
        """
        Determine which anode and plane a channel belongs to.

        Returns:
            (anode_id, plane_id, channel_index_in_plane)
        """
        # Determine CRP from channel
        crp = channel // 3072

        # Determine CRU from remaining channels
        ch_in_crp = channel % 3072
        if ch_in_crp < 476:  # CRU0 U plane
            cru = 0
            plane_in_cru = 0
            ch_idx = ch_in_crp
        elif ch_in_crp < 952:  # CRU1 U plane
            cru = 1
            plane_in_cru = 0
            ch_idx = ch_in_crp - 476
        elif ch_in_crp < 1428:  # CRU0 V plane
            cru = 0
            plane_in_cru = 1
            ch_idx = ch_in_crp - 952
        elif ch_in_crp < 1904:  # CRU1 V plane
            cru = 1
            plane_in_cru = 1
            ch_idx = ch_in_crp - 1428
        elif ch_in_crp < 2488:  # CRU0 W plane
            cru = 0
            plane_in_cru = 2
            ch_idx = ch_in_crp - 1904
        else:  # CRU1 W plane
            cru = 1
            plane_in_cru = 2
            ch_idx = ch_in_crp - 2488

        anode_id = crp * 2 + cru
        plane_id = plane_in_cru

        return anode_id, plane_id, ch_idx

    def get_channel_data(self, channel: int) -> Tuple[Dict[str, np.ndarray], int, int, int]:
        """
        Load all frame data for a specific channel.

        Args:
            channel: Channel number

        Returns:
            (data_dict, anode_id, plane_id, ch_idx) where data_dict maps frame name to 1D array
        """
        anode_id, plane_id, ch_idx = self.determine_anode_plane(channel)

        data = {}

        # Frame types to load
        frame_types = [
            'gauss',
            'orig_trackid_1st', 'orig_pid_1st', 'current_pid_1st', 'charge_1st',
            'orig_trackid_2nd', 'orig_pid_2nd', 'current_pid_2nd', 'charge_2nd'
        ]

        for frame_type in frame_types:
            # Try multiple naming conventions
            possible_keys = [
                f"frame_anode{anode_id}_plane{plane_id}_{frame_type}",
                f"anode{anode_id}_plane{plane_id}_{frame_type}",
            ]

            found = False
            for key in possible_keys:
                if key in self.h5f:
                    frame_data = np.array(self.h5f[key])
                    # Extract 1D projection for this channel (ch_idx is the row index)
                    if ch_idx < frame_data.shape[0]:
                        data[frame_type] = frame_data[ch_idx, :]
                        found = True
                        break
                    else:
                        print(f"WARNING: Channel index {ch_idx} out of bounds for {key} (shape {frame_data.shape})")
                        found = True
                        break

        return data, anode_id, plane_id, ch_idx

    @staticmethod
    def normalize_data(data: np.ndarray) -> np.ndarray:
        """
        Normalize data to [0, 1] range using min-max scaling.

        Handles zero data gracefully.
        """
        data_min = np.min(data)
        data_max = np.max(data)

        if data_max <= data_min:
            return np.zeros_like(data, dtype=float)

        return (data - data_min) / (data_max - data_min)

    def plot_channel(self, channel: int, output_prefix: str = ""):
        """
        Create 1D time projection plots for a channel.

        Creates two subplots: 1st contributions and 2nd contributions.

        Args:
            channel: Channel number to plot
            output_prefix: Prefix for output filename
        """
        data_dict, anode_id, plane_id, ch_idx = self.get_channel_data(channel)

        if not data_dict:
            print(f"No data found for channel {channel}")
            return

        # Define colors for each frame type
        colors = {
            'gauss': 'black',
            'orig_trackid_1st': 'red',
            'orig_pid_1st': 'green',
            'current_pid_1st': 'blue',
            'charge_1st': 'orange',
            'orig_trackid_2nd': 'darkred',
            'orig_pid_2nd': 'darkgreen',
            'current_pid_2nd': 'darkblue',
            'charge_2nd': 'darkorange',
        }

        # Create figure with 2 subplots
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        fig.suptitle(f'Channel {channel} (Anode {anode_id}, Plane {plane_id}, Ch {ch_idx})\n1D Time Projections',
                     fontsize=14, fontweight='bold')

        # Plot 1st contributions (with gauss reference)
        ax1 = axes[0]
        ax1.set_title('1st Contributions + Gauss Reference', fontsize=12, fontweight='bold')

        # Gauss frame as reference (black, slightly thicker)
        if 'gauss' in data_dict:
            gauss_norm = self.normalize_data(data_dict['gauss'])
            ax1.plot(gauss_norm, color=colors['gauss'], linewidth=2, label='gauss', zorder=10)

        # 1st contribution frames (normalized separately)
        first_frames = ['orig_trackid_1st', 'orig_pid_1st', 'current_pid_1st', 'charge_1st']
        for frame_name in first_frames:
            if frame_name in data_dict:
                data_norm = self.normalize_data(data_dict[frame_name])
                ax1.plot(data_norm, color=colors[frame_name], linewidth=1.5, label=frame_name, alpha=0.8)

        ax1.set_xlabel('Time Tick', fontsize=10)
        ax1.set_ylabel('Normalized Value', fontsize=10)
        ax1.legend(loc='best', fontsize=9)
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim([-0.05, 1.05])

        # Plot 2nd contributions (with gauss reference)
        ax2 = axes[1]
        ax2.set_title('2nd Contributions + Gauss Reference', fontsize=12, fontweight='bold')

        # Gauss frame as reference
        if 'gauss' in data_dict:
            gauss_norm = self.normalize_data(data_dict['gauss'])
            ax2.plot(gauss_norm, color=colors['gauss'], linewidth=2, label='gauss', zorder=10)

        # 2nd contribution frames (normalized separately)
        second_frames = ['orig_trackid_2nd', 'orig_pid_2nd', 'current_pid_2nd', 'charge_2nd']
        for frame_name in second_frames:
            if frame_name in data_dict:
                data_norm = self.normalize_data(data_dict[frame_name])
                ax2.plot(data_norm, color=colors[frame_name], linewidth=1.5, label=frame_name, alpha=0.8)

        ax2.set_xlabel('Time Tick', fontsize=10)
        ax2.set_ylabel('Normalized Value', fontsize=10)
        ax2.legend(loc='best', fontsize=9)
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim([-0.05, 1.05])

        plt.tight_layout()

        # Save figure
        if output_prefix:
            filename = f"{output_prefix}_channel{channel}.png"
        else:
            filename = f"rebinned_channel{channel}.png"

        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"Saved: {filename}")
        plt.close()

    def plot_channels(self, channels: list, output_prefix: str = ""):
        """
        Plot multiple channels.

        Args:
            channels: List of channel numbers
            output_prefix: Prefix for output filenames
        """
        for channel in channels:
            try:
                self.plot_channel(channel, output_prefix)
            except Exception as e:
                print(f"Error plotting channel {channel}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Plot 1D time projections of rebinned frames for specific channels'
    )
    parser.add_argument('--rebinned-file', default='g4-rebinned.h5',
                       help='Path to rebinned HDF5 file')
    parser.add_argument('--channels', nargs='+', type=int,
                       help='Channel numbers to plot')
    parser.add_argument('--output-prefix', default='',
                       help='Prefix for output filenames')
    parser.add_argument('--inspect', action='store_true',
                       help='Inspect HDF5 file structure and exit')

    args = parser.parse_args()

    # Verify file exists
    if not Path(args.rebinned_file).exists():
        print(f"ERROR: {args.rebinned_file} not found")
        return 1

    print(f"Loading rebinned file: {args.rebinned_file}")

    with RebinnedChannelPlotter(args.rebinned_file) as plotter:
        if args.inspect:
            plotter.inspect_file()
            return 0

        if not args.channels:
            print("ERROR: --channels required when not using --inspect")
            return 1

        print(f"Channels to plot: {args.channels}")
        plotter.plot_channels(args.channels, args.output_prefix)

    return 0


if __name__ == '__main__':
    exit(main())
