'use strict';
const $=(s,e=document)=>e.querySelector(s);
const API=p=>fetch('/api/'+p).then(r=>{if(!r.ok)return r.json().then(j=>{throw new Error(j.detail||r.status)});return r.json()});
const pct=(x,d=1)=>x==null?'–':(x*100).toFixed(d).replace('.',',')+'%';
const num=(x,d=2)=>x==null?'–':Number(x).toFixed(d).replace('.',',');
const cls=x=>x==null?'':(x>0?'buy':(x<0?'sell':''));
const colr=(x,d=1)=>`<span class="${cls(x)}">${pct(x,d)}</span>`;
const usd=x=>x==null?'–':(x>=1?x.toFixed(2):x.toPrecision(3));
const TABS=[['overzicht','Overzicht'],['h2h','Kop-aan-kop'],['strategie','Strategieën'],['token','Per token'],['trades','Trades'],['robuust','Robuustheid'],['params','Parameters'],['live','Live & Paper']];
const COL={new:'#2fe38a',raw:'#4dc3ff',ew:'#ff4d6d',sol:'#a78bfa',bot:'#ffd84d',gray:'#8a93c2',pink:'#ff7ad9',orange:'#ff9f43'};
let charts=[];
function killCharts(){charts.forEach(c=>c.destroy());charts=[]}
function chart(el,cfg){const c=new Chart(el,cfg);charts.push(c);return c}
Chart.defaults.color='#8a93c2';Chart.defaults.borderColor='#262d57';Chart.defaults.font.family='ui-monospace,Consolas,monospace';Chart.defaults.font.size=11;
function lineCfg(labels,sets,{log=false,fmt=v=>v,ytitle=''}={}){
  return {type:'line',data:{labels,datasets:sets.map(s=>({label:s.label,data:s.data,borderColor:s.color,backgroundColor:s.color+'33',borderWidth:s.w||1.5,pointRadius:0,fill:!!s.fill,tension:0,borderDash:s.dash||[]}))},
    options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},
      plugins:{legend:{labels:{boxWidth:10}},tooltip:{callbacks:{label:c=>c.dataset.label+': '+fmt(c.parsed.y)}}},
      scales:{x:{ticks:{maxTicksLimit:10},grid:{display:false}},y:{type:log?'logarithmic':'linear',ticks:{callback:v=>fmt(v)},title:{display:!!ytitle,text:ytitle}}}}};
}
function rebase(c,from){ // c={t,eq}; returns {t,eq,dd} rebased at 'from'
  let i=c.t.findIndex(x=>x>=from); if(i<0)i=0; const base=c.eq[i-1>=0?i-1:0]||c.eq[0]; // value before first OOS day
  const t=c.t.slice(i),eq=c.eq.slice(i).map(v=>v/base);let pk=0;const dd=eq.map(v=>{pk=Math.max(pk,v);return v/pk-1});return {t,eq,dd}
}
function kpi(l,v,s,c=''){return `<div class="kpi"><div class="l">${l}</div><div class="v ${c}">${v}</div><div class="s">${s||''}</div></div>`}
function tbl(head,rows,{hl=null}={}){return `<div class="tablewrap"><table><thead><tr>${head.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr class="${hl&&hl(r)?'hl':''}">${r.cells.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`}
const R=(cells,meta={})=>Object.assign({cells},meta);

/* ---------- nav ---------- */
let cur='overzicht';
function renderNav(){ $('#nav').innerHTML=TABS.map(([k,l])=>`<button data-k="${k}" class="${k===cur?'on':''}">${l}</button>`).join('');
  $('#nav').querySelectorAll('button').forEach(b=>b.onclick=()=>{cur=b.dataset.k;location.hash=cur;go()}) }
async function go(){renderNav();killCharts();const m=$('#main');m.innerHTML='<div class="panel muted">Laden…</div>';
  try{await VIEWS[cur](m)}catch(e){m.innerHTML=`<div class="panel verdict bad"><b>Fout:</b> ${e.message}</div>`}}
setInterval(()=>$('#clock').textContent=new Date().toISOString().slice(0,19).replace('T',' ')+' UTC',1000);

