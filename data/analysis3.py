#!/usr/bin/env python3
"""Pass-through of Mexico's flavoured-drink tax: difference-in-differences with
brand x size and month fixed effects.

    price_(brand,size,month) = a + b1*(sugary x post26) + b2*(diet x post26)
                                 + gamma_(brand,size) + delta_(month) + e

Water brands (never taxed) are the control group. Weights = number of price
quotes. SEs clustered by month. Pass-through = coefficient / statutory quota
change. The panel is collapsed to brand x size x month first, which removes
composition effects and keeps the design matrix small.
"""
import csv
import json
import os
from collections import defaultdict

import numpy as np
import statsmodels.api as sm

HERE = os.path.dirname(os.path.abspath(__file__))
SIZES = ('can', '600ml', '1L', '1.5L', '2L', '3L')
DTAX = {
    '2025': {'sugary': 1.6451 - 1.5737, 'diet': 0.0},
    '2026': {'sugary': 3.0818 - 1.6451, 'diet': 1.5000 - 0.0},
}


def load_cells():
    rows = []
    for y in ('2024', '2025', '2026'):
        with open(os.path.join(HERE, 'panel_%s.csv' % y)) as f:
            for r in csv.DictReader(f):
                if r['size'] not in SIZES:
                    continue
                rows.append((r['month'], r['group'], r['size'], r['marca'],
                             r['cadena'], int(r['n']), float(r['mean_ppl'])))
    return rows


def collapse(cells, keys):
    """Weighted mean of price per litre grouped by `keys` (tuple per cell)."""
    agg = defaultdict(lambda: [0.0, 0])
    for c in cells:
        k = tuple(c[i] for i in keys)
        agg[k][0] += c[5] * c[6]
        agg[k][1] += c[5]
    out = []
    for k, (num, n) in agg.items():
        out.append({'key': k, 'n': n, 'mean': num / n})
    return out


def design(dat, post_year, fake_start=None):
    units = sorted(set('%s|%s' % (d['key'][3], d['key'][2]) for d in dat))
    months = sorted(set(d['key'][0] for d in dat))
    uidx = {u: i for i, u in enumerate(units)}
    midx = {m: i for i, m in enumerate(months)}
    X, y, w, grp = [], [], [], []
    for d in dat:
        month, group, size, marca = d['key'][0], d['key'][1], d['key'][2], d['key'][3]
        if fake_start is not None:
            post = 1 if month >= fake_start else 0
        else:
            post = 1 if month[:4] == post_year else 0
        sug = 1 if group == 'sugary' else 0
        die = 1 if group == 'diet' else 0
        row = [1, sug * post, die * post]
        ui = uidx['%s|%s' % (marca, size)]
        row += [1 if ui == k else 0 for k in range(1, len(units))]
        mi = midx[month]
        row += [1 if mi == k else 0 for k in range(1, len(months))]
        X.append(row)
        y.append(d['mean'])
        w.append(d['n'])
        grp.append(month)
    return (np.array(X, float), np.array(y, float), np.array(w, float),
            np.array(grp), len(units), len(months))


def fit(dat, post_year='2026', fake_start=None):
    X, y, w, g, nu, nm = design(dat, post_year, fake_start)
    res = sm.WLS(y, X, weights=w).fit(cov_type='cluster', cov_kwds={'groups': g})
    return res, nu - 1, nm - 1


def show(res, label, dtau=None):
    print('\n=== %s ===' % label)
    print('  sugary x post = %+.4f  se=%.4f  p=%.4f  95%%CI[%+.3f,%+.3f]'
          % (res.params[1], res.bse[1], res.pvalues[1],
             res.conf_int()[1][0], res.conf_int()[1][1]))
    print('  diet   x post = %+.4f  se=%.4f  p=%.4f  95%%CI[%+.3f,%+.3f]'
          % (res.params[2], res.bse[2], res.pvalues[2],
             res.conf_int()[2][0], res.conf_int()[2][1]))
    if dtau:
        print('  pass-through:  sugary %.2f   diet %.2f'
              % (res.params[1] / dtau['sugary'],
                 res.params[2] / dtau['diet'] if dtau['diet'] else float('nan')))


