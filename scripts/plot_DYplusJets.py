#!/usr/bin/env python3
"""Plot the DYplusJets observables: SM vs several SMEFT hypotheses, with a ratio panel.

Same style as makePlot.py (plotting.py, ModTDRStyle), but it loops over the variables,
channels of RivetPlugins/DYplusJets.cc and knows their axis titles. Also plots the number of jets.

Input : <input-dir>/scaling/scaling_zj_<channel>_<variable>.json and scaling_ll_nJets.json,
        from scripts/scaling_DYplusJets.sh
Output: <outdir>/zj_<channel>_<variable>_{lin,log}.{png,pdf} and <outdir>/ll_nJets_{lin,log}.{png,pdf}

Example, from the EFT2Obs folder:
  python scripts/plot_DYplusJets.py -i $E -c cards/<sample>/config.json \\
      --draw chj1=1:4 chu=1:2 "chj1=1,chu=1:8" --ratio 0.8,1.2

With --top-ranked <dir>, each histogram also gets its own leading operators, read from
<dir>/ranking_rate/<histogram>.txt and <dir>/ranking_shape/<histogram>.txt (rank_operators.py):
the N leading by rate as solid lines, then the N leading by shape that are not already drawn as
dashed lines, each at the value the ranking used. Shapes below --min-signif standard deviations
(default 3) or without a significance (n/a) are skipped: they are MC noise, not physics. driver_run_DYjets_sample.sh plots this way:
  python scripts/plot_DYplusJets.py -i $E -c cards/<sample>/config.json -o outputs/<sample>/plots \\
      --channels ll ee mm --show-unc --top-ranked outputs/<sample>
"""
import argparse
import glob
import json
import os
import re
import sys

import ROOT

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plotting as plot  # noqa: E402
from eftscaling import EFTScaling  # noqa: E402

ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(ROOT.kTRUE)
ROOT.TH1.AddDirectory(False)
plot.ModTDRStyle()

# Axis titles, slice labels, x ranges, and the list of histograms: shared with plot_DYplusJets_SMsampleRatios.py
from plot_DYplusJets__labels import VARIABLES, SLICE_LABELS, CHANNEL_LABELS, histograms, selection_lines  # noqa: E402
from plot_DYplusJets__ratio import defined_bins, draw_ratio_band, draw_ratio_line  # noqa: E402
from plot_DYplusJets__readme import update_readme_date  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--input-dir', '-i', required=True,
                    help='run folder; the scaling_*.json files are read from <input-dir>/scaling')
parser.add_argument('--config', '-c', required=True, help='the config.json used for the gridpack')
parser.add_argument('--output-dir', '-o', default=None, help='default: <input-dir>/plots_eft')
parser.add_argument('--draw', nargs='+', default=[], metavar='PAR=X[,PAR=X]:COLOR',
                    help='one hypothesis per argument, e.g. chj1=1:4 "chj1=1,chu=1:8"')
parser.add_argument('--top-ranked', metavar='DIR', default=None,
                    help='also draw the leading operators of each histogram from DIR/ranking_{rate,shape}/')
parser.add_argument('--n-top', type=int, default=3, help='with --top-ranked: operators per ranking (default 3)')
parser.add_argument('--min-signif', type=float, default=3.,
                    help='with --top-ranked: smallest significance of a drawn shape, in standard deviations (default 3)')
parser.add_argument('--channels', nargs='+', default=['ll'], choices=sorted(CHANNEL_LABELS))
parser.add_argument('--variables', nargs='+', default=sorted(VARIABLES), choices=sorted(VARIABLES))
parser.add_argument('--translate', default='resources/translate_root_DY.json',
                    help='json file: operator name -> ROOT label')
parser.add_argument('--ratio', default='0.9,1.1', help='y range of the ratio panel')
parser.add_argument('--title-right', default='SMEFTsim3, 13 TeV')
parser.add_argument('--process-title', default=None,
                    help=r'left title: the generated process, e.g. "\mathrm{pp} \rightarrow \ell^{+}\ell^{-} + \leq \mathrm{2j}\ (\mathrm{LO})" (ROOT math mode, see plot_DYplusJets__labels.py). '
                         'The selection of each histogram (jets, m_ll slice) then goes as "sel: ..." above SM '
                         '(with --top-ranked only)')
