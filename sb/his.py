"""Port of the candle-based strategies of Wesley's Claude-bot lab (labStrategies.js) to the honest engine.
Entries are ported 1:1 (indicator definitions as far as visible in the JS); stop = his stop formula (signal skipped if stop > his max %),
take-profit = his first target (full exit instead of 50% + trailing), time stop = his `max` candles. Order flow uses his candle proxy (close-location).
Not portable from candles: volume-profile / real swaps strategies (lvnBrk etc.), pool-age strategies (migSnipe, earlyMom)."""
import numpy as np, pandas as pd
from . import indicators as I

def _ctx(df,tf):
    c,h,l,o,v=[df[k] for k in ("close","high","low","open","volume")]
    P=dict(c=c,h=h,l=l,o=o,v=v)
    P["green"]=c>o
    P["ema9"],P["ema21"],P["ema50"]=I.ema(c,9),I.ema(c,21),I.ema(c,50)
    P["rsi"]=I.rsi(c,14); P["atr"]=I.atr(df,14)
    P["med48"]=v.rolling(48,min_periods=24).median().shift(1)
    P["clv"]=((c-l)/(h-l).replace(0,np.nan)).fillna(0.5)
    n=20; m=c.rolling(n).mean(); s=c.rolling(n).std()
    P["bbmid"]=m; P["bbup"]=m+2*s; bw=(4*s)/m; P["bbw"]=bw
    P["bbwq"]=bw.rolling(100,min_periods=50).quantile(0.15)
    P["kcup"]=I.ema(c,20)+1.5*I.atr(df,20)
    mins={"15m":15,"1h":60,"4h":240,"1d":1440}[tf]; w=max(2,1440//mins)
    tp_=(h+l+c)/3; P["vwap"]=(tp_*v).rolling(w).sum()/v.rolling(w).sum()
    return P

def hiN(P,n): return P["h"].rolling(n).max().shift(1)
def loN(P,n): return P["l"].rolling(n).min().shift(1)

def _pivots(P,k=2):
    h=P["h"].values; l=P["l"].values; n=len(h)
    ph=np.zeros(n,bool); pl=np.zeros(n,bool)
    for j in range(k,n-k):
        if h[j]>h[j-k:j].max() and h[j]>h[j+1:j+k+1].max(): ph[j]=True
        if l[j]<l[j-k:j].min() and l[j]<l[j+1:j+k+1].min(): pl[j]=True
    return ph,pl

def _last_two(flag,px,k=2):
    """for each bar i: last two pivots CONFIRMED by bar i (pivot at j is known at j+k)"""
    n=len(flag); idx=np.where(flag)[0]
    L1=np.full(n,-1); L2=np.full(n,-1)
    pj=0
    for i in range(n):
        while pj<len(idx) and idx[pj]+k<=i: pj+=1
        if pj>=1: L1[i]=idx[pj-1]
        if pj>=2: L2[i]=idx[pj-2]
    return L1,L2

def build_signals(df,tf="1h"):
    """returns dict name -> (entry bool Series, stop_dist Series (fraction), tp Series, max_hold bars, trail_atr_mult or 0)"""
    P=_ctx(df,tf); c,h,l,v=P["c"],P["h"],P["l"],P["v"]; atr=P["atr"]; e=c
    idx=df.index; out={}
    def pack(name,entry,stop_px,maxpct,tpR=None,tpmin=0,maxhold=48):
        dist=((e-stop_px)/e)
        ok=entry&(dist>0)&(dist<=maxpct/100)
        tp=None
        if tpR is not None:
            tpd=np.maximum(tpR*dist,tpmin/100); tp=tpd.where(ok,0.0).fillna(0.0)
        out[name]=dict(entry=ok.fillna(False),stop=dist.where(ok,0.0).fillna(0.0),tp=tp if tp is not None else pd.Series(0.0,index=idx),maxhold=maxhold)
    green=P["green"]; V=v; med=P["med48"]
    # squeeze
    sq=(P["bbw"].shift(1)<=P["bbwq"].shift(1))&(P["bbup"].shift(1)<P["kcup"].shift(1))
    ent=sq&(c>P["bbup"])&green
    pack("squeeze",ent,np.minimum(P["bbmid"],e-1.5*atr),8,None,0,48)
    # emaCross
    ent=(P["ema9"]>P["ema21"])&(P["ema9"].shift(1)<=P["ema21"].shift(1))&(P["ema50"]>P["ema50"].shift(6))&(c>P["ema50"])&(P["rsi"]>=50)&(P["rsi"]<=70)&(V>=1.3*med)
    stop=np.minimum(loN(P,6),e-1.5*atr); dist=(e-stop)/e
    pack("emaCross",ent,stop,8,1.5,2.5,72)
    # rangeBreak
    hi=hiN(P,24); lo=loN(P,24)
    ent=((hi/lo-1)*100<=6)&(c>hi)&green&(V>=2*med)
    pack("rangeBreak",ent,np.maximum(lo,hi-1.5*atr)-0.2*atr,8,None,0,48)
    out["rangeBreak"]["tp"]=pd.Series(np.maximum(((hi-lo)/e).fillna(0),0.025),index=idx).where(out["rangeBreak"]["entry"],0.0)
    # volSpike
    ent=(V>=4*med)&(c>hiN(P,20))&green&((c/c.shift(12)-1)<=0.4)
    pack("volSpike",ent,e-2*atr,12,None,0,72)
    # buyPress (candle proxy)
    bv=(V*P["clv"]).rolling(6).sum(); tv=V.rolling(6).sum(); bv0=bv.shift(6); tv0=tv.shift(6)
    s1=bv/tv; s0=bv0/tv0
    ent=(s1>=0.65)&(s1>s0+0.05)&(tv>1.3*tv0)&(c>P["ema21"])&(P["ema21"]>P["ema50"])
    pack("buyPress",ent,np.minimum(loN(P,6),e-1.5*atr),8,1.5,2.5,48)
    # choch + rsiDiv with confirmed pivots
    ph,pl=_pivots(P); H1,H2=_last_two(ph,h.values); L1,L2=_last_two(pl,l.values)
    hv=h.values; lv=l.values; cv=c.values; rv=P["rsi"].values; n=len(cv)
    # choch uses swings known at i-2 in JS; our confirmed-by-i is already causal
    chent=np.zeros(n,bool); chstop=np.full(n,np.nan); rdent=np.zeros(n,bool); rdstop=np.full(n,np.nan)
    for i in range(3,n):
        a=H1[i]; b=H2[i]
        if a>=0 and b>=0 and hv[a]<hv[b] and cv[i]>hv[a] and cv[i-1]<=hv[a] and cv[i]>P["o"].values[i]:
            chent[i]=True; sl=L1[i]; chstop[i]=(lv[sl] if sl>=0 else np.nan)-0.3*atr.values[i]
        a=L1[i]; b=L2[i]
        if a>=0 and b>=0 and a-b>=5 and i-a<=6 and lv[a]<lv[b] and rv[a]>rv[b] and rv[b]<=35 and cv[i]>P["o"].values[i] and cv[i]>hv[a]:
            rdent[i]=True; rdstop[i]=lv[a]-0.3*atr.values[i]
    pack("choch",pd.Series(chent,index=idx),pd.Series(chstop,index=idx),10,1.5,3,72)
    pack("rsiDiv",pd.Series(rdent,index=idx),pd.Series(rdstop,index=idx),8,1.5,2.5,48)
    # dipBuy
    ent=(P["ema21"]>P["ema50"])&(P["ema50"]>P["ema50"].shift(12))&(c>P["ema50"])&(l<=P["ema21"]*1.003)&(c>P["ema21"])&green&(V.shift(1)<V.shift(2))&(V.shift(2)<V.shift(3))
    pack("dipBuy",ent,np.minimum(l,P["ema50"])-0.5*atr,8,1.5,2.5,72)
    # vwapReclaim
    ent=(c.shift(1)<P["vwap"].shift(1))&(c>P["vwap"])&green&(V>=1.5*med)
    pack("vwapReclaim",ent,np.minimum(l,P["vwap"])-0.5*atr,8,1.5,2.5,72)
    # climax (lottery)
    k=1; clmx=(V.shift(1)>=6*med.shift(1))&(((1-l.shift(1)/h.rolling(12).max().shift(1))*100)>=15)&(P["clv"].shift(1)>=0.4)&green&(c>c.shift(1))
    back=h.rolling(12).max().shift(1)
    ent=clmx; stop=l.shift(1)-0.3*atr
    pack("climax",ent,stop,12,None,0,48)
    out["climax"]["tp"]=(0.5*(back-e)/e).clip(lower=0.01).where(out["climax"]["entry"],0.0).fillna(0.0)
    return out

CORE=["squeeze","emaCross","buyPress","choch","rangeBreak","rsiDiv"]   # (vp:lvnBrk not portable: needs volume profile)
LOTTERY=["climax"]
ALL=["squeeze","emaCross","rangeBreak","volSpike","buyPress","choch","rsiDiv","dipBuy","vwapReclaim","climax"]

def to_sig(df,tf,name,S_):
    s=S_[name]; z=pd.Series(False,index=df.index)
    sd=s["stop"].values
    return dict(entry=s["entry"].values,exit=z.values,size=np.ones(len(df)),stop_dist=sd,tp=s["tp"].values,trail=0,max_hold=s["maxhold"])

def bestof_sig(df,tf,S_,maxhold=48):
    """BEST-OF: signal if any core/lottery pattern fires; first core pattern in list decides stop/tp; size tiers A(>=2 core)=1.0, B(1 core)=0.6, C(lottery only)=0.2"""
    idx=df.index; n=len(df)
    cnt=sum(S_[k]["entry"].astype(int) for k in CORE)
    lot=sum(S_[k]["entry"].astype(int) for k in LOTTERY)>0
    entry=(cnt>=1)|lot
    size=np.where(cnt>=2,1.0,np.where(cnt==1,0.6,0.2))
    stop=pd.Series(0.0,index=idx); tp=pd.Series(0.0,index=idx); mh=pd.Series(maxhold,index=idx)
    for k in LOTTERY+CORE[::-1]:       # first core overrides last
        m=S_[k]["entry"]; stop=stop.where(~m,S_[k]["stop"]); tp=tp.where(~m,S_[k]["tp"]); 
    return dict(entry=entry.values,exit=np.zeros(n,bool),size=size,stop_dist=stop.values,tp=tp.values,trail=0,max_hold=maxhold)
