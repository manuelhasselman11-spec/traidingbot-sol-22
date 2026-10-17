"""Live signals + paper trading (simulation only: no wallet, no keys, no orders).
Uses Binance public klines/tickers. The model portfolio is re-run on fresh daily candles; the paper account tracks it from a chosen start date."""
import json, os, time, threading, requests, numpy as np, pandas as pd
from . import portfolio as P, final as F, strategies as S, engine, metrics as M, indicators as I

# Binance blokkeert soms servers in de VS (HTTP 451): dan valt hij terug op de publieke data-api (alleen marktdata).
BASES=[b for b in [os.environ.get("BINANCE_BASE"),"https://api.binance.com/api/v3","https://data-api.binance.vision/api/v3"] if b]
BASE=BASES[0]
# DATA_DIR = map voor de paper-state (op Railway: koppel een Volume en zet DATA_DIR=/data). Standaard: ./results
STATE=os.path.join(os.environ.get("DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","results"),"paper_state.json")
def _get(path,params=None):
    last=None
    for b in BASES:
        try:
            r=requests.get(f"{b}{path}",params=params,timeout=15)
            if r.status_code==200: return r.json()
            last=f"HTTP {r.status_code}"
        except Exception as e: last=str(e)
    raise RuntimeError(f"Binance niet bereikbaar ({last})")
_lock=threading.Lock(); _cache={}

FUT="https://fapi.binance.com/fapi/v1"
def _klines(sym,limit=1000):
    try: r=_get("/klines",dict(symbol=sym+"USDT",interval="1d",limit=limit))
    except Exception: r=None
    if not isinstance(r,list):   # not on spot -> USDT-M futures price (same proxy as the backtest)
        r=requests.get(f"{FUT}/klines",params=dict(symbol=sym+"USDT",interval="1d",limit=limit),timeout=15).json()
    df=pd.DataFrame(r,columns="t o h l c v ct qv n tb tq i".split())[["t","o","h","l","c","v","qv","n"]].astype(float)
    df["t"]=pd.to_datetime(df.t,unit="ms",utc=True)
    df=df.rename(columns=dict(o="open",h="high",l="low",c="close",v="volume",qv="quote_volume",n="trades")).set_index("t")
    return df

def prices(tokens):
    r=_get("/ticker/price")
    d={x["symbol"]:float(x["price"]) for x in r}
    try:
        for x in requests.get(f"{FUT}/ticker/price",timeout=15).json(): d.setdefault(x["symbol"],float(x["price"]))
    except Exception: pass
    return {t:d.get(t+"USDT") for t in tokens}

def fetch_all(ttl=300):
    if "D" in _cache and time.time()-_cache["ts"]<ttl: return _cache["D"],_cache["btc"]
    toks=[t for t in json.load(open(os.path.join(os.path.dirname(__file__),"..","results","final.json")))["meta"]["universe"] if t!="SRM"]  # SRM delisted (kept in backtest only)
    from concurrent.futures import ThreadPoolExecutor
    def one(t):
        try:
            k=_klines(t)
            if len(k) and k.index[-1]>=pd.Timestamp.utcnow().floor("D")-pd.Timedelta(days=2): return t,k   # skip delisted/settled tokens
        except Exception: pass
        return t,None
    with ThreadPoolExecutor(8) as ex: D={t:k for t,k in ex.map(one,toks) if k is not None}
    btc=_klines("BTC")
    # last candle is the still-forming day: split off
    _cache.update(ts=time.time(),D=D,btc=btc)
    return D,btc

def _closed(df):
    now=pd.Timestamp.utcnow().floor("D")
    return df[df.index<now]

