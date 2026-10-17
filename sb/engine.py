"""Honest long-only backtest engine.
 - signals are computed on CLOSED bars; orders execute at the NEXT bar's open (no look-ahead)
 - fee+slippage charged on every entry and exit (cost_side), stops get extra slippage and gap-through-stop fills at the open
 - trailing / initial ATR stop is checked against bar LOW, filled at min(open, stop)
 - one sleeve per token; the portfolio is the equal-weight average of sleeves that are listed at that time
"""
import numpy as np, pandas as pd, numba as nb
from . import indicators as ind

@nb.njit(cache=True)
def sim(open_,high,low,close,entry,exit_,size_arr,stop_dist,tp_arr,trail,max_hold,cost_side,stop_slip,start,d,funding):
    """d=+1 long, d=-1 short (perp). funding = cost per bar on notional while in a position (conservative: always paid)."""
    n=len(close)
    ret=np.zeros(n)
    pos=0; ref=0.0; size=0.0; stop=0.0; hw=0.0; bars=0
    pend_e=False; pend_x=False; pend_size=0.0; pend_stop=0.0; pend_tp=0.0; tp=0.0
    tr_e=np.zeros(n,np.int64); tr_x=np.zeros(n,np.int64); tr_ep=np.zeros(n); tr_xp=np.zeros(n); tr_r=np.zeros(n); tr_why=np.zeros(n,np.int64)
    nt=0; cum=0.0; ep_raw=0.0; ei=0
    for i in range(start,n):
        if pend_e and pos==0:
            pos=1; size=pend_size; ref=open_[i]; ep_raw=open_[i]; ei=i; hw=open_[i]; bars=0; cum=0.0
            stop=ref*(1.0-d*pend_stop) if pend_stop>0 else 0.0
            tp=ref*(1.0+d*pend_tp) if pend_tp>0 else 0.0
            ret[i]-=size*cost_side; cum-=size*cost_side
        elif pend_x and pos==1:
            r=d*size*(open_[i]/ref-1.0)-size*cost_side
            ret[i]+=r; cum+=r
            tr_e[nt]=ei; tr_x[nt]=i; tr_ep[nt]=ep_raw; tr_xp[nt]=open_[i]; tr_r[nt]=cum/size; tr_why[nt]=0; nt+=1
            pos=0
        pend_e=False; pend_x=False
        if pos==1:
            bars+=1
            ret[i]-=size*funding; cum-=size*funding
            hit=False
            if stop>0:
                if d==1 and low[i]<=stop: hit=True
                if d==-1 and high[i]>=stop: hit=True
            if hit:
                px=min(open_[i],stop) if d==1 else max(open_[i],stop)
                r=d*size*(px/ref-1.0)-size*(cost_side+stop_slip)
                ret[i]+=r; cum+=r
                tr_e[nt]=ei; tr_x[nt]=i; tr_ep[nt]=ep_raw; tr_xp[nt]=px; tr_r[nt]=cum/size; tr_why[nt]=1; nt+=1
                pos=0
            elif tp>0 and ((d==1 and high[i]>=tp) or (d==-1 and low[i]<=tp)):
                px=max(open_[i],tp) if d==1 else min(open_[i],tp)
                r=d*size*(px/ref-1.0)-size*cost_side
                ret[i]+=r; cum+=r
                tr_e[nt]=ei; tr_x[nt]=i; tr_ep[nt]=ep_raw; tr_xp[nt]=px; tr_r[nt]=cum/size; tr_why[nt]=3; nt+=1
                pos=0
            else:
                r=d*size*(close[i]/ref-1.0)
                ret[i]+=r; cum+=r
                ref=close[i]
                if d==1:
                    if high[i]>hw: hw=high[i]
                else:
                    if low[i]<hw: hw=low[i]
        if pos==1:
            if trail>0 and stop_dist[i]>0:
                if d==1:
                    ns=hw*(1.0-stop_dist[i])
                    if ns>stop: stop=ns
                else:
                    ns=hw*(1.0+stop_dist[i])
                    if stop==0.0 or ns<stop: stop=ns
            if exit_[i] or (max_hold>0 and bars>=max_hold):
                pend_x=True
        elif entry[i]:
            pend_e=True; pend_size=size_arr[i]; pend_stop=stop_dist[i] if stop_dist[i]>0 else 0.0; pend_tp=tp_arr[i]
    if pos==1:
        tr_e[nt]=ei; tr_x[nt]=n-1; tr_ep[nt]=ep_raw; tr_xp[nt]=close[n-1]; tr_r[nt]=cum/size; tr_why[nt]=2; nt+=1
    return ret,tr_e[:nt],tr_x[:nt],tr_ep[:nt],tr_xp[:nt],tr_r[:nt],tr_why[:nt]

def run_token(df,sig,cost_side=0.0025,stop_slip=0.003,warm_bars=720,direction=1,funding=0.0):
    """sig: dict(entry,exit,size,stop_dist,trail,max_hold) - arrays aligned to df"""
    o,h,l,c=[df[k].values.astype(np.float64) for k in ("open","high","low","close")]
    ret,te,tx,tep,txp,tr,why=sim(o,h,l,c,sig["entry"].astype(np.bool_),sig["exit"].astype(np.bool_),
        sig["size"].astype(np.float64),sig["stop_dist"].astype(np.float64),(sig["tp"].astype(np.float64) if "tp" in sig else np.zeros(len(c))),float(sig.get("trail",0.0)),int(sig.get("max_hold",0)),
        cost_side,stop_slip,warm_bars,int(direction),float(funding))
    idx=df.index
    r=pd.Series(ret,index=idx)
    trades=pd.DataFrame(dict(entry_time=idx[te],exit_time=idx[tx],entry_px=tep,exit_px=txp,ret=tr,reason=np.array(["signal","stop","open","tp"])[why]))
    return r,trades
