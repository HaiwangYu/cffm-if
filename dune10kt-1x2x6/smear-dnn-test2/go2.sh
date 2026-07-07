#!/bin/bash
set -e
export WIRECELL_PATH="/exp/dune/app/users/yuhw/cffm-if/dune10kt-1x2x6:$WIRECELL_PATH"
export FHICL_FILE_PATH="/exp/dune/app/users/yuhw/cffm-if/dune10kt-1x2x6:$FHICL_FILE_PATH"
cd /exp/dune/app/users/yuhw/cffm-if/dune10kt-1x2x6/smear-dnn-test2
lar -n 1 -c run_dunereco.fcl -s ../test0/g4.root >& sp_dunereco.log
echo "EXIT $?"
