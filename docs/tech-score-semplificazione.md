# Specifica — Semplificazione di TECH_SCORE, Market_Phase e segnale d'ingresso

Stato: **proposta da approvare**. Nessuna modifica al codice è stata fatta.
Data: 2026-10-04. Obiettivo dichiarato: *capire a colpo d'occhio cosa sta facendo il titolo*.

---

## 1. Perché cambiare (misurato)

| | Oggi | Proposta |
|---|---|---|
| Indicatori usati per decidere | **19 valori** da 11 famiglie | **6** |
| Stati di mercato | 6 fasi × **15** dettagli di trend | **4 fasi** + 1 avviso |
| Pesi/soglie | sparsi in `TechnicalAnalyzer.py`, `watchlist_service.py`, `WatchlistCard.tsx` | **un solo blocco di soglie** |
| Ridondanza nella struttura | 6 misure quasi equivalenti di "prezzo sopra le medie" | 1 misura + pendenza |
| Segnale d'ingresso | cascata su `Action` (12 regole) → 4 valori | 4 assi → 4 valori |

Casi che oggi non si distinguono e che la proposta separa:

- `STMMI.MI` e `IP.MI` hanno **entrambi** segnale ATTENDI e lo stesso messaggio, ma uno ha TECH 78,8 e RSI 67, l'altro TECH 44 e DI− > DI+.
- `BMPS.MI` `[PIATTO/DEBOLE/CALANTE]` e `AZM.MI` `[PIATTO/DEBOLE/STABILE]` sono entrambi "RANGE": uno sta perdendo forza, l'altro è fermo.
- `AIPE.MI` è `DOWNTREND` con ADX forte: oggi si legge come gli altri ribassi, senza distinguere un ribasso convinto da una discesa lenta.

---

## 2. I quattro assi

Ogni asse è **indipendente** e si legge da solo. Non c'è più un numero unico che somma cose diverse.

### Asse 1 — DIREZIONE (dove sta andando il prezzo)

- Riferimento: **EMA50** (una sola media, non EMA30 + EMA50 + 3 linee Alligator + SAR).
- Pendenza: variazione dell'EMA50 sulle ultime **5 sedute**.

```
SU      se  Close > EMA50  e  (pendenza5(EMA50) > +0,5%  oppure  ADX >= 22)
GIU     se  Close < EMA50  e  (pendenza5(EMA50) < -0,5%  oppure  ADX >= 22)
PIATTO  altrimenti
```

Perché la condizione `oppure ADX >= 22`: con una soglia di pendenza fissa, un titolo in ribasso lento ma con ADX forte risultava "piatto" — è l'errore che ho trovato misurando (`AIPE.MI`).

### Asse 2 — FORZA (quanto è convincente il movimento)

```
FORTE_SU   se  ADX >= 22  e  DI+ > DI-
FORTE_GIU  se  ADX >= 22  e  DI- > DI+
DEBOLE     altrimenti
```

Sostituisce `ADX_Strong`, `ADX_Trend`, `ADX_Slope`, `ADX_Cross`, `ADX_Trend_Days` (5 colonne oggi usate insieme).

### Asse 3 — MOMENTO (sta accelerando o frenando)

Solo **MACD**: differenza MACD − Signal, confrontata con 3 sedute prima.

```
CRESCENTE  se  (MACD - Signal) > 0  e  in aumento su 3 sedute
CALANTE    se  (MACD - Signal) < 0  e  in diminuzione su 3 sedute
STABILE    altrimenti
```

Sostituisce `MACDH_Trend`, `MACDH_Trend_Days`, `RSI_Trend`, `SK_Trend`, `MACD_vs_Signal` (5 colonne).

### Asse 4 — RISCHIO (quanto è teso)

```
ESTREMO  se  ATR% >= 5   oppure  |Close/EMA50 - 1| >= 9%
TESO     se  ATR% >= 3   oppure  |Close/EMA50 - 1| >= 5%
NORMALE  altrimenti
```

Sostituisce la **penalità di estensione** del TECH_SCORE: oggi toglie fino a 20 punti in modo occulto, qui diventa un'**informazione visibile**.

---

