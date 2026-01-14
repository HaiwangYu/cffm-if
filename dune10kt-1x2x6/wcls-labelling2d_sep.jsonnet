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



local tools_all = tools_maker(params);
local tools = tools_all
//  + {
//     anodes : [tools_all.anodes[0]]
// }
;

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

local chsel_pipes = [
  g.pnode({
    type: 'ChannelSelector',
    name: 'chsel%d' % n,
    data: {
      channels: std.range(2560 * n, 2560 * (n + 1) - 1),
      // tags: [sp_trace_tag], // must specify tag to select traces
      tags: ["dnnsp"], // must specify tag to select traces
      //channels: if n==0 then std.range(2560*n,2560*(n+1)-1) else [],
      //tags: ['orig%d' % n], // traces tag
    },
  }, nin=1, nout=1)
  for n in std.range(0, std.length(tools.anodes) - 1)
];

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

local labelling2d_pipes_nodes = [
  g.pnode({
    type: 'Labelling2D',
    name: 'anode%d' % n,
    data: {
        min_charge: 0,
        reco_tag: sp_trace_tag,
        simchannel_label: "tpcrawdecoder:simpleSC",
        // save_extended_labels: true,
        rebin_time_tick: 4,
    },
  }, nin=1, nout=1)
  for n in std.range(0, std.length(tools.anodes) - 1)
];

local hio_rec = g.pnode({
    type: 'HDF5FrameTap',
    name: 'hio_rec_all',
    data: {
        anode: wc.tn(mega_anode),
        trace_tags: [sp_trace_tag], 
        // trace_tags: ["rebinned_reco"], 
        filename: "g4-rec.h5",
        gzip: 2,
    },
}, nin=1, nout=1);

// Create per-anode HDF5FrameTap nodes - these will be inside each pipeline
// Note: We use mega_anode here because after ChannelSelector, the frame still has
// all channel info, just with some channels having no data. HDF5FrameTap needs the
// full anode definition to map channels correctly.
local hio_tru_nodes = [
  g.pnode({
    type: 'HDF5FrameTap',
    name: 'hio_tru_anode%d' % n,
    data: {
        anode: wc.tn(mega_anode),
        trace_tags: [
            'rebinned_reco',
            'trackid_1st',
            'pid_1st',
            'trackid_2nd',
            'pid_2nd'
        ],
        filename: "g4-tru-anode%d.h5" % n,
        gzip: 2,
    },
  }, nin=1, nout=1)
  for n in std.range(0, std.length(tools.anodes) - 1)
];

// local dumpcap = g.pnode({ type: 'DumpFrames' }, nin=1, nout=0);
local dumpcaps =[ g.pnode({ type: 'DumpFrames' ,name:'dump_%d'%n,}, nin=1, nout=0)for n in std.range(0, std.length(tools.anodes) - 1)];

// Empty tag_rules array means no tag renaming - pass through all tags unchanged
local fanout_tag_rules = [];
// local fanout_tag_rules = [
//           {
//             frame: {
//               '.*': 'orig%d' % tools.anodes[n].data.ident,
//             },
//             trace: {
//               // Pass through trace tags unchanged - empty means no renaming
//             },
//           }
//           for n in std.range(0, std.length(tools.anodes) - 1)
//         ];
local fanin_tag_rules = [
          {
            frame: {
              //['number%d' % n]: ['output%d' % n, 'output'],
              '.*': 'framefanin',
            },
            trace: {
                'rebinned_reco': 'rebinned_reco_%d'%n,
                'trackid_1st':'trackid_1st_%d'%n,
                'pid_1st': 'pid_1st_%d'%n,
                'trackid_2nd': 'trackid_2nd_%d'%n,
                'pid_2nd': 'pid_2nd_%d'%n,
            },

          }
          for n in std.range(0, std.length(tools.anodes) - 1)
        ];
local labelling2d_pipes = [
  g.pipeline(
             [ chsel_pipes[n] ]
             + [labelling2d_pipes_nodes[n] ]
             + [hio_tru_nodes[n]],

             'labelling2d_pipe_%d' % n)
  for n in std.range(0, std.length(tools.anodes) - 1)
];


// Manually build fanout-fanin structure with custom tag rules for both
local fanmult = std.length(labelling2d_pipes);

local fanout = g.pnode({
    type: 'FrameFanout',
    name: 'label2d',
    data: {
        multiplicity: fanmult,
        tag_rules: fanout_tag_rules,
    },
}, nin=1, nout=fanmult);

local fanin = g.pnode({
    type: 'FrameFanin',
    name: 'label2d',
    data: {
        multiplicity: fanmult,
        tag_rules: fanin_tag_rules,
        tags: [],
    },
}, nin=fanmult, nout=1);

local fanpipe = g.intern(
    innodes=[fanout],
    // outnodes=[],
    centernodes=labelling2d_pipes+dumpcaps,
    edges=
        [g.edge(fanout, labelling2d_pipes[n], n, 0) for n in std.range(0, fanmult - 1)] +
        [g.edge(labelling2d_pipes[n], dumpcaps[n], 0, 0) for n in std.range(0, fanmult - 1)],
    name='label2d'
);

// local graph = g.pipeline([wcls_input, hio_rec, labelling2d, hio_tru, dumpcap], "main");
// local graph = g.pipeline([wcls_input, hio_rec, fanpipe, dumpcap], "main");
local graph = g.pipeline([wcls_input, hio_rec, fanpipe], "main");

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
