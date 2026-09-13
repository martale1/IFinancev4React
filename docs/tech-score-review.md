# TECH_SCORE - definizione, revisione e validazione

## Stato del documento

- Stato: formula v2.1 implementata, da validare con una nuova analisi
- Ambito: solo `TECH_SCORE`
- Formula applicativa: v2 a scala fissa; formula precedente conservata come `calculate_technical_score_legacy()`
- Obiettivo: decidere cosa deve misurare il punteggio prima di modificarne il calcolo

## 1. Domanda a cui deve rispondere

Proposta iniziale:

> Quanto e' favorevole oggi il contesto tecnico di un titolo per valutare un nuovo ingresso long con orizzonte indicativo di 5-20 sedute?

Il punteggio deve quindi rappresentare la **qualita' tecnica attuale del setup long**, non un ordine di acquisto e non la probabilita' garantita di un rialzo.

Interpretazione desiderata:

| Intervallo | Significato proposto |
|---|---|
| 0-24 | Contesto tecnico nettamente sfavorevole |
| 25-44 | Contesto debole o deteriorato |
| 45-54 | Contesto neutrale o privo di vantaggio evidente |
| 55-69 | Contesto costruttivo, ma non necessariamente pronto |
| 70-84 | Setup tecnicamente forte |
| 85-100 | Forza molto elevata; verificare anche rischio di eccesso |

Queste fasce sono provvisorie e dovranno essere validate sui rendimenti futuri.

## 2. Cosa non deve misurare

`TECH_SCORE` non deve sostituire:

- `Market_Phase`, che descrive la fase: trend, range, pullback o rischio di inversione;
- `Entry_Signal`, che sintetizza se valutare un ingresso adesso;
- liquidita', rischio, stop loss e rapporto rischio/rendimento;
- livelli AI o condizioni di attivazione di un alert;
- valutazione fondamentale o previsione del valore dell'azienda.

Un titolo puo' avere TECH alto ma essere troppo esteso. Puo' anche avere TECH medio in un pullback interessante. Il punteggio deve descrivere la qualita' tecnica, mentre la decisione operativa deve considerare anche fase, rischio e prezzo d'ingresso.

## 3. Cosa misura oggi

La formula corrente e' in `TechnicalAnalyzer.calculate_technical_score()` e combina:

| Componente | Peso corrente | Informazione principale |
|---|---:|---|
| MACD | 18% | Momentum e direzione |
| RSI | 12% | Forza relativa e trend RSI |
| Stocastico | 10% | Momentum rapido e aree estreme |
| MA trend | 12% | Struttura prezzo, EMA30 ed EMA50 |
| Volume | 8% | Volume corrente sopra la propria media mobile |
| SAR | 6% | Posizione del SAR rispetto al prezzo |
| Performance 5D | 6% | Accelerazione recente del prezzo |
| Alligator | 8% | Ordine delle linee e posizione del prezzo |
| Signal6 | 12% | Stato sintetico dell'Alligator |
| ADX | 12% | Forza e direzione del trend |
| ATR | 6% | Regime di volatilita' |

I pesi vengono normalizzati automaticamente a somma 100%.

## 4. Problemi rilevati nella formula corrente

### 4.1 Normalizzazione relativa al singolo titolo

Il risultato grezzo viene trasformato in 0-100 usando minimo e massimo presenti nella serie storica elaborata:

```text
(score - minimo_della_serie) / (massimo_della_serie - minimo_della_serie) * 100
```

Conseguenze:

- TECH 80 di un titolo non e' necessariamente confrontabile con TECH 80 di un altro;
- il valore puo' cambiare se cambia la profondita' dello storico;
- le soglie assolute 65 e 35 non hanno un significato stabile;
- un titolo strutturalmente debole puo' ottenere un valore alto rispetto alla propria storia recente.

### 4.2 Duplicazione del momentum

MACD, RSI, stocastico, performance 5D, Alligator e Signal6 contengono informazioni in parte correlate. Nel campione MIB30 osservato il TECH corrente ha correlazione circa `0,84` con RSI.

