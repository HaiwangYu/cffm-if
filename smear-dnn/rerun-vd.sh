#!/bin/bash
# dune10kt-vd rerun after the LArG4Detector geometry fix.
set -u
BASE=/exp/dune/app/users/yuhw/cffm-if/smear-dnn
WRAP=/exp/dune/app/users/yuhw/wct-ci/dune/in-sl7-dom.sh
export SETUP_DOM=$BASE/setup-smear-dnn.sh
export WCT_BUILD_DIR=/exp/dune/app/users/yuhw/wct
STATUS=$BASE/status-rerun.txt
note() { echo "$(date '+%m-%d %H:%M:%S') $*" >> $STATUS; }

for ang in 00 45 80 85; do
  d=$BASE/dune10kt-vd/deg$ang
  note "START dune10kt-vd/deg$ang (geo-fixed)"
  cat > $d/rerun-inner.sh <<EOI
#!/bin/bash
set -e
export WIRECELL_PATH="/exp/dune/app/users/yuhw/wire-cell-cfg:\$WIRECELL_PATH"
cd $d
if ! ( [ -f gen.root ] && grep -q 'status 0' gen.log 2>/dev/null ); then
  lar -n 1 -c gen_${ang}.fcl >& gen.log
fi
lar -n 1 -c g4.fcl -s gen.root -o g4.root >& g4.log
lar -n 1 -c sp.fcl -s g4.root >& sp.log
echo DONE
EOI
  chmod +x $d/rerun-inner.sh
  if taskset -c 0-7 $WRAP $d/rerun-inner.sh > $d/rerun.out 2>&1; then
    note "DONE  dune10kt-vd/deg$ang (geo-fixed)"
  else
    note "FAIL  dune10kt-vd/deg$ang (rc=$?)"
  fi
done
note "vd rerun end"
