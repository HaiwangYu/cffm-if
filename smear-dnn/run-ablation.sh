#!/bin/bash
# Ablation (smear off) SP reruns for dune10kt-1x2x6, 4 jobs x 1 core.
# Reuses the existing g4.root (upstream of the DepoFluxWriter smearing).
set -u
BASE=/exp/dune/app/users/yuhw/cffm-if/smear-dnn
WRAP=/exp/dune/app/users/yuhw/wct-ci/dune/in-sl7-dom.sh
export SETUP_DOM=$BASE/setup-smear-dnn.sh
export WCT_BUILD_DIR=/exp/dune/app/users/yuhw/wct
i=0
for ang in 00 45 80 85; do
  d=$BASE/ablation-1x2x6-nosmear/deg$ang
  core=$((i%8)); i=$((i+1))
  (
    cat > $d/inner.sh <<EOI
#!/bin/bash
set -e
export WIRECELL_PATH="/exp/dune/app/users/yuhw/wire-cell-cfg:\$WIRECELL_PATH"
cd $d
rm -f sp.root
lar -n 1 -c sp.fcl -s g4.root >& sp.log
echo DONE
EOI
    chmod +x $d/inner.sh
    if taskset -c $core $WRAP $d/inner.sh > $d/run.out 2>&1; then echo "OK  deg$ang"; else echo "FAIL deg$ang rc=$?"; fi
  ) &
done
wait
echo all-done
