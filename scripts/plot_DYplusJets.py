#!/usr/bin/env python3
"""Plot the DYplusJets observables: SM vs several SMEFT hypotheses, with a ratio panel.

Same style as makePlot.py (plotting.py, ModTDRStyle), but it loops over the variables,
channels of RivetPlugins/DYplusJets.cc and knows their axis titles. Also plots the number of jets.

Input : <input-dir>/scaling/scaling_zj_<channel>_<variable>.json and scaling_ll_nJets.json,
        from scripts/scaling_DYplusJets.sh
Output: <outdir>/zj_<channel>_<variable>_{lin,log}.{png,pdf} and <outdir>/ll_nJets_{lin,log}.{png,pdf}

Example, from the EFT2Obs folder:
  python scripts/plot_DYplusJets.py -i test-dyplusjets -c cards/DYjets/config.json \\
      --draw chj1=0.3:4 chu=0.3:2 "chj1=0.3,chu=0.3:8" --ratio 0.8,1.2
"""
import argparse
import glob
import json
import os
import sys

import ROOT

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plotting as plot  # noqa: E402
from eftscaling import EFTScaling  # noqa: E402

ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(ROOT.kTRUE)
ROOT.TH1.AddDirectory(False)
plot.ModTDRStyle()

# variable name in DYplusJets.cc: (x-axis title, unit)
VARIABLES = {
    # dilepton system
    'mll': ('m_{ll}', 'GeV'),
    'pTll': ('p_{T}^{ll}', 'GeV'),
    'yll': ('|y_{ll}|', ''),
    'etall': ('#eta_{ll}', ''),
    'phill': ('#phi_{ll}', ''),
    'cosThetaCS': ('cos#theta^{*}_{CS}', ''),
    'cosThetaCS_mll0': ('cos#theta^{*}_{CS}', ''),
    'cosThetaCS_mll1': ('cos#theta^{*}_{CS}', ''),
    'cosThetaCS_mll2': ('cos#theta^{*}_{CS}', ''),
    'cosThetaCS_mll3': ('cos#theta^{*}_{CS}', ''),
    'phiStar': ('#phi*_{#eta}', ''),
    # leptons, pT ordered
    'pTlep1': ('p_{T}^{l_{1}}', 'GeV'),
    'pTlep2': ('p_{T}^{l_{2}}', 'GeV'),
    'etalep1': ('#eta_{l_{1}}', ''),
    'etalep2': ('#eta_{l_{2}}', ''),
    'philep1': ('#phi_{l_{1}}', ''),
    'philep2': ('#phi_{l_{2}}', ''),
    # leading jet, and all jets
    'pTj': ('p_{T}^{j}', 'GeV'),
    'absyj': ('|y_{j}|', ''),
    'yj': ('|y_{j}|', ''),
    'etaj': ('#eta_{j}', ''),
    'phij': ('#phi_{j}', ''),
    'HT': ('H_{T}', 'GeV'),
    # Z + leading jet system
    'ystarZj': ('y* = |y_{ll} - y_{j}|/2', ''),
    'yboostZj': ('y_{b} = |y_{ll} + y_{j}|/2', ''),
    'ybPlusystar': ('y_{b} + y* = max(|y_{ll}|, |y_{j}|)', ''),
    'dPhiZj': ('#Delta#phi(ll, j)', ''),
    'zeppenfeld': ('|y_{ll} - (y_{j_{1}} + y_{j_{2}})/2|', ''),
}
# cos theta*_CS slices: MLL_SLICES in DYplusJets.cc, added to the plot title
SLICE_LABELS = {
    'cosThetaCS_mll0': '25 < m_{ll} < 81 GeV',
    'cosThetaCS_mll1': '81 < m_{ll} < 101 GeV',
    'cosThetaCS_mll2': '101 < m_{ll} < 150 GeV',
    'cosThetaCS_mll3': '150 < m_{ll} < 2000 GeV',
}
# Upper end of the x axis, so a long tail doesn't squash the rest. Only for the plot: the bins
# above stay in the histogram and in the scaling files.
X_MAX = {'pTll': 400, 'pTj': 500, 'HT': 800}
CHANNEL_LABELS = {'ll': 'l^{+}l^{-}', 'ee': 'e^{+}e^{-}', 'mm': '#mu^{+}#mu^{-}'}

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--input-dir', '-i', required=True,
                    help='run folder; the scaling_*.json files are read from <input-dir>/scaling')
