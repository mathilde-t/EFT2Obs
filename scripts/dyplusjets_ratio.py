"""Ratio panel drawing, shared by plot_DYplusJets.py (ratio to the SM) and plot_DYplusJets_SMsampleRatios.py
(ratio to the reference sample).

A ratio has no value in bins where the reference has no events (or a negative sum of weights, at
NLO). Those bins are left empty in the ratio panel: drawing 1 would read as "no effect", and 0 as a
drop that is not there. ROOT's HIST and E2 options cannot leave out a bin, so the ratio histograms
are drawn as TGraphs here, without the empty bins.
"""
import ROOT


def defined_bins(ref, x_range=None):
    """Bins (1..N) where the reference `ref` is > 0, and, with x_range = (min, max), whose centre is
    in the drawn x range (either end may be None for the axis edge)."""
    x_min, x_max = (None, None) if x_range is None else x_range
    bins = []
    for i in range(1, ref.GetNbinsX() + 1):
        centre = ref.GetBinCenter(i)
        if ref.GetBinContent(i) <= 0:
            continue
        if (x_min is not None and centre < x_min) or (x_max is not None and centre > x_max):
            continue
        bins.append(i)
    return bins


def draw_ratio_line(r, bins, color, width, style=1):
    """Draws the ratio histogram `r` as a step line over `bins`: one TGraph per run of consecutive
    bins, so the line has a gap at every bin left out. Returns the TGraphs, which must stay alive
    until the canvas is printed."""
    runs = []
    for i in bins:
        if runs and runs[-1][-1] == i - 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    graphs = []
    for run in runs:
        g = ROOT.TGraph()
        for i in run:
            g.SetPoint(g.GetN(), r.GetBinLowEdge(i), r.GetBinContent(i))
            g.SetPoint(g.GetN(), r.GetBinLowEdge(i + 1), r.GetBinContent(i))
        g.SetLineColor(color)
        g.SetLineWidth(width)
        g.SetLineStyle(style)
        g.Draw('LSAME')
        graphs.append(g)
    return graphs


def draw_ratio_band(r, bins, color, alpha=0.3):
    """Draws the uncertainty of the ratio histogram `r` over `bins` as boxes (bin width x +-error),
    like the E2 option. Returns the TGraphErrors, which must stay alive until the canvas is printed."""
    g = ROOT.TGraphErrors()
    for i in bins:
        n = g.GetN()
        g.SetPoint(n, r.GetBinCenter(i), r.GetBinContent(i))
        g.SetPointError(n, 0.5 * r.GetBinWidth(i), r.GetBinError(i))
    g.SetFillColorAlpha(color, alpha)
    g.SetLineWidth(0)
    g.Draw('2SAME')
    return g
