local g = import "pgraph.jsonnet";
local f = import "pgrapher/common/funcs.jsonnet";
local wc = import "wirecell.jsonnet";

local tools_maker = import 'pgrapher/common/tools.jsonnet';

local base = import 'pgrapher/experiment/protodunevd/simparams.jsonnet';
local params = base {
  lar: super.lar { // <- super.lar overrides default values
    // Longitudinal diffusion constant
    DL: std.extVar('DL') * wc.cm2 / wc.s,
    // Transverse diffusion constant
    DT: std.extVar('DT') * wc.cm2 / wc.s,
    // Electron lifetime
    lifetime: std.extVar('lifetime') * wc.ms,
    // Electron drift speed, assumes a certain applied E-field
    drift_speed: std.extVar('driftSpeed') * wc.mm / wc.us,
  },
};


local tools_all = tools_maker(params);
local tools = tools_all {anodes: [tools_all.anodes[n] for n in [0,1]]};
local nanodes = std.length(tools.anodes);
local anode_iota = std.range(0, nanodes - 1);

local mega_anode = {
    type: 'MegaAnodePlane',
    name: 'meganodes',
    data: {
        anodes_tn: [wc.tn(anode) for anode in tools.anodes],
    },
    uses: [anode for anode in tools.anodes],
};

// must match name used in fcl
local wcls_input = g.pnode({
    type: 'wclsCookedFrameSource',
    name: 'sigs',
    data: {
        nticks: params.daq.nticks,
        frame_scale: 50,                             // scale up input recob::Wire by this factor
        summary_scale: 50,                             // scale up input summary by this factor
        frame_tags: ["orig"],                 // frame tags (only one frame in this module)
        recobwire_tags: std.extVar('recobwire_tags'), // ["sptpc2d:gauss", "sptpc2d:wiener"],
        trace_tags: std.extVar('trace_tags'), // ["gauss", "wiener"],
        summary_tags: std.extVar('summary_tags'), // ["", "sptpc2d:wienersummary"],
        input_mask_tags: std.extVar('input_mask_tags'), // ["sptpc2d:badmasks"],
        output_mask_tags: std.extVar('output_mask_tags'), // ["bad"],
    },
}, nin=0, nout=1);

local labelling2d = g.pnode({
    type: 'Labelling2D',
    name: 'all',
    data: {
        nticks: params.daq.nticks,
        reco_tag: "gauss", # input
        simchannel_label: "tpcrawdecoder:simpleSC",
    },
}, nin=1, nout=1);

local hio_rec = g.pnode({
    type: 'HDF5FrameTap',
    name: 'hio_rec_all',
    data: {
        anode: wc.tn(mega_anode),
        trace_tags: ['gauss'], 
        filename: "g4-rec.h5",
        gzip: 2,
    },
}, nin=1, nout=1);

local hio_tru = g.pnode({
    type: 'HDF5FrameTap',
    name: 'hio_tru_all',
    data: {
        anode: wc.tn(mega_anode),
        trace_tags: ['trackid', 'pid'], 
        filename: "g4-tru.h5",
        gzip: 2,
    },
}, nin=1, nout=1);

local dumpcap = g.pnode({ type: 'DumpFrames' }, nin=1, nout=0);
local graph = g.pipeline([wcls_input, hio_rec, labelling2d, hio_tru, dumpcap], "main");

local app = {
  type: 'Pgrapher', //Pgrapher, TbbFlow
  data: {
    edges: g.edges(graph),
  },
};

local cmdline = {
    type: "wire-cell",
    data: {
        plugins: ["WireCellGen", "WireCellPgraph", "WireCellSio", "WireCellSigProc", "WireCellRoot", "WireCellTbb", "WireCellImg"],
        apps: ["Pgrapher"] //TbbFlow
    }
};

[cmdline] + g.uses(graph) + [app]
