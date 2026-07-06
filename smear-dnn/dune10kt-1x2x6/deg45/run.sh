#!/bin/bash
# gen -> g4 -> detsim(+SP+DNN) for one experiment/angle.
# Run inside SL7 with the smear-dnn env sourced.
set -e
cd "$(dirname "$0")"
lar -n 1 -c gen_45.fcl >& gen.log
lar -n 1 -c standard_g4_dune10kt_1x2x6.fcl -s gen.root -o g4.root >& g4.log
lar -n 1 -c sp.fcl -s g4.root >& sp.log
echo DONE