def model_state():
    """Run the frozen model on fresh data. Returns per-token live state, overlay status and model returns."""
    D,btc=fetch_all()
    Dc={t:_closed(df) for t,df in D.items()}; btcc=_closed(btc)
    live_px=prices(list(D)+["BTC"])
    old=P._CACHE.get("1d"); P._CACHE["1d"]=Dc
    try:
        o=F.build("1d",ref_close=btcc.close)
    finally:
        if old is not None: P._CACHE["1d"]=old
        else: P._CACHE.pop("1d",None)
    ma=btcc.close.rolling(F.OVERLAY["regime_ma_days"]).mean()
    regime_on=bool(btcc.close.iloc[-1]>ma.iloc[-1])
    rows=[]; warm=30
    listed=[t for t,df in Dc.items() if len(df)>warm+10]
    nl=len(listed)
    for tok in listed:
        df=Dc[tok]; px=live_px.get(tok); last=float(df.close.iloc[-1]); comps=[]
        for n,p in F.COMPONENTS:
            fn=S.REG[n][0]; sig=fn(df,tf="1d",**p)
            r,t=engine.run_token(df,sig,P.cost_side(tok),P.STOP_SLIP,warm)
            inpos=len(t)>0 and t.reason.iloc[-1]=="open" and t.exit_time.iloc[-1]==df.index[-1]
            entry_sig=bool(sig["entry"][-1]); exit_sig=bool(sig["exit"][-1])
            c=dict(strategy=F.label(n,p),in_position=bool(inpos),entry_signal=entry_sig and not inpos,exit_signal=exit_sig and inpos)
            if inpos:
                et=t.entry_time.iloc[-1]; ei=df.index.get_loc(et)
                c.update(entry_time=str(et.date()),entry_px=float(t.entry_px.iloc[-1]),size=float(sig["size"][max(ei-1,0)]))
                hw=float(df.high.iloc[ei:].max()); sd=float(sig["stop_dist"][-1]); c["stop"]=hw*(1-sd)
                c["unreal"]=(px or last)/c["entry_px"]-1
            if n=="donchian":
                c["next_breakout"]=float(df.high.iloc[-p["entry_days"]:].max()); c["exit_level"]=float(df.low.iloc[-p["exit_days"]:].min())
            else:
                c["next_breakout"]=float(df.high.iloc[-p["entry_days"]:].max())
            comps.append(c)
        ncomp=len(comps); w=sum((c["size"] if c["in_position"] else 0) for c in comps)/ncomp/nl
        n_in=sum(c["in_position"] for c in comps)
        if n_in>0: status="LONG"
        elif any(c["entry_signal"] for c in comps): status="BUY-SIGNAL"
        else: status="FLAT"
        rows.append(dict(token=tok,price=px,last_close=last,chg_24h=(px/float(df.close.iloc[-1])-1) if px else None,status=status,components_long=n_in,components=ncomp,
                         target_weight=w*(1 if regime_on else 0),raw_weight=w,components_detail=comps,vol_ann=float(I.realized_vol(df.close,20,365).iloc[-1])))
    return dict(rows=rows,regime=dict(on=regime_on,btc=live_px.get("BTC"),btc_ma100=float(ma.iloc[-1]),rule="BTC > 100-daags gemiddelde → risico aan; anders alles cash"),
                last_closed=str(max(df.index[-1] for df in Dc.values()).date()),model_r=o["r"],n_listed=nl,Rtok=o["Rtok"],T=o["T"])

# ---------------- paper account ----------------
def load_state():
    if os.path.exists(STATE): return json.load(open(STATE))
    return None
def start_paper(equity=10000.0,start=None):
    st=dict(start=(start or pd.Timestamp.utcnow().floor("D").strftime("%Y-%m-%d")),equity0=float(equity),created=pd.Timestamp.utcnow().isoformat())
    os.makedirs(os.path.dirname(STATE),exist_ok=True); json.dump(st,open(STATE,"w")); return st
def reset_paper():
    if os.path.exists(STATE): os.remove(STATE)

def paper_view():
    st=load_state()
    if not st: return dict(active=False)
    ms=model_state(); r=ms["model_r"]; s0=pd.Timestamp(st["start"],tz="UTC")
    rr=r[r.index>=s0]
    eq=st["equity0"]*(1+rr).cumprod() if len(rr) else pd.Series(dtype=float)
    cur=float(eq.iloc[-1]) if len(eq) else st["equity0"]
    # intraday mark-to-market of open positions at live prices
    intraday=0.0
    if ms["regime"]["on"]:
        for row in ms["rows"]:
            for c in row["components_detail"]:
                if c["in_position"] and row["price"]:
                    intraday+=c["size"]*(row["price"]/row["last_close"]-1)/row["components"]/ms["n_listed"]
    live_eq=cur*(1+intraday)
    T=ms["T"]; T=T[T.exit_time>=s0].sort_values("exit_time",ascending=False)
    closed=[dict(token=x.token,strategy=x.strategy,entry=str(x.entry_time.date()),exit=str(x.exit_time.date()),ret=float(x.ret),reason=x.reason) for x in T.itertuples() if x.reason!="open"]
    openp=[dict(token=row["token"],**c) for row in ms["rows"] for c in row["components_detail"] if c["in_position"]]
    return dict(active=True,start=st["start"],equity0=st["equity0"],equity_closed=cur,equity_live=live_eq,ret_live=live_eq/st["equity0"]-1,
                curve=dict(t=[x.strftime("%Y-%m-%d") for x in eq.index],eq=[round(float(v),2) for v in eq.values]),
                open_positions=openp,closed_trades=closed[:100],regime=ms["regime"],last_closed=ms["last_closed"],
                note="Simulatie: volgt het model vanaf de startdatum met virtueel kapitaal. Er worden nooit echte orders geplaatst.")
