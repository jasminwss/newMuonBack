
# Truth-only version of MuonBack/Inspection/cavern_spectrometer.py for the cuda-propagated muon samples
# (muons start 50 cm before the end of the muon shield, FairShip sim only, no reco).
#
# Categories (nested):
#   all   - every event with a cavern muon: a muon has a daughter starting inside the Cavern volume
#           (same condition as classify_event_origin in inspect_Back.py)
#   truth - a muon from the wall has >= 1 strawtubesPoint. "Muon from the wall" = a muon that interacted in the
#           concrete upstream of Tr1, or a muon descendant of such an interaction (cavern mu -> pi in the wall -> mu).
# digi / reco of the original script are left out: these samples have no reco.
#
# Filled per category: SBT cell multiplicity and Edep per cell (sum Eloss per cell, threshold cut, as inspect_Back.py),
# wall interaction point (z-y, x-y), momentum and x-y at the first strawtubesPoint in station 1 (truth only).
# --pdg: like cavern_spectrometer.py --pdg (wall vertex x and theta_xz at station 1, split by the charge of the wall muon),
#        only the events with strawtubesPoints are read.
#
# Two modes, both run by ../prod:
#   fill (one condor job per sim file):  python cavern_truth.py --sim sim_X.root --geo geo_Y.root --out hists_X.root [--pdg]
#   plot (after hadd of all job files):  python cavern_truth.py --plot merged.root --outdir DIR --tag TAG [--pdg]

import ROOT, os, math, sys
from argparse import ArgumentParser
from array import array

ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(0)
ROOT.gErrorIgnoreLevel = ROOT.kWarning

parser = ArgumentParser()
parser.add_argument('--sim', help='fill: sim file (cbmsim)')
parser.add_argument('--geo', help='fill: geo file (FAIRGeom), the geometry is frozen, any geo file of the sample works')
parser.add_argument('--out', help='fill: output ROOT file with the histograms')
parser.add_argument('--max-events', type=int, default=None, help='fill: only the first N events (test)')
parser.add_argument('--plot', help='plot: merged histogram file')
parser.add_argument('--outdir', help='plot: folder for the png files')
parser.add_argument('--tag', default='', help='plot: title prefix and file name prefix')
parser.add_argument('--pdg', action='store_true', help='wall vertex x and theta_xz at station 1, split by mu+ / mu- of the wall muon')
parser.add_argument('--sumw-tot', type=float, default=None,
                    help='plot: sum of the muon weights of the FULL sample (= 1 spill, A. Magnan); scales to per spill')
options = parser.parse_args()


def event_weight(event):
    """Weight of the incoming muon, MCTrack[0].GetWeight() (3.3 ... 769 in the 2018 sample), as in
    MuonBack/Inspection/cavern_spectrometer.py. It is per spill for the FULL sample; plot() scales by
    sumW_tot / sumW_processed because only part of the sample is simulated (A. Magnan)."""
    return event.MCTrack[0].GetWeight()

Y_UNIT = 'weighted'  # axis labels "weighted events", "weighted muons"; plot() sets 'per spill' when --sumw-tot is given

def ylabel(what):
    return f'{what.capitalize()} per spill' if Y_UNIT == 'per spill' else f'{Y_UNIT} {what}'


threshold_list = [0, 10, 20, 30, 45, 50, 60, 90]
categories = ['all', 'truth']
cat_label = {
    'all':   'all cavern events',
    'truth': '#mu from wall has straw MC points',
}
cat_style = {'all': ('#071b3c', 1), 'truth': ('#c64384', 2)}  # (colour, line style)
pdg_label = {'mup': 'wall muon #mu^{+}', 'mum': 'wall muon #mu^{-}'}
EDEP_REBIN = 10
# inner ECN3 hall in cm (passive/ShipCave.cxx), only used for the dashed outlines in the plots
HALL_X = (-456., 1143.)
HALL_Y = (-336., 864.)
HALL_Z = (2134., 12052.)
# straw aperture in cm (geometry/strawtubes_config.yaml)
ST_X = (-200., 200.)
ST_Y = (-300., 300.)
Z_TR1 = None  # z of straw station 1, read from the geo file (8422 cm in try_2026_v2, 8407 cm in the old MuonBack geometry)


