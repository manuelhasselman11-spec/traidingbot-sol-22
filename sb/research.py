import itertools, json, sys, time, numpy as np, pandas as pd
from multiprocessing import Pool
from . import portfolio as P, metrics as M, strategies as S

def grid(d):
    keys=list(d); g=[dict(zip(keys,v)) for v in itertools.product(*[d[k] for k in keys])]
    return [p for p in g if not ('fast_days' in p and p['fast_days']>=p['slow_days']) and not ('entry_days' in p and 'exit_days' in p and p['exit_days']>=p['entry_days'])]

def token_table(R,a=None,b=None,min_days=30,tf="4h"):
    out={}
    for tok in R.columns:
        x=M.window(R[tok].dropna(),a,b)
        if len(x)<min_days*P.BPD[tf]: continue
        out[tok]=float((1+x).prod()-1)
    return out

def evaluate(args):
    name,params,tf,cost_scale=args
    R,T=P.run_strategy(name,params,tf,cost_scale)
    return summarize(name,params,tf,R,T)

def summarize(name,params,tf,R,T,r=None):
    r=P.combine(R) if r is None else r
    res=dict(strategy=name,tf=tf,params=json.dumps(params))
    for lab,(a,b) in dict(all=(None,None),dev=(None,P.DEV_END),test=(P.DEV_END,None)).items():
        x=M.window(r,a,b); p=M.perf(x,tf)
        Tt=T if len(T)==0 else T[(T.exit_time>=(a or T.exit_time.min()))&(T.exit_time<(b or (T.exit_time.max()+pd.Timedelta(days=1))))]
        ts=M.trade_stats(Tt)
        for k,v in p.items(): res[f"{lab}_{k}"]=v
        res[f"{lab}_trades"]=ts["n"]; res[f"{lab}_win"]=ts["win"]; res[f"{lab}_pf"]=ts["pf"]
        tt=token_table(R,a,b,tf=tf)
        res[f"{lab}_ntok"]=len(tt)
        res[f"{lab}_breadth"]=float(np.mean([v>0 for v in tt.values()])) if tt else 0
        if tt:
            best=max(tt,key=tt.get); res[f"{lab}_best_tok"]=best
            x2=P.combine(R.drop(columns=[best])) if R.shape[1]>1 else x*0
            x2=M.window(x2,a,b); res[f"{lab}_ex_best_ret"]=M.perf(x2,tf)["ret"]
            tot=sum(max(v,0) for v in tt.values()); res[f"{lab}_top_share"]=tt[best]/tot if tot>0 else 0
    return res

if __name__=="__main__":
    tf=sys.argv[1]; cost=float(sys.argv[2]) if len(sys.argv)>2 else 1.0
    jobs=[(n,p,tf,cost) for n,(fn,g) in S.REG.items() for p in grid(g)]
    print(len(jobs),"combos",flush=True); t=time.time()
    with Pool(8) as pool: res=pool.map(evaluate,jobs,chunksize=2)
    df=pd.DataFrame(res); df.to_csv(f"results/sweep_{tf}_c{cost}.csv",index=False)
    print("done",time.time()-t)
