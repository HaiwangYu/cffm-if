#!/bin/bash
# Regenerate ALL 1D + 2D truth-vs-reco plots (plot-waveforms2.py),
# up to 8 concurrent single-core jobs.
# Run inside SL7 with the smear-dnn env sourced.
set -u
BASE=/exp/dune/app/users/yuhw/cffm-if/smear-dnn

meta() { # exp -> "wires_tag frame_scale"
  case $1 in
    protodunevd) echo "wclsdatavd:gauss 0.005";;
    pdhd)        echo "wclsdatahd:gauss 0.001";;
    *)           echo "tpcrawdecoder:dnnsp 0.005";;
  esac
}

i=0
for exp in dune10kt-1x2x6 dune10kt-hd dune-vd dune10kt-vd protodunevd pdhd; do
  read wtag fscale <<< "$(meta $exp)"
  for ang in 00 45 80 85; do
    d=$BASE/$exp/deg$ang
    [ -f $d/sp.root ] || { echo "MISS $exp/deg$ang"; continue; }
    rm -f $d/plots/*.png
    core=$((i % 8)); i=$((i+1))
    (
      cd $d && taskset -c $core python3 $BASE/plot-waveforms2.py \
          --exp $exp --file sp.root --wires $wtag --frame-scale $fscale \
          --simchan tpcrawdecoder:simpleSC \
          --out plots/${exp}_deg${ang} > plot2.log 2>&1 \
        && echo "PLOT OK   $exp/deg$ang" || echo "PLOT FAIL $exp/deg$ang"
    ) &
    [ $((i % 8)) -eq 0 ] && wait
  done
done
wait
echo all done