/* ---------- Overzicht ---------- */
async function vOverzicht(m){
  const d=await API('overview'), f=d.final, mt=f.metrics, bh=d.benchmarks, meta=d.meta;
  const oos=mt.test, all=mt.all, dev=mt.dev, bt=bh.bh_ew.test, bs=bh.bh_sol.test;
  const better=oos.ret>bt.ret;
  const absProfit=oos.ret>0&&oos.sharpe>0.3;
  const vcls=absProfit?'good':'';
  m.innerHTML=`
  <div class="panel verdict ${vcls}"><h2>Eerlijk oordeel</h2>
   <p><b>Er is geen bewezen, robuust voordeel dat geld verdient in het out-of-sample-deel.</b> De beste overlevende aanpak is een <b>defensieve daggelijkse trend-ensemble</b> (Donchian + volume-breakout, long-only, BTC-regime-filter, drawdown-rem).</p>
   <ul class="clean">
    <li>In-sample (dev, t/m ${meta.dev_period.split('→')[1].trim()}): Sharpe <b>${num(dev.sharpe)}</b>, rendement ${colr(dev.ret,0)}, max drawdown ${colr(dev.maxdd,0)} — maar dit deel bevat de bull-markten van SOL/RAY/FIDA en weinig tokens.</li>
    <li>Out-of-sample (${meta.test_period.split('(')[0].trim()}): ensemble <b>${colr(oos.ret)}</b> (Sharpe ${num(oos.sharpe)}, maxDD ${colr(oos.maxdd,0)}) tegen buy&hold gelijk gewogen <b>${colr(bt.ret)}</b> (maxDD ${colr(bt.maxdd,0)}) en buy&hold SOL ${colr(bs.ret)}.</li>
    <li>Dus: ${better?'het ensemble verliest veel minder dan buy&hold (kapitaalbehoud)':'het ensemble is niet beter dan buy&hold'}, maar verdient <b>geen</b> aantoonbaar geld in de huidige bear-periode. Statistisch: bootstrap-Sharpe OOS niet te onderscheiden van 0.</li>
    <li>Alle kortere-termijn strategieën (1u/4u, ook jouw Claude-bot-patronen) verliezen na kosten. Zie tab <i>Kop-aan-kop</i> en <i>Strategieën</i>.</li>
   </ul></div>
  <div class="grid g4">
   ${kpi('Sharpe (alles)',num(all.sharpe),'dev '+num(dev.sharpe)+' · OOS '+num(oos.sharpe))}
   ${kpi('Rendement OOS',pct(oos.ret),'B&H gelijk gewogen '+pct(bt.ret),cls(oos.ret))}
   ${kpi('Max drawdown OOS',pct(oos.maxdd,0),'B&H '+pct(bt.maxdd,0),'')}
   ${kpi('Trades / win% / PF',f.trade_stats.all.n+' / '+pct(f.trade_stats.all.win,0)+' / '+num(f.trade_stats.all.pf),'OOS: '+f.trade_stats.test.n+' trades · PF '+num(f.trade_stats.test.pf))}
  </div>
  <div class="panel"><div class="row"><h2 style="margin:0">Equity-curve (log-schaal, start = 1)</h2>
    <select id="rng"><option value="all">Alles (2020–nu)</option><option value="oos">Alleen out-of-sample</option></select></div>
    <div class="chart"><canvas id="c1"></canvas></div></div>
  <div class="panel"><h2>Drawdown</h2><div class="chart sm"><canvas id="c2"></canvas></div></div>
  <div class="panel"><h2>Per halfjaar: ensemble vs buy&hold (regimes)</h2>
   ${tbl(['Periode','Ensemble','B&H gelijk gewogen','B&H SOL','Actieve tokens','Max DD','Deel'],f.by_period.map(p=>R([p.period,colr(p.strat),colr(p.bh_ew),colr(p.bh_sol),p.active_tokens,colr(p.maxdd,0),p.oos?'<span class="tag df">OOS</span>':'dev'])))}
   <p class="small muted">Het ensemble was positief in ${f.regime_summary.positive} van ${f.regime_summary.periods} halfjaren en verloor minder dan buy&hold in alle ${f.regime_summary.bear_periods} bear-periodes (EW &lt; −20%). In bull-periodes blijft het sterk achter bij buy&hold: dat is de prijs van de bescherming.</p></div>
  <div class="panel"><h2>Wat is geprobeerd?</h2><p class="small">${d.n_trials} parameter-configuraties over 8 strategie-families en 4 timeframes; alle kosten en slippage meegerekend. Zie <i>Strategieën</i> voor wie overleefde en waarom de rest werd weggegooid.</p></div>`;
  const draw=()=>{killCharts();const r=$('#rng').value;let cs={new:f.curve,ew:d.curves.bh_ew,sol:d.curves.bh_sol};
    const from=meta.test_period.match(/\d{4}-\d{2}-\d{2}/)[0];
    if(r==='oos')cs=Object.fromEntries(Object.entries(cs).map(([k,v])=>[k,rebase(v,from)]));
    const all=[...new Set([...cs.new.t,...cs.ew.t,...cs.sol.t])].sort();
    const align=c=>{const mp=new Map(c.t.map((t,i)=>[t,c.eq[i]]));return all.map(t=>mp.has(t)?mp.get(t):null)};
    chart($('#c1'),lineCfg(all,[{label:'Ensemble (eindstrategie)',data:align(cs.new),color:COL.new,w:2},{label:'Buy&hold gelijk gewogen',data:align(cs.ew),color:COL.ew},{label:'Buy&hold SOL',data:align(cs.sol),color:COL.sol}],{log:true,fmt:v=>v>=10?v.toFixed(0):v.toFixed(2)}));
    const dd=c=>{const mp=new Map(c.t.map((t,i)=>[t,c.dd[i]]));return all.map(t=>mp.has(t)?mp.get(t)*100:null)};
    chart($('#c2'),lineCfg(all,[{label:'Ensemble',data:dd(cs.new),color:COL.new,fill:true},{label:'Buy&hold gelijk gewogen',data:dd(cs.ew),color:COL.ew},{label:'Buy&hold SOL',data:dd(cs.sol),color:COL.sol}],{fmt:v=>v.toFixed(0)+'%'}));};
  $('#rng').onchange=draw;draw();
}

