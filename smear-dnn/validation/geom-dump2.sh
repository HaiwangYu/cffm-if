#!/bin/bash
# Dump the LArSoft geometry (TPC bounds) exactly as each standard g4
# workflow sees it: include the workflow fcl, replace physics with
# DumpGeometry.  Run inside SL7 with smear-dnn env.
set -u
OUT=/exp/dune/app/users/yuhw/cffm-if/smear-dnn/geom
mkdir -p $OUT
cd $OUT

dump() { # name g4fcl
  local name=$1 g4=$2
  cat > dump_$name.fcl <<EOF
#include "$g4"
process_name: GeoDump
source: { module_type: EmptyEvent maxEvents: 1 }
physics: {
  analyzers: { geometrydump: { module_type: DumpGeometry outputCategory: "DumpGeometry" } }
  dumpers: [ geometrydump ]
  end_paths: [ dumpers ]
}
outputs: {}
services.message.destinations.GeometryLog: {
  type: file
  filename: "$name-geometry.txt"
  threshold: INFO
  categories: { DumpGeometry: { limit: -1 } default: { limit: 0 } }
}
services.TFileService: { fileName: "/dev/null" }
EOF
  if lar -n 1 -c dump_$name.fcl > $name.log 2>&1; then
    echo "OK  $name  ($(grep -c 'TPC' $name-geometry.txt 2>/dev/null) TPC lines)"
  else
    echo "FAIL $name"; tail -5 $name.log | sed 's/^/     /'
  fi
}

dump dune10kt-1x2x6 standard_g4_dune10kt_1x2x6.fcl
dump dune10kt-hd    standard_g4_dune10kt.fcl
dump dune-vd        standard_g4_dunevd10kt_1x8x14_3view_30deg.fcl
dump dune10kt-vd    standard_g4_dunevd10kt.fcl
dump protodunevd    protodunevd_g4_stage1.fcl
dump pdhd           standard_g4_protodunehd.fcl
