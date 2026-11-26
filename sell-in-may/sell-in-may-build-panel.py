#!/usr/bin/env python3
"""Build the monthly panel for "Sell in May and go away: does it beat buy-and-hold?"
(Truth with Data, November 2026).

Usage:
  python sell-in-may-build-panel.py --fetch RAW_DIR      download the source files into RAW_DIR
  python sell-in-may-build-panel.py RAW_DIR DATA_DIR     build us-stocks-cash-monthly-panel-1871-2026.csv

Sources (all monthly):
  * Robert Shiller, "U.S. Stock Markets 1871-Present and CAPE Ratio" (ie_data.xls,
    http://www.econ.yale.edu/~shiller/data.htm): S&P Composite price (monthly average of daily
    closes), dividends (12-month total, per share, in index points), CPI-U.
    We read the copy republished by the Open Knowledge "datasets" project
    (github.com/datasets/s-and-p-500, data/data.csv), which carries Shiller's columns unchanged and
    appends later monthly price averages. If RAW_DIR/ie_data.xls (Shiller's own file) is present it
    is used instead.
  * FRED TB3MS: 3-month Treasury bill, secondary market rate, % a year, from January 1934.
  * FRED M13002US35620M156NNBR: NBER Macrohistory commercial paper rate, New York, % a year,
    1857-1971. Used as the cash rate before 1934 (no T-bill series exists that far back).
  * FRED CPIAUCNS: CPI-U, not seasonally adjusted (the index Shiller uses), to extend CPI past
    the last month in the Shiller file. October 2025 was never published (US federal government
    shutdown), so it is filled with the geometric mean of September and November 2025.

Gaps we fill, flagged in the panel:
  * Dividends: the Shiller file stops reporting dividends after June 2023. We extend the
    12-month dividend at its own average growth rate over the previous five years (about 6% a
    year). Dividends add about 0.1% a month to the return, so an error of a few per cent in the
    dividend level moves monthly returns by well under 0.01 percentage points.
"""
import os
import sys
import urllib.request

import numpy as np
import pandas as pd

URLS = {
    "shiller/data.csv": "https://raw.githubusercontent.com/datasets/s-and-p-500/main/data/data.csv",
    "TB3MS.csv": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=TB3MS",
    "M13002US35620M156NNBR.csv": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=M13002US35620M156NNBR",
    "CPIAUCNS.csv": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCNS",
}
FIRST, LAST = "1871-01", None   # LAST = last month with price and CPI


def fetch(raw):
    for name, url in URLS.items():
        path = os.path.join(raw, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print("downloading", url)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})
        with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
            f.write(r.read())


def fred(raw, name):
    d = pd.read_csv(os.path.join(raw, name + ".csv"))
    d.columns = ["date", "value"]
    d["date"] = d.date.str[:7]
    d["value"] = pd.to_numeric(d.value, errors="coerce")
    return d.set_index("date").value


def shiller(raw):
    xls = os.path.join(raw, "ie_data.xls")
    if os.path.exists(xls):   # Shiller's own workbook: sheet "Data", header on row 8
        d = pd.read_excel(xls, sheet_name="Data", skiprows=7)
        d = d[pd.to_numeric(d["Date"], errors="coerce").notna()].copy()
        yr = d["Date"].astype(float)
        d["date"] = [f"{int(y)}-{int(round((y - int(y)) * 100)):02d}" for y in yr]
        d = d.rename(columns={"P": "price", "D": "dividend", "CPI": "cpi"})
    else:
        d = pd.read_csv(os.path.join(raw, "shiller", "data.csv"))
        d["date"] = d.Date.str[:7]
        d = d.rename(columns={"SP500": "price", "Dividend": "dividend", "Consumer Price Index": "cpi"})
    d = d[["date", "price", "dividend", "cpi"]].copy()
    for c in ["price", "dividend", "cpi"]:
        d[c] = pd.to_numeric(d[c], errors="coerce").replace(0, np.nan)
    return d.set_index("date")


def build(raw, out):
    s = shiller(raw)
    cpi_f = fred(raw, "CPIAUCNS")
    tb = fred(raw, "TB3MS")
    cp = fred(raw, "M13002US35620M156NNBR")

    # CPI: Shiller's column, then FRED CPI-U NSA for months it lacks
    if "2025-10" in cpi_f.index and np.isnan(cpi_f["2025-10"]):
        cpi_f["2025-10"] = np.sqrt(cpi_f["2025-09"] * cpi_f["2025-11"])
    last_cpi = max(s.cpi.dropna().index.max(), cpi_f.dropna().index.max())
    last = min(s.price.dropna().index.max(), last_cpi)
    p = s.loc[FIRST:last].copy()
    p["cpi_source"] = np.where(p.cpi.notna(), "shiller", "fred_cpiaucns")
    p["cpi"] = p.cpi.fillna(cpi_f.reindex(p.index))
    if "2025-10" in p.index and p.loc["2025-10", "cpi_source"] == "fred_cpiaucns":
        p.loc["2025-10", "cpi_source"] = "interpolated"

    # Dividends: extend after the last reported month at the trailing 5-year growth rate
    k = p.dividend.last_valid_index()
    i = p.index.get_loc(k)
    g = (p.dividend.iloc[i] / p.dividend.iloc[i - 60]) ** (1 / 60)
    p["dividend_source"] = np.where(p.dividend.notna(), "shiller", "extended")
    for j in range(i + 1, len(p)):
        p.iloc[j, p.columns.get_loc("dividend")] = p.dividend.iloc[j - 1] * g
    print(f"dividends extended after {k} at {100 * (g ** 12 - 1):.2f}% a year")

    # Cash: NBER commercial paper before 1934, T-bills from 1934
    p["cash_rate_pct"] = np.where(p.index < "1934-01", cp.reindex(p.index), tb.reindex(p.index))
    p["cash_source"] = np.where(p.index < "1934-01", "nber_commercial_paper", "tb3ms")

    p = p.reset_index()[["date", "price", "dividend", "dividend_source", "cpi", "cpi_source", "cash_rate_pct", "cash_source"]]
    p = p.rename(columns={"price": "sp_composite_price", "dividend": "dividend_12m"})
    assert p.drop(columns=[]).isna().sum().sum() == 0, p[p.isna().any(axis=1)]
    path = os.path.join(out, "us-stocks-cash-monthly-panel-1871-2026.csv")
    p.to_csv(path, index=False, float_format="%.6g")
    print(f"{path}: {len(p)} months, {p.date.iloc[0]} to {p.date.iloc[-1]}")


if __name__ == "__main__":
    if sys.argv[1] == "--fetch":
        fetch(sys.argv[2])
    else:
        build(sys.argv[1], sys.argv[2])
