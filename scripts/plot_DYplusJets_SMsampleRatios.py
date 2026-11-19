#!/usr/bin/env python3
"""Compare the SM of several DYjets samples: one coloured line per sample, with a ratio panel to the
first sample, the reference. Typical use: the LO samples with 0, 0+1, and 0+1+2 partons in the matrix
element against the Born-level LO 0-jet sample, and later the NLO samples in the same way.

Input : <run folder>/Rivet.yoda of each sample. The SM is read from the histograms of the SM
        reweighting point, <histogram>[rw0000] (LO) or <histogram>[rw0000_nlo] (NLO, found
        automatically): the same SM as in the scaling files, as a cross section in pb per bin, with
        its statistical uncertainty. (The plain nominal histograms are not used: with MLM merging they
        are too high by 1/(matching efficiency).)
Output: <outdir>/<histogram>[_<x range>]_{lin,log}.{png,pdf}, same names as plot_DYplusJets.py

Example, from the EFT2Obs folder:
  E=/eos/user/m/mwitt/EFT2Obs
  python scripts/plot_DYplusJets_SMsampleRatios.py -o outputs/compare_LO_13p6TeV \\
      --sample "LO 0j=$E/DYjets_LO_0j_13p6TeV" --sample "LO 0+1j=$E/DYjets_LO_01j_13p6TeV" \\
      --sample "LO 0+1+2j=$E/DYjets_LO_012j_13p6TeV" --channels ll ee mm

With --normalise every sample is scaled to unit area, so the ratio panel compares shapes only: at LO
the normalisation changes with the number of partons in the matrix element.
"""
import argparse
import array
import os
import re
import sys

import ROOT
import yoda

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plotting as plot  # noqa: E402
from dyplusjets_labels import VARIABLES, SLICE_LABELS, CHANNEL_LABELS, histograms, selection_lines  # noqa: E402
from dyplusjets_ratio import defined_bins, draw_ratio_band, draw_ratio_line  # noqa: E402

ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(ROOT.kTRUE)
ROOT.TH1.AddDirectory(False)
plot.ModTDRStyle()

# One colour per sample, in the order given: black for the reference, then red, blue, green, ...
COLORS = [1, 2, 4, 8, 6, 9, 28, 46]

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--sample', action='append', required=True, metavar='LABEL=RUN_FOLDER',
                    help='legend label and run folder (with Rivet.yoda); repeat for every sample, '
                         'the first one is the reference of the ratio panel')
parser.add_argument('--output-dir', '-o', required=True)
parser.add_argument('--channels', nargs='+', default=['ll'], choices=sorted(CHANNEL_LABELS))
parser.add_argument('--variables', nargs='+', default=sorted(VARIABLES), choices=sorted(VARIABLES))
parser.add_argument('--normalise', action='store_true', help='scale every sample to unit area: compare shapes')
parser.add_argument('--ratio', default=None,
                    help='y range of the ratio panel, e.g. 0.5,2; default: from the ratios in the drawn range')
parser.add_argument('--title-right', default='13.6 TeV')
parser.add_argument('--process-title', default=None,
                    help='left title, e.g. "pp #rightarrow l^{+}l^{-} (LO)"; the selection of each histogram '
                         '(jets, m_ll slice) then goes as "sel: ..." in the top left of the frame')
parser.add_argument('--ratio-title', default=None,
                    help='y title of the ratio panel; default: "Ratio to <label of the first sample>"')
args = parser.parse_args()

samples = []  # (label, run folder)
for text in args.sample:
    label, folder = text.split('=', 1)
    samples.append((label, folder))
if len(samples) > len(COLORS):
    parser.error('at most %d samples' % len(COLORS))