Il rischio e' contare piu' volte lo stesso movimento, facendo sembrare il punteggio piu' completo di quanto sia realmente.

### 4.3 Mescolanza di qualita', direzione e rischio

La formula somma elementi diversi:

- direzione del trend;
- forza del trend;
- momentum;
- conferma dei volumi;
- volatilita';
- condizioni di ipercomprato o ipervenduto.

Un singolo numero rende difficile capire se un valore alto deriva da una struttura solida, da accelerazione recente o da un movimento gia' troppo esteso.

### 4.4 Asimmetria rialzista

Molti componenti assegnano punti quando la condizione e' rialzista, ma non sempre applicano una penalita' simmetrica quando e' ribassista. Il punto neutrale del punteggio non e' quindi definito in modo esplicito.

### 4.5 Soglie non ancora validate

Le soglie operative correnti `TECH_SCORE >= 65` e `TECH_SCORE <= 35` sono scelte di configurazione. Non risulta ancora documentata una validazione che dimostri differenze consistenti nei rendimenti futuri tra le fasce.

## 5. Modello concettuale implementato

Prima di scegliere una nuova formula, il TECH dovrebbe essere diviso logicamente in quattro dimensioni. Le dimensioni possono restare visibili internamente anche se la UI mostra un solo totale.

| Dimensione | Domanda | Indicatori candidati |
|---|---|---|
| Struttura | Il prezzo e' inserito in una struttura rialzista ordinata? | Prezzo/EMA30/EMA50, Alligator |
| Momentum | Il movimento sta migliorando o peggiorando? | MACD histogram, RSI trend, stocastico |
| Forza e partecipazione | Il movimento e' sostenuto? | ADX e DI, volume relativo |
| Rischio di estensione | Il titolo e' gia' troppo esteso o volatile? | Distanza da EMA, ATR%, RSI/Stoch estremi |

Composizione implementata:

```text
TECH = 35% Struttura + 35% Momentum + 30% Partecipazione - Penalita' di estensione
```

Le prime tre dimensioni hanno scala fissa 0-100. La penalita' ha scala 0-20. Il totale viene limitato all'intervallo 0-100 e non dipende dal minimo e massimo storico del titolo.

### 5.1 Struttura, peso 35% - revisione v2.1

La v2.1 usa la media di sei distanze percentuali continue:

- prezzo rispetto a EMA30, scala completa a +/-6%;
- EMA30 rispetto a EMA50, scala completa a +/-6%;
- Lips rispetto a Teeth, scala completa a +/-3%;
- Teeth rispetto a Jaw, scala completa a +/-3%;
- prezzo rispetto alla media delle tre linee Alligator, scala completa a +/-6%;
- prezzo rispetto al SAR, scala completa a +/-6%.

Per ogni relazione una distanza pari a zero vale 50. Una distanza positiva aumenta gradualmente il valore fino a 100; una negativa lo riduce gradualmente fino a 0. Oltre la scala completa il valore viene limitato a 0 o 100. Un dato mancante viene escluso dalla media; se mancano tutti i dati, la dimensione vale 50.

Questa revisione sostituisce i precedenti voti binari e non cambia il peso complessivo del 35%.

### 5.2 Momentum, peso 35%

Media di quattro gruppi per ridurre la duplicazione:

- gruppo MACD: MACD sopra Signal e trend istogramma Up;
- gruppo RSI: livello RSI lineare tra 30=0, 50=50 e 70=100, mediato con il trend RSI;
- gruppo stocastico: K sopra D;
- performance 5D: scala lineare, con 0%=50, +10%=100 e -10%=0.

### 5.3 Partecipazione, peso 30%

- 70% direzione e forza ADX/DI;
- 30% volume rispetto alla MA20.

Con ADX debole la componente DI resta vicina a 50. Al crescere di ADX si sposta verso 100 se `+DI >= -DI` e verso 0 nel caso opposto. Il volume vale 50 quando e' in linea con la MA20, 100 a +20% o oltre e 0 a -20% o meno.

