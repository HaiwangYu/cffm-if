import ROOT, gzip, json
from collections import Counter
ROOT.gROOT.SetBatch(True); ROOT.gErrorIgnoreLevel=ROOT.kError
for h in ["gallery/Event.h","lardataobj/Simulation/SimChannel.h","canvas/Utilities/InputTag.h"]:
    ROOT.gInterpreter.ProcessLine(f'#include "{h}"')
cmap={int(k):v for k,v in json.load(gzip.open("chanmap-dune10kt-1x2x6.json.gz","rt")).items()}
# view: HD APA 2560 = 800 U + 800 V + 960 W. within-APA offset -> view
def view(ch):
    o=ch%2560
    return 0 if o<800 else (1 if o<1600 else 2)
fn=ROOT.vector(ROOT.string)(); fn.push_back("sp.root")
ev=ROOT.gallery.Event(fn)
scs=ev.getValidHandle[ROOT.vector(ROOT.sim.SimChannel)](ROOT.art.InputTag("tpcrawdecoder","simpleSC"))
c=Counter()
for sc in scs.product():
    q=sum(sum(i.numElectrons for i in pr.second) for pr in sc.TDCIDEMap())
    if q>0: c[(cmap.get(sc.Channel(),-1),view(sc.Channel()))]+=1
print("truth channels-with-charge per (anode,view):")
for k in sorted(c):
    if k[0] in (3,5,7,9): print(f"  anode {k[0]} view {k[1]}: {c[k]}")