def read_sm(folder, names):
    """SM histograms of one sample, as {histogram name: TH1D} in pb per bin, with uncertainties.
    Reads only the [rw0000] or [rw0000_nlo](SM weights) histograms of the names asked for (a Rivet.yoda with all
    weights is several hundred MB, so the patterns keep the reading fast)."""
    filename = os.path.join(folder, 'Rivet.yoda')
    if not os.path.exists(filename):
        sys.exit('No %s' % filename)
    names_regex = '|'.join(re.escape(n) for n in names)
    patterns = [r'/DYplusJets/(%s)\[rw0000(_nlo)?\]$' % names_regex]
    objects = yoda.read(filename, asdict=True, patterns=patterns)
    result = {}
    for path, obj in objects.items():
        match = re.match(r'/DYplusJets/(.+)\[rw0000(_nlo)?\]$', path)
        if not match:
            continue  # e.g. the unscaled /RAW/DYplusJets/... copies
        name = match.group(1)
        if name in result and not match.group(2):
            continue  # an NLO sample has both; the _nlo weights are the NLO ones
        bins = obj.bins()
        edges = [b.xMin() for b in bins] + [bins[-1].xMax()]
        h = ROOT.TH1D('%s_%s' % (os.path.basename(folder), name), '', len(bins),
                      array.array('d', edges))
        for i, b in enumerate(bins):
            h.SetBinContent(i + 1, b.sumW())
            h.SetBinError(i + 1, b.sumW2() ** 0.5)
        result[name] = h
    return result


def ratio_range(ratios, x_min, x_max):
    """y range of the ratio panel that shows all ratios in the drawn x range, with some room."""
    values = []
    for r in ratios:
        for i in range(1, r.GetNbinsX() + 1):
            centre = r.GetBinCenter(i)
            if x_min <= centre <= x_max and r.GetBinContent(i) > 0:
                values += [r.GetBinContent(i) - r.GetBinError(i), r.GetBinContent(i) + r.GetBinError(i)]
    if not values:
        return 0.5, 1.5
    lo, hi = max(min(values), 0.), min(max(values), 5.)
    pad = 0.1 * (hi - lo) if hi > lo else 0.1
    return max(lo - pad, 0.), hi + pad


