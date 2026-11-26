#!/usr/bin/env python3
"""Is crime really going up in the UK? Two official measures, two different stories (Truth with Data, Nov 2026)

Usage: python uk-crime-analysis.py DATA_DIR [JS_OUT]
  DATA_DIR  folder holding the tidy uk-crime-*.csv tables written by uk-crime-build-tables.py;
            the analysis outputs are written there too.
  JS_OUT    optional path for the lookup tool's data file (js/uk-crime-data.js).

Method
  * England and Wales only. Scotland and Northern Ireland have separate police forces, surveys and
    counting rules, so their figures are not comparable and are not included.
  * Crime Survey for England and Wales (CSEW): ONS estimates of incidents experienced by adults (16+) and
    households, from face-to-face interviews (about 31,000 adults a year). Headline crime excluding fraud
    and computer misuse runs from 1981; fraud and computer misuse are comparable from YE March 2017.
    There are no comparable estimates for YE March 2021 and 2022 (telephone survey in the pandemic).
    "Significant" means ONS's own test at the 5% level (Appendix table A1b); we do not re-test.
  * Police recorded crime (PRC): offences recorded by the 43 territorial forces and British Transport
    Police, excluding fraud and computer misuse. Home Office series to 2001/02 (fraud and forgery taken
    out), ONS table A5a from 2002/03. Counting-rule changes in April 1998 and the National Crime Recording
    Standard (NCRS, April 2002) break the series; we keep both rule sets for 1998/99.
  * The two measures cover different crimes (PRC includes crimes against businesses, drug, weapons and
    public-order offences, homicide; the CSEW includes unreported crime), so we compare their trends, not
    their levels.
  * Local rates: ONS police force area tables (P3) and Community Safety Partnership tables (C4), offences
    per 1,000 residents (residential burglary per 1,000 residents too, for comparability). CSP tables
    exist from YE June 2024 only.
"""
import json
import os
import sys

import pandas as pd

D = sys.argv[1]
JS = sys.argv[2] if len(sys.argv) > 2 else None
LATEST, BASE10, LOW = "YE Jun 2026", "YE Mar 2017", "YE Mar 2014"


def rd(name):
    return pd.read_csv(os.path.join(D, name))


inc = rd("uk-crime-csew-incidents-1981-2026.csv").set_index("offence")
sig = rd("uk-crime-csew-significance-ye-jun-2026.csv")
prc = rd("uk-crime-police-recorded-by-offence-2003-2026.csv").set_index("offence")
hist = rd("uk-crime-police-recorded-historical-1981-2002.csv")
perc = rd("uk-crime-perceptions-2017-2024.csv")
rep = rd("uk-crime-csew-reported-to-police-1981-2024.csv").set_index("offence")
pfa = rd("uk-crime-rates-by-police-force-2022-2026.csv")
csp = rd("uk-crime-rates-by-csp-2024-2026.csv")


def mid(p):
    """'YE Mar 2002' -> 2001.75, the mid-point of the 12 months."""
    mon, yr = p.split()[1:]
    return int(yr) + {"Mar": 3, "Jun": 6, "Sep": 9, "Dec": 12}[mon] / 12 - 0.5


def pct(a, b):
    return 100 * (b / a - 1)


# 1. The two clocks: survey incidents and police records, 1981 to 2026 ----------------------------------
rows = []
for p in inc.columns:
    v = inc.loc["all_excl_fraud", p]
    rows.append({"period": p, "year": mid(p), "measure": "CSEW incidents, excl. fraud and computer misuse",
                 "millions": v / 1000, "series": "CSEW"})
    if pd.notna(inc.loc["all_incl_fraud", p]):
        rows.append({"period": p, "year": mid(p), "measure": "CSEW incidents, incl. fraud and computer misuse",
                     "millions": inc.loc["all_incl_fraud", p] / 1000, "series": "CSEW from YE Mar 2017"})
for _, r in hist.iterrows():
    rows.append({"period": r.period, "year": r.year, "measure": "Police recorded crime, excl. fraud",
                 "millions": r.total_excl_fraud / 1e6, "series": "Home Office, " + r.rules})
for p in prc.columns:
    rows.append({"period": p, "year": mid(p), "measure": "Police recorded crime, excl. fraud",
                 "millions": prc.loc["total_excl_fraud", p] / 1e6, "series": "ONS A5a (NCRS from Apr 2002)"})
clocks = pd.DataFrame(rows).sort_values(["measure", "year"])
clocks = clocks[~((clocks.period == "YE Mar 2026") & (clocks.measure.str.startswith("CSEW")))]  # keep the June year only
clocks.to_csv(os.path.join(D, "uk-crime-two-measures-1981-2026.csv"), index=False, float_format="%.4f")

