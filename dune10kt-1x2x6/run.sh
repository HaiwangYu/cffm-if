time lar -n 10 -c gen_genie.fcl -o gen.root >& gen.log
time lar -n 10 -c g4.fcl -s gen.root -o g4.root >& g4.log
time lar -n 10 -c wcls_sim_sp.fcl -s g4.root -o sp.root >& sp.log
time lar -n 10 -c wcls-labelling2d.fcl -s sp.root --no-output >& labelling2d.log