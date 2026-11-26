#!/usr/bin/env python3
# coding: utf-8

"""
Rank operators by their effect on a scaling_<hist>.json, one operator at a time.

Usage: rank_operators.py scaling_zj_ll_pTll.json [cvalue=1] [--sort total|linear|shape]

Columns (in %, except signif and the bins; operator set to `cvalue`, all others 0):
    total    SM-weighted change of the whole histogram, linear + quadratic
    linear                -"-                         , interference term only
    bin min  most negative change in one bin
    bin max  most positive change in one bin
    shape    bin max - bin min, the spread of the ratio to the SM. 0 = pure rescaling.
    signif   shape / sqrt(delta_min^2 + delta_max^2), in standard deviations: is the shape real in the
             simulation? delta = MC uncertainty of the change in the bin of bin min and bin max (spread of the
             event weights / sqrt(N), stored with the terms). Below ~3 the shape can be simulation noise.
             n/a if one of the two bins has no estimated uncertainty (e.g. a single MC event).
    min@bin  bin of bin min (0 = first bin)
    max@bin  bin of bin max

bin min, bin max, shape, signif, min@bin, and max@bin use every bin with SM events. Empty bins carry no information.
"""

import argparse
import json
import math

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('file', help='scaling_<hist>.json from get_scaling.py')
parser.add_argument('cvalue', nargs='?', type=float, default=1., help='Wilson coefficient value (default 1)')
parser.add_argument('--sort', choices=['total', 'linear', 'shape'], default='total', help='sort by |total|, linear, or by shape')
args = parser.parse_args()
wilson_coeff = args.cvalue

# === Read the scaling file ===
with open(args.file) as scaling_file:
    scaling = json.load(scaling_file)
sm_xsec = scaling['sm_vals'] # SM cross section per bin, pb
sm_xsec_total = sum(sm_xsec)
used_bins = [bin_idx for bin_idx, sm_bin in enumerate(sm_xsec) if sm_bin > 0] # bins with SM events

# Linear terms A_b (one operator) and quadratic terms B_b (the same operator twice), with their MC uncertainties,
# cross terms are not used
linear_terms, quad_terms = {}, {}
linear_uncerts, quad_uncerts = {}, {}
for term_params, term_values, term_uncerts in scaling['terms']:
    if len(term_params) == 1:
        linear_terms[term_params[0]] = term_values
        linear_uncerts[term_params[0]] = term_uncerts
    elif term_params[0] == term_params[1]:
        quad_terms[term_params[0]] = term_values
        quad_uncerts[term_params[0]] = term_uncerts


# === Rate and shape effect for each operator ===
rows = []
for operator in linear_terms:
    no_quad_term = [0.] * len(sm_xsec) # an operator without quadratic term (safety, if scaling is run for linear terms only)
    linear_term, linear_uncert = linear_terms[operator], linear_uncerts[operator]
    quad_term, quad_uncert = quad_terms.get(operator, no_quad_term), quad_uncerts.get(operator, no_quad_term)

    # effect per bin: e_b = A_b * c + B_b * c^2
    total_effect = [linear_term[bin_idx] * wilson_coeff + quad_term[bin_idx] * wilson_coeff**2 for bin_idx in range(len(sm_xsec))]
    linear_effect = [linear_term[bin_idx] * wilson_coeff for bin_idx in range(len(sm_xsec))]

    # rate change of the whole histogram, linear + quadratic
    total_rate_change = sum(sm_bin * effect_bin for sm_bin, effect_bin in zip(sm_xsec, total_effect)) / sm_xsec_total * 100. # in %
    linear_rate_change = sum(sm_bin * effect_bin for sm_bin, effect_bin in zip(sm_xsec, linear_effect)) / sm_xsec_total * 100. # in %

    # shape: spread of the effect over the bins, highest bin minus lowest bin
    min_bin = min(used_bins, key=lambda bin_idx: total_effect[bin_idx])
    max_bin = max(used_bins, key=lambda bin_idx: total_effect[bin_idx])
    shape = total_effect[max_bin] - total_effect[min_bin]

    # MC uncertainty of the change in a bin: delta = sqrt( (delta_A * c)^2 + (delta_B * c^2)^2 ),
    # uncertainties of A_b * c and B_b * c^2 added in quadrature
    def effect_uncert(bin_idx):
        return math.hypot(linear_uncert[bin_idx] * wilson_coeff, quad_uncert[bin_idx] * wilson_coeff**2)

    # significance of the shape: is it real in the simulation ? or noise ? 
    # delta = MC uncertainty of the change in the bin of bin min and bin max 
    # (spread of the event weights / sqrt(N), stored with the terms in scaling_<hist>.json)
    bin_min_uncert, bin_max_uncert = effect_uncert(min_bin), effect_uncert(max_bin)
    if bin_min_uncert > 0 and bin_max_uncert > 0:
        signif = shape / math.hypot(bin_min_uncert, bin_max_uncert)
    else:
        signif = None # None if one of the two bins has no estimated uncertainty (e.g. a single MC event)

    rows.append({
        'operator': operator,
        'total': total_rate_change,
        'linear': linear_rate_change,
        'bin_min': total_effect[min_bin] * 100.,
        'bin_max': total_effect[max_bin] * 100.,
        'shape': shape * 100.,
        'signif': signif,
        'min_bin': min_bin,
        'max_bin': max_bin,
        })
    
rows.sort(key=lambda row: -abs(row[args.sort]))

# === Print the results ===
# Operators that are zero in every used bin do not enter this histogram
zero_operators = sorted(row['operator'] for row in rows if row['bin_min'] == 0 and row['bin_max'] == 0)

print('%s, c = %g, one operator at a time, sorted by %s, %d/%d bins used' % (
    args.file, wilson_coeff, args.sort, len(used_bins), len(sm_xsec)))
print('%-10s %9s %9s %9s %9s %9s %9s %8s %8s' % ('operator', 'total %', 'linear %', 'bin min %', 'bin max %',
                                                  'shape %', 'signif', 'min@bin', 'max@bin'))
for row in rows:
    if row['operator'] in zero_operators:
        continue
    signif_str = 'n/a' if row['signif'] is None else '%.1f' % row['signif']
    print('%-10s %+9.3f %+9.3f %+9.3f %+9.3f %9.3f %9s %8d %8d' % (
        row['operator'], row['total'], row['linear'], row['bin_min'], row['bin_max'],
        row['shape'], signif_str, row['min_bin'], row['max_bin']))
print('zero in this histogram: ' + ' '.join(zero_operators))