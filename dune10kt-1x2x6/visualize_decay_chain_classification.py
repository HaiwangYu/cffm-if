#!/usr/bin/env python3
"""
Decay chain visualization with particle classification labels and colors.

Same compact graph format as visualize_decay_chain.py, but each node is:
  - Colored by classification (Track/Shower/Michel/DeltaRay/Other)
  - Labeled with classification on a new line below the process name

Classification color scheme:
  Track    -> #aed6f1  (steel blue)
  Shower   -> #f9e79f  (yellow)
  Michel   -> #a9dfbf  (mint green)
  DeltaRay -> #f5cba7  (peach/orange)
  Other    -> #d5d8dc  (gray)

Usage:
    python visualize_decay_chain_classification.py [trackid_pid_map.h5]
"""

import h5py
import sys
import numpy as np
from collections import defaultdict, Counter

# ── Reuse helpers from visualize_decay_chain.py ──────────────────────────────

PDG_NAMES = {
    11: "e-", -11: "e+",
    12: "nu_e", -12: "anti_nu_e",
    13: "mu-", -13: "mu+",
    14: "nu_mu", -14: "anti_nu_mu",
    22: "gamma",
    111: "pi0", 211: "pi+", -211: "pi-",
    321: "K+", -321: "K-",
    2112: "n", 2212: "p",
    1000180400: "Ar40", 1000180390: "Ar39", 1000180380: "Ar38",
    1000170350: "Cl35", 1000170370: "Cl37",
}

PROCESS_NAMES = {
    0: "primary", 1: "Decay", 2: "eIoni", 3: "muIoni", 4: "eBrem",
    5: "compt", 6: "phot", 7: "conv", 8: "hIoni", 9: "nCapture",
    10: "muPairProd", 11: "CoulombScat", 12: "muBrems",
    13: "LowEnConversion", 14: "annihil", -1: "unset",
}

# Classification → fill color
CATEGORY_COLOR = {
    "Track":    "#aed6f1",   # steel blue
    "Shower":   "#f9e79f",   # yellow
    "Michel":   "#a9dfbf",   # mint green
    "DeltaRay": "#f5cba7",   # peach
    "Other":    "#d5d8dc",   # gray
}


