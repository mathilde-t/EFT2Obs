#!/usr/bin/env python3
"""Rank operators by their effect on a scaling_<hist>.json, one operator at a time.

Usage: rank_operators.py scaling_zj_ll_pTll.json [value=0.3] [--sort total|shape]

Columns (all in %, operator set to `value`, all others 0):
  total     SM-weighted change of the whole histogram (linear + quadratic)
  linear    the same, interference term only
  bin min   smallest change in one bin
  bin max   largest change in one bin
  shape     spread of the *normalised* ratio: each bin's ratio to SM divided by the total ratio,
            max - min over the bins. 0 = pure rescaling (no shape change), so this is the part
            of the effect a fit to a normalised distribution would still see.
  max@bin   bin where the normalised ratio deviates most from 1 (0 = first bin)

Only bins with at least --min-frac (default 1%) of the largest SM bin are used for bin min/max and
shape, so nearly empty bins don't dominate. With few events, raise it: a single-event bin can pass 1%.
"""
import argparse
import json

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('file', help='scaling_<hist>.json from get_scaling.py')
parser.add_argument('value', nargs='?', type=float, default=0.3, help='Wilson coefficient value (default 0.3)')
parser.add_argument('--sort', choices=['total', 'shape'], default='total', help='sort by |total| or by shape')
parser.add_argument('--min-frac', type=float, default=0.01,
                    help='use only bins with SM >= this fraction of the largest SM bin (default 0.01)')
args = parser.parse_args()
value = args.value

with open(args.file) as f:
    d = json.load(f)
sm = d['sm_vals']
total = sum(sm)
good = [i for i, s in enumerate(sm) if s >= args.min_frac * max(sm)]
lin, quad = {}, {}
for params, vals, _ in d['terms']:
    if len(params) == 1:
        lin[params[0]] = vals
    elif params[0] == params[1]:
        quad[params[0]] = vals

rows = []
for p in lin:
    q = quad.get(p, [0.] * len(sm))
    eff = [lin[p][i] * value + q[i] * value * value for i in range(len(sm))]
    inc = sum(s * e for s, e in zip(sm, eff)) / total
    lin_only = sum(s * l for s, l in zip(sm, lin[p])) / total * value
    # normalised ratio: shape change after removing the overall rescaling
    norm = {i: (1. + eff[i]) / (1. + inc) - 1. for i in good}
    shape = max(norm.values()) - min(norm.values())
    worst = max(norm, key=lambda i: abs(norm[i]))
    rows.append(dict(p=p, inc=inc, lin=lin_only, lo=min(eff[i] for i in good),
                     hi=max(eff[i] for i in good), shape=shape, worst=worst))

key = 'inc' if args.sort == 'total' else 'shape'
rows.sort(key=lambda r: -abs(r[key]))

print('%s, c = %g, one operator at a time, sorted by %s, %d/%d bins used' % (args.file, value, args.sort, len(good), len(sm)))
print('%-10s %9s %9s %9s %9s %9s %8s' % ('operator', 'total %', 'linear %', 'bin min %', 'bin max %',
                                         'shape %', 'max@bin'))
for r in rows:
    if r['lo'] == 0 and r['hi'] == 0:
        continue
    print('%-10s %+9.3f %+9.3f %+9.3f %+9.3f %9.3f %8d' % (r['p'], 100 * r['inc'], 100 * r['lin'],
          100 * r['lo'], 100 * r['hi'], 100 * r['shape'], r['worst']))
print('zero in this histogram: ' + ' '.join(sorted(r['p'] for r in rows if r['lo'] == 0 and r['hi'] == 0)))
