# Portafoglio virtuale — specifica definitiva

Documento di progetto. **Nessun codice di questa funzione è stato scritto**: qui ci
sono schermate, campi, formule e formato dei file. Serve per essere d'accordo prima
di toccare il programma.

Versione: 1.0 · 17 ottobre 2026

---

## 0. Le decisioni chiuse

| # | Decisione | Scelta |
|---|---|---|
| 1 | Capitale iniziale | **definibile per ogni portafoglio** |
| 2 | Profili | **nessun profilo utente**: tanti portafogli indipendenti, ognuno con i suoi parametri. I profili sono solo *preset* di partenza |
| 3 | Grado di automazione | **tutto automatico**, con intervento manuale sempre possibile |
| 4 | Prezzo di esecuzione | **quello visto dal motore quando gira** (ogni 15 minuti) |
| 5 | Fascia oraria | **9:30–18:00** per tutti + **18:00–22:00** solo titoli USA |
| 6 | Analisi intraday | si può lanciare, ma **non può comprare** |
| 7 | Rotazione | **spenta** |
| 8 | Riserva di liquidità | **10%** |
| 9 | Valute | **cassa unica in EUR**, conversione automatica con costo |
| 10 | Scadenza segnale | **3 sedute** in coda, poi si scarta |
| 11 | Commissioni | **0,19% minimo 2,95 €**, cambio **0,25%** |

---

## 1. Glossario

| termine | significato preciso |
|---|---|
| **portafoglio** | capitale virtuale separato, con proprie regole e proprie posizioni |
| **posizione** | titolo posseduto ora, con quantità, prezzo d'ingresso e stop |
| **operazione** | una posizione chiusa: ingresso, uscita, motivo, profitto |
| **coda** | segnali d'acquisto validi ma non ancora eseguiti per mancanza di cassa |
| **scarto** | decisione di *non* comprare, registrata con il motivo |
| **motore** | il programma che ogni 15 minuti valuta uscite e ingressi |
| **analisi finale** | quella prodotta dopo la chiusura (18:43), con barre giornaliere complete |
| **analisi intraday** | quella lanciata a mano durante la seduta: **non genera ingressi** |
| **R** | rischio iniziale dell'operazione in euro (= quantità × distanza dallo stop) |
| **snapshot** | valore del portafoglio fotografato a fine giornata |

---

## 2. Modello dei dati

### 2.1 Portafoglio

| campo | tipo | esempio | note |
|---|---|---|---|
| `id` | testo | `bilanciato_2026` | immutabile |
| `nome` | testo | `Bilanciato 2026` | modificabile |
| `valuta_base` | testo | `EUR` | per ora sempre EUR |
| `capitale_iniziale` | numero | `10000.00` | definito alla creazione |
| `liquidita` | numero | `8234.12` | in EUR, aggiornata a ogni operazione |
| `stato` | testo | `attivo` / `in_pausa` / `archiviato` | in pausa: non compra, continua a vendere |
| `creato` | data-ora | `2026-10-17T18:00:00` | |
| `note` | testo | `Prova con stop su ATR` | libero |

### 2.2 Parametri (uno per portafoglio)

| campo | tipo | default | significato |
|---|---|---|---|
| `rischio_per_operazione_pct` | numero | `1.0` | quanto capitale rischiare, dal prezzo allo stop |
| `max_per_titolo_pct` | numero | `10.0` | tetto di capitale su un singolo titolo |
| `max_posizioni` | intero | `12` | quante posizioni aperte insieme |
| `esposizione_max_pct` | numero | `90.0` | oltre non si compra (100 − riserva) |
| `riserva_liquidita_pct` | numero | `10.0` | cassa che non si tocca mai |
| `stop_atr_mult` | numero | `2.0` | stop = ingresso − ATR × questo |
| `stop_min_pct` | numero | `1.5` | stop mai più stretto di così |
| `stop_max_pct` | numero | `15.0` | stop mai più largo di così |
| `trailing_atr_mult` | numero | `2.0` | stop dinamico; `0` = disattivato |
| `obiettivo_pct` | numero | `15.0` | take profit |
| `rischio_ammesso` | lista | `["NORMALE","TESO"]` | quali livelli di rischio accettare |
| `tech_score_min` | numero | `75` | punteggio minimo |
| `ingressi_da` | lista | `["ENTRA"]` | quali indicazioni generano acquisti |
| `scadenza_segnale_sedute` | intero | `3` | dopo quante sedute il segnale scade |
| `uscita_tempo_sedute` | intero | `30` | uscita dopo N sedute senza risultato; `0` = mai |
| `max_nuove_posizioni_giorno` | intero | `3` | per non aprire dieci posizioni in un giro |
| `rotazione` | booleano | `false` | spenta |
| `liquidita_minima_ordine_eur` | numero | `300.0` | sotto questa cifra non vale la pena (minimo 2,95 € pesa troppo) |

