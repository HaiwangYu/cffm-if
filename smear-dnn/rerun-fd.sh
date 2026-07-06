#!/bin/bash
# Rerun pass for the FD combos that failed on DNN tensor-shape issues:
#  - dune-vd, dune10kt-vd: need the chan_pad_multiple WCT patch
#    (WCT_BUILD_DIR local build) + dnnroi_pp chan_pad_multiple: 4
#  - dune10kt-hd: needed dnnroi_pp tick_pad_multiple 128 (jsonnet-only fix)
# Reuses existing gen.root/g4.root when their stage completed.
set -u
BASE=/exp/dune/app/users/yuhw/cffm-if/smear-dnn
WRAP=/exp/dune/app/users/yuhw/wct-ci/dune/in-sl7-dom.sh
export SETUP_DOM=$BASE/setup-smear-dnn.sh
export WCT_BUILD_DIR=/exp/dune/app/users/yuhw/wct
STATUS=$BASE/status-rerun.txt

note() { echo "$(date '+%m-%d %H:%M:%S') $*" >> $STATUS; }

stage_ok() { # log
  [ -f "$1" ] && grep -q 'status 0' "$1"
}

runone() { # exp angle
  local exp=$1 ang=$2
  local d=$BASE/$exp/deg$ang
  note "START $exp/deg$ang"
  # inner script: put the dunereco config tree back in front of wct/cfg,
  # then run only the missing stages.
  cat > $d/rerun-inner.sh <<EOF
#!/bin/bash
set -e
export WIRECELL_PATH="/exp/dune/app/users/yuhw/wire-cell-cfg:\$WIRECELL_PATH"
cd $d
if ! ( [ -f gen.root ] && grep -q 'status 0' gen.log 2>/dev/null ); then
  lar -n 1 -c gen_${ang}.fcl >& gen.log
fi
if ! ( [ -f g4.root ] && grep -q 'status 0' g4.log 2>/dev/null ); then
  lar -n 1 -c \$(grep -o 'lar -n 1 -c [^ ]*' run.sh | sed -n 2p | awk '{print \$5}') -s gen.root -o g4.root >& g4.log
fi
rm -f sp.root
lar -n 1 -c sp.fcl -s g4.root >& sp.log
echo DONE
EOF
  chmod +x $d/rerun-inner.sh
  if $WRAP $d/rerun-inner.sh > $d/rerun.out 2>&1; then
    note "DONE  $exp/deg$ang"
  else
    note "FAIL  $exp/deg$ang (rc=$?)"
  fi
}

: > $STATUS
note "rerun start (WCT_BUILD_DIR=$WCT_BUILD_DIR)"

i=0
for spec in "dune-vd 00" "dune-vd 45" "dune-vd 80" "dune-vd 85" \
            "dune10kt-hd 00" "dune10kt-hd 45" "dune10kt-hd 80" "dune10kt-hd 85"; do
  runone $spec &
  i=$((i+1)); [ $((i % 2)) -eq 0 ] && wait
done
wait

for spec in "dune10kt-vd 00" "dune10kt-vd 45" "dune10kt-vd 80" "dune10kt-vd 85"; do
  runone $spec
done

note "rerun end"
