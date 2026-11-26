#!/usr/bin/env python3
"""How far does your salary really go in another country? (Truth with Data, November 2026)

Usage: python salary-ppp-analysis.py DATA_DIR [JS_OUT]
  DATA_DIR  folder holding the three tables built by salary-ppp-build-panel.py; outputs are written there too.
  JS_OUT    optional path for the converter's data file (js/salary-ppp-data.js).

Method
  * Price level = PPP conversion factor for private consumption (local currency per international $,
    World Bank WDI PA.NUS.PRVT.PP) / market exchange rate (local currency per US$, PA.NUS.FCRF), same year.
    1.00 = US prices; 0.25 = a typical household basket costs a quarter of what it would at market rates.
  * "What $1,000 is really worth" = $1,000 changed at the market rate and spent locally, valued at US prices:
    1000 / price level, in international dollars.
  * Salary converter: S in country A is worth S / FX_A * FX_B in B at market rates, and S / PPP_A * PPP_B
    in B for the same average basket (the PPP equivalent). The ratio between them is price level A / price level B.
  * Country coverage: the latest year with both series, kept only if it is 2024 or 2025 (older PPP factors are
    unreliable after high inflation, e.g. Argentina 2021). Bulgaria's PPP factors are published in euros and its
    2025 exchange rate in leva, so the PPP factors are converted to leva. Liberia is dropped: its WDI PPP factor is on a
    different currency basis from its exchange rate (price level 0.003).
  * Median earnings: ILOSTAT median monthly earnings of all employees (both sexes), latest survey year 2018 or
    later, uprated to the PPP year with each country's CPI (WDI FP.CPI.TOTL). Countries whose uprating factor
    is above 2 (very high inflation since the survey) are left out, as are records that fail a unit check
    against ILOSTAT's own US-dollar series. ILOSTAT reports EU-SILC figures for non-euro countries in euros;
    they are converted back at that year's exchange rates. Two old currencies are rescaled to the units WDI
    uses (Sierra Leone leone / 1000, Mauritania ouguiya / 10). Zimbabwe, Somalia and Madagascar are dropped
    (currency changes or implausible values).
  * No taxes, rent premiums in big cities, or prices of internationally traded goods: see the article.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

D = sys.argv[1]
JS = sys.argv[2] if len(sys.argv) > 2 else None
MIN_YEAR = 2024
REDENOM = {"SLE": 1000, "MRT": 10}          # old-currency units per WDI unit
PPP_UNIT = {"BGR": 1.95583}                 # Bulgaria: WDI's PPP factors are already in euros (euro since Jan 2026),
                                            # its 2025 exchange rate is still in leva; 1.95583 leva = 1 euro
DROP_EARN = {"ZWE", "SOM", "MDG"}
# Currency of the WDI local-currency series (for display in the converter only); Bulgaria is in leva for 2025
CURRENCY = dict(zip(*[iter("""
AGO AOA ALB ALL ARE AED ARM AMD ATG XCD AUS AUD AUT EUR AZE AZN BDI BIF BEL EUR BEN XOF BFA XOF
BGD BDT BGR BGN BHR BHD BHS BSD BIH BAM BLR BYN BLZ BZD BOL BOB BRA BRL BRN BND BTN BTN BWA BWP
CAF XAF CAN CAD CHE CHF CHL CLP CHN CNY CIV XOF CMR XAF COG XAF COL COP COM KMF CPV CVE CRI CRC
CYP EUR CZE CZK DEU EUR DJI DJF DMA XCD DNK DKK DOM DOP DZA DZD ECU USD EGY EGP ESP EUR EST EUR
ETH ETB FIN EUR FJI FJD FRA EUR GAB XAF GBR GBP GEO GEL GHA GHS GMB GMD GNB XOF GNQ XAF GRC EUR
GRD XCD GTM GTQ GUY GYD HKG HKD HND HNL HRV EUR HTI HTG HUN HUF IDN IDR IND INR IRL EUR IRQ IQD
ISL ISK ISR ILS ITA EUR JAM JMD JOR JOD JPN JPY KAZ KZT KEN KES KGZ KGS KHM KHR KIR AUD KOR KRW
KWT KWD LAO LAK LBN LBP LBY LYD LCA XCD LKA LKR LSO LSL LTU EUR LUX EUR LVA EUR MAC MOP MAR MAD
MDA MDL MDG MGA MDV MVR MEX MXN MKD MKD MLI XOF MLT EUR MNE EUR MNG MNT MOZ MZN MUS MUR MYS MYR
NAM NAD NER XOF NGA NGN NIC NIO NLD EUR NOR NOK NPL NPR NZL NZD OMN OMR PAK PKR PAN USD PER PEN
PHL PHP PLW USD PNG PGK POL PLN PRT EUR PRY PYG QAT QAR ROU RON RUS RUB RWA RWF SAU SAR SEN XOF
SGP SGD SLB SBD SLV USD SMR EUR SRB RSD STP STN SUR SRD SVK EUR SVN EUR SWE SEK SYC SCR TCD XAF
TGO XOF THA THB TJK TJS TLS USD TON TOP TTO TTD TUN TND TUR TRY TZA TZS UGA UGX UKR UAH URY UYU
USA USD UZB UZS VCT XCD VNM VND VUT VUV WSM WST ZAF ZAR ZMB ZMW
""".split())] * 2))
NICE = {"Egypt, Arab Rep.": "Egypt", "Gambia, The": "Gambia", "Bahamas, The": "Bahamas", "Lao PDR": "Laos",
        "Viet Nam": "Vietnam", "Korea, Rep.": "South Korea", "Russian Federation": "Russia", "Turkiye": "Türkiye",
        "Slovak Republic": "Slovakia", "Kyrgyz Republic": "Kyrgyzstan", "Hong Kong SAR, China": "Hong Kong",
        "Macao SAR, China": "Macao", "Congo, Rep.": "Congo (Republic)", "Brunei Darussalam": "Brunei",
        "Cote d'Ivoire": "Côte d'Ivoire", "Sao Tome and Principe": "São Tomé and Príncipe", "Czechia": "Czech Republic"}
CASE_FROM = "IND"
CASE_TO = ["GBR", "USA", "ARE", "DEU"]
CASE_SALARIES = [50000, 100000, 200000]      # rupees a month

w = pd.read_csv(os.path.join(D, "salary-ppp-wdi-countries.csv"))
w["region"] = w.region.str.strip()
w = w.rename(columns={"ppp_private_consumption_lcu_per_intl_usd": "ppp", "exchange_rate_lcu_per_usd": "fx",
                      "ppp_gdp_lcu_per_intl_usd": "ppp_gdp"})
for k, f in PPP_UNIT.items():
    w.loc[w.iso3 == k, ["ppp", "ppp_gdp"]] *= f
w["price_level"] = w.ppp / w.fx
w["value_of_1000_usd"] = 1000 / w.price_level
w["ok"] = (w.wdi_year >= MIN_YEAR) & (w.iso3 != "LBR") & w.price_level.between(0.1, 2.5)
dropped = w[~w.ok][["iso3", "country", "wdi_year", "price_level"]]
c = w[w.ok].copy()
c["rank_furthest"] = c.value_of_1000_usd.rank(ascending=False, method="first").astype(int)
c["price_level_gdp"] = c.ppp_gdp / c.fx

# 1. Earnings: ILOSTAT median, checked and uprated ------------------------------------------------------
e = pd.read_csv(os.path.join(D, "salary-ppp-ilostat-median-earnings.csv"))
e = e[~e.iso3.isin(DROP_EARN)].copy()
non_euro = e.currency_note.str.contains(r"Euro \(EUR\)", na=False) & ((e.fx_survey_year - e.eur_per_usd_survey_year).abs() > 1e-6)
conv = np.where(non_euro, e.fx_survey_year / e.eur_per_usd_survey_year, 1.0) / e.iso3.map(REDENOM).fillna(1)
e["median_lcu_survey_year"] = e.median_monthly_lcu * conv
e["mean_lcu_survey_year"] = e.mean_monthly_lcu * conv
e["eur_converted"] = non_euro
e["unit_check"] = e.median_lcu_survey_year / e.fx_survey_year / e.ilo_median_usd   # ~1 when units agree
e = e.merge(c[["iso3", "wdi_year", "ppp", "fx", "price_level"]], on="iso3", how="inner")
same_year = e.year >= e.wdi_year
e["uprate"] = np.where(same_year, 1.0, e.cpi_latest / e.cpi_survey_year)
e["note"] = ""
e.loc[e.unit_check.notna() & ((e.unit_check - 1).abs() > 0.05), "note"] = "failed unit check"
e.loc[(e.note == "") & e.uprate.isna(), "note"] = "no CPI to uprate"
e.loc[(e.note == "") & (e.uprate > 2), "note"] = "inflation since survey too high (uprating > 2x)"
e["median_monthly_lcu_ppp_year"] = e.median_lcu_survey_year * e.uprate
e["median_monthly_usd_market"] = e.median_monthly_lcu_ppp_year / e.fx
e["median_monthly_intl_usd_ppp"] = e.median_monthly_lcu_ppp_year / e.ppp
earn = e[e.note == ""].copy()
earn_out = e[["iso3", "survey", "year", "coverage_note", "median_monthly_lcu", "currency_note", "eur_converted",
              "median_lcu_survey_year", "unit_check", "uprate", "median_monthly_lcu_ppp_year", "wdi_year",
              "median_monthly_usd_market", "median_monthly_intl_usd_ppp", "note"]]
earn_out = earn_out.merge(c[["iso3", "country"]], on="iso3")
earn_out.sort_values("median_monthly_intl_usd_ppp", ascending=False).to_csv(
    os.path.join(D, "salary-ppp-median-earnings-by-country.csv"), index=False, float_format="%.4g")
c = c.merge(earn[["iso3", "year", "survey", "median_monthly_lcu_ppp_year", "median_monthly_usd_market",
                  "median_monthly_intl_usd_ppp"]].rename(columns={"year": "earnings_year"}), on="iso3", how="left")

# 2. Country table -----------------------------------------------------------------------------------------
cols = ["rank_furthest", "iso3", "country", "region", "income_group", "wdi_year", "ppp", "fx", "price_level",
        "value_of_1000_usd", "ppp_gdp", "price_level_gdp", "earnings_year", "survey", "median_monthly_lcu_ppp_year",
        "median_monthly_usd_market", "median_monthly_intl_usd_ppp"]
c = c.sort_values("rank_furthest")
c[cols].to_csv(os.path.join(D, "salary-ppp-price-levels-by-country.csv"), index=False, float_format="%.5g")

# 3. Summaries --------------------------------------------------------------------------------------------
reg = (c.groupby("region").agg(countries=("iso3", "size"), median_price_level=("price_level", "median"),
                               median_value_of_1000=("value_of_1000_usd", "median")).reset_index()
       .sort_values("median_price_level"))
inc = (c.groupby("income_group").agg(countries=("iso3", "size"), median_price_level=("price_level", "median"),
                                     median_value_of_1000=("value_of_1000_usd", "median")).reset_index())
reg.to_csv(os.path.join(D, "salary-ppp-price-levels-by-region.csv"), index=False, float_format="%.4g")
gdp_diff = (c.price_level_gdp / c.price_level - 1).dropna()
rank_corr = float(c.dropna(subset=["price_level_gdp"])[["price_level", "price_level_gdp"]].rank().corr().iloc[0, 1])


# 4. Case studies: India to the UK, US, UAE and Germany -------------------------------------------------------
def convert(s, a, b, share_market=0.0):
    A, B = c.set_index("iso3").loc[a], c.set_index("iso3").loc[b]
    fx_eq = s / A.fx * B.fx
    ppp_eq = s / A.ppp * B.ppp
    return fx_eq, (1 - share_market) * ppp_eq + share_market * fx_eq


ci = c.set_index("iso3")
rows = []
for s in CASE_SALARIES:
    for b in CASE_TO:
        fx_eq, ppp_eq = convert(s, CASE_FROM, b)
        r = {"salary_inr_month": s, "to": ci.loc[b, "country"], "iso3": b, "market_rate_equivalent": fx_eq,
             "ppp_equivalent": ppp_eq, "ppp_over_market": ppp_eq / fx_eq,
             "with_30pct_spending_at_market_prices": convert(s, CASE_FROM, b, 0.3)[1]}
        if pd.notna(ci.loc[CASE_FROM, "median_monthly_lcu_ppp_year"]):
            mult = s / ci.loc[CASE_FROM, "median_monthly_lcu_ppp_year"]
            r["times_india_median"] = mult
            if pd.notna(ci.loc[b, "median_monthly_lcu_ppp_year"]):
                r["destination_median_lcu"] = ci.loc[b, "median_monthly_lcu_ppp_year"]
                r["ppp_equivalent_times_destination_median"] = ppp_eq / ci.loc[b, "median_monthly_lcu_ppp_year"]
                r["same_rank_salary_lcu"] = mult * ci.loc[b, "median_monthly_lcu_ppp_year"]
        rows.append(r)
cases = pd.DataFrame(rows)
cases.to_csv(os.path.join(D, "salary-ppp-india-case-studies.csv"), index=False, float_format="%.4g")

# Share of spending at market prices: India -> UK, Rs 1 lakh a month
sens = pd.DataFrame([{"share_at_market_prices_pct": 100 * q, "to": b,
                      "equivalent_lcu": convert(100000, CASE_FROM, b, q)[1]}
                     for b in CASE_TO for q in np.arange(0, 1.0001, 0.1)])
sens.to_csv(os.path.join(D, "salary-ppp-india-sensitivity-traded-share.csv"), index=False, float_format="%.4g")

# 5. Occupations (ILO's own 2021 PPP $) --------------------------------------------------------------------
o = pd.read_csv(os.path.join(D, "salary-ppp-ilostat-occupations.csv"))
o = o[o.iso3.isin(c.iso3) & ~o.iso3.isin(DROP_EARN) & (o.year >= 2022)].merge(c[["iso3", "country"]], on="iso3")
o = o.rename(columns={"isco_2": "professionals", "isco_3": "technicians_associate_prof", "isco_5": "service_sales",
                      "isco_9": "elementary"})
o["professionals_vs_all"] = o.professionals / o.all_employees
occ = o[["iso3", "country", "year", "all_employees", "professionals", "technicians_associate_prof", "service_sales",
         "elementary", "professionals_vs_all"]].sort_values("professionals", ascending=False)
occ.to_csv(os.path.join(D, "salary-ppp-occupation-earnings-ppp.csv"), index=False, float_format="%.4g")

# 6. Summary JSON -----------------------------------------------------------------------------------------------
top = c.nsmallest(20, "price_level")
bot = c.nlargest(20, "price_level")
summ = {"countries": int(len(c)), "years": c.wdi_year.value_counts().sort_index().to_dict(),
        "dropped_wdi": dropped.to_dict("records"),
        "median_price_level": float(c.price_level.median()),
        "median_value_of_1000": float(c.value_of_1000_usd.median()),
        "share_cheaper_than_us": float((c.price_level < 1).mean()),
        "n_dearer_than_us": int((c.price_level > 1).sum()),
        "dearer_than_us": c[c.price_level > 1].country.tolist(),
        "top20": top[["country", "price_level", "value_of_1000_usd"]].to_dict("records"),
        "bottom20": bot[["country", "price_level", "value_of_1000_usd"]].to_dict("records"),
        "regions": reg.to_dict("records"), "income": inc.to_dict("records"),
        "gdp_vs_private_ppp_median_abs_diff_pct": float(100 * gdp_diff.abs().median()),
        "gdp_vs_private_ppp_rank_corr": rank_corr,
        "earnings_countries": int(len(earn)), "earnings_years": earn.year.value_counts().sort_index().to_dict(),
        "earnings_excluded": e[e.note != ""][["iso3", "year", "note"]].to_dict("records"),
        "earnings_eur_converted": e[e.eur_converted].iso3.tolist(),
        "cases": cases.to_dict("records"),
        "focus": ci.loc[["IND", "GBR", "USA", "ARE", "DEU", "CHE", "EGY", "PAK", "CAN", "AUS", "SGP"],
                        ["country", "wdi_year", "ppp", "fx", "price_level", "value_of_1000_usd", "earnings_year",
                         "median_monthly_lcu_ppp_year", "median_monthly_intl_usd_ppp"]].reset_index().to_dict("records")}
json.dump(summ, open(os.path.join(D, "salary-ppp-summary.json"), "w"), indent=1, default=float)

# 7. Data for the in-browser converter ------------------------------------------------------------------------------
if JS:
    rows = []
    for _, r in c.assign(nice=c.country.map(lambda x: NICE.get(x, x))).sort_values("nice").iterrows():
        d = {"c": r.iso3, "n": NICE.get(r.country, r.country), "k": CURRENCY[r.iso3], "y": int(r.wdi_year), "p": float(f"{r.ppp:.6g}"),
             "x": float(f"{r.fx:.6g}")}
        if pd.notna(r.median_monthly_lcu_ppp_year):
            d["m"] = float(f"{r.median_monthly_lcu_ppp_year:.5g}")
            d["my"] = int(r.earnings_year)
            d["ms"] = r.survey
        rows.append(d)
    with open(JS, "w") as f:
        f.write("/* Salary purchasing-power data, generated by data/salary-ppp-analysis.py (Truth with Data, Nov 2026).\n"
                "   k = currency code; p = PPP conversion factor, private consumption (local currency per international $), World Bank WDI PA.NUS.PRVT.PP;\n"
                "   x = official exchange rate (local currency per US$), WDI PA.NUS.FCRF; y = year of both (latest available);\n"
                "   m = ILOSTAT median monthly earnings of employees, local currency, uprated with CPI to year y; my = survey year;\n"
                "   ms = survey. WDI last updated 11 Nov 2026, ILOSTAT 23-24 Nov 2026 (both CC BY 4.0). */\n")
        f.write("var SPP_DATA = " + json.dumps({"countries": rows}, separators=(",", ":"), ensure_ascii=False) + ";\n")

# Console summary -------------------------------------------------------------------------------------------------
pd.set_option("display.width", 220)
print(f"{len(c)} countries (PPP and exchange rate for {MIN_YEAR} or later); dropped {len(dropped)}")
print("Years:", summ["years"])
print(f"Median price level {summ['median_price_level']:.3f}; median value of $1,000 = ${summ['median_value_of_1000']:,.0f}; "
      f"{summ['n_dearer_than_us']} dearer than the US: {', '.join(summ['dearer_than_us'])}")
print("Furthest:", "; ".join(f"{r.country} {r.value_of_1000_usd:,.0f}" for r in top.itertuples()))
print("Least far:", "; ".join(f"{r.country} {r.value_of_1000_usd:,.0f}" for r in bot.itertuples()))
print(reg.round(3).to_string(index=False))
print(f"GDP vs private-consumption PPP: median abs diff {summ['gdp_vs_private_ppp_median_abs_diff_pct']:.1f}%, rank corr {rank_corr:.3f}")
print(f"Median earnings for {len(earn)} countries; survey years {summ['earnings_years']}")
print("Excluded:", summ["earnings_excluded"])
print(ci.loc[["IND", "GBR", "USA", "ARE", "DEU"], ["price_level", "value_of_1000_usd", "earnings_year",
                                                   "median_monthly_lcu_ppp_year", "median_monthly_intl_usd_ppp"]].round(3).to_string())
print(cases.round(2).to_string(index=False))