### 2.3 Posizione aperta

| campo | esempio | note |
|---|---|---|
| `id` | `pos_0007` | progressivo |
| `ticker` | `ENI.MI` | |
| `mercato` | `MIB30` | per gli ingressi futuri |
| `valuta` | `EUR` | valuta dello strumento |
| `data_ingresso` / `ora_ingresso` | `2026-10-20` / `10:15:00` | |
| `prezzo_ingresso` | `25.9550` | al netto dello slippage, come eseguito |
| `quantita` | `38` | interi, niente frazioni |
| `importo_investito_eur` | `986.29` | prezzo × quantità × cambio + commissioni |
| `commissione_ingresso_eur` | `2.95` | |
| `imposta_tobin_eur` | `0.99` | solo azioni italiane |
| `stop_iniziale` | `23.9000` | non cambia mai |
| `stop_attuale` | `24.3500` | sale con il trailing, non scende mai |
| `obiettivo` | `29.8500` | |
| `atr_ingresso` | `0.9800` | ATR al momento dell'ingresso |
| `rischio_iniziale_eur` | `78.09` | quantità × (ingresso − stop_iniziale) |
| `motivo_ingresso` | `segnale ENTRA · TECH 93 · rischio NORMALE` | |
| `analisi_riferimento` | `MIB30_TA_Analyses.xlsx · 2026-10-16` | **obbligatorio**: senza non si spiega nulla fra sei mesi |
| `manuale` | `false` | `true` se aperta da te |

### 2.4 Operazione chiusa

Tutti i campi della posizione, più:

| campo | esempio | note |
|---|---|---|
| `data_uscita` / `ora_uscita` | `2026-10-27` / `15:30:00` | |
| `prezzo_uscita` | `24.1000` | al netto dello slippage |
| `motivo_uscita` | `stop` | `stop` / `obiettivo` / `trailing` / `segnale` / `tempo` / `manuale` |
| `commissioni_totali_eur` | `5.90` | ingresso + uscita |
| `pnl_lordo_eur` | `-70.49` | prima dei costi |
| `pnl_netto_eur` | `-77.38` | dopo commissioni, Tobin e cambio |
| `pnl_pct` | `-7.15` | sul capitale investito |
| `r_multiplo` | `-0.99` | `pnl_netto / rischio_iniziale` |
| `giorni_detenuti` | `7` | |
| `prezzo_fonte` | `yahoo · ritardo possibile 15 min` | **dichiarato sempre** |

### 2.5 Voce di coda (segnale non eseguito)

`ticker`, `mercato`, `segnale` (`ENTRA`), `tech_score`, `rilevato_il`, `sedute_in_coda`, `stato` (`in_attesa` / `eseguito` / `scaduto` / `scartato`), `motivo_scarto`.

### 2.6 Scarto

`data-ora`, `ticker`, `motivo`, `dettaglio`. Motivi previsti: `cassa_insufficiente`, `limite_posizioni`, `esposizione_massima`, `rischio_non_ammesso`, `tech_score_basso`, `prezzo_stantio`, `gia_in_posizione`, `limite_giornaliero`.

### 2.7 Snapshot giornaliero

