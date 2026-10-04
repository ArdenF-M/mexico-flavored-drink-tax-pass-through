#!/usr/bin/env python3
"""Emit the exhibit tables used in the paper from the built panel + results."""
import csv
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SIZES = ('600ml', '1L', '2L', '3L')


def wm(cells):
    n = sum(c['n'] for c in cells)
    return sum(c['mean'] * c['n'] for c in cells) / n if n else None


def main():
    rows = []
    for y in ('2024', '2025', '2026'):
        with open(os.path.join(HERE, 'panel_%s.csv' % y)) as f:
            for r in csv.DictReader(f):
                rows.append(r)
    out = []
    A = out.append

    A('## Table 1. Data coverage (PROFECO QQP, category "Refrescos Envasados")')
    A('')
    A('| Year | Months | Sugary quotes | Diet quotes | Water quotes | Total |')
    A('|---|---|---|---|---|---|')
    for y in ('2024', '2025', '2026'):
        sub = [r for r in rows if r['month'][:4] == y]
        g = defaultdict(int)
        for r in sub:
            g[r['group']] += int(r['n'])
        ms = len(set(r['month'] for r in sub))
        A('| %s | %d | %s | %s | %s | %s |' % (
            y, ms, f"{g['sugary']:,}", f"{g['diet']:,}", f"{g['water']:,}",
            f"{sum(g.values()):,}"))
    A('| **Total** | **%d** | | | | **%s** |' % (
        len(set(r['month'] for r in rows)), f"{sum(int(r['n']) for r in rows):,}"))
    A('')
    A('Distinct retail chains: %d. Distinct states: %d. Distinct brands: %d.'
      % (len(set(r['cadena'] for r in rows)), len(set(r['estado'] for r in rows)),
         len(set(r['marca'] for r in rows))))
    A('')

    A('## Table 2. Mean price per litre (pesos), by tax group / package size / year')
    A('')
    A('| Size | Group | 2024 | 2025 | 2026 | 2025 vs 2024 | 2026 vs 2025 |')
    A('|---|---|---|---|---|---|---|')
    for s in SIZES:
        for g in ('sugary', 'diet', 'water'):
            vals = {}
            for y in ('2024', '2025', '2026'):
                cells = [{'n': int(r['n']), 'mean': float(r['mean_ppl'])}
                         for r in rows if r['size'] == s and r['group'] == g
                         and r['month'][:4] == y]
                if cells:
                    vals[y] = wm(cells)
            if len(vals) == 3:
                A('| %s | %s | %.2f | %.2f | %.2f | %+.2f | %+.2f |' % (
                    s, g, vals['2024'], vals['2025'], vals['2026'],
                    vals['2025'] - vals['2024'], vals['2026'] - vals['2025']))
    A('')

    res = json.load(open(os.path.join(HERE, 'results3.json')))
    A('## Table 3. Difference-in-differences estimates (post = Jan-2026 reform)')
    A('')
    A('| Specification | Sugary coeff | SE | p | Implied pass-through |')
    A('|---|---|---|---|---|')
    d = res['did2026']
    A('| Headline (sizes 600ml/1L/2L/3L) | %+.3f | %.3f | %.4f | %.2f |' % (
        d['b_sugary'], d['se_sugary'], d['p_sugary'], d['pt_sugary']))
    A('| Headline: diet (edulcorante) | %+.3f | %.3f | %.4f | %.2f |' % (
        d['b_diet'], d['se_diet'], d['p_diet'], d['pt_diet']))
    a = res['did2026_all_sizes']
    A('| All sizes incl. can/1.5L (sugary) | %+.3f | . | %.4f | . |' % (
        a['b_sugary'], a['p_sugary']))
    A('')

    A('## Table 4. Validation: placebo (fake) reform dates, pre-2026 sample')
    A('')
    A('| Fake reform date | Sugary coeff | p | Diet coeff | p |')
    A('|---|---|---|---|---|')
    for f in ('2025-07', '2025-04', '2024-07'):
        v = res['placebo_%s' % f]
        A('| %s | %+.3f | %.3f | %+.3f | %.3f |' % (f, v[0], v[1], v[2], v[3]))
    A('| *real* 2026 reform | %+.3f | %.4f | %+.3f | %.4f |' % (
        d['b_sugary'], d['p_sugary'], d['b_diet'], d['p_diet']))
    A('')

    A('## Table 5. Pass-through by package size')
    A('')
    A('| Size | Sugary coeff | p | Pass-through | Diet coeff | p | Pass-through |')
    A('|---|---|---|---|---|---|---|')
    for s, v in res['by_size'].items():
        A('| %s | %+.3f | %.3f | %.2f | %+.3f | %.3f | %.2f |' % (
            s, v[0], v[1], v[2], v[3], v[4], v[5]))
    A('')

    A('## Table 6. Pass-through by retail chain (top 14)')
    A('')
    A('| Chain | Sugary coeff | p | Pass-through |')
    A('|---|---|---|---|')
    items = sorted(res['by_chain'].items(), key=lambda x: -x[1][0])[:14]
    for cad, v in items:
        A('| %s | %+.3f | %.3f | %.2f |' % (cad, v[1], v[2], v[0]))
    A('')

    with open(os.path.join(HERE, 'tables.md'), 'w') as f:
        f.write('\n'.join(out))
    print('\n'.join(out))


if __name__ == '__main__':
    main()
