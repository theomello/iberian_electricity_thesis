"""Split the gas-cap export leak by border: exporters' gain (price fall x scheduled export, ESIOS 32/34/35)
at rho 0.55/0.73/1.0 from gas_cap_dispatch_welfare_hourly, and the charge an export would bear at ESIOS 1907/1908/1909.
Section I1b of notes/rq-crisis-quantity.md."""
import pandas as pd, sys, zoneinfo
sys.path.insert(0,'scripts/lib')
from omie_common import day_periods_utc
tz=zoneinfo.ZoneInfo('Europe/Madrid')
h=pd.read_parquet('outputs/tables/gas_cap_dispatch_welfare_hourly.parquet'); h=h[h.ok]
def esios(i):
    e=pd.read_parquet(f'data/esios/esios_{i}.parquet')
    if 'geo_name' in e and e.geo_name.nunique()>1: e=e[e.geo_name==e.geo_name.value_counts().index[0]]
    return e.assign(t=pd.to_datetime(e.utc_timestamp,utc=True)).groupby('t').value.sum()
ex={k:-esios(i) for k,i in [('France',32),('Morocco',34),('Andorra',35)]}
rates={i:esios(i) for i in (1907,1908,1909)}
m={}
for d,g in h[['date','period']].drop_duplicates().groupby('date'):
    n=g.period.max()
    ts=day_periods_utc(d.date(), int(n), tz)
    for p,t in enumerate(ts,1): m[(d,p)]=pd.Timestamp(t)
h['t']=[m[(d,p)] for d,p in zip(h.date,h.period)]
h['t']=pd.to_datetime(h.t,utc=True)
for rho in [0.55,0.73,1.0]:
    x=h[h.rho==rho].set_index('t'); dp=x.p_c-x.p_o
    print(rho, {k:round((dp*s.reindex(dp.index).fillna(0)).sum()/1e6,1) for k,s in ex.items()})
idx=pd.DatetimeIndex(h[h.rho==0.73].t)
for k,s in ex.items():
    s=s.reindex(idx).fillna(0)
    print(k,'TWh',round(s.sum()/1e6,2), {r:round((s*v.reindex(idx).fillna(0)).sum()/1e6,1) for r,v in rates.items()})
