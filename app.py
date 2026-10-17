"""SolBot Lab — eerlijke Solana-strategie-lab + paper trading (GEEN echte orders, GEEN wallet/keys).
Start:  uvicorn app:app --host 0.0.0.0 --port $PORT
Env (optioneel): DATA_DIR (map voor paper_state.json, bv. Railway Volume op /data), BINANCE_BASE
"""
import json, os, time, threading
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT=os.path.dirname(os.path.abspath(__file__))
app=FastAPI(title="SolBot Lab",docs_url="/api/docs")
_cache={}
def load(name):
    p=os.path.join(ROOT,"results",name)
    if not os.path.exists(p): raise HTTPException(404,f"{name} ontbreekt — draai eerst run_research.py / run_h2h.py")
    m=os.path.getmtime(p)
    if name not in _cache or _cache[name][0]!=m: _cache[name]=(m,json.load(open(p)))
    return _cache[name][1]

@app.get("/api/health")
def health():
    return dict(ok=True,paper_only=True,live_trading=False,time=time.strftime("%Y-%m-%d %H:%M:%S UTC",time.gmtime()))
@app.get("/api/meta")
def meta():
    d=load("final.json"); return dict(meta=d["meta"],n_trials=d["n_trials"],benchmarks=d["benchmarks"])
@app.get("/api/overview")
def overview():
    d=load("final.json"); f=d["final"]
    return dict(meta=d["meta"],final=dict(metrics=f["metrics"],metrics_no_overlay=f["metrics_no_overlay"],trade_stats=f["trade_stats"],regime_summary=f["regime_summary"],curve=f["curve"],
        components=f["components"],overlay=f["overlay"],sizing=f["sizing"],by_period=f["by_period"]),benchmarks=d["benchmarks"],curves=dict(bh_ew=d["family_curves"]["BH_EW"],bh_sol=d["family_curves"]["BH_SOL"]),n_trials=d["n_trials"])
@app.get("/api/families")
def families():
    d=load("final.json"); return dict(families=d["families"],curves=d["family_curves"],timeframe_sweep=d["timeframe_sweep"],benchmarks=d["benchmarks"])
@app.get("/api/per_token")
def per_token(): return load("final.json")["final"]["per_token"]
@app.get("/api/trades")
def trades(token:str=None,strategy:str=None,limit:int=Query(200,le=2000),offset:int=0):
    t=load("final.json")["final"]["trades"]
    if token: t=[x for x in t if x["token"]==token]
    if strategy: t=[x for x in t if strategy in x["strategy"]]
    return dict(total=len(t),rows=t[offset:offset+limit])
@app.get("/api/robustness")
def robustness(): return load("final.json")["robustness"]
@app.get("/api/h2h")
def h2h(): return load("h2h.json")
@app.get("/api/params")
def params():
    d=load("final.json"); f=d["final"]
    return dict(components=f["components"],overlay=f["overlay"],sizing=f["sizing"],meta=d["meta"])

# ---- live (simulation only) ----
_lv={"ts":0,"data":None}; _lock=threading.Lock()
@app.get("/api/live/signals")
def live_signals(refresh:bool=False):
    from sb import live
    with _lock:
        if refresh or time.time()-_lv["ts"]>120 or _lv["data"] is None:
            try:
                ms=live.model_state()
                rows=[{k:v for k,v in r.items()} for r in ms["rows"]]
                _lv.update(ts=time.time(),data=dict(rows=rows,regime=ms["regime"],last_closed=ms["last_closed"],n_listed=ms["n_listed"],fetched=time.strftime("%H:%M:%S UTC",time.gmtime())))
            except Exception as e:
                raise HTTPException(502,f"Live data niet beschikbaar: {e}")
    return _lv["data"]
@app.get("/api/paper")
def paper():
    from sb import live
    try: return live.paper_view()
    except Exception as e: raise HTTPException(502,f"Live data niet beschikbaar: {e}")
@app.post("/api/paper/start")
def paper_start(equity:float=10000.0,start:str=None):
    from sb import live
    try: return live.start_paper(equity,start)
    except OSError as e: raise HTTPException(500,f"Kan paper-state niet opslaan ({e}). Controleer DATA_DIR / Volume.")
@app.post("/api/paper/reset")
def paper_reset():
    from sb import live
    try: live.reset_paper()
    except OSError as e: raise HTTPException(500,f"Kan paper-state niet wissen ({e}).")
    return dict(ok=True)

app.mount("/static",StaticFiles(directory=os.path.join(ROOT,"static")),name="static")
@app.get("/")
def index(): return FileResponse(os.path.join(ROOT,"static","index.html"),headers={"Cache-Control":"no-store"})
