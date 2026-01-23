#!/bin/sh

#JSONNET_PATH=$WIRECELL_PATH jsonnet   --ext-str recobwire_tags='["sptpc2d:gauss"]'   --ext-str trace_tags='["gauss"]'   --ext-str summary_tags='[""]'   --ext-str input_mask_tags='["sptpc2d:badmasks"]'   --ext-str output_mask_tags='["bad"]'   wcls-labelling2d.jsonnet -o a.json
JSONNET_PATH=$WIRECELL_PATH jsonnet   --ext-str recobwire_tags='["sptpc2d:gauss"]'   --ext-str trace_tags='["gauss"]'   --ext-str summary_tags='[""]'   --ext-str input_mask_tags='["sptpc2d:badmasks"]'   --ext-str output_mask_tags='["bad"]'   wcls-labeling2d-per-anode.jsonnet -o a.json

source /exp/dune/app/users/jjo/venv/bin/activate
wirecell-pgraph dotify --jpath -1 --no-params a.json flow-simple.pdf
deactivate

