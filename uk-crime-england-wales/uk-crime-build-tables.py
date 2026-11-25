#!/usr/bin/env python3
"""Build tidy tables for 'Is crime really going up in the UK?' (Truth with Data, November 2026).

Usage:
    python uk-crime-build-tables.py --fetch RAW_DIR      # download the official source files into RAW_DIR
    python uk-crime-build-tables.py RAW_DIR OUT_DIR      # write the tidy uk-crime-*.csv tables into OUT_DIR

Sources (England and Wales only; Scotland and Northern Ireland publish separate statistics):
  appendix-yejun2026.xlsx  ONS, Crime in England and Wales: Appendix tables, year ending June 2026 (22 Oct 2026).
                           A1a/A1b: CSEW incidents since 1981 and ONS significance flags; A5a: police recorded
                           crime by offence since 2002/03.
  pfa-yejunYYYY.xlsx       ONS, Police force area data tables, years ending June 2022 to June 2026.
                           P3: recorded crime per 1,000 people by force; C4: per 1,000 by Community Safety
                           Partnership (published from YE June 2024).
  other-yemar2024.xlsx     ONS, Other related tables, year ending March 2024. F17: perceptions of crime levels.
  trend-yemar2024.xlsx     ONS, Annual trend and demographic tables, YE March 2024. D10: % reported to police.
  rec-crime-1898-2002.xls  Home Office, Historical crime data: recorded crime 1898 to 2001/02.
All ONS and Home Office material is published under the Open Government Licence v3.0.
"""
import os
import re
import sys
import time

import pandas as pd

ONS = "https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/crimeandjustice/datasets/"
FILES = {
    "appendix-yejun2026.xlsx": ONS + "crimeinenglandandwalesappendixtables/yearendingjune2026/appendixtablesyejun2026.xlsx",
    "pfa-yejun2026.xlsx": ONS + "policeforceareadatatables/yearendingjune2026/pfatablesyejune2026.xlsx",
    "pfa-yejun2025.xlsx": ONS + "policeforceareadatatables/yearendingjune2025/policeforceareatablesyejune25final.xlsx",
    "pfa-yejun2024.xlsx": ONS + "policeforceareadatatables/yearendingjune2024/policeforceareatablesfinal.xlsx",
    "pfa-yejun2023.xlsx": ONS + "policeforceareadatatables/yearendingjune2023/pfatablesfinaljun23.xlsx",
    "pfa-yejun2022.xlsx": ONS + "policeforceareadatatables/yearendingjune2022/pfajun22.xlsx",
    "other-yemar2024.xlsx": ONS + "crimeinenglandandwalesotherrelatedtables/yearendingmarch2024/otherrelatedtablesmar24.xlsx",
    "trend-yemar2024.xlsx": ONS + "crimeinenglandandwalesannualtrendanddemographictables/current/"
                                  "annualtrendanddemographictablesmarch24final.xlsx",
    "rec-crime-1898-2002.xls": "https://assets.publishing.service.gov.uk/media/5a7ac815ed915d71db8b26f4/rec-crime-1898-2002.xls",
}
MON = {"Mar": 3, "Jun": 6, "Sep": 9, "Dec": 12}

# CSEW rows (Table A1a/A1b labels, matched on the start of the label once notes are stripped)
CSEW = [("violence", "VIOLENCE"), ("violence_with_injury", "Violence with injury"),
        ("violence_without_injury", "Violence without injury"), ("robbery", "ROBBERY"),
        ("theft", "THEFT OFFENCES"), ("theft_from_person", "Theft from the person"),
        ("other_personal_theft", "Other theft of personal property"), ("domestic_burglary", "Domestic burglary"),
        ("other_household_theft", "Other household theft"), ("vehicle_theft", "Vehicle-related theft"),
        ("bicycle_theft", "Bicycle theft"), ("criminal_damage", "CRIMINAL DAMAGE"),
        ("all_excl_fraud", "ALL CSEW HEADLINE CRIME EXCLUDING"), ("fraud", "Fraud"),
        ("computer_misuse", "Computer misuse"), ("all_incl_fraud", "ALL CSEW HEADLINE CRIME INCLUDING")]
