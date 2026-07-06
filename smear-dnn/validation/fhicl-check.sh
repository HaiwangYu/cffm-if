#!/bin/bash
# fhicl-dump every detsim entry that consumes an edited wirecell block,
# plus override test-fcls for the new _dnnroi variants.
# Run inside SL7 with the smear-dnn env sourced.
set -u
TD=$(mktemp -d)
trap 'rm -rf $TD' EXIT

check() { # name fclfile
  local name=$1 f=$2
  if fhicl-dump -c "$f" > "$TD/$name.flat" 2> "$TD/$name.err"; then
    # verify the wirecell module config landed with the new components
    echo "OK    $name"
  else
    echo "FAIL  $name"
    head -12 "$TD/$name.err" | sed 's/^/      /'
  fi
}

echo "=== standard detsim entries"
check detsim_1x2x6        standard_detsim_dune10kt_1x2x6.fcl
check detsim_1x8x14_30deg standard_detsim_dunevd10kt_1x8x14_3view_30deg.fcl
check detsim_dune10kt_hd  standard_detsim_dune10kt.fcl
check detsim_dunevd10kt   standard_detsim_dunevd10kt.fcl
check detsim_pdvd         protodunevd_detsim.fcl
check detsim_pdhd         standard_detsim_protodunehd.fcl

echo "=== dnnroi variants + splusn (override test fcls)"
mk() { # name base block [deep]
  local name=$1 base=$2 block=$3 deep=${4:-}
  {
    echo "#include \"$base\""
    if [ -n "$deep" ]; then
      echo "physics.producers.tpcrawdecoder: @local::$block"
    else
      echo "physics.producers.tpcrawdecoder: @local::$block"
    fi
  } > "$TD/$name.fcl"
  ( cd "$TD" && check "$name" "$name.fcl" )
}
mk t_1x2x6_dnnroi  standard_detsim_dune10kt_1x2x6.fcl        dunefd_horizdrift_1x2x6_sim_nfsp_dnnroi
mk t_vd14_dnnroi   standard_detsim_dunevd10kt_1x8x14_3view_30deg.fcl dune10kt_dunefd_vertdrift_1x8x14_3view_sim_nfsp_dnnroi
mk t_hd_dnnroi     standard_detsim_dune10kt.fcl              dune10kt_horizdrift_sim_nfsp_dnnroi
mk t_10ktvd_dnnroi standard_detsim_dunevd10kt.fcl            dune10kt_vertdrift_sim_nfsp_dnnroi
mk t_pdvd_splusn   protodunevd_detsim.fcl                    wirecell_protodunevd_mc_splusn

echo "=== grep sanity: DepoFluxWriter + smear in dumped configs"
for n in detsim_1x2x6 detsim_1x8x14_30deg detsim_dune10kt_hd detsim_dunevd10kt detsim_pdvd detsim_pdhd; do
  [ -f "$TD/$n.flat" ] || continue
  df=$(grep -c 'wclsDepoFluxWriter:postdrift' "$TD/$n.flat" || true)
  sk=$(grep -c 'wclsSimChannelSink:postdrift' "$TD/$n.flat" || true)
  echo "$n: DepoFluxWriter refs=$df SimChannelSink refs=$sk"
done
