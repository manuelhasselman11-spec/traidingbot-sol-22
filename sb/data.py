import pandas as pd, numpy as np, os, glob
DATA=os.path.join(os.path.dirname(__file__),"..","data")
WARMUP_DAYS=30   # skip first 30 days after listing (listing pump not tradable + indicator warm-up)

def load_raw(sym,base="1h"):
    if base=="15m": return pd.read_csv(f"{DATA}/../data15/{sym}_15m.csv",index_col=0,parse_dates=True)
    return pd.read_csv(f"{DATA}/{sym}_1h.csv",index_col=0,parse_dates=True)

def resample(df,tf):
    if tf=="1h": return df
    off=None
    if tf.startswith("1d") and len(tf)>2: off=pd.Timedelta(hours=int(tf[2:])); tf="24h"
    if tf=="1d": tf="24h"
    r=df.resample(tf,label="left",closed="left",**({"offset":off} if off is not None else {})).agg(dict(open="first",high="max",low="min",close="last",volume="sum",quote_volume="sum",trades="sum"))
    return r.dropna(subset=["close"])

CORE="SOL RAY FIDA SRM JUP JTO BONK WIF PYTH W TNSR IO RENDER PNUT ACT BOME ME PENGU TRUMP ORCA LAYER KMNO PUMP MET".split()
def universe():
    allu=sorted(os.path.basename(p)[:-7] for p in glob.glob(f"{DATA}/*_1h.csv") if not os.path.basename(p).startswith("BTC"))
    return [u for u in allu if u in CORE] if os.environ.get("SB_UNIVERSE","all")=="core" else allu

def load_all(tf="1h"):
    out={}
    for s in universe():
        if tf=="15m":
            if not os.path.exists(f"{DATA}/../data15/{s}_15m.csv"): continue
            df=load_raw(s,"15m")
        else: df=resample(load_raw(s),tf)
        out[s]=df
    return out

def first_tradable(df):
    return df.index[0]+pd.Timedelta(days=WARMUP_DAYS)
