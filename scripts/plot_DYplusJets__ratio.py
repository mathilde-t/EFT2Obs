# coding: utf-8

"""
Helpers to draw the ratio panel, used by plot_DYplusJets.py (ratio to the SM) and plot_DYplusJets_SMsampleRatios.py
(ratio to the first sample).
Bins where the reference histogram is empty, or a negative sum of weights (at NLO), are left out.
Drawing 1 would read as "no effect", and 0 as a drop that is not there.
ROOT's HIST and E2 options cannot skip a bin, so the ratio is drawn as TGraphs instead.
"""

import ROOT


def defined_bins(ref_hist, x_range=None):
    """Return the bin numbers (1...N) where the ratio can be drawn: reference > 0 and bin inside the x range."""
    x_min, x_max = (None, None) if x_range is None else x_range # None = no limit on that side
    used_bins = []
    for bin_idx in range(1, ref_hist.GetNbinsX() + 1):
        bin_centre = ref_hist.GetBinCenter(bin_idx)

        # Skip empty reference bins, the ratio would be a division by 0
        if ref_hist.GetBinContent(bin_idx) <= 0:
            continue
        # Skip bins outside the drawn x range
        if (x_min is not None and bin_centre < x_min) or (x_max is not None and bin_centre > x_max):
            continue

        used_bins.append(bin_idx)
    return used_bins


def draw_ratio_line(ratio_hist, used_bins, line_color, line_width, line_style=1):
    """Draw the ratio as a step line over used_bins, with a gap where a bin is missing.
    Return the TGraphs: keep them until the canvas is saved, otherwise ROOT deletes them."""

    # Group neighbouring bins, e.g. [1, 2, 3, 6, 7] -> [[1, 2, 3], [6, 7]]: one line per group, so the gap stays empty
    bin_runs = []
    for bin_idx in used_bins:
        if bin_runs and bin_runs[-1][-1] == bin_idx - 1:
            bin_runs[-1].append(bin_idx) # neighbour of the previous bin: same group
        else:
            bin_runs.append([bin_idx]) # gap before this bin: new group

    # Draw each group as a step: a horizontal line from the low to the high edge of every bin
    graphs = []
    for the_run in bin_runs:
        step_graph = ROOT.TGraph()
        for bin_idx in the_run:
            step_graph.SetPoint(step_graph.GetN(), ratio_hist.GetBinLowEdge(bin_idx), ratio_hist.GetBinContent(bin_idx))
            step_graph.SetPoint(step_graph.GetN(), ratio_hist.GetBinLowEdge(bin_idx + 1), ratio_hist.GetBinContent(bin_idx))
        step_graph.SetLineColor(line_color)
        step_graph.SetLineWidth(line_width)
        step_graph.SetLineStyle(line_style)
        step_graph.Draw('LSAME')
        graphs.append(step_graph)
    return graphs


def draw_ratio_band(ratio_hist, used_bins, fill_color, fill_alpha=0.3):
    """Draw the uncertainty of the ratio as a transparent box per bin (bin width x +-error), only over used_bins.
    Return the TGraphErrors: keep it until the canvas is saved, otherwise ROOT deletes it."""
    band_graph = ROOT.TGraphErrors()
    for bin_idx in used_bins:
        # Box centred on the bin: half the bin width to each side, the error of the ratio up and down
        point_idx = band_graph.GetN()
        band_graph.SetPoint(point_idx, ratio_hist.GetBinCenter(bin_idx), ratio_hist.GetBinContent(bin_idx))
        band_graph.SetPointError(point_idx, 0.5 * ratio_hist.GetBinWidth(bin_idx), ratio_hist.GetBinError(bin_idx))
    band_graph.SetFillColorAlpha(fill_color, fill_alpha)
    band_graph.SetLineWidth(0) # no outline, only the filled box
    band_graph.Draw('2SAME') # option 2: filled boxes
    return band_graph