parser.add_argument('--show-unc', action='store_true', help='draw the statistical uncertainty of the EFT terms')
parser.add_argument('--no-square', action='store_true', help='drop the quadratic terms')
parser.add_argument('--no-cross', action='store_true', help='drop the cross terms')
args = parser.parse_args()
if not args.draw and not args.top_ranked:
    parser.error('nothing to draw: give --draw and/or --top-ranked')

with open(args.config) as jsonfile:
    KNOWN_PARAMETERS = {p['name'] for p in json.load(jsonfile)['parameters']}
TRANSLATIONS = {}
if os.path.exists(args.translate):
    with open(args.translate) as jsonfile:
        TRANSLATIONS = json.load(jsonfile)


def parse_hypothesis(text):
    """'chj1=1,chu=1:8' -> ({'chj1': 1.0, 'chu': 1.0}, 8, legend label)"""
    values_part, color = text.rsplit(':', 1)
    values = {}
    labels = []
    for item in values_part.split(','):
        name, value = item.split('=')
        if name not in KNOWN_PARAMETERS:
            sys.exit('Unknown operator "%s": it is not in %s' % (name, args.config))
        values[name] = float(value)
        labels.append('%s=%g' % (TRANSLATIONS.get(name, name), float(value)))
    # line style 1 = solid; group None = not from a ranking (see top_ranked_hypotheses)
    return values, int(color), ', '.join(labels), 1, None


# --top-ranked: colours of the rate-ranked (solid) and then the shape-ranked (dashed) operators
TOP_COLORS = [2, 4, 8, 6, 9, 28, 46, 30, 38, 41]
# --top-ranked: the coefficient values of the rankings (one value in practice), shown in the legend
TOP_RANKED_VALUES = set()


def read_ranking(filename):
    """rank_operators.py output -> (value of the Wilson coefficient, [(operator, total %, shape %, signif)] in
    ranking order). Columns: operator, total %, linear %, bin min %, bin max %, shape %, signif, min@bin,
    max@bin. total % is the change of the whole histogram (rate), shape % the max - min spread of the
    ratio to the SM over the bins (bin max % - bin min %); both at this value. signif is the shape in
    standard deviations of its MC uncertainty, None for n/a."""
    with open(filename) as f:
        lines = f.read().splitlines()
    value = float(re.search(r'c = ([^,]+),', lines[0]).group(1))
    rows = []
    for line in lines[2:]:
        # operator lines start with the name; skip '...', 'zero in this histogram:' and its continuation
        fields = line.split()
        if len(fields) == 9 and not line[0].isspace():
            signif = None if fields[6] == 'n/a' else float(fields[6])
            rows.append((fields[0], float(fields[1]), float(fields[5]), signif))
    return value, rows


def top_ranked_hypotheses(name):
    """Hypotheses for histogram `name`: N leading by rate, then N leading by shape not yet drawn.
    Each is tagged with its group, 'rate' or 'shape', so the legend can show them in two columns.
    The label gets the number the operator was ranked by: the rate change (total %, with sign) for
    the rate operators, the shape change (max - min, %) for the shape operators.
    Shapes below --min-signif or without significance (n/a) are skipped: there the spread of the bins
    is within the MC uncertainty, e.g. one bin with a single event, so it is noise, not a shape."""
    chosen = []  # (operator, value, line style, group, number for the label)
    for kind, style in (('rate', 1), ('shape', 2)):
        filename = os.path.join(args.top_ranked, 'ranking_%s' % kind, '%s.txt' % name)
        if not os.path.exists(filename):
            print('No ranking %s, its operators are not drawn' % filename)
            continue
        value, rows = read_ranking(filename)
        new = [row for row in rows if row[0] not in [c[0] for c in chosen]]
        if kind == 'shape':
            new = [row for row in new if row[3] is not None and row[3] >= args.min_signif]
        for op, total, shape, _ in new[:args.n_top]:
            number = '%+.2f%%' % total if kind == 'rate' else '%.2f%%' % shape
            chosen.append((op, value, style, kind, number))
    hypotheses = []
    for i, (op, value, style, kind, number) in enumerate(chosen):
        values, color, _, _, _ = parse_hypothesis('%s=%g:%d' % (op, value, TOP_COLORS[i % len(TOP_COLORS)]))
        # All ranked operators have the same value; it is shown once, below the SM entry
        TOP_RANKED_VALUES.add(value)
        hypotheses.append((values, color, '%s: %s' % (TRANSLATIONS.get(op, op), number), style, kind))
    return hypotheses


