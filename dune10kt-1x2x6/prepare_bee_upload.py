#!/usr/bin/env python3
"""
Prepare BEE upload zip from the mc.json files produced by TrackIDPIDMap2h5.

The C++ code writes:  bee/data/<frame_id>/<frame_id>-mc.json
This script adds a companion cluster.json and packages into a zip.
If a trackid_pid_map.h5 with classification data is provided, also creates
cluster_class.json where cluster_id is the classification label (0-6).

Usage:   python3 prepare_bee_upload.py [bee_dir] [trackid_pid_map.h5]
Upload:  bash upload-to-bee.sh bee/bee_upload.zip
"""

import json, os, sys, zipfile
import numpy as np
import h5py


def collect_nodes(node):
    yield node
    for child in node.get("children", []):
        yield from collect_nodes(child)


def make_cluster_json(mctree, event_id, geom="dune10kt"):
    xs, ys, zs, qs, cids = [], [], [], [], []
    for root in mctree:
        for node in collect_nodes(root):
            d = node.get("data", {})
            tx, ty, tz = d.get("traj_x"), d.get("traj_y"), d.get("traj_z")
            if not tx or not ty or not tz:
                continue
            tid = node.get("id", 0)
            n = len(tx)
            xs.extend(round(v, 2) for v in tx)
            ys.extend(round(v, 2) for v in ty)
            zs.extend(round(v, 2) for v in tz)
            qs.extend([1.0] * n)
            cids.extend([tid] * n)
    return {
        "runNo": 0, "subRunNo": 0, "eventNo": int(event_id),
        "geom": geom, "type": "cluster",
        "x": xs, "y": ys, "z": zs, "q": qs, "cluster_id": cids,
    }


def load_classification_map(truth_file):
    """Load tid->label mapping from mcpart/ in trackid_pid_map.h5.

    Returns dict: event_key (str) -> dict(tid -> label_int)
    """
    maps = {}
    with h5py.File(truth_file, 'r') as f:
        for ek in f.keys():
            mc = f[ek]['mcpart']
            if 'labels' not in mc:
                continue
            tids   = mc['track_ids'][:]
            labels = mc['labels'][:]
            maps[ek] = {int(t): int(l) for t, l in zip(tids, labels)}
    return maps


def make_cluster_class_json(mctree, event_id, label_map, geom="dune10kt"):
    """Like make_cluster_json but cluster_id is the classification label."""
    xs, ys, zs, qs, cids = [], [], [], [], []
    for root in mctree:
        for node in collect_nodes(root):
            d = node.get("data", {})
            tx, ty, tz = d.get("traj_x"), d.get("traj_y"), d.get("traj_z")
            if not tx or not ty or not tz:
                continue
            tid = node.get("id", 0)
            label = label_map.get(abs(tid), 6)  # default to Other (6)
            n = len(tx)
            xs.extend(round(v, 2) for v in tx)
            ys.extend(round(v, 2) for v in ty)
            zs.extend(round(v, 2) for v in tz)
            qs.extend([1.0] * n)
            cids.extend([label] * n)
    return {
        "runNo": 0, "subRunNo": 0, "eventNo": int(event_id),
        "geom": geom, "type": "cluster",
        "x": xs, "y": ys, "z": zs, "q": qs, "cluster_id": cids,
    }


def main():
    bee_dir = sys.argv[1] if len(sys.argv) > 1 else "bee"
    truth_file = sys.argv[2] if len(sys.argv) > 2 else None
    data_dir = os.path.join(bee_dir, "data")

    if not os.path.isdir(data_dir):
        print(f"Error: {data_dir} not found. Run the art job with save_mc_json=true first.")
        sys.exit(1)

    event_dirs = sorted(
        d for d in os.listdir(data_dir)
        if os.path.isdir(os.path.join(data_dir, d))
    )
    if not event_dirs:
        print(f"Error: no event subdirectories found in {data_dir}")
        sys.exit(1)

    # Load classification maps if truth file provided
    classification_maps = {}
    if truth_file and os.path.exists(truth_file):
        classification_maps = load_classification_map(truth_file)
        print(f"Loaded classification for {len(classification_maps)} event(s) from {truth_file}")
    elif truth_file:
        print(f"Warning: truth file {truth_file} not found, skipping cluster_class.json")

    print(f"Found {len(event_dirs)} event(s) in {data_dir}")

    for event_id in event_dirs:
        ev_path = os.path.join(data_dir, event_id)
        mc_file = os.path.join(ev_path, f"{event_id}-mc.json")
        if not os.path.exists(mc_file):
            print(f"  [{event_id}] WARNING: {mc_file} not found, skipping")
            continue

        with open(mc_file) as f:
            mctree = json.load(f)

        cluster = make_cluster_json(mctree, event_id)
        with open(os.path.join(ev_path, f"{event_id}-cluster.json"), 'w') as f:
            json.dump(cluster, f)

        # Generate cluster_class.json if classification is available
        label_map = classification_maps.get(event_id)
        if label_map is not None:
            cluster_class = make_cluster_class_json(mctree, event_id, label_map)
            with open(os.path.join(ev_path, f"{event_id}-cluster_class.json"), 'w') as f:
                json.dump(cluster_class, f)
            print(f"  [{event_id}] mc: {len(mctree)} primaries, cluster: {len(cluster['x'])} pts, "
                  f"cluster_class: {len(cluster_class['x'])} pts")
        else:
            print(f"  [{event_id}] mc: {len(mctree)} primaries, cluster: {len(cluster['x'])} pts"
                  f" (no classification available)")

    zip_path = os.path.join(bee_dir, "bee_upload.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for event_id in event_dirs:
            ev_path = os.path.join(data_dir, event_id)
            for fname in sorted(os.listdir(ev_path)):
                if fname.endswith('.json'):
                    zf.write(os.path.join(ev_path, fname),
                             os.path.join("data", event_id, fname))

    print(f"\nBEE zip ready: {zip_path}")
    print(f"Upload with:   bash upload-to-bee.sh {zip_path}")


if __name__ == "__main__":
    main()