RAW_HISTS = {'n_processed', 'sumw_processed', 'n_events_raw'}  # not scaled to per spill


def book():
    h = {}
    h['n_processed'] = ROOT.TH1D('n_processed', 'processed events;;MC events', 1, 0, 1)
    h['sumw_processed'] = ROOT.TH1D('sumw_processed', 'sum of the muon weights of all processed events;;sum w', 1, 0, 1)
    h['n_events']     = ROOT.TH1D('n_events',     f'cavern events;;{ylabel("events")}', len(categories), 0, len(categories))
    h['n_events_raw'] = ROOT.TH1D('n_events_raw', 'cavern events;;MC events',           len(categories), 0, len(categories))
    for c in categories:
        for t in threshold_list:
            h[f'{c}_{t}_digihit_multiplicity'] = ROOT.TH1D(
                f'{c}_{t}_digihit_multiplicity',
                f'{cat_label[c]} @ {t} MeV;Number of triggered SBT cells in an event;{ylabel("events")}',
                101, -0.5, 100.5)
            h[f'{c}_{t}_digihit_energydeposition'] = ROOT.TH1D(
                f'{c}_{t}_digihit_energydeposition',
                f'{cat_label[c]} @ {t} MeV;E_deposition per digihit (GeV);{ylabel("digihits")}',
                1000, 0., 1.)
        h[f'{c}_wall_zy'] = ROOT.TH2D(f'{c}_wall_zy', f'{cat_label[c]};z (cm);y (cm);{ylabel("muons")}',
                                      212, 2000., 12600., 65, -400., 900.)  # to 12600: ~40 % hit the back wall (z > 12052)
        h[f'{c}_wall_xy'] = ROOT.TH2D(f'{c}_wall_xy', f'{cat_label[c]};x (cm);y (cm);{ylabel("muons")}',
                                      200, -700., 1300., 150, -500., 1000.)
    h['truth_p_station1'] = ROOT.TH1D('truth_p_station1', f'{cat_label["truth"]};p at straw station 1 (GeV);{ylabel("muons")}',
                                      50, 0., 10.)
    h['truth_station1_xy'] = ROOT.TH2D('truth_station1_xy', f'{cat_label["truth"]};x (cm);y (cm);{ylabel("muons")}',
                                       70, -350., 350., 80, -400., 400.)
    for hist in h.values():
        hist.Sumw2()
        hist.SetDirectory(0)
    return h

def book_pdg():
    h = {}
    h['n_processed'] = ROOT.TH1D('n_processed', 'processed events;;MC events', 1, 0, 1)
    h['sumw_processed'] = ROOT.TH1D('sumw_processed', 'sum of the muon weights of all processed events;;sum w', 1, 0, 1)
    for sign, label in [('mup', '#mu^{+}'), ('mum', '#mu^{-}')]:
        h[f'truth_vtx_x_{sign}'] = ROOT.TH1D(f'truth_vtx_x_{sign}',
                                             f'wall muon {label};x of the wall vertex (cm);{ylabel("muons")}',
                                             200, -700., 1300.)
        h[f'truth_st1_ang_xz_{sign}'] = ROOT.TH1D(f'truth_st1_ang_xz_{sign}',
                                                  f'wall muon {label};#theta_{{xz}} = atan(p_{{x}}/p_{{z}}) at the first straw point in station 1 (deg);{ylabel("muons")}',
                                                  180, -90., 90.)
        h[f'{sign}_st1_x_ang_xz'] = ROOT.TH2D(f'{sign}_st1_x_ang_xz',
                                              f'wall muon {label};x at the first straw point in station 1 (cm);#theta_{{xz}} (deg);{ylabel("muons")}',
                                              50, -250., 250., 36, -90., 90.)
    for hist in h.values():
        hist.Sumw2()
        hist.SetDirectory(0)
    return h


# ---------------------------------------------------------------- truth classification (as cavern_spectrometer.py)