def get_particle_name(pdg):
    if pdg in PDG_NAMES:
        return PDG_NAMES[pdg]
    if pdg > 1000000000:
        z = (pdg // 10000) % 1000
        a = (pdg // 10) % 1000
        elements = {1: "H", 2: "He", 6: "C", 7: "N", 8: "O",
                    14: "Si", 16: "S", 17: "Cl", 18: "Ar", 19: "K", 20: "Ca"}
        return f"{elements.get(z, f'Z{z}')}{a}"
    return f"pdg:{pdg}"


# ── Classification (same logic as classify_and_dump_json.py) ─────────────────

_TRACK_PDGS = {13, -13, 15, -15, 211, -211, 321, -321, 2212, -2212,
               2112, 130, 310, 3122, 3112, 3222, 3312, 3334,
               1000010020, 1000010030, 1000020030, 1000020040}
_IONIZATION_PROCESSES = {2, 3, 8}   # eIoni, muIoni, hIoni


def classify_all(track_ids, pids, processes, mother_pids):
    tid_to_pid     = {tid: pids[i]          for i, tid in enumerate(track_ids)}
    tid_to_proc    = {tid: int(processes[i]) for i, tid in enumerate(track_ids)}
    tid_to_mothpid = {tid: mother_pids[i]   for i, tid in enumerate(track_ids)}

    result = {}
    for tid in track_ids:
        pid      = int(tid_to_pid.get(tid, 0))
        proc     = tid_to_proc.get(tid, -1)
        moth_pid = int(tid_to_mothpid.get(tid, 0))

        if abs(pid) == 11 and proc == 1 and abs(moth_pid) == 13:
            result[tid] = "Michel"
        elif tid < 0:
            result[tid] = "DeltaRay"
        elif abs(pid) == 11 and proc in _IONIZATION_PROCESSES and abs(moth_pid) in _TRACK_PDGS:
            result[tid] = "DeltaRay"
        elif abs(pid) in _TRACK_PDGS:
            result[tid] = "Track"
        elif abs(pid) in (11, 22, 111):   # pi0 -> shower
            result[tid] = "Shower"
        else:
            result[tid] = "Other"
    return result


# ── Tree building (same as visualize_decay_chain.py) ─────────────────────────

def build_tree(track_ids, pids, mother_ids):
    track_to_pid    = {tid: pids[i]       for i, tid in enumerate(track_ids)}
    track_to_mother = {tid: mother_ids[i] for i, tid in enumerate(track_ids)}
    children = defaultdict(list)
    roots = set()

    for tid in track_ids:
        if tid < 0:
            pos = abs(tid)
            if pos in track_to_pid:
                children[pos].append(tid)
            else:
                mid = track_to_mother[tid]
                if mid == 0:
                    roots.add(tid)
                else:
                    children[mid].append(tid)
                    if mid not in track_to_pid:
                        roots.add(mid)
        else:
            mid = track_to_mother[tid]
            if mid == 0:
                roots.add(tid)
            else:
                children[mid].append(tid)
                if mid not in track_to_pid:
                    roots.add(mid)

    primaries = sorted([t for t in roots
                        if t in track_to_pid and track_to_mother.get(t, 0) == 0])
    pseudo_primaries = sorted([t for t in roots if t not in track_to_pid])
    return track_to_pid, track_to_mother, children, primaries, pseudo_primaries


# ── Classification-colored compact graph ──────────────────────────────────────

def generate_graphviz_classified(track_ids, pids, mother_ids, processes,
                                  categories,
                                  output_file="decay_chain_classified.dot",
                                  graph_title=None, collapse_em=True):
    """Compact decay chain DOT file colored by classification category.

    Same structure as generate_graphviz_compact() but:
    - Node fill color = classification color (not particle-type color)
    - Node label gets an extra line: the classification name
    - Border style: dashed for DeltaRay/negative-tid nodes
    """
    track_to_pid, track_to_mother, children, primaries, pseudo_primaries = build_tree(
        track_ids, pids, mother_ids
    )

    track_to_process = {tid: processes[i] for i, tid in enumerate(track_ids)}

    def is_nucleus(pid):
        return pid > 1000000000

    def collect_nodes(tid, visited, max_depth=50, depth=0):
        if tid in visited or depth > max_depth:
            return
        visited.add(tid)
        for child in children.get(tid, []):
            collect_nodes(child, visited, max_depth, depth + 1)

    def is_collapsible_nucleus(tid):
        if tid not in track_to_pid or not is_nucleus(track_to_pid[tid]):
            return False
        return all(
            k not in track_to_pid or is_nucleus(track_to_pid[k]) or k < 0
            for k in children.get(tid, [])
        )

    all_primary_nodes = set()
    for primary in primaries:
        collect_nodes(primary, all_primary_nodes)

    collapsed_nuclei = {t for t in all_primary_nodes if is_collapsible_nucleus(t)}
    em_shower_nodes  = {t for t in all_primary_nodes if t < 0} if collapse_em else set()
    render_nodes     = all_primary_nodes - collapsed_nuclei - em_shower_nodes

    # Summaries for collapsed children
    nucleus_summary = defaultdict(Counter)
    em_summary      = defaultdict(int)
    for tid in collapsed_nuclei:
        nucleus_summary[track_to_mother.get(tid, 0)][get_particle_name(track_to_pid[tid])] += 1
    for tid in em_shower_nodes:
        em_summary[abs(tid)] += 1

    def node_label(tid):
        pid  = track_to_pid.get(tid, 0)
        name = get_particle_name(pid)
        cat  = categories.get(tid, "Other")
        lines = [f"{tid}  {name}"]
        # Process name
        if tid in track_to_process:
            proc_code = track_to_process[tid]
            proc_name = PROCESS_NAMES.get(int(proc_code), f"proc:{proc_code}")
            lines.append(proc_name)
        # Classification label
        lines.append(f"[{cat}]")
        # Collapsed-child summaries
        if tid in em_summary:
            lines.append(f"+{em_summary[tid]} EM")
        if tid in nucleus_summary:
            for nname, cnt in sorted(nucleus_summary[tid].items()):
                lines.append(f"+{cnt} {nname}")
        return "\\n".join(lines)

    def node_style(tid):
        cat = categories.get(tid, "Other")
        color = CATEGORY_COLOR.get(cat, "#d5d8dc")
        # Dashed border for DeltaRay or negative tid
        border = "filled,dashed" if (tid < 0 or cat == "DeltaRay") else "filled"
        return color, border

    with open(output_file, 'w') as f:
        f.write("digraph DecayChain {\n")
        if graph_title:
            f.write(f'  label="{graph_title}";\n')
            f.write('  labelloc="t"; labeljust="l";\n')
        f.write("  rankdir=LR;\n")
        f.write("  graph [nodesep=0.25, ranksep=0.6, compound=true];\n")
        f.write('  node [shape=box, fontsize=9, margin="0.08,0.04"];\n')
        f.write("  edge [fontsize=7];\n\n")

        # Legend
        f.write('  subgraph cluster_legend {\n')
        f.write('    label="Legend"; style=filled; fillcolor="white"; fontsize=9;\n')
        for cat, color in CATEGORY_COLOR.items():
            f.write(f'    "legend_{cat}" [label="{cat}", style=filled, '
                    f'fillcolor="{color}", fontsize=8];\n')
        f.write('  }\n\n')

        # One subgraph per primary chain
        for i, primary in enumerate(sorted(primaries)):
            chain_nodes = set()
            collect_nodes(primary, chain_nodes)
            chain_render = chain_nodes - collapsed_nuclei - em_shower_nodes

            pid = track_to_pid.get(primary, 0)
            cat = categories.get(primary, "Other")
            chain_label = f"Chain {i+1}: [{primary}] {get_particle_name(pid)} [{cat}]"

            f.write(f'  subgraph cluster_{i} {{\n')
            f.write(f'    label="{chain_label}";\n')
            f.write(f'    style=filled; fillcolor="#f8f8f8";\n')
            f.write(f'    fontsize=10;\n')

            for tid in sorted(chain_render):
                label = node_label(tid)
                color, border = node_style(tid)
                f.write(f'    "{tid}" [label="{label}", style="{border}", '
                        f'fillcolor="{color}"];\n')

            f.write("  }\n\n")

        # Edges
        for parent_tid in sorted(render_nodes):
            for child_tid in sorted(children.get(parent_tid, [])):
                if child_tid in render_nodes:
                    f.write(f'  "{parent_tid}" -> "{child_tid}";\n')

        f.write("}\n")

    n_orig    = len(all_primary_nodes)
    n_compact = len(render_nodes)
    em_note   = (f" + {len(em_shower_nodes)} EM collapsed" if collapse_em
                 else f" ({len({t for t in all_primary_nodes if t < 0})} EM shown)")
    print(f"DOT written: {output_file}")
    print(f"  Nodes: {n_orig} -> {n_compact} "
          f"(collapsed {len(collapsed_nuclei)} nuclei{em_note})")


def _render_dot(dot_file, out_file):
    import subprocess
    ext = out_file.rsplit('.', 1)[-1]
    try:
        subprocess.run(["dot", f"-T{ext}", dot_file, "-o", out_file], check=True)
        print(f"  Rendered: {out_file}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  Warning: could not render {dot_file}: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    filename = sys.argv[1] if len(sys.argv) > 1 else "trackid_pid_map.h5"
    print(f"Loading: {filename}")

    with h5py.File(filename, 'r') as f:
        groups = list(f.keys())
        print(f"Found {len(groups)} event(s): {groups}")
        all_data = {}
        for grp in groups:
            mc = f[grp]['mcpart']
            all_data[grp] = {
                'track_ids':   mc['track_ids'][:],
                'pids':        mc['pids'][:],
                'mother_ids':  mc['mother_ids'][:],
                'processes':   mc['processes'][:],
                'mother_pids': mc['mother_pids'][:],
            }

    for event_id, data in all_data.items():
        print(f"\n{'='*60}\nEVENT: {event_id}\n{'='*60}")

        track_ids  = data['track_ids']
        pids       = data['pids']
        mother_ids = data['mother_ids']
        processes  = data['processes']
        mother_pids = data['mother_pids']

        categories = classify_all(track_ids, pids, processes, mother_pids)

        # Summary
        cnt = Counter(categories.values())
        total = len(categories)
        for cat in ("Track", "Shower", "Michel", "DeltaRay", "Other"):
            n = cnt.get(cat, 0)
            print(f"  {cat:<10}: {n:>4}  ({100*n/total:.1f}%)")

        dot_file = f"decay_chain_classified_event{event_id}.dot"
        png_file = f"decay_chain_classified_event{event_id}.png"

        generate_graphviz_classified(
            track_ids, pids, mother_ids, processes,
            categories,
            output_file=dot_file,
            graph_title=f"MC decay chain with classification — event {event_id}",
            collapse_em=True,
        )
        _render_dot(dot_file, png_file)


if __name__ == "__main__":
    main()