cs = inc.loc["all_excl_fraud"]
h_old = hist[hist.rules == "old counting rules"].set_index("period").total_excl_fraud
pr = prc.loc["total_excl_fraud"]
phases = {
    "csew_1981": cs["YE Dec 1981"], "csew_peak_1995": cs["YE Dec 1995"], "csew_2014": cs[LOW],
    "csew_latest": cs[LATEST], "csew_incl_fraud_2017": inc.loc["all_incl_fraud", BASE10],
    "csew_incl_fraud_latest": inc.loc["all_incl_fraud", LATEST],
    "prc_1981": h_old["YE Dec 1981"], "prc_1995": h_old["YE Dec 1995"], "prc_peak_old_rules": h_old.max(),
    "prc_peak_old_rules_period": h_old.idxmax(), "prc_2003": pr["YE Mar 2003"], "prc_low": pr.min(),
    "prc_low_period": pr.idxmin(), "prc_latest": pr[LATEST],
    "prc_1999_old": hist[(hist.period == "YE Mar 1999") & (hist.rules == "old counting rules")].total_excl_fraud.iloc[0],
    "prc_1999_new": hist[(hist.period == "YE Mar 1999") & (hist.rules != "old counting rules")].total_excl_fraud.iloc[0],
}
phases.update({
    "csew_rise_1981_1995_pct": pct(phases["csew_1981"], phases["csew_peak_1995"]),
    "prc_rise_1981_1995_pct": pct(phases["prc_1981"], phases["prc_1995"]),
    "csew_fall_1995_2014_pct": pct(phases["csew_peak_1995"], phases["csew_2014"]),
    "prc_fall_2003_2014_pct": pct(phases["prc_2003"], phases["prc_low"]),
    "csew_fall_2014_latest_pct": pct(phases["csew_2014"], phases["csew_latest"]),
    "prc_rise_2014_latest_pct": pct(phases["prc_low"], phases["prc_latest"]),
    "csew_fall_1995_latest_pct": pct(phases["csew_peak_1995"], phases["csew_latest"]),
    "counting_rules_1998_effect_pct": pct(phases["prc_1999_old"], phases["prc_1999_new"]),
    "csew_incl_fraud_change_2017_pct": pct(phases["csew_incl_fraud_2017"], phases["csew_incl_fraud_latest"]),
    "interviews_latest": int(inc.loc["unweighted_base_adults", LATEST]),
})

# 2. Which crimes are really rising? Survey vs police, YE March 2017 to YE June 2026 ------------------------
S = sig.set_index(["offence", "compared_with"])
PANEL = [  # label, CSEW key, police key, police base period
    ("Fraud", "fraud", None, None),
    ("Theft from outside homes and other household theft", "other_household_theft", None, None),
    ("Shoplifting", None, "shoplifting", BASE10),
    ("Theft from the person (pickpocketing, snatches)", "theft_from_person", "theft_from_person", BASE10),
    ("Violence", "violence", "violence_against_person", BASE10),
    ("Robbery", "robbery", "robbery", BASE10),
    ("Domestic / residential burglary", "domestic_burglary", "residential_burglary", "YE Mar 2018"),
    ("Vehicle theft", "vehicle_theft", "vehicle_offences", BASE10),
    ("Bicycle theft", "bicycle_theft", "bicycle_theft", BASE10),
    ("Criminal damage", "criminal_damage", "criminal_damage_arson", BASE10),
    ("Computer misuse (hacking, viruses)", "computer_misuse", None, None),
]
rows = []
for lab, ck, pk, pb in PANEL:
    r = {"offence": lab}
    if ck:
        s = S.loc[(ck, BASE10)]
        r.update({"csew_change_pct": s.pct_change_to_ye_jun_2026, "csew_significant": bool(s.significant_5pct),
                  "csew_latest_thousands": inc.loc[ck, LATEST], "csew_base_thousands": inc.loc[ck, BASE10],
                  "csew_change_vs_1995_pct": S.loc[(ck, "YE Dec 1995")].pct_change_to_ye_jun_2026,
                  "csew_change_1y_pct": S.loc[(ck, "YE Jun 2025")].pct_change_to_ye_jun_2026,
                  "csew_change_1y_significant": bool(S.loc[(ck, "YE Jun 2025")].significant_5pct)})
        r["csew_direction"] = ("up" if r["csew_change_pct"] > 0 else "down") if r["csew_significant"] else "no clear change"
    if pk:
        a, b = prc.loc[pk, pb], prc.loc[pk, LATEST]
        r.update({"police_base_period": pb, "police_base": int(a), "police_latest": int(b), "police_change_pct": pct(a, b),
                  "police_peak": int(prc.loc[pk].max()), "police_peak_period": prc.loc[pk].idxmax(),
                  "police_change_1y_pct": pct(prc.loc[pk, "YE Jun 2025"], b)})
        r["police_direction"] = "up" if b > a else "down"
    c, p = r.get("csew_direction"), r.get("police_direction")
    if c == "up":
        r["verdict"] = "Rising: the survey shows a real increase"
    elif c == "down" and p == "up":
        r["verdict"] = "Falling in the survey; police records up (recording and reporting)"
    elif c == "down":
        r["verdict"] = "Falling on both measures" if p else "Falling: the survey shows a real decrease"
    elif c == "no clear change":
        r["verdict"] = "No clear change in the survey" + ("; police records up" if p == "up" else "")
    else:
        r["verdict"] = "Rising in police records (no survey measure)" if p == "up" else "Falling in police records"
    rows.append(r)
