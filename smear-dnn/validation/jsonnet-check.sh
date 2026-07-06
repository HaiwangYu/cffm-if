#!/bin/bash
# Compile-check the edited DUNEWireCell jsonnets with gojsonnet.
# Run inside SL7 with the smear-dnn env sourced.
set -u
WCCFG=/cvmfs/larsoft.opensciencegrid.org/products/wirecell/v0_37_0/Linux64bit+3.10-2.17-e26-prof/share/wirecell
LOCAL=/exp/dune/app/users/yuhw/wire-cell-cfg
JSONNET=/cvmfs/larsoft.opensciencegrid.org/products/gojsonnet/v0_18_0a/Linux64bit+3.10-2.17-e26/bin/jsonnet
D=/exp/dune/app/users/yuhw/dunereco/dunereco/DUNEWireCell

# superset of ext vars; jsonnet ignores unused ones
CODE=(
  nticks=6000 DL=4.0e-9 DT=8.8e-9 lifetime=10400 efield=0.5 temperature=87
  G4RefTime=-250 driftSpeed=1.60563 response_plane=18.92
  use_hydra=false save_rawdigits=false adc_resolution=12
  Nbit=12 elecGain=14 clock_speed=2.0
)
STR=(
  apa_sparsity=all dnn_model=ts-model/CP49_mobilenetv3.ts engine=Pgrapher
  files_wires=dunevd10kt_3view_v2_refactored_1x8x14ref.json.bz2
  files_fields=dunevd-resp-isoc3views-18d92.json.bz2
  files_noise=dunevd10kt-1x6x6-3view-noise-spectra-v1.json.bz2
  geo_planeid_labels=default
)

run() { # file extra-code...
  local f=$1; shift
  local args=(-J "$LOCAL" -J "$WCCFG")
  for kv in "${CODE[@]}"; do args+=(--ext-code "$kv"); done
  for kv in "${STR[@]}";  do args+=(--ext-str  "$kv"); done
  while [ $# -gt 0 ]; do args+=(--ext-code "$1"); shift; done
  if "$JSONNET" "${args[@]}" "$f" > /dev/null 2> /tmp/jerr.$$; then
     echo "OK    $f ${EXTRA_DESC:-}"
  else
     echo "FAIL  $f ${EXTRA_DESC:-}"
     sed 's/^/      /' /tmp/jerr.$$ | head -8
  fi
  rm -f /tmp/jerr.$$
}

echo "=== PD Task-1 files"
run $D/protodunevd/wcls-sim-drift-simchannel.jsonnet
run $D/protodunevd/wcls-sim-drift-simchannel-splusn.jsonnet
run $D/protodunevd/wcls-sim-drift-y-simchannel.jsonnet
run $D/protodunevd/wcls-sim-drift-depoflux.jsonnet use_dnnroi=false
run $D/pdhd/wcls-sim-drift-simchannel-priorSCE.jsonnet
run $D/pdhd/wcls-sim-drift-simchannel-priorSCE-depoflux.jsonnet

echo "=== FD files (use_dnnroi=false)"
run $D/dune10kt-1x2x6/wcls-sim-drift-simchannel-nf-sp.jsonnet use_dnnroi=false
EXTRA_DESC="(process_crm=full ncrm=112)" ; STR+=(process_crm=full)
run $D/dune-vd/wcls-sim-drift-simchannel-nf-sp.jsonnet use_dnnroi=false ncrm=112
run $D/dune10kt-hd/wcls-sim-drift-simchannel-nf-sp.jsonnet use_dnnroi=false
STR=("${STR[@]/process_crm=full/process_crm=all}")
EXTRA_DESC="(process_crm=all ncrm=320)"
run $D/dune10kt-vd/wcls-sim-drift-simchannel-nf-sp.jsonnet use_dnnroi=false ncrm=320

echo "=== FD files (use_dnnroi=true)"
STR=("${STR[@]/process_crm=all/process_crm=full}")
EXTRA_DESC="(dnnroi on)"
run $D/dune10kt-1x2x6/wcls-sim-drift-simchannel-nf-sp.jsonnet use_dnnroi=true
run $D/dune-vd/wcls-sim-drift-simchannel-nf-sp.jsonnet use_dnnroi=true ncrm=112
run $D/dune10kt-hd/wcls-sim-drift-simchannel-nf-sp.jsonnet use_dnnroi=true
STR=("${STR[@]/process_crm=full/process_crm=all}")
run $D/dune10kt-vd/wcls-sim-drift-simchannel-nf-sp.jsonnet use_dnnroi=true ncrm=320
