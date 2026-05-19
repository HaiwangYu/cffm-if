#!/usr/bin/env python3
"""
Classify MC tracks from trackid_pid_map.h5 and dump CellTree-compatible JSON.

Classification categories (priority order):
  Michel   — electron/positron from muon decay
  DeltaRay — negative track_id (EM shower suppressed by G4), or ionization e-
              with a Track-type parent
  Track    — extended ionizing particle (mu, pi, K, p, ...)
  Shower   — EM particle (e, gamma) not classified above; Blips included here
  Other    — neutrinos, nuclei, neutrons, etc.

Output JSON format matches CellTree DumpMCJSON:
  [ { "id": <tid>,
      "text": "<name>  0 MeV",
      "data": { "traj_x": [sx, ex], "traj_y": [sy, ey], "traj_z": [sz, ez],
                "start": [sx, sy, sz], "end": [ex, ey, ez],
                "pid": <pdg>, "process": <proc_code>,
                "category": "<category>" },
      "children": [...],
      "icon": "jstree-file"   // leaf nodes only
    }, ... ]

Usage:
    python classify_and_dump_json.py [trackid_pid_map.h5]
"""

import h5py
import json
import sys
import numpy as np
from collections import defaultdict

# ── PDG / process name tables ────────────────────────────────────────────────

PDG_NAMES = {
    11: "e-", -11: "e+",
    12: "nu_e", -12: "anti_nu_e",
    13: "mu-", -13: "mu+",
    14: "nu_mu", -14: "anti_nu_mu",
    22: "gamma",
    111: "pi0", 211: "pi+", -211: "pi-",
    321: "K+", -321: "K-",
    2112: "n", 2212: "p",
    1000180400: "Ar40", 1000180390: "Ar39", 1000180380: "Ar38",
    1000170350: "Cl35", 1000170370: "Cl37",
}

PROCESS_NAMES = {
    0: "primary", 1: "Decay", 2: "eIoni", 3: "muIoni", 4: "eBrem",
    5: "compt", 6: "phot", 7: "conv", 8: "hIoni", 9: "nCapture",
    10: "muPairProd", 11: "CoulombScat", 12: "muBrems",
    13: "LowEnConversion", 14: "annihil", -1: "unset",
}

# PDG sets for classification
_TRACK_PDGS = {13, -13, 15, -15, 211, -211, 321, -321, 2212, -2212,
               2112, 130, 310, 3122, 3112, 3222, 3312, 3334,
               1000010020, 1000010030, 1000020030, 1000020040}
_IONIZATION_PROCESSES = {2, 3, 8}   # eIoni, muIoni, hIoni
_EM_SHOWER_PROCESSES  = {4, 5, 6, 7, 14}  # eBrem, compt, phot, conv, annihil


