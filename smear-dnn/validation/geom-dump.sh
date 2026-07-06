#!/bin/bash
# Dump the geometry (TPC bounds) used by each standard workflow.
# Run inside SL7 with smear-dnn env.
set -u
OUT=/exp/dune/app/users/yuhw/cffm-if/smear-dnn/geom
mkdir -p $OUT
cd $OUT

# 1) which GDML does each standard g4 fcl use?
for spec in \
  "dune10kt-1x2x6:standard_g4_dune10kt_1x2x6.fcl" \
  "dune10kt-hd:standard_g4_dune10kt.fcl" \
  "dune-vd:standard_g4_dunevd10kt_1x8x14_3view_30deg.fcl" \
  "dune10kt-vd:standard_g4_dunevd10kt.fcl" \
  "protodunevd:standard_g4_protodunevd.fcl" \
  "pdhd:standard_g4_protodunehd.fcl" ; do
  name=${spec%%:*}; fcl=${spec#*:}
  gdml=$(fhicl-dump -c $fcl 2>/dev/null | grep -m1 '^\s*GDML:' | awk '{print $2}')
  echo "GDML $name $fcl -> ${gdml:-DUMP_FAILED}"
done
