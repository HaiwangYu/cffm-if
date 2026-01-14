
From Dom:
prodgenie_nu_dune10kt_1x2x6.fcl
standard_{g4,detsim,reco1,reco2}_dune10kt_1x2x6.fcl
standard_g4_dune10kt_1x2x6.fcl

```bash
time lar -n 10 -c prodgenie_nu_dune10kt_1x2x6.fcl -o gen.root >& gen.log
```

```bash
time lar -n 10 -c gen_genie.fcl -o gen.root >& gen.log
time lar -n 10 -c g4.fcl -s gen.root -o g4.root >& g4.log
time lar -n 10 -c wcls_sim_sp.fcl -s g4.root -o sp.root >& sp.log
time lar -n 10 -c wcls-labelling2d.fcl -s sp.root --no-output >& labelling2d.log
```


```bash
lar -n 1 -c eventdump.fcl -s sp.root >& sp.log
python h5plot.py g4-rec.h5 1/frame_dnnsp
python h5plot.py g4-tru.h5 1/frame_current_pid_1st
```


```test
time lar -n 1 -c wcls_sim_sp.fcl -s test3/g4.root -o sp.root >& sp.log
```

jay-dec-18
```bash
time lar -n 1 -c wcls-labelling2d.fcl -s jay-dec-18-sp/monte-carlo-011200-000477_261682_49_1_20251212T205158Z_sp.root --no-output >& labelling2d.log
time lar -n 1 -c wcls-labelling2d.fcl -s test3-2026-01-05-hydra/sp.root --no-output >& labelling2d.log
time lar -n 1 -c wcls-labelling2d.fcl -s jay-jan-12/monte-carlo-011334-000001_270046_1_1_20251224T223325Z_sp.root --no-output >& jay-jan-12/labelling2d.log
python h5plot.py jay-jan-12/g4-rec.h5 1/frame_rebinned_reco 0
```

```bash
time lar -n 1 -c gen_genie.fcl -o test-v10_16_00d00/gen.root >& test-v10_16_00d00/gen.log
time lar -n 1 -c g4.fcl -s test-v10_16_00d00/gen.root -o test-v10_16_00d00/g4.root >& test-v10_16_00d00/g4.log
time lar -n 1 -c wcls_sim_sp.fcl -s g4.root -o test-v10_16_00d00/sp.root >& test-v10_16_00d00/sp.log
time lar -n 1 -c wcls-labelling2d.fcl -s test-v10_16_00d00/sp.root --no-output >& test-v10_16_00d00/labelling2d.log
python h5plot.py test-v10_16_00d00/g4-rec.h5 1/frame_rebinned_reco 0
```