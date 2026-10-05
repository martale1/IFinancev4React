# Specifica — Applicazione multiutente (branch `multiuser`)

Stato: **bozza da approvare**. Nessuna riga di codice è stata scritta o modificata.
Base: branch `multiuser` @ `f2d77a0` (identico a `Cusago2026_temp`).
Data: 2026-10-05.

---

## 1. Obiettivo

Rendere l'applicazione utilizzabile da **più persone**, con dati separati, un
amministratore che gestisce gli accessi, e tracciamento di chi entra e cosa fa.

Fuori perimetro (per ora): esposizione pubblica su internet, pagamenti,
autenticazione a due fattori, accesso con account Google/Apple.

**Scala prevista**: fino a **una ventina di utenti**. Incide sulle scelte:
nessuna paginazione del registro attività, backup giornaliero sufficiente,
un solo elaboratore basta.

---

## 2. Ruoli

| Ruolo | Chi | Può |
|---|---|---|
| **Admin** | tu | tutto: creare/sospendere/eliminare utenti, vedere il registro attività, rigenerare le analisi, usare le funzioni AI, gestire bot e notifiche |
| **Utente** | gli altri | usare watchlist, liste, monitor, alert, notifiche, grafici. **Vede** le funzioni AI ma non può attivarle. Nessun accesso ai dati altrui |

Un solo admin iniziale, creato in fase di installazione. L'admin può promuovere
un utente ad admin (decisione aperta n. 4, §12).

---

## 3. Requisiti richiesti

### R1 — Registrazione autonoma, approvazione dell'admin
L'utente **si registra da solo** indicando **email** e **password** (scelta da lui,
con requisiti minimi di lunghezza). L'email è l'identificativo di accesso ed è unica.

La registrazione **non dà accesso immediato**: l'account nasce in stato
**in attesa di approvazione** e l'admin lo **approva** o lo **rifiuta** dalla sezione
*Utenti*. Serve perché l'app è raggiungibile da chiunque sia sulla rete: senza questo
passaggio, chiunque potrebbe crearsi un account.

L'admin può in ogni caso: **sospendere** (l'utente non entra, i dati restano),
**riattivare**, **reimpostare la password** (procedura assistita, vedi R5) e
**eliminare** con conferma esplicita.

### R2 — Registro delle attività
L'admin vede, per ogni utente: **quando si è collegato**, **da quale indirizzo IP**,
**quando si è disconnesso**, e le **azioni rilevanti** compiute.

Eventi da registrare (proposta, da confermare):
- registrazione richiesta, approvazione, rifiuto, sospensione
- accesso riuscito, accesso fallito, disconnessione, sessione scaduta
- richiesta di reimpostazione password, reimpostazione completata
- creazione/modifica/eliminazione di una lista, di un titolo in monitoraggio, di una nota
- attivazione/disattivazione di un alert e invio di una notifica
- collegamento e scollegamento di Telegram
- avvio di un'analisi o di una scansione (le operazioni pesanti)
- tentativo di usare una funzione riservata all'admin (utile per capire cosa serve agli utenti)

Ogni voce contiene: **data e ora**, utente, indirizzo IP, tipo di azione,
oggetto (per esempio il ticker o il nome della lista), ed esito.
Il registro è **in sola lettura per l'admin**, non modificabile dagli utenti né da loro visibile.

### R3 — Funzioni AI riservate all'admin
**Tutte** le funzioni AI sono per ora riservate all'admin: Chiedi ad AI, ricerca news,
chat AI, alert e livelli generati dall'AI, pulsante AI sulle card.

