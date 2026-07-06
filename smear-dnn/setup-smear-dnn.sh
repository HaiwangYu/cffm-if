# setup-smear-dnn.sh
# Environment for the truth-smearing + 6-channel DNN-ROI campaign
# (dunereco branch smear-dnn).
#
# Source this INSIDE the SL7 apptainer, e.g. via
#   SETUP_DOM=/exp/dune/app/users/yuhw/cffm-if/smear-dnn/setup-smear-dnn.sh \
#     /exp/dune/app/users/yuhw/wct-ci/dune/in-sl7-dom.sh <cmd>
#
# Uses the latest cvmfs dunesw and prepends the LOCAL dunereco source so its
# wirecell_dune.fcl (FHICL_FILE_PATH) and DUNEWireCell jsonnet (WIRECELL_PATH,
# via the wire-cell-cfg symlink tree) override the released ones.  The
# DUNEWireCell content is config-only, so edits take effect with no rebuild.

DUNESW_VERSION="${DUNESW_VERSION:-v10_21_01d00}"
USERREPO=/exp/dune/app/users/yuhw

source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh
setup dunesw "${DUNESW_VERSION}" -q e26:prof

# Local dunereco config overrides (no build needed).
path-prepend "${USERREPO}/wire-cell-cfg" WIRECELL_PATH
path-prepend "${USERREPO}/dunereco/dunereco/DUNEWireCell" FHICL_FILE_PATH

echo "smear-dnn env ready:"
echo "  dunesw         : ${DUNESW_VERSION}"
echo "  local dunereco : ${USERREPO}/dunereco (FHICL_FILE_PATH + WIRECELL_PATH prepended)"
echo "  which lar      : $(command -v lar)"
