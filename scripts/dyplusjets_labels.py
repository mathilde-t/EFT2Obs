"""Axis titles, channel labels, and x ranges of the DYplusJets histograms (RivetPlugins/DYplusJets.cc).

Shared by plot_DYplusJets.py (SM vs SMEFT hypotheses) and plot_DYplusJets_SMsampleRatios.py (SM of several
samples), so both label and cut the axes in the same way.
"""

# variable name in DYplusJets.cc: (x-axis title, unit)
VARIABLES = {
    # dilepton system
    'mll': ('m_{ll}', 'GeV'),
    'pTll': ('p_{T}^{ll}', 'GeV'),
    'yll': ('y_{ll}', ''),
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
    'yj': ('y_{j}', ''),
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
# x range drawn, (min, max), None = the histogram edge. So a long, nearly empty tail doesn't squash
# the rest. Only for the plot: the bins outside stay in the histogram and in the scaling files.
# A dict of ranges gives one plot per range, named <histogram>_<key>: mll goes from 25 to 2000 GeV,
# but most events are around the Z peak, so it gets the full range and a short one around the peak.
X_RANGE = {'pTll': (None, 400), 'pTj': (None, 500), 'HT': (None, 800),
           'mll': {'full': None, 'short': (50, 150)}}
CHANNEL_LABELS = {'ll': 'l^{+}l^{-}', 'ee': 'e^{+}e^{-}', 'mm': '#mu^{+}#mu^{-}'}


def selection_lines(name):
    """Selection of histogram <name>, as lines of text for the plot (with --process-title): the jet
    requirement of DYplusJets.cc (jets: anti-kT 0.4, pT > 20 GeV) and, for the m_ll slices, their
    m_ll range. ll_nJets has no jet requirement (its first bin has the events with no jet)."""
    if name == 'll_nJets':
        return ['sel: jets p_{T} > 20 GeV']
    jets = '#geq2 jets' if name.endswith('_zeppenfeld') else '#geq1 jet'
    lines = ['sel: %s (p_{T} > 20 GeV)' % jets]
    variable = name.split('_', 2)[2]  # zj_<channel>_<variable>
    if variable in SLICE_LABELS:
        lines.append(SLICE_LABELS[variable])
    return lines


def histograms(channels, variables):
    """The histograms to plot, as (histogram name, output name, title, x title, y title, x range):
    zj_<channel>_<variable>, one entry per x range, and ll_nJets at the end."""
    plots = []
    for channel in channels:
        for variable in variables:
            x_title, unit = VARIABLES[variable]
            title = 'pp #rightarrow %s + #geq1 jet' % CHANNEL_LABELS[channel]
            if variable in SLICE_LABELS:
                title += ', ' + SLICE_LABELS[variable]
            name = 'zj_%s_%s' % (channel, variable)
            x_ranges = X_RANGE.get(variable)
            if not isinstance(x_ranges, dict):
                x_ranges = {None: x_ranges}
            for key, x_range in x_ranges.items():
                plots.append((name, name if key is None else '%s_%s' % (name, key), title,
                              x_title + (' [%s]' % unit if unit else ''),
                              'd#sigma/d%s [pb%s]' % (x_title.split(' = ')[0], '/' + unit if unit else ''),
                              x_range))
    # Bins of width 1, so the y axis is the cross section per bin. Includes events with no jet.
    plots.append(('ll_nJets', 'll_nJets', 'pp #rightarrow %s + jets' % CHANNEL_LABELS['ll'],
                  'Number of jets (last bin: 7 or more)', '#sigma [pb]', None))
    return plots