parser.add_argument('--config', '-c', required=True, help='the config.json used for the gridpack')
parser.add_argument('--output-dir', '-o', default=None, help='default: <input-dir>/plots_eft')
parser.add_argument('--draw', nargs='+', required=True, metavar='PAR=X[,PAR=X]:COLOR',
                    help='one hypothesis per argument, e.g. chj1=0.3:4 "chj1=0.3,chu=0.3:8"')
parser.add_argument('--channels', nargs='+', default=['ll'], choices=sorted(CHANNEL_LABELS))
parser.add_argument('--variables', nargs='+', default=sorted(VARIABLES), choices=sorted(VARIABLES))
parser.add_argument('--translate', default='resources/translate_root_DY.json',
                    help='json file: operator name -> ROOT label')
parser.add_argument('--ratio', default='0.9,1.1', help='y range of the ratio panel')
parser.add_argument('--title-right', default='SMEFTsim3, 13 TeV')
parser.add_argument('--show-unc', action='store_true', help='draw the statistical uncertainty of the EFT terms')
parser.add_argument('--no-square', action='store_true', help='drop the quadratic terms')
parser.add_argument('--no-cross', action='store_true', help='drop the cross terms')
args = parser.parse_args()

with open(args.config) as jsonfile:
    KNOWN_PARAMETERS = {p['name'] for p in json.load(jsonfile)['parameters']}
TRANSLATIONS = {}
if os.path.exists(args.translate):
    with open(args.translate) as jsonfile:
        TRANSLATIONS = json.load(jsonfile)


def parse_hypothesis(text):
    """'chj1=0.3,chu=0.3:8' -> ({'chj1': 0.3, 'chu': 0.3}, 8, legend label)"""
    values_part, color = text.rsplit(':', 1)
    values = {}
    labels = []
    for item in values_part.split(','):
        name, value = item.split('=')
        if name not in KNOWN_PARAMETERS:
            sys.exit('Unknown operator "%s": it is not in %s' % (name, args.config))
        values[name] = float(value)
        labels.append('%s=%g' % (TRANSLATIONS.get(name, name), float(value)))
    return values, int(color), ', '.join(labels)


def smallest_positive_height(hists):
    heights = [h.GetBinContent(i) for h in hists for i in range(1, h.GetNbinsX() + 1)]
    heights = [x for x in heights if x > 0]
    return min(heights) if heights else None


def make_ratio(h, h_sm, with_errors):
    """Ratio to the SM. Bins without SM events have no ratio: draw 1 instead of a drop to 0."""
    ratio = plot.MakeRatioHist(h, h_sm, with_errors, False)
    for i in range(1, ratio.GetNbinsX() + 1):
        if h_sm.GetBinContent(i) <= 0:
            ratio.SetBinContent(i, 1.)
            ratio.SetBinError(i, 0.)
    return ratio


