# News sulle card

Il pulsante News apre l'ultimo report salvato. `Cerca notizie` avvia la prima
ricerca; `Nuova ricerca` sostituisce il report solo dopo un completamento riuscito.
Aprire il pannello, ricaricare la pagina o riavviare il backend non avvia ricerche.
Il punto accanto a News segnala un report disponibile. Data e ora sono mostrate
nel pannello e nel suggerimento del pulsante.

Configurazione backend: `OPENAI_API_KEY` nel `.env` del progetto, come per le
altre funzioni AI. `OPENAI_NEWS_MODEL` è opzionale (default `gpt-4.1`);
il modello deve supportare Responses API e lo strumento `web_search`.
Ogni ricerca manuale utilizza l'API OpenAI a pagamento; leggere i report salvati
non genera chiamate AI. La ricerca richiede connessione e credito API.

I risultati sono conservati senza scadenza in `data/news.sqlite3`, escluso da Git.
Includere questo file nei backup. Windows e Raspberry mantengono archivi separati:
un git pull trasferisce il codice, non i report. Chiave del report: ticker completo
(compreso suffisso borsa), condiviso tra liste diverse dello stesso titolo.

Il report include notizie recenti, sentiment delle notizie, target analisti ed
eventi/rischi, con fonti consultabili. Dati non reperibili sono indicati come tali;
non si tratta di un feed strutturato garantito di target o quotazioni live.
Il prezzo storico della card e la sua data sono salvati insieme al report.

API: GET `/api/news?ticker=ENI.MI` legge soltanto; POST `/api/news/research`
avvia la ricerca. Una ricerca alla volta per processo backend; le richieste
concorrenti ricevono 409. Errori del provider non cancellano il risultato precedente.

Test: dalla cartella backend, `python -m unittest test_news_service -v`.
