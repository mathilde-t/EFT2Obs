# coding: utf-8

r"""
Axis titles, channel labels, and x ranges of the DYplusJets histograms (RivetPlugins/DYplusJets.cc).

Shared by
- plot_DYplusJets.py (SM vs SMEFT hypotheses) and
- plot_DYplusJets_SMsampleRatios.py (SM of several samples, ratios),
so both label and cut the axes in the same way.

All labels are in ROOT's math mode (TMathText, LaTeX syntax): ROOT switches to it for every text that contains a
backslash. Only math mode has the lepton symbol \ell; the usual TLatex (#-syntax) has none. Rules:
- one label is either math mode (\...) or TLatex (#...), never both: math mode does not know #eta, #sigma, ...
- words and units upright with \mathrm{...}, spaces as '\ ' (math mode drops plain spaces)
- raw strings r'...', so Python leaves the backslashes alone
"""

# variable name in DYplusJets.cc: (x-axis title, unit)
VARIABLES = {
    # dilepton system
    'mll': (r'm_{\ell\ell}', 'GeV'),
    'pTll': (r'p_{T}^{\ell\ell}', 'GeV'),
    'yll': (r'y_{\ell\ell}', ''),
    'etall': (r'\eta_{\ell\ell}', ''),
    'phill': (r'\phi_{\ell\ell}', ''),
    'cosThetaCS': (r'\cos\theta^{*}_{CS}', ''),
    'cosThetaCS_mll0': (r'\cos\theta^{*}_{CS}', ''),
    'cosThetaCS_mll1': (r'\cos\theta^{*}_{CS}', ''),
    'cosThetaCS_mll2': (r'\cos\theta^{*}_{CS}', ''),
    'cosThetaCS_mll3': (r'\cos\theta^{*}_{CS}', ''),
    'phiStar': (r'\phi^{*}_{\eta}', ''),
    # leptons, pT ordered
    'pTlep1': (r'p_{T}^{\ell_{1}}', 'GeV'),
    'pTlep2': (r'p_{T}^{\ell_{2}}', 'GeV'),
    'etalep1': (r'\eta_{\ell_{1}}', ''),
    'etalep2': (r'\eta_{\ell_{2}}', ''),
    'philep1': (r'\phi_{\ell_{1}}', ''),
    'philep2': (r'\phi_{\ell_{2}}', ''),
    # leading jet, and all jets
    'pTj': (r'p_{T}^{j}', 'GeV'),
    'yj': (r'y_{j}', ''),
    'etaj': (r'\eta_{j}', ''),
    'phij': (r'\phi_{j}', ''),
    'HT': (r'H_{T}', 'GeV'),
    # Z + leading jet system
    'ystarZj': (r'y^{*} = |y_{\ell\ell} - y_{j}|/2', ''),
    'yboostZj': (r'y_{b} = |y_{\ell\ell} + y_{j}|/2', ''),
    'ybPlusystar': (r'y_{b} + y^{*} = \max(|y_{\ell\ell}|, |y_{j}|)', ''),
    'dPhiZj': (r'\Delta\phi(\ell\ell, j)', ''),
    'zeppenfeld': (r'|y_{\ell\ell} - (y_{j_{1}} + y_{j_{2}})/2|', ''),
}
# cos theta*_CS slices: MLL_SLICES in DYplusJets.cc, added to the plot title
SLICE_LABELS = {
    'cosThetaCS_mll0': r'25 < m_{\ell\ell} < 81\ \mathrm{GeV}',
    'cosThetaCS_mll1': r'81 < m_{\ell\ell} < 101\ \mathrm{GeV}',
    'cosThetaCS_mll2': r'101 < m_{\ell\ell} < 150\ \mathrm{GeV}',
    'cosThetaCS_mll3': r'150 < m_{\ell\ell} < 2000\ \mathrm{GeV}',
}
# x range drawn, (min, max), None = the histogram edge. So a long, nearly empty tail doesn't squash the rest.
# Only for the plot: the bins outside stay in the histogram and in the scaling files.
# A dict of ranges gives one plot per range, named <histogram>_<key>: mll goes from 25 to 2000 GeV,
# but most events are around the Z peak, so it gets the full range and a short one around the peak.
X_RANGE = {'pTll': (None, 400),
           'pTj': (None, 500),
           'HT': (None, 800),
           'mll': {'full': None, 'short': (50, 150)}}