BASE = ("unweighted_base_adults", "Unweighted base - number of people aged 16 and over")  # interviews, personal crime
# Police recorded crime rows (Table A5a offence-category labels)
PRC = [("violence_against_person", "TOTAL VIOLENCE AGAINST THE PERSON"), ("homicide", "Homicide"),
       ("violence_with_injury", "Violence with injury"), ("violence_without_injury", "Violence without injury"),
       ("stalking_harassment", "Stalking and harassment"), ("sexual_offences", "TOTAL SEXUAL OFFENCES"),
       ("robbery", "TOTAL ROBBERY"), ("domestic_burglary_old", "Domestic burglary"),
       ("residential_burglary", "Residential burglary"), ("burglary", "Burglary"),
       ("vehicle_offences", "Vehicle offences"), ("theft_from_person", "Theft from the person"),
       ("bicycle_theft", "Bicycle theft"), ("shoplifting", "Shoplifting"), ("theft", "TOTAL THEFT OFFENCES"),
       ("criminal_damage_arson", "TOTAL CRIMINAL DAMAGE AND ARSON"), ("drug_offences", "TOTAL DRUG OFFENCES"),
       ("weapons", "TOTAL POSSESSION OF WEAPONS OFFENCES"), ("public_order", "TOTAL PUBLIC ORDER OFFENCES"),
       ("total_excl_fraud", "TOTAL RECORDED CRIME - ALL OFFENCES EXCLUDING"),
       ("fraud_computer_misuse", "TOTAL FRAUD  AND COMPUTER MISUSE"),
       ("total_incl_fraud", "TOTAL RECORDED CRIME – ALL OFFENCES INCLUDING")]
# Offence groups for the local lookup (P3 / C4 column headings)
LOCAL = [("total", "total recorded crime"), ("violence_against_person", "violence against the person"),
         ("violence_with_injury", "violence with injury"), ("sexual_offences", "sexual offences"),
         ("robbery", "robbery"), ("residential_burglary", "residential burglary"),
         ("vehicle_offences", "vehicle offences"), ("theft_from_person", "theft from the person"),
         ("bicycle_theft", "bicycle theft"), ("shoplifting", "shoplifting"),
         ("criminal_damage_arson", "criminal damage and arson"), ("drug_offences", "drug offences"),
         ("weapons", "possession of weapons offences"), ("public_order", "public order offences")]


def clean(s):
    s = re.sub(r"\[[^\]]*\]", "", str(s)).replace("\n", " ")
    return re.sub(r"\s+", " ", s).strip()


def period(label):
    """'Apr 2001 to\\n Mar 2002' -> ('YE Mar 2002', 2001.75): label and decimal year of the mid-point."""
    m = re.findall(r"([A-Z][a-z]{2})\s*(\d{4})", clean(label))
    mon, yr = m[-1]
    return f"YE {mon} {yr}", round(int(yr) + MON[mon] / 12 - 0.5, 3)


def sheet(path, name):
    x = pd.ExcelFile(path)
    s = [n for n in x.sheet_names if n.strip() == name][0]
    return pd.read_excel(x, s, header=None)


def header_row(d, text):
    return [i for i in range(len(d)) if any(text in clean(v) for v in d.iloc[i])][0]


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def csew(raw):
    a = sheet(os.path.join(raw, "appendix-yejun2026.xlsx"), "Table A1a")
    h = header_row(a, "Offence group")
    labels = [clean(v) for v in a.iloc[:, 0]]
    rows = []
    for key, lab in CSEW + [BASE]:
        i = [k for k in range(h + 1, len(a)) if labels[k].startswith(lab)][0]
        for j in range(1, a.shape[1]):
            if pd.isna(a.iloc[h, j]):
                continue
            p, x = period(a.iloc[h, j])
            rows.append({"offence": key, "period": p, "year": x, "incidents_thousands": num(a.iloc[i, j])})
    inc = pd.DataFrame(rows)

    b = sheet(os.path.join(raw, "appendix-yejun2026.xlsx"), "Table A1b")
    h = header_row(b, "Offence group")
    labels = [clean(v) for v in b.iloc[:, 0]]
    rows = []
    for key, lab in CSEW:
        i = [k for k in range(h + 1, len(b)) if labels[k].startswith(lab)][0]
        for j in range(1, b.shape[1]):
            head = clean(b.iloc[h, j])
            if not head or "Significance" in head:
                continue
            sig = str(b.iloc[i, j + 1]).strip() == "[s]" if j + 1 < b.shape[1] else False
            p, x = period(head)
            rows.append({"offence": key, "compared_with": p, "year": x, "pct_change_to_ye_jun_2026": num(b.iloc[i, j]),
                         "significant_5pct": sig})
    return inc, pd.DataFrame(rows)


