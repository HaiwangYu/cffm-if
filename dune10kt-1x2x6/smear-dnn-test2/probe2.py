import ROOT, gzip, json
ROOT.gROOT.SetBatch(True); ROOT.gErrorIgnoreLevel = ROOT.kError
for h in ["gallery/Event.h", "lardataobj/Simulation/SimChannel.h",
          "lardataobj/RecoBase/Wire.h", "canvas/Utilities/InputTag.h"]:
    ROOT.gInterpreter.ProcessLine(f'#include "{h}"')
cmap = {int(k): v for k, v in json.load(gzip.open("chanmap-dune10kt-1x2x6.json.gz", "rt")).items()}
fn = ROOT.vector(ROOT.string)(); fn.push_back("sp.root")
ev = ROOT.gallery.Event(fn)
ws = ev.getValidHandle[ROOT.vector(ROOT.recob.Wire)](ROOT.art.InputTag("tpcrawdecoder", "dnnsp"))
from collections import Counter
wtot = Counter(); wsig = Counter()
for w in ws.product():
    ap = cmap.get(w.Channel(), -1); v = int(w.View())
    wtot[(ap, v)] += 1
    import numpy as np
    if np.any(np.asarray(w.Signal(), dtype=float) != 0):
        wsig[(ap, v)] += 1
scs = ev.getValidHandle[ROOT.vector(ROOT.sim.SimChannel)](ROOT.art.InputTag("tpcrawdecoder", "simpleSC"))
stot = Counter()
for sc in scs.product():
    dd = sc.TDCIDEMap()
    q = sum(sum(ide.numElectrons for ide in pr.second) for pr in dd)
    if q > 0:
        stot[(cmap.get(sc.Channel(), -1), None)] += 1  # per-anode truth-channel count
sperap = Counter()
for (ap, _), n in stot.items():
    sperap[ap] += n
print("dnnsp channels-with-signal per (anode,view):")
for k in sorted(wsig):
    print(f"  anode {k[0]} view {k[1]}: {wsig[k]} / {wtot[k]}")
print("truth (simpleSC) channels-with-charge per anode:")
for ap in sorted(sperap):
    print(f"  anode {ap}: {sperap[ap]}")
