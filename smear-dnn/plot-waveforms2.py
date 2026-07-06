#!/usr/bin/env python3
"""Truth-vs-reco comparison plots from an sp.root:

1D: per plane (U/V/W) of the highest-truth-charge APA/CRM, overlay the
    recob::Wire waveform (scaled back to electrons by DIVIDING out the
    wclsFrameSaver frame_scale) and the SimChannel electrons/tick on ONE
    shared y-axis (no auto twin-axis scaling), zoomed to the signal.

2D: per plane of the same APA/CRM, two aligned channel-vs-tick panels
    (reco electrons / truth electrons) with a SHARED color scale; the 1D
    channel is marked.

Run inside SL7 with the smear-dnn env (gallery + PyROOT + matplotlib).

Usage:
  python3 plot-waveforms2.py --exp dune10kt-1x2x6 --file sp.root \
      --wires tpcrawdecoder:dnnsp --simchan tpcrawdecoder:simpleSC \
      --frame-scale 0.005 --out plots/dune10kt-1x2x6_deg00
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


_CHANMAP = None


def load_chanmap(exp):
    """Exact channel -> anode ident map built from the workflow's WCT wires
    file by build-chanmaps.py (channel numbering is NOT a simple arithmetic
    block layout for the VD and PD detectors)."""
    import gzip, json
    global _CHANMAP
    if _CHANMAP is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            f"chanmap-{exp}.json.gz")
        with gzip.open(path, "rt") as fp:
            _CHANMAP = {int(k): v for k, v in json.load(fp).items()}
    return _CHANMAP


def anode_of(exp, ch):
    return load_chanmap(exp).get(ch, -1)


def parse_tag(s):
    parts = s.split(":")
    return parts[0], (parts[1] if len(parts) > 1 else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--file", required=True)
    ap.add_argument("--wires", required=True)
    ap.add_argument("--simchan", required=True)
    ap.add_argument("--frame-scale", type=float, required=True,
                    help="wclsFrameSaver frame_scale used when saving; "
                         "stored samples are DIVIDED by this to get electrons")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    for h in ["gallery/Event.h", "lardataobj/RecoBase/Wire.h",
              "lardataobj/Simulation/SimChannel.h", "canvas/Utilities/InputTag.h"]:
        ROOT.gInterpreter.ProcessLine(f'#include "{h}"')

    fnames = ROOT.vector(ROOT.string)()
    fnames.push_back(args.file)
    ev = ROOT.gallery.Event(fnames)

    wires = ev.getValidHandle[ROOT.vector(ROOT.recob.Wire)](
        ROOT.art.InputTag(*parse_tag(args.wires)))
    scs = ev.getValidHandle[ROOT.vector(ROOT.sim.SimChannel)](
        ROOT.art.InputTag(*parse_tag(args.simchan)))

    # channel -> (view, waveform[electrons])
    wmap = {}
    for w in wires.product():
        sig = np.asarray(w.Signal(), dtype=float)
        if sig.size == 0 or not np.any(sig != 0):
            continue
        wmap[w.Channel()] = (int(w.View()), sig / args.frame_scale)

    # channel -> dict(tdc -> electrons)
    smap = {}
    for sc in scs.product():
        dd = {}
        for pair in sc.TDCIDEMap():
            q = sum(ide.numElectrons for ide in pair.second)
            if q > 0:
                dd[int(pair.first)] = q
        if dd:
            smap[sc.Channel()] = dd

    both = sorted(set(wmap) & set(smap))
    print(f"wires with signal: {len(wmap)}, simchannels: {len(smap)}, overlap: {len(both)}")
    if not both:
        print("ERROR: no overlapping channels", file=sys.stderr)
        sys.exit(1)

    # ── pick the APA/CRM with the highest total truth charge ────────────
    qsum = {}
    for ch, dd in smap.items():
        qsum[anode_of(args.exp, ch)] = qsum.get(anode_of(args.exp, ch), 0.0) + sum(dd.values())
    apa = max(qsum, key=qsum.get)
    print(f"selected APA/CRM {apa} (truth charge {qsum[apa]:.3g} e)")

    apach = [ch for ch in both if anode_of(args.exp, ch) == apa]
    byview = {}
    for ch in apach:
        byview.setdefault(wmap[ch][0], []).append(ch)

    nticks = max(len(w[1]) for w in wmap.values())
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    for view, chans in sorted(byview.items()):
        vname = VIEW_NAMES.get(view, f"view{view}")
        # 1D: highest-truth-charge channel of this plane in the chosen APA
        ch1d = max(chans, key=lambda c: sum(smap[c].values()))
        sig = wmap[ch1d][1]
        tdcs = np.array(sorted(smap[ch1d])); qs = np.array([smap[ch1d][t] for t in tdcs])

        nz = np.nonzero(sig)[0]
        lo = max(0, int(min(nz.min(), tdcs.min())) - 100)
        hi = min(nticks - 1, int(max(nz.max(), tdcs.max())) + 100)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(tdcs, qs, width=1.0, color="r", alpha=0.45,
               label=f"SimChannel {args.simchan}")
        ax.plot(np.arange(len(sig)), sig, "b-", lw=1.0,
                label=f"recob::Wire {args.wires} / frame_scale({args.frame_scale:g})")
        ax.set_xlim(lo, hi)
        ax.set_xlabel("tick (TDC)")
        ax.set_ylabel("electrons / tick")
        ax.legend(loc="upper right", fontsize=9)
        ax.set_title(f"{os.path.basename(args.out)}  plane {vname}  ch {ch1d}  (APA/CRM {apa})")
        fig.tight_layout()
        png = f"{args.out}_{vname}.png"
        fig.savefig(png, dpi=120); plt.close(fig)
        print("wrote", png)

        # ── 2D: this plane of the chosen APA, reco vs truth, shared scale ──
        # channel rows: contiguous range covered by this plane in this APA
        # (include SC-only channels inside the range)
        cmin, cmax = min(chans), max(chans)
        for ch in smap:
            if anode_of(args.exp, ch) == apa and cmin <= ch <= cmax:
                pass  # already inside range
        rows = np.arange(cmin, cmax + 1)
        # tick window: union of signal extents over the plane
        tlo, thi = hi, lo
        for ch in rows:
            if ch in wmap and wmap[ch][0] == view:
                nzc = np.nonzero(wmap[ch][1])[0]
                if nzc.size:
                    tlo = min(tlo, nzc.min()); thi = max(thi, nzc.max())
            if ch in smap:
                tt = list(smap[ch])
                tlo = min(tlo, min(tt)); thi = max(thi, max(tt))
        tlo = max(0, int(tlo) - 50); thi = min(nticks - 1, int(thi) + 50)
        tw = thi - tlo + 1

        reco = np.zeros((rows.size, tw))
        tru = np.zeros((rows.size, tw))
        for i, ch in enumerate(rows):
            if ch in wmap and wmap[ch][0] == view:
                s = wmap[ch][1]
                seg = s[tlo:thi + 1]
                reco[i, :seg.size] = seg
            if ch in smap:
                for t, q in smap[ch].items():
                    if tlo <= t <= thi:
                        tru[i, t - tlo] += q
        vmax = max(reco.max(), tru.max())
        if vmax <= 0:
            vmax = 1.0

        fig, axs = plt.subplots(2, 1, figsize=(11, 8), sharex=True, sharey=True)
        for axp, arr, ttl in ((axs[0], reco, f"recob::Wire {args.wires} / frame_scale"),
                              (axs[1], tru, f"SimChannel {args.simchan}")):
            im = axp.imshow(arr, aspect="auto", origin="lower", cmap="viridis",
                            extent=[tlo, thi, cmin, cmax + 1], vmin=0, vmax=vmax)
            axp.axhline(ch1d + 0.5, color="r", ls="--", lw=0.8, alpha=0.8)
            axp.set_ylabel("channel")
            axp.set_title(ttl, fontsize=10)
        axs[1].set_xlabel("tick (TDC)")
        fig.suptitle(f"{os.path.basename(args.out)}  plane {vname}  APA/CRM {apa} "
                     f"(dashed = 1D ch {ch1d})", fontsize=11)
        cbar = fig.colorbar(im, ax=axs, fraction=0.03, pad=0.02)
        cbar.set_label("electrons / tick")
        png = f"{args.out}_2D_{vname}.png"
        fig.savefig(png, dpi=120); plt.close(fig)
        print("wrote", png)


if __name__ == "__main__":
    main()
