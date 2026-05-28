# MC Truth Data & Pixel Classification Pipeline

This document describes the MC truth information available in `trackid_pid_map.h5`,
how pixel-level classification labels are assigned, and the tools for inspecting
and improving the labelling.

## Data Location

A ready-to-use example with 10 events (DUNE 10kt 1x2x6, GENIE neutrino) lives in:

```
cffm-if/dune10kt-1x2x6/exa_10evts_for_tag/
    trackid_pid_map.h5        # per-particle MC truth (all 10 events)
    pixeldata-anode{0..11}.h5 # per-pixel reco + track IDs (12 anodes x 10 events)
    classify_pixels.py        # assign classification labels
    visualize_decay_chain.py  # diagnostic: decay chain printout
    prepare_bee_upload.py     # package for BEE event display
```

You can work directly in this folder -- no art job needed. The HDF5 files and scripts
are self-contained.

## Overview

The pipeline has two stages:

1. **C++ (art/WCT job)** -- `TrackIDPIDMap2h5` dumps per-particle MC truth and
   `Labelling2D` dumps per-pixel track IDs into HDF5 files.
2. **Python scripts** -- read the HDF5 files, classify particles, assign per-pixel
   labels, and optionally produce BEE visualization output.

```
sp.root  -->  [art job: wcls-labelling2d_sep.fcl]
                |
                +--> trackid_pid_map.h5   (per-particle MC truth)
                +--> pixeldata-anode*.h5  (per-pixel reco + track IDs)
                +--> bee/data/*/          (MC JSON for BEE, optional)
                |
                v
         [classify_pixels.py]    --> writes frame_label_1st/2nd into pixeldata-anode*.h5
         [visualize_decay_chain.py] --> prints decay chain diagnostics
         [prepare_bee_upload.py] --> packages BEE upload zip
```

---

## 1. `trackid_pid_map.h5` -- MC Truth per Particle

Each event is stored under `/<event_id>/` with two groups:

### `/<event_id>/mcpart/` -- All Geant4-tracked particles

Every particle stored by Geant4 (regardless of whether it ionized in the TPC).

| Dataset | Shape | Dtype | Description |
|---------|-------|-------|-------------|
| `track_ids` | (N,) | int32 | Geant4 track ID |
| `pids` | (N,) | int32 | PDG code |
| `mother_ids` | (N,) | int32 | Parent track ID (0 = primary) |
| `mother_pids` | (N,) | int32 | Parent's PDG code |
| `processes` | (N,) | int32 | G4 creation process code (see table below) |
| `start_xyzts` | (N, 4) | float32 | Start position [x, y, z, t] in cm / ns |
| `end_xyzts` | (N, 4) | float32 | End position [x, y, z, t] in cm / ns |
| `start_moms` | (N, 4) | float32 | Start 4-momentum [px, py, pz, E] in GeV |
| `end_moms` | (N, 4) | float32 | End 4-momentum [px, py, pz, E] in GeV |
| `end_processes` | (N,) | int32 | G4 termination process code (*) |
| `statuses` | (N,) | int32 | Generator/G4 status code (1 = tracked) (*) |
| `masses` | (N,) | float32 | PDG mass in GeV (*) |
| `ndaughters` | (N,) | int32 | Number of daughter particles (*) |
| `ntrajpts` | (N,) | int32 | Number of Geant4 trajectory points (*) |
| `labels` | (N,) | int8 | Classification label 0--6 (written by `classify_pixels.py`) |

(*) Extended fields -- only present when `save_extended_mcpart: true` in the WCT config.

### `/<event_id>/simchnl/` -- TPC-ionizing particles only

Particles that deposited ionization energy in the TPC (via SimChannel / ParticleInventoryService).
Includes EM shower daughters that may be absent from `mcpart` when `keepEMShowerDaughters=false`.

| Dataset | Shape | Dtype | Description |
|---------|-------|-------|-------------|
| `track_ids` | (M,) | int32 | Track ID (negative = EM shower daughter) |
| `pids` | (M,) | int32 | PDG code |
| `mother_ids` | (M,) | int32 | Parent track ID |
| `mother_pids` | (M,) | int32 | Parent's PDG code |
| `processes` | (M,) | int32 | G4 creation process code |
| `energies` | (M,) | float32 | Total deposited energy in MeV (summed across all TDCs/channels) |

### G4 Process Code Table

Both `processes` and `end_processes` use this encoding:

