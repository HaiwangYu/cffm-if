import h5py
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, ListedColormap, BoundaryNorm
import sys
import os


def process_file(filename):
    """Process a single HDF5 file and generate plots."""

    print("\nFile structure:")
    print("-" * 80)

    with h5py.File(filename, 'r') as f:
        def print_name(name, obj):
            indent = "  " * (name.count('/'))
            if isinstance(obj, h5py.Dataset):
                print(f"{indent}{name}: shape={obj.shape}, dtype={obj.dtype}")
            else:
                print(f"{indent}{name}/ (group)")

        f.visititems(print_name)

        print("\n" + "=" * 80)
        print("Dataset Details:")
        print("=" * 80)

        # Recursively get all datasets
        datasets_found = {}
        def collect_datasets(name, obj):
            if isinstance(obj, h5py.Dataset):
                datasets_found[name] = obj

        f.visititems(collect_datasets)

        # Print details for each dataset
        for ds_name, dataset in datasets_found.items():
            print(f"\n{ds_name}:")
            print(f"  Shape: {dataset.shape}")
            print(f"  Dtype: {dataset.dtype}")
            print(f"  Size: {dataset.size} elements")
            if dataset.size > 0 and dataset.size <= 100:
                print(f"  Data: {dataset[()]}")
            elif dataset.size > 0:
                print(f"  Sample (first 5 elements): {dataset[...].flat[:5]}")

        # Try to find and plot 2D data (channels vs time)
        print("\n" + "=" * 80)
        print("Looking for 2D data for visualization...")
        print("=" * 80)

        # Look for frame structure and extract 2D arrays
        frames_to_plot = {}

        for frame_key in f.keys():
            frame_obj = f[frame_key]
            if isinstance(frame_obj, h5py.Group):
                print(f"\nProcessing frame: {frame_key}")

                # Look for different types of datasets based on filename
                if 'tru' in filename.lower():
                    # For g4-tru.h5: look for trackid and pid (discrete labels)
                    for tag in ['trackid', 'pid']:
                        dataset_path = f"{frame_key}/frame_{tag}"
                        if dataset_path in f:
                            data = f[dataset_path][:]
                            print(f"  Found {dataset_path}: shape={data.shape}")
                            frames_to_plot[f"{frame_key}_{tag}"] = (tag, data, 'discrete')

                elif 'rec' in filename.lower():
                    # For g4-rec.h5: look for gauss (continuous charge values)
                    for tag in ['gauss']:
                        dataset_path = f"{frame_key}/frame_{tag}"
                        if dataset_path in f:
                            data = f[dataset_path][:]
                            print(f"  Found {dataset_path}: shape={data.shape}")
                            frames_to_plot[f"{frame_key}_{tag}"] = (tag, data, 'continuous')

        # If no frame structure, try direct access
        if not frames_to_plot:
            print("\nNo frame structure found, looking for direct datasets...")
            for ds_name, dataset in datasets_found.items():
                if dataset.ndim == 2:
                    if 'pid' in ds_name.lower():
                        frames_to_plot[ds_name] = ('pid', dataset[()], 'discrete')
                    elif 'trackid' in ds_name.lower():
                        frames_to_plot[ds_name] = ('trackid', dataset[()], 'discrete')
                    elif 'gauss' in ds_name.lower():
                        frames_to_plot[ds_name] = ('gauss', dataset[()], 'continuous')
                    else:
                        # Default to continuous for unknown datasets
                        frames_to_plot[ds_name] = (ds_name, dataset[()], 'continuous')

        # Plot the data
        if frames_to_plot:
            print("\n" + "=" * 80)
            print(f"Creating plots for {len(frames_to_plot)} dataset(s)...")
            print("=" * 80)

            fig_idx = 0
            for plot_name, plot_data in frames_to_plot.items():
                tag_type, data, plot_type = plot_data

                if data.size == 0:
                    print(f"Skipping {plot_name}: empty dataset")
                    continue

                fig_idx += 1

                # Create figure with proper size
                fig, ax = plt.subplots(figsize=(14, 8))

                # Create heatmap
                if data.ndim == 1:
                    print(f"Warning: {plot_name} is 1D, cannot create 2D plot")
                    continue

                print(f"\nPlotting {plot_name}:")
                print(f"  Data shape: {data.shape}")
                print(f"  Data range: [{data.min()}, {data.max()}]")
                print(f"  Non-zero elements: {np.count_nonzero(data)}")
                print(f"  Plot type: {plot_type}")

                if plot_type == 'discrete':
                    # ===== DISCRETE PLOTTING (trackid, pid) =====
                    # Transpose: Channels on X-axis, Time on Y-axis

                    data_transposed = data.T

                    print(f"  Transposed shape: {data_transposed.shape}")

                    # Get unique values and create discrete colormap
                    unique_vals = np.unique(data.astype(int))
                    print(f"  Unique values: {unique_vals}")
                    print(f"  Number of unique values: {len(unique_vals)}")

                    # Create color palette: white for 0, distinct colors for other integers
                    base_colors = [
                        '#FF0000',  # Red
                        '#0000FF',  # Blue
                        '#00FF00',  # Green
                        '#FFD700',  # Gold/Yellow
                        '#FF8C00',  # Orange
                        '#FF1493',  # Deep Pink
                        '#00FFFF',  # Cyan
                        '#9932CC',  # Dark Orchid
                        '#32CD32',  # Lime Green
                        '#FF4500',  # Orange Red
                        '#1E90FF',  # Dodger Blue
                        '#DC143C',  # Crimson
                        '#00CED1',  # Dark Turquoise
                        '#ADFF2F',  # Green Yellow
                        '#FF69B4',  # Hot Pink
                        '#8A2BE2',  # Blue Violet
                        '#20B2AA',  # Light Sea Green
                        '#FF6347',  # Tomato
                        '#4169E1',  # Royal Blue
                        '#9400D3',  # Dark Violet
                    ]

                    # Map each unique value to a color
                    color_map = {}
                    color_map[0] = '#FFFFFF'  # White for 0

                    for idx, val in enumerate(unique_vals):
                        if val != 0:
                            color_map[val] = base_colors[idx % len(base_colors)]

                    # Convert data to integer
                    data_int = data_transposed.astype(int)

                    # Create list of colors for the colormap (ordered by value)
                    sorted_vals = sorted(unique_vals)
                    colors_list = [color_map[v] for v in sorted_vals]

                    # Create boundaries for BoundaryNorm
                    if len(sorted_vals) == 1:
                        boundaries = [sorted_vals[0] - 0.5, sorted_vals[0] + 0.5]
                    else:
                        boundaries = [sorted_vals[0] - 0.5]
                        for i in range(len(sorted_vals) - 1):
                            boundaries.append((sorted_vals[i] + sorted_vals[i + 1]) / 2.0)
                        boundaries.append(sorted_vals[-1] + 0.5)

                    # Create custom colormap and norm
                    cmap = ListedColormap(colors_list)
                    norm = BoundaryNorm(boundaries, cmap.N)

                    # Create the image
                    im = ax.imshow(data_int, aspect='auto', cmap=cmap, norm=norm,
                                  origin='lower', interpolation='nearest')

                    # Labels and title
                    ax.set_xlabel('Channels', fontsize=12)
                    ax.set_ylabel('Time Bins', fontsize=12)
                    ax.set_title(f'{plot_name}\n{tag_type.upper()} vs Channel vs Time\n'
                                f'(Unique values: {len(unique_vals)}, White=0)',
                                fontsize=14, fontweight='bold')

                    # Colorbar with discrete ticks
                    cbar = plt.colorbar(im, ax=ax, label=f'{tag_type.upper()} (Discrete Values)',
                                      boundaries=boundaries, ticks=sorted_vals)
                    cbar.ax.set_yticklabels([str(v) for v in sorted_vals], fontsize=9)

                else:  # continuous
                    # ===== CONTINUOUS PLOTTING (gauss charge) =====
                    # Transpose: Channel on X-axis, Time on Y-axis

                    data_transposed = data.T

                    print(f"  Transposed shape: {data_transposed.shape}")
                    print(f"  Data min: {data.min()}, max: {data.max()}")

                    # Use log scale if large dynamic range
                    use_log = (data.max() > 0 and data.min() >= 0 and
                              data.max() / (data.min() + 1e-10) > 100)

                    if use_log and np.any(data > 0):
                        data_plot = np.where(data_transposed > 0, data_transposed, 1e-10)
                        im = ax.imshow(data_plot, aspect='auto', cmap='viridis',
                                      norm=LogNorm(vmin=data[data > 0].min(), vmax=data.max()),
                                      origin='lower', interpolation='bilinear')
                        cbar_label = f'{tag_type.upper()} Charge (log scale)'
                    else:
                        im = ax.imshow(data_transposed, aspect='auto', cmap='viridis',
                                      origin='lower', interpolation='bilinear')
                        cbar_label = f'{tag_type.upper()} Charge'

                    # Labels and title
                    ax.set_xlabel('Channels', fontsize=12)
                    ax.set_ylabel('Time Bins', fontsize=12)
                    ax.set_title(f'{plot_name}\nCharge vs Channel vs Time',
                                fontsize=14, fontweight='bold')

                    # Colorbar
                    cbar = plt.colorbar(im, ax=ax, label=cbar_label)

                # Add grid
                ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

                plt.tight_layout()

                # Save figure with filename prefix
                file_prefix = filename.replace('.h5', '')
                output_name = f"{file_prefix}_{plot_name.replace('/', '_')}_heatmap.png"
                plt.savefig(output_name, dpi=100, bbox_inches='tight')
                print(f"  Saved: {output_name}")

                plt.close()

            print("\n" + "=" * 80)
            print("Plotting complete for this file!")
            print("=" * 80)
        else:
            print("\nNo 2D datasets found suitable for plotting")


# Find all HDF5 files to process
files_to_process = []
if os.path.exists('g4-tru.h5'):
    files_to_process.append('g4-tru.h5')
if os.path.exists('g4-rec.h5'):
    files_to_process.append('g4-rec.h5')

if not files_to_process:
    print("ERROR: No HDF5 files found (g4-tru.h5 or g4-rec.h5)")
    sys.exit(1)

print("=" * 80)
print(f"Found {len(files_to_process)} file(s) to process: {files_to_process}")
print("=" * 80)

# Process all files
for filename in files_to_process:
    print("\n" + "=" * 80)
    print(f"Inspecting HDF5 file: {filename}")
    print("=" * 80)

    process_file(filename)

print("\n" + "=" * 80)
print("All files processed successfully!")
print("=" * 80)
