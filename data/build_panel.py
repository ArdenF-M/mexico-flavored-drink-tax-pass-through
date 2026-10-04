#!/usr/bin/env python3
"""Build a beverage price panel from PROFECO's 'Quien es Quien en los Precios'
(QQP) open-data archives.

Input : one or more QQP_YYYY.rar archives (streamed via bsdtar, no extraction)
Output: data/panel_<year>.csv, one row per (month, group, marca, cadena,
        estado) with count / mean / median / p25 / p75 of price per litre.

The QQP 'Refrescos Envasados' category bundles carbonated soft drinks, bottled
water, juices, flavoured/sparkling water and isotonic drinks. We keep that
category, parse the package volume from the `presentacion` string, and classify
each row into one of three tax-relevant groups:

    sugary : carbonated / flavoured drinks with added sugar  (taxed since 2014)
    diet   : light / zero / sin-azucar variants (added non-caloric sweetener;
             untaxed 2014-2025, taxed at 1.50 pesos/litre from Jan 2026)
    water  : plain bottled water (never taxed; the control group)

Price per litre = precio / litres parsed from the presentation string.
"""
import csv
import io
import os
import re
import subprocess
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PROFECO_DIR = os.path.join(HERE, 'profeco')

CATEGORY = 'Refrescos Envasados'

VOL_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s*(ml|mililitros|lt|lts|litros?|l)\b', re.I)
DIET_KW = ('light', 'zero', 'cero', 'sin az', 'sin cal', 'be-light', 'b-light', 'diet', 'max')
FLAVOR_KW = ('sabor', 'limon', 'fizz', 'infusion', 'naranj', 'té', 'te ', 'manzana',
             'fresa', 'uva', 'toronj', 'piña', 'frut', 'jamaica', 'horchata')
WATER_BRANDS = {'ciel', 'epura', 'e-pura', 'bonafont', 'peñafiel', 'penafiel',
                'santa maria', 'santa maría', 'agua', 'electropura', 'ciel. light'}


def parse_month(date):
    """Return 'YYYY-MM' from either YYYY/MM/DD or DD/MM/YYYY."""
    d = (date or '').strip()
    m = re.match(r'(\d{4})[/-](\d{1,2})', d)
    if m and 1 <= int(m.group(2)) <= 12:
        return '%s-%02d' % (m.group(1), int(m.group(2)))
    m = re.match(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', d)
    if m and 1 <= int(m.group(2)) <= 12:
        return '%s-%02d' % (m.group(3), int(m.group(2)))
    return None


def parse_litres(pres):
    m = VOL_RE.search(pres or '')
    if not m:
        return None
    val = float(m.group(1).replace(',', '.'))
    unit = m.group(2).lower()
    if unit.startswith('ml') or unit.startswith('mil'):
        val /= 1000.0
    return val


def classify(producto, marca, presentacion):
    blob = '%s %s' % (marca.lower(), presentacion.lower())
    prod = (producto or '').strip().lower()
    # Plain still or sparkling water: never taxed ("agua natural" is out of LIEPS scope).
    if prod in ('agua sin gas', 'agua con gas') and not any(k in blob for k in FLAVOR_KW):
        return 'water'
    if any(k in blob for k in DIET_KW):
        return 'diet'
    if prod in ('refresco', 'agua con gas', 'bebida varias', 'té preparado', 'te preparado',
                'jugo de fruta', 'bebidas hidratantes'):
        return 'sugary'
    return None


def size_bucket(litres):
    if litres <= 0.4:
        return 'can'
    if litres <= 0.75:
        return '600ml'
    if litres <= 1.05:
        return '1L'
    if litres <= 1.6:
        return '1.5L'
    if litres <= 2.1:
        return '2L'
    if litres <= 3.1:
        return '3L'
    return 'bulk'


def stream_rows(archive, member):
    """Yield dict rows from one CSV inside the rar archive."""
    p = subprocess.Popen(['bsdtar', '-xOf', archive, member], stdout=subprocess.PIPE)
    reader = csv.DictReader(
        io.TextIOWrapper(p.stdout, encoding='utf-8-sig', errors='replace'))
    for row in reader:
        yield row
    p.wait()


def members(archive):
    out = subprocess.check_output(['bsdtar', '-tf', archive]).decode()
    return [m for m in out.splitlines() if m.lower().endswith('.csv')]


def main(archive):
    year = re.search(r'(\d{4})', os.path.basename(archive)).group(1)
    agg = defaultdict(list)
    nonlocal_drops = [0]
    n_read = n_kept = 0
    for mem in members(archive):
        for row in stream_rows(archive, mem):
            n_read += 1
            if row.get('categoria') != CATEGORY:
                continue
            litres = parse_litres(row.get('presentacion', ''))
            group = classify(row.get('producto', ''), row.get('marca', ''),
                             row.get('presentacion', ''))
            if litres is None or litres <= 0 or litres > 25 or group is None:
                continue
            try:
                price = float(row['precio'])
            except (ValueError, KeyError, TypeError):
                continue
            if price <= 0:
                continue
            month = parse_month(row.get('fecha_registro', ''))
            if month is None:
                nonlocal_drops[0] += 1
                continue
            size = size_bucket(litres)
            key = (month, group, size, row.get('marca', '').strip(),
                   row.get('cadena_comercial', '').strip(),
                   row.get('estado', '').strip())
            agg[key].append(price / litres)
            n_kept += 1
        print('  %-24s read=%d kept=%d' % (mem, n_read, n_kept), file=sys.stderr)

    out = os.path.join(HERE, 'panel_%s.csv' % year)
    with open(out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['month', 'group', 'size', 'marca', 'cadena', 'estado', 'n',
                    'mean_ppl', 'median_ppl', 'p25_ppl', 'p75_ppl'])
        for (month, group, size, marca, cadena, estado), vals in agg.items():
            vals.sort()
            n = len(vals)
            mean = sum(vals) / n
            med = vals[n // 2]
            p25 = vals[n // 4]
            p75 = vals[(3 * n) // 4]
            w.writerow([month, group, size, marca, cadena, estado, n,
                        round(mean, 4), round(med, 4), round(p25, 4), round(p75, 4)])
    print('wrote %s (%d cells, %d obs, %d rows read, %d undated dropped)' %
          (out, len(agg), n_kept, n_read, nonlocal_drops[0]), file=sys.stderr)


if __name__ == '__main__':
    for a in sys.argv[1:]:
        print('== %s ==' % a, file=sys.stderr)
        main(a)