def get_cavern_muons(event):
    """Returns (all, upstream, wall_children):
    all           - {TrackID: (x, y, z)} muons with a daughter starting inside the Cavern volume, (x, y, z) = start
                    vertex of the most energetic such daughter (interaction point in the wall)
    upstream      - same, but only daughters starting upstream of Tr1 (z < Z_TR1)
    wall_children - TrackIDs of all those daughters upstream of Tr1"""
    vtx, vtx_up, wall_children = {}, {}, set()  # TrackID -> (E, x, y, z)
    for k, track in enumerate(event.MCTrack):
        motherId = track.GetMotherId()
        if motherId == -1: continue
        if abs(event.MCTrack[motherId].GetPdgCode()) == 13:
            node = ROOT.gGeoManager.FindNode(track.GetStartX(), track.GetStartY(), track.GetStartZ())
            if node and node.GetVolume().GetName().startswith('Cavern'):
                cand = (track.GetEnergy(), track.GetStartX(), track.GetStartY(), track.GetStartZ())
                if cand[3] < Z_TR1:
                    wall_children.add(k)
                for d in ((vtx, vtx_up) if cand[3] < Z_TR1 else (vtx,)):
                    if motherId not in d or cand[0] > d[motherId][0]:
                        d[motherId] = cand
    return {k: v[1:] for k, v in vtx.items()}, {k: v[1:] for k, v in vtx_up.items()}, wall_children

def get_wall_descendant_muons(event, wall_children):
    """TrackIDs of muons whose ancestry contains a wall child, e.g. cavern mu -> pi in the wall -> pi decays -> mu"""
    ids = set()
    for k, track in enumerate(event.MCTrack):
        if abs(track.GetPdgCode()) != 13: continue
        j = k
        while j >= 0:
            if j in wall_children:
                ids.add(k)
                break
            j = event.MCTrack[j].GetMotherId()
    return ids

def get_wall_ancestor(event, k, cavern_vtx_up, wall_children):
    """wall muon (key of cavern_vtx_up) behind the muon k"""
    if k in cavern_vtx_up:
        return k
    j = k
    while j >= 0:
        if j in wall_children:
            return event.MCTrack[j].GetMotherId()
        j = event.MCTrack[j].GetMotherId()
    return None

def station1_points(event, ids):
    """TrackID -> most upstream strawtubesPoint in station 1 (detID = station * 1e6 + ...) of the muons in ids"""
    st1 = {}
    for point in event.strawtubesPoint:
        tid = point.GetTrackID()
        if tid not in ids or point.GetDetectorID() // 1000000 != 1: continue
        if tid not in st1 or point.GetZ() < st1[tid].GetZ():
            st1[tid] = point
    return st1


# ---------------------------------------------------------------- fill (one sim file)

def open_input():
    global Z_TR1
    fgeo = ROOT.TFile.Open(options.geo)
    fgeo.Get('FAIRGeom')
    Z_TR1 = ROOT.gGeoManager.GetTopVolume().FindNode('Tr1_1').GetMatrix().GetTranslation()[2]
    print(f'Z_TR1 = {Z_TR1} cm (Tr1_1 in {os.path.basename(options.geo)})')
    f_sim = ROOT.TFile.Open(options.sim)
    tree = f_sim.Get('cbmsim')
    return fgeo, f_sim, tree