/* ---------- Kop-aan-kop ---------- */
async function vH2H(m){
  const [h,ov]=await Promise.all([API('h2h'),API('overview')]);
  const rows=h.rows; let tf='1h',win='oos';
  const find=(label,t,w)=>rows.find(r=>r.label===label&&r.tf===t&&r.window===w);
  function draw(){
    killCharts();
    const bot=find('BEST-OF',tf,win), nw=find('Nieuw: dagelijkse trend-ensemble','1d',win), nw2=find('Nieuw (zonder BTC-regime/breaker)','1d',win);
    const bhe=find('Buy&hold gelijk gewogen','1d',win), bhs=find('Buy&hold SOL','1d',win);
    const bhe_tf=find('Buy&hold gelijk gewogen',tf,win);
    const line=(lab,r,hl)=>r?R([lab,colr(r.ret),num(r.sharpe),colr(r.maxdd,0),r.trades||'–',r.win==null?'–':pct(r.win,0),r.pf==null?'–':num(r.pf),r.avg_net==null?'–':colr(r.avg_net,2),r.avg_gross==null?'–':colr(r.avg_gross,2)],{hl}):null;
    const T=[line(`Claude-bot BEST-OF (${tf})`,bot,true),line('Nieuw: dagelijkse trend-ensemble (1d)',nw,true),line('Nieuw zonder regime/breaker (1d)',nw2),line(`Buy&hold gelijk gewogen (${tf}-grid)`,bhe_tf),line('Buy&hold SOL',bhs)].filter(Boolean);
    const winner=(bot&&nw)?(nw.ret>bot.ret&&nw.sharpe>bot.sharpe?'nieuw':(bot.ret>nw.ret&&bot.sharpe>nw.sharpe?'bot':'gemengd')):'?';
    const wtxt={nieuw:'De nieuwe ensemble scoort <b>beter</b> dan de Claude-bot BEST-OF op rendement én Sharpe in dit venster.',bot:'De Claude-bot BEST-OF scoort beter dan de nieuwe ensemble.',gemengd:'Gemengd beeld: geen van beide wint op alle punten.','?':''}[winner];
    const botAbs=bot&&bot.ret>0, nwAbs=nw&&nw.ret>0;
    const pats=rows.filter(r=>r.family==='claude_pattern'&&r.tf===tf&&r.window===win).sort((a,b)=>b.sharpe-a.sharpe);
    $('#h2h-body').innerHTML=`
     <div class="panel verdict ${nwAbs&&botAbs?'good':'bad'}"><h2>Uitslag (${win==='oos'?'out-of-sample vanaf '+h.meta.oos_start:win==='history'?'periode vóór '+h.meta.oos_start:'alle data'})</h2>
      <p>${wtxt} ${bot?`Claude-bot BEST-OF op ${tf}: ${colr(bot.ret)} (Sharpe ${num(bot.sharpe)}, ${bot.trades} trades, gem. <b>${colr(bot.avg_net,2)}</b> netto per trade; bruto ${colr(bot.avg_gross,2)}).`:''}
      Nieuw: ${nw?colr(nw.ret)+' (Sharpe '+num(nw.sharpe)+')':'–'}. Buy&hold gelijk gewogen: ${bhe?colr(bhe.ret):'–'}.</p>
      <p class="small">${botAbs||nwAbs?'':'<b>Geen van beide verdient geld in dit venster.</b> '}Het verschil zit vooral in <i>hoeveel</i> ze verliezen: de langzame daggelijkse aanpak betaalt veel minder kosten (weinig trades) dan de snelle patronen.</p></div>
     <div class="panel"><h2>Kop-aan-kop tabel</h2>${tbl(['Strategie','Rendement','Sharpe','Max DD','Trades','Win%','Profit factor','Gem. netto/trade','Gem. bruto/trade'],T,{hl:r=>r.hl})}
      <p class="small muted">Zelfde tokens (${h.meta.universe.length}), zelfde kostenmodel, zelfde venster. Rendement = gelijk-gewogen portefeuille over beschikbare tokens (elke token krijgt 1/N van het kapitaal). Bruto = zelfde trades zonder kosten/slippage. Het portefeuille-rendement hangt van de sizing-conventie af (hier: elke token 1/N, Claude-bot-signalen op volle grootte, tiers A/B/C = 1,0/0,6/0,2); <b>gem. netto per trade is conventievrij</b> en laat hetzelfde zien als jouw eigen onderzoek: bruto ≈ 0, netto ≈ −0,7% tot −0,9% per trade.</p></div>
     <div class="grid g2"><div class="panel"><h2>Equity out-of-sample (start = 1)</h2><div class="chart sm"><canvas id="h1"></canvas></div></div>
      <div class="panel"><h2>Rendement per aanpak</h2><div class="chart sm"><canvas id="h2"></canvas></div></div></div>
     <div class="panel"><h2>Alle Claude-bot patronen op ${tf} (zelfde venster)</h2>${pats.length?tbl(['Patroon','Rendement','Sharpe','Max DD','Trades','Win%','Gem. netto/trade','Gem. bruto/trade'],pats.map(r=>R([r.label,colr(r.ret),num(r.sharpe),colr(r.maxdd,0),r.trades,pct(r.win,0),colr(r.avg_net,2),colr(r.avg_gross,2)]))):'<p class="muted">Geen data</p>'}
      <p class="small muted">Entries 1:1 geport uit labStrategies.js (squeeze, emaCross, rangeBreak, volSpike, buyPress-proxy, choch, rsiDiv, dipBuy, vwapReclaim, climax). Exits vereenvoudigd: zijn stop-formule, eerste target volledig, tijdstop. Niet portable uit candles: vp:lvnBrk en echte swap-orderflow.</p></div>
     <div class="panel"><h2>Per token, out-of-sample rendement</h2>${tbl(['Token','Claude-bot BEST-OF (1u)','Nieuw (1d)','Buy&hold'],h.per_token_oos.map(r=>R([r.token,colr(r.bestof_1h),colr(r.new_1d),colr(r.buyhold)])))}
      <p class="small muted">Nieuw is positief/beter dan B&H op ${h.per_token_oos.filter(r=>r.new_1d>r.buyhold).length} van ${h.per_token_oos.length} tokens; Claude-bot BEST-OF op ${h.per_token_oos.filter(r=>r.bestof_1h>r.buyhold).length}. Let op: B&H van tokens die crashten is een lage lat.</p></div>`;
    const c=h.curves, from=h.meta.oos_start; const bc=c['bestof_'+tf];
    const sets=[{k:'new',label:'Nieuw ensemble (1d)',color:COL.new,w:2},{k:'bh_ew',label:'Buy&hold gelijk gewogen',color:COL.ew},{k:'bh_sol',label:'Buy&hold SOL',color:COL.sol}].map(s=>({...s,c:c[s.k]}));
    if(bc)sets.push({k:'bot',label:`Claude-bot BEST-OF (${tf})`,color:COL.bot,w:2,c:bc});
    const all=[...new Set(sets.flatMap(s=>s.c.t))].sort();
    chart($('#h1'),lineCfg(all,sets.map(s=>{const rb=rebase(s.c,from);const mp=new Map(rb.t.map((t,i)=>[t,rb.eq[i]]));return {label:s.label,color:s.color,w:s.w,data:all.map(t=>mp.has(t)?mp.get(t):null)}}),{fmt:v=>v.toFixed(2)}));
    const bars=[[`Claude-bot ${tf}`,bot&&bot.ret,COL.bot],['Nieuw 1d',nw&&nw.ret,COL.new],['B&H EW',bhe&&bhe.ret,COL.ew],['B&H SOL',bhs&&bhs.ret,COL.sol]];
    chart($('#h2'),{type:'bar',data:{labels:bars.map(b=>b[0]),datasets:[{data:bars.map(b=>b[1]==null?null:b[1]*100),backgroundColor:bars.map(b=>b[2])}]},options:{responsive:true,maintainAspectRatio:false,animation:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.parsed.y.toFixed(1)+'%'}}},scales:{y:{ticks:{callback:v=>v+'%'}}}}});
  }
  m.innerHTML=`<div class="panel"><h2>Claude-bot (jouw BEST-OF/lab-strategieën) vs. nieuwe ensemble</h2>
    <p class="small">Exact dezelfde data, kosten en out-of-sample-periode. De parameters van de Claude-bot zijn niet getuned op deze data; daarom is alles vanaf ${h.meta.oos_start} voor beide out-of-sample (het nieuwe ensemble is vóór de test bevroren).</p>
    <div class="row"><label>Timeframe Claude-bot: <select id="tfsel"><option>15m</option><option selected>1h</option><option>4h</option></select></label>
    <label>Venster: <select id="winsel"><option value="oos">Out-of-sample (2025-04 → nu)</option><option value="history">Historie (vóór 2025-04)</option><option value="all">Alles</option></select></label></div></div><div id="h2h-body"></div>`;
  $('#tfsel').onchange=e=>{tf=e.target.value;if(tf==='15m'){win='oos';$('#winsel').value='oos'}draw()};
  $('#winsel').onchange=e=>{win=e.target.value;if(tf==='15m'&&win!=='oos'){tf='1h';$('#tfsel').value='1h'}draw()};
  draw();
}

