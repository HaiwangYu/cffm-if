# Pixel Classification Definition

Based on `classify_pixels.py`. Each pixel in the TPC anode frame carries a
float32 track ID from SimChannel; this is mapped to an integer label using MC
truth from `trackid_pid_map.h5`.

---

## Label Table

| Label | Int | Particles | Condition |
|-------|-----|-----------|-----------|
| Background | 0 | — | `track_id == 0` (no ionization) |
| Track | 1 | μ±, π±, p/p̄ | PDG in `_TRACK_PDGS`, not caught by higher-priority rules |
| Shower | 2 | e±, γ, π⁰ | EM-PDG particle that is shower-seeded (see below) |
| Michel | 3 | e±  | e± from `Decay` of μ± |
| DeltaRay | 4 | any | Created by an ionization process (`eIoni`/`muIoni`/`hIoni`) with a Track-type parent |
| Blip | 5 | e±, γ, π⁰ | EM-PDG particle that is **not** shower-seeded |
| Other | 6 | n, K⁰, nuclei, ν, ... | Anything not matched above |

---

## Classification Priority

Rules are checked in this order; the first match wins:

```
1. Michel
2. DeltaRay
3. Track
4. Shower  ─┐  (both require EM PDG)
5. Blip    ─┘
6. Other
```

---

## PDG and Process Sets

**Track PDGs** (`_TRACK_PDGS`):
μ±(13), π±(211), p/p̄(2212)

**EM-shower PDGs** (`_EM_SHOWER_PDGS`):
e±(11), γ(22), π⁰(111)

**Ionization processes** (`_IONIZATION_PROCESSES`):
`eIoni`(2), `muIoni`(3), `hIoni`(8) — or any process name containing `"Ioni"`

**EM-shower processes** (`_NOT_STORED_PHYSICS`, substring match):
`conv`, `LowEnConversion`, `Pair`, `compt`, `Compt`, `Brem`, `phot`, `Photo`, `annihil`
> `"Ion"` is deliberately excluded so ionization electrons are DeltaRay, not Shower.

---

## Shower-Seeded Definition

A particle is **shower-seeded** if it or any ancestor was created by an
EM-shower process (substring match against `_NOT_STORED_PHYSICS`), or is a
primary EM particle (process=0, PDG in `_EM_SHOWER_PDGS`).

Once a shower root is identified, **all its descendants** (any PDG, any depth)
inherit shower membership. This mirrors the `fNotStoredPhysics` logic in
`ParticleListAction.cc`: G4 collapses the entire sub-tree under a negative
track ID pointing to the root.

---

## G4-Dropped Particles and Negative Track IDs

### Background: what G4 drops

With `keepEMShowerDaughters: false`, G4's `ParticleListAction` uses
`fNotStoredPhysics` (substring match) to drop particles from the MCParticle
list.  The default list is:

```
"conv", "LowEnConversion", "Pair", "compt", "Compt",
"Brem", "phot", "Photo", "Ion", "annihil"
```

**Critically, `"Ion"` matches `eIoni`, `muIoni`, `hIoni`, `ionIoni`** — so
all ionization electrons (delta rays) are also dropped, not just EM shower
daughters.

Dropped particles never appear in the MCParticle vector.  Their energy
deposits in SimChannel carry a **negative `trackID`** =
`-1 * GetParentage(origTrackID)`, pointing to the first stored ancestor.
The `origTrackID` field preserves the real G4 track ID but has no
corresponding MCParticle entry.

### Classification of negative track IDs

In `build_label_frame`, negative tids are resolved via `label_map[abs(tid)]` —
the label of the ancestor particle.  No attempt is made to infer the dropped
particle's own identity (delta ray vs shower daughter), because the negative
trackID alone does not distinguish between the two.

---

## Simple Examples

### Cosmic muon crossing the TPC
```
tid=1  μ⁻  proc=primary  →  Track
```

### Michel electron from muon decay
```
tid=1  μ⁻  proc=primary        →  Track
tid=2  e⁻  proc=Decay  parent=μ⁻  →  Michel   ← caught by rule 1
```

