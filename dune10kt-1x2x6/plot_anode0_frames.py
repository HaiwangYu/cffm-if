#!/usr/bin/env python3
"""
Script to plot all frame*pid* and frame*trackid* frames from HDF5 file.

Supports both g4-rebinned.h5 (original labels) and g4-tru.h5 (new rebinned labels).
Recursively searches nested HDF5 groups for frame datasets.

Frame types:
  - trackid, trackid_1st, trackid_2nd: Track IDs (1st/2nd by charge in rebinned bins)
  - pid, pid_1st, pid_2nd: Particle IDs (1st/2nd by charge in rebinned bins)

Creates 2D heatmaps for each frame, saved to multi-page PDF.
Region: channels [0, max/2], time [0.8*max, max]
"""

import h5py
import numpy as np
import argparse
from pathlib import Path
from typing import List, Tuple
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm


class LabelFramePlotter:
    """Plot all label frames (PID and TrackID) from HDF5 file (g4-rebinned.h5 or g4-tru.h5)."""

    def __init__(self, input_file: str, verbose: bool = False):
        """
        Initialize plotter with HDF5 file.

        Args:
            input_file: Path to HDF5 file (g4-rebinned.h5 or g4-tru.h5)
            verbose: If True, print detailed info about loaded frames
        """
        self.input_file = input_file
        self.h5f = None
        self.verbose = verbose

    def __enter__(self):
        self.h5f = h5py.File(self.input_file, 'r')
        return self

    def __exit__(self, *args):
        if self.h5f:
            self.h5f.close()

    def get_label_frames(self) -> List[Tuple[str, np.ndarray]]:
        """
        Load all frame*pid* and frame*trackid* datasets from file.

        Returns:
            List of (frame_name, data_array) tuples
        """
        frames = []

        # Recursively find all datasets containing 'frame' in their path
        def find_frame_datasets(group, path=""):
            """Recursively search for datasets containing 'frame' in name"""
            label_keys = {}
            for key in group.keys():
                current_path = f"{path}/{key}" if path else key
                item = group[key]

                if isinstance(item, h5py.Dataset):
                    # This is a dataset, check if it contains 'frame'
                    if 'frame' in key.lower():
                        label_keys[current_path] = item
                elif isinstance(item, h5py.Group):
                    # This is a group, recurse into it
                    label_keys.update(find_frame_datasets(item, current_path))

            return label_keys

        label_keys = find_frame_datasets(self.h5f)

        if not label_keys:
            print("WARNING: No frame datasets found in file")
            return frames

        print(f"Found {len(label_keys)} label frame datasets:")

        # Categorize frames for better organization
        trackid_frames = []
        pid_frames = []

        for key_path in sorted(label_keys.keys()):
            data = np.array(label_keys[key_path])
            frames.append((key_path, data))

            if self.verbose:
                print(f"  {key_path}: shape {data.shape}")

            # Categorize for summary
            if 'trackid' in key_path.lower():
                trackid_frames.append(key_path)
            elif 'pid' in key_path.lower():
                pid_frames.append(key_path)

        # Print summary
        if trackid_frames:
            print(f"  TrackID frames ({len(trackid_frames)}): {', '.join(trackid_frames)}")
        if pid_frames:
            print(f"  PID frames ({len(pid_frames)}): {', '.join(pid_frames)}")

        return frames

    @staticmethod
    def extract_region(data: np.ndarray, ch_max_frac: float = 1, ch_min_frac: float = 0,
                       time_min_frac: float = 0,time_max_frac: float = 1) -> np.ndarray:
        """
        Extract region from data array.

        Args:
            data: (n_channels, n_ticks) array
            ch_max_frac: Fraction of max channels to include (0-1)
            time_min_frac: Start time as fraction of max ticks (0-1)

        Returns:
            Cropped data array
        """
        n_ch, n_ticks = data.shape

        # Channel: 0 to (max * ch_max_frac)
        ch_start = int(n_ch * ch_min_frac)
        ch_end = int(n_ch * ch_max_frac)

        # Time: (max * time_min_frac) to max
        time_start = int(n_ticks * time_min_frac)
        time_end = int(n_ticks * time_max_frac)

        return data[ch_start:ch_end, time_start:time_end]

    @staticmethod
    def create_white_zero_colormap():
        """
        Create a custom colormap: white -> green -> blue -> red
        0 = white, positive values progress through green -> blue -> red

        Returns:
            LinearSegmentedColormap
        """
        colors_list = [
            (1.0, 1.0, 1.0),    # white at 0
            (0.5, 1.0, 0.5),    # light green at ~0.25
            (0.0, 1.0, 0.0),    # green at ~0.5
            (0.0, 0.5, 1.0),    # blue at ~0.75
            (0.0, 0.0, 1.0),    # darker blue at ~0.85
            (1.0, 0.0, 0.0),    # red at max
        ]
        cmap = LinearSegmentedColormap.from_list('white_green_blue_red', colors_list, N=256)
        return cmap

    @staticmethod
    def create_discrete_pid_colormap(unique_values: np.ndarray):
        """
        Create a discrete colormap for PID values.
        0 = white, other values get distinct colors.

        Args:
            unique_values: Array of unique non-zero values in data

        Returns:
            LinearSegmentedColormap with distinct colors for each value
        """
        # Create colormap with white at 0, distinct colors for other values
        n_colors = len(unique_values) + 1  # +1 for 0 (white)
        colors = [(1.0, 1.0, 1.0)]  # Start with white for 0

        # Generate distinct colors using HSV color space
        for i in range(len(unique_values)):
            hue = i / max(len(unique_values), 1)
            # Convert HSV to RGB (simple approach)
            if hue < 1/6:
                r, g, b = 1.0, hue * 6, 0.0
            elif hue < 2/6:
                r, g, b = 2 - hue * 6, 1.0, 0.0
            elif hue < 3/6:
                r, g, b = 0.0, 1.0, (hue - 2/6) * 6
            elif hue < 4/6:
                r, g, b = 0.0, 2 - (hue - 2/6) * 6, 1.0
            elif hue < 5/6:
                r, g, b = (hue - 4/6) * 6, 0.0, 1.0
            else:
                r, g, b = 1.0, 0.0, 2 - (hue - 4/6) * 6

            colors.append((r, g, b))

        cmap = LinearSegmentedColormap.from_list('pid_discrete', colors, N=256)
        return cmap

    @staticmethod
    def create_trackid_colormap():
        """
        Create a fixed colormap for TrackID frames.
        10 color positions: 0 = white (no track), 1-9 = 9 distinct colors.
        TrackID values are mapped using (value % 10) to cycle through colors.

        Returns:
            LinearSegmentedColormap with 10 fixed colors
        """
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
        cmap = LinearSegmentedColormap.from_list('trackid_fixed', colors, N=256)
        return cmap

    @staticmethod
    def plot_frame(ax, data: np.ndarray, frame_name: str,
                   normalize: bool = True):
        """
        Plot a single frame as 2D heatmap with frame-type-specific coloring.

        Supports frame types:
        - Original: trackid, pid (per-sample labels)
        - Rebinned: trackid_1st, trackid_2nd (top 2 tracks), pid_1st, pid_2nd (top 2 PIDs)
        - Continuous: gauss, charge

        Args:
            ax: Matplotlib axis object
            data: 2D data array
            frame_name: Name of the frame (for title)
            normalize: Whether to normalize data for display
        """
        # Determine frame type from name
        # Check for PID frames: pid, pid_1st, pid_2nd
        is_pid = 'pid' in frame_name.lower() and 'trackid' not in frame_name.lower()
        # Check for TrackID frames: trackid, trackid_1st, trackid_2nd
        is_trackid = 'trackid' in frame_name.lower()
        is_continuous = 'gauss' in frame_name.lower() or 'charge' in frame_name.lower()

        # Only clamp negative values to 0 for continuous frames
        if is_continuous:
            data = np.maximum(data, 0)

        data_min = np.min(data)
        data_max = np.max(data)

        # Store original data for legend creation
        original_data = data.copy()

        # ===== PID FRAMES: Discrete colormap with legend =====
        if is_pid:
            # Get unique non-zero values (preserve negatives too)
            unique_vals = np.unique(data[data != 0])

            if len(unique_vals) == 0:
                # No data, just plot empty
                cmap = plt.cm.Greys
                norm = plt.Normalize(vmin=0, vmax=1)
                data_mapped = data
            else:
                # Create discrete colormap
                cmap = LabelFramePlotter.create_discrete_pid_colormap(unique_vals)

                # Map data values to [0, len(unique_vals)] for discrete colors
                # 0 stays at 0 (white), other values get mapped to 1, 2, ..., len(unique_vals)
                data_mapped = np.zeros_like(data, dtype=float)
                for idx, val in enumerate(unique_vals):
                    data_mapped[data == val] = idx + 1

                norm = plt.Normalize(vmin=0, vmax=len(unique_vals))
                data = data_mapped

        # ===== TRACKID FRAMES: Fixed colormap with modulo mapping =====
        elif is_trackid:
            # Use fixed 9-color palette, cycling through colors based on (value % 10)
            # 0 = white (no track), 1-9 cycle through 9 distinct colors
            cmap = LabelFramePlotter.create_trackid_colormap()

            # Map data values using modulo 10
            # 0 stays 0 (white), non-zero values cycle through 1-9
            data_int = data.astype(int)
            data_mapped = np.where(data_int != 0, np.abs(data_int) % 10, 0).astype(float)

            norm = plt.Normalize(vmin=0, vmax=9)
            data = data_mapped

        # ===== CONTINUOUS FRAMES: White -> Green -> Blue -> Red =====
        elif is_continuous:
            cmap = LabelFramePlotter.create_white_zero_colormap()

            if normalize:
                # Use percentile-based normalization
                vmax = np.percentile(data[data > 0], 98) if np.any(data > 0) else 1
            else:
                vmax = data_max

            vmin = 0
            norm = plt.Normalize(vmin=vmin, vmax=vmax)

        # Default case
        else:
            cmap = LabelFramePlotter.create_white_zero_colormap()
            vmin = 0
            vmax = np.percentile(data[data > 0], 98) if np.any(data > 0) else 1
            norm = plt.Normalize(vmin=vmin, vmax=vmax)

        # Create heatmap (transpose so channels are x-axis, time ticks are y-axis)
        im = ax.imshow(data.T, aspect='auto', origin='lower',
                       cmap=cmap, norm=norm,
                       interpolation='nearest')

        ax.set_xlabel('Channel')
        ax.set_ylabel('Time Tick')
        ax.set_title(frame_name, fontsize=10, fontweight='bold')

        # Add colorbar or legend depending on frame type
        if is_pid:
            # Create legend for PID discrete values
            unique_vals_original = np.unique(original_data[original_data != 0])

            if len(unique_vals_original) > 0:
                # Create legend patches
                legend_patches = []
                for idx, val in enumerate(unique_vals_original):
                    # Get color from colormap
                    color_idx = idx + 1  # +1 because 0 is reserved for white
                    color = cmap(norm(color_idx))
                    patch = plt.Rectangle((0, 0), 1, 1, fc=color, ec='black', linewidth=0.5)
                    legend_patches.append(patch)

                # Create legend with value labels
                legend_labels = [f'{int(val)}' for val in unique_vals_original]
                ax.legend(legend_patches, legend_labels, loc='upper left', fontsize=8,
                         framealpha=0.9, title='Value', title_fontsize=8)
        elif is_trackid:
            # TrackID frames: no legend, just discrete colors without labels
            pass
        else:
            # Use colorbar for continuous data
            cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label('Value', fontsize=9)

        return im

    def save_to_pdf(self, output_file: str, frames: List[Tuple[str, np.ndarray]],
                    ch_min_frac: float = 0, ch_max_frac: float = 1,
                    time_min_frac: float = 0, time_max_frac: float = 1,
                    plots_per_page: int = 4):
        """
        Save all frames to multi-page PDF.

        Args:
            output_file: Output PDF filename
            frames: List of (frame_name, data) tuples
            ch_min_frac: Channel start fraction
            ch_max_frac: Channel end fraction
            time_min_frac: Time start fraction
            time_max_frac: Time end fraction
            plots_per_page: Number of plots per PDF page
        """
        print(f"\nCreating multi-page PDF: {output_file}")
        print(f"Region: channels [{ch_min_frac*100:.0f}% max, {ch_max_frac*100:.0f}% max], "
              f"time [{time_min_frac*100:.0f}% max, {time_max_frac*100:.0f}% max]")
        print(f"Plots per page: {plots_per_page}")

        # Calculate grid layout for plots_per_page
        if plots_per_page == 1:
            rows, cols = 1, 1
        elif plots_per_page == 2:
            rows, cols = 2, 1
        elif plots_per_page == 3:
            rows, cols = 3, 1
        elif plots_per_page == 4:
            rows, cols = 2, 2
        elif plots_per_page == 6:
            rows, cols = 3, 2
        else:
            rows = int(np.ceil(np.sqrt(plots_per_page)))
            cols = int(np.ceil(plots_per_page / rows))

        pdf_pages = PdfPages(output_file)

        # Process frames in groups
        for page_idx in range(0, len(frames), plots_per_page):
            page_frames = frames[page_idx:page_idx + plots_per_page]

            # Create figure for this page
            fig, axes = plt.subplots(rows, cols, figsize=(14, 10))

            # Handle single vs. multiple subplots
            if plots_per_page == 1:
                axes = np.array([axes])
            elif rows == 1 or cols == 1:
                axes = axes.flatten()
            else:
                axes = axes.flatten()

            # Plot each frame on this page
            for plot_idx, (frame_name, data) in enumerate(page_frames):
                # Extract region
                region_data = self.extract_region(data, ch_max_frac, ch_min_frac,
                                                  time_min_frac, time_max_frac)

                # Plot
                self.plot_frame(axes[plot_idx], region_data, frame_name)

            # Hide unused subplots
            for plot_idx in range(len(page_frames), len(axes)):
                axes[plot_idx].axis('off')

            # Add overall title
            page_num = (page_idx // plots_per_page) + 1
            fig.suptitle(f'Anode0 Frames - Page {page_num}',
                        fontsize=14, fontweight='bold', y=0.995)

            plt.tight_layout(rect=[0, 0, 1, 0.99])

            # Save page to PDF
            pdf_pages.savefig(fig, bbox_inches='tight')
            plt.close(fig)

            print(f"  Page {page_num}: {len(page_frames)} frames")

        pdf_pages.close()
        print(f"\nSaved to {output_file}")

    def plot_to_pdf(self, output_file: str, ch_min_frac: float = 0,
                    ch_max_frac: float = 1, time_min_frac: float = 0,
                    time_max_frac: float = 1, plots_per_page: int = 4):
        """
        Main entry point: load frames and save to PDF.

        Args:
            output_file: Output PDF filename
            ch_min_frac: Channel start fraction (0-1)
            ch_max_frac: Channel end fraction (0-1)
            time_min_frac: Time start fraction (0-1)
            time_max_frac: Time end fraction (0-1)
            plots_per_page: Number of plots per PDF page
        """
        # Load frames
        frames = self.get_label_frames()

        if not frames:
            print("ERROR: No frames loaded")
            return False

        # Sort frames by name for consistent ordering
        frames.sort(key=lambda x: x[0])

        # Save to PDF
        self.save_to_pdf(output_file, frames, ch_min_frac, ch_max_frac,
                        time_min_frac, time_max_frac, plots_per_page)

        return True


def main():
    parser = argparse.ArgumentParser(
        description='Plot all frame*pid* and frame*trackid* frames from HDF5 to multi-page PDF',
        epilog='Supports both g4-rebinned.h5 (original) and g4-tru.h5 (rebinned with new labels)'
    )
    parser.add_argument('--input-file', '-i', default='g4-tru.h5',
                       help='Path to HDF5 file (g4-rebinned.h5 or g4-tru.h5), default g4-tru.h5')
    parser.add_argument('--output', '-o', default='anode0_frames.pdf',
                       help='Output PDF filename, default anode0_frames.pdf')
    parser.add_argument('--ch-min-frac', type=float, default=0,
                       help='Channel start as fraction of max (0-1), default 0')
    parser.add_argument('--ch-max-frac', type=float, default=1,
                       help='Channel end as fraction of max (0-1), default 1')
    parser.add_argument('--time-min-frac', type=float, default=0,
                       help='Time start as fraction of max (0-1), default 0')
    parser.add_argument('--time-max-frac', type=float, default=1,
                       help='Time end as fraction of max (0-1), default 1')
    parser.add_argument('--plots-per-page', type=int, default=4,
                       help='Number of plots per page (1, 2, 3, 4, 6), default 4')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show verbose output of loaded frames')

    args = parser.parse_args()

    # Validate arguments
    if not (0 <= args.ch_min_frac <= 1):
        print("ERROR: --ch-min-frac must be in [0, 1]")
        return 1
    if not (0 <= args.ch_max_frac <= 1):
        print("ERROR: --ch-max-frac must be in [0, 1]")
        return 1
    if not (0 <= args.time_min_frac <= 1):
        print("ERROR: --time-min-frac must be in [0, 1]")
        return 1
    if not (0 <= args.time_max_frac <= 1):
        print("ERROR: --time-max-frac must be in [0, 1]")
        return 1
    if args.ch_min_frac >= args.ch_max_frac:
        print("ERROR: --ch-min-frac must be less than --ch-max-frac")
        return 1
    if args.time_min_frac >= args.time_max_frac:
        print("ERROR: --time-min-frac must be less than --time-max-frac")
        return 1

    # Verify file exists
    if not Path(args.input_file).exists():
        print(f"ERROR: {args.input_file} not found")
        return 1

    print(f"Loading HDF5 file: {args.input_file}")

    with LabelFramePlotter(args.input_file, verbose=args.verbose) as plotter:
        success = plotter.plot_to_pdf(
            args.output,
            ch_min_frac=args.ch_min_frac,
            ch_max_frac=args.ch_max_frac,
            time_min_frac=args.time_min_frac,
            time_max_frac=args.time_max_frac,
            plots_per_page=args.plots_per_page
        )

    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
