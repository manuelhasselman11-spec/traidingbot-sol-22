"""Long-only signal generators. Every signal at bar t uses only data up to and including the close of bar t."""
import numpy as np, pandas as pd
from . import indicators as I

HRS={"15m":0.25,"1h":1,"2h":2,"4h":4,"12h":12,"1d":24,"1d6":24,"1d12":24,"1d18":24}
BPY={k:int(8760/v) for k,v in HRS.items()}

def _size(df,tf,mode,target_vol,maxsize=1.0):
    if mode=="full": return pd.Series(1.0,index=df.index)
    v=I.realized_vol(df.close,(288 if tf=="15m" else 72) if tf in ("15m","1h") else (36 if tf in ("2h","4h") else 20),BPY[tf])
    return (target_vol/v).clip(0.2,maxsize).fillna(0.2)

def _pack(df,entry,exit_,tf,atr_mult=3.0,trail=1,size_mode="vol",target_vol=0.8,max_hold=0,atr_n=14):
    a=I.atr(df,atr_n)
    sd=(atr_mult*a/df.close).fillna(0.0) if atr_mult>0 else pd.Series(0.0,index=df.index)
    return dict(entry=entry.fillna(False).values,exit=exit_.fillna(False).values,size=_size(df,tf,size_mode,target_vol).values,
                stop_dist=sd.clip(upper=0.5).values,trail=trail,max_hold=max_hold)

# bars per day helper: lookbacks are expressed in DAYS-equivalent so params are meaningful across timeframes
def bars(days,tf): return max(2,int(round(days*24/HRS[tf])))

def donchian(df,tf="4h",entry_days=20,exit_days=10,atr_mult=3.0,vol_mult=0,size_mode="vol",target_vol=0.8,**k):
    n1,n2=bars(entry_days,tf),bars(exit_days,tf)
    hi=df.high.rolling(n1).max().shift(1); lo=df.low.rolling(n2).min().shift(1)
    entry=df.close>hi
    if vol_mult>0: entry&=df.volume>vol_mult*df.volume.rolling(bars(10,tf)).mean().shift(1)
    exit_=df.close<lo
    return _pack(df,entry,exit_,tf,atr_mult,1,size_mode,target_vol)

def donchian_short(df,tf="4h",entry_days=20,exit_days=10,atr_mult=3.0,vol_mult=0,size_mode="vol",target_vol=0.8,**k):
    n1,n2=bars(entry_days,tf),bars(exit_days,tf)
    lo=df.low.rolling(n1).min().shift(1); hi=df.high.rolling(n2).max().shift(1)
    entry=df.close<lo
    exit_=df.close>hi
    return _pack(df,entry,exit_,tf,atr_mult,1,size_mode,target_vol)

def ema_trend(df,tf="4h",fast_days=10,slow_days=40,adx_min=0,atr_mult=3.5,size_mode="vol",target_vol=0.8,**k):
    f,s=I.ema(df.close,bars(fast_days,tf)),I.ema(df.close,bars(slow_days,tf))
    up=(f>s)&(df.close>s)
    entry=up&~up.shift(1,fill_value=False)
    if adx_min>0:
        ax=I.adx(df,14); entry&=ax>adx_min
        # allow entry while trend persists once ADX crosses
        entry=up&(ax>adx_min)&~(up&(ax>adx_min)).shift(1,fill_value=False)
    exit_=~up
    return _pack(df,entry,exit_,tf,atr_mult,1,size_mode,target_vol)

def tsmom(df,tf="4h",lookback_days=30,thr=0.0,atr_mult=3.0,size_mode="vol",target_vol=0.8,**k):
    L=bars(lookback_days,tf)
    m=df.close/df.close.shift(L)-1
    v=I.realized_vol(df.close,(288 if tf=="15m" else 72) if tf in ("15m","1h") else (36 if tf in ("2h","4h") else 20),BPY[tf])*np.sqrt(L/BPY[tf])
    z=m/v
    on=z>thr
    entry=on&~on.shift(1,fill_value=False); exit_=z<0
    return _pack(df,entry,exit_,tf,atr_mult,1,size_mode,target_vol)