/* ---------- Strategieën ---------- */
async function vStrategie(m){
  const d=await API('families'); const F=d.families;
  const names={donchian:'Donchian-breakout',donchian_vol:'Donchian + volumefilter',ema_trend:'EMA-trend + ATR-trailing',tsmom:'Time-series momentum (vol-genormaliseerd)',vol_breakout:'Volume-breakout',supertrend:'Supertrend',rsi_pullback:'RSI-pullback in uptrend (mean reversion)',bb_revert:'Bollinger mean reversion',rotation_momentum:'Cross-sectional momentum-rotatie (wekelijks)',short_only_perp:'Short-only perps (Donchian)',long_short_perp:'Long/short perps (Donchian)',donchian_short:'Donchian short'};
  const list=Object.values(F).filter(f=>names[f.strategy]).sort((a,b)=>b.metrics.test.sharpe-a.metrics.test.sharpe);
  const bt=d.benchmarks.bh_ew.test;
  m.innerHTML=`<div class="panel"><h2>Strategie-families op daggrafiek (representatieve parameters gekozen op dev, niet op test)</h2>
   <div class="tablewrap">${tbl(['Strategie','Dev Sharpe','OOS Sharpe','OOS rend.','OOS maxDD','Trades','Grid OOS-rend >0','Zonder beste token','Oordeel'],list.map(f=>{
     const v=f.survived?'<span class="tag ok">OVERLEEFT</span>':(f.defensive?'<span class="tag df">DEFENSIEF</span>':'<span class="tag no">VERWORPEN</span>');
     return R([names[f.strategy],num(f.metrics.dev.sharpe),num(f.metrics.test.sharpe),colr(f.metrics.test.ret),colr(f.metrics.test.maxdd,0),f.trades_all??'–',f.grid_posret_test==null?'–':pct(f.grid_posret_test,0),f.test_ex_best==null?'–':colr(f.test_ex_best),v])}))}</div>
   <p class="small muted">Buy&hold gelijk gewogen OOS: ${pct(bt.ret)} (maxDD ${pct(bt.maxdd,0)}). “Overleeft” vereist: ≥100 trades, dev-Sharpe ≥0,5, OOS-rendement &gt;0 én Sharpe &gt;0,3, ≥60% van de parameter-grid positief, positief zonder de beste token, OOS-maxDD beter dan −40%. <b>Geen enkele familie haalt dit.</b> “Defensief” = verliest OOS ruim minder dan buy&hold met veel lagere drawdown.</p></div>
  <div class="panel"><h2>Waarom verworpen</h2><ul class="clean small">${list.map(f=>`<li><b>${names[f.strategy]}</b>: ${f.reasons.length?f.reasons.join('; '):'alle criteria gehaald'}</li>`).join('')}</ul></div>
  <div class="panel"><h2>Timeframe-effect (mediaan over de volledige parameter-grid per strategie, OOS)</h2>
   <div class="row"><select id="tfs"><option>1h</option><option>4h</option><option>12h</option><option selected>1d</option></select></div><div id="tfb"></div>
   <p class="small muted">Hoe korter de timeframe, hoe meer trades en hoe harder de kosten toeslaan. Alleen de dagelijkse trend-families zijn rond nul OOS; alles op 1u/4u verliest.</p></div>
  <div class="panel"><h2>Equity-curves (alles, log)</h2><div class="row"><select id="fsel">${list.map(f=>`<option value="${f.strategy}">${names[f.strategy]}</option>`).join('')}</select></div><div class="chart"><canvas id="fc"></canvas></div></div>
  <div class="panel"><h2>Verbeterpogingen (gemeten, niet doorgevoerd: geen robuuste verbetering)</h2>
   ${tbl(['Poging','Dev Sharpe','OOS Sharpe','Conclusie'],[
    R(['Basis: ensemble + BTC-regime + breaker','1,53','−0,04','referentie']),
    R(['Liquiditeitsfilter ≥ $1M / 3M / 10M / 30M dagvolume','1,54 / 1,56 / 1,48 / 1,27','−0,32 / −0,48 / −0,06 / −0,52','geen verbetering']),
    R(['Regime op marktbreedte (≥30% tokens boven eigen 50d-gem.)','1,51','0,15','binnen ruis (OOS-rendement +2%); niet gekozen om niet op de test te tunen']),
    R(['Regime op SOL-100d i.p.v. BTC','1,24','−0,36','slechter']),
    R(['Zonder regime/breaker','1,45','0,08','vrijwel gelijk']),
    R(['Kosten ×0,5 (zeer goedkope uitvoering)','1,55','0,02','OOS nog steeds ≈ 0']),
    R(['Long/short met perps (Donchian short erbij)','0,90','0,13','shorts verliezen (dev Sharpe −0,19); niet beter']),
    R(['Walk-forward parameter-herselectie','–','–','slechter dan vast ensemble (zie Robuustheid)']),
    R(['Cross-sectional momentum-rotatie','0,90','0,79','schijnwinst: +55% OOS maar maxDD −69%, hangt af van ALCH/PIPPIN/ZEREBRO, wisselt per k (−27% … +160%): verworpen'])])}
   <p class="small muted">Er is bewust niet verder getuned op de out-of-sample-periode: dat zou de test waardeloos maken.</p></div>
  <div class="panel"><h2>Onderzoek: wat zegt de literatuur / GitHub (en wat is hype)</h2>
   <ul class="clean small">
    <li><b>Bewijs ✔︎ (voorzichtig)</b>: trend-following/Donchian-ensembles op liquide crypto (Zarattini e.a. 2025, SSRN 5209907: Sharpe ~1,5 net, maar zelf-gerapporteerde backtest); time-series momentum op korte horizon (Huang e.a. SSRN 4825389); cross-sectional momentum (Fieberg e.a. 2023). Onafhankelijke tests 2017-2025 vinden positieve ruwe rendementen maar geen multiple-testing-significantie.</li>
    <li><b>Hype ✘</b>: memecoin-sniping/“moon-rate”-filters. 2.380 tokens × 100+ strategieën (SwapHunt): geen betrouwbaar positieve EV na 8–12% round-trip slippage; fill-real dataset: echte frictie 10,7% round-trip op pump.fun-achtige tokens; overlevingsbias in trending-lijsten.</li>
    <li><b>Open source</b>: Freqtrade (GPL-3.0), Jesse (MIT), vectorbt, backtesting.py (AGPL-3.0), Flint (MIT; Solana perps/DEX lab), kboranyldz/sol-trading-research (geen licentie: rejected: breakout/compression/sweep, behouden: trend-pullback), Quant-Sol (MIT; RSI/Bollinger, 4–13 trades, Sharpe negatief), Dalgona (Flash Trade perps, licentie onduidelijk), Open Alpha (live-executie nog stub).</li>
   </ul></div>`;
  const tfdraw=()=>{const tf=$('#tfs').value;const r=d.timeframe_sweep[tf];$('#tfb').innerHTML=tbl(['Strategie','Configs','Dev Sharpe (med)','OOS Sharpe (med)','OOS rend. (med)','% grid OOS Sharpe>0','Trades OOS (med)'],r.map(x=>R([names[x.strategy]||x.strategy,x.n,num(x.dev_sharpe_med),num(x.test_sharpe_med),colr(x.test_ret_med),pct(x.pos_test,0),Math.round(x.trades_med)])))};
  $('#tfs').onchange=tfdraw;tfdraw();
  const fd=()=>{killCharts();const k=$('#fsel').value,c=d.curves[k];const bh=d.curves.BH_EW;const all=[...new Set([...c.t,...bh.t])].sort();const al=cc=>{const mp=new Map(cc.t.map((t,i)=>[t,cc.eq[i]]));return all.map(t=>mp.has(t)?mp.get(t):null)};
    chart($('#fc'),lineCfg(all,[{label:names[k],data:al(c),color:COL.new,w:2},{label:'Buy&hold gelijk gewogen',data:al(bh),color:COL.ew},{label:'Buy&hold SOL',data:al(d.curves.BH_SOL),color:COL.sol}],{log:true,fmt:v=>v>=10?v.toFixed(0):v.toFixed(2)}))};
  $('#fsel').onchange=fd;fd();
}

