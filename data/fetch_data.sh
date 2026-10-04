#!/usr/bin/env bash
# Download the raw PROFECO "Quien es Quien en los Precios" open-data archives.
# The file.php tokens are the ones published on
# https://datos.profeco.gob.mx/datos_abiertos/qqp.php (checked 1 October 2026).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p profeco
base="https://datos.profeco.gob.mx/datos_abiertos/file.php?t="

dl () {  # token  filename
  if [ -f "profeco/$2" ]; then echo "have profeco/$2"; return; fi
  echo "downloading $2 ..."
  curl -fL --retry 2 "$base$1" -o "profeco/$2"
}

dl 2de3505b2d37e7db72557a09262d95c5 QQP_2024.rar
dl b9540b181657c2bc7735892091e81f96 QQP_2025.rar
dl 9d62040eae6dcc63e36b8ac821427647 QQP_2026.rar

# metadata + data dictionary
curl -fL "$base""42ed7dad4da507b9d536d9b737e7912d" -o profeco/QQP_metadatos.csv
curl -fL "$base""2de3505b2d37e7db72557a09262d95c7" -o profeco/QQP_diccionario.csv

echo "done. now run:"
echo "  python3 data/build_panel.py data/profeco/QQP_2024.rar data/profeco/QQP_2025.rar data/profeco/QQP_2026.rar"
