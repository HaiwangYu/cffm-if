#!/bin/bash
# Re-run the SP stage for FD-HD combos after the sp.jsonnet tag fix
# (numbered tight_lf/loose_lf/decon_charge/mp2/mp3 tags for DNN inputs).
set -u
BASE=/exp/dune/app/users/yuhw/cffm-if/smear-dnn
WRAP=/exp/dune/app/users/yuhw/wct-ci/dune/in-sl7-dom.sh
export SETUP_DOM=$BASE/setup-smear-dnn.sh
export WCT_BUILD_DIR=/exp/dune/app/users/yuhw/wct
STATUS=$BASE/status-rerun.txt
note() { echo "$(date '+%m-%d %H:%M:%S') $*" >> $STATUS; }

runsp() { # exp ang
  local d=$BASE/$1/deg$2
  note "START $1/deg$2 (sp tag fix)"
  cat > $d/rerun-sp.sh <<EOI
#!/bin/bash
set -e
export WIRECELL_PATH="/exp/dune/app/users/yuhw/wire-cell-cfg:\$WIRECELL_PATH"
cd $d
rm -f sp.root
lar -n 1 -c sp.fcl -s g4.root >& sp.log
echo DONE
EOI
  chmod +x $d/rerun-sp.sh
  if taskset -c 0-7 $WRAP $d/rerun-sp.sh > $d/rerun-sp.out 2>&1; then
    note "DONE  $1/deg$2 (sp tag fix)"
  else
    note "FAIL  $1/deg$2 (sp tag fix rc=$?)"
  fi
}

i=0
for spec in "dune10kt-1x2x6 00" "dune10kt-1x2x6 45" "dune10kt-1x2x6 80" "dune10kt-1x2x6 85" \
            "dune10kt-hd 00" "dune10kt-hd 45" "dune10kt-hd 80" "dune10kt-hd 85"; do
  runsp $spec

done
wait
note "hd sp rerun end"