/* ---------- Per token ---------- */
async function vToken(m){
  const d=await API('per_token');
  const cell=(p)=>p?[colr(p.strat_ret,0),colr(p.bh_ret,0),num(p.sharpe),colr(p.maxdd,0)]:['–','–','–','–'];
  m.innerHTML=`<div class="panel"><h2>Per token: ensemble-sleeve vs buy&hold (de sleeve = alleen kapitaal van dit token)</h2>
   ${tbl(['Token','Start','Trades','Win%','PF','Alles: strat','B&H','Sharpe','maxDD','OOS: strat','B&H','Sharpe','maxDD'],d.map(r=>R([r.token,r.start,r.trades,pct(r.win,0),num(r.pf),...cell(r.all),...cell(r.test)])))}
   <p class="small muted">Een token telt pas mee na 30 dagen handelsgeschiedenis (listing-pomp uitgesloten). SRM is gedelisteerd (FTX-crash) en zit bewust in de data; ook gedelisteerde perp-tokens (PONKE, AI16Z, VINE, SLERF, MYRO) zijn meegenomen om overlevingsbias te verkleinen.</p>
   <div class="chart" style="height:360px"><canvas id="tc"></canvas></div></div>`;
  const rows=d.filter(r=>r.test);
  chart($('#tc'),{type:'bar',data:{labels:rows.map(r=>r.token),datasets:[{label:'Ensemble OOS',data:rows.map(r=>r.test.strat_ret*100),backgroundColor:COL.new},{label:'Buy&hold OOS',data:rows.map(r=>r.test.bh_ret*100),backgroundColor:COL.ew}]},options:{responsive:true,maintainAspectRatio:false,animation:false,scales:{y:{ticks:{callback:v=>v+'%'}}}}});
}

