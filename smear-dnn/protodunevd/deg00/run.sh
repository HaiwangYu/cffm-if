#!/bin/bash
# gen -> g4 -> detsim(+SP+DNN) for one experiment/angle.
# Run inside SL7 with the smear-dnn env sourced.
set -e
cd "$(dirname "$0")"
lar -n 1 -c gen_00.fcl >& gen.log
lar -n 1 -c protodunevd_g4_stage1.fcl -s gen.root -o g4_stage1.root >& g4_stage1.log
lar -n 1 -c protodunevd_g4_stage2.fcl -s g4_stage1.root -o g4.root >& g4_stage2.log
lar -n 1 -c sp.fcl -s g4.root >& sp.log
lar -n 1 -c sp2.fcl -s detsim.root >& sp2.log
echo DONE