def make_plot(filename, output, title, x_title, y_title, x_max, hypotheses, logy):
    scaling = EFTScaling.fromJSON(filename)

    canvas = ROOT.TCanvas(output, '')
    pads = plot.TwoPadSplit(0.27, 0.01, 0.01)

    h_reference = scaling.getNominalTH1('nominal')  # cross section per bin [pb]
    h_sm = h_reference.Clone()
    h_sm.Scale(1., 'width')  # -> differential cross section
    if h_sm.Integral() <= 0:
        print('Skipping %s: no SM events in this histogram' % filename)
        return False

    h_axes = [h_sm.Clone() for _ in pads]
    for h in h_axes:
        h.Reset()
    if x_max is not None:
        for h in h_axes:
            h.GetXaxis().SetRangeUser(h.GetXaxis().GetXmin(), x_max)
    h_axes[1].GetXaxis().SetTitle(x_title)
    h_axes[0].GetYaxis().SetTitle(y_title)

    pads[0].cd()
    h_axes[0].Draw()

    legend = ROOT.TLegend(0.60, 0.88 - 0.06 * (len(hypotheses) + 1), 0.92, 0.91, '', 'NBNDC')
    legend.SetTextSize(0.035)
    legend.AddEntry(h_sm, 'SM', 'L')
    plot.Set(h_sm, LineColor=1, LineWidth=3)
    h_sm.Draw('HISTSAME')

    hists = [h_sm]
    bands = []  # same length as hists[1:]; ROOT only draws objects that stay alive
    for values, color, label in hypotheses:
        h = scaling.getScaled(h_reference, values, lin_terms=True, square_terms=not args.no_square,
                              cross_terms=not args.no_cross)
        h.Scale(1., 'width')
        plot.Set(h, LineColor=color, LineWidth=2)
        if args.show_unc:
            h_err = h.Clone()
            plot.Set(h_err, LineColor=color, LineWidth=2, MarkerColor=color, MarkerSize=0, FillColorAlpha=(color, 0.3))
            h_err.Draw('E2SAME')
            bands.append(h_err)
        h.Draw('HISTSAME')
        legend.AddEntry(bands[-1] if args.show_unc else h, label, 'LF' if args.show_unc else 'L')
        hists.append(h)

    # y range: leave room for the legend on top. Bins can be empty in a low-statistics region.
    if logy:
        pads[0].SetLogy()
        h_axes[0].SetMinimum(0.5 * smallest_positive_height(hists))
    else:
        h_axes[0].SetMinimum(0.)
    # The frame is 0.66 of the pad height; the legend takes 0.06 per row
    plot.FixTopRange(pads[0], plot.GetPadYMax(pads[0]), (0.06 * (len(hypotheses) + 1) + 0.08) / 0.66)
    legend.Draw()

    # Ratio panel: hypothesis / SM
    pads[1].cd()
    pads[1].SetGrid(0, 1)
    h_axes[1].Draw()
    ratios = []
    for h_err in bands:
        ratios.append(make_ratio(h_err, h_sm, True))
        ratios[-1].Draw('E2SAME')
    for h in hists:
        ratios.append(make_ratio(h, h_sm, False))
        ratios[-1].Draw('HISTSAME')
    ratio_lo, ratio_hi = [float(x) for x in args.ratio.split(',')]
    plot.SetupTwoPadSplitAsRatio(pads, plot.GetAxisHist(pads[0]), plot.GetAxisHist(pads[1]),
                                 'Ratio to SM', True, ratio_lo, ratio_hi)

    pads[0].cd()
    pads[0].GetFrame().Draw()
    pads[0].RedrawAxis()
    plot.DrawTitle(pads[0], title, 1)
    plot.DrawTitle(pads[0], args.title_right, 3)

    canvas.Print(output + '.png')
    canvas.Print(output + '.pdf')
    return True


hypotheses = [parse_hypothesis(x) for x in args.draw]
output_dir = args.output_dir or os.path.join(args.input_dir, 'plots_eft')
os.makedirs(output_dir, exist_ok=True)

# (histogram name, title, x title, y title, x max)
plots = []
for channel in args.channels:
    for variable in args.variables:
        x_title, unit = VARIABLES[variable]
        title = 'pp #rightarrow %s + #geq1 jet' % CHANNEL_LABELS[channel]
        if variable in SLICE_LABELS:
            title += ', ' + SLICE_LABELS[variable]
        plots.append(('zj_%s_%s' % (channel, variable), title,
                      x_title + (' [%s]' % unit if unit else ''),
                      'd#sigma/d%s [pb%s]' % (x_title.split(' = ')[0], '/' + unit if unit else ''),
                      X_MAX.get(variable)))
# Bins of width 1, so the y axis is the cross section per bin. Includes events with no jet.
plots.append(('ll_nJets', 'pp #rightarrow %s + jets' % CHANNEL_LABELS['ll'],
              'Number of jets (last bin: 7 or more)', '#sigma [pb]', None))

missing = []
for name, title, x_title, y_title, x_max in plots:
    filename = os.path.join(args.input_dir, 'scaling', 'scaling_%s.json' % name)
    if not glob.glob(filename):
        missing.append(name)
        continue
    for suffix, logy in (('lin', False), ('log', True)):
        make_plot(filename, os.path.join(output_dir, '%s_%s' % (name, suffix)),
                  title, x_title, y_title, x_max, hypotheses, logy)

# The ee and mm channels only have the fit variables, so missing files are normal there
if missing:
    print('No scaling file, skipped: ' + ' '.join(missing))
