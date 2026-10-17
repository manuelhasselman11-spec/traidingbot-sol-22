import numpy as np, pandas as pd, numba as nb
from . import data, engine, strategies as S

MEMES={"BONK","WIF","BOME","PNUT","ACT","PENGU","TRUMP","PUMP"}
TIER1={"SOL"}
def cost_side(tok,scale=1.0):
    base=0.0020 if tok in TIER1 else (0.0040 if tok in MEMES else 0.0030)
    return base*scale
STOP_SLIP=0.003
MIN_QV=0.0   # optional liquidity gate: min 30d average DAILY quote volume (USD) to allow new entries
DEV_END=pd.Timestamp("2025-04-01",tz="UTC")
BPD={"15m":96,"1h":24,"2h":12,"4h":6,"12h":2,"1d":1,"1d6":1,"1d12":1,"1d18":1}

_CACHE={}
def get_data(tf):
    if tf not in _CACHE: _CACHE[tf]=data.load_all(tf)
    return _CACHE[tf]

def run_strategy(name,params,tf="4h",cost_scale=1.0,tokens=None,fn=None,direction=1,funding_day=0.0):
    fn=fn or S.REG[name][0]
    D=get_data(tf); rets={}; trades={}
    warm=data.WARMUP_DAYS*BPD[tf]
    for tok,df in D.items():
        if tokens and tok not in tokens: continue
        if len(df)<warm+100: continue
        sig=fn(df,tf=tf,**params)
        if MIN_QV>0:
            dv=(df.quote_volume.rolling(30*BPD[tf]).sum()/30).shift(1)
            sig=dict(sig); sig['entry']=sig['entry']&(dv>=MIN_QV).fillna(False).values
        r,t=engine.run_token(df,sig,cost_side(tok,cost_scale),STOP_SLIP,warm,direction,funding_day/BPD[tf])
        r.iloc[:warm]=np.nan
        rets[tok]=r; t["token"]=tok; trades[tok]=t
    R=pd.DataFrame(rets)
    T=pd.concat(trades.values(),ignore_index=True) if trades else pd.DataFrame()
    return R,T

def bh_returns(tf="4h",tokens=None):
    D=get_data(tf); warm=data.WARMUP_DAYS*BPD[tf]; out={}
    for tok,df in D.items():
        if tokens and tok not in tokens: continue
        if len(df)<warm+100: continue
        r=df.open.shift(-1)/df.open-1   # open-to-open to match engine timing
        r=(df.close/df.close.shift(1)-1)
        r.iloc[:warm]=np.nan
        out[tok]=r
    return pd.DataFrame(out)

def combine(R,weights=None):
    """equal-weight across tokens that are listed (non-NaN) at each bar"""
    return R.mean(axis=1,skipna=True).fillna(0.0)

@nb.njit(cache=True)
def _dd_breaker(r,dd_limit,cool,lookahead_free=True):
    n=len(r); out=np.zeros(n); eq=1.0; peak=1.0; off=0
    for i in range(n):
        if off>0:
            off-=1
            if off==0: peak=eq   # reset after cooldown
            continue_=True
            out[i]=0.0
            continue
        out[i]=r[i]
        eq*=1.0+r[i]
        if eq>peak: peak=eq
        if eq/peak-1.0<-dd_limit:
            off=cool
    return out

def overlay_breaker(r,dd_limit=0.25,cool_bars=6*14):
    """Portfolio circuit breaker: if equity drawdown from peak exceeds dd_limit, go to cash for cool_bars, then restart with a fresh peak."""
    return pd.Series(_dd_breaker(r.values.astype(np.float64),dd_limit,cool_bars),index=r.index)

def overlay_regime(r,tf="4h",ref="BTC",ma_days=50,flip_cost=0.001,ref_close=None):
    """Only hold risk when the reference asset (BTC) closes above its MA — known at previous close."""
    b=ref_close if ref_close is not None else data.resample(data.load_raw(ref),tf).close
    ma=b.rolling(ma_days*BPD[tf]).mean()
    on=(b>ma).shift(1).reindex(r.index).fillna(False)
    out=r.where(on,0.0)
    flips=(on!=on.shift(1)).astype(float); flips.iloc[0]=0
    return out-flips*flip_cost

def vol_scale(r,target=0.5,tf="4h",span=30):
    """Scale portfolio exposure to a target annual vol using only past realised vol (shifted), max 1x (no leverage)."""
    ppy=BPD[tf]*365
    v=r.rolling(span*BPD[tf]).std().shift(1)*np.sqrt(ppy)
    s=(target/v).clip(0,1).fillna(0.0)
    return r*s
