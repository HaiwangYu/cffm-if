#!/bin/bash
# Make waveform overlay plots for every finished combo.
# Run inside SL7 with the smear-dnn env sourced.
set -u
BASE=/exp/dune/app/users/yuhw/cffm-if/smear-dnn

wires_tag() {
  case $1 in
    protodunevd) echo "wclsdatavd:gauss";;
    pdhd)        echo "wclsdatahd:gauss";;
    *)           echo "tpcrawdecoder:dnnsp";;
  esac
}

for exp in dune10kt-1x2x6 dune10kt-hd dune-vd dune10kt-vd protodunevd pdhd; do
  for ang in 00 45 80 85; do
    d=$BASE/$exp/deg$ang
    [ -f $d/sp.root ] || continue
    # skip if plots newer than sp.root
    if [ -d $d/plots ] && [ -n "$(find $d/plots -name '*.png' -newer $d/sp.root 2>/dev/null | head -1)" ]; then
      echo "SKIP $exp/deg$ang (plots up to date)"; continue
    fi
    ( cd $d && python3 $BASE/plot-waveforms.py --file sp.root \
        --wires $(wires_tag $exp) --simchan tpcrawdecoder:simpleSC \
        --out plots/${exp}_deg${ang} ) > $d/plot.log 2>&1 \
      && echo "PLOT OK   $exp/deg$ang" || echo "PLOT FAIL $exp/deg$ang"
  done
done