/* ---------- Trades ---------- */
async function vTrades(m){
  const toks=(await API('per_token')).map(r=>r.token);
  m.innerHTML=`<div class="panel"><h2>Trade-lijst (ensemble, alle sleeves, nieuwste eerst)</h2><div class="row"><select id="tt"><option value="">alle tokens</option>${toks.map(t=>`<option>${t}</option>`).join('')}</select><span id="tinfo" class="muted"></span><button class="act" id="prev">←</button><button class="act" id="next">→</button></div><div id="tl"></div></div>`;
  let off=0;const L=50;
  async function load(){const t=$('#tt').value;const r=await API(`trades?limit=${L}&offset=${off}`+(t?`&token=${t}`:''));$('#tinfo').textContent=`${off+1}–${Math.min(off+L,r.total)} van ${r.total}`;
    $('#tl').innerHTML=tbl(['Token','Component','Instap','Uitstap','In','Uit','Netto','Reden'],r.rows.map(x=>R([x.token,x.strategy.replace('donchian','donch').replace('vol_breakout','volbrk'),x.entry_time,x.exit_time,usd(x.entry_px),usd(x.exit_px),colr(x.ret,1),x.reason==='stop'?'stop':(x.reason==='signal'?'signaal':x.reason)])))}
  $('#tt').onchange=()=>{off=0;load()};$('#prev').onclick=()=>{off=Math.max(0,off-L);load()};$('#next').onclick=()=>{off+=L;load()};load();
}

