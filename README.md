# Pass-through of Mexico's tax on flavored drinks

📄 **[Read the paper](paper.pdf)** — *Pass-Through of Mexico's Tax on Flavored
Drinks: Evidence from the January 2026 Reform* (21 pp.), in this repository at the
link above.

**What it asks.** How much of Mexico's specific excise (IEPS) on flavored drinks
reaches retail shelf prices? The analysis pivots on the **January 2026 reform**,
which raised the quota on added-sugar drinks from **1.6451 to 3.0818 pesos per
liter** and, for the first time, taxed non-caloric **"edulcorante" (diet) drinks at
1.5000 pesos per liter**.

**Answer.** Pass-through is **essentially full for added-sugar drinks (1.01)** and
**partial for diet drinks (0.38)**. Consumers, not bottlers or retailers, absorbed
the 2026 increase.

| Added-sugar coefficient | 95% CI | Pass-through |
|---|---|---|
| **+1.445 peso/L** (s.e. 0.092, p<0.001) | [+1.264, +1.626] | **1.01** |
| Diet (edulcorante) +0.576 (s.e. 0.113) | [+0.354, +0.798] | 0.38 |

Placebo reform dates (no actual tax change) produce effects **5–11x smaller**, so
the result is not a general price trend.

## Data (all public, all real)

1. **Retail prices — PROFECO "Quién es Quién en los Precios"** open-data archives
   (`QQP_2024.rar`, `QQP_2025.rar`, `QQP_2026.rar`), one row per
   product–store–date price. Category `Refrescos Envasados`, Jan-2024 to Jul-2026.
   **1,448,631 price observations**, 69 chains, 44 states, 46 brands.
   <https://datos.profeco.gob.mx/datos_abiertos/qqp.php>
2. **Statutory quota (the tax)** — LIEPS art. 2, I, G) plus the annual DOF
   agreements. <https://www.diputados.gob.mx/LeyesBiblio/pdf/LIEPS.pdf>,
   <https://sidof.segob.gob.mx/notas/5772359>
3. Published demand studies for validation (Colchero et al.; Seiler et al.).

`data/README.md` documents exactly where the raw archives come from, their sizes
and their SHA-256 checksums.

## How it was analysed

Difference-in-differences with **brand-by-package-size and month fixed effects**,
weighted by price quotes, standard errors clustered by month:

```
price(brand,size,month) = a + b1*(sugary x post2026) + b2*(diet x post2026)
                            + gamma(brand x size) + delta(month) + e
```

Plain bottled water (never taxed) is the control group. Pass-through =
coefficient / statutory quota change. `can` and `1.5 L` package buckets, whose
per-liter water prices are noisy, are excluded from the headline.

## Reproduce

```bash
pip install -r requirements.txt
bash data/fetch_data.sh                 # downloads the three QQP archives (~375 MB)
python3 data/build_panel.py data/profeco/QQP_2024.rar data/profeco/QQP_2025.rar data/profeco/QQP_2026.rar
python3 data/analysis3.py               # -> data/results3.json
python3 data/make_tables.py             # -> data/tables.md
```

Those four commands regenerate the data, the coefficients and the exhibit tables
that the paper reports. The `panel_*.csv` files are already committed, so
`analysis3.py` and `make_tables.py` can be run without re-downloading anything.

`build_panel.py` needs `bsdtar` (present on macOS/Linux) to stream the `.rar`
archives; it parses the package volume, classifies each row as sugary / diet /
water and aggregates to brand×size×chain×state×month price-per-liter cells.
Requires Python 3 and `numpy` + `statsmodels` (no pandas needed).

## Layout

```
paper.pdf               the submitted paper (21 pp.)
data/README.md          where the raw data comes from, with checksums
data/build_panel.py     prices -> tidy panel (parse volume, classify, price/liter)
data/analysis3.py       DiD with fixed effects -> results3.json
data/make_tables.py     exhibit tables -> tables.md
data/panel_*.csv        built panels (one row per cell) — the data the paper uses
data/results3.json      the coefficients reported in the paper
data/tables.md          every exhibit as text
data/profeco/           raw QQP archives (git-ignored; fetch_data.sh re-downloads)
```

## What the repository shows an employer

- **The problem** — pass-through of a live 2026 tax reform (section 1).
- **The data** — public PROFECO microdata, rebuilt from primary archives.
- **The analysis** — an event-study/DiD design with placebo validation.
- **Reproducibility** — every number regenerates from the raw archives with the
  commands above.
- **The conclusion** — near-full pass-through; consumers bear the tax; the new
  diet quota under-shifts (section 6).

## Limitations

Prices, not quantities: this identifies incidence, not demand. The control group
(water) absorbs common inflation but has its own mild drift, which is why placebo
effects are non-zero and the headline should be read as slightly conservative.
