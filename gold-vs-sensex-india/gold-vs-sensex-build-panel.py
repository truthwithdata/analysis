#!/usr/bin/env python3
"""Build the monthly panel for 'Has gold beaten the Sensex for Indian investors?' (Truth with Data, Nov 2026).

Usage:
    python gold-vs-sensex-build-panel.py --fetch RAW_DIR      # download the five source files into RAW_DIR
    python gold-vs-sensex-build-panel.py RAW_DIR OUT_DIR      # build india-gold-sensex-monthly-panel-1990-2026.csv

Sources (all monthly averages):
  CMO-Historical-Data-Monthly.xlsx   World Bank Commodity Price Data (Pink Sheet), 'Monthly Prices' sheet,
                                     column 'Gold ($/troy oz)'. Updated 3 November 2026. CC BY 4.0.
  EXINUS.csv                         US Federal Reserve H.10 via FRED: Indian rupees to one US dollar, monthly average.
  SPASTT01INM661N.csv                OECD Main Economic Indicators via FRED: share prices, India, 2015 = 100,
                                     monthly average. Since 1990 it tracks the BSE Sensex (checked against known
                                     Sensex levels: 1,000 in July 1990, 10,000 in Feb 2006, 20,000 in Dec 2007 ...).
  INDCPIALLMINMEI.csv                OECD MEI via FRED: consumer prices, India, all items, 2015 = 100 (ends March 2025).
  mospi-cpi-combined-general.csv     MOSPI eSankhyiki API: CPI (base 2012 = 100), All India, Combined, General index.
The two CPI series are chained in January 2014 (OECD before, MOSPI from then on).
"""
import json
import os
import sys

import pandas as pd

FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
WB = ("https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/"
      "CMO-Historical-Data-Monthly.xlsx")
MOSPI = "https://api.mospi.gov.in/api/cpi/getCPIIndex"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def fetch(raw):
    import requests
    os.makedirs(raw, exist_ok=True)
    for sid in ["EXINUS", "SPASTT01INM661N", "INDCPIALLMINMEI"]:
        open(os.path.join(raw, sid + ".csv"), "wb").write(requests.get(FRED.format(sid), timeout=60).content)
    open(os.path.join(raw, "CMO-Historical-Data-Monthly.xlsx"), "wb").write(requests.get(WB, timeout=120).content)
    rows = []
    for year in range(2014, 2026):
        page = 1
        while True:
            r = requests.get(MOSPI, timeout=60, params={"base_year": "2012", "year": str(year), "Format": "JSON",
                                                        "limit": "200", "page": str(page), "state_code": "99",
                                                        "sector_code": "3"}).json()
            rows += [e for e in r.get("data") or [] if e["group"] == "General"]
            if not r.get("meta_data") or page >= r["meta_data"]["totalPages"]:
                break
            page += 1
    pd.DataFrame(rows).to_csv(os.path.join(raw, "mospi-cpi-combined-general.csv"), index=False)
    print("downloaded to", raw)


def build(raw, out):
    x = pd.read_excel(os.path.join(raw, "CMO-Historical-Data-Monthly.xlsx"), sheet_name="Monthly Prices", header=None)
    col = [i for i, h in enumerate(x.iloc[4]) if isinstance(h, str) and h.startswith("Gold")][0]
    g = x.iloc[6:, [0, col]].dropna()
    g.columns = ["date", "gold_usd_per_oz"]
    g["date"] = g.date.str.replace("M", "-")

    def fred(sid, name):
        f = pd.read_csv(os.path.join(raw, sid + ".csv"))
        f.columns = ["date", name]
        f["date"] = f.date.str[:7]
        return f

    m = pd.read_csv(os.path.join(raw, "mospi-cpi-combined-general.csv"))
    m = m[(m.year >= 2014) & (m.state == "All India") & (m.sector == "Combined")]
    m["date"] = m.year.astype(str) + "-" + m.month.map(lambda s: f"{MONTHS.index(s) + 1:02d}")
    m = m[["date", "index"]].rename(columns={"index": "mospi_cpi_combined_2012_100"}).drop_duplicates("date")

    p = (fred("EXINUS", "usd_inr").merge(g, on="date", how="left")
         .merge(fred("SPASTT01INM661N", "oecd_india_share_price_2015_100"), on="date", how="left")
         .merge(fred("INDCPIALLMINMEI", "oecd_cpi_2015_100"), on="date", how="left")
         .merge(m, on="date", how="left"))
    p = p[p.date >= "1990-01"].sort_values("date")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "india-gold-sensex-monthly-panel-1990-2026.csv")
    p.to_csv(path, index=False, float_format="%.7g")
    print(path, len(p), "rows,", p.date.iloc[0], "to", p.date.iloc[-1])


if __name__ == "__main__":
    if sys.argv[1] == "--fetch":
        fetch(sys.argv[2])
    else:
        build(sys.argv[1], sys.argv[2])