def main():
    cells = load_cells()
    dat = collapse(cells, (0, 1, 2, 3))
    print('brand-size-month cells: %d (from %d raw cells, %d quotes)'
          % (len(dat), len(cells), sum(c[5] for c in cells)))

    out = {}
    HEAD = ('600ml', '1L', '2L', '3L')   # exclude 'can' (miscoded water) and '1.5L'
    head = [d for d in dat if d['key'][2] in HEAD]
    r26, nsug, nmon = fit(head, '2026')
    show(r26, 'HEADLINE DiD post=2026, sizes 600ml/1L/2L/3L', DTAX['2026'])
    print('  [brand-size FE: %d, month FE: %d, cells: %d]' % (nsug, nmon, len(head)))
    rall, _, _ = fit(dat, '2026')
    show(rall, 'all sizes incl. can/1.5L (sensitivity)', DTAX['2026'])
    out['did2026_all_sizes'] = {'b_sugary': float(rall.params[1]),
                                'p_sugary': float(rall.pvalues[1])}
    out['did2026'] = {
        'b_sugary': float(r26.params[1]), 'se_sugary': float(r26.bse[1]),
        'p_sugary': float(r26.pvalues[1]),
        'b_diet': float(r26.params[2]), 'se_diet': float(r26.bse[2]),
        'p_diet': float(r26.pvalues[2]),
        'pt_sugary': float(r26.params[1] / DTAX['2026']['sugary']),
        'pt_diet': float(r26.params[2] / DTAX['2026']['diet']),
        'n_cells': len(head)}

    headpre = [d for d in head if d['key'][0] < '2026-01']
    r25, _, _ = fit(headpre, '2025')
    show(r25, 'DiD post=2025 on pre-2026 sample (quota barely moved; expect ~0)',
         DTAX['2025'])
    out['did2025'] = {'b_sugary': float(r25.params[1]), 'p_sugary': float(r25.pvalues[1]),
                      'b_diet': float(r25.params[2]), 'p_diet': float(r25.pvalues[2]),
                      'pt_sugary': float(r25.params[1] / DTAX['2025']['sugary'])}

    for fs, lbl in (('2025-07', 'placebo fake post = Jul-2025'),
                    ('2025-04', 'placebo fake post = Apr-2025'),
                    ('2024-07', 'placebo fake post = Jul-2024')):
        r, _, _ = fit(headpre, fake_start=fs)
        print('\n=== %s ===\n  sugary x post = %+.4f (p=%.3f)   diet x post = %+.4f (p=%.3f)'
              % (lbl, r.params[1], r.pvalues[1], r.params[2], r.pvalues[2]))
        out['placebo_%s' % fs] = [float(r.params[1]), float(r.pvalues[1]),
                                  float(r.params[2]), float(r.pvalues[2])]

    print('\n=== pass-through by package size (post=2026) ===')
    out['by_size'] = {}
    for s in SIZES:
        sub = [d for d in dat if d['key'][2] == s]
        if len(set(d['key'][3] for d in sub)) < 5:
            continue
        r, _, _ = fit(sub, '2026')
        pt_s = r.params[1] / DTAX['2026']['sugary']
        pt_d = r.params[2] / DTAX['2026']['diet'] if DTAX['2026']['diet'] else float('nan')
        print('  %-6s sugary b=%+.3f (p=%.3f) PT=%.2f | diet b=%+.3f (p=%.3f) PT=%.2f'
              % (s, r.params[1], r.pvalues[1], pt_s, r.params[2], r.pvalues[2], pt_d))
        out['by_size'][s] = [float(r.params[1]), float(r.pvalues[1]), float(pt_s),
                             float(r.params[2]), float(r.pvalues[2]), float(pt_d)]

    print('\n=== pass-through by retail chain (post=2026) ===')
    datc = collapse(cells, (0, 1, 2, 3, 4))
    out['by_chain'] = {}
    for cad in sorted(set(c[4] for c in cells)):
        sub = [d for d in datc if d['key'][4] == cad]
        if len(set(d['key'][3] for d in sub)) < 5 or len(sub) < 300:
            continue
        try:
            r, _, _ = fit(sub, '2026')
        except Exception:
            continue
        pt_s = r.params[1] / DTAX['2026']['sugary']
        out['by_chain'][cad] = [float(pt_s), float(r.params[1]), float(r.pvalues[1])]
    for cad, v in sorted(out['by_chain'].items(), key=lambda x: -x[1][0])[:12]:
        print('  %-24s PT sugary=%.2f (b=%+.3f p=%.3f)' % (cad[:24], v[0], v[1], v[2]))

    with open(os.path.join(HERE, 'results3.json'), 'w') as f:
        json.dump(out, f, indent=2)
    print('\nwrote results3.json')


if __name__ == '__main__':
    main()
