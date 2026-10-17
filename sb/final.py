"""Final ensemble definition (frozen a-priori, NOT tuned on the test window) + helpers used by both research and the web app."""
import numpy as np, pandas as pd
from . import portfolio as P, metrics as M, strategies as S

TF="1d"
COMPONENTS=[("donchian",dict(entry_days=e,exit_days=10,atr_mult=4.0)) for e in (20,40,60,100)]+\
           [("vol_breakout",dict(entry_days=e,vol_mult=1.5,atr_mult=3.5)) for e in (10,20)]
OVERLAY=dict(regime_ref="BTC",regime_ma_days=100,breaker_dd=0.25,breaker_cool_days=14)

def label(n,p): return n+"("+",".join(f"{k}={v}" for k,v in p.items())+")"

def build(tf=TF,cost_scale=1.0,tokens=None,components=None,overlay=True,regime=True,breaker=True,ref_close=None):
    comps=components or COMPONENTS
    Rs=[];Ts=[]
    for n,p in comps:
        R,T=P.run_strategy(n,p,tf,cost_scale,tokens=tokens); R=R.copy(); T=T.copy(); T["strategy"]=label(n,p); Rs.append(R); Ts.append(T)
    cols=sorted(set().union(*[set(R.columns) for R in Rs]))
    Rtok=sum(R.reindex(columns=cols).fillna(0.0).where(R.reindex(columns=cols).notna(),0.0) for R in Rs)/len(Rs)
    # keep NaN where not listed
    mask=Rs[0].reindex(columns=cols).notna()
    Rtok=Rtok.where(mask)
    r=P.combine(Rtok)
    r_raw=r
    if overlay:
        if regime: r=P.overlay_regime(r,tf,OVERLAY["regime_ref"],OVERLAY["regime_ma_days"],ref_close=ref_close)
        if breaker: r=P.overlay_breaker(r,OVERLAY["breaker_dd"],OVERLAY["breaker_cool_days"]*P.BPD[tf])
    T=pd.concat(Ts,ignore_index=True)
    return dict(r=r,r_raw=r_raw,Rtok=Rtok,T=T,Rs=Rs)
