#!/bin/bash
# Core-pool queue runner: up to 8 concurrent jobs, each pinned to ONE core.
# Remaining campaign work:
#   - sp-stage reruns for dune10kt-1x2x6 + dune10kt-hd (sp.jsonnet tag fix)
#     [skipped when sp.root is already newer than the sp.jsonnet fix]
#   - full g4+sp reruns for dune10kt-vd (LArG4Detector geometry fix)
set -u
BASE=/exp/dune/app/users/yuhw/cffm-if/smear-dnn
WRAP=/exp/dune/app/users/yuhw/wct-ci/dune/in-sl7-dom.sh
DWC=/exp/dune/app/users/yuhw/dunereco/dunereco/DUNEWireCell
export SETUP_DOM=$BASE/setup-smear-dnn.sh
export WCT_BUILD_DIR=/exp/dune/app/users/yuhw/wct
STATUS=$BASE/status-rerun.txt
POOL=$BASE/.corepool

note() { echo "$(date '+%m-%d %H:%M:%S') $*" >> $STATUS; }

rm -rf $POOL; mkdir -p $POOL
for c in 0 1 2 3 4 5 6 7; do touch $POOL/$c; done

claim_core() { # echoes core id; blocks until one is free
  while true; do
    for f in $POOL/0 $POOL/1 $POOL/2 $POOL/3 $POOL/4 $POOL/5 $POOL/6 $POOL/7; do
      [ -e "$f" ] || continue
      if mv "$f" "$f.busy" 2>/dev/null; then basename "$f"; return; fi
    done
    sleep 3
  done
}
release_core() { mv "$POOL/$1.busy" "$POOL/$1" 2>/dev/null; }

launch() { # exp ang mode(sp|full)
  local exp=$1 ang=$2 mode=$3
  local d=$BASE/$exp/deg$ang
  local core; core=$(claim_core)
  (
    note "START $exp/deg$ang ($mode, core $core)"
    cat > $d/q-inner.sh <<EOI
#!/bin/bash
set -e
export WIRECELL_PATH="/exp/dune/app/users/yuhw/wire-cell-cfg:\$WIRECELL_PATH"
cd $d
if [ "$mode" = full ]; then
  if ! ( [ -f gen.root ] && grep -q 'status 0' gen.log 2>/dev/null ); then
    lar -n 1 -c gen_${ang}.fcl >& gen.log
  fi
  lar -n 1 -c g4.fcl -s gen.root -o g4.root >& g4.log
fi
rm -f sp.root
lar -n 1 -c sp.fcl -s g4.root >& sp.log
echo DONE
EOI
    chmod +x $d/q-inner.sh
    if taskset -c $core $WRAP $d/q-inner.sh > $d/q.out 2>&1; then
      note "DONE  $exp/deg$ang ($mode)"
    else
      note "FAIL  $exp/deg$ang ($mode rc=$?)"
    fi
    release_core $core
  ) &
}

note "core-pool queue start (8 x 1-core jobs)"

# HD sp reruns, skipping ones already redone after the tag fix
for exp in dune10kt-1x2x6 dune10kt-hd; do
  for ang in 00 45 80 85; do
    d=$BASE/$exp/deg$ang
    if [ -f $d/sp.root ] && [ $d/sp.root -nt $DWC/$exp/sp.jsonnet ] \
       && grep -q 'status 0' $d/sp.log 2>/dev/null; then
      note "SKIP  $exp/deg$ang (sp.root newer than sp.jsonnet fix)"
      continue
    fi
    launch $exp $ang sp
  done
done

# VD full reruns (geometry fix)
for ang in 00 45 80 85; do
  launch dune10kt-vd $ang full
done

wait
note "core-pool queue end"