| Code | Name | Physics |
|------|------|---------|
| 0 | primary | Neutrino interaction product |
| 1 | Decay | Particle decay (e.g. muon -> Michel e) |
| 2 | eIoni | Electron ionization (delta rays) |
| 3 | muIoni | Muon ionization (delta rays) |
| 4 | eBrem | Electron bremsstrahlung |
| 5 | compt | Compton scattering |
| 6 | phot | Photoelectric effect |
| 7 | conv | Pair production (gamma -> e+e-) |
| 8 | hIoni | Hadron ionization |
| 9 | nCapture | Neutron capture |
| 10 | muPairProd | Muon pair production |
| 11 | CoulombScat | Coulomb scattering |
| 12 | muBrems | Muon bremsstrahlung |
| 13 | LowEnConversion | Low-energy conversion |
| 14 | annihil | Positron annihilation |
| 15 | neutronInelastic | Neutron inelastic |
| 16 | hadElastic | Hadronic elastic |
| 17 | hBertiniCaptureAtRest | Hadron capture at rest |
| 18 | muMinusCaptureAtRest | Muon capture at rest |
| 19 | protonInelastic | Proton inelastic |
| 20 | pi+Inelastic | Pi+ inelastic |
| 21 | pi-Inelastic | Pi- inelastic |
| 22 | PhotonInelastic | Photon-nuclear |
| 23 | CHIPSNuclearCaptureAtRest | Nuclear capture at rest |
| 24 | Transportation | Geant4 boundary crossing |
| 25 | kaon+Inelastic | Kaon+ inelastic |
| 26 | kaon-Inelastic | Kaon- inelastic |
| 27 | kaon0LInelastic | K0L inelastic |
| 28 | ionInelastic | Ion inelastic |
| 29 | Scintillation | Scintillation |
| 30 | ionIoni | Ion ionization |
| 31 | nKiller | Neutron killer (time/energy cut) |
| 32 | StepLimiter | Step limiter |
| 33 | dInelastic | Deuteron inelastic |
| -1 | (unknown) | Not in map |

---

## 2. `pixeldata-anode*.h5` -- Per-Pixel Data

One file per anode (12 anodes for DUNE 10kt 1x2x6). Each event `/<event_id>/` contains:

| Dataset | Shape | Dtype | Description |
|---------|-------|-------|-------------|
| `frame_rebinned_reco` | (Nch, Ntick) | float32 | Reconstructed charge (rebinned) |
| `frame_total_numelectrons` | (Nch, Ntick) | float32 | True ionization electrons |
| `frame_trackid_1st` | (Nch, Ntick) | float32 | Track ID of dominant contributor |
| `frame_trackid_2nd` | (Nch, Ntick) | float32 | Track ID of 2nd contributor |
| `frame_energyfrac_1st` | (Nch, Ntick) | float32 | Energy fraction of 1st contributor |
| `frame_energyfrac_2nd` | (Nch, Ntick) | float32 | Energy fraction of 2nd contributor |
| `frame_label_1st` | (Nch, Ntick) | int8 | Classification label for 1st contributor |
| `frame_label_2nd` | (Nch, Ntick) | int8 | Classification label for 2nd contributor |

`frame_label_1st` and `frame_label_2nd` are written by `classify_pixels.py`.

Typical dimensions: Nch=2560, Ntick=1500.

---

## 3. Classification Labels

| Label | Name | Definition |
|-------|------|------------|
| 0 | Background | No MC hit (track_id == 0) |
| 1 | Track | Extended ionizing particle: mu+/-, pi+/-, p/pbar |
| 2 | Shower | EM shower particle: e+/e-, gamma, pi0 that is shower-seeded |
| 3 | Michel | e+/e- from muon decay |
| 4 | DeltaRay | Ionization electron with a Track-type parent |
| 5 | Blip | Isolated EM deposit (nCapture gamma, hadronic e-, etc.) |
| 6 | Other | Neutrinos, nuclei, neutrons, anything else |

**Shower-seeded** means the particle or one of its ancestors was created by an
EM-shower process (conv, compt, phot, eBrem, annihil, LowEnConversion, etc.) or
has a negative track ID (Geant4's convention for EM shower daughters when
`keepEMShowerDaughters=false`).

---

## 4. Python Scripts

### `classify_pixels.py`

**Purpose**: Assigns classification labels (0--6) to every pixel in the pixeldata
files, and also writes per-particle labels into `trackid_pid_map.h5`.

**This is the main script collaborators should review and improve.**

```bash
python3 classify_pixels.py trackid_pid_map.h5 [pixeldata-anode*.h5 ...]
```

Key functions to review:
- `classify_particle()` -- decides the label for a single track ID
- `build_em_shower_ancestor_set()` -- identifies the EM shower chain
- `is_shower_seeded()` -- checks if a particle belongs to an EM shower

Output:
- Writes `frame_label_1st` / `frame_label_2nd` into each `pixeldata-anode*.h5`
- Writes `labels` dataset into `trackid_pid_map.h5` under `/<event>/mcpart/`
- Prints per-event label statistics to stdout

### `visualize_decay_chain.py`

**Purpose**: Diagnostic tool. Prints the full particle decay chain, mcpart vs simchnl
comparison, and summary statistics for each event.

```bash
python3 visualize_decay_chain.py trackid_pid_map.h5
```

Output:
- mcpart vs simchnl overlap analysis
- Energy deposition summary (top depositors)
- Particle type breakdown
- Decay chain tree (text)

