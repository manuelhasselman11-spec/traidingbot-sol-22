# SolBot Lab — eerlijke Solana-strategieën + paper trading (nooit echte orders)

**Doel:** uitzoeken wat er wél en niet werkt na kosten, op veel tokens en periodes, en dat in één nette Nederlandstalige web-app tonen.
**Geen** wallet, **geen** keys, **geen** echte orders. Live handelen bestaat in deze app niet.

## Snel starten
```bash
cd /workspace/solbot
pip install --break-system-packages -r requirements.txt     # (op een gewone machine zonder --break-system-packages)
python3 -m uvicorn app:app --host 0.0.0.0 --port 8847        # open http://localhost:8847
```
Opnieuw rekenen (optioneel, ±10 min; data staat al in `data/` en `data15/`):
```bash
python3 fetch_data.py && python3 fetch_data2.py              # publieke Binance-candles (spot + USDT-M futures als prijs-proxy)
for tf in 1h 4h 12h 1d; do python3 -m sb.research $tf 1.0; done   # parameter-sweeps (8 strategie-families)
python3 run_research.py                                      # → results/final.json (eindstrategie, robuustheid, walk-forward)
python3 run_h2h.py                                           # → results/h2h.json (Claude-bot vs nieuw vs buy&hold)
python3 tests/test_engine.py                                 # no-lookahead / kosten / gap-stop tests
```

## Structuur
- `sb/engine.py` – numba backtest-engine: signaal op gesloten candle → fill op **volgende open**, kosten per kant, stop vs. low, gap-through-stop vult op open, optionele TP, long/short, funding.
- `sb/strategies.py` – Donchian, EMA-trend, TSMOM, volume-breakout, Supertrend, RSI-pullback, Bollinger-mean-reversion (+ short-variant).
- `sb/his.py` – port van de Claude-bot-patronen (labStrategies.js): squeeze, emaCross, rangeBreak, volSpike, buyPress(proxy), choch, rsiDiv, dipBuy, vwapReclaim, climax + BEST-OF.
- `sb/rotation.py` – cross-sectional momentum-rotatie.
- `sb/final.py` – de bevroren eindstrategie (ensemble). `sb/live.py` – live signalen + paper-account (alleen simulatie).
- `app.py` + `static/` – FastAPI + dark UI (kleuren/typografie uit NEONDESK `DESIGN.md`, eigen canvas→Chart.js lokaal gebundeld, geen CDN).

## Uitkomst (kort, eerlijk)
- Geen enkele strategie heeft een bewezen, robuust voordeel dat in het out-of-sample-deel (2025-04-01 → 2026-10) **geld verdient**. 
- Alles op 15m/1u/4u verliest na kosten; bruto ≈ 0 (bevestigt het eigen onderzoek van de Claude-bot): BEST-OF 1u −0,77% netto per trade (bruto +0,03%).
- Enige familie met een stabiele, plateau-vormige dev-prestatie: **daggelijkse trend-ensemble** (Donchian 20/40/60/100 + volume-breakout, ATR-trailing, vol-sizing, BTC-regime, drawdown-rem). Dev Sharpe 1,53; OOS −1,2% (maxDD −14%) tegen buy&hold −19% (maxDD −73%). Het is **defensief**: spaart kapitaal in een bear-markt, verdient er niets.
- Deflated Sharpe ≈ 0: na correctie voor ~900 geteste configuraties is de in-sample-Sharpe niet bewezen boven toeval.

## Deploy (Railway, jouw GitHub-flow)
De app is Python (FastAPI), jouw bot is Node: zet het als **aparte service** (aparte GitHub-repo of map).
1. Nieuwe repo (bv. `solbot-lab`) → upload deze map **zonder** `data/` en `data15/` (staan in `.gitignore`; alleen nodig om opnieuw te rekenen). `results/final.json` en `results/h2h.json` moeten wél mee.
2. Railway → New Project → Deploy from GitHub → kies de repo. Railway herkent `requirements.txt` + `Procfile` (`uvicorn app:app --host 0.0.0.0 --port $PORT`).
3. Geen environment-variabelen nodig. Paper-staat wordt in `results/paper_state.json` bewaard (op Railway vluchtig tenzij je een Volume koppelt).
4. Wil je het in de bestaande `signaal-terminal` Node-site? Dan kan de pagina als iframe/link; de strategie-logica zit in Python en is niet 1:1 in Node geport.

## Beperkingen
Binance-candles zijn een proxy voor on-chain DEX-prijzen (liquide tokens volgen elkaar nauw; echte DEX-slippage is in de kosten verdisconteerd). Universum = tokens met Binance spot/futures-listing (inclusief delisted PONKE, AI16Z, VINE, SLERF, MYRO, SRM), dus *minder* maar niet nul overlevingsbias; micro-cap pump.fun-tokens zitten er niet in. De out-of-sample periode is één bear-markt (±18 maanden).
**Backtests garanderen geen winst.**

> Dit is de deploy-versie (zonder data/ en onderzoeksscripts). Zie DEPLOY.md om online te zetten.