def fill(h):
    fgeo, f_sim, tree = open_input()
    tree.SetBranchStatus('*', 0)
    for b in ['MCEventHeader*', 'MCTrack*', 'vetoPoint*', 'strawtubesPoint*']:
        tree.SetBranchStatus(b, 1)
    n_total = tree.GetEntries() if options.max_events is None else min(options.max_events, tree.GetEntries())
    n_cavern = n_truth = 0
    for eventNr in range(n_total):
        tree.GetEntry(eventNr)
        weight = event_weight(tree)
        h['sumw_processed'].Fill(0.5, weight)  # every event, also those without a cavern muon
        cavern_vtx, cavern_vtx_up, wall_children = get_cavern_muons(tree)
        if not cavern_vtx:
            continue
        n_cavern += 1
        muon_ids = set(cavern_vtx_up) | get_wall_descendant_muons(tree, wall_children)
        truth_ids = {p.GetTrackID() for p in tree.strawtubesPoint} & muon_ids
        flags = {'all': True, 'truth': bool(truth_ids)}
        n_truth += flags['truth']

        ElossPerDetId = {}
        for veto_point in tree.vetoPoint:
            detID = veto_point.GetDetectorID()
            ElossPerDetId[detID] = ElossPerDetId.get(detID, 0.) + veto_point.GetEnergyLoss()

        for c in categories:
            if not flags[c]:
                continue
            h['n_events'].Fill(categories.index(c), weight)
            h['n_events_raw'].Fill(categories.index(c))
            for x, y, z in (cavern_vtx if c == 'all' else cavern_vtx_up).values():
                h[f'{c}_wall_zy'].Fill(z, y, weight)
                h[f'{c}_wall_xy'].Fill(x, y, weight)
            for t in threshold_list:
                mult = 0
                for eloss in ElossPerDetId.values():
                    if eloss < 0.001 * t: continue
                    mult += 1
                    h[f'{c}_{t}_digihit_energydeposition'].Fill(eloss, weight)
                h[f'{c}_{t}_digihit_multiplicity'].Fill(mult, weight)
        if flags['truth']:
            for point in station1_points(tree, truth_ids).values():
                h['truth_p_station1'].Fill(math.sqrt(point.GetPx()**2 + point.GetPy()**2 + point.GetPz()**2), weight)
                h['truth_station1_xy'].Fill(point.GetX(), point.GetY(), weight)
    h['n_processed'].Fill(0.5, n_total)
    print(f'processed {n_total} events, {n_cavern} cavern events, {n_truth} with a mu from wall in the straws')
    f_sim.Close(); fgeo.Close()

def fill_pdg(h):
    fgeo, f_sim, tree = open_input()
    tree.SetBranchStatus('*', 0)
    for b in ['MCEventHeader*', 'MCTrack*', 'strawtubesPoint*']:
        tree.SetBranchStatus(b, 1)
    n_total = tree.GetEntries() if options.max_events is None else min(options.max_events, tree.GetEntries())
    for eventNr in range(n_total):  # sum of weights over ALL events, for the per-spill scaling
        tree.GetEntry(eventNr)
        h['sumw_processed'].Fill(0.5, event_weight(tree))
    # only the events with straw MC points, selected in C++
    tree.Draw('>>straw_list', 'strawtubesPoint@.size() > 0', 'entrylist', n_total)
    straw_list = ROOT.gDirectory.Get('straw_list')
    n_truth = n_no_st1 = 0
    for i in range(straw_list.GetN()):
        tree.GetEntry(straw_list.GetEntry(i))
        weight = event_weight(tree)
        _, cavern_vtx_up, wall_children = get_cavern_muons(tree)
        if not cavern_vtx_up:
            continue
        muon_ids = set(cavern_vtx_up) | get_wall_descendant_muons(tree, wall_children)
        straw_ids = {p.GetTrackID() for p in tree.strawtubesPoint} & muon_ids
        if not straw_ids:
            continue
        n_truth += 1
        for anc in {get_wall_ancestor(tree, k, cavern_vtx_up, wall_children) for k in straw_ids}:
            sign = 'mup' if tree.MCTrack[anc].GetPdgCode() == -13 else 'mum'
            h[f'truth_vtx_x_{sign}'].Fill(cavern_vtx_up[anc][0], weight)
        st1 = station1_points(tree, straw_ids)
        n_no_st1 += len(straw_ids) - len(st1)
        for tid, point in st1.items():
            anc = get_wall_ancestor(tree, tid, cavern_vtx_up, wall_children)
            sign = 'mup' if tree.MCTrack[anc].GetPdgCode() == -13 else 'mum'
            theta = math.degrees(math.atan2(point.GetPx(), point.GetPz()))
            h[f'truth_st1_ang_xz_{sign}'].Fill(theta, weight)
            h[f'{sign}_st1_x_ang_xz'].Fill(point.GetX(), theta, weight)
    h['n_processed'].Fill(0.5, n_total)
    print(f'processed {n_total} events, {straw_list.GetN()} with straw MC points, {n_truth} with a mu from wall in the straws, '
          f'{n_no_st1} straw muons without a point in station 1')
    f_sim.Close(); fgeo.Close()


