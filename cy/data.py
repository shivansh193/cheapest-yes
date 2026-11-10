"""Dataset loading. Raw downloads live in data/raw (git-ignored); see docs/DATA.md for sources."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
UCI_CSV = RAW / "uci_shoppers" / "online_shoppers_intention.csv"
UCI_URL = "https://archive.ics.uci.edu/static/public/468/online+shoppers+purchasing+intention+dataset.zip"
CRITEO_GZ = RAW / "criteo-uplift-v2.1.csv.gz"
CRITEO_URL = "https://huggingface.co/datasets/criteo/criteo-uplift/resolve/main/criteo-research-uplift-v2.1.csv.gz"
# Compact copy of the UCI sessions shipped with the app so the simulator runs on Render.
# UCI data is CC BY 4.0 (Sakar & Kastro 2018, doi:10.24432/C5F88Q); redistribution with attribution is allowed.
UCI_PARQUET = ROOT / "artifacts" / "uci_sessions.parquet"


def load_uci() -> pd.DataFrame:
    if UCI_PARQUET.exists():
        return pd.read_parquet(UCI_PARQUET)
    if not UCI_CSV.exists():
        _download_uci()
    df = pd.read_csv(UCI_CSV)
    UCI_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(UCI_PARQUET, index=False)
    return df


def _download_uci() -> None:
    import io
    import urllib.request
    import zipfile

    UCI_CSV.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(UCI_URL, timeout=120) as r:
        zipfile.ZipFile(io.BytesIO(r.read())).extractall(UCI_CSV.parent)


def load_criteo(nrows: int | None = 2_000_000) -> pd.DataFrame:
    if not CRITEO_GZ.exists():
        import urllib.request

        CRITEO_GZ.parent.mkdir(parents=True, exist_ok=True)
        print(f"downloading Criteo uplift v2.1 (~311 MB) from {CRITEO_URL}")
        urllib.request.urlretrieve(CRITEO_URL, CRITEO_GZ)
    return pd.read_csv(CRITEO_GZ, nrows=nrows)
