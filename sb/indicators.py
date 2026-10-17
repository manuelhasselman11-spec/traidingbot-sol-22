import numpy as np, pandas as pd
def sma(x,n): return x.rolling(n,min_periods=n).mean()
def ema(x,n): return x.ewm(span=n,adjust=False,min_periods=n).mean()
def atr(df,n=14):
    pc=df.close.shift(1)
    tr=pd.concat([df.high-df.low,(df.high-pc).abs(),(df.low-pc).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
def rsi(x,n=14):
    d=x.diff(); up=d.clip(lower=0).ewm(alpha=1/n,adjust=False,min_periods=n).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    return 100-100/(1+up/dn.replace(0,np.nan))
def adx(df,n=14):
    up=df.high.diff(); dn=-df.low.diff()
    pdm=np.where((up>dn)&(up>0),up,0.0); mdm=np.where((dn>up)&(dn>0),dn,0.0)
    a=atr(df,n)
    pdi=100*pd.Series(pdm,index=df.index).ewm(alpha=1/n,adjust=False,min_periods=n).mean()/a
    mdi=100*pd.Series(mdm,index=df.index).ewm(alpha=1/n,adjust=False,min_periods=n).mean()/a
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    return dx.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
def realized_vol(close,n=72,bars_per_year=8760):
    r=np.log(close).diff()
    return r.ewm(span=n,min_periods=n//2).std()*np.sqrt(bars_per_year)