# ---------------------------------------------------------------- plots (merged file)

def out_png(name):
    return os.path.join(options.outdir, f'{options.tag}{name}.png')

def summary(h):
    n_all = h['n_events'].GetBinContent(1)
    print(f'\n  processed events: {h["n_processed"].GetBinContent(1):.0f}')
    print(f'  {"category":<36} {"MC events":>10} {"weighted":>14} {"fraction":>10}')
    for i, c in enumerate(categories, start=1):
        n, n_raw = h['n_events'].GetBinContent(i), h['n_events_raw'].GetBinContent(i)
        print(f'  {cat_label[c].replace("#mu", "mu"):<36} {n_raw:>10.0f} {n:>14.3e} {n / n_all if n_all else 0:>10.3f}')

def draw_overlay(h, quantity, xtitle, ytitle, xmax, rebin, name):
    hists = {}
    for t in threshold_list:
        for cat in categories:
            hc = h[f'{cat}_{t}_{quantity}'].Clone(f'{cat}_{t}_{quantity}_draw')
            hc.SetDirectory(0)
            if rebin > 1: hc.Rebin(rebin)
            col, ls = cat_style[cat]
            hc.SetLineColor(ROOT.TColor.GetColor(col)); hc.SetLineStyle(ls); hc.SetLineWidth(4)
            hc.SetTitle(f';{xtitle};{ytitle}')
            hc.GetXaxis().SetRangeUser(0, xmax)
            hists[(t, cat)] = hc
    ymax = max(hc.GetMaximum() for hc in hists.values())
    ymin = min((hc.GetMinimum(0) for hc in hists.values() if hc.GetMinimum(0) > 0), default=1e-3)

    c = ROOT.TCanvas(f'c_{name}', name, 2800, 1500)
    title_pad = ROOT.TPad(f'title_pad_{name}', '', 0, 0.88, 1, 1)
    main_pad  = ROOT.TPad(f'main_pad_{name}',  '', 0, 0, 1, 0.88)
    title_pad.Draw(); main_pad.Draw()
    title_pad.cd()
    title = ROOT.TLatex(); title.SetNDC(); title.SetTextFont(62); title.SetTextSize(0.32); title.SetTextAlign(22)
    title.DrawLatex(0.5, 0.75, f'{options.tag.rstrip("_")}: cavern events, {name}')
    leg = ROOT.TLegend(0.2, 0.02, 0.8, 0.45)
    leg.SetNColumns(len(categories)); leg.SetBorderSize(0); leg.SetFillStyle(0); leg.SetTextSize(0.26)
    for cat in categories:
        leg.AddEntry(hists[(threshold_list[0], cat)], cat_label[cat], 'l')
    leg.Draw()
    main_pad.Divide(4, 2)
    keep = [title_pad, main_pad, title, leg]
    for i, t in enumerate(threshold_list, start=1):
        pad = main_pad.cd(i)
        pad.SetLogy(); pad.SetLeftMargin(0.19); pad.SetRightMargin(0.04); pad.SetBottomMargin(0.17); pad.SetTopMargin(0.05)
        for j, cat in enumerate(categories):
            hc = hists[(t, cat)]
            hc.SetMaximum(5 * ymax); hc.SetMinimum(0.5 * ymin)
            for axis in (hc.GetXaxis(), hc.GetYaxis()):
                axis.SetLabelSize(0.06); axis.SetTitleSize(0.065)
            hc.GetXaxis().SetTitleOffset(1.1); hc.GetYaxis().SetTitleOffset(1.45)
            hc.GetXaxis().SetNdivisions(505)
            if j > 0 and hc.Integral() == 0: continue
            hc.Draw('HIST' if j == 0 else 'HIST SAME')
        lab = ROOT.TLatex(); lab.SetNDC(); lab.SetTextFont(62); lab.SetTextSize(0.075); lab.SetTextAlign(33)
        lab.DrawLatex(0.93, 0.92, f'{t} MeV')
        keep.append(lab)
    keep += list(hists.values())
    c.SaveAs(out_png(f'cavern_{quantity}'))