panel = pd.DataFrame(rows)
panel.to_csv(os.path.join(D, "uk-crime-which-crimes-are-rising-2017-2026.csv"), index=False, float_format="%.1f")

# 3. Where the police-recorded rise since 2013/14 came from ---------------------------------------------------
GROUPS = [("violence_against_person", "Violence against the person"), ("sexual_offences", "Sexual offences"),
          ("public_order", "Public order offences"), ("weapons", "Possession of weapons"), ("drug_offences", "Drug offences"),
          ("robbery", "Robbery"), ("theft", "Theft offences (incl. burglary, vehicle, shoplifting)"),
          ("criminal_damage_arson", "Criminal damage and arson")]
rows = []
for k, lab in GROUPS:
    rows.append({"group": lab, "ye_mar_2014": int(prc.loc[k, LOW]), "ye_jun_2026": int(prc.loc[k, LATEST])})
other = {"group": "Other crimes against society", "ye_mar_2014": int(pr[LOW]) - sum(r["ye_mar_2014"] for r in rows),
         "ye_jun_2026": int(pr[LATEST]) - sum(r["ye_jun_2026"] for r in rows)}
rows.append(other)
dec = pd.DataFrame(rows)
dec["change"] = dec.ye_jun_2026 - dec.ye_mar_2014
dec["change_pct"] = 100 * dec.change / dec.ye_mar_2014
dec["share_of_net_rise_pct"] = 100 * dec.change / dec.change.sum()
dec.to_csv(os.path.join(D, "uk-crime-police-rise-decomposition-2014-2026.csv"), index=False, float_format="%.1f")
sub = {k: (int(prc.loc[k, LOW]), int(prc.loc[k, LATEST])) for k in
       ["stalking_harassment", "violence_with_injury", "violence_without_injury", "shoplifting", "burglary",
        "vehicle_offences", "homicide", "theft_from_person"]}

# 4. Reporting and perceptions ------------------------------------------------------------------------------
lastrep = rep.columns[-1]
reporting = {k: {"YE Dec 1981": rep.loc[k, "YE Dec 1981"], "YE Dec 1991": rep.loc[k, "YE Dec 1991"],
                 lastrep: rep.loc[k, lastrep]} for k in rep.index}
pl = perc.iloc[-1]
perceptions = {"period": pl.period, "national_pct": pl.national_pct_said_crime_rose, "local_pct": pl.local_pct_said_crime_rose,
               "base": int(pl.unweighted_base), "first_period": perc.period.iloc[0],
               "first_national_pct": perc.national_pct_said_crime_rose.iloc[0], "first_local_pct": perc.local_pct_said_crime_rose.iloc[0],
               "peak_national_pct": perc.national_pct_said_crime_rose.max(),
               "peak_period": perc.period[perc.national_pct_said_crime_rose.idxmax()]}
csew_pre = {p: inc.loc["all_excl_fraud", p] for p in ["YE Mar 2018", "YE Mar 2020", "YE Mar 2023", "YE Mar 2024"]}

# 5. Local rates for the lookup tool ---------------------------------------------------------------------------
G = ["total", "violence_against_person", "violence_with_injury", "sexual_offences", "robbery", "residential_burglary",
     "vehicle_offences", "theft_from_person", "bicycle_theft", "shoplifting", "criminal_damage_arson", "drug_offences",
     "weapons", "public_order"]
LABELS = {"total": "All recorded crime (excl. fraud)", "violence_against_person": "Violence against the person",
          "violence_with_injury": "Violence with injury", "sexual_offences": "Sexual offences", "robbery": "Robbery",
          "residential_burglary": "Residential burglary", "vehicle_offences": "Vehicle offences",
          "theft_from_person": "Theft from the person", "bicycle_theft": "Bicycle theft", "shoplifting": "Shoplifting",
          "criminal_damage_arson": "Criminal damage and arson", "drug_offences": "Drug offences",
          "weapons": "Possession of weapons", "public_order": "Public order offences"}
