"""Scoping check for the sustained-price-level design (descriptive; no estimation).

    .venv/bin/python -I scripts/analysis/industry_sector_intensity_scoping.py

Question: across industry sectors, are electricity intensity and gas intensity separable? Energy spending by sector and product (INE ECE table 01001, thousand euros, 2-digit CNAE) is divided by the sector's value added at basic prices
(INE input-output Tabla1, million euros, same year; ECE years 2017, 2019, 2021, 2022 match the 2016-22 tables). ECE divisions are aggregated to the input-output CPA groups. Writes outputs/tables/industry_sector_intensity_scoping.csv.
"""
import re
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent.parent
INE = ROOT / "data" / "ine"
OUT = ROOT / "outputs" / "tables"


def ece():
    txt = (INE / "ece" / "01001.px").read_text(encoding="latin-1")
    v = lambda n: re.findall(r'"([^"]*)"', re.search(r'VALUES\("%s[^"]*"\)=(.*?);' % n, txt, re.S).group(1))
    act, prod, per = v("Actividad"), v("Producto"), v("Periodo")
    data = re.search(r"DATA=(.*?);", txt, re.S).group(1).split()
    a = np.array([np.nan if x.startswith((".", '"')) else float(x) for x in data]).reshape(len(act), len(prod), len(per))
    rows = [(ac, pr, int(y), a[i, j, k]) for i, ac in enumerate(act) for j, pr in enumerate(prod) for k, y in enumerate(per)]
    D = pd.DataFrame(rows, columns=["act", "prod", "year", "v"])
    D["div"] = D.act.str.extract(r"^(\d{2}) ")[0]
    return D[D["div"].notna()]


def groups(year):
    wb = openpyxl.load_workbook(INE / "tio" / f"cne_tio_{str(year)[2:]}.xlsx", read_only=True, data_only=True)
    t4 = list(wb["Tabla4"].iter_rows(values_only=True))
    t1 = list(wb["Tabla1"].iter_rows(values_only=True))
    cpa = {}
    for r in t4[8:]:
        if r[1] and r[2] and str(r[2]).strip() and str(r[3] or "").strip():
            cpa[str(r[2]).strip()] = str(r[3]).strip().replace("–", "-")
    names = [str(x) for x in t1[7][2:]]
    lab = {str(r[1]).strip(): r for r in t1[8:] if r[1]}
    return names, lab, t4


def main():
    E = ece()
    wb0 = openpyxl.load_workbook(INE / "tio" / "cne_tio_20.xlsx", read_only=True, data_only=True)
    t4 = list(wb0["Tabla4"].iter_rows(values_only=True))
    code = {}  # product number -> cpa code
    for r in t4[8:]:
        if r[2] is not None and r[3] is not None and str(r[2]).strip().isdigit():
            code[int(str(r[2]).strip())] = str(r[3]).strip().replace("–", "-")
    rows = []
    for y in (2017, 2019, 2021, 2022):
        wb = openpyxl.load_workbook(INE / "tio" / f"cne_tio_{str(y)[2:]}.xlsx", read_only=True, data_only=True)
        t1 = list(wb["Tabla1"].iter_rows(values_only=True))
        vab = next(r for r in t1 if r[1] and str(r[1]).startswith("Valor añadido bruto"))
        prd = next(r for r in t1 if r[1] and str(r[1]).startswith("Producción a precios básicos"))
        for i in range(1, 80):
            c = code.get(i)
            if c is None:
                continue
            a, b = (c.split("-") + [c])[:2] if "-" in c else (c, c)
            lo, hi = int(a), int(b)
            if not 5 <= lo <= 33:
                continue
            ds = [f"{d:02d}" for d in range(lo, hi + 1)]
            sub = E[(E["div"].isin(ds)) & (E.year == y)]
            if sub.empty:
                continue
            g = sub.pivot_table(index="prod", values="v", aggfunc="sum")["v"]
            rows.append(dict(year=y, cpa=c, vab=float(vab[1 + i]), out=float(prd[1 + i]), el=g.get("Electricidad"), gas=g.get("Gas"), tot=g.get("Total consumos energéticos")))
    D = pd.DataFrame(rows)
    D["el_vab"] = D.el / 1000 / D.vab  # thousand euros -> million euros
    D["gas_vab"] = D.gas / 1000 / D.vab
    D["el_out"] = D.el / 1000 / D.out
    D["gas_out"] = D.gas / 1000 / D.out
    D["sh_el"] = D.el / D.tot
    D["sh_gas"] = D.gas / D.tot
    D.round(5).to_csv(OUT / "industry_sector_intensity_scoping.csv", index=False)
    pd.set_option("display.width", 220)
    res = []
    for y, g in D.groupby("year"):
        gg = g.dropna(subset=["el_vab", "gas_vab"])
        gp = gg[(gg.el_vab > 0) & (gg.gas_vab > 0)]
        res.append(dict(year=y, n=len(gg), rank_corr_vab=spearmanr(gg.el_vab, gg.gas_vab)[0], log_corr_vab=np.corrcoef(np.log(gp.el_vab), np.log(gp.gas_vab))[0, 1], rank_corr_out=spearmanr(gg.el_out, gg.gas_out)[0], rank_corr_shares=spearmanr(gg.sh_el, gg.sh_gas)[0]))
    print(pd.DataFrame(res).round(2).to_string(index=False))
    P = D.pivot(index="cpa", columns="year", values="el_vab")
    print("electricity intensity (spend / value added), rank corr across years:\n", P.corr(method="spearman").round(2).to_string())
    G = D[D.year == 2022].sort_values("el_vab", ascending=False)
    print(G[["cpa", "el_vab", "gas_vab", "sh_el", "sh_gas", "vab"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
