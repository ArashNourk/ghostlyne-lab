"""Build the Ghostlyne Registry page (docs/index.html) from results/R1.json."""
import json, sys
from universe import TARGETS, EXTERNALS
d = json.load(open("results/R1.json"))
SHORT = {"PCU334413334413": "Chip prices", "PCU33443344": "Component prices", "PCU334111334111": "Computer and server prices",
         "IPG3344S": "Chip production", "A34SNO": "Electronics orders"}
ext = {k: v[0] for k, v in EXTERNALS.items()}
for i in (1, 2, 3): ext[f"PLACEBO_{i}"] = f"Placebo {i} (random)"
rows = []
for r in d["pairs"]:
    if "p" not in r: continue
    rows.append({"t": r["target"], "x": r["external"], "g": r["ring"], "dir": r["direction"], "L": r["lag"],
                 "a": round(r["r2_2016_2020"] * 100, 1), "b": round(r["r2_2021_on"] * 100, 1), "o": round(r["r2_oos"] * 100, 1),
                 "q": round(r["q"], 3), "s": r["status"], "why": r["reason"]})
data = {"meta": d["meta"], "targets": SHORT, "targetsLong": {k: v[0] for k, v in TARGETS.items()}, "ext": ext, "rows": rows,
        "prereg": "1d6bcc8", "power": [[12, 70], [8, 48], [5, 20], [2, 5]], "p05": sum(1 for r in d["pairs"] if "p" in r and r["ring"] > 0 and r["p"] < 0.05), "preregAt": "26 Nov 2026, 17:51 ET"}
html = open("page_template.html").read().replace("/*DATA*/null", json.dumps(data, separators=(",", ":")))
out = sys.argv[1] if len(sys.argv) > 1 else "../docs/index.html"
open(out, "w").write(html); print("wrote", out, len(html))
