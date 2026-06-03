time lar -n 10 -c gen_genie.fcl -o gen.root >& gen.log
time lar -n 10 -c g4.fcl -s test3/gen.root -o g4.root >& g4.log
time lar -n 1 -c wcls_sim_sp.fcl -s test3/g4.root -o test3-2026-01-05-hydra/sp.root >& test3-2026-01-05-hydra/sp.log
time lar -n 1 -c wcls-labelling2d.fcl -s sp.root --no-output >& test3-2026-01-05-hydra/labelling2d.log