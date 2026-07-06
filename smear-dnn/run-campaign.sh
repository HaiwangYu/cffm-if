#!/bin/bash
# Queue runner for the smear-dnn validation campaign.
# Runs each <exp>/deg<NN>/run.sh inside the SL7 container, light jobs
# with concurrency 2, heavy full-detector jobs serially.
# Progress -> status.txt
set -u
BASE=/exp/dune/app/users/yuhw/cffm-if/smear-dnn
WRAP=/exp/dune/app/users/yuhw/wct-ci/dune/in-sl7-dom.sh
export SETUP_DOM=$BASE/setup-smear-dnn.sh
STATUS=$BASE/status.txt

note() { echo "$(date '+%m-%d %H:%M:%S') $*" >> $STATUS; }

runone() { # exp angle
  local d=$BASE/$1/deg$2
  if [ -f $d/sp.root ] && grep -q 'status 0' $d/sp.log 2>/dev/null; then
     note "SKIP  $1/deg$2 (sp.root exists)"; return 0
  fi
  note "START $1/deg$2"
  if $WRAP $d/run.sh > $d/run.out 2>&1; then
     note "DONE  $1/deg$2"
  else
     note "FAIL  $1/deg$2 (rc=$?)"
  fi
}

: > $STATUS
note "campaign start"

# light + medium, 2 at a time
LIGHT=(
  "protodunevd 45" "protodunevd 80" "protodunevd 85"
  "pdhd 45" "pdhd 80" "pdhd 85"
  "dune10kt-1x2x6 45" "dune10kt-1x2x6 80" "dune10kt-1x2x6 85"
  "dune-vd 00" "dune-vd 45" "dune-vd 80" "dune-vd 85"
)
i=0
for spec in "${LIGHT[@]}"; do
  runone $spec &
  i=$((i+1))
  if [ $((i % 2)) -eq 0 ]; then wait; fi
done
wait

# heavy full-detector jobs, serial
for spec in "dune10kt-hd 00" "dune10kt-hd 45" "dune10kt-hd 80" "dune10kt-hd 85" \
            "dune10kt-vd 00" "dune10kt-vd 45" "dune10kt-vd 80" "dune10kt-vd 85"; do
  runone $spec
done

note "campaign end"
