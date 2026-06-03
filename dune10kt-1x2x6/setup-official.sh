exp_name="dune"
local_wirecell_path=/exp/${exp_name}/app/users/$USER/opt

source /cvmfs/${exp_name}.opensciencegrid.org/products/${exp_name}/setup_${exp_name}.sh

setup dunesw v10_16_00d00 -q e26:prof

# larwirecell build
# path-prepend ${local_wirecell_path} CMAKE_PREFIX_PATH


# path-prepend ${local_wirecell_path}/bin PATH
# path-prepend ${local_wirecell_path}/lib64 LD_LIBRARY_PATH
# path-prepend /exp/${exp_name}/app/users/$USER/wct/cfg WIRECELL_PATH

source /nashome/y/$USER/.bash_profile
export PS1=(app)$PS1

source /exp/${exp_name}/app/users/$USER/wire-cell-python/venv/bin/activate

# path-prepend /exp/${exp_name}/app/users/$USER/wire-cell-data WIRECELL_PATH
# path-prepend /exp/${exp_name}/app/users/$USER/wire-cell-cfg WIRECELL_PATH


# path-prepend /exp/${exp_name}/app/users/$USER/dunereco/dunereco/DUNEWireCell/ FHICL_FILE_PATH