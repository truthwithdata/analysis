#!/usr/bin/env python3
"""Build the country panels for 'How far does your salary really go in another country?' (Truth with Data, Nov 2026).

Usage:
    python salary-ppp-build-panel.py --fetch RAW_DIR      # download the source files into RAW_DIR
    python salary-ppp-build-panel.py RAW_DIR OUT_DIR      # build the two panels below in OUT_DIR

Sources
  World Bank, World Development Indicators (API v2, last updated 11 November 2026, CC BY 4.0):
    PA.NUS.PRVT.PP  PPP conversion factor, private consumption (local currency per international $)
    PA.NUS.PPP      PPP conversion factor, GDP (local currency per international $)
    PA.NUS.FCRF     Official exchange rate (local currency per US$, period average)
    FP.CPI.TOTL     Consumer price index (2010 = 100), used only to uprate ILOSTAT earnings to 2025
    /v2/country     Country names, regions and income groups (aggregates are dropped)
  ILOSTAT (ILO, rplumber bulk API, updated 23-24 November 2026, CC BY 4.0):
    EAR_EMTM_SEX_NB_A      Median monthly earnings of employees by sex (local currency)
    EAR_EMTA_SEX_NB_A      Average (mean) monthly earnings of employees by sex (local currency)
    EAR_EMTM_SEX_CUR_NB_A  Median monthly earnings by sex and currency (US$ version used as a unit check)
    EAR_EMTM_SEX_OCU_CUR_NB_A  Median monthly earnings by sex, occupation (ISCO-08 major groups) and currency;
                           only ILO's "2021 PPP $" rows for both sexes are kept (the full file is very large)

Outputs
  salary-ppp-wdi-countries.csv               one row per country: the latest year (2025 for most) with both the
                                             private-consumption PPP factor and the exchange rate, plus the GDP PPP factor
  salary-ppp-ilostat-occupations.csv         one row per country: latest (2018+) median monthly earnings in ILO's
                                             2021 PPP $ for all employees and ISCO-08 major groups 1-9
  salary-ppp-ilostat-median-earnings.csv     one row per country: latest (2018 or later) median and mean monthly earnings
                                             of all employees in local currency, the survey, coverage and currency notes,
                                             the survey-year exchange rate and CPI, and the latest CPI (for uprating)
"""
import json
import os
import sys

import pandas as pd

WB = "https://api.worldbank.org/v2/country/all/indicator/{}?format=json&per_page=1000&date={}"
WDI = ["PA.NUS.PRVT.PP", "PA.NUS.PPP", "PA.NUS.FCRF", "FP.CPI.TOTL"]
ILO = "https://rplumber.ilo.org/data/indicator/?id={}&format=.csv&type=both"
ILO_IDS = ["EAR_EMTM_SEX_NB_A", "EAR_EMTA_SEX_NB_A", "EAR_EMTM_SEX_CUR_NB_A"]
YEARS = range(2018, 2026)


def fetch(raw):
    import requests
    os.makedirs(raw, exist_ok=True)
    for ind in WDI:
        for y in YEARS:   # one call per year: the API times out on large requests
            j = requests.get(WB.format(ind, y), timeout=120).json()
            json.dump(j, open(os.path.join(raw, f"{ind}_{y}.json"), "w"))
    j = requests.get("https://api.worldbank.org/v2/country?format=json&per_page=400", timeout=120).json()
    json.dump(j, open(os.path.join(raw, "countries.json"), "w"))
    for i in ILO_IDS:
        open(os.path.join(raw, i + ".csv"), "wb").write(requests.get(ILO.format(i), timeout=300).content)
    url = "https://rplumber.ilo.org/data/indicator/?id=EAR_EMTM_SEX_OCU_CUR_NB_A&format=.csv&type=code"
    with requests.get(url, stream=True, timeout=300) as r, open(os.path.join(raw, "ocu_ppp_filtered.csv"), "w") as f:
        for n, line in enumerate(r.iter_lines()):
            line = line.decode("utf-8-sig")
            if n == 0 or ("SEX_T" in line and "CUR_TYPE_PPP" in line and "ISCO08" in line):
                f.write(line + "\n")
    print("downloaded to", raw)