def police(raw):
    a = sheet(os.path.join(raw, "appendix-yejun2026.xlsx"), "Table A5a")
    h = header_row(a, "Offence category")
    labels = [clean(v) for v in a.iloc[:, 1]]
    codes = a.iloc[:, 0]
    rows = []
    for key, lab in PRC:
        i = [k for k in range(h + 1, len(a)) if pd.isna(codes[k]) and labels[k].startswith(clean(lab))][0]
        for j in range(2, a.shape[1]):
            head = clean(a.iloc[h, j])
            if "change" in head or not head:
                continue
            p, x = period(head)
            rows.append({"offence": key, "period": p, "year": x, "offences": num(a.iloc[i, j]), "series": "A5a"})
    prc = pd.DataFrame(rows)

    # Home Office historical series to 2001/02 (fraud and forgery removed so totals match 'excluding fraud')
    d = pd.read_excel(os.path.join(raw, "rec-crime-1898-2002.xls"), header=None)
    head = [clean(v).lower() for v in d.iloc[5]]
    tot = [i for i, v in enumerate(head) if v.startswith("total recorded")][0]
    fr = [i for i, v in enumerate(head) if v.startswith("total fraud")][0]
    bur = [i for i, v in enumerate(head) if v.startswith("total burglary")][0]
    hist = []
    for i in range(7, len(d)):
        y = str(d.iloc[i, 1]).strip()
        m = re.match(r"^(\d{4})(?:/(\d+))?", y)
        if not m or int(m.group(1)) < 1981 or num(d.iloc[i, tot]) is None:
            continue
        if m.group(2):  # financial year, ends March of the next year
            x, lab = int(m.group(1)) + 0.75, f"YE Mar {int(m.group(1)) + 1}"
            rule = "old counting rules" if "old" in y else ("new counting rules (from Apr 1998)" if int(m.group(1)) >= 1998 else "old counting rules")
        else:
            x, lab, rule = int(m.group(1)) + 0.5, f"YE Dec {m.group(1)}", "old counting rules"
        hist.append({"period": lab, "year": round(x, 3), "rules": rule, "total_incl_fraud": num(d.iloc[i, tot]),
                     "fraud_forgery": num(d.iloc[i, fr]), "burglary": num(d.iloc[i, bur])})
    hist = pd.DataFrame(hist)
    hist["total_excl_fraud"] = hist.total_incl_fraud - hist.fraud_forgery
    return prc, hist


def local_cols(d, h):
    out = {}
    for j, v in enumerate(d.iloc[h]):
        c = clean(v).lower()
        if "household" in c and "residential burglary" in c:
            continue
        if c.startswith("population"):
            out["population"] = j
        c = re.sub(r"\(.*?\)", "", c).strip().replace("all other theft", "other theft")
        for key, lab in LOCAL:
            if c == lab and key not in out:
                out[key] = j
    return out