/* ---------- Robuustheid ---------- */
async function vRobuust(m){
  const r=await API('robustness'),o=await API('overview');
  const hm=r.donchian_heatmap, ent=[...new Set(hm.map(x=>x.entry))], ex=[...new Set(hm.map(x=>x.exit))];
  const col=v=>v>0.5?'#12301f':v>0?'#1a2a22':v>-0.3?'#2a1a22':'#3a1426';
  const heat=(k)=>`<table class="heat"><thead><tr><th>entry \\ exit</th>${ex.map(e=>`<th>${e}d</th>`).join('')}</tr></thead><tbody>${ent.map(e=>`<tr><td>${e}d</td>${ex.map(x=>{const c=hm.find(h=>h.entry===e&&h.exit===x);return c?`<td class="c" style="background:${col(c[k])}">${num(c[k])}</td>`:'<td></td>'}).join('')}</tr>`).join('')}</tbody></table>`;
  const rs=r.random_subsets, bs=r.bootstrap, wf=r.walk_forward;
  const loo=r.leave_one_out.slice().sort((a,b)=>a.sharpe_test-b.sharpe_test);
  m.innerHTML=`
  <div class="panel"><h2>Statistiek: is dit meer dan toeval?</h2>
   ${tbl(['Venster','Sharpe','90%-interval (block-bootstrap)','P(Sharpe ≤ 0)','Deflated Sharpe prob.'],['dev','test','all'].map(k=>R([{dev:'Dev',test:'Out-of-sample',all:'Alles'}[k],num(bs[k].sharpe),`${num(bs[k].ci5)} … ${num(bs[k].ci95)}`,pct(bs[k].p_leq0,1),num(bs[k].dsr,3)])))}
   <p class="small muted">${r.n_trials} configuraties getest. De deflated Sharpe corrigeert voor selectie uit zoveel pogingen: de waarden ≈ 0 betekenen dat de in-sample Sharpe <b>niet bewezen</b> boven toeval uitkomt als je al het zoeken meetelt. Out-of-sample is het interval ruim rond 0.</p></div>
  <div class="grid g2">
   <div class="panel"><h2>Donchian-parameters: Sharpe dev (ATR 4)</h2>${heat('dev')}<p class="small muted">Plateau, geen piek: vrijwel alle parameters werken in dev.</p></div>
   <div class="panel"><h2>Donchian-parameters: Sharpe out-of-sample</h2>${heat('test')}<p class="small muted">OOS rond nul en wisselend: de dev-sterkte houdt niet stand in een bear-markt.</p></div></div>
  <div class="grid g2">
   <div class="panel"><h2>Willekeurige token-subsets (200× 8 tokens)</h2>
    ${tbl(['','P5','Mediaan','P95','% > 0'],[R(['Ensemble Sharpe alles',num(rs.sharpe_all.p5),num(rs.sharpe_all.p50),num(rs.sharpe_all.p95),pct(rs.sharpe_all.pos,0)]),R(['Ensemble Sharpe OOS',num(rs.sharpe_test.p5),num(rs.sharpe_test.p50),num(rs.sharpe_test.p95),pct(rs.sharpe_test.pos,0)]),R(['Buy&hold Sharpe alles',num(rs.bh_sharpe_all.p5),num(rs.bh_sharpe_all.p50),num(rs.bh_sharpe_all.p95),'–'])])}
    <p class="small muted">Het resultaat hangt niet van één coin af, maar de spreiding is groot.</p></div>
   <div class="panel"><h2>Kosten-stresstest</h2>${tbl(['Kosten ×','Sharpe dev','Sharpe OOS','Rend. OOS','Rend. alles'],r.cost_stress.map(c=>R([c.cost_scale+'×',num(c.sharpe_dev),num(c.sharpe_test),colr(c.ret_test),colr(c.ret_all,0)])))}</div></div>
  <div class="grid g2">
   <div class="panel"><h2>Dag-grens verschuiven (UTC-offset candles)</h2>${tbl(['Offset','Sharpe dev','Sharpe OOS','Sharpe alles','Max DD'],r.offset.map(c=>R([{'1d':'00:00','1d6':'06:00','1d12':'12:00','1d18':'18:00'}[c.offset],num(c.sharpe_dev),num(c.sharpe_test),num(c.sharpe_all),colr(c.maxdd,0)])))}</div>
   <div class="panel"><h2>Leave-one-token-out (zwakste 8, OOS Sharpe)</h2>${tbl(['Zonder token','Sharpe OOS','Sharpe alles','Rend. alles'],loo.slice(0,8).map(c=>R([c.dropped,num(c.sharpe_test),num(c.sharpe_all),colr(c.ret_all,0)])))}
    <p class="small muted">Sharpe alles blijft tussen ${num(Math.min(...r.leave_one_out.map(x=>x.sharpe_all)))} en ${num(Math.max(...r.leave_one_out.map(x=>x.sharpe_all)))} bij het weglaten van één token.</p></div></div>
  <div class="panel"><h2>Walk-forward (kwartaal-herkalibratie van Donchian-parameters op voorgaande 2 jaar, vanaf ${wf.start})</h2>
   <div class="grid g3">${kpi('Walk-forward rend.',pct(wf.metrics.ret,0),'Sharpe '+num(wf.metrics.sharpe)+' · maxDD '+pct(wf.metrics.maxdd,0))}${kpi('Buy&hold zelfde periode',pct(wf.bh_same_window.ret,0),'Sharpe '+num(wf.bh_same_window.sharpe)+' · maxDD '+pct(wf.bh_same_window.maxdd,0))}${kpi('Eindstrategie zelfde periode',pct(wf.final_ens_same_window.ret,0),'Sharpe '+num(wf.final_ens_same_window.sharpe)+' · maxDD '+pct(wf.final_ens_same_window.maxdd,0))}</div>
   <div class="chart sm"><canvas id="wf"></canvas></div>
   <p class="small muted">Walk-forward met herselectie levert minder dan de vaste ensemble: parameter-tuning voegt niets toe — daarom is het ensemble bewust niet getuned (meerdere lookbacks gemengd).</p></div>`;
  chart($('#wf'),lineCfg(wf.curve.t,[{label:'Walk-forward',data:wf.curve.eq,color:COL.bot}],{log:true,fmt:v=>v.toFixed(2)}));
}

/* ---------- Parameters ---------- */
async function vParams(m){
  const d=await API('params');
  m.innerHTML=`<div class="panel"><h2>Eindstrategie: dagelijkse trend-ensemble (bevroren vóór de test)</h2>
   ${tbl(['#','Component','Parameters'],d.components.map((c,i)=>R([i+1,c.strategy,Object.entries(c.params).map(([k,v])=>`${k}=${v}`).join(', ')])))}
   <h3>Overlay (portefeuille)</h3><ul class="clean"><li>Regime-filter: alleen risico aan als <b>${d.overlay.regime_ref}</b> boven zijn ${d.overlay.regime_ma_days}-daags gemiddelde sluit (signaal van de vorige candle).</li><li>Drawdown-rem: bij −${d.overlay.breaker_dd*100}% vanaf piek ${d.overlay.breaker_cool_days} dagen cash, daarna herstart met nieuwe piek.</li></ul>
   <h3>Sizing &amp; risico</h3><p class="small">${d.sizing}</p>
   <h3>Uitvoering &amp; kosten</h3><ul class="clean small"><li>Signalen op gesloten daggrafiek; orders op de <b>volgende open</b> (geen look-ahead).</li><li>Stops: ATR-trailing, getoetst tegen de dag-low; gap onder stop vult op open + extra slippage 0,3%.</li><li>Kosten per kant: SOL 0,20%, mid-caps 0,30%, memecoins 0,40% (fee + slippage + impact).</li><li>Eerste 30 dagen na listing doen niet mee.</li><li>Geen leverage, geen shorts (spot).</li></ul>
   <h3>Data</h3><p class="small">${d.meta.source}. Tokens (${d.meta.universe.length}): ${d.meta.universe.join(', ')}.</p></div>`;
}

