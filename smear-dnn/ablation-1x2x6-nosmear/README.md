# Ablation: dune10kt-1x2x6 truth smearing OFF

Purpose: isolate the effect of the DepoFluxWriter truth smearing added in
the smear-dnn campaign, for dune10kt-1x2x6 at the same 4 muon angles
(0/45/80/85 deg).

## What was changed

The DepoFluxWriter `smear_long` / `smear_tran` were removed so both fall
back to the C++ default of 0 (no extra smearing of the truth SimChannel to
SP resolution).  This is the only difference from the nominal campaign run;
everything else (gen, g4, DNN-ROI reco) is identical.

Diff applied to
`dunereco/dunereco/DUNEWireCell/dune10kt-1x2x6/wcls-sim-drift-simchannel-nf-sp.jsonnet`
(in the `wclsDepoFluxWriter` "postdrift" data block), then reverted after
the run:

```diff
     sparse: false,
-    // Smear the truth SimChannel to reco (SP) resolution ...
-    //   smear_long [ticks] = sigma_t/tick, sigma_t = 1/(2*pi*0.12MHz) = 1.326us
-    //   smear_tran [pitch] = 1/(2*sqrt(pi)*k): Wire_ind k=0.75 (U,V); Wire_col k=3.0 (W)
-    smear_long: 2.6526,
-    smear_tran: [0.37612, 0.37612, 0.09403],
   },
```

## How it was produced

`../run-ablation.sh` reruns only the SP stage (the DepoFluxWriter lives in
the detsim/SP producer, downstream of gen+g4), reusing each nominal
`../../dune10kt-1x2x6/deg<NN>/g4.root` via a symlink.  Plots are made with
`../plot-waveforms2.py` (`--out plots/dune10kt-1x2x6_deg<NN>_nosmear`).

To reproduce: apply the diff above, run `run-ablation.sh` inside SL7 with
`setup-smear-dnn.sh`, then revert the diff.

## Result

The reco `dnnsp` waveform is unchanged vs. the nominal (smearing only
affects the truth label, not reconstruction).  The SimChannel truth is
sharper / taller and no longer follows the deconvolved reco width — e.g.
deg45 plane U peak ~10.3k e (no smear) vs ~6.9k e (nominal smeared).
This confirms the nominal smear_long=2.6526 / smear_tran=[0.376,0.376,0.094]
values are what register the truth onto the SP-resolution reco charge.

Data products (`sp.root`, `*.log`, `plots/*.png`) are git-ignored; only
this README, the per-angle `sp.fcl`, and `../run-ablation.sh` are tracked.