def build(raw, out):
    meta = json.load(open(os.path.join(raw, "countries.json")))[1]
    c = pd.DataFrame([{"iso3": m["id"], "country": m["name"], "region": m["region"]["value"],
                       "income_group": m["incomeLevel"]["value"]} for m in meta if m["region"]["value"] != "Aggregates"])
    rows = []
    for ind in WDI:
        for y in YEARS:
            j = json.load(open(os.path.join(raw, f"{ind}_{y}.json")))
            rows += [{"iso3": r["countryiso3code"], "year": int(r["date"]), "ind": ind, "value": r["value"]}
                     for r in (j[1] or []) if r["value"] is not None and r["countryiso3code"]]
    w = pd.DataFrame(rows).pivot_table(index=["iso3", "year"], columns="ind", values="value").reset_index()
    w = w.rename(columns={"PA.NUS.PRVT.PP": "ppp", "PA.NUS.PPP": "ppp_gdp", "PA.NUS.FCRF": "fx", "FP.CPI.TOTL": "cpi"})
    w = w[w.iso3.isin(c.iso3)]

    # 1. One row per country: the latest year with both the private-consumption PPP factor and the exchange rate
    both = w.dropna(subset=["ppp", "fx"]).sort_values("year").groupby("iso3").tail(1)
    k = c.merge(both[["iso3", "year", "ppp", "fx", "ppp_gdp"]], on="iso3")
    k = k.rename(columns={"year": "wdi_year", "ppp": "ppp_private_consumption_lcu_per_intl_usd",
                          "fx": "exchange_rate_lcu_per_usd", "ppp_gdp": "ppp_gdp_lcu_per_intl_usd"})
    os.makedirs(out, exist_ok=True)
    k.sort_values("iso3").to_csv(os.path.join(out, "salary-ppp-wdi-countries.csv"), index=False, float_format="%.6g")

    # 2. ILOSTAT: latest year (2018 or later) of median monthly earnings, all employees, both sexes
    def ilo(i, keep):
        d = pd.read_csv(os.path.join(raw, i + ".csv"))
        return d[d["sex.label"] == "Total"][keep]

    med = ilo("EAR_EMTM_SEX_NB_A", ["ref_area", "source.label", "time", "obs_value", "note_indicator.label",
                                    "note_source.label"]).rename(columns={"obs_value": "median_monthly_lcu"})
    mean = ilo("EAR_EMTA_SEX_NB_A", ["ref_area", "source.label", "time", "obs_value"]).rename(
        columns={"obs_value": "mean_monthly_lcu"})
    usd = pd.read_csv(os.path.join(raw, "EAR_EMTM_SEX_CUR_NB_A.csv"))
    usd = usd[(usd["sex.label"] == "Total") & usd["classif1.label"].str.contains("U.S. dollars")]
    usd = usd[["ref_area", "source.label", "time", "obs_value"]].rename(columns={"obs_value": "ilo_median_usd"})
    e = med.merge(mean, on=["ref_area", "source.label", "time"], how="left").merge(
        usd, on=["ref_area", "source.label", "time"], how="left")
    e = e.rename(columns={"ref_area": "iso3", "source.label": "survey", "time": "year",
                          "note_indicator.label": "currency_note", "note_source.label": "coverage_note"})
    e["coverage_note"] = (e.coverage_note.fillna("").str.replace("Repository: ILO-STATISTICS - Micro data processing", "")
                          .str.strip(" |"))
    e["currency_note"] = e.currency_note.str.extract(r"Currency: ([^|]+)")[0].str.strip()
    e = e[(e.year >= 2018) & e.iso3.isin(c.iso3)].dropna(subset=["median_monthly_lcu"])
    # several surveys in one year: keep the labour force survey if there is one, else the first listed
    e["lfs"] = e.survey.str.startswith("LFS")
    e = e.sort_values(["iso3", "year", "lfs"]).groupby("iso3").tail(1).drop(columns="lfs")
    # exchange rate and CPI in the survey year, and CPI in the latest year available (to uprate earnings)
    e = e.merge(w[["iso3", "year", "fx", "cpi"]].rename(columns={"fx": "fx_survey_year", "cpi": "cpi_survey_year"}),
                on=["iso3", "year"], how="left")
    # EU-SILC figures for countries outside the euro area are published by ILOSTAT in euros: keep the euro rate
    eur = w[w.iso3 == "DEU"][["year", "fx"]].rename(columns={"fx": "eur_per_usd_survey_year"})
    e = e.merge(eur, on="year", how="left")
    last_cpi = w.dropna(subset=["cpi"]).sort_values("year").groupby("iso3").tail(1)[["iso3", "year", "cpi"]]
    e = e.merge(last_cpi.rename(columns={"year": "cpi_latest_year", "cpi": "cpi_latest"}), on="iso3", how="left")
    e.sort_values("iso3").to_csv(os.path.join(out, "salary-ppp-ilostat-median-earnings.csv"), index=False,
                                 float_format="%.6g")
    o = pd.read_csv(os.path.join(raw, "ocu_ppp_filtered.csv"))
    o = o[(o.time >= 2018) & o.ref_area.isin(c.iso3)]
    o = o[o.time == o.groupby("ref_area").time.transform("max")]
    o["lfs"] = o.source.str.startswith("BA")
    o = o[o.lfs == o.groupby("ref_area").lfs.transform("max")]
    o = o[o.source == o.groupby("ref_area").source.transform("first")]
    o = o.pivot_table(index=["ref_area", "time"], columns="classif1", values="obs_value").reset_index()
    o.columns = [str(x).replace("OCU_ISCO08_", "isco_") for x in o.columns]
    o = o.rename(columns={"ref_area": "iso3", "time": "year", "isco_TOTAL": "all_employees"})
    o.to_csv(os.path.join(out, "salary-ppp-ilostat-occupations.csv"), index=False, float_format="%.5g")
    print(len(k), "countries with WDI PPP and exchange rate;", len(e), "with ILOSTAT median earnings 2018+")


if __name__ == "__main__":
    if sys.argv[1] == "--fetch":
        fetch(sys.argv[2])
    else:
        build(sys.argv[1], sys.argv[2])