def vol_breakout(df,tf="4h",entry_days=10,vol_mult=1.5,atr_mult=2.5,hold_days=0,size_mode="vol",target_vol=0.8,**k):
    n=bars(entry_days,tf)
    hi=df.high.rolling(n).max().shift(1)
    vavg=df.volume.rolling(bars(10,tf)).mean().shift(1)
    rng=(df.close-df.low)/(df.high-df.low).replace(0,np.nan)
    entry=(df.close>hi)&(df.volume>vol_mult*vavg)&(rng>0.6)
    ema_exit=I.ema(df.close,bars(entry_days/2+1,tf))
    exit_=df.close<ema_exit
    return _pack(df,entry,exit_,tf,atr_mult,1,size_mode,target_vol,max_hold=bars(hold_days,tf) if hold_days else 0)

def rsi_pullback(df,tf="4h",trend_days=50,rsi_n=14,rsi_lo=30,rsi_hi=55,atr_mult=3.0,hold_days=7,size_mode="vol",target_vol=0.8,**k):
    r=I.rsi(df.close,rsi_n if tf!="1h" else rsi_n)
    trend=df.close>I.sma(df.close,bars(trend_days,tf))
    entry=trend&(r<rsi_lo)&(r.shift(1)>=rsi_lo)  # fresh oversold cross inside an uptrend
    entry=trend&(r<rsi_lo)
    exit_=r>rsi_hi
    return _pack(df,entry,exit_,tf,atr_mult,0,size_mode,target_vol,max_hold=bars(hold_days,tf))

def bb_revert(df,tf="4h",n_days=5,k_std=2.0,atr_mult=3.0,hold_days=5,trend_filter=0,size_mode="vol",target_vol=0.8,**kw):
    n=bars(n_days,tf); m=I.sma(df.close,n); s=df.close.rolling(n).std()
    lower=m-k_std*s
    entry=df.close<lower
    if trend_filter: entry&=df.close>I.sma(df.close,bars(50,tf))
    exit_=df.close>m
    return _pack(df,entry,exit_,tf,atr_mult,0,size_mode,target_vol,max_hold=bars(hold_days,tf))

def supertrend(df,tf="4h",atr_n_days=3,mult=3.0,size_mode="vol",target_vol=0.8,**k):
    n=bars(atr_n_days,tf); a=I.atr(df,n); hl2=(df.high+df.low)/2
    ub=(hl2+mult*a).values; lb=(hl2-mult*a).values; c=df.close.values
    fub=ub.copy(); flb=lb.copy(); dirn=np.ones(len(c),dtype=bool)
    for i in range(1,len(c)):
        if np.isnan(ub[i]) or np.isnan(fub[i-1]): fub[i]=ub[i]; flb[i]=lb[i]; continue
        fub[i]=ub[i] if (ub[i]<fub[i-1] or c[i-1]>fub[i-1]) else fub[i-1]
        flb[i]=lb[i] if (lb[i]>flb[i-1] or c[i-1]<flb[i-1]) else flb[i-1]
        if dirn[i-1] and c[i]<flb[i]: dirn[i]=False
        elif (not dirn[i-1]) and c[i]>fub[i]: dirn[i]=True
        else: dirn[i]=dirn[i-1]
    up=pd.Series(dirn&~np.isnan(a.values),index=df.index)
    entry=up&~up.shift(1,fill_value=False); exit_=~up
    return _pack(df,entry,exit_,tf,0,0,size_mode,target_vol)

REG={
 "donchian_short":(donchian_short,dict(entry_days=[20,40,60],exit_days=[10],atr_mult=[4.0])),
 "donchian":(donchian,dict(entry_days=[10,20,40,60],exit_days=[5,10,20],atr_mult=[3.0,4.0])),
 "donchian_vol":(donchian,dict(entry_days=[10,20,40],exit_days=[5,10],atr_mult=[3.0],vol_mult=[1.2,1.5,2.0])),
 "ema_trend":(ema_trend,dict(fast_days=[5,10,20],slow_days=[20,40,80],atr_mult=[3.0,4.0],adx_min=[0,20])),
 "tsmom":(tsmom,dict(lookback_days=[10,20,30,60,90],thr=[0.0,0.5],atr_mult=[3.0,4.0])),
 "vol_breakout":(vol_breakout,dict(entry_days=[5,10,20],vol_mult=[1.5,2.0,3.0],atr_mult=[2.5,3.5])),
 "supertrend":(supertrend,dict(atr_n_days=[2,3,5],mult=[2.0,3.0,4.0])),
 "rsi_pullback":(rsi_pullback,dict(trend_days=[30,50,100],rsi_lo=[25,35,45],rsi_hi=[55,65],atr_mult=[3.0],hold_days=[5])),
 "bb_revert":(bb_revert,dict(n_days=[3,7,14],k_std=[1.5,2.0,2.5],atr_mult=[3.0],trend_filter=[0,1])),
}
