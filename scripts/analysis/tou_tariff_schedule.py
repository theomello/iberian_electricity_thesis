"""Old (to 31 May 2021) and new (from 1 June 2021) energy prices by hour for the Spanish industrial and commercial access tariffs, peninsula.

Sources and values: docs/tou-policy-sources.md. New: tolls + charges, Circular 3/2020 art. 7 periods (3.0TD, 6.1TD-6.4TD), six periods by season; prices in outputs/tables/tou_tariff_prices_2021.csv.
Old: access-toll energy terms of Orden IET/107/2014 and IET/2444/2014; periods of Orden ITC/2794/2007, annex II: 3.0A and 3.1A have three periods by winter/summer clock time (every day, no weekend
distinction); 6.1A, 6.2, 6.3, 6.4 have six periods by day type (A: Dec-Feb, A1: second half of June and July, B: first half of June and September, B1: November and March, C: April, May, October;
D: weekends, national holidays and all of August). Holidays: the repo's national-holiday table plus 6 January (an approximation of the 'national, not substitutable' rule).
Writes outputs/tables/tou_tariff_hourly_change.csv (month x day type x hour x tariff).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables"
OLD = {"3.0": [18.762, 12.575, 4.670], "3.1": [14.335, 12.754, 7.805], "6.1": [26.674, 19.921, 10.615, 5.283, 3.411, 2.137],
       "6.2": [15.587, 11.641, 6.204, 3.087, 1.993, 1.247], "6.3": [15.048, 11.237, 5.987, 2.979, 1.924, 1.206], "6.4": [8.465, 7.022, 4.025, 2.285, 1.475, 1.018]}
rng = lambda *pairs: [h for a, b in pairs for h in range(a, b)]


def old_period_6(day_type, hour):
    """Old six-period schedule, peninsula (ITC/2794/2007 annex II, 3.3.3); returns 1-6."""
    if day_type == "D" or hour < 8:
        return 6
    t = {"A": {1: rng((10, 13), (18, 21)), 2: rng((8, 10), (13, 18), (21, 24))},
         "A1": {1: rng((11, 19)), 2: rng((8, 11), (19, 24))},
         "B": {3: rng((9, 15)), 4: rng((8, 9), (15, 24))},
         "B1": {3: rng((16, 22)), 4: rng((8, 16), (22, 24))},
         "C": {5: rng((8, 24))}}[day_type]
    return next(p for p, hs in t.items() if hour in hs)


def old_day_type(date, holiday):
    if date.dayofweek >= 5 or holiday or date.month == 8:
        return "D"
    m, d = date.month, date.day
    if m in (12, 1, 2):
        return "A"
    if m == 7 or (m == 6 and d > 15):
        return "A1"
    if m == 9 or (m == 6 and d <= 15):
        return "B"
    if m in (11, 3):
        return "B1"
    return "C"  # April, May, October


def old_period_3(date, hour):
    """Old three-period schedule for 3.0A and 3.1A, zone 1 (peninsula): winter or summer clock time; applies every day."""
    summer = pd.Timestamp(date).tz_localize("Europe/Madrid") + pd.Timedelta(hours=12)
    summer = bool(summer.dst())
    if summer:
        return 1 if 11 <= hour < 15 else (3 if hour < 8 else 2)
    return 1 if 18 <= hour < 22 else (3 if hour < 8 else 2)


def new_period_6(date, hour, holiday):
    """Circular 3/2020 art. 7, peninsula; returns 1-6."""
    if date.dayofweek >= 5 or holiday or (date.month == 1 and date.day == 6) or hour < 8:
        return 6
    m = date.month
    base = 1 if m in (1, 2, 7, 12) else 2 if m in (3, 11) else 3 if m in (6, 8, 9) else 4
    return base if (9 <= hour < 14 or 18 <= hour < 22) else base + 1


def holidays():
    h = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    return set(pd.to_datetime(h[(h.area == "AN") & (h.mark == "national")].date))


def new_price_table():
    p = pd.read_csv(OUT / "tou_tariff_prices_2021.csv")
    return {(r.tariff.replace("TD", ""), int(r.period[1])): r.total_eur_mwh for r in p.itertuples()}


def schedule(dates):
    hol = holidays()
    newp = new_price_table()
    rows = []
    for d in dates:
        d = pd.Timestamp(d)
        isH = d in hol
        dt = old_day_type(d, isH)
        for h in range(24):
            p6o, p6n = old_period_6(dt, h), new_period_6(d, h, isH)
            p3o = old_period_3(d, h)
            for tar in ("3.0", "3.1", "6.1", "6.2", "6.3", "6.4"):
                po = p3o if tar in ("3.0", "3.1") else p6o
                old = OLD[tar][po - 1]
                if tar == "3.1":
                    continue  # 3.1A (1-36 kV, up to 450 kW) became 6.1TD: handled below
                new = newp[(tar, p6n)]
                rows.append(dict(date=d, hour=h, tariff=tar, old_period=po, new_period=p6n, old_price=old, new_price=new))
            # 3.1A customers move to 6.1TD
            rows.append(dict(date=d, hour=h, tariff="3.1->6.1", old_period=p3o, new_period=p6n, old_price=OLD["3.1"][p3o - 1], new_price=newp[("6.1", p6n)]))
    return pd.DataFrame(rows)


def main():
    dates = pd.date_range("2019-01-01", "2019-12-31")  # one calendar year of structure (2019 holidays)
    s = schedule(dates)
    s["month"] = s.date.dt.month
    s["daytype"] = np.where(s.date.dt.dayofweek >= 5, "weekend", "weekday")
    g = s.groupby(["tariff", "month", "daytype", "hour"])[["old_price", "new_price"]].mean().reset_index()
    g["dln_price"] = np.log(g.new_price / g.old_price)
    g.round(4).to_csv(OUT / "tou_tariff_hourly_change.csv", index=False)
    # checks: every hour assigned (no KeyError above); coverage by period over the year
    chk = s[s.tariff == "6.1"].groupby("new_period").size() / 365
    print("new periods, hours per day on average (6.1):", chk.round(2).to_dict())
    chk = s[s.tariff == "6.1"].groupby("old_period").size() / 365
    print("old periods, hours per day on average (6.1):", chk.round(2).to_dict())
    pd.set_option("display.width", 200)
    for tar in ("3.0", "3.1->6.1", "6.1", "6.2", "6.3", "6.4"):
        w = g[(g.tariff == tar) & (g.daytype == "weekday") & (g.month.isin([7]))]
        print(tar, "July weekday: ln(new/old) price by hour block:",
              {f"{a}-{b - 1}h": round(float(w[(w.hour >= a) & (w.hour < b)].dln_price.mean()), 2) for a, b in ((0, 8), (8, 10), (10, 14), (14, 18), (18, 22), (22, 24))})


if __name__ == "__main__":
    main()
