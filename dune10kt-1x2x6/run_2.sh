source /cvmfs/dune.opensciencegrid.org/products/dune/setup_dune.sh
setup dunesw v10_04_03d01 -q e26:prof
source /exp/dune/data/users/xning/larsoft/v10_04_04d00/localProducts_larsoft_v10_04_03_e26_prof/setup
mrbsetenv
#mrb i -j 8 #if want to rebuild
mrbslp


#lar -n 1 -c wcls-labelling2d.fcl -s xuyang.root --no-output
lar -n 1 -c wcls-labelling2d_sep.fcl -s sp.root 
#lar -n 1 -c wcls-labelling2d.fcl -s sp.root 
#lar -n 1 -c wcls-labeling2d-per-anode.fcl -s xuyang.root 
#python plot_anode0_frames.py --ch-min-frac 0.45 --ch-max-frac 0.6 --time-min-frac 0.2 --time-max-frac 0.4
