
From Dom:
prodgenie_nu_dune10kt_1x2x6.fcl
standard_{g4,detsim,reco1,reco2}_dune10kt_1x2x6.fcl

```bash
lar -n 1 -c prodgenie_nu_dune10kt_1x2x6.fcl -o gen.root
lar -n 1 -c standard_g4_dune10kt_1x2x6.fcl -s gen.root -o g4.root
lar -n 1 -c wcls_sim_sp.fcl -s g4.root -o sp.root
lar -n 1 -c wcls-labelling2d.fcl -s sp.root --no-output
```


```bash
python h5plot.py g4-rec.h5 1/frame_gauss
python h5plot.py g4-tru.h5 1/frame_pid
```