Gli altri utenti **vedono i pulsanti ma non possono usarli**: disabilitati in modo
visibile, con spiegazione al passaggio del mouse (per esempio *"Funzione riservata
all'amministratore"*). Il divieto è applicato **anche lato server**: se un utente
non admin chiama direttamente l'API, riceve un rifiuto. Nascondere il pulsante non
basta mai.

### R4 — Notifiche personali
Ogni utente attiva le proprie notifiche e **le riceve sul proprio recapito**, non
su quello dell'admin. Le regole di alert sono per utente: quello che attiva un
utente non genera notifiche agli altri.

### R5 — Reimpostazione della password
L'utente che l'ha dimenticata può reimpostarla **da solo**, senza conoscere la
vecchia password. La procedura proposta (vedi §12, decisione aperta n. 2, per il
canale di invio del codice) è a **codice monouso**:

1. L'utente preme *Password dimenticata* e inserisce la propria email.
2. L'app genera un **codice monouso** valido 1 ora e lo mette in evidenza nella
   sezione *Utenti* dell'admin, come **richiesta in sospeso**, insieme all'email.
3. L'admin comunica il codice all'utente con il canale che preferisce (di persona,
   messaggio, telefono). Il codice **non** viene mostrato all'utente nell'app,
   altrimenti chiunque conosca l'email potrebbe reimpostare la password.
4. L'utente inserisce codice e nuova password. Il codice si invalida dopo l'uso.

Resta sempre disponibile la via **assistita**: l'admin imposta una nuova password
temporanea dalla sezione *Utenti* e l'utente la cambia al primo accesso.

**Perché non l'email automatica**: servirebbe un servizio di invio (SMTP) da
configurare e mantenere, e per venti utenti il passaggio dal canale che già usate
è più semplice e non ha costi né credenziali da custodire. Se in futuro vorrai
l'invio automatico, la procedura a codice resta valida e cambia solo il modo in cui
il codice arriva all'utente.

---

## 4. Notifiche Telegram: come farle arrivare a ciascun utente

Questo è il punto tecnicamente più delicato. Telegram offre due strade.

### Opzione A — Un bot dell'applicazione, collegamento per utente (consigliata)

Un **unico bot** (quello che hai già, o uno nuovo dedicato all'app) e un
collegamento una volta sola per utente:

1. L'utente apre la pagina **Notifiche** e preme *Collega Telegram*.
2. L'app mostra un **codice di collegamento** a 6 cifre, valido 15 minuti
   (esempio `K7-2M9`).
3. L'utente apre Telegram, cerca il bot dell'app e invia il codice.
4. Il bot riceve il messaggio, riconosce il codice e **salva il `chat_id`** di
   quell'utente. Da quel momento le sue notifiche vanno lì.
5. L'app conferma: *"Telegram collegato"*, e permette di **scollegare** in qualsiasi momento.

Perché è la strada giusta:
- il **token del bot resta segreto** sul server: nessun utente lo vede né lo può usare;
- l'utente non deve creare un bot né incollare token;
- se un utente blocca il bot, l'invio segnala l'errore e l'app lo mostra nella pagina Notifiche.

### Opzione B — Ogni utente ha il proprio bot
L'utente crea un bot con BotFather e incolla **token** e **chat_id** nell'app.
Funziona e isola completamente i consumi, ma: ogni utente deve saper usare BotFather,
e i token di altri utenti finiscono nel nostro database (da custodire cifrati).

### Cosa farei
**Opzione A**, con la possibilità di aggiungere la B più avanti. Si compone con
il sistema di alert già presente: le regole diventano per utente, e l'invio usa il
`chat_id` del proprietario della regola.

### Punto aperto importante
Se **due utenti attivano la stessa regola** sullo stesso titolo, oggi partirebbero
**due notifiche**. Va deciso (decisione aperta n. 6, §12): notifiche separate
(ognuno la sua, più chiaro) oppure una sola notifica condivisa (meno rumore).

---

## 5. Accesso e sicurezza

- **Ambito**: rete locale (casa). Nessuna esposizione a internet in questa fase.
- **Identificativo di accesso**: **email**, unica per utente. Il **nome visualizzato**
  è separato e serve solo all'interfaccia.
- **Approvazione obbligatoria**: nessun account creato da solo è utilizzabile prima
  che l'admin lo approvi.
- **Password**: mai in chiaro; hash con algoritmo lento (bcrypt/argon2) e sale per utente.
  Requisiti minimi proposti: almeno 10 caratteri.
- **Codici di reimpostazione**: monouso, validi 1 ora, generati in modo casuale e
  conservati **solo come hash** (così chi legge il database non può usarli).
- **Sessione**: cookie firmato, `HttpOnly`, `SameSite=Lax`, con scadenza (proposta: 12 ore)
  e rinnovo a ogni uso. Disconnessione che invalida la sessione lato server.
- **Tentativi di accesso**: blocco temporaneo dopo N tentativi falliti (proposta: 5 in 15 minuti),
  con registrazione nel registro attività. Vale anche per la registrazione e per
  le richieste di reimpostazione, per non permettere di scoprire quali email esistono.
- **Chiavi API** (OpenAI e simili): restano **solo dell'admin**. Gli utenti non le vedono,
  non le inseriscono, e le funzioni che le usano sono riservate all'admin.
- **Dati tra utenti**: ogni richiesta viene filtrata per `user_id` lato server.
  Un utente non può leggere né scrivere dati di un altro, nemmeno indovinando gli identificativi.

---

## 6. Dove vivono i dati

| Dato | Oggi | Proposta |
|---|---|---|
| Analisi di mercato (workbook Excel) | condiviso in `analyses/` | **resta condiviso, sola lettura** per gli utenti; rigenerabile solo dall'admin |
| Utenti (email, password, ruolo, stato), sessioni, registro attività, codici di reimpostazione | non esistono | **SQLite** (un file) |
| Watchlist e liste personalizzate | file JSON | **SQLite**, per utente |
| Monitor e note operative | `monitor_items.json` | **SQLite**, per utente |
| Alert: regole e stato di invio | file JSON/YAML | **SQLite**, per utente |
| Collegamenti Telegram (`chat_id`) | non esiste | **SQLite**, per utente |
| Preferenze di visualizzazione | `localStorage` del browser | **SQLite** (così seguono l'utente su qualsiasi dispositivo) |

### Struttura dei dati utente (proposta)

```
utenti            id, email (unica), password_hash, nome_visualizzato,
                  ruolo (admin|utente), stato (in_attesa|attivo|sospeso),
                  creato_il, ultimo_accesso_il, approvato_da
sessioni          id, utente_id, token_hash, creato_il, scade_il, ip, user_agent
attivita          id, utente_id (o NULL per eventi anonimi), quando, ip,
                  azione, oggetto, esito
reimpostazioni    id, utente_id, codice_hash, scade_il, usato_il
telegram          utente_id, chat_id, collegato_il
preferenze        utente_id, chiave, valore
watchlists        utente_id, nome, ticker…            (sostituisce i file JSON attuali)
monitor           utente_id, ticker, mercato, nota, creato_il
alert_regole      utente_id, id_regola, abilitata, definizione…
alert_stato       utente_id, id_regola, ultimo_invio, conteggio_oggi
```

**Perché SQLite e non file JSON**: con più utenti che scrivono, due salvataggi
simultanei su un file si sovrascrivono. SQLite gestisce la concorrenza con
transazioni, non richiede installazione ed è un file solo da salvare.

**Perché i workbook restano fuori**: sono il risultato dell'analisi, pesante e
condivisa. Tenerli separati significa che il lavoro costoso resta dell'admin e
nessun utente può bloccare la macchina.

---

## 7. Cosa cambia nell'interfaccia

- **Accesso e registrazione**: pagina con *Accedi* / *Registrati* / *Password dimenticata*.
  Chi si registra vede un messaggio chiaro: *"Richiesta inviata: l'amministratore deve approvarla"*.
  Se non c'è sessione, l'app non mostra nessun dato di mercato.
- **Barra in alto**: nome utente, ruolo, pulsante *Esci*.
- **Nuova sezione "Utenti"** (solo admin): elenco utenti con stato, approvazione delle
  richieste in attesa, sospensione, riattivazione, cambio ruolo, reimpostazione assistita,
  eliminazione. In evidenza le **richieste di reimpostazione password** con il codice da comunicare.
- **Nuova sezione "Attività"** (solo admin): registro filtrabile per utente, data e tipo.
- **Pagina "Notifiche"** (tutti): stato del collegamento Telegram, codice di
  collegamento, scollegamento, e l'elenco delle proprie regole di alert.
- **Funzioni AI**: per gli utenti non admin restano visibili ma disabilitate,
  con spiegazione. Nessun percorso alternativo per attivarle.
- **Preferenze**: tab iniziale, vista Schede/Tabella, filtri — salvati per utente.

---

## 8. Requisiti non funzionali

- **Prestazioni**: il login e le pagine non devono rallentare il Pi. L'analisi
  resta l'unica operazione pesante, e solo l'admin può avviarla.
- **Concorrenza**: due utenti che salvano nello stesso momento non devono
  perdere dati (è il motivo di SQLite).
- **Robustezza**: un errore su un dato di un utente non deve impedire l'accesso agli altri.
- **Manutenzione**: le soglie e le regole del modello restano dove sono ora
  (`four_axes.py`), senza duplicazioni con il livello utenti.
- **Backup**: il file SQLite va incluso nei backup del Pi (una copia è sufficiente),
  insieme ai workbook.

---

## 9. Casi particolari da gestire

- Registrazione con **email già esistente**: messaggio generico, senza rivelare che
  l'account esiste (evita di scoprire quali email sono registrate).
- Utente **in attesa di approvazione** che prova ad accedere: messaggio chiaro che
  spiega che serve l'approvazione dell'admin, senza dati di mercato.
- Utente **sospeso** mentre ha una sessione aperta: la sessione va invalidata subito.
- **Codice di reimpostazione** scaduto, già usato o sbagliato: stesso messaggio,
  nessun indizio su quale dei tre casi sia.
- **Ultimo admin**: non può essere sospeso né eliminato, altrimenti nessuno può più gestire nulla.
- **Utente che scollega Telegram**: le sue regole restano attive ma non inviano;
  l'app lo segnala come avviso, non come errore.
- **Bot bloccato dall'utente**: Telegram restituisce un errore all'invio; l'app lo
  registra e avvisa l'utente nella pagina Notifiche.
- **Stesso account Telegram collegato a due utenti**: consentito ma segnalato
  (le notifiche arriverebbero mescolate sulla stessa chat).
- **Primo avvio dopo l'aggiornamento**: senza utenti l'app deve guidare alla
  creazione dell'admin, non restare bloccata.

---

## 10. Criteri di accettazione

1. Un utente si registra da solo e **non entra** finché l'admin non lo approva;
   dopo l'approvazione entra con la password che ha scelto.
2. Create due utenti, **nessuno dei due vede** liste, monitor, note o alert dell'altro.
3. Un utente non admin che chiama l'API delle funzioni AI **riceve un rifiuto**,
   anche se costruisce la richiesta a mano; nell'interfaccia il pulsante è visibile ma disabilitato.
4. Nel registro attività compaiono accessi (riusciti e falliti), disconnessioni, registrazioni,
   approvazioni e le azioni rilevanti, con data, utente e indirizzo IP.
5. Un utente che ha dimenticato la password la reimposta col codice fornito dall'admin,
   **senza che l'admin conosca la nuova password**; il codice non funziona una seconda volta.
6. Un utente collega Telegram col codice e **riceve sul proprio account** una
   notifica di prova; l'altro utente non la riceve.
7. Sospendendo un utente, la sua sessione **smette di funzionare** entro pochi secondi.
8. L'ultimo admin non può essere eliminato né sospeso.
9. Riavviando il servizio, utenti, dati e collegamenti Telegram **restano**.

---

## 11. Tappe di realizzazione

| Tappa | Contenuto | Verifica a fine tappa |
|---|---|---|
| **1** | Registrazione con email, approvazione dell'admin, login, sessione, ruoli, registro attività | un utente si registra, l'admin approva, entra; nessuno vede i dati dell'altro; il registro mostra accessi e approvazioni |
| **2** | Reimpostazione password a codice monouso (+ via assistita) | il codice funziona una volta sola e scade; l'admin non conosce la nuova password |
| **3** | Migrazione dati in SQLite (liste, monitor, note, alert) | i dati attuali risultano nel tuo utente, nulla è perso |
| **4** | Funzioni AI riservate (interfaccia + controllo server) | il controllo server rifiuta l'utente non admin |
| **5** | Notifiche Telegram per utente (codice di collegamento) | notifica di prova ricevuta solo dal proprietario |
| **6** | Preferenze per utente, pagine Utenti e Attività, rifiniture | le preferenze seguono l'utente, l'admin gestisce tutto da interfaccia |

---

## 12. Decisioni

### Chiuse

| # | Decisione | Scelta |
|---|---|---|
| 1 | Registrazione | **autonoma con email e password**, con approvazione dell'admin |
| 2 | Password dimenticata | **reimpostazione autonoma** a codice monouso comunicato dall'admin |
| 3 | Ruoli | **admin** (tutto, incluse le funzioni AI) e **utente** |
| 4 | Funzioni AI | **tutte** riservate all'admin; gli altri le vedono disabilitate |
| 5 | Numero di utenti | **una ventina al massimo** per ora |
| 6 | Ambito di rete | **rete locale** |

### Aperte

Da chiudere prima o durante la realizzazione. Le mie proposte sono indicate.

1. **Approvazione**: confermi che ogni registrazione va approvata dall'admin?
   *Proposta: sì — senza, chiunque sia sulla rete può crearsi un account.*
2. **Invio del codice di reimpostazione**: va bene il passaggio dall'admin (di persona
   o con un messaggio), o vuoi predisporre l'invio automatico via email?
   *Proposta: passaggio dall'admin; l'invio automatico si aggiunge dopo senza rifare nulla.*
3. **Eliminazione utente**: dati cancellati o archiviati? *Proposta: archiviati, con
   cancellazione definitiva come azione separata e confermata.*
4. **Promozione ad admin**: consentita? *Proposta: sì, con avviso; l'ultimo admin non è toccabile.*
5. **Registro attività**: vanno bene le azioni elencate in R2, conservate 12 mesi?
   *Proposta: sì.*
6. **Notifiche duplicate**: se due utenti attivano la stessa regola sullo stesso titolo,
   due notifiche o una? *Proposta: due, una per proprietario.*
7. **Preferenze su database o browser**: *Proposta: database, così seguono l'utente.*
8. **Requisiti minimi della password**: *Proposta: almeno 10 caratteri, senza obbligo di
   simboli (le regole troppo rigide portano a password peggiori).*
9. **Nome utente visibile**: basta il nome visualizzato scelto in registrazione,
   o vuoi che l'admin possa modificarlo? *Proposta: modificabile dall'utente e dall'admin.*
