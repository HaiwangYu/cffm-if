local g = import "pgraph.jsonnet";
local f = import "pgrapher/common/funcs.jsonnet";
local wc = import "wirecell.jsonnet";

local tools_maker = import 'pgrapher/common/tools.jsonnet';

local params_maker = import 'pgrapher/experiment/dune10kt-1x2x6/simparams.jsonnet';
local sp_trace_tag = "dnnsp"; // gauss, dnnsp
local fcl_params = {
    G4RefTime: std.extVar('G4RefTime') * wc.us,
};
local params = params_maker(fcl_params) {
  lar: super.lar {
    // Longitudinal diffusion constant
    DL: std.extVar('DL') * wc.cm2 / wc.ns,
    // Transverse diffusion constant
    DT: std.extVar('DT') * wc.cm2 / wc.ns,
    // Electron lifetime
    lifetime: std.extVar('lifetime') * wc.us,
    // Electron drift speed, assumes a certain applied E-field
    drift_speed: std.extVar('driftSpeed') * wc.mm / wc.us,
  },
};


local tools = tools_maker(params);

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
        min_charge: 0,
        reco_tag: sp_trace_tag,
        simchannel_label: "tpcrawdecoder:simpleSC",
    },
}, nin=1, nout=1);

local hio_rec = g.pnode({
    type: 'HDF5FrameTap',
    name: 'hio_rec_all',
    data: {
        anode: wc.tn(mega_anode),
        trace_tags: [sp_trace_tag], 
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
