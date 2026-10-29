#!/usr/bin/env python3
"""
Is renting really 'dead money' in the UK?  Truth with Data, October 2026.
Rent-versus-buy model: break-even years by region and local authority,
a historical backtest (2005-2026) and sensitivity tables.

Usage:
    pip install pandas numpy openpyxl
    python uk-rent-vs-buy-analysis.py RAW_DIR OUT_DIR

RAW_DIR must contain the four source files exactly as downloaded:
    UK-HPI-full-file-2026-07.csv                          HM Land Registry, UK HPI (July 2026 data)
    priceindexofprivaterentsukmonthlypricestatistics.xlsx ONS PIPR, 21 October 2026 edition
    priceindexofprivaterentsukhistoricalseries.xlsx       ONS PIPR historical series, 26 March 2025
    Bank_of_England__Database.xlsx                        BoE quoted 2-year fixed mortgage rates
                                                          (IUMBV34, IUMB482, ...), monthly, 1995-2026

The model (identical in the R script):
  * The buyer pays a deposit plus buying costs. The renter keeps that same cash
    invested instead.
  * Every month, whoever has the lower housing outgoings invests the difference.
    Buyer outgoings: mortgage payment (interest + capital), maintenance,
    buildings insurance, service charge (flats), a product fee at each 2-year re-fix.
    Renter outgoings: rent, re-set once a year.
  * Buyer net wealth = home value - mortgage balance - selling costs + buyer's investments.
    Renter net wealth = renter's investments.
  * Break-even = first month from which the buyer's net wealth stays ahead of the renter's.
Capital repayment is not a cost: it reappears as equity. What the buyer loses is
interest, maintenance, insurance, fees, taxes and the return the cash would
have earned; what the buyer gains is house-price growth.
"""
import sys, os, json
import numpy as np
import pandas as pd