## 3. Le quattro fasi

```
TENDENZA  =  DIREZIONE SU      e  FORZA FORTE_SU  e  MOMENTO != CALANTE
RIPRESA   =  DIREZIONE SU      e  non è TENDENZA      (forza debole o momento calante)
RIBASSO   =  DIREZIONE GIU
LATERALE  =  DIREZIONE PIATTO  (qualunque sia la forza)
```

Sostituisce: `Market_Phase` (6 valori) + `Trend_Phase_Detail` (15 valori) + `Layer1/Layer2/Trading_State`.
Il valore `DOWNTREND` con `ADX_Trend` ribassista non serve più separarlo: è `RIBASSO` con `FORZA = FORTE_GIU`.

### Indicazione operativa (quattro valori, come oggi)

```
ENTRA    =  TENDENZA  e  MOMENTO != CALANTE  e  RISCHIO = NORMALE
OSSERVA  =  RIPRESA   oppure  (DIREZIONE SU  e  MOMENTO CRESCENTE)
EVITA    =  RIBASSO   e  FORZA FORTE_GIU
ATTENDI  =  tutti gli altri casi
```

Nota: il solo "momento crescente" **non** basta più per OSSERVA (prima portava al 39% dei titoli in OSSERVA), serve anche una direzione rialzista.

---

## 4. Validazione sui dati reali (Excel attuali)

### MIB30 (42 titoli)

| Nuova fase | BREAKOUT | UPTREND | PULLBACK | RANGE | DOWNTREND | REVERSAL_RISK | totale |
|---|---|---|---|---|---|---|---|
| TENDENZA | 0 | 2 | 0 | 0 | 0 | 0 | **2** |
| RIPRESA | 0 | 1 | 1 | 1 | 0 | 3 | **6** |
| LATERALE | 0 | 0 | 1 | 16 | 2 | 0 | **19** |
| RIBASSO | 0 | 0 | 0 | 4 | 9 | 2 | **15** |

Indicazione risultante: **ATTENDI 21 · EVITA 13 · OSSERVA 8 · ENTRA 0** (oggi: 7 ATTENDI, 4 OSSERVA, 31 EVITA, 0 ENTRA).

### ETF (1685 titoli)

| Nuova fase | totale |
|---|---|
| TENDENZA | **151** |
| RIPRESA | **349** |
| LATERALE | **508** |
| RIBASSO | **677** |

Indicazione risultante: **ATTENDI 747 · EVITA 460 · OSSERVA 435 · ENTRA 43**.

### Esempi concreti (prima → dopo)

| Ticker | Oggi | Proposta | Assi |
|---|---|---|---|
| `C3M.MI` | UPTREND | **TENDENZA / ENTRA** | SU · FORTE_SU · STABILE · NORMALE |
| `AIUU.MI` | UPTREND | **TENDENZA / OSSERVA** | SU · FORTE_SU · CRESCENTE · NORMALE |
| `CL2.MI` | PULLBACK | **RIPRESA / OSSERVA** | SU · DEBOLE · CRESCENTE · NORMALE |
| `AIPE.MI` | DOWNTREND | **RIBASSO / EVITA** | GIU · FORTE_GIU · STABILE · NORMALE |
| `ANAU.MI` | PULLBACK | **LATERALE / ATTENDI** | PIATTO · DEBOLE · CRESCENTE · NORMALE |
| `AHYU.MI` | REVERSAL_RISK | **LATERALE / ATTENDI** | PIATTO · DEBOLE · STABILE · NORMALE |

### Tre difetti trovati misurando (e già corretti nella spec)

1. Con soglia di pendenza fissa, `AIPE.MI` (ribasso lento, ADX forte) risultava **LATERALE**: risolto legando la direzione all'ADX.
2. Con l'ADX non legato alla direzione, **183 ETF** risultavano LATERALE pur avendo `FORTE_GIU`: risolto come sopra.
3. `momento crescente` da solo promuoveva a OSSERVA il **39%** degli ETF: ristretto a direzione rialzista.

---

## 5. Cosa resta e cosa sparisce

