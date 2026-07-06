#!/usr/bin/env python3
"""Build exact channel -> anode-ident maps from the WCT wires files each
workflow actually loaded (see sp.log).  Output: chanmap-<exp>.json.gz with
{"channel": anode_ident} (string keys)."""
import bz2, gzip, json, os

CFG = "/cvmfs/dune.opensciencegrid.org/products/dune/dunereco/v10_21_01d00/wire-cell-cfg"
FILES = {
    "dune10kt-1x2x6": f"{CFG}/dune10kt-1x2x6-wires-larsoft-v1.json.bz2",
    "dune10kt-hd":    f"{CFG}/dune10kt_v7_refactored.json.bz2",
    "dune-vd":        f"{CFG}/dunevd10kt_3view_30deg_v7_refactored_1x8x14.json.bz2",
    "dune10kt-vd":    f"{CFG}/dunevd10kt_3view_30deg_v6_refactored.json.bz2",
    "protodunevd":    f"{CFG}/protodunevd-wires-larsoft-v5.json.bz2",
    "pdhd":           f"{CFG}/protodunehd-wires-larsoft-v1.json.bz2",
}

OUT = os.path.dirname(os.path.abspath(__file__))

for exp, path in FILES.items():
    d = json.load(bz2.open(path))["Store"]
    anodes, faces, planes, wires = d["anodes"], d["faces"], d["planes"], d["wires"]
    cmap = {}
    for an in anodes:
        a = an["Anode"]
        ident = a["ident"]
        for fi in a["faces"]:
            if fi is None:
                continue
            f = faces[fi]["Face"]
            for ip in f["planes"]:
                for wi in planes[ip]["Plane"]["wires"]:
                    cmap[str(wires[wi]["Wire"]["channel"])] = ident
    out = os.path.join(OUT, f"chanmap-{exp}.json.gz")
    with gzip.open(out, "wt") as fp:
        json.dump(cmap, fp)
    print(f"{exp}: {len(cmap)} channels, {len(set(cmap.values()))} anodes -> {out}")