### EM shower from beam electron
```
tid=1  e⁻   proc=primary          →  Shower  (primary EM → shower root)
tid=2  γ    proc=eBrem  parent=e⁻  →  Shower  (descendant of shower root)
tid=3  e⁺   proc=conv   parent=γ   →  Shower
tid=4  e⁻   proc=conv   parent=γ   →  Shower
```
> With `keepEMShowerDaughters=false`, tid=2/3/4 are dropped.  Their energy
> appears as `tid=-1` in SimChannel → inherits label of tid=1 → **Shower**.

### Neutron capture blip
```
tid=10  n    proc=primary           →  Other
tid=11  γ    proc=nCapture parent=n →  Blip    ← EM PDG but not shower-seeded
tid=12  e⁻   proc=phot    parent=γ  →  Shower  ← phot is in _NOT_STORED_PHYSICS → shower root
```
> tid=12 is dropped; energy appears as `tid=-11` → inherits label of tid=11 → **Blip**.

### Delta ray from pion (dropped by G4)
```
tid=5  π⁺  proc=primary            →  Track
tid=6  e⁻  proc=hIoni  parent=π⁺   →  (dropped, "Ion" matches hIoni)
```
> Energy appears as `tid=-5` → inherits label of tid=5 → **Track**.
> Note: this is a real delta ray, but it inherits the parent Track label
> because G4 dropped it before it could be classified individually.

---

## Tricky Cases

### Michel vs DeltaRay: both are e⁻ from a muon

| Particle | Process | Rule hit | Label |
|----------|---------|----------|-------|
| e⁻ from μ⁻ decay | `Decay` (proc=1) | Rule 1 (Michel first) | **Michel** |
| e⁻ knocked off by μ⁻ | `muIoni` (proc=3) | Dropped by G4 | **Track** (inherits μ⁻ label) |

Michel is checked **before** DeltaRay for positive trackIDs.  Ionization
electrons from muons are G4-dropped and arrive only as negative tids;
they inherit the ancestor's label (Track), not DeltaRay.

---

### Shower vs Blip: both are γ not in _TRACK_PDGS

| Particle | Origin | Shower-seeded? | Label |
|----------|--------|---------------|-------|
| γ from `eBrem` (e⁻ radiating) | EM shower | yes | **Shower** |
| γ from `nCapture` (thermal n) | hadronic | no | **Blip** |
| γ from nuclear de-excitation after `hBertiniCaptureAtRest` | hadronic | no | **Blip** |

The process of the γ itself does not have to be an EM-shower process — it is
enough that **any ancestor** is shower-seeded. But a γ born directly from a
hadronic process with no EM-shower ancestor is a Blip.

---

### Shower vs Blip: phot (photoelectric) e⁻ from a Blip γ

```
tid=11  γ    proc=nCapture  parent=n   →  Blip   (not shower-seeded)
tid=12  e⁻   proc=phot      parent=γ   →  Shower ← phot is in _NOT_STORED_PHYSICS → shower root
```

Even though the grandparent is a neutron, `phot` seeds a new shower root at
tid=12. All descendants of tid=12 become Shower. The γ (tid=11) itself remains
Blip because it was classified before its child was processed — the shower root
is tid=12, not tid=11.

> With G4 dropping: tid=12 is dropped (phot matched).  Energy appears as
> `tid=-11` → inherits label of tid=11 → **Blip**.

---

### DeltaRay vs Other: ionization e⁻ from a non-Track parent

```
tid=20  n    proc=primary              →  Other
tid=21  e⁻   proc=hIoni  parent=n(2112)→  (dropped by G4)
```

Energy appears as `tid=-20` → inherits label of tid=20 → **Other**.

For the rare case where tid=21 survives in MCParticle (e.g., custom FCL
without `"Ion"` in `NotStoredPhysics`):
```
tid=21  e⁻  proc=hIoni  parent=n  →  Blip  (EM PDG, not shower-seeded, n not in _TRACK_PDGS)
```

---

### Known limitation: delta rays indistinguishable from parent

With the default `fNotStoredPhysics` including `"Ion"`, all ionization
electrons are dropped and their energy is attributed to the parent via
negative trackID.  In `build_label_frame`, these pixels inherit the parent's
label (e.g., Track for a muon's delta ray).  The DeltaRay classification
rule (rule 2) can only fire for ionization electrons that are **not** dropped
— which requires a custom FCL with `"Ion"` removed from `NotStoredPhysics`,
or `keepEMShowerDaughters: true`.