def draw_heatmap(h, quantity, cats, outline, nx, ny, shown, labels=cat_label):
    """2D heatmap {cat}_{quantity}, one panel per category; outline = dashed box (x1, y1, x2, y2)"""
    cols = ['#fbeef4', '#c64384', '#3d0a24']
    rgb = [[int(col[i:i + 2], 16) / 255. for col in cols] for i in (1, 3, 5)]
    ROOT.TColor.CreateGradientColorTable(len(cols), array('d', [0., 0.5, 1.]), *[array('d', v) for v in rgb], 255)

    c = ROOT.TCanvas(f'c_{quantity}', quantity, 1400 * nx, 1500 if ny > 1 else 1100)
    c.Divide(nx, ny)
    keep = []
    for i, cat in enumerate(cats, start=1):
        pad = c.cd(i)
        pad.SetLogz(); pad.SetBottomMargin(0.12); pad.SetTopMargin(0.13); pad.SetLeftMargin(0.1); pad.SetRightMargin(0.16)
        hc = h[f'{cat}_{quantity}']
        hc.SetTitle('')
        hc.GetZaxis().SetTitle(ylabel('muons'))
        for axis in (hc.GetXaxis(), hc.GetYaxis(), hc.GetZaxis()):
            axis.SetLabelSize(0.045); axis.SetTitleSize(0.05)
        hc.GetYaxis().SetTitleOffset(0.95); hc.GetZaxis().SetTitleOffset(1.1)
        hc.GetXaxis().SetNdivisions(505)
        hc.Draw('COLZ')
        box = ROOT.TBox(*outline)
        box.SetFillStyle(0); box.SetLineColor(ROOT.kGray + 2); box.SetLineStyle(2); box.SetLineWidth(2)
        box.Draw()
        xc = (pad.GetLeftMargin() + 1 - pad.GetRightMargin()) / 2
        for y, font, size, text in [(0.955, 62, 0.05, f'{options.tag.rstrip("_")}: {labels[cat]}'), (0.905, 42, 0.035, shown)]:
            lat = ROOT.TLatex(); lat.SetNDC(); lat.SetTextAlign(22); lat.SetTextFont(font); lat.SetTextSize(size)
            lat.DrawLatex(xc, y, text)
            keep.append(lat)
        keep.append(box)
    c.SaveAs(out_png(f'cavern_{quantity}'))

def draw_1d(curves, title, name, walls=False):
    """curves = [(hist, legend label, colour, line style)]; walls: dotted lines at the inner hall walls in x"""
    ymax = max(hc.GetMaximum() for hc, _, _, _ in curves)
    ymin = min((hc.GetMinimum(0) for hc, _, _, _ in curves if hc.GetMinimum(0) > 0), default=1e-3)
    c = ROOT.TCanvas(f'c_{name}', title, 1800, 1200)
    c.SetLogy(); c.SetLeftMargin(0.12); c.SetRightMargin(0.04)
    leg = ROOT.TLegend(0.50, 0.76, 0.94, 0.88)
    leg.SetBorderSize(0); leg.SetFillStyle(0); leg.SetTextSize(0.035)
    for j, (hc, label, col, ls) in enumerate(curves):
        hc.SetLineColor(ROOT.TColor.GetColor(col)); hc.SetLineStyle(ls); hc.SetLineWidth(4)
        hc.SetTitle(f'{options.tag.rstrip("_")}: {title}')
        hc.SetMaximum(5 * ymax); hc.SetMinimum(0.5 * ymin)
        hc.Draw('HIST' if j == 0 else 'HIST SAME')
        leg.AddEntry(hc, f'{label} ({hc.GetEntries():.0f} MC muons)', 'l')
    leg.Draw()
    lines = []
    if walls:
        for xw in HALL_X:
            line = ROOT.TLine(xw, 0.5 * ymin, xw, 5 * ymax)
            line.SetLineColor(ROOT.kGray + 2); line.SetLineStyle(3); line.SetLineWidth(2)
            line.Draw()
            lines.append(line)
    c.SaveAs(out_png(name))

