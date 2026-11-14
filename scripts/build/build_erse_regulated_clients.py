#!/usr/bin/env python3
"""Portugal's regulated clients (last-resort supplier, CUR) by month, from ERSE's bulletins on disk (fetch_erse_bulletins.py): outputs/tables/erse_regulated_clients_monthly.csv.

The text of each bulletin says 'No global, cerca de X milhões|mil clientes permanecem ... no CUR'. Resolution: 10,000 clients to June 2020 ('1,08 milhões'), 1,000 from January 2021 ('959 mil'); the July-December 2020
bulletins and the missing March-April 2021 issues do not state it in the text (blank). The free-market client count (exact, 2019-01 -> 2020-12) is carried beside it.
"""
import glob
import os
import re
from pathlib import Path

import pandas as pd
import pymupdf

ROOT = Path(__file__).resolve().parent.parent.parent


def main():
    rows = []
    for f in sorted(glob.glob(str(ROOT / "data/erse/boletim_*.pdf"))):
        ym = os.path.basename(f)[len("boletim_"):-4]
        t = re.sub(r"\s+", " ", " ".join(p.get_text() for p in pymupdf.open(f)))
        c = re.search(r"(?i)No global, cerca de ([\d,\.]+) (milh[õo]es|mil) (?:de )?clientes", t)
        ml = re.search(r"(\d{1,2}\s\d{3}\s\d{3}) Clientes", t)
        cur = None
        if c:
            v = float(c.group(1).replace(",", "."))
            cur = round(v * (1e6 if c.group(2).startswith("milh") else 1e3))
        rows.append(dict(month=f"{ym[:4]}-{ym[4:]}", regulated_clients_cur=cur, free_market_clients=int(ml.group(1).replace(" ", "")) if ml else None,
                         resolution=("10,000" if cur and cur >= 1e6 else "1,000") if cur else "", source=f"ERSE Boletim do Mercado Liberalizado de Eletricidade {ym[:4]}-{ym[4:]}"))
    d = pd.DataFrame(rows)
    d.to_csv(ROOT / "outputs/tables/erse_regulated_clients_monthly.csv", index=False)
    print(d[["month", "regulated_clients_cur", "free_market_clients"]].to_string(index=False))


if __name__ == "__main__":
    main()