def make_plot(name, sm, output, title, x_title, y_title, x_range, logy):
    # --process-title: the process as title, the selection as text in the frame
    selection = []
    if args.process_title:
        selection = selection_lines(name)
        title = args.process_title
    """sm: [(label, TH1D in pb per bin)] in sample order; the first is the reference."""
    canvas = ROOT.TCanvas(output, '')
    pads = plot.TwoPadSplit(0.35, 0.01, 0.01)  # same ratio-panel height as plot_DYplusJets.py

    hists = []
    for label, h_bin in sm:
        h = h_bin.Clone()
        if args.normalise and h.Integral() > 0:
            h.Scale(1. / h.Integral())
        h.Scale(1., 'width')  # -> differential cross section
        hists.append(h)
    if hists[0].Integral() <= 0:
        print('Skipping %s: no events in the reference' % output)
        return

    h_axes = [hists[0].Clone() for _ in pads]
    for h in h_axes:
        h.Reset()
    x_min, x_max = hists[0].GetXaxis().GetXmin(), hists[0].GetXaxis().GetXmax()
    if x_range is not None:
        x_min = x_min if x_range[0] is None else x_range[0]
        x_max = x_max if x_range[1] is None else x_range[1]
        for h in h_axes:
            h.GetXaxis().SetRangeUser(x_min, x_max)
    h_axes[1].GetXaxis().SetTitle(x_title)
    if args.normalise:
        y_title = '1/#sigma ' + y_title.replace(' [pb', ' [').replace('[/', '[1/').replace(' []', '')
    h_axes[0].GetYaxis().SetTitle(y_title)

    pads[0].cd()
    h_axes[0].Draw()
    bands = []
    for i, h in enumerate(hists):
        color = COLORS[i]
        band = h.Clone()
        plot.Set(band, LineColor=color, MarkerSize=0, FillColorAlpha=(color, 0.3))
        band.Draw('E2SAME')
        plot.Set(h, LineColor=color, LineWidth=3 if i == 0 else 2)
        h.Draw('HISTSAME')
        bands.append(band)

    legend = ROOT.TLegend(0.55, 0.88 - 0.05 * len(hists), 0.93, 0.90, '', 'NBNDC')
    legend.SetTextSize(0.035)
    for (label, _), h, band in zip(sm, hists, bands):
        band.SetLineWidth(h.GetLineWidth())
        legend.AddEntry(band, label, 'LF')

    if logy:
        pads[0].SetLogy()
        positive = [h.GetBinContent(i) for h in hists for i in range(1, h.GetNbinsX() + 1) if h.GetBinContent(i) > 0]
        h_axes[0].SetMinimum(0.5 * min(positive))
    else:
        h_axes[0].SetMinimum(0.)
    frame_height = 1. - pads[0].GetTopMargin() - pads[0].GetBottomMargin()
    plot.FixTopRange(pads[0], plot.GetPadYMax(pads[0]), (0.05 * len(hists) + 0.08) / frame_height)
    legend.Draw()
    # Selection, top left, level with the legend's first row; same text size as in plot_DYplusJets.py
    sel_text = ROOT.TLatex()
    sel_text.SetNDC()
    sel_text.SetTextFont(42)
    sel_text.SetTextSize(0.0232)
    sel_text.SetTextAlign(12)  # left, vertically centred
    for k, line in enumerate(selection):
        sel_text.DrawLatex(0.20, 0.865 - 0.04 * k, line)

    # Ratio panel: every sample / reference. The reference is drawn as its relative uncertainty
    # around 1; the other ratios carry only their own uncertainty.
    pads[1].cd()
    pads[1].SetGrid(0, 1)
    h_axes[1].Draw()
    # Bins without events in the reference have no ratio: they are left empty (see dyplusjets_ratio.py)
    bins = defined_bins(hists[0], x_range)
    ratios = []  # ratio histograms, for ratio_range (it skips the empty bins, which are 0 there)
    drawn = []  # ROOT only draws objects that stay alive
    for i, (h, band) in enumerate(zip(hists, bands)):
        r_band = plot.MakeRatioHist(band, hists[0], True, False)
        r_line = plot.MakeRatioHist(h, hists[0], False, False)
        drawn.append(draw_ratio_band(r_band, bins, COLORS[i]))
        drawn += draw_ratio_line(r_line, bins, COLORS[i], h.GetLineWidth())
        ratios += [r_band, r_line]
    if args.ratio:
        ratio_lo, ratio_hi = [float(x) for x in args.ratio.split(',')]
    else:
        ratio_lo, ratio_hi = ratio_range(ratios[2:] or ratios, x_min, x_max)
    plot.SetupTwoPadSplitAsRatio(pads, plot.GetAxisHist(pads[0]), plot.GetAxisHist(pads[1]),
                                 args.ratio_title or 'Ratio to %s' % sm[0][0], True, ratio_lo, ratio_hi)

    pads[0].cd()
    pads[0].GetFrame().Draw()
    pads[0].RedrawAxis()
    plot.DrawTitle(pads[0], title, 1)
    # The m_ll slice titles are long: there the right title goes in two smaller lines, as in plot_DYplusJets.py
    right_lines = args.title_right.split(', ')
    if any(label in title for label in SLICE_LABELS.values()) and len(right_lines) == 2:
        plot.DrawTitle(pads[0], right_lines[0], 3, textOffset=0.08, textSize=0.42)
        plot.DrawTitle(pads[0], right_lines[1], 3, textOffset=0.58, textSize=0.42)
    else:
        plot.DrawTitle(pads[0], args.title_right, 3)

    canvas.Print(output + '.png')
    canvas.Print(output + '.pdf')


plots = histograms(args.channels, args.variables)
names = sorted(set(p[0] for p in plots))
sm_per_sample = [(label, read_sm(folder, names)) for label, folder in samples]
os.makedirs(args.output_dir, exist_ok=True)

missing = set()
for name, output_name, title, x_title, y_title, x_range in plots:
    sm = [(label, hs[name]) for label, hs in sm_per_sample if name in hs]
    if name not in sm_per_sample[0][1]:
        missing.add(name)  # no reference, no ratio
        continue
    if len(sm) < len(samples):
        print('%s: only in %s' % (name, ', '.join(label for label, _ in sm)))
    for suffix, logy in (('lin', False), ('log', True)):
        make_plot(name, sm, os.path.join(args.output_dir, '%s_%s' % (output_name, suffix)),
                  title, x_title, y_title, x_range, logy)
if missing:
    # The ee and mm channels only have the fit variables, so missing histograms are normal there
    print('Not in the reference sample, skipped: ' + ' '.join(sorted(missing)))