Useful for verifying that classification decisions make physics sense.

### `prepare_bee_upload.py`

**Purpose**: Packages MC truth JSON files (produced by the C++ code) into a zip
for upload to the BEE event display.

```bash
python3 prepare_bee_upload.py bee trackid_pid_map.h5
bash upload-to-bee.sh bee/bee_upload.zip
```

Output:
- `bee/data/<event_id>/<event_id>-cluster.json` (trajectory points for 3D display)
- `bee/data/<event_id>/<event_id>-cluster_class.json` (color-coded by classification label)
- `bee/bee_upload.zip` (ready for upload)

---

## 5. Quick Start

### Working with the example data (no art job needed)

```bash
cd cffm-if/dune10kt-1x2x6/exa_10evts_for_tag/

# 1. Assign pixel labels (modifies pixeldata-anode*.h5 in place)
python3 classify_pixels.py trackid_pid_map.h5

# 2. Inspect decay chains (diagnostic, stdout only)
python3 visualize_decay_chain.py trackid_pid_map.h5

# 3. Prepare BEE upload (optional, needs bee/data/ from art job)
python3 prepare_bee_upload.py bee trackid_pid_map.h5
```

### Regenerating from scratch (requires art environment)

```bash
cd cffm-if/dune10kt-1x2x6/
lar -n 10 -c wcls-labelling2d_sep.fcl -s sp.root
python3 classify_pixels.py trackid_pid_map.h5
```

---

## 6. Python Access Examples

```python
import h5py
import numpy as np

# --- Read MC truth ---
f = h5py.File('trackid_pid_map.h5', 'r')
event = '1'

# All Geant4 particles
mcpart = f[event]['mcpart']
tids      = mcpart['track_ids'][:]      # int32[N]
pdgs      = mcpart['pids'][:]           # PDG codes
mothers   = mcpart['mother_ids'][:]     # parent track ID
procs     = mcpart['processes'][:]      # creation process code
starts    = mcpart['start_xyzts'][:]    # (N, 4) start [x,y,z,t] cm
ends      = mcpart['end_xyzts'][:]      # (N, 4) end [x,y,z,t] cm
start_p   = mcpart['start_moms'][:]     # (N, 4) start [px,py,pz,E] GeV
end_p     = mcpart['end_moms'][:]       # (N, 4) end [px,py,pz,E] GeV
labels    = mcpart['labels'][:]         # int8[N] classification (0-6)

# Extended fields (if save_extended_mcpart was true)
end_procs = mcpart['end_processes'][:]  # termination process code
masses    = mcpart['masses'][:]         # PDG mass in GeV
ndaught   = mcpart['ndaughters'][:]     # number of daughters
ntraj     = mcpart['ntrajpts'][:]       # trajectory point count

# TPC-ionizing particles only
simchnl = f[event]['simchnl']
energies  = simchnl['energies'][:]      # deposited MeV per track

# --- Compute kinetic energy ---
E  = start_p[:, 3]
px, py, pz = start_p[:, 0], start_p[:, 1], start_p[:, 2]
mass = np.sqrt(np.maximum(0, E**2 - px**2 - py**2 - pz**2))
KE_MeV = (E - mass) * 1000.0

# --- Read pixel labels ---
g = h5py.File('pixeldata-anode0.h5', 'r')
reco   = g[event]['frame_rebinned_reco'][:]    # (2560, 1500) reco charge
label1 = g[event]['frame_label_1st'][:]         # (2560, 1500) int8 label
label2 = g[event]['frame_label_2nd'][:]         # (2560, 1500) int8 label
efrac1 = g[event]['frame_energyfrac_1st'][:]    # (2560, 1500) energy fraction
```

---

## 7. How to Improve the Classification

The classification logic lives in `classify_pixels.py`. Key areas to review:

1. **Shower vs Blip boundary**: Currently, "shower-seeded" is determined by whether
   the particle or an ancestor was created by an EM process (conv, compt, phot, eBrem,
   annihil, etc.). Isolated EM deposits that are NOT shower-seeded become Blip.
   The threshold and process list may need tuning.

2. **DeltaRay definition**: Currently requires an ionization process (eIoni/muIoni/hIoni)
   AND a Track-type parent. Some edge cases (e.g., delta rays from proton inelastic)
   may warrant discussion.

3. **Michel electron identification**: Currently matches e+/e- from muon Decay.
   Muon capture products (`muMinusCaptureAtRest`) are currently classified differently.

4. **Energy fraction weighting**: Each pixel has a 1st and 2nd contributor with
   energy fractions. Currently labels are assigned independently. A future option
   could weight or merge labels based on the fractions.

5. **Negative track IDs**: In SimChannel, negative track IDs indicate EM shower
   daughters (from `keepEMShowerDaughters=false`). The absolute value maps to the
   shower parent. This is handled but worth verifying edge cases.
