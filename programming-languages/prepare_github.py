"""Extract the language rows we need from GitHub's Innovation Graph.

Clone https://github.com/github/innovationgraph (data licensed CC0 1.0) and pass the
path to its data/languages.csv. Writes data/inputs/github-innovation-graph-pushers.csv:
quarterly unique pushers per language for GB, US, IN and WORLD (sum of all
economies, excluding the EU aggregate), plus the total over every language GitHub
classes as 'programming' (the denominator for shares).
"""
import sys
from pathlib import Path

import pandas as pd

LANGS = ["Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "C", "Go", "Rust",
         "Kotlin", "Swift", "PHP", "Ruby", "R", "Dart", "Scala", "Julia", "Lua", "Zig", "Shell"]

src = Path(sys.argv[1] if len(sys.argv) > 1 else "innovationgraph/data/languages.csv")
d = pd.read_csv(src, keep_default_na=False)          # keep_default_na: Namibia is "NA"
d = d[(d.iso2_code != "EU") & (d.language_type == "programming")]
d["geo"] = d.iso2_code.where(d.iso2_code.isin(["GB", "US", "IN"]), "OTHER")

frames = []
for geo, sub in [("WORLD", d), ("GB", d[d.geo == "GB"]), ("US", d[d.geo == "US"]), ("IN", d[d.geo == "IN"])]:
    tot = sub.groupby(["year", "quarter"]).num_pushers.sum().rename("ALL_PROGRAMMING")
    lang = sub[sub.language.isin(LANGS)].groupby(["year", "quarter", "language"]).num_pushers.sum().unstack()
    out = lang.join(tot).reset_index()
    out.insert(0, "geo", geo)
    frames.append(out)
res = pd.concat(frames)
res.columns.name = None
out = Path(__file__).parent / "data/inputs/github-innovation-graph-pushers.csv"
res.to_csv(out, index=False, float_format="%.0f")
print(out, res.shape)