`data`, `valore_totale_eur`, `liquidita_eur`, `esposizione_eur`, `esposizione_pct`, `num_posizioni`, `pnl_giorno_eur`, `pnl_totale_eur`, `drawdown_pct`.

---

## 3. Formato dei file

```
analyses/portafogli/
├── bilanciato_2026.json              configurazione + posizioni aperte + coda
├── bilanciato_2026_operazioni.jsonl  una riga per operazione chiusa (append-only)
├── bilanciato_2026_storico.jsonl     uno snapshot per giorno (append-only)
├── bilanciato_2026_scarti.jsonl      decisioni di non comprare (append-only)
└── bilanciato_2026.lock              lock del motore
```

**Perché `jsonl` append-only per operazioni, storico e scarti**: quei dati non si
riscrivono mai. Un file riscritto può corrompersi a metà scrittura e perdere tutto
lo storico; un file a cui si aggiungono righe, no. Il `.json` del portafoglio è
l'unico riscritto, ed è quello meno prezioso (posizioni ricostruibili dalle
operazioni).

Esempio di `bilanciato_2026.json`:

```json
{
  "id": "bilanciato_2026",
  "nome": "Bilanciato 2026",
  "valuta_base": "EUR",
  "capitale_iniziale": 10000.0,
  "liquidita": 8234.12,
  "stato": "attivo",
  "creato": "2026-10-17T18:00:00",
  "parametri": {
    "rischio_per_operazione_pct": 1.0,
    "max_per_titolo_pct": 10.0,
    "max_posizioni": 12,
    "esposizione_max_pct": 90.0,
    "riserva_liquidita_pct": 10.0,
    "stop_atr_mult": 2.0,
    "stop_min_pct": 1.5,
    "stop_max_pct": 15.0,
    "trailing_atr_mult": 2.0,
    "obiettivo_pct": 15.0,
    "rischio_ammesso": ["NORMALE", "TESO"],
    "tech_score_min": 75,
    "ingressi_da": ["ENTRA"],
    "scadenza_segnale_sedute": 3,
    "uscita_tempo_sedute": 30,
    "max_nuove_posizioni_giorno": 3,
    "rotazione": false,
    "liquidita_minima_ordine_eur": 300.0
  },
  "posizioni": [],
  "coda": [],
  "ultimo_giro": "2026-10-17T18:00:00",
  "analisi_finale_usata": "MIB30_TA_Analyses.xlsx · 2026-10-16"
}
```

---

## 4. Formule

### 4.1 Costi

```
slippage      = 0,05%  (acquisto: prezzo × 1,0005 · vendita: prezzo × 0,9995)
commissione   = max(2,95 €; 0,19% × importo)          su acquisto E vendita
tobin         = 0,10% × importo                        solo acquisto, solo azioni italiane
cambio        = 0,25% × importo                        solo strumenti non in EUR
```

### 4.2 Dimensionamento

```
rischio_eur    = capitale_totale × rischio_per_operazione_pct / 100
distanza_stop  = prezzo_ingresso − stop_iniziale
quantita_rischio = floor(rischio_eur / distanza_stop)

tetto_titolo   = capitale_totale × max_per_titolo_pct / 100
quantita_tetto = floor(tetto_titolo / (prezzo_ingresso × cambio))

cassa_libera   = liquidita − capitale_totale × riserva_liquidita_pct / 100
quantita_cassa = floor(cassa_libera / (prezzo_ingresso × cambio × 1,0019))

quantita       = min(quantita_rischio, quantita_tetto, quantita_cassa)
```