def get_particle_name(pdg):
    if pdg in PDG_NAMES:
        return PDG_NAMES[pdg]
    if pdg > 1000000000:
        z = (pdg // 10000) % 1000
        a = (pdg // 10) % 1000
        elements = {1: "H", 2: "He", 6: "C", 7: "N", 8: "O",
                    14: "Si", 16: "S", 17: "Cl", 18: "Ar", 19: "K", 20: "Ca"}
        return f"{elements.get(z, f'Z{z}')}{a}"
    return f"pdg:{pdg}"


# ── Data loading ─────────────────────────────────────────────────────────────

def load_data(filename):
    """Load mcpart group for all events; also read start/end_xyzts if present."""
    with h5py.File(filename, 'r') as f:
        groups = list(f.keys())
        print(f"Found {len(groups)} event(s): {groups}")
        all_data = {}
        for grp in groups:
            mc = f[grp]['mcpart']
            n = len(mc['track_ids'])
            zeros4 = np.zeros((n, 4), dtype=np.float32)
            entry = {
                'track_ids':  mc['track_ids'][:],
                'pids':       mc['pids'][:],
                'mother_ids': mc['mother_ids'][:],
                'processes':  mc['processes'][:],
                'mother_pids': mc['mother_pids'][:],
                'start_xyzts': mc['start_xyzts'][:] if 'start_xyzts' in mc else zeros4,
                'end_xyzts':   mc['end_xyzts'][:]   if 'end_xyzts'   in mc else zeros4,
            }
            all_data[grp] = entry
    return all_data


# ── Tree building (from visualize_decay_chain.py) ────────────────────────────

def build_tree(track_ids, pids, mother_ids):
    track_to_pid    = {tid: pids[i]       for i, tid in enumerate(track_ids)}
    track_to_mother = {tid: mother_ids[i] for i, tid in enumerate(track_ids)}
    children = defaultdict(list)
    roots = set()

    for tid in track_ids:
        if tid < 0:
            pos = abs(tid)
            if pos in track_to_pid:
                children[pos].append(tid)
            else:
                mid = track_to_mother[tid]
                if mid == 0:
                    roots.add(tid)
                else:
                    children[mid].append(tid)
                    if mid not in track_to_pid:
                        roots.add(mid)
        else:
            mid = track_to_mother[tid]
            if mid == 0:
                roots.add(tid)
            else:
                children[mid].append(tid)
                if mid not in track_to_pid:
                    roots.add(mid)

    primaries = sorted([t for t in roots if t in track_to_pid and track_to_mother.get(t, 0) == 0])
    return track_to_pid, track_to_mother, children, primaries


# ── Classification ────────────────────────────────────────────────────────────

def classify_all(track_ids, pids, processes, mother_pids):
    """Return dict tid → category string.

    Priority: Michel > DeltaRay > Track > Shower > Other
    """
    # Build fast lookup dicts
    tid_to_pid      = {tid: pids[i]        for i, tid in enumerate(track_ids)}
    tid_to_proc     = {tid: int(processes[i]) for i, tid in enumerate(track_ids)}
    tid_to_mothpid  = {tid: mother_pids[i] for i, tid in enumerate(track_ids)}

    result = {}

    for tid in track_ids:
        pid      = int(tid_to_pid.get(tid, 0))
        proc     = tid_to_proc.get(tid, -1)
        moth_pid = int(tid_to_mothpid.get(tid, 0))

        # 1. Michel: e+/e- from Decay of mu+/mu-
        if abs(pid) == 11 and proc == 1 and abs(moth_pid) == 13:
            result[tid] = "Michel"
            continue

        # 2. DeltaRay: negative track ID (EM shower daughter suppressed by G4)
        #    or ionization electron with a Track-type parent
        if tid < 0:
            result[tid] = "DeltaRay"
            continue
        if abs(pid) == 11 and proc in _IONIZATION_PROCESSES and abs(moth_pid) in _TRACK_PDGS:
            result[tid] = "DeltaRay"
            continue

        # 3. Track: extended ionizing hadron or muon
        if abs(pid) in _TRACK_PDGS:
            result[tid] = "Track"
            continue

        # 4. Shower: EM particles (e+/e-, gamma, pi0) — Blips merged in here
        #    pi0 decays immediately to two gammas so it belongs in the EM shower category
        if abs(pid) in (11, 22, 111):
            result[tid] = "Shower"
            continue

        # 5. Other (neutrinos, nuclei, neutrons that didn't ionise, etc.)
        result[tid] = "Other"

    return result


# ── JSON tree building ────────────────────────────────────────────────────────

def _make_node(tid, track_to_pid, children, categories,
               tid_to_proc, starts, ends, visited):
    """Recursively build a CellTree-format JSON node dict."""
    if tid in visited:
        return None
    visited.add(tid)

    pid      = int(track_to_pid.get(tid, 0))
    name     = get_particle_name(pid)
    proc     = int(tid_to_proc.get(tid, -1))
    cat      = categories.get(tid, "Other")
    sx, sy, sz = float(starts[tid][0]), float(starts[tid][1]), float(starts[tid][2])
    ex, ey, ez = float(ends[tid][0]),   float(ends[tid][1]),   float(ends[tid][2])

    node = {
        "id":   tid,
        "text": f"{name}  0 MeV",
        "data": {
            "traj_x": [round(sx, 1), round(ex, 1)],
            "traj_y": [round(sy, 1), round(ey, 1)],
            "traj_z": [round(sz, 1), round(ez, 1)],
            "start":  [round(sx, 1), round(sy, 1), round(sz, 1)],
            "end":    [round(ex, 1), round(ey, 1), round(ez, 1)],
            "pid":      pid,
            "process":  proc,
            "category": cat,
        },
        "children": [],
    }

    child_nodes = []
    for child_tid in sorted(children.get(tid, [])):
        child_node = _make_node(child_tid, track_to_pid, children, categories,
                                tid_to_proc, starts, ends, visited)
        if child_node is not None:
            child_nodes.append(child_node)

    if child_nodes:
        node["children"] = child_nodes
    else:
        node["children"] = []
        node["icon"] = "jstree-file"

    return node


def dump_mctree_json(data, categories, output_file):
    """Build and write a CellTree DumpMCJSON-format JSON file."""
    track_ids   = data['track_ids']
    pids        = data['pids']
    mother_ids  = data['mother_ids']
    processes   = data['processes']
    start_xyzts = data['start_xyzts']
    end_xyzts   = data['end_xyzts']

    track_to_pid, track_to_mother, children, primaries = build_tree(
        track_ids, pids, mother_ids
    )

    # Build fast per-tid lookups
    n = len(track_ids)
    tid_to_proc = {track_ids[i]: int(processes[i]) for i in range(n)}
    starts = {track_ids[i]: start_xyzts[i] for i in range(n)}
    ends   = {track_ids[i]: end_xyzts[i]   for i in range(n)}

    visited = set()
    tree = []
    for primary in primaries:
        node = _make_node(primary, track_to_pid, children, categories,
                          tid_to_proc, starts, ends, visited)
        if node is not None:
            tree.append(node)

    class _NpEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.integer): return int(obj)
            if isinstance(obj, np.floating): return float(obj)
            if isinstance(obj, np.ndarray): return obj.tolist()
            return super().default(obj)

    with open(output_file, 'w') as f:
        json.dump(tree, f, indent=2, cls=_NpEncoder)
    print(f"  Written: {output_file}  ({len(tree)} primary chain(s))")


# ── BEE cluster json from MC tracks ──────────────────────────────────────────

# Category → cluster_id mapping (shown as color groups in BEE)
CATEGORY_ID = {
    "Track":    0,
    "Shower":   1,
    "Michel":   2,
    "DeltaRay": 3,
    "Other":    4,
}

def _sample_segment(sx, sy, sz, ex, ey, ez, n_points):
    """Uniformly sample n_points between (sx,sy,sz) and (ex,ey,ez)."""
    xs, ys, zs = [], [], []
    for t in np.linspace(0.0, 1.0, n_points):
        xs.append(round(float(sx + t * (ex - sx)), 2))
        ys.append(round(float(sy + t * (ey - sy)), 2))
        zs.append(round(float(sz + t * (ez - sz)), 2))
    return xs, ys, zs


def _collect_nodes(node):
    """Recursively yield all nodes from an mc tree."""
    yield node
    for child in node.get("children", []):
        yield from _collect_nodes(child)


def make_bee_cluster_from_mctree(mctree, output_file,
                                  geom="dune10kt", run_no=0, subrun_no=0,
                                  points_per_cm=0.3, min_points=2):
    """Generate a BEE cluster JSON from the mc tree JSON.

    Each track is sampled uniformly between start and end.
    Number of sample points scales with track length (points_per_cm).
    cluster_id encodes the category: Track=0, Shower=1, Michel=2, DeltaRay=3, Other=4
    q is always 1.
    """
    xs, ys, zs, qs, cids = [], [], [], [], []

    for root_node in mctree:
        for node in _collect_nodes(root_node):
            d = node["data"]
            cat = d.get("category", "Other")
            cid = CATEGORY_ID.get(cat, 4)
            sx, sy, sz = d["start"]
            ex, ey, ez = d["end"]

            # skip degenerate points (start == end)
            length = ((ex-sx)**2 + (ey-sy)**2 + (ez-sz)**2) ** 0.5
            n = max(min_points, int(length * points_per_cm))
            if length < 0.01:
                n = 1

            px, py, pz = _sample_segment(sx, sy, sz, ex, ey, ez, n)
            xs.extend(px)
            ys.extend(py)
            zs.extend(pz)
            qs.extend([1.0] * n)
            cids.extend([cid] * n)

    event_no = mctree[0]["id"] if mctree else 0  # use first track id as proxy; override below
    out = {
        "runNo":      run_no,
        "subRunNo":   subrun_no,
        "eventNo":    int(subrun_no),   # will be overridden by caller
        "geom":       geom,
        "type":       "cluster",
        "x":          xs,
        "y":          ys,
        "z":          zs,
        "q":          qs,
        "cluster_id": cids,
    }

    with open(output_file, 'w') as f:
        json.dump(out, f)
    print(f"  Written: {output_file}  ({len(xs)} points, "
          f"categories: {', '.join(f'{k}={CATEGORY_ID[k]}' for k in CATEGORY_ID)})")
    return out


# ── Statistics ────────────────────────────────────────────────────────────────

def print_category_summary(categories):
    from collections import Counter
    counts = Counter(categories.values())
    total = len(categories)
    print(f"\n  Classification summary ({total} tracks):")
    for cat in ("Track", "Shower", "Michel", "DeltaRay", "Other"):
        n = counts.get(cat, 0)
        print(f"    {cat:<10}: {n:>6}  ({100*n/total:.1f}%)" if total else f"    {cat:<10}: 0")


# ── BEE zip packaging ─────────────────────────────────────────────────────────

def make_bee_zip(event_map, zip_name="upload.zip"):
    """Package mc + cluster JSON files into BEE-compatible zip.

    BEE expects:
        data/
          {eventNo}/
            {eventNo}-mc.json
            {eventNo}-cluster.json
    event_map: dict of event_id -> {'mc': path, 'cluster': path}
    """
    import zipfile, shutil, os

    data_dir = "data"
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    os.makedirs(data_dir)

    for event_id, paths in event_map.items():
        ev_dir = os.path.join(data_dir, str(event_id))
        os.makedirs(ev_dir)

        dest_mc = os.path.join(ev_dir, f"{event_id}-mc.json")
        shutil.copy(paths['mc'], dest_mc)
        print(f"  Packed: {dest_mc}")

        dest_cl = os.path.join(ev_dir, f"{event_id}-cluster.json")
        shutil.copy(paths['cluster'], dest_cl)
        print(f"  Packed: {dest_cl}")

    if os.path.exists(zip_name):
        os.remove(zip_name)
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(data_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                zf.write(fpath)
    shutil.rmtree(data_dir)
    print(f"\nBEE zip ready: {zip_name}")
    print(f"Upload with:   bash upload-to-bee.sh {zip_name}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    filename = sys.argv[1] if len(sys.argv) > 1 else "trackid_pid_map.h5"
    print(f"Loading: {filename}")

    try:
        all_data = load_data(filename)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    event_map = {}
    for event_id, data in all_data.items():
        print(f"\n{'='*60}")
        print(f"EVENT: {event_id}")
        print(f"{'='*60}")

        categories = classify_all(
            data['track_ids'], data['pids'],
            data['processes'], data['mother_pids']
        )
        print_category_summary(categories)

        out_mc = f"mctree_event{event_id}.json"
        dump_mctree_json(data, categories, out_mc)

        # Load the mc tree back to sample points for the BEE cluster json
        with open(out_mc) as f:
            mctree = json.load(f)

        out_cluster = f"bee_cluster_event{event_id}.json"
        cl_out = make_bee_cluster_from_mctree(
            mctree, out_cluster,
            geom="dune10kt", run_no=0, subrun_no=0,
        )
        # Patch eventNo to match the HDF5 event key
        cl_out["eventNo"] = int(event_id)
        with open(out_cluster, 'w') as f:
            json.dump(cl_out, f)

        event_map[event_id] = {'mc': out_mc, 'cluster': out_cluster}

    make_bee_zip(event_map)


if __name__ == "__main__":
    main()
