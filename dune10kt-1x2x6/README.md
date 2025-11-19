
From Dom:
prodgenie_nu_dune10kt_1x2x6.fcl
standard_{g4,detsim,reco1,reco2}_dune10kt_1x2x6.fcl

```bash
time lar -n 10 -c prodgenie_nu_dune10kt_1x2x6.fcl -o gen.root >& gen.log
```

```bash
time lar -n 10 -c gen_genie.fcl -o gen.root >& gen.log
time lar -n 10 -c g4.fcl -s gen.root -o g4.root >& g4.log
time lar -n 10 -c wcls_sim_sp.fcl -s g4.root -o sp.root >& sp.log
time lar -n 1 -c wcls-labelling2d.fcl -s ref0-dnn-nohydra/sp.root --no-output >& labelling2d.log
```


```bash
lar -n 1 -c eventdump.fcl -s sp.root >& sp.log
python h5plot.py g4-rec.h5 1/frame_dnnsp
python h5plot.py g4-tru.h5 1/frame_current_pid_1st
```