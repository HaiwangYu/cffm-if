#!/usr/bin/env python3
"""Overlay recob::Wire (dnnsp) and sim::SimChannel for the same channel,
one plot per plane (U/V/W), zoomed to the signal region.

Run inside SL7 with the smear-dnn env sourced (needs gallery + PyROOT +
matplotlib).

Usage:
  python3 plot-waveforms.py --file sp.root \
      --wires tpcrawdecoder:dnnsp --simchan tpcrawdecoder:simpleSC \
      --out plots/dune10kt-1x2x6_deg00
"""
import argparse, os, sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import ROOT
ROOT.gROOT.SetBatch(True)
ROOT.gErrorIgnoreLevel = ROOT.kError

VIEW_NAMES = {0: "U", 1: "V", 2: "W", 3: "W(Y)", 4: "X"}


def parse_tag(s):
    parts = s.split(":")
    label = parts[0]
    inst = parts[1] if len(parts) > 1 else ""
    return label, inst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--wires", required=True, help="label:instance of recob::Wire")
    ap.add_argument("--simchan", required=True, help="label:instance of sim::SimChannel")
    ap.add_argument("--out", required=True, help="output png prefix")
    ap.add_argument("--nchan", type=int, default=1, help="channels to plot per plane")
    args = ap.parse_args()

    for h in ["gallery/Event.h", "lardataobj/RecoBase/Wire.h",
              "lardataobj/Simulation/SimChannel.h", "canvas/Utilities/InputTag.h"]:
        ROOT.gInterpreter.ProcessLine(f'#include "{h}"')

    filenames = ROOT.vector(ROOT.string)()
    filenames.push_back(args.file)
    ev = ROOT.gallery.Event(filenames)

    wtag = ROOT.art.InputTag(*parse_tag(args.wires))
    stag = ROOT.art.InputTag(*parse_tag(args.simchan))

    get_wires = ev.getValidHandle[ROOT.vector(ROOT.recob.Wire)]
    get_scs = ev.getValidHandle[ROOT.vector(ROOT.sim.SimChannel)]

    wires = get_wires(wtag)
    scs = get_scs(stag)

    # channel -> (view, np waveform)
    wmap = {}
    for w in wires.product():
        sig = np.asarray(w.Signal(), dtype=float)
        if sig.size == 0 or not np.any(sig != 0):
            continue
        wmap[w.Channel()] = (int(w.View()), sig)

    # channel -> (tdc array, charge array)
    smap = {}
    for sc in scs.product():
        tdcs, qs = [], []
        for pair in sc.TDCIDEMap():
            tdc = pair.first
            q = sum(ide.numElectrons for ide in pair.second)
            if q > 0:
                tdcs.append(tdc); qs.append(q)
        if tdcs:
            smap[sc.Channel()] = (np.asarray(tdcs, float), np.asarray(qs, float))

    print(f"wires with signal: {len(wmap)}, simchannels: {len(smap)}, "
          f"overlap: {len(set(wmap) & set(smap))}")

    # group overlap channels by view
    byview = {}
    for ch in sorted(set(wmap) & set(smap)):
        byview.setdefault(wmap[ch][0], []).append(ch)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    made = 0
    for view, chans in sorted(byview.items()):
        # rank by total SimChannel charge
        chans = sorted(chans, key=lambda c: smap[c][1].sum(), reverse=True)
        for i, ch in enumerate(chans[: args.nchan]):
            vname = VIEW_NAMES.get(view, f"view{view}")
            sig = wmap[ch][1]
            tdcs, qs = smap[ch]

            nz = np.nonzero(sig)[0]
            lo = int(min(nz.min(), tdcs.min())) - 100
            hi = int(max(nz.max(), tdcs.max())) + 100
            lo = max(lo, 0); hi = min(hi, len(sig) - 1 if len(sig) else int(tdcs.max()) + 100)

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(np.arange(len(sig)), sig, "b-", lw=1.0,
                    label=f"recob::Wire {args.wires}")
            ax.set_xlabel("tick (TDC)")
            ax.set_ylabel("wire signal [x frame_scale]", color="b")
            ax.tick_params(axis="y", labelcolor="b")

            ax2 = ax.twinx()
            ax2.bar(tdcs, qs, width=1.0, color="r", alpha=0.45,
                    label=f"SimChannel {args.simchan}")
            ax2.set_ylabel("SimChannel electrons / tick", color="r")
            ax2.tick_params(axis="y", labelcolor="r")

            ax.set_xlim(lo, hi)
            h1, l1 = ax.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            ax.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=9)
            ax.set_title(f"{os.path.basename(args.out)}  plane {vname}  ch {ch}")
            fig.tight_layout()
            suffix = f"_{vname}" + (f"_{i}" if args.nchan > 1 else "")
            png = f"{args.out}{suffix}.png"
            fig.savefig(png, dpi=120)
            plt.close(fig)
            print("wrote", png)
            made += 1
    if made == 0:
        print("ERROR: no overlapping channels with signal found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
