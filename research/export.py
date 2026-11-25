"""Export the production feature/label table (all markets, all days since 2021) for offline research.
Same loader and features as the engine; nothing here changes the live model."""
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT / "engine")); import common as G
through = pd.Timestamp.now("UTC").tz_localize(None).normalize() - pd.Timedelta(days=1)
D = G.features(G.load(ROOT / "data", through))
out = ROOT / "export"; out.mkdir(exist_ok=True); D.to_parquet(out / "features.parquet")
print(len(D), D.sym.nunique(), D.Date.min(), D.Date.max())