/* ---------- Live & Paper ---------- */
async function vLive(m){
  m.innerHTML=`<div class="panel"><h2>Live signalen (simulatie — geen orders)</h2><div class="row"><button class="act" id="rf">Ververs</button><span id="lmeta" class="muted"></span></div><div id="lreg"></div><div id="lt" class="muted">Live data laden… (eerste keer ±20 s)</div></div>
   <div class="panel"><h2>Paper-account</h2><div id="pp" class="muted">Laden…</div></div>`;
  let err=false;
  async function sig(refresh){
    try{const s=await API('live/signals'+(refresh?'?refresh=true':''));
      $('#lmeta').textContent=`laatste gesloten dag: ${s.last_closed} · opgehaald ${s.fetched} · ${s.n_listed} tokens`;
      $('#lreg').innerHTML=`<div class="panel verdict ${s.regime.on?'good':'bad'}" style="margin:6px 0"><b>Marktregime: ${s.regime.on?'RISICO AAN':'RISICO UIT (alles cash)'}</b> — BTC ${usd(s.regime.btc)} vs 100d-gemiddelde ${usd(s.regime.btc_ma100)}. <span class="muted small">${s.regime.rule}</span></div>`;
      const rows=s.rows.slice().sort((a,b)=>(b.components_long-a.components_long)||(b.target_weight-a.target_weight));
      $('#lt').innerHTML=tbl(['Token','Prijs','24u','Status','Componenten long','Doelgewicht','Vol (ann.)','Instap','Stop (hoogste comp.)','Uitbraak-niveau (20d)'],rows.map(r=>{const lc=r.components_detail.filter(c=>c.in_position);const stop=lc.length?Math.max(...lc.map(c=>c.stop)):null;const ent=lc.length?lc[0].entry_time:'–';
        const bo=r.components_detail.find(c=>c.strategy.includes('entry_days=20'));return R([r.token,usd(r.price),colr(r.chg_24h,1),`<span class="pill ${r.status}">${r.status}</span>`,r.components_long+'/'+r.components,pct(r.target_weight,1),pct(r.vol_ann,0),ent,stop?usd(stop):'–',bo?usd(bo.next_breakout):'–'])}));
    }catch(e){$('#lt').innerHTML=`<span class="sell">${e.message}</span>`}}
  async function paper(){
    try{const p=await API('paper');
      if(!p.active){$('#pp').innerHTML=`<p>Er is nog geen paper-account. Start er een met virtueel kapitaal; het volgt het model vanaf vandaag (nooit echte orders).</p><div class="row"><input id="eq" type="number" value="10000" style="width:110px"> <button class="act" id="ps">Start paper-account</button></div>`;$('#ps').onclick=async()=>{await fetch('/api/paper/start?equity='+$('#eq').value,{method:'POST'});paper()};return}
      $('#pp').innerHTML=`<div class="grid g4">${kpi('Start',p.start,'$'+p.equity0.toFixed(0))}${kpi('Waarde (live)','$'+p.equity_live.toFixed(2),'gesloten dag: $'+p.equity_closed.toFixed(2))}${kpi('Rendement',pct(p.ret_live,2),'sinds start',cls(p.ret_live))}${kpi('Open posities',p.open_positions.length,'componenten')}</div>
       <h3>Open posities</h3>${p.open_positions.length?tbl(['Token','Component','Instap','Instapprijs','Grootte','Stop','Ongerealiseerd'],p.open_positions.map(o=>R([o.token,o.strategy,o.entry_time,usd(o.entry_px),num(o.size),usd(o.stop),colr(o.unreal,1)]))):'<p class="muted small">Geen open posities (cash).</p>'}
       <h3>Gesloten trades sinds start</h3>${p.closed_trades.length?tbl(['Token','Component','In','Uit','Netto','Reden'],p.closed_trades.map(o=>R([o.token,o.strategy,o.entry,o.exit,colr(o.ret),o.reason]))):'<p class="muted small">Nog geen gesloten trades.</p>'}
       <div class="chart sm"><canvas id="pc"></canvas></div><p class="small muted">${p.note}</p><button class="act danger" id="pr">Reset paper-account</button>`;
      $('#pr').onclick=async()=>{await fetch('/api/paper/reset',{method:'POST'});paper()};
      killCharts();if(p.curve.t.length>1)chart($('#pc'),lineCfg(p.curve.t,[{label:'Paper-equity ($)',data:p.curve.eq,color:COL.new}],{fmt:v=>'$'+v.toFixed(0)}));
    }catch(e){$('#pp').innerHTML=`<span class="sell">${e.message}</span>`}}
  $('#rf').onclick=()=>{sig(true);paper()};
  sig(false).then(paper);
}
const VIEWS={overzicht:vOverzicht,h2h:vH2H,strategie:vStrategie,token:vToken,trades:vTrades,robuust:vRobuust,params:vParams,live:vLive};
cur=(location.hash||'#overzicht').slice(1);if(!VIEWS[cur])cur='overzicht';go();
