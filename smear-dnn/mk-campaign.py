#!/usr/bin/env python3
"""Generate the smear-dnn validation campaign fcls + run scripts.

Per experiment x angle (0/45/80/85 deg between track and Z, in the XZ
plane at central Y): gen_<angle>.fcl -> g4 -> detsim(+SP+DNN) fcls.

Geometry envelopes (cm) extracted from DumpGeometry of the exact
workflow geometries (see geom/):
"""
import os, textwrap

BASE = os.path.dirname(os.path.abspath(__file__))
ANGLES = [0, 45, 80, 85]

# name -> dict
EXPS = {
    "dune10kt-1x2x6": dict(
        env=dict(x=(-363.4, 363.4), y=(-607.8, 607.8), z=(-0.9, 1393.5)),
        g4fcl="standard_g4_dune10kt_1x2x6.fcl",
        geo_override="",
        sp=textwrap.dedent("""\
            #include "standard_detsim_dune10kt_1x2x6.fcl"
            # 6-channel DNN-ROI on (ProtoDUNE-HD model)
            physics.producers.tpcrawdecoder.wcls_main.structs.use_dnnroi: true
            physics.producers.tpcrawdecoder.wcls_main.plugins: ["WireCellPgraph", "WireCellGen","WireCellSio","WireCellSigProc","WireCellRoot","WireCellLarsoft","WireCellTbb","WireCellImg","WireCellPytorch"]
            # TPC only (skip PDS sim)
            physics.simulate: [ rns, tpcrawdecoder ]
            outputs.out1.fileName: "sp.root"
            """),
    ),
    "dune10kt-hd": dict(
        env=dict(x=(-746.0, 746.0), y=(-607.8, 607.8), z=(-0.9, 5808.9)),
        g4fcl="standard_g4_dune10kt.fcl",
        geo_override="",
        sp=textwrap.dedent("""\
            #include "standard_detsim_dune10kt.fcl"
            # 6-channel DNN-ROI on (ProtoDUNE-HD model)
            physics.producers.tpcrawdecoder.wcls_main.structs.use_dnnroi: true
            physics.producers.tpcrawdecoder.wcls_main.plugins: ["WireCellPgraph", "WireCellGen","WireCellSio","WireCellSigProc","WireCellRoot","WireCellLarsoft","WireCellTbb","WireCellImg","WireCellPytorch"]
            # TPC only (skip PDS sim)
            physics.simulate: [ rns, tpcrawdecoder ]
            outputs.out1.fileName: "sp.root"
            """),
    ),
    "dune-vd": dict(
        env=dict(x=(-325.0, 325.1), y=(-672.3, 672.3), z=(0.5, 2091.4)),
        g4fcl="standard_g4_dunevd10kt_1x8x14_3view_30deg.fcl",
        geo_override="",
        sp=textwrap.dedent("""\
            #include "standard_detsim_dunevd10kt_1x8x14_3view_30deg.fcl"
            # 6-channel DNN-ROI on (ProtoDUNE-VD model)
            physics.producers.tpcrawdecoder.wcls_main.structs.use_dnnroi: true
            physics.producers.tpcrawdecoder.wcls_main.plugins: ["WireCellPgraph", "WireCellGen","WireCellSio","WireCellSigProc","WireCellRoot","WireCellLarsoft","WireCellTbb","WireCellImg","WireCellPytorch"]
            # TPC only (dodge the duneopdet WaveformDigitizerSim issue)
            physics.simulate: [ rns, tpcrawdecoder ]
            outputs.out1.fileName: "sp.root"
            """),
    ),
    "dune10kt-vd": dict(
        env=dict(x=(-652.0, 652.2), y=(-672.3, 672.3), z=(0.5, 5976.3)),
        g4fcl="standard_g4_dunevd10kt.fcl",
        # this release has no full-VD geometry preset; configure explicitly
        # (same as the existing dune10kt-vd detsim jobs in wct-ci)
        geo_override=textwrap.dedent("""\
            services.Geometry: {
              GDML: "dunevd10kt_3view_30deg_v6_refactored.gdml"
              Name: "dunevd10kt_3view_30deg_v6_refactored"
              SortingParameters: { SortTPCPDVD: false tool_type: "GeoObjectSorterCRU60D" }
              SurfaceY: 147828
            }
            services.AuxDetGeometry.GDML: "dunevd10kt_3view_30deg_v6_refactored.gdml"
            # Geant4 tracks the LArG4Detector gdml (NOT services.Geometry);
            # without this the muon is stepped through the default HD world
            # and no SimEnergyDeposits are produced.
            services.LArG4Detector: {
              category: "world"
              gdmlFileName_: "dunevd10kt_3view_30deg_v6_refactored.gdml"
              stepLimits: [ 4e-1, 4e-1 ]
              volumeNames: [ "volTPCActive", "volCryostat" ]
            }
            """),
        sp=textwrap.dedent("""\
            #include "standard_detsim_dunevd10kt.fcl"
            # full-VD 320-CRM WCT block with 6-channel DNN-ROI (ProtoDUNE-VD model)
            physics.producers.tpcrawdecoder: @local::dune10kt_vertdrift_sim_nfsp_dnnroi
            # TPC only (dodge the duneopdet WaveformDigitizerSim issue)
            physics.simulate: [ rns, tpcrawdecoder ]
            outputs.out1.fileName: "sp.root"
            GEO_OVERRIDE
            """),
    ),
    "protodunevd": dict(
        env=dict(x=(-341.6, 341.6), y=(-336.4, 336.4), z=(0.6, 298.7)),
        g4fcl="protodunevd_g4_stage1.fcl",
        g4fcl2="protodunevd_g4_stage2.fcl",
        geo_override="",
        sp=textwrap.dedent("""\
            #include "protodunevd_detsim.fcl"
            # TPC only (detsim; truth smearing lives in wirecell_protodunevd_mc)
            physics.simulate: [ rns, tpcrawdecoder ]
            outputs.out1.fileName: "detsim.root"
            """),
        # separate SP+DNN reco stage on detsim output
        sp2=textwrap.dedent("""\
            #include "protodunevd_reco.fcl"
            # NF+SP+DNN-ROI (6-channel) only
            physics.producers.wclsdatavd: @local::protodunevd_nfsp_dnnroi_mc
            physics.reco: [ rns, wclsdatavd ]
            physics.trigger_paths: [ reco ]
            outputs.out1.fileName: "sp.root"
            """),
    ),
    "pdhd": dict(
        env=dict(x=(-371.3, 371.1), y=(-0.0, 607.5), z=(-0.6, 463.1)),
        g4fcl="standard_g4_protodunehd.fcl",
        geo_override="",
        sp=textwrap.dedent("""\
            #include "standard_detsim_protodunehd.fcl"
            # TPC only (detsim; truth smearing lives in wirecell_protodunehdmc)
            physics.simulate: [ rns, tpcrawdecoder ]
            outputs.out1.fileName: "detsim.root"
            """),
        sp2=textwrap.dedent("""\
            #include "standard_reco_protodunehd_MC.fcl"
            # NF+SP+DNN-ROI+L1SP (6-channel) only
            physics.reco: [ wclsdatahd ]
            physics.trigger_paths: [ reco ]
            outputs.out1.fileName: "sp.root"
            """),
    ),
}