def areas(raw):
    pfa, csp = [], []
    for yr in range(2022, 2027):
        path = os.path.join(raw, f"pfa-yejun{yr}.xlsx")
        d = sheet(path, "Table P3")
        h = header_row(d, "Area Code")
        cols = local_cols(d, h)
        cc = [j for j, v in enumerate(d.iloc[h]) if "Area Code" in str(v)][0]
        for i in range(h + 1, len(d)):
            code = str(d.iloc[i, cc]).strip()
            if not re.match(r"^[EKW]\d{8}$", code):
                continue
            r = {"year_ending": f"Jun {yr}", "area_code": code, "area_name": clean(d.iloc[i, cc + 1])}
            r.update({k: num(d.iloc[i, j]) for k, j in cols.items()})
            pfa.append(r)
        if yr < 2024:
            continue
        # Share of each force's crimes that the force could not assign to a CSP (Table C2 "Unassigned" rows)
        c2 = sheet(path, "Table C2")
        tot, una = {}, {}
        for i in range(header_row(c2, "Community Safety Partnership code") + 1, len(c2)):
            code, n = str(c2.iloc[i, 0]).strip(), num(c2.iloc[i, 6])
            if n is None:
                continue
            if pd.isna(c2.iloc[i, 2]) and pd.isna(c2.iloc[i, 3]):
                tot[code] = n
            elif "unassigned" in str(c2.iloc[i, 3]).lower():
                una[code] = una.get(code, 0) + n  # some forces have more than one unassigned row
        d = sheet(path, "Table C4")
        h = header_row(d, "Community Safety Partnership code")
        cols = local_cols(d, h)
        for i in range(h + 1, len(d)):
            code = str(d.iloc[i, 2]).strip()
            if not re.match(r"^[EW]\d{8}$", code):
                continue
            r = {"year_ending": f"Jun {yr}", "pfa_code": str(d.iloc[i, 0]).strip(), "pfa_name": clean(d.iloc[i, 1]),
                 "csp_code": code, "csp_name": clean(d.iloc[i, 3])}
            r.update({k: num(d.iloc[i, j]) for k, j in cols.items()})
            pc = r["pfa_code"]
            r["pfa_unassigned_pct"] = round(100 * una.get(pc, 0) / tot[pc], 1) if tot.get(pc) else None
            if r["pfa_unassigned_pct"] and r["pfa_unassigned_pct"] > 25:  # Kent, YE June 2026: 44% unassigned
                r.update({k: None for k, _ in LOCAL})
            csp.append(r)
    return pd.DataFrame(pfa), pd.DataFrame(csp)


def perceptions(raw):
    d = sheet(os.path.join(raw, "other-yemar2024.xlsx"), "Table F17")
    h = header_row(d, "Percentage saying")
    rows = []
    lab = {clean(d.iloc[i, 0]): i for i in range(h + 1, len(d))}
    base = [i for k, i in lab.items() if k.startswith("Unweighted")][0]
    for j in range(1, d.shape[1]):
        if pd.isna(d.iloc[h, j]):
            continue
        head = clean(d.iloc[h, j]).replace("Jan 2023 to Mar 2024", "Apr 2023 to Mar 2024")  # label typo in F17
        p, x = period(head)
        rows.append({"period": p, "year": x, "national_pct_said_crime_rose": num(d.iloc[lab["National"], j]),
                     "local_pct_said_crime_rose": num(d.iloc[lab["Local"], j]), "unweighted_base": num(d.iloc[base, j])})
    return pd.DataFrame(rows)


def reporting(raw):
    d = sheet(os.path.join(raw, "trend-yemar2024.xlsx"), "Table D10")
    h = header_row(d, "Offence group")
    want = {"VIOLENCE": "violence", "ROBBERY": "robbery", "Theft from the person": "theft_from_person",
            "Domestic burglary": "domestic_burglary", "Vehicle-related theft": "vehicle_theft",
            "CRIMINAL DAMAGE": "criminal_damage", "ALL CSEW HEADLINE CRIME": "all_headline",
            "Fraud": "fraud", "Computer misuse": "computer_misuse"}
    rows = []
    seen = set()
    for i in range(h + 1, len(d)):
        lab = clean(d.iloc[i, 0])
        key = next((v for k, v in want.items() if lab.startswith(k)), None)
        if not key or key in seen:
            continue
        seen.add(key)
        for j in range(1, d.shape[1]):
            head = clean(d.iloc[h, j])
            if not re.match(r"^[A-Z][a-z]{2} \d{4} to [A-Z][a-z]{2} \d{4}$", head):
                continue
            p, x = period(head)
            if any(r["offence"] == key and r["period"] == p for r in rows):
                continue
            rows.append({"offence": key, "label": lab, "period": p, "year": x, "pct_reported": num(d.iloc[i, j])})
    return pd.DataFrame(rows)


