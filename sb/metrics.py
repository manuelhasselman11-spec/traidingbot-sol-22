import numpy as np, pandas as pd
from scipy import stats

def daily(r):
    r=r.copy(); r.index=pd.DatetimeIndex(r.index)
    return (1+r).groupby(r.index.floor("D")).prod()-1

def equity(r): return (1+r).cumprod()

def perf(r,tf="4h"):
    """r: bar returns of a portfolio. Sharpe from daily returns (crypto trades 365d)."""
    if len(r)==0 or r.abs().sum()==0: return dict(ret=0,cagr=0,sharpe=0,sortino=0,maxdd=0,calmar=0,vol=0,days=0)
    d=daily(r); eq=(1+d).cumprod(); n=len(d)
    tot=eq.iloc[-1]-1; yrs=max(n/365,1/365)
    cagr=(eq.iloc[-1])**(1/yrs)-1 if eq.iloc[-1]>0 else -1
    sd=d.std(); sh=d.mean()/sd*np.sqrt(365) if sd>0 else 0
    dn=d[d<0].std(); so=d.mean()/dn*np.sqrt(365) if dn and dn>0 else 0
    dd=(eq/eq.cummax()-1).min()
    return dict(ret=float(tot),cagr=float(cagr),sharpe=float(sh),sortino=float(so),maxdd=float(dd),calmar=float(cagr/abs(dd)) if dd<0 else 0,vol=float(sd*np.sqrt(365)),days=int(n))

def trade_stats(T):
    if T is None or len(T)==0: return dict(n=0,win=0,pf=0,avg=0,med=0,avg_win=0,avg_loss=0,hold_h=0)
    x=T.ret; w=x[x>0]; l=x[x<=0]
    pf=w.sum()/abs(l.sum()) if l.sum()!=0 else np.inf
    hold=(T.exit_time-T.entry_time).dt.total_seconds().mean()/3600
    return dict(n=int(len(x)),win=float((x>0).mean()),pf=float(min(pf,99)),avg=float(x.mean()),med=float(x.median()),avg_win=float(w.mean()) if len(w) else 0,avg_loss=float(l.mean()) if len(l) else 0,hold_h=float(hold))

def bootstrap_sharpe(r,n=2000,block=10,seed=0):
    d=daily(r).values
    if len(d)<30 or d.std()==0: return (0,0,1.0)
    rng=np.random.default_rng(seed); N=len(d); nb=int(np.ceil(N/block)); shs=[]
    for _ in range(n):
        st=rng.integers(0,N-block+1,nb); x=np.concatenate([d[s:s+block] for s in st])[:N]
        shs.append(x.mean()/x.std()*np.sqrt(365) if x.std()>0 else 0)
    shs=np.array(shs)
    return (float(np.percentile(shs,5)),float(np.percentile(shs,95)),float((shs<=0).mean()))

def deflated_sharpe(r,n_trials,sr_var):
    """Bailey & Lopez de Prado deflated Sharpe ratio probability (daily Sharpe units)."""
    d=daily(r).values; T=len(d)
    if T<30 or d.std()==0: return 0.0
    sr=d.mean()/d.std(); sk=stats.skew(d); ku=stats.kurtosis(d,fisher=False)
    emc=0.5772156649
    e_max=np.sqrt(sr_var)*((1-emc)*stats.norm.ppf(1-1/n_trials)+emc*stats.norm.ppf(1-1/(n_trials*np.e)))
    denom=np.sqrt(max(1e-12,1-sk*sr+(ku-1)/4*sr**2))
    return float(stats.norm.cdf((sr-e_max)*np.sqrt(T-1)/denom))

def window(r,a=None,b=None):
    x=r
    if a is not None: x=x[x.index>=a]
    if b is not None: x=x[x.index<b]
    return x