GEN_TMPL = """\
#include "{g4fcl}"
# Reuse the workflow g4 services (correct geometry) for the gen stage.
process_name: SinglesGen
source: {{
  module_type: EmptyEvent
  timestampPlugin: {{ plugin_type: "GeneratedEventTimestamp" }}
  maxEvents: 1
  firstRun: 1
  firstEvent: 1
}}
physics: {{
  producers: {{
    rns: {{ module_type: "RandomNumberSaver" }}
    generator: {{
      module_type:           "SingleGen"
      ParticleSelectionMode: "all"
      PadOutVectors:         false
      PDG:                   [ 13 ]
      P0:                    [ 10.0 ]
      SigmaP:                [ 0.0 ]
      PDist:                 "Gaussian"
      X0:                    [ {x0:.1f} ]
      Y0:                    [ {y0:.1f} ]
      Z0:                    [ {z0:.1f} ]
      T0:                    [ 0.0 ]
      SigmaX:                [ 0.0 ]
      SigmaY:                [ 0.0 ]
      SigmaZ:                [ 0.0 ]
      SigmaT:                [ 0.0 ]
      Theta0XZ:              [ {ang:.1f} ]
      Theta0YZ:              [ 0.0 ]
      SigmaThetaXZ:          [ 0.0 ]
      SigmaThetaYZ:          [ 0.0 ]
      PosDist:               "uniform"
      TDist:                 "uniform"
      AngleDist:             "Gaussian"
    }}
  }}
  simulate: [ rns, generator ]
  stream1: [ out1 ]
  trigger_paths: [ simulate ]
  end_paths: [ stream1 ]
}}
outputs: {{
  out1: {{
    module_type: RootOutput
    fileName: "gen.root"
    dataTier: "generated"
    compressionLevel: 1
  }}
}}
services.TFileService.fileName: "gen_hist.root"
# the g4-stage services pin NuRandomService to preDefinedSeed (largeant only);
# the generator needs its own seed
services.NuRandomService: {{ policy: "perEvent" }}
{geo_override}"""

