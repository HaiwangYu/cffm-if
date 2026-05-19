#!/usr/bin/env python3
"""
Visualize particle decay chains from trackid_pid_map.h5

This script reads the HDF5 file containing track_ids, pids, and mother_ids,
builds the decay chain tree, and visualizes it.

Usage:
    python visualize_decay_chain.py [trackid_pid_map.h5]
"""

import h5py
import numpy as np
import sys
from collections import defaultdict

# PDG code to particle name mapping
PDG_NAMES = {
    11: "e-",
    -11: "e+",
    12: "nu_e",
    -12: "anti_nu_e",
    13: "mu-",
    -13: "mu+",
    14: "nu_mu",
    -14: "anti_nu_mu",
    22: "gamma",
    111: "pi0",
    211: "pi+",
    -211: "pi-",
    321: "K+",
    -321: "K-",
    2112: "n",
    2212: "p",
    1000180400: "Ar40",
    1000180390: "Ar39",
    1000180380: "Ar38",
    1000170350: "Cl35",
    1000170370: "Cl37",
}

def get_particle_name(pdg):
    """Convert PDG code to human-readable name."""
    if pdg in PDG_NAMES:
        return PDG_NAMES[pdg]
    elif pdg > 1000000000:
        # Nuclear code: 10LZZZAAAI
        z = (pdg // 10000) % 1000
        a = (pdg // 10) % 1000
        elements = {1: "H", 2: "He", 6: "C", 7: "N", 8: "O",
                    14: "Si", 16: "S", 17: "Cl", 18: "Ar", 19: "K", 20: "Ca"}
        elem = elements.get(z, f"Z{z}")
        return f"{elem}{a}"
    else:
        return f"pdg:{pdg}"


def load_data(filename):
    """Load track data from HDF5 file.

    Supports the two-group structure: {event}/mcpart/ and {event}/simchnl/
    """
    with h5py.File(filename, 'r') as f:
        groups = list(f.keys())
        print(f"Found {len(groups)} event(s): {groups}")

        all_data = {}
        for group in groups:
            mc = f[group]['mcpart']
            sc = f[group]['simchnl']
            all_data[group] = {
                'mcpart': {
                    'track_ids': mc['track_ids'][:],
                    'pids': mc['pids'][:],
                    'mother_ids': mc['mother_ids'][:],
                    'processes': mc['processes'][:],
                    'mother_pids': mc['mother_pids'][:],
                },
                'simchnl': {
                    'track_ids': sc['track_ids'][:],
                    'pids': sc['pids'][:],
                    'mother_ids': sc['mother_ids'][:],
                    'processes': sc['processes'][:],
                    'mother_pids': sc['mother_pids'][:],
                    'energies': sc['energies'][:],
                }
            }
    return all_data


def build_tree(track_ids, pids, mother_ids):
    """Build parent-child relationships using bottom-up approach.

    Special handling for negative track IDs:
    1. If positive counterpart exists in data -> child of positive counterpart
    2. If positive counterpart doesn't exist -> use mother_id
    3. If both don't exist -> orphan

    This function traces each particle upward to find all ancestry relationships,
    ensuring no particles are orphaned unless truly disconnected.
    """
    # Create lookup dictionaries
    track_to_idx = {tid: i for i, tid in enumerate(track_ids)}
    track_to_pid = {tid: pids[i] for i, tid in enumerate(track_ids)}
    track_to_mother = {tid: mother_ids[i] for i, tid in enumerate(track_ids)}

    # Build children map by processing each particle
    children = defaultdict(list)
    roots = set()  # Track all root particles we find

    for tid in track_ids:
        # Special case: negative track IDs
        if tid < 0:
            positive_counterpart = abs(tid)

            # Check if positive counterpart exists
            if positive_counterpart in track_to_pid:
                # Case 1: Positive counterpart exists -> child of it
                children[positive_counterpart].append(tid)
            else:
                # Case 2: Positive counterpart doesn't exist -> use mother_id
                mid = track_to_mother[tid]
                if mid == 0:
                    # This negative track is a root (shouldn't happen but handle it)
                    roots.add(tid)
                else:
                    children[mid].append(tid)
                    # If parent doesn't exist in our data, it becomes a root
                    if mid not in track_to_pid:
                        roots.add(mid)
        else:
            # Positive track ID - use mother_id
            mid = track_to_mother[tid]
            if mid == 0:
                # This is a primary particle
                roots.add(tid)
            else:
                # Add to parent's children
                children[mid].append(tid)
                # If parent doesn't exist in our data, it becomes a root
                if mid not in track_to_pid:
                    roots.add(mid)

    # True primaries are those with mother_id == 0 and positive track ID
    primaries = sorted([tid for tid in roots if tid in track_to_pid and track_to_mother.get(tid, 0) == 0])

    # Pseudo-primaries are roots not in our data (parents that are missing)
    pseudo_primaries = sorted([tid for tid in roots if tid not in track_to_pid])

    return track_to_pid, track_to_mother, children, primaries, pseudo_primaries


def print_tree(tid, track_to_pid, children, indent=0, visited=None, max_depth=10):
    """Recursively print the decay tree."""
    if visited is None:
        visited = set()

    if tid in visited or indent > max_depth:
        return
    visited.add(tid)

    pid = track_to_pid.get(tid, 0)
    name = get_particle_name(pid)

    # Handle negative track IDs (EM shower particles)
    if tid < 0:
        prefix = "  " * indent + "|- "
        print(f"{prefix}[{tid}] {name} (EM shower -> ancestor {abs(tid)})")
    else:
        prefix = "  " * indent + "|- "
        print(f"{prefix}[{tid}] {name}")

    # Print children
    for child in sorted(children.get(tid, [])):
        print_tree(child, track_to_pid, children, indent + 1, visited, max_depth)


def analyze_negative_trackids(track_ids, pids, mother_ids):
    """Analyze negative track IDs and their relationship to ancestors."""
    print("\n" + "="*60)
    print("NEGATIVE TRACK ID ANALYSIS (EM Shower Particles)")
    print("="*60)

    neg_mask = track_ids < 0
    neg_tids = track_ids[neg_mask]
    neg_pids = pids[neg_mask]
    neg_mothers = mother_ids[neg_mask]

    print(f"\nTotal negative track IDs: {len(neg_tids)}")

    if len(neg_tids) == 0:
        return

    # Group by ancestor (abs value)
    ancestor_groups = defaultdict(list)
    for tid, pid, mid in zip(neg_tids, neg_pids, neg_mothers):
        ancestor = abs(tid)
        ancestor_groups[ancestor].append((tid, pid, mid))

    print(f"Unique ancestors: {len(ancestor_groups)}")
    print("\nSample negative track IDs:")
    print(f"{'track_id':>10} | {'pid':>8} | {'name':>10} | {'mother_id':>10} | {'ancestor':>10}")
    print("-" * 60)

    for i, (tid, pid, mid) in enumerate(zip(neg_tids[:20], neg_pids[:20], neg_mothers[:20])):
        name = get_particle_name(pid)
        ancestor = abs(tid)
        print(f"{tid:>10} | {pid:>8} | {name:>10} | {mid:>10} | {ancestor:>10}")

    if len(neg_tids) > 20:
        print(f"... and {len(neg_tids) - 20} more")


def generate_graphviz(track_ids, pids, mother_ids, output_file="decay_chain.dot", max_nodes=500):
    """Generate Graphviz DOT file for visualization.

    Uses the same logic as build_tree() and print_tree() for consistency.
    """
    # Use the same tree-building logic as the printed decay chain
    track_to_pid, track_to_mother, children, primaries, pseudo_primaries = build_tree(
        track_ids, pids, mother_ids
    )

    # Collect all nodes to include (traverse from all roots)
    def collect_descendants(tid, visited, max_depth, current_depth=0):
        """Recursively collect all descendants."""
        if tid in visited or current_depth > max_depth:
            return
        visited.add(tid)
        for child in children.get(tid, []):
            collect_descendants(child, visited, max_depth, current_depth + 1)

    # Collect nodes up to certain depth
    all_nodes = set()
    depth_limit = 50  # Same as print_tree max_depth

    # Collect from primaries
    for primary in primaries:
        collect_descendants(primary, all_nodes, depth_limit)

    # Also collect from pseudo-primaries (missing parents)
    for pseudo in pseudo_primaries:
        all_nodes.add(pseudo)  # Add the pseudo-primary itself
        for child in children.get(pseudo, []):
            collect_descendants(child, all_nodes, depth_limit)

    # Limit nodes if too many
    if len(all_nodes) > max_nodes:
        print(f"\nWarning: Limiting graph to {max_nodes} nodes (out of {len(all_nodes)})")
        # Take first max_nodes by breadth-first traversal from primaries
        limited_nodes = set()
        queue = sorted(primaries)
        while queue and len(limited_nodes) < max_nodes:
            tid = queue.pop(0)
            if tid not in limited_nodes:
                limited_nodes.add(tid)
                queue.extend(sorted(children.get(tid, [])))
        all_nodes = limited_nodes

    with open(output_file, 'w') as f:
        f.write("digraph DecayChain {\n")
        f.write("  rankdir=TB;\n")
        f.write("  node [shape=box, fontsize=10];\n")
        f.write("  edge [fontsize=8];\n\n")

        # Define node colors by particle type
        f.write("  // Color scheme: leptons=blue, photons=yellow, hadrons=green, nuclei=gray\n")

        # Add nodes
        for tid in all_nodes:
            pid = track_to_pid.get(tid, 0)

            # Check if this is a pseudo-primary (not in our data)
            if tid not in track_to_pid:
                f.write(f'  "{tid}" [label="{tid}\\n(not in data)", '
                       f'style="dotted,filled", fillcolor="white"];\n')
                continue

            name = get_particle_name(pid)

            # Color based on particle type
            if abs(pid) in [11, 13, 15]:  # Leptons
                color = "lightblue"
            elif pid == 22:  # Photon
                color = "lightyellow"
            elif abs(pid) in [211, 321, 111]:  # Mesons
                color = "palegreen"
            elif abs(pid) in [2112, 2212]:  # Nucleons
                color = "lightcoral"
            elif pid > 1000000000:  # Nuclei
                color = "lightgray"
            else:
                color = "white"

            # Special style for negative track IDs
            if tid < 0:
                f.write(f'  "{tid}" [label="{tid}\\n{name}\\n(EM shower)", '
                       f'style="filled,dashed", fillcolor="{color}"];\n')
            else:
                f.write(f'  "{tid}" [label="{tid}\\n{name}", '
                       f'style=filled, fillcolor="{color}"];\n')

        f.write("\n  // Edges (based on children map from build_tree)\n")

        # Add edges based on the children dictionary (same as print_tree)
        for parent_tid in all_nodes:
            for child_tid in sorted(children.get(parent_tid, [])):
                if child_tid in all_nodes:
                    f.write(f'  "{parent_tid}" -> "{child_tid}";\n')

        f.write("}\n")

    print(f"\nGraphviz DOT file written to: {output_file}")
    print("To generate PNG: dot -Tpng {output_file} -o decay_chain.png")
    print("To generate SVG: dot -Tsvg {output_file} -o decay_chain.svg")


def print_primary_summary(track_ids, pids, mother_ids):
    """Print summary of all primary particles."""
    print("\n" + "="*60)
    print("PRIMARY PARTICLE SUMMARY")
    print("="*60)

    # Find all primaries (mother_id = 0 AND positive track ID)
    # Negative track IDs are children of their positive counterpart, not primaries
    primary_mask = (mother_ids == 0) & (track_ids > 0)
    primary_tids = track_ids[primary_mask]
    primary_pids = pids[primary_mask]

    print(f"\nTotal primary particles: {len(primary_tids)}")
    print("\nNote: Negative track IDs are children of the positive track ID")
    print("      with the same absolute value (EM shower particles).")

    print(f"\n{'Track ID':>10} | {'PDG':>12} | {'Particle Name':>15}")
    print("-" * 60)

    # Sort by track ID for easier reading
    sorted_indices = np.argsort(primary_tids)
    for idx in sorted_indices:
        tid = primary_tids[idx]
        pid = primary_pids[idx]
        name = get_particle_name(pid)
        print(f"{tid:>10} | {pid:>12} | {name:>15}")


def print_statistics(track_ids, pids, mother_ids):
    """Print summary statistics."""
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)

    print(f"\nTotal tracks: {len(track_ids)}")
    print(f"  Positive track IDs: {np.sum(track_ids > 0)}")
    print(f"  Negative track IDs: {np.sum(track_ids < 0)} (EM shower particles)")

    # Count primaries (only positive track IDs with mother_id=0)
    primaries = np.sum((mother_ids == 0) & (track_ids > 0))
    print(f"\nPrimaries (mother_id=0, positive track ID): {primaries}")

    # Particle type breakdown
    print("\nParticle types:")
    unique_pids, counts = np.unique(pids, return_counts=True)
    sorted_idx = np.argsort(-counts)
    for idx in sorted_idx[:15]:
        pid = unique_pids[idx]
        count = counts[idx]
        name = get_particle_name(pid)
        print(f"  {name:>15} (pdg={pid:>12}): {count:>5}")
    if len(unique_pids) > 15:
        print(f"  ... and {len(unique_pids) - 15} more particle types")


# Process code → name mapping from TrackIDPIDMap2h5.cxx (s_process_map).
# -1 is the fallback assigned when the G4 process name is not in that map.
PROCESS_NAMES = {
    0:  "primary",
    1:  "Decay",
    2:  "eIoni",
    3:  "muIoni",
    4:  "eBrem",
    5:  "compt",
    6:  "phot",
    7:  "conv",
    8:  "hIoni",
    9:  "nCapture",
    10: "muPairProd",
    11: "CoulombScat",
    12: "muBrems",
    13: "LowEnConversion",
    14: "annihil",
    -1: "unset",
}


def generate_graphviz_compact(track_ids, pids, mother_ids, output_file="decay_chain_compact.dot",
                              graph_title=None, collapse_em=True,
                              processes=None, energies=None):
    """Generate a compact Graphviz DOT file.

    Improvements over generate_graphviz():
    - Collapses nuclear recoil leaves (Ar, Cl, S, ...) into a summary label on parent
    - Collapses EM shower particles (negative track IDs) into a summary label on ancestor
      (only when collapse_em=True; set False to render negative-ID nodes explicitly)
    - Uses subgraph clusters, one per primary chain, so chains stack vertically
    - rankdir=LR within each cluster for natural left-to-right decay flow
    """
    from collections import Counter, defaultdict

    track_to_pid, track_to_mother, children, primaries, pseudo_primaries = build_tree(
        track_ids, pids, mother_ids
    )

    # Optional per-track lookups
    track_to_process = ({tid: processes[i] for i, tid in enumerate(track_ids)}
                        if processes is not None else {})
    track_to_energy  = ({tid: energies[i]  for i, tid in enumerate(track_ids)}
                        if energies  is not None else {})

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

    def node_color(pid):
        if is_nucleus(pid):            return "lightgray"
        if abs(pid) in [11, 13, 15]:   return "lightblue"
        if pid == 22:                  return "#ffffaa"
        if abs(pid) in [211, 321, 111]: return "palegreen"
        if abs(pid) in [2112, 2212]:   return "lightcoral"
        return "white"

    all_primary_nodes = set()
    for primary in primaries:
        collect_nodes(primary, all_primary_nodes)

    # Classify nodes
    collapsed_nuclei = {t for t in all_primary_nodes if is_collapsible_nucleus(t)}
    em_shower_nodes  = {t for t in all_primary_nodes if t < 0} if collapse_em else set()
    render_nodes     = all_primary_nodes - collapsed_nuclei - em_shower_nodes

    # Build per-node annotation summaries
    nucleus_summary = defaultdict(Counter)
    em_summary      = defaultdict(int)
    for tid in collapsed_nuclei:
        nucleus_summary[track_to_mother.get(tid, 0)][get_particle_name(track_to_pid[tid])] += 1
    for tid in em_shower_nodes:
        em_summary[abs(tid)] += 1

    def node_label(tid):
        pid = track_to_pid.get(tid, 0)
        name = get_particle_name(pid)
        lines = [f"{tid}  {name}"]
        # Process name on second line
        if tid in track_to_process:
            proc_code = track_to_process[tid]
            proc_name = PROCESS_NAMES.get(int(proc_code), f"proc:{proc_code}")
            lines.append(proc_name)
        # Energy on third line (simchnl only)
        if tid in track_to_energy:
            lines.append(f"{track_to_energy[tid]:.2f} MeV")
        # Collapsed-child summaries
        if tid in em_summary:
            lines.append(f"+{em_summary[tid]} EM")
        if tid in nucleus_summary:
            for nname, cnt in sorted(nucleus_summary[tid].items()):
                lines.append(f"+{cnt} {nname}")
        return "\\n".join(lines)

    with open(output_file, 'w') as f:
        f.write("digraph DecayChain {\n")
        if graph_title:
            f.write(f'  label="{graph_title}";\n')
            f.write('  labelloc="t"; labeljust="l";\n')
        f.write("  rankdir=LR;\n")
        f.write("  graph [nodesep=0.25, ranksep=0.6, compound=true];\n")
        f.write('  node [shape=box, fontsize=9, margin="0.08,0.04"];\n')
        f.write("  edge [fontsize=7];\n\n")

        # One subgraph cluster per primary chain
        for i, primary in enumerate(sorted(primaries)):
            chain_nodes = set()
            collect_nodes(primary, chain_nodes)
            chain_render = chain_nodes - collapsed_nuclei - em_shower_nodes

            pid = track_to_pid.get(primary, 0)
            chain_label = f"Chain {i+1}: [{primary}] {get_particle_name(pid)}"

            f.write(f'  subgraph cluster_{i} {{\n')
            f.write(f'    label="{chain_label}";\n')
            f.write(f'    style=filled; fillcolor="#f8f8f8";\n')
            f.write(f'    fontsize=10; fontname="bold";\n')

            for tid in sorted(chain_render):
                pid_t = track_to_pid.get(tid, 0)
                label = node_label(tid)
                color = node_color(pid_t)
                # Negative track IDs rendered with dashed border to distinguish EM shower
                style = "filled,dashed" if tid < 0 else "filled"
                f.write(f'    "{tid}" [label="{label}", style="{style}", fillcolor="{color}"];\n')

            f.write("  }\n\n")

        # Edges (within render_nodes only)
        for parent_tid in sorted(render_nodes):
            for child_tid in sorted(children.get(parent_tid, [])):
                if child_tid in render_nodes:
                    f.write(f'  "{parent_tid}" -> "{child_tid}";\n')

        f.write("}\n")

    n_orig = len(all_primary_nodes)
    n_compact = len(render_nodes)
    em_note = f" + {len(em_shower_nodes)} EM shower collapsed" if collapse_em else \
              f" ({len({t for t in all_primary_nodes if t < 0})} EM shower shown as nodes)"
    print(f"\nCompact Graphviz DOT written to: {output_file}")
    print(f"  Nodes: {n_orig} → {n_compact} "
          f"(collapsed {len(collapsed_nuclei)} nuclei{em_note})")


def compare_mcpart_simchnl(mc, sc):
    """Compare mcpart and simchnl groups and print set relationship analysis."""
    from collections import Counter

    mc_ids = mc['track_ids']
    mc_pids = mc['pids']
    sc_ids = sc['track_ids']
    sc_pids = sc['pids']
    sc_energies = sc['energies']

    mc_abs = set(np.abs(mc_ids))
    sc_abs = set(np.abs(sc_ids))
    in_mc_not_sc = mc_abs - sc_abs
    in_sc_not_mc = sc_abs - mc_abs
    in_both = mc_abs & sc_abs

    print("\n" + "="*60)
    print("MCPART vs SIMCHNL COMPARISON")
    print("="*60)
    print(f"\n  mcpart entries : {len(mc_ids)} (unique |track_id|: {len(mc_abs)})")
    print(f"  simchnl entries: {len(sc_ids)} (unique |track_id|: {len(sc_abs)}, "
          f"of which {np.sum(sc_ids < 0)} negative/EM-shower)")
    print(f"\n  Overlap (|id|) : {len(in_both)}")
    print(f"  In mcpart only : {len(in_mc_not_sc)}  <-- not ionizing (e.g. neutrons)")
    print(f"  In simchnl only: {len(in_sc_not_mc)}  (should be 0 if mcpart is superset)")

    if in_sc_not_mc:
        print(f"\n  WARNING: {len(in_sc_not_mc)} simchnl track_ids NOT found in mcpart:")
        mask = np.isin(np.abs(sc_ids), sorted(in_sc_not_mc))
        for sid, spid in zip(sc_ids[mask][:10], sc_pids[mask][:10]):
            print(f"    track_id={sid}, pid={spid} ({get_particle_name(spid)})")

    # Breakdown of mcpart-only particles by PID
    mc_only_pids = []
    mc_abs_set = {abs(x): i for i, x in enumerate(mc_ids)}
    for aid in in_mc_not_sc:
        idx = mc_abs_set[aid]
        mc_only_pids.append(mc_pids[idx])
    pid_counts = Counter(mc_only_pids)
    print(f"\n  mcpart-only particle types:")
    for pid, cnt in sorted(pid_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"    {get_particle_name(pid):>12} (pdg={pid:>12}): {cnt}")

    # SimChnl energy summary
    print(f"\n  simchnl energy summary (MeV deposited per track):")
    print(f"    total deposited: {sc_energies.sum():.2f} MeV")
    print(f"    mean per track : {sc_energies.mean():.2f} MeV")
    print(f"    max single track: {sc_energies.max():.2f} MeV")
    # Top energy depositors
    top_idx = np.argsort(sc_energies)[::-1][:5]
    print(f"    top 5 depositors:")
    for i in top_idx:
        pid = sc_pids[i]
        print(f"      track_id={sc_ids[i]:>7}, pid={pid:>12} ({get_particle_name(pid):>8}), "
              f"energy={sc_energies[i]:.2f} MeV")


def _render_dot(dot_file, png_file):
    """Render a DOT file to PNG using graphviz dot."""
    import subprocess
    try:
        subprocess.run(["dot", "-Tpng", dot_file, "-o", png_file], check=True)
        print(f"  PNG rendered: {png_file}")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  Warning: could not render {dot_file} -> {png_file}: {e}")


def main():
    # Default filename
    filename = "trackid_pid_map.h5"
    if len(sys.argv) > 1:
        filename = sys.argv[1]

    print(f"Loading data from: {filename}")

    try:
        all_data = load_data(filename)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)

    # Process each event
    for event_id, data in all_data.items():
        print(f"\n{'='*60}")
        print(f"EVENT: {event_id}")
        print(f"{'='*60}")

        mc = data['mcpart']
        sc = data['simchnl']

        # Compare the two groups
        compare_mcpart_simchnl(mc, sc)

        # Full analysis runs on mcpart (the complete picture)
        track_ids = mc['track_ids']
        pids = mc['pids']
        mother_ids = mc['mother_ids']

        # Print statistics
        print_statistics(track_ids, pids, mother_ids)

        # Print primary particle summary
        print_primary_summary(track_ids, pids, mother_ids)

        # Analyze negative track IDs
        analyze_negative_trackids(track_ids, pids, mother_ids)

        # Build and print decay tree
        track_to_pid, track_to_mother, children, primaries, pseudo_primaries = build_tree(
            track_ids, pids, mother_ids
        )

        print("\n" + "="*60)
        print("DECAY CHAIN (from primaries, using mcpart)")
        print("="*60)
        print("\nPrimary particles and their descendants:")

        visited = set()
        for primary in sorted(primaries):
            print()
            print_tree(primary, track_to_pid, children, indent=0, visited=visited, max_depth=50)

        # Also print chains from pseudo-primaries (missing parents)
        if pseudo_primaries:
            print("\n" + "="*60)
            print("CHAINS FROM MISSING PARENTS (not in data)")
            print("="*60)
            for pseudo in pseudo_primaries:
                print()
                print(f"|- [{pseudo}] (NOT IN DATA - parent missing)")
                for child in sorted(children.get(pseudo, [])):
                    print_tree(child, track_to_pid, children, indent=1, visited=visited, max_depth=50)

        # Check for orphaned particles (not visited)
        all_track_ids = set(track_ids)
        orphaned = all_track_ids - visited
        if orphaned:
            print(f"\n\nWarning: {len(orphaned)} particles not connected to any chain:")
            print(f"Orphaned track IDs (first 20): {sorted(list(orphaned))[:20]}")
            # Check their mother IDs
            orphaned_list = sorted(list(orphaned))[:10]
            print(f"\nSample orphaned particles:")
            print(f"{'track_id':>10} | {'mother_id':>10} | {'pid':>12} | {'name':>15}")
            print("-" * 60)
            for tid in orphaned_list:
                idx = list(track_ids).index(tid)
                mid = mother_ids[idx]
                pid = pids[idx]
                name = get_particle_name(pid)
                print(f"{tid:>10} | {mid:>10} | {pid:>12} | {name:>15}")

        # Generate Graphviz files (using mcpart)
        dot_file = f"decay_chain_event{event_id}.dot"
        generate_graphviz(track_ids, pids, mother_ids, output_file=dot_file)
        compact_dot_file = f"decay_chain_event{event_id}_compact.dot"
        generate_graphviz_compact(track_ids, pids, mother_ids, output_file=compact_dot_file,
                                  processes=mc['processes'])

        # MCtruth-only compact plot (mcpart, explicit label)
        mcpart_dot = f"decay_chain_event{event_id}_mctruth.dot"
        mcpart_png = f"decay_chain_event{event_id}_mctruth.png"
        generate_graphviz_compact(
            mc['track_ids'], mc['pids'], mc['mother_ids'],
            output_file=mcpart_dot,
            graph_title=f"MCtruth (mcpart) — event {event_id}",
            processes=mc['processes'],
        )
        _render_dot(mcpart_dot, mcpart_png)

        # SimChnl-only compact plot
        simchnl_dot = f"decay_chain_event{event_id}_simchnl.dot"
        simchnl_png = f"decay_chain_event{event_id}_simchnl.png"
        generate_graphviz_compact(
            sc['track_ids'], sc['pids'], sc['mother_ids'],
            output_file=simchnl_dot,
            graph_title=f"SimChannel (simchnl) — event {event_id}",
            collapse_em=False,
            processes=sc['processes'],
            energies=sc['energies'],
        )
        _render_dot(simchnl_dot, simchnl_png)


if __name__ == "__main__":
    main()