def wide(df, key, by, cols, order):
    """One row per offence or area; columns <period> or <group>_<year>."""
    w = df.pivot(index=key, columns=by, values=cols)
    if isinstance(w.columns, pd.MultiIndex):
        w.columns = [f"{g}_{y.split()[-1]}" for g, y in w.columns]
    else:
        w = w[list(dict.fromkeys(df[by]))]
    return w.reindex(order).reset_index()


def rate(v):
    return "" if pd.isna(v) else (f"{v:.1f}" if abs(v) >= 1 else f"{v:.2f}")


def build(raw, out):
    os.makedirs(out, exist_ok=True)
    inc, sig = csew(raw)
    prc, hist = police(raw)
    pfa, csp = areas(raw)
    rep = reporting(raw)
    groups = [k for k, _ in LOCAL]
    keep = ["YE Dec 1995", "YE Mar 2017", "YE Mar 2020", "YE Mar 2024", "YE Jun 2025"]
    last_p, last_c = pfa[pfa.year_ending == "Jun 2026"], csp[csp.year_ending == "Jun 2026"]
    pw = wide(pfa, "area_code", "year_ending", groups, list(last_p.area_code))
    pw.insert(1, "area_name", list(last_p.area_name))
    pw.insert(2, "population_mid2025", list(last_p.population.astype(int)))
    cw = wide(csp, "csp_code", "year_ending", groups, list(last_c.csp_code))
    cw.insert(1, "csp_name", list(last_c.csp_name))
    cw.insert(2, "pfa_name", list(last_c.pfa_name))
    cw.insert(3, "population_mid2024", list(last_c.population.astype(int)))
    # CSP tables start in YE June 2024: keep the three-year total and the latest year by offence group
    cw = cw[list(cw.columns[:4]) + ["total_2024", "total_2025"] + [f"{g}_2026" for g in groups]]
    cw["pfa_unassigned_pct_2026"] = list(last_c.pfa_unassigned_pct)
    tables = {
        "uk-crime-csew-incidents-1981-2026.csv": wide(inc, "offence", "period", "incidents_thousands", [k for k, _ in CSEW + [BASE]]),
        "uk-crime-csew-significance-ye-jun-2026.csv": sig[sig.compared_with.isin(keep)].drop(columns="year").round(1),
        "uk-crime-police-recorded-by-offence-2003-2026.csv": wide(prc, "offence", "period", "offences", [k for k, _ in PRC]),
        "uk-crime-police-recorded-historical-1981-2002.csv": hist,
        "uk-crime-rates-by-police-force-2022-2026.csv": pw, "uk-crime-rates-by-csp-2024-2026.csv": cw,
        "uk-crime-perceptions-2017-2024.csv": perceptions(raw).round(1),
        "uk-crime-csew-reported-to-police-1981-2024.csv": wide(rep, "offence", "period", "pct_reported",
                                                               list(dict.fromkeys(rep.offence))).round(1)}
    for name, t in tables.items():
        t = t.copy()
        for c in t.columns:
            if t[c].dtype == float and t[c].dropna().mod(1).eq(0).all():
                t[c] = t[c].astype("Int64")
            elif t[c].dtype == float and name.startswith("uk-crime-rates"):
                t[c] = t[c].map(rate)
        t.to_csv(os.path.join(out, name), index=False)
        print(f"{name}: {len(t)} rows x {t.shape[1]} cols")


def fetch(raw):
    import requests
    os.makedirs(raw, exist_ok=True)
    for name, url in FILES.items():
        for wait in (5, 30, 90, 0):  # the ONS site rate-limits quick successive downloads
            r = requests.get(url, timeout=180, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 429 or not wait:
                break
            time.sleep(wait)
        r.raise_for_status()
        time.sleep(5)
        open(os.path.join(raw, name), "wb").write(r.content)
        print(name, len(r.content), "bytes")


if __name__ == "__main__":
    if sys.argv[1] == "--fetch":
        fetch(sys.argv[2])
    else:
        build(sys.argv[1], sys.argv[2])