for name, cfg in EXPS.items():
    x, y, z = cfg["env"]["x"], cfg["env"]["y"], cfg["env"]["z"]
    Lx, Lz = x[1]-x[0], z[1]-z[0]
    y0 = 0.5*(y[0]+y[1])
    for ang in ANGLES:
        d = os.path.join(BASE, name, f"deg{ang:02d}")
        os.makedirs(d, exist_ok=True)
        if ang == 0:
            x0 = x[0] + 0.25*Lx     # mid of the low-X drift region
        else:
            x0 = x[0] + 0.05*Lx     # near low-X edge, heading +X +Z
        z0 = z[0] + 0.02*Lz
        with open(os.path.join(d, f"gen_{ang:02d}.fcl"), "w") as f:
            f.write(GEN_TMPL.format(g4fcl=cfg["g4fcl"], x0=x0, y0=y0, z0=z0,
                                    ang=float(ang),
                                    geo_override=cfg["geo_override"]))
        # g4 stage fcl (only needed when geometry must be overridden)
        if cfg["geo_override"]:
            with open(os.path.join(d, "g4.fcl"), "w") as f:
                f.write(f'#include "{cfg["g4fcl"]}"\n' + cfg["geo_override"])
            g4fcl_touse = "g4.fcl"
        else:
            g4fcl_touse = cfg["g4fcl"]
        # sp / detsim stage
        sp = cfg["sp"].replace("GEO_OVERRIDE", cfg["geo_override"])
        with open(os.path.join(d, "sp.fcl"), "w") as f:
            f.write(sp)
        if "sp2" in cfg:
            with open(os.path.join(d, "sp2.fcl"), "w") as f:
                f.write(cfg["sp2"])
        # runner
        lines = [
            "#!/bin/bash",
            "# gen -> g4 -> detsim(+SP+DNN) for one experiment/angle.",
            "# Run inside SL7 with the smear-dnn env sourced.",
            "set -e",
            'cd "$(dirname "$0")"',
            f"lar -n 1 -c gen_{ang:02d}.fcl >& gen.log",
        ]
        if name == "protodunevd":
            lines += [
                f"lar -n 1 -c {cfg['g4fcl']} -s gen.root -o g4_stage1.root >& g4_stage1.log",
                f"lar -n 1 -c {cfg['g4fcl2']} -s g4_stage1.root -o g4.root >& g4_stage2.log",
            ]
        else:
            lines += [
                f"lar -n 1 -c {g4fcl_touse} -s gen.root -o g4.root >& g4.log",
            ]
        lines += ["lar -n 1 -c sp.fcl -s g4.root >& sp.log"]
        if "sp2" in cfg:
            lines += ["lar -n 1 -c sp2.fcl -s detsim.root >& sp2.log"]
        lines += ["echo DONE"]
        rp = os.path.join(d, "run.sh")
        with open(rp, "w") as f:
            f.write("\n".join(lines) + "\n")
        os.chmod(rp, 0o755)
    print(f"{name}: gen/sp fcls + run.sh written for angles {ANGLES}")