### 5.4 Penalita' di estensione, massimo 20 punti

- fino a 8 punti per distanza del prezzo da EMA30 oltre il 4%;
- fino a 5 punti per ATR% oltre il 3%;
- fino a 4 punti per RSI oltre 70;
- fino a 3 punti per Stoch K oltre 80.

La penalita' viene sottratta dopo aver calcolato la qualita' tecnica. In questo modo un movimento forte resta riconoscibile, ma il totale segnala il rischio di inseguire un prezzo gia' esteso.

### 5.5 Colonne diagnostiche

Ogni analisi genera:

- `TECH_STRUCTURE`;
- `TECH_MOMENTUM`;
- `TECH_PARTICIPATION`;
- `TECH_EXTENSION_PENALTY`;
- `TECH_SCORE`.

I quattro valori diagnostici sono visibili nei dettagli della vista tabellare.

## 6. Principi per la nuova formula

1. **Confrontabilita'**: lo stesso valore deve avere lo stesso significato tra titoli e mercati.
2. **Stabilita'**: aggiungere dati storici non deve riscrivere retroattivamente il significato della scala.
3. **Spiegabilita'**: deve essere possibile mostrare il contributo delle quattro dimensioni.
4. **Informazione non duplicata**: indicatori molto correlati non devono pesare come segnali indipendenti.
5. **Neutralita' esplicita**: 50 deve rappresentare un contesto realmente neutrale.
6. **Penalita' separate**: forza rialzista ed eccesso rialzista non sono la stessa cosa.
7. **Dati mancanti**: un indicatore assente non deve diventare automaticamente un segnale negativo o positivo.
8. **Nessuna dipendenza circolare**: TECH non deve usare `Market_Phase`, `Action` o `Entry_Signal` se questi usano a loro volta TECH.

## 7. Come validarlo

La validazione deve usare dati fuori campione e prevenire il look-ahead bias.

Per ogni data storica e titolo si registrano:

- TECH e contributi delle dimensioni;
- rendimento futuro a 5, 10 e 20 sedute;
- massimo rialzo e massimo ribasso nelle 20 sedute successive;
- mercato e regime generale;
- liquidita' disponibile in quella data.

Controlli minimi:

1. rendimento futuro mediano per fascia TECH;
2. percentuale di rendimenti positivi per fascia;
3. drawdown futuro mediano e percentile 90;
4. monotonicita': fasce TECH maggiori dovrebbero produrre risultati progressivamente migliori;
5. stabilita' tra MIB30, ETF, ETC, DAX e altri mercati;
6. confronto contro baseline semplici: RSI, prezzo sopra EMA50 e rendimento 5D;
7. verifica che TECH aggiunga informazione rispetto a `Market_Phase`.

## 8. Decisioni da prendere prima del codice

- [x] Confermare che l'obiettivo sia un setup **long** a 5-20 sedute.
- [x] TECH misura qualita' tecnica; non dichiara direttamente una probabilita' di rendimento positivo.
- [x] Mantenere il totale e registrare anche i quattro sottopunteggi.
- [x] Escludere il dato mancante dal sottopunteggio e usare 50 se manca tutta la dimensione.
- [ ] Stabilire se le soglie debbano essere uguali per tutti i mercati.
- [ ] Scegliere l'orizzonte principale di validazione: 5, 10 o 20 sedute.
- [ ] Definire quale drawdown futuro sia accettabile per una fascia alta.

## 9. Sequenza di lavoro

1. Approvare la definizione nella sezione 1.
2. Inventariare precisamente ogni contributo della formula corrente.
3. Calcolare ridondanze e distribuzioni su dati storici.
4. Disegnare la formula candidata con intervalli fissi.
5. Eseguire un confronto storico tra formula corrente, nuova formula e baseline.
6. Scegliere soglie e nomi delle fasce dai risultati, non a priori.
7. Solo dopo, modificare il calcolo applicativo e aggiornare la UI.

