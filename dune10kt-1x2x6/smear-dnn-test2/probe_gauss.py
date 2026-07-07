import ROOT, gzip, json, numpy as np
from collections import Counter
ROOT.gROOT.SetBatch(True); ROOT.gErrorIgnoreLevel=ROOT.kError
for h in ["gallery/Event.h","lardataobj/RecoBase/Wire.h","canvas/Utilities/InputTag.h"]:
    ROOT.gInterpreter.ProcessLine(f'#include "{h}"')
cmap={int(k):v for k,v in json.load(gzip.open("chanmap-dune10kt-1x2x6.json.gz","rt")).items()}
fn=ROOT.vector(ROOT.string)(); fn.push_back("sp.root")
ev=ROOT.gallery.Event(fn)
# list all recob::Wire instance labels present
print("recob::Wire instances:")
for br in ev.getValidHandle[ROOT.vector(ROOT.recob.Wire)] and []: pass
for tag in ["gauss","wiener","dnnsp"]:
    try:
        ws=ev.getValidHandle[ROOT.vector(ROOT.recob.Wire)](ROOT.art.InputTag("tpcrawdecoder",tag))
        sig=Counter()
        for w in ws.product():
            if np.any(np.asarray(w.Signal(),dtype=float)!=0):
                sig[int(w.View())]+=1
        print(f"  tag={tag}: signal channels per view = {dict(sorted(sig.items()))}")
    except Exception as e:
        print(f"  tag={tag}: {e}")