**Resta** (già calcolato, serve al resto dell'app): tutti gli indicatori salvati nel workbook, i pattern S2-S9, i livelli di stop, il grafico.
**Non serve più per decidere**: `ADX_Strong`, `ADX_Slope`, `ADX_Cross`, `ADX_Trend_Days`, `MACD_vs_Signal` come segnale separato, `RSI_Trend`, `SK_Trend`, `WILLR_*` come stato, le 3 linee Alligator per la struttura, `Trend_Phase_Detail` (15 valori), `Layer1/Layer2/Trading_State`.

**Compatibilità GUI**: le colonne `TECH_SCORE`/`Market_Phase`/`Entry_Signal` restano con gli stessi nomi, quindi card, filtri, tab e alert continuano a funzionare. Cambia come sono calcolate — e `Trend_Phase_Detail` si riduce ai 4 valori di fase.

**TECH_SCORE**: la proposta lo **ricalcola** (opzione (a) approvata) come somma visibile dei quattro assi, sulla stessa scala 0-100.

### Contributi in punti (nessun peso occulto)

| Asse | Valore | Punti |
|---|---|---|
| DIREZIONE | SU / PIATTO / GIU | **+60 / 0 / −60** |
| FORZA | FORTE_SU / DEBOLE / FORTE_GIU | **+35 / 0 / −35** |
| MOMENTO | CRESCENTE / STABILE / CALANTE | **+35 / 0 / −35** |
| RISCHIO | NORMALE / TESO / ESTREMO | **0 / −10 / −20** |

```
somma = direzione + forza + momento + rischio        (da -150 a +130)
TECH_SCORE_v3 = clip(50 + somma * (50 / 150), 0, 100)
```

L'ancora è esatta: **somma 0 → 50** (titolo senza convinzione né rischio). La direzione pesa più di forza e momento perché è l'unica che dice *dove* si va; il rischio non può alzare il punteggio, può solo abbassarlo.

### Verifica della scala (casi teorici)

| Situazione | Punteggio |
|---|---|
| fermo, niente di niente | **50,0** |
| solo direzione su (forza debole) | 70,0 |
| tendenza piena, rischio normale | **93,3** |
| tendenza piena ma tesa | 90,0 |
| tendenza piena ma estrema | 86,7 |
| ribasso pieno | **6,7** |

### Effetto sui dati reali

| | MIB30 (42) | ETF (1685) |
|---|---|---|
| mediana v2 → v3 | 40,3 → **38,3** | 44,5 → **50,0** |
| media v2 → v3 | 40,0 → **40,1** | 43,5 → **46,0** |
| range v3 | 0 – 93,3 | 0 – 93,3 |
| titoli con TECH ≥ 65 | 2 → **4** (4,8% → 9,5%) | 87 → **449** (5,2% → 26,6%) |
| titoli con TECH ≤ 35 | 16 → **16** (38,1%) | 477 → **639** (28,3% → 37,9%) |

L'ultima riga è il punto da decidere: con le soglie attuali (65/35) il nuovo punteggio è **più generoso in alto e più severo in basso** sugli ETF, perché la direzione pesa molto. Se preferisci mantenere la selettività di oggi, si alzano le soglie (per esempio 70/30) oppure si riduce il peso della direzione da 60 a 50.

### Difetto trovato misurando la formula (e corretto)

Il primo tentativo usava `(somma + 200) / 350 * 100` con contributi 40/60/50/−25/−50: un titolo **piatto e senza forza prendeva 57,1 invece di 50**, perché i contributi positivi erano più grandi dei negativi. Corretto con pesi simmetrici e ancora esplicita a 50.

---

## 6. Dove stanno le soglie

Un unico blocco in cima al modulo di analisi:

```python
SOGLIE = {
    "adx_forte": 22,            # Forza
    "slope_piatta_pct": 0.5,    # Direzione (pendenza EMA50 su 5 sedute)
    "macd_momento_sedute": 3,   # Momento
    "atr_teso_pct": 3.0,        # Rischio
    "atr_estremo_pct": 5.0,
    "dist_tesa_pct": 5.0,
    "dist_estrema_pct": 9.0,
}
```

Cambiare una soglia = cambiare una riga, in un punto solo.
