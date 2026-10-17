"""Cross-sectional momentum rotation (long-only, top-K of listed tokens with absolute-momentum + trend filter).
Decisions at the close of bar t, executed at the open of t+1 (open-to-open returns). Costs charged on turnover."""
import numpy as np, pandas as pd
from . import data, portfolio as P, indicators as I, strategies as S

def run_rotation(tf="1d",k=5,mom_days=(20,60),trend_days=50,rebalance_days=7,cost_scale=1.0,stop_atr=0,vol_weight=True,max_w=0.35):
    D=P.get_data(tf); warm=data.WARMUP_DAYS*P.BPD[tf]
    toks=[t for t,df in D.items() if len(df)>warm+100]
    idx=sorted(set().union(*[D[t].index for t in toks])); idx=pd.DatetimeIndex(idx)
    O=pd.DataFrame({t:D[t].open for t in toks}).reindex(idx); C=pd.DataFrame({t:D[t].close for t in toks}).reindex(idx)
    live=pd.DataFrame({t:(pd.Series(np.arange(len(D[t])),index=D[t].index)>=warm) for t in toks}).reindex(idx).fillna(False).astype(bool)
    score=sum(C.pct_change(S.bars(d,tf)) for d in mom_days)/len(mom_days)
    trend=C>C.rolling(S.bars(trend_days,tf)).mean()
    vol=np.log(C).diff().rolling(S.bars(20,tf)).std()
    elig=live&trend&(score>0)&score.notna()
    rank=score.where(elig).rank(axis=1,ascending=False)
    pick=(rank<=k)
    if vol_weight:
        w=(1/vol).where(pick); w=w.div(w.sum(axis=1),axis=0)
    else:
        w=pick.astype(float); w=w.div(w.sum(axis=1),axis=0)
    w=w.clip(upper=max_w).fillna(0)
    # exposure is scaled down when fewer than k names pass the filter (rest in cash)
    n_pick=pick.sum(axis=1); expo=(n_pick/k).clip(upper=1.0)
    w=w.div(w.sum(axis=1).replace(0,np.nan),axis=0).fillna(0).mul(expo,axis=0)
    # rebalance only every `rebalance_days`
    step=max(1,int(rebalance_days*24/S.HRS[tf]))
    mask=np.zeros(len(idx),bool); mask[::step]=True
    wr=w.copy(); wr[~mask]=np.nan; wr=wr.ffill().fillna(0)
    # tokens falling out of eligibility between rebalances are NOT sold (simple weekly rebalance) except a hard exit if close < trend MA
    hard=~(C>C.rolling(S.bars(trend_days,tf)).mean())
    wr=wr.where(~hard,0.0)
    wr=wr.where(live,0.0)
    W=wr.shift(0)          # weights decided at close t -> held over open[t+1]->open[t+2]
    oo=O.shift(-2)/O.shift(-1)-1   # return earned by weights set at close t
    oo=oo.fillna(0)
    gross=(W*oo).sum(axis=1)
    cs=pd.Series({t:P.cost_side(t,cost_scale) for t in toks})
    turnover=W.diff().abs().fillna(W.abs()).mul(cs,axis=1).sum(axis=1)
    net=gross-turnover
    # align: return earned at time of open[t+2]; shift so index = bar in which return is earned
    net=net.shift(2).fillna(0.0)
    # count of listed tokens only for start
    start=idx[live.any(axis=1).values.argmax()] if live.any().any() else idx[0]
    W2=W.shift(2).fillna(0)
    # per-token sleeve contribution (for per-token breakdown)
    contrib=(W*oo).sub(W.diff().abs().fillna(W.abs()).mul(cs,axis=1)).shift(2).fillna(0)
    contrib=contrib.where(live)
    # trade episodes
    trades=[]
    for t in toks:
        w_=W2[t].values>0; o=O[t].values; i=0; n=len(w_)
        while i<n:
            if w_[i]:
                j=i
                while j<n and w_[j]: j+=1
                if i>0 and j<n and not np.isnan(o[i]) and not np.isnan(o[min(j,n-1)]):
                    trades.append(dict(token=t,entry_time=idx[i],exit_time=idx[j],entry_px=o[i],exit_px=o[j],ret=o[j]/o[i]-1-2*P.cost_side(t,cost_scale),reason="rotation"))
                i=j
            else: i+=1
    return net.loc[start:],contrib.loc[start:],pd.DataFrame(trades)
