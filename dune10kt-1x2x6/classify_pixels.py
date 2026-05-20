#!/usr/bin/env python3
"""
classify_pixels.py — Assign classification labels to each pixel in pixeldata-anode*.h5
based on MC truth from trackid_pid_map.h5.

For each event frame, reads frame_trackid_1st and frame_trackid_2nd (float32 arrays
storing track IDs per pixel), builds the MC decay chain classification, then writes
frame_label_1st and frame_label_2nd into the same pixeldata-anode*.h5 files.

Classification label encoding:
    0 = Background (track_id == 0, i.e. no hit)
    1 = Track      (mu+/-, pi+/-, p/pbar)
    2 = Shower     (e+/e-, gamma, pi0 via EM-shower process or from EM-shower parent)
    3 = Michel     (e+/e- from muon decay)
    4 = DeltaRay   (ionization e- with Track-type parent)
    5 = Blip       (isolated EM deposit: nCapture gamma, hadronic e-, etc.)
    6 = Other      (neutrinos, nuclei, neutrons, etc.)

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
LABEL_BLIP       = 5
LABEL_OTHER      = 6

LABEL_NAMES = {
    LABEL_BACKGROUND: "Background",
    LABEL_TRACK:      "Track",
    LABEL_SHOWER:     "Shower",
    LABEL_MICHEL:     "Michel",
    LABEL_DELTARAY:   "DeltaRay",
    LABEL_BLIP:       "Blip",
    LABEL_OTHER:      "Other",
}

# ── PDG sets for classification (authoritative — other scripts must match) ────

_TRACK_PDGS = {13, -13, 211, -211, 2212, -2212}
_EM_SHOWER_PDGS       = {11, -11, 22, 111}
_IONIZATION_PROCESSES = {2, 3, 8}       # eIoni, muIoni, hIoni
# Substrings used to identify EM-shower processes, mirroring the default
# fNotStoredPhysics list in ParticleListAction.cc — "Ion" excluded intentionally.
_NOT_STORED_PHYSICS = ("conv", "LowEnConversion", "Pair", "compt", "Compt",
                       "Brem", "phot", "Photo", "annihil")

PROCESS_NAMES = {
    0: "primary", 1: "Decay", 2: "eIoni", 3: "muIoni", 4: "eBrem",
    5: "compt", 6: "phot", 7: "conv", 8: "hIoni", 9: "nCapture",
    10: "muPairProd", 11: "CoulombScat", 12: "muBrems",
    13: "LowEnConversion", 14: "annihil",
    15: "neutronInelastic", 16: "hadElastic",
    17: "hBertiniCaptureAtRest", 18: "muMinusCaptureAtRest",
    19: "protonInelastic", 20: "pi+Inelastic", 21: "pi-Inelastic",
    22: "PhotonInelastic", 23: "CHIPSNuclearCaptureAtRest",
    -1: "unset",
}

def build_em_shower_ancestor_set(track_ids, pids, processes, children_map, children_list,
                                 track_to_mother=None):
    """Return the set of track IDs that are EM-shower-seeded.

    Mirrors the fNotStoredPhysics logic in ParticleListAction.cc:
    a shower root is any particle whose creator process name contains one of
    the _NOT_STORED_PHYSICS substrings (conv, LowEnConversion, Pair, compt,
    Compt, Brem, phot, Photo, annihil — "Ion" excluded).  No PDG filter is
    applied, matching the C++ behaviour.  Primary EM particles (proc==0,
    e+/e-/gamma/pi0) are also treated as shower roots.

    Uses pre-built children_map and children_list (from _build_ancestry /
    get_all_children) so no tree is rebuilt here.

    Args:
        track_ids:     array of track IDs
        pids:          array of PDG codes (same order)
        processes:     array of process codes (same order)
        children_map:  dict tid -> [child tids]  (from _build_ancestry)
        children_list: list of descendant-id lists, one per track_ids entry
                       (from get_all_children, same order as track_ids)
    """
    tid_to_pid  = {int(tid): int(pids[i])      for i, tid in enumerate(track_ids)}
    tid_to_proc = {int(tid): int(processes[i]) for i, tid in enumerate(track_ids)}

    # Mirror ParticleListAction.cc logic: a particle is a shower root if its
    # creator process name contains any _NOT_STORED_PHYSICS substring (no PDG
    # filter — any particle born by these processes is shower-seeded).
    # Primary EM particles (proc==0) are also shower roots, same as before.
    shower_chain = set()
    for i, tid_raw in enumerate(track_ids):
        tid       = int(tid_raw)
        proc_code = tid_to_proc.get(tid, -1)
        proc_name = PROCESS_NAMES.get(proc_code, "")
        is_shower_proc = any(sub in proc_name for sub in _NOT_STORED_PHYSICS)
        is_primary_em  = (proc_code == 0 and abs(tid_to_pid.get(tid, 0)) in _EM_SHOWER_PDGS)
        if is_shower_proc or is_primary_em:
            print(tid)
            # Mark this root and all its descendants as shower-seeded
            if tid not in shower_chain:
                shower_chain.add(tid)
                shower_chain.update(children_list[i])

    def _print_subtree(tid, indent=0, visited=None):
        if visited is None:
            visited = set()
        if tid in visited:
            return
        visited.add(tid)
        pid  = tid_to_pid.get(tid, 0)
        proc = tid_to_proc.get(tid, -1)
        marker = "* " if tid in shower_chain else "  "
        print(f"{'  ' * indent}|- {marker}[{tid}]  pid={pid}  proc={PROCESS_NAMES.get(proc, proc)}")
        for child in sorted(children_map.get(tid, [])):
            _print_subtree(child, indent + 1, visited)

    print(f"  [debug] shower_chain={len(shower_chain)}")
    print(shower_chain)
    # Print each shower-chain member with its root ancestor's full subtree
    printed_roots = set()
    for tid in sorted(shower_chain):
        root = get_root_ancestor(tid, track_to_mother) if track_to_mother else tid
        if root not in printed_roots:
            printed_roots.add(root)
            root_pid  = tid_to_pid.get(root, 0)
            root_proc = tid_to_proc.get(root, -1)
            print(f"  [root ancestor] [{root}]  pid={root_pid}"
                  f"  proc={PROCESS_NAMES.get(root_proc, root_proc)}")
            _print_subtree(root)
    return shower_chain


def classify_all(track_ids, pids, processes, mother_ids, mother_pids,
                 children_map=None, children_list=None):
    """Return dict tid (int) → label (int).

    Priority: Michel > DeltaRay > Track > Shower > Blip > Other

    Shower vs Blip is decided via the ancestor map built once from the full
    decay chain: an EM particle is Shower if any ancestor in its EM chain was
    created by an EM-shower process; otherwise it is a Blip (isolated deposit
    seeded by a hadronic/nuclear process — nCapture gamma, hadronic e-, etc.).

    children_map / children_list: pre-built by _build_ancestry / get_all_children.
    If not provided they are built here (backward-compatible).
    """
    tid_to_pid     = {int(tid): int(pids[i])        for i, tid in enumerate(track_ids)}
    tid_to_proc    = {int(tid): int(processes[i])   for i, tid in enumerate(track_ids)}
    tid_to_mothpid = {int(tid): int(mother_pids[i]) for i, tid in enumerate(track_ids)}

    if children_map is None or children_list is None:
        _, children_map = _build_ancestry(track_ids, pids, mother_ids)
        children_list   = [get_all_children(tid, children_map) for tid in track_ids]

    track_to_mother_local = {int(tid): int(mother_ids[i]) for i, tid in enumerate(track_ids)}
    shower_chain = build_em_shower_ancestor_set(track_ids, pids, processes,
                                                children_map, children_list,
                                                track_to_mother=track_to_mother_local)

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

        # 2. DeltaRay: created by an ionization process whose parent is a Track-type particle
        proc_name = PROCESS_NAMES.get(proc, "")
        if (proc in _IONIZATION_PROCESSES or "Ioni" in proc_name) and abs(moth_pid) in _TRACK_PDGS:
            result[tid] = LABEL_DELTARAY
            continue

        # 3. Track: extended ionizing hadron or muon
        if abs(pid) in _TRACK_PDGS:
            result[tid] = LABEL_TRACK
            continue

        # 4/5. Shower vs Blip: any EM particle whose ancestor (any depth) is
        #      shower-seeded is itself Shower; otherwise isolated Blip
        if abs(pid) in _EM_SHOWER_PDGS:
            result[tid] = LABEL_SHOWER if tid in shower_chain else LABEL_BLIP
            continue

        # 6. Other
        result[tid] = LABEL_OTHER

    # debug printout — all label types
    tid_to_ancestor = {tid: get_root_ancestor(tid, track_to_mother_local)
                       for tid in track_to_mother_local}
    for lbl, lbl_name in sorted(LABEL_NAMES.items()):
        if lbl == LABEL_BACKGROUND:
            continue
        for tid, tlbl in sorted(result.items()):
            if tlbl != lbl:
                continue
            pid      = tid_to_pid.get(tid, 0)
            proc     = tid_to_proc.get(tid, -1)
            moth_pid = tid_to_mothpid.get(tid, 0)
            moth_tid = track_to_mother_local.get(tid, 0)
            anc_tid  = tid_to_ancestor.get(tid, 0)
            print(f"  [{lbl_name:10s}] tid={tid:6d}  pid={pid:12d}"
                  f"  proc={PROCESS_NAMES.get(proc, proc)}"
                  f"  moth_pid={moth_pid}  moth_tid={moth_tid}  ancestor_tid={anc_tid}")

    return result


def _build_ancestry(track_ids, pids, mother_ids):
    """Build parent/child maps from track arrays.

    Returns:
        track_to_mother: dict  tid -> mother_id
        children_map:    dict  tid -> [child tids]
    """
    track_to_mother = {int(tid): int(mid) for tid, mid in zip(track_ids, mother_ids)}
    track_to_pid    = {int(tid): int(pid) for tid, pid in zip(track_ids, pids)}
    children_map    = defaultdict(list)

    for tid in track_ids:
        tid = int(tid)
        if tid < 0:
            pos = abs(tid)
            if pos in track_to_pid:
                children_map[pos].append(tid)
            else:
                mid = track_to_mother[tid]
                if mid != 0:
                    children_map[mid].append(tid)
        else:
            mid = track_to_mother[tid]
            if mid != 0:
                children_map[mid].append(tid)

    return track_to_mother, children_map


def get_root_ancestor(tid, track_to_mother):
    """Walk mother_id links upward and return the root ancestor track_id."""
    visited = set()
    current = int(tid)
    while True:
        if current in visited:
            break
        visited.add(current)
        mid = track_to_mother.get(current, 0)
        if mid == 0 or mid not in track_to_mother:
            break
        current = mid
    return current


def get_all_children(tid, children_map):
    """Return a flat list of ALL descendant track_ids (depth-first, excluding tid)."""
    result  = []
    stack   = list(children_map.get(int(tid), []))
    visited = {int(tid)}
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        result.append(node)
        stack.extend(children_map.get(node, []))
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
            track_ids   = mc['track_ids'][:]
            pids        = mc['pids'][:]
            processes   = mc['processes'][:]
            mother_ids  = mc['mother_ids'][:]
            mother_pids = mc['mother_pids'][:]
            track_to_mother, children_map = _build_ancestry(track_ids, pids, mother_ids)
            ancestor_ids  = [get_root_ancestor(tid, track_to_mother) for tid in track_ids]
            children_list = [get_all_children(tid, children_map)     for tid in track_ids]

            label_map = classify_all(track_ids, pids, processes, mother_ids, mother_pids,
                                     children_map=children_map, children_list=children_list)
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
        # Negative tids are G4-dropped particles attributed to their
        # MCParticle parent (abs(tid)) by SimChannel — inherit parent's label.
        nonzero_labels = np.array([label_map.get(int(abs(t)), LABEL_OTHER) for t in nonzero_tids],
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
