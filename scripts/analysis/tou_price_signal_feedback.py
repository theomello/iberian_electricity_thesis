"""T3: did the reform change the price signal, and does the price change feed back into demand?
(docs/specs/2026-11-19-price-signal-feedback-design.md)

    .venv/bin/python scripts/analysis/tou_price_signal_feedback.py

(a1) descriptive: the reform's evening-minus-night price contrast against the observed spread (2021 window, the same
     calendar weekdays of 2019 and 2020, the nine 106-day placebo windows of the price-effect test).
(a2) P1: kappa = 1000 * 2h / band (EUR/MWh per GW), band = all status-O offers within +/-h of the price, at p* and at
     p* - dp (T2's hour file, one row per hour); rule |mean dkappa| <= 10% of mean kappa, all / evening / night.
(b)  B1: feedback MW = |sigma| lambda theta |dp| / rbar * L, households (E0, ESIOS 1201) + industry (6.2-6.4, ESIOS
     1216-1218), at worst-case inputs, against |mean dQ| of the block (neutral level); <= 10%; blocks with |dQ| < 50 MW
     reported, not judged.
Writes outputs/tables/tou_price_signal_feedback{,_checks}.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import industry_iv_noise_reducers as N  # noqa: E402
import tou_cross_tariff as CT  # noqa: E402
import tou_did as T  # noqa: E402
from holidays import ES_MAINLAND, _matrix  # noqa: E402

OUT = T.OUT
H = 5.0
EVENING, NIGHT = list(range(18, 22)), list(range(0, 8))
PEAK = list(range(10, 14)) + EVENING
POST0, POST1 = pd.Timestamp("2021-06-01"), pd.Timestamp("2021-09-14")
PLACEBO_STARTS = list(pd.date_range("2019-01-01", "2019-09-01", freq="MS"))
P1_BAR, B1_BAR, MIN_DQ = 0.10, 0.10, 50.0
# load effects (log points) and the M-F gap of the price-effect test (its Results section)
B_TYPE = {"peak": -0.0528, "mid": -0.0364, "off": 0.0143}
GAP = -0.0457
S_IND = 0.851  # T1 step 0: wholesale share of the industrial per-period price
INPUTS = {  # group: (sigma, lambda, theta, rbar mode)
    "worst": {"hh": (0.12, 1.0, 0.30, "p"), "ind": (0.544, 0.71, 0.49, "p")},
    "point": {"hh": (0.09, 1.0, 0.25, "p"), "ind": (0.177, 0.01, 0.32, "full")},
}


def block(hour):
    return np.where(np.isin(hour, EVENING), "evening", np.where(np.isin(hour, NIGHT), "night", "other"))


def htype(hour):
    return np.where(np.isin(hour, PEAK), "peak", np.where(np.isin(hour, NIGHT), "off", "mid"))


def weekdays(d0, d1):
    days = pd.date_range(d0, d1)
    hol = _matrix(days)[list(ES_MAINLAND)].eq(1).all(axis=1)
    return days[(days.dayofweek < 5) & ~hol.to_numpy()]


def spread(p, days):
    s = p[p.index.get_level_values("date").isin(days)].reset_index()
    b = block(s.hour.to_numpy())
    return s.p[b == "evening"].mean() - s.p[b == "night"].mean()


def main():
    hf = pd.read_csv(OUT / "tou_reform_market_power_hours.csv", parse_dates=["date"])
    h = hf.drop_duplicates(["date", "period"]).reset_index(drop=True)
    print("hours", len(h), flush=True)
    p = CT.omie_hourly()
    idx = pd.MultiIndex.from_arrays([h.date, h.hour])
    h["p"] = p.reindex(idx).to_numpy()
    h["blk"] = block(h.hour.to_numpy())
    rows, checks = [], []

    # (a1) shape
    con = pd.read_csv(OUT / "tou_price_effect_summary.csv")
    con = con[con["sample"] == "post window"].set_index("level").contrast
    s21v = h.p[h.blk == "evening"].mean() - h.p[h.blk == "night"].mean()
    rows.append(dict(part="a1", item="observed spread 2021 window, valid hours", value=s21v))
    for y in (2019, 2020, 2021):
        v = spread(p, weekdays(f"{y}-06-01", f"{y}-09-14"))
        rows.append(dict(part="a1", item=f"observed spread {y}-06-01..09-14, weekdays", value=v))
    plc = []
    for s0 in PLACEBO_STARTS:
        v = spread(p, weekdays(s0, s0 + pd.Timedelta(days=105)))
        plc.append(v)
        rows.append(dict(part="a1", item=f"observed spread placebo {s0:%Y-%m}", value=v))
    for lev, c in con.items():
        rows.append(dict(part="a1", item=f"reform contrast / observed 2021 spread, {lev}", value=c / s21v))
    rows.append(dict(part="a1", item="placebo spread min", value=min(plc)))
    rows.append(dict(part="a1", item="placebo spread max", value=max(plc)))

    # (a2) kappa
    for lev in ("neutral", "F", "M"):
        ka = 1000 * 2 * H / h.band_p_star
        kc = 1000 * 2 * H / h[f"band_pcf_{lev}"]
        dk = ka - kc
        for b in ("all", "evening", "night"):
            m = np.ones(len(h), bool) if b == "all" else (h.blk == b).to_numpy()
            ok = m & np.isfinite(dk.to_numpy())
            mk, md = ka[ok].mean(), dk[ok].mean()
            rows.append(dict(part="a2", item=f"kappa {lev} {b}", value=mk, dkappa=md, ratio=abs(md) / mk, n=int(ok.sum())))
            if lev == "neutral":
                checks.append(dict(rule="P1", block=b, value=abs(md) / mk, bar=P1_BAR, verdict="pass" if abs(md) / mk <= P1_BAR else "FAIL"))
    hk = h.assign(dk=1000 * 2 * H / h.band_p_star - 1000 * 2 * H / h.band_pcf_neutral, ka=1000 * 2 * H / h.band_p_star)
    for hr, g in hk.groupby("hour"):
        rows.append(dict(part="a2 by hour", item=f"hour {hr}", value=g.ka.mean(), dkappa=g.dk.mean(), ratio=abs(g.dk.mean()) / g.ka.mean()))

    # (b) feedback
    e0 = N.hourly(1201).reindex(idx).to_numpy()
    ind = sum(N.hourly(i) for i in (1216, 1217, 1218)).reindex(idx).to_numpy()
    bt = np.array([B_TYPE[t] for t in htype(h.hour.to_numpy())])
    dq = {"neutral": h.dq_neutral.to_numpy(), "F": e0 * (np.exp(-bt) - 1.0), "M": e0 * (np.exp(-(bt + GAP)) - 1.0)}
    print("missing E0", int(np.isnan(e0).sum()), "missing industry", int(np.isnan(ind).sum()), flush=True)
    pp = h.p.to_numpy()
    for case, inp in INPUTS.items():
        for lev in ("neutral", "F", "M"):
            adp = np.abs(h[f"dp_{lev}"].to_numpy())
            fb = {}
            for g, L in (("hh", e0), ("ind", ind)):
                sg, la, th, mode = inp[g]
                rbar = pp if mode == "p" else pp / S_IND
                fb[g] = sg * la * th * adp / rbar * L
            for b in ("evening", "night"):
                m = (h.blk == b).to_numpy() & np.isfinite(fb["hh"]) & np.isfinite(fb["ind"]) & (pp > 0)
                f_hh, f_ind = fb["hh"][m].mean(), fb["ind"][m].mean()
                dqm, dqa = abs(dq[lev][m].mean()), np.abs(dq[lev][m]).mean()
                share = (f_hh + f_ind) / dqm
                rows.append(dict(part="b", item=f"{case} {lev} {b}", value=f_hh + f_ind, f_hh=f_hh, f_ind=f_ind,
                                 dq_abs_mean=dqm, dq_mean_abs=dqa, ratio=share, share_mean_abs=(f_hh + f_ind) / dqa,
                                 multiplier=1 / (1 - share) if share < 1 else np.nan, n=int(m.sum())))
                if case == "worst" and lev == "neutral":
                    if dqm < MIN_DQ:
                        v = "reported (|dQ| < 50 MW)"
                    else:
                        v = "pass" if share <= B1_BAR else "FAIL"
                    checks.append(dict(rule="B1", block=b, value=share, bar=B1_BAR, verdict=v, dq=dqm))

    R, C = pd.DataFrame(rows), pd.DataFrame(checks)
    R.round(5).to_csv(OUT / "tou_price_signal_feedback.csv", index=False)
    C.round(5).to_csv(OUT / "tou_price_signal_feedback_checks.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_columns", 20, "display.max_rows", 200):
        print(R.round(4).to_string(index=False))
        print(C.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