def plot(h):
    summary(h)
    draw_overlay(h, 'digihit_multiplicity', 'Triggered SBT cells per event', ylabel('events'), 100, 1, 'SBT digihit multiplicity')
    draw_overlay(h, 'digihit_energydeposition', 'E_deposition per digihit (GeV)', ylabel('digihits'), 1., EDEP_REBIN,
                 'SBT E_deposition per cell')
    wall_shown = 'MC position: start vertex of the most energetic daughter of the cavern muon in the concrete'
    draw_heatmap(h, 'wall_zy', categories, (HALL_Z[0], HALL_Y[0], HALL_Z[1], HALL_Y[1]), 2, 1, wall_shown)
    draw_heatmap(h, 'wall_xy', categories, (HALL_X[0], HALL_Y[0], HALL_X[1], HALL_Y[1]), 2, 1, wall_shown)
    draw_1d([(h['truth_p_station1'], cat_label['truth'], cat_style['truth'][0], 1)], '#mu from wall momentum at straw station 1',
            'cavern_p_station1')
    draw_heatmap(h, 'station1_xy', ['truth'], (ST_X[0], ST_Y[0], ST_X[1], ST_Y[1]), 1, 1,
                 'MC position: first strawtubesPoint in Tr1')

def plot_pdg(h):
    print(f'\n  processed events: {h["n_processed"].GetBinContent(1):.0f}')
    for q, title, walls in [('vtx_x', 'wall vertex x, #mu from wall has straw MC points', True),
                            ('st1_ang_xz', '#theta_{xz} at straw station 1, #mu from wall has straw MC points', False)]:
        draw_1d([(h[f'truth_{q}_mup'], 'wall muon #mu^{+}', '#c64384', 1),
                 (h[f'truth_{q}_mum'], 'wall muon #mu^{-}', '#071b3c', 7)], title, f'cavern_{q}_pdg', walls)
    draw_heatmap(h, 'st1_x_ang_xz', ['mup', 'mum'], (ST_X[0], -90., ST_X[1], 90.), 2, 1,
                 'MC: first strawtubesPoint in station 1, #theta_{xz} = atan(p_{x}/p_{z})', pdg_label)


if options.plot:
    f_in = ROOT.TFile.Open(options.plot)
    h = {}
    for k in f_in.GetListOfKeys():
        h[k.GetName()] = f_in.Get(k.GetName())
        h[k.GetName()].SetDirectory(0)
    f_in.Close()
    if options.sumw_tot:
        if 'sumw_processed' not in h:
            sys.exit('merged file has no sumw_processed (made before the per-spill scaling), rerun the cavern jobs')
        sumw = h['sumw_processed'].GetBinContent(1)
        scale = options.sumw_tot / sumw
        print(f'per spill: sumW_tot / sumW_processed = {options.sumw_tot:.6e} / {sumw:.6e} = {scale:.4f}')
        Y_UNIT = 'per spill'
        for name, hist in h.items():
            if name in RAW_HISTS:
                continue
            hist.Scale(scale)
            if hist.GetDimension() == 1:  # booked as "weighted <what>"; 2D z titles are set in draw_heatmap
                hist.GetYaxis().SetTitle(ylabel(hist.GetYaxis().GetTitle().split()[-1]))
    else:
        print('no --sumw-tot: weights are not scaled to one spill, axes say "weighted"')
    os.makedirs(options.outdir, exist_ok=True)
    plot_pdg(h) if options.pdg else plot(h)
else:
    if not (options.sim and options.geo and options.out):
        sys.exit('fill mode needs --sim, --geo and --out (or --plot for plotting)')
    h = book_pdg() if options.pdg else book()
    fill_pdg(h) if options.pdg else fill(h)
    f_out = ROOT.TFile(options.out, 'RECREATE')
    for hist in h.values():
        hist.Write()
    f_out.Close()
    print(f'Histograms written to {options.out}')