RAW = sys.argv[1] if len(sys.argv) > 1 else "raw"
OUT = sys.argv[2] if len(sys.argv) > 2 else "out"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Assumptions (every number has a source; see the article's methodology)
# ---------------------------------------------------------------------------
A = dict(
    ref_month="2026-07-01",          # latest UK HPI month; PIPR rents for the same month
    rate_month="2026-09-30",         # latest BoE quoted rate (what a buyer pays today)
    term_years=25,                   # repayment mortgage term
    fix_months=24,                   # 2-year fixes, re-fixed at the same rate in the forward model
    product_fee=1141.0,              # Moneyfacts average fixed-rate product fee (Feb 2024)
    conveyancing_house=1420.0,       # ClearScore 2026 guide: freehold purchase, fees + disbursements
    conveyancing_flat=1825.0,        # same guide: leasehold flat £1,550-£2,100 (midpoint)
    survey_points=[(150000, 400), (250000, 600), (400000, 800), (750000, 1200)],  # same guide
    agent_fee_pct=1.42,              # HomeOwners Alliance 2026 average, inc. VAT
    conveyancing_sell=950.0,         # HomeOwners Alliance: £610-£950 to sell (upper end)
    maintenance_house_pct=1.0,       # widely used 1%-of-value rule of thumb (sensitivity 0.5-1.5%)
    maintenance_flat_pct=0.5,        # our assumption: the service charge covers communal repairs
    buildings_insurance=306.0,       # ABI average buildings-only premium, Q1 2026 (houses only)
    service_charge_ew=2405.0,        # Hamptons 2025 Service Charge Index, England & Wales average
    service_charge_london=2801.0,    # Hamptons 2025, London
    cost_inflation_pct=2.0,          # fixed £ costs grow at the Bank of England's 2% CPI target
    invest_return_pct=5.0,           # FCA COBS 13 Annex 2 intermediate projection rate (ISA wrapper)
    invest_low_pct=2.0, invest_high_pct=8.0,
    horizon_years=30,
)

REGIONS = [  # (display name, ONS/HMLR code, nation for transaction tax)
    ("North East", "E12000001", "england"), ("North West", "E12000002", "england"),
    ("Yorkshire and The Humber", "E12000003", "england"), ("East Midlands", "E12000004", "england"),
    ("West Midlands", "E12000005", "england"), ("East of England", "E12000006", "england"),
    ("London", "E12000007", "england"), ("South East", "E12000008", "england"),
    ("South West", "E12000009", "england"), ("Wales", "W92000004", "wales"),
    ("Scotland", "S92000003", "scotland"), ("Northern Ireland", "N92000002", "ni"),
]
# No "UK average" row: the UK average rent is weighted by the rental stock (London-heavy) and the
# UK average price by sales, so their ratio describes no real home. We compare like with like by region.
TYPES = {  # model type: (HPI price column, PIPR rent column)
    "all": ("AveragePrice", "Rental price"),
    "detached": ("DetachedPrice", "Rental price detached"),
    "semi": ("SemiDetachedPrice", "Rental price semidetached"),
    "terraced": ("TerracedPrice", "Rental price terraced"),
    "flat": ("FlatPrice", "Rental price flat maisonette"),
}

# Bank Rate changes since 2004 (Bank of England, "Official Bank Rate history").
BANK_RATE = [("2004-02-05", 4.00), ("2004-05-06", 4.25), ("2004-06-10", 4.50), ("2004-08-05", 4.75),
             ("2005-08-04", 4.50), ("2006-08-03", 4.75), ("2006-11-09", 5.00), ("2007-01-11", 5.25),
             ("2007-05-10", 5.50), ("2007-07-05", 5.75), ("2007-12-06", 5.50), ("2008-02-07", 5.25),
             ("2008-04-10", 5.00), ("2008-10-08", 4.50), ("2008-11-06", 3.00), ("2008-12-04", 2.00),
             ("2009-01-08", 1.50), ("2009-02-05", 1.00), ("2009-03-05", 0.50), ("2016-08-04", 0.25),
             ("2017-11-02", 0.50), ("2018-08-02", 0.75), ("2020-03-11", 0.25), ("2020-03-19", 0.10),
             ("2021-12-16", 0.25), ("2022-02-03", 0.50), ("2022-03-17", 0.75), ("2022-05-05", 1.00),
             ("2022-06-16", 1.25), ("2022-08-04", 1.75), ("2022-09-22", 2.25), ("2022-11-03", 3.00),
             ("2022-12-15", 3.50), ("2023-02-02", 4.00), ("2023-03-23", 4.25), ("2023-05-11", 4.50),
             ("2023-06-22", 5.00), ("2023-08-03", 5.25), ("2024-08-01", 5.00), ("2024-11-07", 4.75),
             ("2025-02-06", 4.50), ("2025-05-08", 4.25), ("2025-08-07", 4.00), ("2025-12-18", 3.75)]

# ---------------------------------------------------------------------------
# 2. Transaction taxes in force in October 2026
# ---------------------------------------------------------------------------
def banded(price, bands):
    """bands: list of (upper threshold, rate %) applied to the slice below each threshold."""
    tax, lower = 0.0, 0.0
    for upper, rate in bands:
        if price > lower:
            tax += (min(price, upper) - lower) * rate / 100
        lower = upper
    return tax

INF = float("inf")
SDLT = [(125000, 0), (250000, 2), (925000, 5), (1500000, 10), (INF, 12)]           # England & NI
SDLT_FTB = [(300000, 0), (500000, 5)]                                                 # price <= £500k
LBTT = [(145000, 0), (250000, 2), (325000, 5), (750000, 10), (INF, 12)]               # Scotland
LBTT_FTB = [(175000, 0), (250000, 2), (325000, 5), (750000, 10), (INF, 12)]
LTT = [(225000, 0), (400000, 6), (750000, 7.5), (1500000, 10), (INF, 12)]             # Wales, no FTB relief

def transaction_tax(price, nation, first_time_buyer=True):
    if nation in ("england", "ni"):
        if first_time_buyer and price <= 500000:
            return banded(price, SDLT_FTB)
        return banded(price, SDLT)
    if nation == "scotland":
        return banded(price, LBTT_FTB if first_time_buyer else LBTT)
    if nation == "wales":
        return banded(price, LTT)
    raise ValueError(nation)

def survey_cost(price):
    xs, ys = zip(*A["survey_points"])
    return float(np.interp(price, xs, ys))

# ---------------------------------------------------------------------------
# 3. The model: one monthly simulation gives buyer and renter wealth at every horizon
# ---------------------------------------------------------------------------
def simulate(value, rent, mrate, ret, cidx, deposit_pct, nation, is_flat, region_code,
             ftb=True, maint_pct=None):
    """value[m], cidx[m] for m = 0..M; rent[m], ret[m] for m = 1..M (rent[0], ret[0] unused);
    mrate[m] = quoted 2-year fixed rate (%) available at the end of month m.
    Returns (buyer_wealth, renter_wealth) arrays of length M+1."""
    M = len(value) - 1
    P = value[0]
    if maint_pct is None:
        maint_pct = A["maintenance_flat_pct"] if is_flat else A["maintenance_house_pct"]
    sc = 0.0
    if is_flat:
        sc = A["service_charge_london"] if region_code == "E12000007" else A["service_charge_ew"]
    ins = 0.0 if is_flat else A["buildings_insurance"]
    conv = A["conveyancing_flat"] if is_flat else A["conveyancing_house"]

    deposit = P * deposit_pct / 100
    loan = P - deposit
    buy_costs = transaction_tax(P, nation, ftb) + (conv + A["product_fee"]) * cidx[0] + survey_cost(P)
    renter = deposit + buy_costs          # the renter invests the cash the buyer spends up front
    buyer = 0.0                           # buyer's side pot (invested when owning is cheaper)
    bal, n_left = loan, A["term_years"] * 12
    i = mrate[0] / 1200
    pmt = bal * i / (1 - (1 + i) ** -n_left)

    def sell_cost(v, c):
        return v * A["agent_fee_pct"] / 100 + A["conveyancing_sell"] * c

    bw = np.empty(M + 1); rw = np.empty(M + 1)
    bw[0] = value[0] - bal - sell_cost(value[0], cidx[0]); rw[0] = renter
    for m in range(1, M + 1):
        g = (1 + ret[m] / 100) ** (1 / 12)
        renter *= g; buyer *= g
        pay = 0.0
        if bal > 0:
            interest = bal * i
            principal = min(pmt - interest, bal)
            pay = interest + principal
            bal -= principal; n_left -= 1
            if bal < 1e-6:
                bal = 0.0
        out = pay + maint_pct / 100 * value[m - 1] / 12 + (ins + sc) / 12 * cidx[m]
        if m % A["fix_months"] == 0 and bal > 0 and m < M:   # re-fix: new rate, product fee
            i = mrate[m] / 1200
            pmt = bal * i / (1 - (1 + i) ** -n_left)
            out += A["product_fee"] * cidx[m]
        diff = out - rent[m]
        if diff > 0:
            renter += diff
        else:
            buyer -= diff
        bw[m] = value[m] - bal - sell_cost(value[m], cidx[m]) + buyer
        rw[m] = renter
    return bw, rw

def breakeven_years(bw, rw):
    """Break-even in years: the first month from which the buyer stays ahead of the renter for the
    rest of the horizon (NaN if the buyer is behind at the end). Using the last crossing rather than
    the first stops a brief lead (e.g. just before a re-fix fee or a price fall) counting as break-even."""
    behind = np.nonzero(bw[1:] < rw[1:])[0]
    if len(behind) == 0:
        return 1 / 12
    if behind[-1] == len(bw) - 2:
        return np.nan
    return (behind[-1] + 2) / 12

def forward_paths(P, R0, rate_pct, g_price, g_rent, r_inv, years=None):
    years = years or A["horizon_years"]
    M = years * 12
    m = np.arange(M + 1)
    value = P * (1 + g_price / 100) ** (m / 12)
    rent = R0 * (1 + g_rent / 100) ** ((m - 1) // 12)          # tenancy re-set once a year
    mrate = np.full(M + 1, rate_pct)
    ret = np.full(M + 1, r_inv)
    cidx = (1 + A["cost_inflation_pct"] / 100) ** (m / 12)
    return value, rent, mrate, ret, cidx

def run_forward(P, R0, rate_pct, g_price, g_rent, r_inv, deposit_pct, nation, is_flat, code, **kw):
    v, r, mr, rt, c = forward_paths(P, R0, rate_pct, g_price, g_rent, r_inv)
    return simulate(v, r, mr, rt, c, deposit_pct, nation, is_flat, code, **kw)

# ---------------------------------------------------------------------------
# 4. Load data
# ---------------------------------------------------------------------------
hpi = pd.read_csv(os.path.join(RAW, "UK-HPI-full-file-2026-07.csv"), low_memory=False)
hpi["Date"] = pd.to_datetime(hpi["Date"], dayfirst=True)

pipr = pd.read_excel(os.path.join(RAW, "priceindexofprivaterentsukmonthlypricestatistics.xlsx"),
                     sheet_name="Table 1", header=2)
pipr["Time period"] = pd.to_datetime(pipr["Time period"])
for c in pipr.columns[4:]:
    pipr[c] = pd.to_numeric(pipr[c], errors="coerce")       # '[x]' (not available) -> NaN

hist = pd.read_excel(os.path.join(RAW, "priceindexofprivaterentsukhistoricalseries.xlsx"),
                     sheet_name="Table 1", header=2)
hist = hist[hist.iloc[:, 0] != "Region Code"].copy()
hist.columns = ["date"] + list(hist.columns[1:])
hist["date"] = pd.to_datetime(hist["date"])
hist_codes = {"North East": "E12000001", "North West": "E12000002", "Yorkshire and The Humber": "E12000003",
              "East Midlands": "E12000004", "West Midlands": "E12000005", "East ": "E12000006",
              "London": "E12000007", "South East": "E12000008", "South West": "E12000009",
              "Wales": "W92000004", "Scotland": "S92000003", "Northern Ireland": "N92000002",
              "England": "E92000001", "United Kingdom": "K02000001"}

boe = pd.read_excel(os.path.join(RAW, "Bank_of_England__Database.xlsx"), header=1)
boe.columns = ["date"] + [str(c).split()[-1] for c in boe.columns[1:]]   # series codes
boe["date"] = pd.to_datetime(boe["date"], format="%d %b %y")
for c in boe.columns[1:]:
    boe[c] = pd.to_numeric(boe[c], errors="coerce")
boe = boe.sort_values("date")
boe["month"] = boe["date"].dt.to_period("M").dt.to_timestamp()
rate_row = boe[boe["date"] == A["rate_month"]].iloc[0]
RATE90, RATE75 = float(rate_row["IUMB482"]), float(rate_row["IUMBV34"])

ref = pd.Timestamp(A["ref_month"])

def rent_index(code):
    """PIPR index (Jan 2023 = 100): historical series before 2015, monthly series from Jan 2015.
    The two are identical where they overlap (checked: 2015-01 to 2025-02)."""
    mon = pipr[pipr["Area code"] == code].set_index("Time period")["Index"].dropna()
    name = [k for k, v in hist_codes.items() if v == code]
    if name:
        h = pd.to_numeric(hist.set_index("date")[name[0]], errors="coerce").dropna()
        return pd.concat([h[h.index < mon.index.min()], mon])
    return mon

# Baseline forward growth: England, July 2005 -> July 2026 (the longest window both series cover)
eng_p = hpi[hpi.AreaCode == "E92000001"].set_index("Date")["AveragePrice"]
eng_r = rent_index("E92000001")
yrs = 21
G_PRICE = float(((eng_p[ref] / eng_p[pd.Timestamp("2005-07-01")]) ** (1 / yrs) - 1) * 100)
G_RENT = float(((eng_r[ref] / eng_r[pd.Timestamp("2005-07-01")]) ** (1 / yrs) - 1) * 100)
uk_p = hpi[hpi.AreaCode == "K02000001"].set_index("Date")["AveragePrice"]
G_PRICE_1995 = float(((uk_p[ref] / uk_p[pd.Timestamp("1995-07-01")]) ** (1 / 31) - 1) * 100)

# ---------------------------------------------------------------------------
# 5. Inputs and break-even by region x property type x deposit
# ---------------------------------------------------------------------------
def region_own_growth(code):
    """Region's own annualised price and rent growth over the longest common window to July 2026."""
    ri = rent_index(code)
    p = hpi[hpi.AreaCode == code].set_index("Date")["AveragePrice"]
    start = max(pd.Timestamp("2005-07-01"), ri.index.min())
    start = pd.Timestamp(year=start.year + (start.month > 7), month=7, day=1)
    n = (ref.year - start.year)
    return (float(((p[ref] / p[start]) ** (1 / n) - 1) * 100),
            float(((ri[ref] / ri[start]) ** (1 / n) - 1) * 100), start.year)

rows = []
for name, code, nation in REGIONS:
    hrow = hpi[(hpi.AreaCode == code) & (hpi.Date == ref)].iloc[0]
    prow = pipr[(pipr["Area code"] == code) & (pipr["Time period"] == ref)].iloc[0]
    gp_own, gr_own, gstart = region_own_growth(code)
    for t, (pc, rc) in TYPES.items():
        P, R0 = float(hrow[pc]), float(prow[rc])
        is_flat = t == "flat"
        for dep, rate in ((10, RATE90), (25, RATE75)):
            bw, rw = run_forward(P, R0, rate, G_PRICE, G_RENT, A["invest_return_pct"], dep, nation, is_flat, code)
            bwo, rwo = run_forward(P, R0, rate, gp_own, gr_own, A["invest_return_pct"], dep, nation, is_flat, code)
            bwf, rwf = run_forward(P, R0, rate, 0.0, G_RENT, A["invest_return_pct"], dep, nation, is_flat, code)
            bwr, rwr = run_forward(P, R0, rate + 1, G_PRICE, G_RENT, A["invest_return_pct"], dep, nation, is_flat, code)
            rows.append(dict(
                region=name, area_code=code, nation=nation, property_type=t, deposit_pct=dep,
                mortgage_rate_pct=rate, price_jul2026=P, monthly_rent_jul2026=R0,
                gross_rental_yield_pct=round(12 * R0 / P * 100, 2),
                price_to_annual_rent=round(P / (12 * R0), 1),
                transaction_tax=round(transaction_tax(P, nation, True)),
                breakeven_years=breakeven_years(bw, rw),
                gap_after_2y=bw[24] - rw[24], gap_after_5y=bw[60] - rw[60],
                gap_after_10y=bw[120] - rw[120], gap_after_20y=bw[240] - rw[240],
                own_growth_price_pct=round(gp_own, 2), own_growth_rent_pct=round(gr_own, 2),
                own_growth_from=gstart, breakeven_years_own_growth=breakeven_years(bwo, rwo),
                breakeven_years_flat_prices=breakeven_years(bwf, rwf),
                breakeven_years_rate_plus_1pt=breakeven_years(bwr, rwr),
            ))
reg = pd.DataFrame(rows)

# First-year snapshot of the unrecoverable cost of owning vs renting (all property types, 10% deposit)
snap = []
for name, code, nation in REGIONS:
    r = reg[(reg.region == name) & (reg.property_type == "all") & (reg.deposit_pct == 10)].iloc[0]
    P, R0 = r.price_jul2026, r.monthly_rent_jul2026
    loan = 0.9 * P; i = RATE90 / 1200; n = A["term_years"] * 12
    pmt = loan * i / (1 - (1 + i) ** -n)
    bal, interest = loan, 0.0
    for _ in range(12):
        it = bal * i; interest += it; bal -= pmt - it
    cash_in = 0.1 * P + r.transaction_tax + A["conveyancing_house"] + A["product_fee"] + survey_cost(P)
    snap.append(dict(region=name, rent_year1=12 * R0, interest=interest,
                     maintenance=A["maintenance_house_pct"] / 100 * P, insurance=A["buildings_insurance"],
                     opportunity_cost=cash_in * A["invest_return_pct"] / 100,
                     expected_price_gain=P * G_PRICE / 100,
                     one_off_buy_and_sell_costs=cash_in - 0.1 * P + P * A["agent_fee_pct"] / 100 + A["conveyancing_sell"]))
snap = pd.DataFrame(snap)
snap["net_cost_of_owning"] = snap[["interest", "maintenance", "insurance", "opportunity_cost"]].sum(axis=1) - snap["expected_price_gain"]

# ---------------------------------------------------------------------------
# 6. Sensitivity: each cell is run for all 12 regions (average home, 10% deposit unless
#    stated); we report the median break-even across regions and the fastest/slowest region.
# ---------------------------------------------------------------------------
base = reg[(reg.property_type == "all") & (reg.deposit_pct == 10)]
sens = []
def add(table, **kw):
    args = dict(rate=RATE90, gp=G_PRICE, gr=G_RENT, ret=A["invest_return_pct"], dep=10, maint=None)
    args.update(kw)
    be, g10 = [], []
    for _, r in base.iterrows():
        bw, rw = run_forward(r.price_jul2026, r.monthly_rent_jul2026, args["rate"], args["gp"], args["gr"],
                             args["ret"], args["dep"], r.nation, False, r.area_code, maint_pct=args["maint"])
        be.append(breakeven_years(bw, rw)); g10.append(bw[120] - rw[120])
    be = np.array(be)
    sens.append(dict(table=table, mortgage_rate_pct=args["rate"], price_growth_pct=args["gp"],
                     rent_growth_pct=args["gr"], invest_return_pct=args["ret"], deposit_pct=args["dep"],
                     maintenance_pct=args["maint"] if args["maint"] is not None else A["maintenance_house_pct"],
                     median_breakeven_years=float(np.median(np.where(np.isnan(be), np.inf, be))),
                     fastest_region_years=float(np.nanmin(be)) if np.isfinite(be).any() else np.nan,
                     slowest_region_years=float(np.max(np.where(np.isnan(be), np.inf, be))),
                     regions_not_breaking_even_in_30y=int(np.isnan(be).sum()),
                     median_gap_after_10y=float(np.median(g10))))
GP_GRID = [0.0, 1.0, 2.0, round(G_PRICE, 2), 4.0, 5.0]       # 3% replaced by the 2005-2026 baseline
for rate in [3.0, 3.5, 4.0, 4.5, 5.0, RATE90, 6.0, 6.5, 7.0]:  # 5.5% replaced by today's 90% LTV rate
    for gp in GP_GRID:
        add("rate_x_price_growth", rate=rate, gp=gp)
for ret in [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]:
    for gp in GP_GRID:
        add("return_x_price_growth", ret=ret, gp=gp)
for gr in [1.0, 2.0, round(G_RENT, 2), 4.0, 5.0]:
    for gp in GP_GRID:
        add("rent_growth_x_price_growth", gr=gr, gp=gp)
for maint in [0.5, 1.0, 1.5]:
    add("maintenance", maint=maint)
for dep in [5, 10, 15, 20, 25, 40]:
    add("deposit", dep=dep)
sens = pd.DataFrame(sens).replace(np.inf, np.nan)

# ---------------------------------------------------------------------------
# 7. Local authorities (England and Wales: PIPR and UK HPI share LA codes)
# ---------------------------------------------------------------------------
la_rent = pipr[(pipr["Time period"] == ref) & pipr["Area code"].str.match(r"^(E06|E07|E08|E09|W06)")]
la_rows = []
for _, pr in la_rent.iterrows():
    h = hpi[(hpi.AreaCode == pr["Area code"]) & (hpi.Date == ref)]
    if h.empty or pd.isna(pr["Rental price"]):
        continue
    P, R0 = float(h.iloc[0]["AveragePrice"]), float(pr["Rental price"])
    nation = "wales" if pr["Area code"].startswith("W") else "england"
    bw, rw = run_forward(P, R0, RATE90, G_PRICE, G_RENT, A["invest_return_pct"], 10, nation, False, pr["Area code"])
    row = dict(area_code=pr["Area code"], local_authority=pr["Area name"],
               region=pr["Region or country name"], price_jul2026=P, monthly_rent_jul2026=R0,
               gross_rental_yield_pct=round(12 * R0 / P * 100, 2),
               breakeven_years=breakeven_years(bw, rw),
               gap_after_5y=round(bw[60] - rw[60]), gap_after_10y=round(bw[120] - rw[120]))
    # Robustness: like-for-like by property type (terraced houses, flats) where both series exist
    for t in ("terraced", "flat"):
        pc, rc = TYPES[t]
        Pt, Rt = h.iloc[0][pc], pr[rc]
        if pd.notna(Pt) and pd.notna(Rt):
            bt_, rt_ = run_forward(float(Pt), float(Rt), RATE90, G_PRICE, G_RENT, A["invest_return_pct"], 10,
                                   nation, t == "flat", pr["Area code"])
            row[f"breakeven_years_{t}"] = breakeven_years(bt_, rt_)
        else:
            row[f"breakeven_years_{t}"] = np.nan
    la_rows.append(row)
la = pd.DataFrame(la_rows).sort_values("breakeven_years")

# ---------------------------------------------------------------------------
# 8. Historical backtest: bought in July of year X, sold in July of year Y (all property types)
# ---------------------------------------------------------------------------
months = pd.date_range("2005-01-01", A["ref_month"], freq="MS")
br = pd.Series([r for _, r in BANK_RATE], index=pd.to_datetime([d for d, _ in BANK_RATE]))
bank_monthly = pd.Series([br[br.index <= d + pd.Timedelta(days=14)].iloc[-1] for d in months], index=months)
r75 = boe.set_index("month")["IUMBV34"].reindex(months)

panel_rows, bt_rows = [], []
for name, code, nation in REGIONS + [("England", "E92000001", "england")]:
    price = hpi[hpi.AreaCode == code].set_index("Date")["AveragePrice"].reindex(months)
    ri = rent_index(code).reindex(months)
    rent_level = ri / ri[ref] * float(pipr[(pipr["Area code"] == code) & (pipr["Time period"] == ref)]["Rental price"].iloc[0])
    for d in months:
        panel_rows.append(dict(region=name, area_code=code, nation=nation, month=d.strftime("%Y-%m"),
                               avg_price=price[d], rent_index=ri[d], monthly_rent=rent_level[d],
                               rate_2y_fixed_75ltv=r75[d], bank_rate=bank_monthly[d]))
    if code == "E92000001":
        continue                      # England is in the panel only for the baseline growth rates
    first = ri.dropna().index.min()
    start_year = first.year + (first.month > 7)
    for x in range(start_year, ref.year):
        d0 = pd.Timestamp(year=x, month=7, day=1)
        sl = months[months >= d0]
        M = len(sl) - 1
        m = np.arange(M + 1)
        value = price[sl].to_numpy(float)
        anniv = sl[((m - 1) // 12) * 12]                      # rent re-set each July
        rent = rent_level[anniv].to_numpy(float)
        mrate = r75[sl].to_numpy(float)
        cidx = (1 + A["cost_inflation_pct"] / 100) ** ((m + (x - ref.year) * 12) / 12)
        for label, ret in (("bank_rate", bank_monthly[sl].to_numpy(float)), ("fixed_5pct", np.full(M + 1, 5.0))):
            bw, rw = simulate(value, rent, mrate, ret, cidx, 25, nation, False, code)
            be = breakeven_years(bw, rw)
            for y in range(x + 1, ref.year + 1):
                k = (y - x) * 12
                bt_rows.append(dict(region=name, area_code=code, return_assumption=label, buy_year=x,
                                    sell_year=y, years_held=y - x, price_bought=value[0],
                                    buyer_wealth=round(bw[k]), renter_wealth=round(rw[k]),
                                    buyer_minus_renter=round(bw[k] - rw[k]),
                                    gap_pct_of_price=round((bw[k] - rw[k]) / value[0] * 100, 2),
                                    breakeven_years=be))
panel = pd.DataFrame(panel_rows)
bt = pd.DataFrame(bt_rows)

# ---------------------------------------------------------------------------
# 9. Write outputs
# ---------------------------------------------------------------------------
def r2(df):
    out = df.copy()
    for c in out.columns:
        if out[c].dtype.kind == "f":
            out[c] = out[c].round(2)
    return out

r2(reg).to_csv(os.path.join(OUT, "uk-rent-vs-buy-breakeven-by-region-2026.csv"), index=False)
r2(la).to_csv(os.path.join(OUT, "uk-rent-vs-buy-breakeven-by-local-authority-2026.csv"), index=False)
r2(bt).to_csv(os.path.join(OUT, "uk-rent-vs-buy-backtest-2005-2026.csv"), index=False)
r2(sens).to_csv(os.path.join(OUT, "uk-rent-vs-buy-sensitivity-2026.csv"), index=False)
panel.round(6).to_csv(os.path.join(OUT, "uk-rent-vs-buy-monthly-panel-2005-2026.csv"), index=False)
r2(snap).round(0).to_csv(os.path.join(OUT, "uk-rent-vs-buy-first-year-costs-2026.csv"), index=False)

summary = dict(assumptions=A, rate90=RATE90, rate75=RATE75, g_price=G_PRICE, g_rent=G_RENT,
               g_price_uk_1995=G_PRICE_1995, n_la=len(la))
with open(os.path.join(OUT, "summary.json"), "w") as f:
    json.dump(summary, f, indent=1, default=str)

# Key numbers (also printed by the R script; they should agree)
print(f"Rates Sep 2026: 90% LTV {RATE90:.2f}%, 75% LTV {RATE75:.2f}%")
print(f"Baseline growth, England Jul 2005-Jul 2026: prices {G_PRICE:.2f}%/yr, rents {G_RENT:.2f}%/yr")
show = reg[(reg.property_type == "all")].pivot(index="region", columns="deposit_pct", values="breakeven_years")
print("Break-even years, all property types:\n", show.round(2).to_string())
t = sens[sens.table == "rate_x_price_growth"].pivot(index="mortgage_rate_pct", columns="price_growth_pct",
                                                     values="median_breakeven_years")
print("Median break-even (years) by mortgage rate x price growth:\n", t.round(2).to_string())
print("LA break-even quartiles:", la.breakeven_years.quantile([0, .25, .5, .75, 1]).round(2).tolist(),
      "never within 30y:", int(la.breakeven_years.isna().sum()))
rk = la[["breakeven_years", "breakeven_years_terraced"]].replace(np.nan, 99).rank()
print("LA rank correlation, all types vs terraced:", round(rk.corr().iloc[0, 1], 2))
b5 = bt[(bt.return_assumption == "fixed_5pct")]
for h in (2, 5, 10):
    s = b5[b5.years_held == h]
    print(f"Backtest (5% return), held {h}y: buying ahead in {(s.buyer_minus_renter > 0).mean()*100:.0f}% of {len(s)} cases")
bb = bt[(bt.return_assumption == "bank_rate")]
for h in (2, 5, 10):
    s = bb[bb.years_held == h]
    print(f"Backtest (Bank Rate cash), held {h}y: buying ahead in {(s.buyer_minus_renter > 0).mean()*100:.0f}% of {len(s)} cases")

# ---------------------------------------------------------------------------
# 10. Presets for the Rent vs Buy Calculator (js/rent-vs-buy-data.js)
# ---------------------------------------------------------------------------
presets = []
for name, code, nation in REGIONS:
    d = reg[(reg.area_code == code) & (reg.deposit_pct == 10)]
    presets.append(dict(name=name, code=code, nation=nation, types={
        t: dict(price=int(d[d.property_type == t].price_jul2026.iloc[0]),
                rent=int(d[d.property_type == t].monthly_rent_jul2026.iloc[0]))
        for t in ["all", "terraced", "semi", "detached", "flat"]}))
calc = dict(
    asOf="Prices and rents: July 2026 (HM Land Registry UK HPI; ONS PIPR). Mortgage rates: September 2026 (Bank of England).",
    rate90=RATE90, rate75=RATE75, priceGrowth=round(G_PRICE, 2), rentGrowth=round(G_RENT, 2),
    assumptions=dict(term=A["term_years"], fixMonths=A["fix_months"], productFee=A["product_fee"],
                     conveyancingHouse=A["conveyancing_house"], conveyancingFlat=A["conveyancing_flat"],
                     surveyPoints=A["survey_points"], agentFeePct=A["agent_fee_pct"],
                     conveyancingSell=A["conveyancing_sell"], maintenanceHousePct=A["maintenance_house_pct"],
                     maintenanceFlatPct=A["maintenance_flat_pct"], buildingsInsurance=A["buildings_insurance"],
                     serviceChargeEW=A["service_charge_ew"], serviceChargeLondon=A["service_charge_london"],
                     costInflationPct=A["cost_inflation_pct"], investReturnPct=A["invest_return_pct"]),
    regions=presets)
with open(os.path.join(OUT, "rent-vs-buy-data.js"), "w") as f:
    f.write("/* Rent vs Buy Calculator presets, generated by data/uk-rent-vs-buy-analysis.py (Truth with Data, Oct 2026).\n"
            "   Average prices and rents by region and property type; sources in blog/is-renting-dead-money-uk.html. */\n"
            "var RVB_DATA = " + json.dumps(calc, separators=(",", ":")) + ";\n")