## 10. Registro decisioni

| Data | Decisione | Motivazione |
|---|---|---|
| 2026-09-13 | Avviata revisione separata del solo TECH_SCORE | Evitare di cambiare contemporaneamente Segnale e Scenario |
| 2026-09-13 | Definito TECH come qualita' tecnica long a 5-20 sedute | Rendere esplicito e verificabile lo scopo del punteggio |
| 2026-09-13 | Rimossa la normalizzazione min-max per titolo | Rendere confrontabili valori e soglie |
| 2026-09-13 | Introdotti quattro sottopunteggi | Separare qualita', partecipazione e rischio di estensione |
| 2026-09-13 | Resa graduale la componente Struttura | Eliminare i salti discreti e misurare l'intensita' della struttura |

## 11. Prima esecuzione v2 - MIB30

Esecuzione del 2026-09-13 su 42 titoli.

### Distribuzione

| Statistica | TECH v2 |
|---|---:|
| Minimo | 12,61 |
| Percentile 25 | 29,01 |
| Mediana | 40,77 |
| Media | 45,36 |
| Percentile 75 | 64,71 |
| Massimo | 79,73 |

| Fascia | Titoli |
|---|---:|
| 0-24 | 7 |
| 25-44 | 15 |
| 45-54 | 5 |
| 55-69 | 8 |
| 70-84 | 7 |
| 85-100 | 0 |

La nuova scala non forza piu' artificialmente minimo e massimo a 0 e 100. La soglia 65 seleziona una parte ristretta del campione, mentre la fascia 85-100 non viene raggiunta in questa esecuzione.

### Sottopunteggi

| Componente | Media | Min | Max |
|---|---:|---:|---:|
| Struttura | 40,48 | 0 | 100 |
| Momentum | 53,75 | 10,51 | 91,46 |
| Partecipazione | 42,80 | 0 | 85,29 |
| Penalita' estensione | 0,46 | 0 | 7,62 |

La penalita' massima osservata e' `7,62` su LTMC.MI. Il limite teorico di 20 non viene avvicinato nel campione corrente; prima di modificarlo servono altre esecuzioni e dati storici.

### Relazioni osservate

- correlazione TECH/Struttura: `0,92`;
- correlazione TECH/Momentum: `0,82`;
- correlazione TECH/Partecipazione: `0,70`;
- correlazione TECH/RSI: `0,90`;
- correlazione TECH/performance 5D: `0,66`.

La forte correlazione con RSI non e' stata ridotta dalla v2. Il primo elemento da riesaminare e' la componente Struttura: usa condizioni binarie molto nette ed e' a sua volta correlata `0,89` con RSI nel campione. Non si modificano ancora soglie o pesi finche' non viene definita una struttura piu' graduale e meno ridondante.

### Primi titoli per TECH v2

| Ticker | TECH | Struttura | Momentum | Partecipazione | Penalita' |
|---|---:|---:|---:|---:|---:|
| BMPS.MI | 79,73 | 80 | 89,90 | 67,53 | 0 |
| MB.MI | 78,86 | 80 | 88,96 | 65,75 | 0 |
| ENI.MI | 78,13 | 100 | 71,63 | 60,20 | 0 |
| G.MI | 78,04 | 100 | 86,53 | 45,17 | 0,80 |
| A2A.MI | 77,76 | 80 | 90,07 | 65,00 | 1,26 |

### Valutazione provvisoria

- **Confermato**: la scala e' ora confrontabile e indipendente dalla lunghezza dello storico.
- **Confermato**: i sottopunteggi rendono leggibile l'origine del totale.
- **Corretto nella v2.1, da rivalidare**: la Struttura discreta (`0, 20, 40, ... 100`) e' stata sostituita con distanze percentuali continue.
- **Da rivedere**: TECH resta troppo vicino a RSI.
- **Da osservare**: la penalita' di estensione e' molto contenuta nel campione corrente.
- **Non ancora valutabile**: capacita' del punteggio di anticipare rendimenti a 5-20 sedute.