Se `quantita × prezzo < liquidita_minima_ordine_eur` → **si scarta** con motivo
`ordine_troppo_piccolo` (con 2,95 € di minimo, un ordine da 200 € costa l'1,5%).

### 4.3 Stop e obiettivo

```
stop_iniziale = prezzo_ingresso − ATR × stop_atr_mult
stop_iniziale = max(stop_iniziale, prezzo_ingresso × (1 − stop_max_pct/100))
stop_iniziale = min(stop_iniziale, prezzo_ingresso × (1 − stop_min_pct/100))
obiettivo     = prezzo_ingresso × (1 + obiettivo_pct/100)
```

Le due correzioni servono a impedire stop assurdi: un ATR enorme non deve
significare rischio del 40%, e un ATR minuscolo non deve mettere lo stop dentro il
rumore.

### 4.4 Stop dinamico

```
stop_attuale = max(stop_attuale, prezzo_corrente − ATR × trailing_atr_mult)
```

Non scende mai. Vale solo se `trailing_atr_mult > 0`.

### 4.5 Risultato

```
pnl_lordo   = (prezzo_uscita − prezzo_ingresso) × quantita × cambio_uscita
pnl_netto   = pnl_lordo − commissioni_acquisto − commissioni_vendita − tobin − costi_cambio
pnl_pct     = pnl_netto / importo_investito_eur × 100
r_multiplo  = pnl_netto / rischio_iniziale_eur
```

### 4.6 Valore e drawdown

```
valore_totale = liquidita + Σ (quantita × prezzo_corrente × cambio_a_eur)
drawdown_pct  = (valore_totale − massimo_storico) / massimo_storico × 100
```

### 4.7 Statistiche

```
win_rate      = operazioni_in_guadagno / operazioni_totali
profit_factor = somma_guadagni / |somma_perdite|
expectancy    = win_rate × guadagno_medio − (1 − win_rate) × perdita_media
CAGR          = (valore_finale / capitale_iniziale)^(365 / giorni) − 1
```

---

## 5. Il motore: cosa fa a ogni giro

### 5.1 Ordine delle operazioni

```
 1. Il lock è libero? no → esci (un altro giro è in corso)
 2. Prendi il lock
 3. Oggi è giorno di mercato? no → esci
 4. Carica l'analisi FINALE più recente (ignora le intraday)
 5. Per ogni portafoglio attivo:
      a. quotazioni dei titoli in posizione + dei candidati
      b. ESCE: stop → trailing → obiettivo → segnale → tempo → manuale
      c. AGGIORNA gli stop dinamici
      d. ENTRA: candidati in coda, in ordine di priorità, finché c'è cassa
      e. Snapshot di fine giornata (una volta al giorno)
 6. Rilascia il lock, scrivi una riga di log
```

**Perché le uscite prima degli ingressi**: vendere libera la cassa che serve a
comprare, nello stesso giro.

### 5.2 Condizioni di ingresso (tutte obbligatorie)

1. indicazione = `ENTRA` da **analisi finale** (le intraday sono escluse)
2. `TECH_SCORE` ≥ `tech_score_min`
3. `Rischio_Trend` ∈ `rischio_ammesso`
4. `Liquidity` = `OK`
5. quotazione più vecchia di 30 minuti → **no**
6. portafoglio `attivo`, posizioni < `max_posizioni`, esposizione < `esposizione_max_pct`
7. titolo non già in portafoglio
8. nuove posizioni oggi < `max_nuove_posizioni_giorno`
9. `quantita` calcolata > 0 e importo ≥ `liquidita_minima_ordine_eur`
10. fascia oraria compatibile col mercato del titolo (vedi 5.5)

### 5.3 Ordine di priorità dei candidati

`TECH_SCORE` decrescente → `ADX` decrescente → rischio `NORMALE` prima di `TESO` → ticker
in ordine alfabetico (per rendere il risultato ripetibile a parità di punteggio).

### 5.4 Condizioni di uscita, in ordine di priorità

| # | condizione | motivo registrato |
|---|---|---|
| 1 | prezzo ≤ `stop_attuale` | `stop` |
| 2 | prezzo ≥ `obiettivo` | `obiettivo` |
| 3 | indicazione `EVITA`, o momento `CALANTE`, o fase `RIBASSO` | `segnale` |
| 4 | sedute in posizione ≥ `uscita_tempo_sedute` (se > 0) | `tempo` |
| 5 | richiesta manuale | `manuale` |

L'ordine non è casuale: **prima si protegge il capitale, poi si incassa, solo dopo
si aspetta ancora**.

### 5.5 Fascia oraria e mercato

| fascia | orario | titoli trattabili |
|---|---|---|
| 1 | 9:30–18:00 | tutti (Borsa Italiana 9:00–17:30; USA apre 15:30) |
| 2 | 18:00–22:00 | **solo** titoli USA (`US_Others` o valuta USD) |

Fuori fascia il motore non apre posizioni; **le uscite restano possibili solo in
fascia** (fuori non c'è prezzo affidabile). Uno stop che scatta fuori orario viene
eseguito **alla prima quotazione valida della fascia successiva**: è un limite
dichiarato, e va scritto nell'interfaccia.

### 5.6 Guardie

| situazione | comportamento |
|---|---|
| quotazione assente o ferma | salta il titolo, registra `prezzo_stantio` |
| errore su un titolo | non ferma il giro, annota e prosegue |
| analisi finale con più di 5 sedute | **nessun nuovo ingresso** (uscite sì) |
| mercato chiuso / festivo | giro saltato, nessun costo |
| giro precedente ancora in corso | giro saltato dal lock |
| titolo sospeso | nessun prezzo valido, salta |

---

## 6. Cron e script

### 6.1 Righe da aggiungere (proposta, da applicare solo su tua conferma)

```cron
# Portafoglio virtuale — ogni 15 minuti nei giorni feriali
30,45 9 * * 1-5    /home/pi/PycharmProjects/IFinancev4React-sicilia26/portafoglio.sh
*/15 10-17 * * 1-5 /home/pi/PycharmProjects/IFinancev4React-sicilia26/portafoglio.sh
0 18 * * 1-5       /home/pi/PycharmProjects/IFinancev4React-sicilia26/portafoglio.sh
*/15 18-21 * * 1-5 /home/pi/PycharmProjects/IFinancev4React-sicilia26/portafoglio.sh
0 22 * * 1-5       /home/pi/PycharmProjects/IFinancev4React-sicilia26/portafoglio.sh
```

51 esecuzioni al giorno. Lo script:

1. prende il lock (`flock`), se non lo prende esce in silenzio
2. chiama l'endpoint del motore (`/api/portafogli/esegui`)
3. scrive **una riga** nel log del portafoglio: data, giri, uscite, ingressi, valore
4. rilascia il lock

**Il log va ruotato** (giornaliero, 7 giorni): il cron dell'analisi ha già prodotto
un file da 1,3 GB senza rotazione, e questo gira 51 volte al giorno.

**Il cron dell'analisi non si tocca.**

### 6.2 Trigger manuale dell'analisi

- pulsante **"Analizza ora"** con scelta del mercato (MIB30 = 45 titoli in ~1 minuto; ETF = 1684 in ~15 minuti)
- se un'analisi è già in corso, il pulsante è disabilitato con il motivo
- l'analisi prodotta è marcata **`intraday: true`** in un file di stato
- **il motore ignora le analisi intraday per gli ingressi** (le uscite no)
- l'interfaccia lo scrive: *"analisi intraday — non usata per comprare"*

**Perché è necessario**: a metà seduta la barra giornaliera è incompleta, le
indicazioni possono cambiare e tornare indietro alla sera. Se il motore comprasse
su un'analisi intraday, comprerebbe su un segnale che alle 18:43 non esiste più,
pagando due volte le commissioni.

---

## 7. Interfaccia

### 7.1 Nuova tab `💼 Portafogli`

**Elenco** — una card per portafoglio:

```
Bilanciato 2026                    attivo
10.412 €   +4,12%                  6 posizioni · 1.980 € liquidi
Drawdown  −3,2%     Ultimo giro 15:45:03     [ Apri ]
```

**Dettaglio** — quattro sezioni a schede:

| scheda | contenuto |
|---|---|
| **Posizioni** | tabella: titolo, quantità, ingresso, prezzo ora, P/L € e %, **distanza dallo stop in %**, giorni, [Vendi] |
| **Operazioni** | storico chiuso: date, prezzi, motivo, P/L, R, giorni |
| **Curva** | valore nel tempo + drawdown + confronto con FTSEMIB |
| **Regole** | i parametri, modificabili (con conferma: cambiano il comportamento da subito) |

**Pulsanti di testata**: `Investi` (cerca titolo), `Analizza ora`, `Pausa`, `Chiudi tutto`.

### 7.2 Pulsante `Investi` sulle righe

Accanto a `+ Monitor` in Highlights, Schede e Lista. Apre un pannello con:

- titolo, prezzo ora, indicazione, TECH
- **quantità calcolata** e importo, con la spiegazione: *"1% di 10.400 € = 104 € di
  rischio; stop a 23,90 (−6,2%) → 42 azioni = 1.090 €"*
- stop, obiettivo, **perdita massima in euro**
- quale portafoglio (se ne hai più di uno)
- avviso: *"esecuzione al prezzo che l'app vede adesso (possibile ritardo 15 minuti)"*

### 7.3 Pannello "Stato motore"

Nella tab Portafogli, in alto: ultimo giro, prossimo giro previsto, eventuali giri
saltati con il motivo (*"prezzi fermi"*, *"lock occupato"*), e un interruttore
globale che ferma tutti i portafogli.

---

## 8. Multivaluta

- una sola cassa, **in EUR**
- lo strumento ha il suo prezzo in valuta nativa (USD, GBP)
- **acquisto**: `euro_spesi = quantità × prezzo × cambio × (1 + 0,0025)`
- **vendita**: `euro_incassati = quantità × prezzo × cambio × (1 − 0,0025)`
- il cambio applicato è quello **del momento dell'operazione**, e viene **registrato**
- il P/L mostrato è quindi **sempre al netto del cambio**, il che è ciò che conta

---

## 9. Casi limite dichiarati (limiti noti, da non nascondere)

| caso | comportamento in fase 1 | quando si risolve |
|---|---|---|
| **Ritardo dei prezzi** | esecuzione al prezzo visto, dichiarato | non si risolve: è un simulatore |
| **Stop toccato intraday** | valutato sull'ultimo prezzo, non sul minimo della seduta | fase 2 con minimo/massimo |
| **Dividendi** | **non conteggiati**: il rendimento è sottostimato | fase 2 (`actions=True` da yahoo) |
| **Frazionamenti** | rilevati e corretti (quantità e prezzo) | fase 2 |
| **Titoli usciti dall'analisi** | restano in portafoglio, gestiti col prezzo | — |
| **Tasse sul capital gain** | **non applicate** (solo Tobin sull'acquisto) | dichiarato, non simulato |
| **Titolo sospeso o delistato** | nessun prezzo → posizione congelata, segnalata | manuale |
| **Festivi** | giro saltato automaticamente | — |

Ogni limite è mostrato **nell'interfaccia**, non solo qui: un numero senza la sua
avvertenza è una bugia.

---

## 10. Criteri di accettazione per fase

| fase | contenuto | si considera fatta quando |
|---|---|---|
| **1** | portafoglio, compra/vendita manuale, P/L, costi, multivaluta | compro 3 titoli (uno in USD), vedo P/L al netto dei costi, chiudo e i conti tornano a mano |
| **2** | uscite automatiche: stop, obiettivo, trailing, tempo | lo stop scatta da solo, il motivo è registrato, il P/L coincide col prezzo di esecuzione |
| **3** | ingressi automatici da segnale + coda + scarti | il motore compra da solo rispettando i limiti e so perché ha scartato ogni candidato |
| **4** | metriche, curva, drawdown, benchmark, confronto fra portafogli | posso dire "il Bilanciato ha fatto meglio del Conservativo" con numeri difendibili |

Ogni fase è utilizzabile da sola. **La fase 1 ha già valore.**

---

## 11. Le regole che non cambieranno mai

1. **Nessun look-ahead**: si compra solo con segnali già pubblicati.
2. **Nessun numero senza la sua fonte**: ogni operazione registra prezzo, ora e analisi usata.
3. **Nessun dato nascosto**: i limiti (ritardo, dividendi, tasse) sono scritti dove si leggono i numeri.
4. **Prima si esce, poi si entra.**
5. **Il capitale si protegge prima di guadagnare**: stop su ATR, stop solo in salita, riserva di cassa intoccabile.
