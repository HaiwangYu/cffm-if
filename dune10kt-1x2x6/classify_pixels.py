#!/usr/bin/env python3
"""
classify_pixels.py — Assign classification labels to each pixel in pixeldata-anode*.h5
based on MC truth from trackid_pid_map.h5.

For each event frame, reads frame_trackid_1st and frame_trackid_2nd (float32 arrays
storing track IDs per pixel), builds the MC decay chain classification, then writes
frame_label_1st and frame_label_2nd into the same pixeldata-anode*.h5 files.

Classification label encoding:
    0 = Background (track_id == 0, i.e. no hit)
    1 = Track      (mu, pi, K, p, n, heavy ions)
    2 = Shower     (e+/e-, gamma, pi0)
    3 = Michel     (e+/e- from muon decay)
    4 = DeltaRay   (negative track_id, or ionization e- with Track-type parent)
    5 = Other      (neutrinos, nuclei, neutrons, etc.)

Usage:
    python3 classify_pixels.py [trackid_pid_map.h5] [pixeldata-anode*.h5 ...]

    If no pixeldata files are given, globs for pixeldata-anode*.h5 in same directory.

Example:
    python3 classify_pixels.py trackid_pid_map.h5 pixeldata-anode0.h5 pixeldata-anode1.h5
"""

import sys
import glob
import os
import numpy as np
import h5py
from collections import defaultdict

# ── Label encoding ────────────────────────────────────────────────────────────

LABEL_BACKGROUND = 0
LABEL_TRACK      = 1
LABEL_SHOWER     = 2
LABEL_MICHEL     = 3
LABEL_DELTARAY   = 4
LABEL_OTHER      = 5

LABEL_NAMES = {
    LABEL_BACKGROUND: "Background",
    LABEL_TRACK:      "Track",
    LABEL_SHOWER:     "Shower",
    LABEL_MICHEL:     "Michel",
    LABEL_DELTARAY:   "DeltaRay",
    LABEL_OTHER:      "Other",
}

# ── PDG sets for classification (same logic as classify_and_dump_json.py) ─────

_TRACK_PDGS = {13, -13, 15, -15, 211, -211, 321, -321, 2212, -2212,
               2112, 130, 310, 3122, 3112, 3222, 3312, 3334,
               1000010020, 1000010030, 1000020030, 1000020040}
_IONIZATION_PROCESSES = {2, 3, 8}   # eIoni, muIoni, hIoni


def classify_all(track_ids, pids, processes, mother_pids):
    """Return dict tid (int) → label (int).

    Priority: Michel > DeltaRay > Track > Shower > Other
    """
    tid_to_pid     = {int(tid): int(pids[i])        for i, tid in enumerate(track_ids)}
    tid_to_proc    = {int(tid): int(processes[i])   for i, tid in enumerate(track_ids)}
    tid_to_mothpid = {int(tid): int(mother_pids[i]) for i, tid in enumerate(track_ids)}

    result = {}

    for tid_raw in track_ids:
        tid      = int(tid_raw)
        pid      = tid_to_pid.get(tid, 0)
        proc     = tid_to_proc.get(tid, -1)
        moth_pid = tid_to_mothpid.get(tid, 0)

        # 1. Michel: e+/e- from Decay (proc=1) of mu+/mu-
        if abs(pid) == 11 and proc == 1 and abs(moth_pid) == 13:
            result[tid] = LABEL_MICHEL
            continue

        # 2. DeltaRay: negative track ID, or ionization e- with Track-type parent
        if tid < 0:
            result[tid] = LABEL_DELTARAY
            continue
        if abs(pid) == 11 and proc in _IONIZATION_PROCESSES and abs(moth_pid) in _TRACK_PDGS:
            result[tid] = LABEL_DELTARAY
            continue

        # 3. Track: extended ionizing hadron or muon
        if abs(pid) in _TRACK_PDGS:
            result[tid] = LABEL_TRACK
            continue

        # 4. Shower: EM particles (e+/e-, gamma, pi0)
        if abs(pid) in (11, 22, 111):
            result[tid] = LABEL_SHOWER
            continue

        # 5. Other
        result[tid] = LABEL_OTHER

    return result


def load_classification_maps(truth_file):
    """Load mcpart from all events in trackid_pid_map.h5.

    Returns dict: event_key (str) → dict(tid → label_int)
    """
    print(f"Loading MC truth: {truth_file}")
    maps = {}
    with h5py.File(truth_file, 'r') as f:
        event_keys = list(f.keys())
        print(f"  Events found: {event_keys}")
        for ek in event_keys:
            mc = f[ek]['mcpart']
            track_ids  = mc['track_ids'][:]
            pids       = mc['pids'][:]
            processes  = mc['processes'][:]
            mother_pids = mc['mother_pids'][:]
            label_map = classify_all(track_ids, pids, processes, mother_pids)
            maps[ek] = label_map
            # Summary
            from collections import Counter
            counts = Counter(label_map.values())
            total = len(label_map)
            print(f"  Event {ek}: {total} tracks — " +
                  ", ".join(f"{LABEL_NAMES[l]}={counts.get(l,0)}" for l in sorted(LABEL_NAMES) if l != 0))
    return maps


