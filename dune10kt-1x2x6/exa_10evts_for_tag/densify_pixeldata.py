#!/usr/bin/env python3
"""Convert a SPARSE pixeldata-anode*.h5 file into the DENSE layout that
classify_pixels.py expects.

The sparse files (those under a .../sparse/... path) store each frame as a
group:

    {event}/frame_<tag>/coords    (N, 2) int32   -- (channel, tick) indices
    {event}/frame_<tag>/features  (N,)   float32 -- value at each coord

classify_pixels.py instead does `grp['frame_trackid_1st'][:]` and then
`.ravel()` / `.reshape(shape)`, i.e. it requires each `frame_<tag>` to be a
DENSE 2-D dataset of shape (N_channels, N_ticks). This script scatters the
sparse coords/features into dense arrays so the classifier (and any other
dense-format consumer) can read them.

Channel-axis size comes from the companion `channels_<tag>` dataset length.
Tick-axis size is max(tickinfo nticks, observed max tick + 1) so no hits are
clipped. Empty pixels are 0 (classify_pixels treats 0 track-id as "no hit").

The companion scalar/per-channel datasets (channels_*, tickinfo_*) are copied
through unchanged so the dense file remains self-describing.

Usage:
    python3 densify_pixeldata.py <sparse_in.h5> <dense_out.h5>
    python3 densify_pixeldata.py <sparse_in.h5> -o <out_dir>   # auto-name

The input is opened read-only, so it is safe to point at a read-only pnfs path.
"""
import argparse
import os

import h5py
import numpy as np


def dense_shape(group, tag, coords):
    """(n_channels, n_ticks) for frame <tag>, sized to clip nothing."""
    chkey = f"channels_{tag}"
    if chkey in group:
        nchan = int(group[chkey].shape[0])
    else:
        nchan = int(coords[:, 0].max()) + 1 if coords.size else 1

    ntick = 0
    tikey = f"tickinfo_{tag}"
    if tikey in group:
        ti = group[tikey][:]
        if len(ti) >= 2 and ti[1] > 0:
            ntick = int(ti[1])
    if coords.size:
        ntick = max(ntick, int(coords[:, 1].max()) + 1)
    ntick = max(ntick, 1)

    # Guard: if a channel index exceeds the companion-derived width, grow it
    if coords.size:
        nchan = max(nchan, int(coords[:, 0].max()) + 1)
    return nchan, ntick


def densify_frame(group, tag):
    """Scatter sparse frame_<tag> into a dense (n_ch, n_tick) float32 array."""
    fgrp = group[f"frame_{tag}"]
    coords = fgrp["coords"][:]
    features = fgrp["features"][:]

    nchan, ntick = dense_shape(group, tag, coords)
    dense = np.zeros((nchan, ntick), dtype=np.float32)

    if coords.size:
        ch = coords[:, 0].astype(np.int64)
        tk = coords[:, 1].astype(np.int64)
        inside = (ch >= 0) & (ch < nchan) & (tk >= 0) & (tk < ntick)
        # Last write wins on duplicate coords (matches simple scatter semantics).
        dense[ch[inside], tk[inside]] = features[inside].astype(np.float32)
        dropped = int((~inside).sum())
        if dropped:
            print(f"    [{tag}] WARNING: {dropped} hits out of dense bounds, dropped")
    return dense, coords.shape[0]


def frame_tags(group):
    return sorted(k[len("frame_"):] for k in group if k.startswith("frame_"))


def is_sparse_frame(obj):
    return isinstance(obj, h5py.Group) and "coords" in obj and "features" in obj


def convert(in_path, out_path):
    print(f"Densifying: {in_path}\n        ->  {out_path}")
    with h5py.File(in_path, "r") as fin, h5py.File(out_path, "w") as fout:
        # Preserve any root-level attributes.
        for k, v in fin.attrs.items():
            fout.attrs[k] = v

        events = [k for k in fin if isinstance(fin[k], h5py.Group)]
        for ev in events:
            gin = fin[ev]
            gout = fout.create_group(ev)
            tags = frame_tags(gin)
            print(f"  event {ev}: {len(tags)} frames")

            converted = set()
            for tag in tags:
                fname = f"frame_{tag}"
                if not is_sparse_frame(gin[fname]):
                    continue  # already dense or unexpected — handled in copy pass
                dense, nhits = densify_frame(gin, tag)
                gout.create_dataset(fname, data=dense, dtype=np.float32,
                                    compression="gzip", compression_opts=4)
                converted.add(fname)
                print(f"    {fname}: {nhits} hits -> dense {dense.shape}")

            # Copy through everything else unchanged (channels_*, tickinfo_*,
            # and any already-dense frames or other datasets/groups).
            for key in gin:
                if key in converted:
                    continue
                obj = gin[key]
                if is_sparse_frame(obj) and f"frame_{key[len('frame_'):]}" in converted:
                    continue
                gin.copy(key, gout, name=key)


def main():
    ap = argparse.ArgumentParser(
        description="Convert sparse pixeldata-anode*.h5 to dense layout for classify_pixels.py")
    ap.add_argument("infile")
    ap.add_argument("outfile", nargs="?", default=None,
                    help="dense output path (default: auto-named in -o dir)")
    ap.add_argument("-o", "--outdir", default=".",
                    help="directory for auto-named output (default: CWD)")
    args = ap.parse_args()

    if args.outfile:
        out_path = args.outfile
    else:
        base = os.path.basename(args.infile)
        # mark the conversion in the name, drop nothing else
        stem, ext = os.path.splitext(base)
        out_path = os.path.join(args.outdir, f"{stem}_dense{ext}")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    convert(args.infile, out_path)
    print(f"\nDone. Dense file: {out_path}")
    print("Now you can run, e.g.:")
    print(f"  python3 classify_pixels.py <trackid_pid_map.h5> {out_path}")


if __name__ == "__main__":
    main()