def smallest_positive_height(hists):
    """Smallest bin content > 0 over all histograms (under- and overflow not included), or None if
    every bin is empty or negative. Sets the lower end of the log-scale y axis: empty bins (0) cannot
    be shown on a log scale, and negative weights can occur. make_plot skips histograms without SM
    events, so there it is never None."""
    heights = [h.GetBinContent(i) for h in hists for i in range(1, h.GetNbinsX() + 1)]
    heights = [x for x in heights if x > 0]
    return min(heights) if heights else None


def make_plot(filename, output, title, x_title, y_title, x_range, hypotheses, logy):
    """One plot from the scaling file `filename` (scaling_<histogram>.json): upper panel the SM and
    each hypothesis as differential cross section (per bin width), lower panel their ratio to the
    SM. hypotheses: (values, colour, label, line style, group) from parse_hypothesis or
    top_ranked_hypotheses. x_range: (min, max), either may be None for the axis edge; None = full
    axis. Writes output.png and output.pdf. Returns False (nothing written) if the histogram has no
    SM events, else True."""
    scaling = EFTScaling.fromJSON(filename)
    # --process-title: the generated process as title, the selection as text above SM
    selection = []
    if args.process_title:
        selection = selection_lines(os.path.basename(filename)[len('scaling_'):-len('.json')])
        title = args.process_title

    canvas = ROOT.TCanvas(output, '')
    # Height of the ratio panel: fraction of the canvas below the split, including the x-axis
    # labels. Larger = taller ratio panel; the upper frame and the legend room adapt to it.
    ratio_height = 0.35
    pads = plot.TwoPadSplit(ratio_height, 0.01, 0.01)

    h_reference = scaling.getNominalTH1('nominal')  # cross section per bin [pb]
    h_sm = h_reference.Clone()
    h_sm.Scale(1., 'width')  # -> differential cross section
    if h_sm.Integral() <= 0:
        print('Skipping %s: no SM events in this histogram' % filename)
        return False

    h_axes = [h_sm.Clone() for _ in pads]
    for h in h_axes:
        h.Reset()
    if x_range is not None:
        x_min = h_sm.GetXaxis().GetXmin() if x_range[0] is None else x_range[0]
        x_max = h_sm.GetXaxis().GetXmax() if x_range[1] is None else x_range[1]
        for h in h_axes:
            h.GetXaxis().SetRangeUser(x_min, x_max)
    h_axes[1].GetXaxis().SetTitle(x_title)
    h_axes[0].GetYaxis().SetTitle(y_title)

    pads[0].cd()
    h_axes[0].Draw()

    plot.Set(h_sm, LineColor=1, LineWidth=3)
    h_sm.Draw('HISTSAME')

    hists = [h_sm]
    bands = []  # same length as hists[1:]; ROOT only draws objects that stay alive
    entries = {None: [], 'rate': [], 'shape': []}  # legend entries (object, label, option) per group
    for values, color, label, style, group in hypotheses:
        h = scaling.getScaled(h_reference, values, lin_terms=True, square_terms=not args.no_square,
                              cross_terms=not args.no_cross)
        h.Scale(1., 'width')
        plot.Set(h, LineColor=color, LineWidth=2, LineStyle=style)
        if args.show_unc:
            h_err = h.Clone()
            plot.Set(h_err, LineColor=color, LineWidth=2, MarkerColor=color, MarkerSize=0, FillColorAlpha=(color, 0.3))
            h_err.Draw('E2SAME')
            bands.append(h_err)
        h.Draw('HISTSAME')
        entries[group].append((bands[-1] if args.show_unc else h, label, 'LF' if args.show_unc else 'L'))
        hists.append(h)

    # Legend, filled row by row. A cell is an entry, a text-only header (str), or empty (None).
    sm_entry = (h_sm, 'SM', 'L')
    grouped = bool(entries['rate'] or entries['shape'])
    if grouped:
        # --top-ranked: two columns with a header each, left the operators leading in shape
        # (dashed), right those leading in rate (solid). SM is not a cell here: it gets its own
        # small legend left of them, next to the first operator row (see below)
        n_columns = 2
        # The number after each operator is the one it was ranked by (see top_ranked_hypotheses)
        cells = ['Shape (max#minusmin)', 'Rate (total change)']
        for i in range(max(len(entries['shape']), len(entries['rate']))):
            cells += [entries[group][i] if i < len(entries[group]) else None for group in ('shape', 'rate')]
        cells += entries[None]  # --draw hypotheses below, two per row
    else:
        # Only --draw: SM + hypotheses. More than 4 entries go in two columns over the full frame
        # width, so the legend has half the rows and the y axis needs less room above the curves.
        cells = [sm_entry] + entries[None]
        n_columns = 2 if len(cells) > 4 else 1
    n_rows = (len(cells) + n_columns - 1) // n_columns
    # Legend size. The room the legend takes, and so the empty space above the curves, is set by
    # the row height; the text size is a fraction of it (smaller fraction = more space between lines).
    legend_row_height = 0.04     # height of one legend row, as a fraction of the pad height
    legend_text_fraction = 0.65   # entry text size / row height
    header_text_fraction = 0.58   # "Leading by ..." text size / row height (a bit smaller than the entries)
    # With --top-ranked: SM, the shape block, and the rate block are three equally wide columns
    # between x = 0.20 and 0.95, so their symbols are equally spaced along the x axis
    sm_legend_width = (0.95 - 0.20) / 3
    if grouped:
        legend_x1 = 0.20 + sm_legend_width
    else:
        legend_x1 = 0.20 if n_columns == 2 else 0.60
    legend_x2, legend_y1, legend_y2 = 0.95, 0.88 - legend_row_height * n_rows, 0.91
    legend = ROOT.TLegend(legend_x1, legend_y1, legend_x2, legend_y2, '', 'NBNDC')
    legend.SetNColumns(n_columns)
    legend.SetTextSize(legend_text_fraction * legend_row_height)
    headers = []  # (text, row, column): drawn after the legend, see below
    for i, cell in enumerate(cells):
        if isinstance(cell, str):
            headers.append((cell, i // n_columns, i % n_columns))
        if cell is None or isinstance(cell, str):
            legend.AddEntry(ROOT.nullptr, '', '')  # keeps the cell empty
        else:
            legend.AddEntry(*cell)

    # y range: leave room for the legend on top. Bins can be empty in a low-statistics region.
    if logy:
        pads[0].SetLogy()
        h_axes[0].SetMinimum(0.5 * smallest_positive_height(hists))
    else:
        h_axes[0].SetMinimum(0.)
    # The legend takes legend_row_height of the pad height per row (+ 0.08 spacing); FixTopRange
    # wants that as a fraction of the upper frame: the pad minus its top margin and the ratio panel
    frame_height = 1. - pads[0].GetTopMargin() - pads[0].GetBottomMargin()
    plot.FixTopRange(pads[0], plot.GetPadYMax(pads[0]), (legend_row_height * n_rows + 0.08) / frame_height)
    legend.Draw()
    # Headers as separate, smaller text, left-aligned with the coloured boxes below them.
    # TLegend centres the box at margin/2 in each column, with half width 0.35*margin, where
    # margin = fMargin (default 0.25) * column width; rows split the legend height evenly.
    # (The legend's own Get*NDC() are only set when it is painted, so use the values it was made with.)
    # TLegend spreads its rows over the whole box, so a cell is a little taller than legend_row_height.
    column_width = (legend_x2 - legend_x1) / n_columns
    margin = legend.GetMargin() * column_width
    cell_height = (legend_y2 - legend_y1) / n_rows
    header_text = ROOT.TLatex()
    header_text.SetNDC()
    header_text.SetTextFont(42)
    header_text.SetTextSize(header_text_fraction * legend_row_height)
    header_text.SetTextAlign(12)  # left, vertically centred
    for text, row, column in headers:
        header_text.DrawLatex(legend_x1 + column * column_width + 0.15 * margin,
                              legend_y2 - (row + 0.5) * cell_height, text)
    if grouped:
        # SM legend: one cell, at the height of the first operator row (row 1, below the headers),
        # with the same text size and the same absolute symbol width as the main legend
        # A second selection line (the m_ll slice) takes the SM row: SM and c move one row down
        shift = max(len(selection) - 1, 0)
        sm_legend = ROOT.TLegend(0.20, legend_y2 - (2 + shift) * cell_height, 0.20 + sm_legend_width,
                                 legend_y2 - (1 + shift) * cell_height, '', 'NBNDC')
        sm_legend.SetTextSize(legend_text_fraction * legend_row_height)
        sm_legend.SetMargin(margin / sm_legend_width)
        sm_legend.AddEntry(*sm_entry)
        sm_legend.Draw()
        # Selection: first line in the header row, level with the shape and rate headers
        for k, line in enumerate(selection):
            header_text.DrawLatex(0.20 + 0.15 * margin, legend_y2 - (0.5 + k) * cell_height, line)
        # Below SM: the value of the ranked operators, in the style of the headers
        if TOP_RANKED_VALUES:
            header_text.DrawLatex(0.20 + 0.15 * margin, legend_y2 - (2.5 + shift) * cell_height,
                                  'c = ' + ', '.join('%g' % v for v in sorted(TOP_RANKED_VALUES)))

    # Ratio panel: hypothesis / SM
    pads[1].cd()
    pads[1].SetGrid(0, 1)
    h_axes[1].Draw()
    # Bins without SM events have no ratio: they are left empty (see plot_DYplusJets__ratio.py)
    bins = defined_bins(h_sm, x_range)
    ratios = []  # ROOT only draws objects that stay alive
    for h_err in bands:
        ratios.append(draw_ratio_band(plot.MakeRatioHist(h_err, h_sm, True, False), bins, h_err.GetLineColor()))
    for h in hists:
        ratios += draw_ratio_line(plot.MakeRatioHist(h, h_sm, False, False), bins, h.GetLineColor(),
                                  h.GetLineWidth(), h.GetLineStyle())
    ratio_lo, ratio_hi = [float(x) for x in args.ratio.split(',')]
    plot.SetupTwoPadSplitAsRatio(pads, plot.GetAxisHist(pads[0]), plot.GetAxisHist(pads[1]),
                                 'Ratio to SM', True, ratio_lo, ratio_hi)

    pads[0].cd()
    pads[0].GetFrame().Draw()
    pads[0].RedrawAxis()
    plot.DrawTitle(pads[0], title, 1)
    # The m_ll slice titles are long and reach the right title: there, split the right title at its
    # comma into two smaller lines, the model below and the energy above it
    right_lines = args.title_right.split(', ')
    if any(label in title for label in SLICE_LABELS.values()) and len(right_lines) == 2:
        plot.DrawTitle(pads[0], right_lines[0], 3, textOffset=0.08, textSize=0.42)
        plot.DrawTitle(pads[0], right_lines[1], 3, textOffset=0.58, textSize=0.42)
    else:
        plot.DrawTitle(pads[0], args.title_right, 3)

    canvas.Print(output + '.png')
    canvas.Print(output + '.pdf')
    return True


hypotheses = [parse_hypothesis(x) for x in args.draw]
output_dir = args.output_dir or os.path.join(args.input_dir, 'plots_eft')
os.makedirs(output_dir, exist_ok=True)

# (histogram name, output name, title, x title, y title, x range)
plots = histograms(args.channels, args.variables)

missing = []
for name, output_name, title, x_title, y_title, x_range in plots:
    filename = os.path.join(args.input_dir, 'scaling', 'scaling_%s.json' % name)
    if not glob.glob(filename):
        if name not in missing:
            missing.append(name)
        continue
    plot_hypotheses = hypotheses + (top_ranked_hypotheses(name) if args.top_ranked else [])
    for suffix, logy in (('lin', False), ('log', True)):
        make_plot(filename, os.path.join(output_dir, '%s_%s' % (output_name, suffix)),
                  title, x_title, y_title, x_range, plot_hypotheses, logy)

# The ee and mm channels only have the fit variables, so missing files are normal there
if missing:
    print('No scaling file, skipped: ' + ' '.join(missing))

# Date of the plots in the README of the folder, so it always matches the plots
update_readme_date(output_dir)