def build_label_frame(track_id_frame, label_map):
    """Convert a float32 track_id frame to an int8 label frame.

    track_id_frame: np.ndarray shape (N_ch, N_tick), dtype float32
                    Values are float-encoded track IDs; 0.0 means no hit.
    label_map: dict(int tid → int label)

    Returns: np.ndarray same shape, dtype int8
    """
    shape = track_id_frame.shape
    flat = track_id_frame.ravel()

    # Convert float→int track IDs (values are stored as float32 of integer IDs)
    tid_int = flat.astype(np.int32)

    # Vectorized lookup via numpy (fast path for large frames)
    # Build lookup table covering the full ID range if feasible, else use dict
    label_flat = np.zeros(len(tid_int), dtype=np.int8)

    nonzero_mask = tid_int != 0
    if nonzero_mask.any():
        nonzero_tids = tid_int[nonzero_mask]
        # Vectorized dict lookup
        nonzero_labels = np.array([label_map.get(int(t), LABEL_OTHER) for t in nonzero_tids],
                                   dtype=np.int8)
        label_flat[nonzero_mask] = nonzero_labels

    return label_flat.reshape(shape)


def print_label_stats(label_frame, name):
    """Print per-label pixel counts for a label frame."""
    from collections import Counter
    counts = Counter(label_frame.ravel().tolist())
    total = label_frame.size
    nonzero = total - counts.get(0, 0)
    print(f"    {name}: {nonzero} hit pixels of {total} total")
    for l in sorted(LABEL_NAMES):
        n = counts.get(l, 0)
        if n > 0:
            print(f"      {LABEL_NAMES[l]:10s}({l}): {n:>8}  ({100*n/total:.2f}%)")


def process_anode_file(anode_file, classification_maps, overwrite=True):
    """Read frame_trackid_1st/2nd, compute label frames, write back to same file."""
    print(f"\nProcessing: {anode_file}")
    with h5py.File(anode_file, 'r+') as f:
        event_keys = list(f.keys())
        for ek in event_keys:
            grp = f[ek]

            # Get classification map for this event
            label_map = classification_maps.get(ek)
            if label_map is None:
                print(f"  Event {ek}: no MC truth available, skipping")
                continue

            for slot in ('1st', '2nd'):
                src_name = f'frame_trackid_{slot}'
                dst_name = f'frame_label_{slot}'

                if src_name not in grp:
                    print(f"  Event {ek}: {src_name} not found, skipping")
                    continue

                tid_frame = grp[src_name][:]
                label_frame = build_label_frame(tid_frame, label_map)

                if dst_name in grp:
                    if overwrite:
                        del grp[dst_name]
                        print(f"  Event {ek}: overwriting {dst_name}")
                    else:
                        print(f"  Event {ek}: {dst_name} already exists, skipping (use --overwrite)")
                        continue

                grp.create_dataset(dst_name, data=label_frame,
                                   dtype=np.int8, compression='gzip', compression_opts=4)
                print(f"  Event {ek}: wrote {dst_name}  shape={label_frame.shape} dtype=int8")
                print_label_stats(label_frame, dst_name)


def main():
    args = sys.argv[1:]

    # Parse arguments: first arg is truth file, rest are anode files
    # If no explicit anode files, glob in same directory as truth file
    if not args:
        print("Usage: python3 classify_pixels.py <trackid_pid_map.h5> [pixeldata-anode*.h5 ...]")
        sys.exit(1)

    truth_file = args[0]
    anode_files = args[1:]

    if not anode_files:
        base_dir = os.path.dirname(os.path.abspath(truth_file))
        anode_files = sorted(glob.glob(os.path.join(base_dir, 'pixeldata-anode*.h5')))
        if not anode_files:
            print(f"No pixeldata-anode*.h5 files found in {base_dir}")
            sys.exit(1)
        print(f"Auto-detected anode files: {[os.path.basename(p) for p in anode_files]}")

    if not os.path.exists(truth_file):
        print(f"Truth file not found: {truth_file}")
        sys.exit(1)

    # Load classification maps (once, shared across all anode files)
    classification_maps = load_classification_maps(truth_file)

    # Process each anode file
    for anode_file in anode_files:
        if not os.path.exists(anode_file):
            print(f"Warning: {anode_file} not found, skipping")
            continue
        process_anode_file(anode_file, classification_maps)

    print("\nDone.")


if __name__ == '__main__':
    main()
