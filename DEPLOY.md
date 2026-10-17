# SolBot Lab online zetten (Railway via GitHub) — stap voor stap

> **Let op: dit is alleen paper trading (nep-geld).** Er is geen wallet, geen API-key en geen wachtwoord nodig.
> De app plaatst nooit echte orders. Je hoeft nergens een sleutel in te vullen.

Je hebt nodig: een gratis GitHub-account en een Railway-account (inloggen met GitHub kan). Railway kost ongeveer $5 per maand (of je gratis proefcredits).

---

## Deel 1 — Bestanden op GitHub zetten

1. Pak de zip **`solbot-deploy.zip`** uit op je computer. Je krijgt een map met o.a. `app.py`, `Procfile`, `requirements.txt`, een map `sb`, een map `static` en een map `results`.
2. Ga naar **https://github.com** en log in.
3. Klik rechtsboven op het **+** en kies **New repository**.
4. Bij *Repository name* typ je: `solbot-lab`.
5. Kies **Private** (alleen jij ziet het) of Public. Laat de rest staan. **Vink niets aan** bij "Add a README".
6. Klik op de groene knop **Create repository**.
7. Je ziet nu een pagina met een link **uploading an existing file**. Klik daarop.
8. Open de uitgepakte map op je computer. Selecteer **alles in de map** (Ctrl+A / Cmd+A) en **sleep het naar het GitHub-venster**.
   - Belangrijk: sleep de *inhoud* van de map, niet de map zelf. `app.py` en `Procfile` moeten bovenaan in de repository komen te staan.
   - Controleer dat ook de mappen `sb`, `static` en `results` mee zijn gegaan. Wacht tot alle bestanden klaar zijn met uploaden.
9. Scroll naar beneden en klik op de groene knop **Commit changes**.
10. Controleer: in je repository zie je `app.py`, `Procfile`, `requirements.txt`, `runtime.txt`, en de mappen `sb`, `static`, `results`. In `results` moeten `final.json` en `h2h.json` staan.

> Lukt het slepen van mappen niet (sommige browsers)? Upload dan de losse bestanden eerst. Daarna klik je in de repository op **Add file → Upload files** en sleep je elke map apart erin. Of gebruik GitHub Desktop.

---

## Deel 2 — Op Railway zetten

1. Ga naar **https://railway.com** en klik op **Login** → **Login with GitHub**. Geef toestemming.
2. Klik op **New Project**.
3. Kies **Deploy from GitHub repo**.
4. Staat je repository er niet bij? Klik op **Configure GitHub App**, geef Railway toegang tot `solbot-lab` en ga terug.
5. Klik op **solbot-lab**. Als er een knop **Deploy Now** verschijnt, klik daarop.
6. Railway gaat bouwen. De eerste keer duurt dit **3 tot 8 minuten** (er worden rekenpakketten geïnstalleerd). Je kunt de voortgang zien bij **Deployments → View logs**. Het is klaar als je **Success** / **Active** ziet.

### Variabelen (optioneel — de app werkt ook zonder)
Er zijn **geen sleutels of wachtwoorden nodig**. Alleen als je je paper-account wilt bewaren (zie "Volume" hieronder), zet je 1 variabele:

1. Klik op je service (het blokje) → tabblad **Variables**.
2. Klik **New Variable**. Naam: `DATA_DIR`, waarde: `/data`. Klik **Add**.
3. (Alleen als Binance niet bereikbaar is, zie "Problemen" onderaan:) `BINANCE_BASE` = `https://data-api.binance.vision/api/v3`.

Railway start de app daarna vanzelf opnieuw.

### Een link (domein) maken
1. Klik op je service → tabblad **Settings**.
2. Zoek **Networking** → **Public Networking** en klik op **Generate Domain**.
3. Je krijgt een link zoals `solbot-lab-production.up.railway.app`. Open die link: dat is je app.

### Volume (optioneel, aanbevolen): je paper-account bewaren
Zonder Volume wordt je paper-account gewist als Railway de app opnieuw start of bijwerkt. De rest (backtest, vergelijking, live signalen) blijft gewoon werken.

1. Op je project-canvas: klik op **Create** (of rechtermuisklik op de achtergrond) → **Volume**, en koppel hem aan je service. Of: service → **Settings** → **Volumes** → **Add Volume**.
2. Vul bij **Mount path** in: `/data`
3. Zorg dat de variabele `DATA_DIR` = `/data` staat (zie hierboven). Beide moeten hetzelfde zijn.
4. Klaar. Je paper-account blijft nu bewaard.

---

## Updaten later
Wil je iets aanpassen? Ga in GitHub naar het bestand, klik op het potloodje, wijzig, en klik **Commit changes**. Railway zet de nieuwe versie automatisch online.

## Problemen?
- **"Application failed to respond" / link werkt niet:** wacht 1–2 minuten en kijk bij *Deployments → View logs* of er **Success** staat. Staat er rood? Stuur me de laatste regels van de log.
- **Tabblad "Live" of "Paper" geeft een fout:** Binance blokkeert soms servers in de VS. Zet in Railway bij *Settings → Region* een Europese regio (bijv. **EU West (Amsterdam)**), of zet de variabele `BINANCE_BASE` zoals hierboven. De backtest en vergelijking werken ook zonder live data.
- **Paper-account weg na herstart:** je hebt nog geen Volume gekoppeld (zie hierboven).

## Wat er wel en niet in zit
- De cijfers (backtest, "Kop-aan-kop") staan vast in `results/final.json` en `results/h2h.json`. Daarvoor is geen extra data nodig.
- De grote datamappen `data/` en `data15/` (prijsgeschiedenis, ~260 MB) staan **niet** online. Die zijn alleen nodig om het onderzoek opnieuw te draaien op je eigen computer.
- Eerlijke waarschuwing: geen enkele strategie in deze test verdiende aantoonbaar geld na kosten. Gebruik dit als lab en paper trading, niet als belofte van winst.