YRS = [2022, 2023, 2024, 2025, 2026]
forces = pfa[pfa.area_code.str.match(r"^(E23|W15)")].copy()
ew = pfa[pfa.area_code == "K04000001"].iloc[0]
forces["ratio_total"] = forces.total_2026 / ew.total_2026
forces["change_total_pct"] = 100 * (forces.total_2026 / forces.total_2022 - 1)
fsum = forces.dropna(subset=["total_2026"]).sort_values("total_2026")
local = {"forces": len(forces), "forces_with_rates": int(forces.total_2026.notna().sum()),
         "ew_total_2026": ew.total_2026, "ew_total_2022": ew.total_2022,
         "lowest_force": [fsum.area_name.iloc[0], fsum.total_2026.iloc[0]],
         "highest_force": [fsum.area_name.iloc[-1], fsum.total_2026.iloc[-1]],
         "forces_up_since_2022": int((fsum.total_2026 > fsum.total_2022).sum()),
         "csp_count": len(csp), "csp_with_rates": int(csp.total_2026.notna().sum())}
cs2 = csp[csp.population_mid2024 >= 10000].dropna(subset=["total_2026"]).sort_values("total_2026")  # Isles of Scilly too small
local["lowest_csp"] = [cs2.csp_name.iloc[0], cs2.total_2026.iloc[0]]
local["highest_csp"] = [cs2.csp_name.iloc[-1], cs2.total_2026.iloc[-1]]
local["csp_median"] = float(cs2.total_2026.median())
ewr = {g: [ew[f"{g}_{y}"] for y in YRS] for g in G}
force_rows = forces.sort_values("total_2026", ascending=False)
force_rows[["area_code", "area_name", "population_mid2025", "total_2022", "total_2026", "ratio_total", "change_total_pct"]].to_csv(
    os.path.join(D, "uk-crime-force-summary-2026.csv"), index=False, float_format="%.2f")

if JS:
    def v(x):
        return None if pd.isna(x) else float(x)
    data = {
        "updated": "2026-11-25", "source": "ONS, Crime in England and Wales: year ending June 2026 (22 October 2026)",
        "years": YRS, "groups": [[g, LABELS[g]] for g in G], "ew": {g: [v(x) for x in ewr[g]] for g in G},
        "forces": [[r["area_code"], r["area_name"], int(r["population_mid2025"]), [[v(r[f"{g}_{y}"]) for y in YRS] for g in G]]
                   for _, r in forces.sort_values("area_name").iterrows()],
        "csps": [[r["csp_code"], r["csp_name"], r["pfa_name"], int(r["population_mid2024"]),
                  [v(r["total_2024"]), v(r["total_2025"]), v(r["total_2026"])], [v(r[f"{g}_2026"]) for g in G],
                  v(r["pfa_unassigned_pct_2026"])] for _, r in csp.sort_values("csp_name").iterrows()],
    }
    with open(JS, "w") as f:
        f.write("// Generated by data/uk-crime-analysis.py from ONS police force area and CSP tables (YE June 2022-2026).\n"
                "// Police recorded crime per 1,000 residents, excluding fraud. Open Government Licence v3.0.\n")
        f.write("window.UK_CRIME_DATA = " + json.dumps(data, separators=(",", ":"), allow_nan=False) + ";\n")

summary = {"phases": phases, "panel": panel.to_dict("records"), "decomposition": dec.to_dict("records"),
           "police_subgroups_2014_2026": sub, "reporting_pct": reporting, "perceptions": perceptions,
           "csew_excl_fraud_thousands": csew_pre, "local": local,
           "homicide": {"latest": int(prc.loc["homicide", LATEST]), "min": int(prc.loc["homicide"].min()),
                        "min_period": prc.loc["homicide"].idxmin()},
           "police_total_incl_fraud_latest": int(prc.loc["total_incl_fraud", LATEST]),
           "police_fraud_latest": int(prc.loc["fraud_computer_misuse", LATEST])}
json.dump(summary, open(os.path.join(D, "uk-crime-summary.json"), "w"), indent=1, default=float)

# Console report ------------------------------------------------------------------------------------------------
f = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in phases.items()}
print("Phases:", json.dumps(f, default=str))
print(panel[["offence", "csew_change_pct", "csew_significant", "police_base_period", "police_change_pct", "verdict"]]
      .round(1).to_string(index=False))
print(dec.round(1).to_string(index=False))
print("Police sub-groups 2013/14 -> YE Jun 2026:", sub)
print("Reported to police (%):", {k: {p: x for p, x in d.items()} for k, d in reporting.items() if k in ("all_headline", "violence", "fraud")})
print("Perceptions:", perceptions)
print("Local:", local)