CHANNEL_LABELS = {'ll': r'\ell^{+}\ell^{-}',
                  'ee': r'e^{+}e^{-}',
                  'mm': r'\mu^{+}\mu^{-}'}


def selection_lines(name):
    """Selection of histogram <name>, as lines of text for the plot (with --process-title):
    the jet requirement of DYplusJets.cc (jets: anti-kT 0.4, pT > 20 GeV) and,
    for the m_ll slices, their m_ll range.
    ll_nJets has no jet requirement (its first bin has the events with no jet).
    Compact math mode: {:}, {\\geq}, {>} in braces get no extra space around them, and \\, is a thin space, so the
    line is as wide as in TLatex and stays left of the legend."""
    if name == 'll_nJets':
        return [r'\mathrm{sel{:}\ jets}\ p_{T}{>}20\,\mathrm{GeV}']
    jets_str = r'{\geq}2\,\mathrm{jets}' if name.endswith('_zeppenfeld') else r'{\geq}1\,\mathrm{jet}'
    lines = [r'\mathrm{sel{:}}\ %s\ (p_{T}{>}20\,\mathrm{GeV})' % jets_str]
    variable = name.split('_', 2)[2] # zj_<channel>_<variable>
    if variable in SLICE_LABELS:
        lines.append(SLICE_LABELS[variable])
    return lines


def axis_unit(unit, prefix=''):
    """' [unit]' for an axis title in math mode, e.g. axis_unit('GeV') -> '\\ [\\mathrm{GeV}]',
    axis_unit('GeV', 'pb/') -> '\\ [\\mathrm{pb/GeV}]'; without a unit only the prefix, '' if both are empty."""
    unit_str = prefix + unit
    return r'\ [\mathrm{%s}]' % unit_str if unit_str else ''


def histograms(channels, variables):
    """The histograms to plot, as (histogram name, output name, title, x title, y title, x range):
    zj_<channel>_<variable>, one entry per x range, and ll_nJets at the end."""
    plots = []
    for channel in channels:
        for variable in variables:
            x_title, unit = VARIABLES[variable]
            title = r'\mathrm{pp} \rightarrow %s + \geq 1\ \mathrm{jet}' % CHANNEL_LABELS[channel]
            if variable in SLICE_LABELS:
                title += ', ' + SLICE_LABELS[variable]
            name = 'zj_%s_%s' % (channel, variable)
            x_ranges = X_RANGE.get(variable)
            if not isinstance(x_ranges, dict):
                x_ranges = {None: x_ranges}
            # d sigma / d x: the symbol of x only, without its definition ('y^{*} = ...' -> 'y^{*}')
            y_title = r'\mathrm{d}\sigma/\mathrm{d}%s' % x_title.split(' = ')[0] + axis_unit(unit, 'pb/' if unit else 'pb')
            for key, x_range in x_ranges.items():
                plots.append((name, name if key is None else '%s_%s' % (name, key), title,
                              x_title + axis_unit(unit), y_title, x_range))
    # Bins of width 1, so the y axis is the cross section per bin. Includes events with no jet.
    plots.append(('ll_nJets', 'll_nJets', r'\mathrm{pp} \rightarrow %s + \mathrm{jets}' % CHANNEL_LABELS['ll'],
                  r'\mathrm{Number\ of\ jets\ (last\ bin:\ 7\ or\ more)}', r'\sigma' + axis_unit('pb'), None))
    return plots
