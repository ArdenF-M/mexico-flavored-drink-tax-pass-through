# The data used in this project

Two layers of data live here, deliberately separated so the repository stays
small enough for GitHub while remaining fully verifiable.

## Layer 1 — the data the numbers are calculated from (in this repository)

These are committed and are the files the analysis reads:

| File | Rows | Contents |
|---|---|---|
| `panel_2024.csv` | 120,437 | brand × package size × chain × state × month price-per-litre cells, Jan–Dec 2024 |
| `panel_2025.csv` | 108,648 | same, Jan–Dec 2025 |
| `panel_2026.csv` | 66,614 | same, Jan–Jul 2026 |
| `profeco/QQP_diccionario.csv` | — | official PROFECO data dictionary for the source files |
| `profeco/QQP_metadatos.csv` | — | official PROFECO metadata (field types, coverage) |

Each row is one cell: the mean shelf price per litre (VAT included) of a given
brand–presentation in a given commercial chain in a given state in a given month,
together with the number of underlying price quotes, the modal package volume and
the tax classification (`sugary` / `diet` / `water`). `results3.json` and
`tables.md` in this folder are the outputs computed from these panels.

These panels are built from **1,448,631 individual shelf-price observations**.

## Layer 2 — the raw government archives (NOT committed; re-downloadable)

The primary source is PROFECO's open-data programme *Quién es Quién en los
Precios* (QQP), published monthly as RAR archives of one row per
product–presentation–store–date:

<https://datos.profeco.gob.mx/datos_abiertos/qqp.php>

The three archives used, as downloaded on **1 October 2026**:

| Archive | Size | SHA-256 (first 16 hex) | Coverage |
|---|---|---|---|
| `QQP_2024.rar` | 91.6 MB | `740e1498e9d7fae7` | 12 monthly files, Jan–Dec 2024 |
| `QQP_2025.rar` | 81.2 MB | `41ca4cd962e696f9` | 12 monthly files, Jan–Dec 2025 |
| `QQP_2026.rar` | 186.5 MB | `172bd1a44c17ac35` | 7 monthly files, Jan–Jul 2026 |

**Why they are not in the repository.** GitHub rejects any individual file larger
than 100 MB, and `QQP_2026.rar` is 186 MB, so the archives cannot be pushed as
regular files. They are instead downloaded by a single command:

```bash
bash data/fetch_data.sh
```

That script hits the same `file.php` endpoints published on the page above
(the tokens are pinned in the script) and writes the three `.rar` files here.
The `.rar` files are listed in `.gitignore`, so they never enter the repository.

Alternatively, the same three archives can be attached to a GitHub *Release* on
this repository (release assets allow files up to 2 GB) and linked from the
README if you want the bytes archived on GitHub itself.

## Rebuilding everything

```bash
pip install -r requirements.txt
bash data/fetch_data.sh
python3 data/build_panel.py data/profeco/QQP_2024.rar \
                            data/profeco/QQP_2025.rar \
                            data/profeco/QQP_2026.rar
python3 data/analysis3.py      # -> results3.json
python3 data/make_tables.py    # -> tables.md
```

`build_panel.py` streams the RAR members without extracting them (it needs
`bsdtar`, present on macOS and most Linux distributions). It parses the package
volume from the free-text presentation field, classifies every row as
sugary / diet / water from the statutory definition of the tax base, and
aggregates to the panel cells above — so the numbers in the paper can be traced
from a raw government price quote to a regression coefficient.

## Statutory tax values (the treatment)

Not data files but inputs to the pass-through calculation; taken from the LIEPS
and the annual DOF update agreements, listed in the paper's reference list:

| Year | Added-sugar quota (peso/L) | *Edulcorante* quota (peso/L) |
|---|---|---|
| 2024 | 1.5737 | 0 |
| 2025 | 1.6451 | 0 |
| 2026 | 3.0818 | 1.5000 |
