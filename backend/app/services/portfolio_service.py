"""Portafoglio virtuale: fase 1.

Cosa c'e' qui, e cosa non c'e' ancora.

C'E': creazione di piu' portafogli indipendenti, compravendita manuale, calcolo di
quantita' e costi (commissioni, imposta Tobin, cambio), valutazione delle posizioni
con il prezzo corrente e il cambio del giorno, storico delle operazioni chiuse.

NON C'E' (fasi successive, vedi docs/portafoglio-virtuale-specifica.md):
  - uscite automatiche (stop, obiettivo, trailing)
  - ingressi automatici dai segnali
  - il motore che gira ogni 15 minuti

PERCHE' I COSTI STANNO NEL DIMENSIONAMENTO e non solo nel risultato: con un minimo
di 2,95 € per operazione, comprare 300 € costa l'1% solo di commissione. Se il
dimensionamento non ne tiene conto, il simulatore compra un numero di posizioni
che nella realta' sarebbe in perdita certa.

UNITA' DI MISURA: ogni importo in questo modulo e' in EURO, tranne i campi
esplicitamente chiamati `prezzo_nativo` (valuta dello strumento) e `cambio`.
"""
from __future__ import annotations

import json
import math
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.config import ANALYSES_DIR

# ── Costi (vedi specifica §4.1) ────────────────────────────────────────
COMMISSIONE_PCT = 0.0019      # 0,19%
COMMISSIONE_MIN_EUR = 2.95    # minimo per operazione
TOBIN_PCT = 0.0010            # 0,10%, solo acquisto, solo azioni italiane
CAMBIO_PCT = 0.0025           # 0,25% di spread sul cambio
SLIPPAGE_PCT = 0.0005         # 0,05% prudenziale

# I mercati su cui un portafoglio puo' operare. Devono combaciare con i file di
# analisi esistenti, altrimenti il mercato non e' verificabile.
MERCATI_VALIDI = ("MIB30", "DAX", "ETF", "ETC", "Crypto", "US_Others", "Preferite")

# ── Parametri di default di un portafoglio nuovo (preset "Bilanciato") ─
PARAMETRI_DEFAULT: dict[str, Any] = {
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
    "mercati": list(MERCATI_VALIDI),
    "tech_score_min": 75,
    "ingressi_da": ["ENTRA"],
    "scadenza_segnale_sedute": 3,
    "uscita_tempo_sedute": 30,
    "max_nuove_posizioni_giorno": 3,
    "rotazione": False,
    "liquidita_minima_ordine_eur": 300.0,
}

# Preset proposti alla creazione. Non sono "profili utente": sono solo punti di
# partenza che vengono copiati nei parametri del portafoglio.
PRESET: dict[str, dict[str, Any]] = {
    "conservativo": {
        "rischio_per_operazione_pct": 0.5,
        "max_per_titolo_pct": 5.0,
        "max_posizioni": 8,
        "esposizione_max_pct": 60.0,
        "stop_atr_mult": 1.5,
        "trailing_atr_mult": 0.0,
        "obiettivo_pct": 8.0,
        "rischio_ammesso": ["NORMALE"],
        "tech_score_min": 80,
        "ingressi_da": ["ENTRA"],
    },
    "bilanciato": {},  # = PARAMETRI_DEFAULT
    "aggressivo": {
        "rischio_per_operazione_pct": 2.0,
        "max_per_titolo_pct": 20.0,
        "max_posizioni": 20,
        "esposizione_max_pct": 100.0,
        "riserva_liquidita_pct": 0.0,
        "stop_atr_mult": 2.5,
        "obiettivo_pct": 25.0,
        "rischio_ammesso": ["NORMALE", "TESO", "ESTREMO"],
        "tech_score_min": 70,
        "ingressi_da": ["ENTRA", "OSSERVA"],
    },
}


def cartella() -> Path:
    """Cartella dei portafogli (dati di runtime, non versionati)."""
    percorso = ANALYSES_DIR / "portafogli"
    percorso.mkdir(parents=True, exist_ok=True)
    return percorso


def _percorso(pid: str) -> Path:
    return cartella() / f"{pid}.json"


def _valida_id(pid: str) -> str:
    """Solo lettere, numeri, trattino e trattino basso: niente percorsi."""
    pulito = re.sub(r"[^a-zA-Z0-9_-]", "", str(pid or ""))
    if not pulito:
        raise ValueError("Identificativo del portafoglio non valido")
    return pulito


def _slug(nome: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", str(nome or "").strip().lower()).strip("_")
    return base or "portafoglio"


# ── Lettura e scrittura ────────────────────────────────────────────────
def leggi(pid: str) -> dict[str, Any]:
    percorso = _percorso(_valida_id(pid))
    if not percorso.exists():
        raise FileNotFoundError(f"Portafoglio '{pid}' inesistente")
    return json.loads(percorso.read_text(encoding="utf-8"))


def scrivi(pf: dict[str, Any]) -> None:
    """Scrittura atomica: se fallisce a meta', il file precedente resta valido."""
    percorso = _percorso(_valida_id(pf["id"]))
    temporaneo = percorso.with_suffix(".json.tmp")
    temporaneo.write_text(json.dumps(pf, ensure_ascii=False, indent=2), encoding="utf-8")
    temporaneo.replace(percorso)


def _aggiungi_riga(pid: str, suffisso: str, riga: dict[str, Any]) -> None:
    """Append-only: operazioni, storico e scarti non si riscrivono mai.

    Un file riscritto puo' troncarsi a meta' scrittura e perdere tutto lo storico.
    Uno a cui si aggiungono righe, no.
    """
    percorso = cartella() / f"{_valida_id(pid)}{suffisso}.jsonl"
    with percorso.open("a", encoding="utf-8") as f:
        f.write(json.dumps(riga, ensure_ascii=False) + "\n")


def leggi_righe(pid: str, suffisso: str) -> list[dict[str, Any]]:
    percorso = cartella() / f"{_valida_id(pid)}{suffisso}.jsonl"
    if not percorso.exists():
        return []
    righe: list[dict[str, Any]] = []
    for testo in percorso.read_text(encoding="utf-8").splitlines():
        testo = testo.strip()
        if not testo:
            continue
        try:
            righe.append(json.loads(testo))
        except json.JSONDecodeError:
            # Una riga corrotta non deve rendere illeggibile tutto lo storico.
            continue
    return righe


# ── Creazione e parametri ──────────────────────────────────────────────
def parametri_da_preset(preset: str) -> dict[str, Any]:
    scelto = PRESET.get(str(preset or "").strip().lower())
    if scelto is None:
        raise ValueError(f"Preset '{preset}' sconosciuto")
    return {**PARAMETRI_DEFAULT, **scelto}


def crea(nome: str, capitale: float, preset: str = "bilanciato",
         parametri: dict[str, Any] | None = None, note: str = "") -> dict[str, Any]:
    nome_pulito = str(nome or "").strip()
    if not nome_pulito:
        raise ValueError("Il nome del portafoglio e' obbligatorio")
    try:
        capitale_iniziale = float(capitale)
    except (TypeError, ValueError):
        raise ValueError("Il capitale deve essere un numero")
    if capitale_iniziale <= 0:
        raise ValueError("Il capitale deve essere positivo")

    base = {**parametri_da_preset(preset), **(parametri or {})}
    pid = _slug(nome_pulito)
    # Due portafogli con lo stesso nome non devono sovrascriversi.
    contatore = 2
    while _percorso(pid).exists():
        pid = f"{_slug(nome_pulito)}_{contatore}"
        contatore += 1

    pf = {
        "id": pid,
        "nome": nome_pulito,
        "valuta_base": "EUR",
        "capitale_iniziale": round(capitale_iniziale, 2),
        "liquidita": round(capitale_iniziale, 2),
        "stato": "attivo",
        "creato": datetime.now().isoformat(timespec="seconds"),
        "note": str(note or ""),
        "parametri": base,
        "posizioni": [],
        "coda": [],
        "ultimo_giro": None,
        "analisi_finale_usata": None,
    }
    scrivi(pf)
    return pf


def elenco() -> list[dict[str, Any]]:
    risultato: list[dict[str, Any]] = []
    for percorso in sorted(cartella().glob("*.json")):
        try:
            pf = json.loads(percorso.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(pf, dict) or "id" not in pf:
            continue
        operazioni = leggi_righe(pf["id"], "_operazioni")

        # Riepilogo vero anche a portafoglio chiuso: senza il valore attuale la
        # riga mostrerebbe solo la liquidita', che non dice se stai guadagnando.
        # Il costo e' una quotazione per posizione, servita dalla cache dell'Excel.
        valore_totale = 0.0
        valore_posizioni = 0.0
        for pos in pf.get("posizioni") or []:
            try:
                prezzo, _fonte = prezzo_corrente(str(pos.get("ticker")))
                cambio = cambio_a_eur(str(pos.get("valuta", "EUR")))
                valore_posizioni += float(pos.get("quantita", 0.0)) * prezzo * cambio
            except Exception:
                # Prezzo non disponibile: la posizione vale il suo costo.
                valore_posizioni += float(pos.get("importo_investito_eur", 0.0))
        valore_totale = float(pf.get("liquidita", 0.0)) + valore_posizioni
        capitale = float(pf.get("capitale_iniziale", 0.0))

        risultato.append({
            "id": pf["id"],
            "nome": pf.get("nome", pf["id"]),
            "stato": pf.get("stato", "attivo"),
            "valuta_base": pf.get("valuta_base", "EUR"),
            "capitale_iniziale": capitale,
            "liquidita": pf.get("liquidita", 0.0),
            "valore_totale": round(valore_totale, 2),
            "valore_posizioni": round(valore_posizioni, 2),
            "pnl_eur": round(valore_totale - capitale, 2),
            "pnl_pct": round((valore_totale / capitale - 1.0) * 100.0, 2) if capitale else 0.0,
            "esposizione_pct": round(valore_posizioni / valore_totale * 100.0, 2) if valore_totale else 0.0,
            "num_posizioni": len(pf.get("posizioni") or []),
            "num_operazioni": len(operazioni),
            "creato": pf.get("creato"),
        })
    return risultato


def aggiorna(pid: str, nome: str | None = None, stato: str | None = None,
             parametri: dict[str, Any] | None = None, note: str | None = None) -> dict[str, Any]:
    pf = leggi(pid)
    if nome is not None:
        pf["nome"] = str(nome).strip() or pf["nome"]
    if stato is not None:
        if stato not in ("attivo", "in_pausa", "archiviato"):
            raise ValueError("Stato non valido")
        pf["stato"] = stato
    if note is not None:
        pf["note"] = str(note)
    if parametri:
        sconosciute = [k for k in parametri if k not in PARAMETRI_DEFAULT]
        if sconosciute:
            raise ValueError(f"Parametri non riconosciuti: {', '.join(sconosciute)}")
        if "mercati" in parametri:
            scelti = parametri["mercati"]
            if not isinstance(scelti, list):
                raise ValueError("'mercati' deve essere una lista")
            ignoti = [str(m) for m in scelti if str(m) not in MERCATI_VALIDI]
            if ignoti:
                raise ValueError(
                    f"Mercati sconosciuti: {', '.join(ignoti)}. "
                    f"Validi: {', '.join(MERCATI_VALIDI)}"
                )
            parametri = {**parametri, "mercati": [str(m) for m in scelti]}
        pf["parametri"] = {**pf.get("parametri", {}), **parametri}
    scrivi(pf)
    return pf


# ── Mercato: prezzo, ATR, cambio ───────────────────────────────────────
_CACHE_RIGHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_CAMBI: dict[str, tuple[float, float]] = {}


def riga_titolo(ticker: str) -> dict[str, Any] | None:
    """La riga dell'analisi per un titolo, cercata nei mercati.

    Serve per ATR, nome e segnale. La ricerca e' in memoria con controllo della
    data del file: se l'analisi viene rigenerata, la cache si invalida da sola.
    """
    simbolo = str(ticker or "").strip().upper()
    if not simbolo:
        return None

    from app.services.watchlist_service import analysis_path_for_market, load_market_dataframe

    for mercato in ("MIB30", "DAX", "ETF", "ETC", "Crypto", "US_Others", "Preferite"):
        try:
            percorso = analysis_path_for_market(mercato)
        except Exception:
            continue
        try:
            istante = percorso.stat().st_mtime
        except OSError:
            continue
        chiave = f"{mercato}:{simbolo}"
        in_cache = _CACHE_RIGHE.get(chiave)
        if in_cache and in_cache[0] == istante:
            # Se in questo mercato il titolo NON c'era, si deve passare al
            # successivo. Restituire None qui era un difetto vero: al secondo
            # accesso un titolo DAX risultava "non presente nelle analisi",
            # quindi non verificabile, quindi non comprabile.
            if in_cache[1]:
                return in_cache[1]
            continue
        try:
            df = load_market_dataframe(mercato)
        except Exception:
            continue
        if df is None or df.empty or "Ticker" not in df.columns:
            continue
        trovata = df[df["Ticker"].astype(str).str.upper() == simbolo]
        if trovata.empty:
            _CACHE_RIGHE[chiave] = (istante, {})
            continue
        riga = {str(k): v for k, v in trovata.iloc[0].to_dict().items()}
        riga["_mercato"] = mercato
        _CACHE_RIGHE[chiave] = (istante, riga)
        return riga
    return None


def risolvi_titolo(testo: str) -> str:
    """Dal testo scritto dall'utente al ticker vero.

    "Eni" diventa "ENI.MI". Se il testo non corrisponde a nulla si restituisce
    com'e': il messaggio d'errore successivo dira' che non e' verificabile, che e'
    piu' chiaro di un "non trovato" generico.
    """
    grezzo = str(testo or "").strip()
    if not grezzo:
        return grezzo
    try:
        from app.services.monitor_service import resolve_input

        risolto = resolve_input(grezzo, None)
        if risolto.get("found"):
            ticker = str(risolto["item"].get("ticker") or "").strip()
            if ticker:
                return ticker.upper()
    except Exception:
        pass
    return grezzo.upper()


def candidati(pf: dict[str, Any], ricerca: str, limite: int = 12) -> list[dict[str, Any]]:
    """Titoli dei mercati abilitati che corrispondono al testo cercato.

    Serve a non dover conoscere i ticker a memoria. Restituisce anche indicazione
    e TECH, cosi' si sceglie con un'informazione davanti invece che alla cieca.
    """
    from app.services.watchlist_service import load_market_dataframe

    termine = str(ricerca or "").strip().lower()
    ammessi = [str(m) for m in (pf.get("parametri", {}).get("mercati") or [])]
    if not ammessi:
        return []

    trovati: list[dict[str, Any]] = []
    for mercato in ammessi:
        try:
            df = load_market_dataframe(mercato)
        except Exception:
            continue
        if df is None or df.empty or "Ticker" not in df.columns:
            continue

        for _, riga in df.iterrows():
            ticker = str(riga.get("Ticker") or "").strip().upper()
            if not ticker:
                continue
            nome = str(riga.get("Name") or "")
            if termine and termine not in ticker.lower() and termine not in nome.lower():
                continue
            trovati.append({
                "ticker": ticker,
                "nome": nome or ticker,
                "mercato": mercato,
                "indicazione": riga.get("Entry_Signal"),
                "tech_score": riga.get("TECH_SCORE"),
                "rischio": riga.get("Rischio_Trend"),
            })
            if len(trovati) >= limite:
                return trovati
    return trovati


def mercato_di(ticker: str) -> str | None:
    """Il mercato di un titolo, letto dalle analisi. None se non e' presente."""
    riga = riga_titolo(str(ticker or "").strip().upper())
    if not riga:
        return None
    return str(riga.get("_mercato") or "") or None


def verifica_mercato_ammesso(pf: dict[str, Any], ticker: str) -> str:
    """Blocca l'acquisto se il titolo non appartiene ai mercati del portafoglio.

    Restituisce il mercato del titolo. Solleva ValueError se non ammesso o se il
    mercato non e' verificabile: meglio rifiutare che comprare al buio.
    """
    mercato = mercato_di(ticker)
    ammessi = [str(m) for m in (pf.get("parametri", {}).get("mercati") or [])]

    if mercato is None:
        raise ValueError(
            f"{ticker} non e' presente nelle analisi: il suo mercato non e' verificabile, "
            "quindi l'acquisto e' bloccato. Aggiungilo a un mercato analizzato oppure "
            "scegli un titolo che compaia nell'elenco."
        )
    if ammessi and mercato not in ammessi:
        raise ValueError(
            f"{ticker} appartiene al mercato {mercato}, che non e' abilitato per questo "
            f"portafoglio (abilitati: {', '.join(ammessi) or 'nessuno'})."
        )
    return mercato


def strumento_da_mercato(mercato: str) -> str:
    """Che cosa e' lo strumento: azione, ETF, ETC, cripto.

    Si ricava dal mercato in cui il titolo viene analizzato. Non e' una verita'
    di borsa, e' l'etichetta della colonna "Strumento": serve a distinguere a
    colpo d'occhio un'azione da un ETF, e a questo basta.
    """
    codice = str(mercato or "").strip().upper()
    if codice == "ETF":
        return "ETF"
    if codice == "ETC":
        return "ETC"
    if codice == "CRYPTO":
        return "Cripto"
    return "Azione"


def valuta_da_ticker(ticker: str) -> str:
    """Valuta dello strumento ricavata dal suffisso del ticker.

    Approssimazione dichiarata: il suffisso dice il mercato di quotazione, che
    nella grande maggioranza dei casi coincide con la valuta.
    """
    simbolo = str(ticker or "").upper()
    if simbolo.endswith(".MI") or simbolo.endswith(".DE") or simbolo.endswith(".PA"):
        return "EUR"
    if simbolo.endswith(".AS") or simbolo.endswith(".MC") or simbolo.endswith(".BR"):
        return "EUR"
    if simbolo.endswith(".SW"):
        return "CHF"
    if simbolo.endswith(".L"):
        return "GBP"
    return "USD"


def e_azione_italiana(ticker: str, nome: str = "") -> bool:
    """Imposta Tobin: solo azioni italiane, non ETF/ETC.

    Distinzione per nome: gli ETF/ETC non pagano la Tobin. E' un'euristica, quindi
    viene dichiarata: se sbaglia, sbaglia di 0,10% su un solo acquisto.
    """
    simbolo = str(ticker or "").upper()
    if not simbolo.endswith(".MI"):
        return False
    testo = f"{simbolo} {nome or ''}".upper()
    return not any(p in testo for p in ("ETF", "ETC", "UCITS", "FONDO", "INDICE"))


def cambio_a_eur(valuta: str) -> float:
    """Quanti euro vale una unita' della valuta indicata. EUR = 1."""
    codice = str(valuta or "EUR").upper()
    if codice == "EUR":
        return 1.0

    import time

    adesso = time.time()
    in_cache = _CACHE_CAMBI.get(codice)
    if in_cache and adesso - in_cache[0] < 900:  # 15 minuti
        return in_cache[1]

    # yfinance quota EURUSD=X come "quanti dollari per un euro".
    from yfinance_runtime import yf

    coppia = f"EUR{codice}=X"
    valore: float | None = None
    try:
        dati = yf.Ticker(coppia).history(period="5d", interval="1d", actions=False)
        if dati is not None and not dati.empty:
            serie = dati["Close"].dropna()
            if len(serie):
                valore = float(serie.iloc[-1])
    except Exception:
        valore = None

    if not valore or valore <= 0:
        # Nessun cambio disponibile: meglio un errore esplicito che un numero
        # inventato che falserebbe ogni P/L in valuta estera.
        raise RuntimeError(f"Cambio {codice}/EUR non disponibile")

    risultato = 1.0 / valore
    _CACHE_CAMBI[codice] = (adesso, risultato)
    return risultato


def prezzo_corrente(ticker: str) -> tuple[float, str]:
    """Prezzo attuale e fonte. Usa la stessa fonte delle card (Excel, poi Yahoo)."""
    from app.services.quote_service import chart_snapshot

    snap = chart_snapshot(ticker)
    prezzo = snap.get("close")
    if prezzo is None:
        raise RuntimeError(f"Prezzo non disponibile per {ticker}")
    return float(prezzo), str(snap.get("source") or "")


# ── Costi ──────────────────────────────────────────────────────────────
def commissione(importo_eur: float) -> float:
    return round(max(COMMISSIONE_MIN_EUR, abs(importo_eur) * COMMISSIONE_PCT), 2)


def imposta_tobin(importo_eur: float, ticker: str, nome: str = "") -> float:
    if not e_azione_italiana(ticker, nome):
        return 0.0
    return round(abs(importo_eur) * TOBIN_PCT, 2)


def _arrotonda_prezzo(valore: float) -> float:
    """Quattro decimali: bastano per gli strumenti da 0,05 e per il P/L."""
    return round(float(valore), 4)


# ── Dimensionamento ────────────────────────────────────────────────────
def calcola_stop(prezzo: float, atr: float, parametri: dict[str, Any]) -> float:
    moltiplicatore = float(parametri.get("stop_atr_mult", 2.0))
    minimo_pct = float(parametri.get("stop_min_pct", 1.5))
    massimo_pct = float(parametri.get("stop_max_pct", 15.0))

    stop = prezzo - atr * moltiplicatore
    # Le due correzioni impediscono stop assurdi: un ATR enorme non deve valere un
    # rischio del 40%, un ATR minuscolo non deve mettere lo stop dentro il rumore.
    stop = max(stop, prezzo * (1.0 - massimo_pct / 100.0))
    stop = min(stop, prezzo * (1.0 - minimo_pct / 100.0))
    return _arrotonda_prezzo(max(stop, 0.0001))


def capitale_totale(pf: dict[str, Any]) -> float:
    """Liquidita' + valore delle posizioni al prezzo corrente."""
    totale = float(pf.get("liquidita", 0.0))
    for pos in pf.get("posizioni") or []:
        try:
            prezzo, _ = prezzo_corrente(pos["ticker"])
            totale += float(pos["quantita"]) * prezzo * cambio_a_eur(pos.get("valuta", "EUR"))
        except Exception:
            # Se il prezzo manca, la posizione vale il suo costo: meglio che zero.
            totale += float(pos.get("importo_investito_eur", 0.0))
    return totale


def dimensiona(pf: dict[str, Any], prezzo: float, cambio: float,
               atr: float | None, importo_richiesto: float | None = None) -> dict[str, Any]:
    """Quante azioni comprare, e perche'.

    Restituisce anche i tre limiti che hanno concorso, cosi' l'interfaccia puo'
    spiegare la cifra invece di mostrarla e basta.
    """
    par = pf.get("parametri", {})
    capitale = capitale_totale(pf)
    liquidita = float(pf.get("liquidita", 0.0))

    stop = calcola_stop(prezzo, atr or prezzo * 0.03, par)
    distanza = max(prezzo - stop, 0.0001)
    prezzo_eseguito = prezzo * (1.0 + SLIPPAGE_PCT)

    def a_quantita(importo_eur: float) -> int:
        costo_unitario = prezzo_eseguito * cambio * (1.0 + COMMISSIONE_PCT)
        return int(math.floor(max(importo_eur, 0.0) / max(costo_unitario, 0.0001)))

    if importo_richiesto is not None:
        # Acquisto manuale: l'importo lo decide l'utente, i tetti restano.
        tetto_titolo = capitale * float(par.get("max_per_titolo_pct", 10.0)) / 100.0
        cassa_libera = liquidita - capitale * float(par.get("riserva_liquidita_pct", 10.0)) / 100.0
        importo = min(float(importo_richiesto), tetto_titolo, cassa_libera)
        return {
            "quantita": a_quantita(importo),
            "prezzo": prezzo,
            "prezzo_eseguito": _arrotonda_prezzo(prezzo_eseguito),
            "stop": stop,
            "obiettivo": _arrotonda_prezzo(prezzo * (1.0 + float(par.get("obiettivo_pct", 15.0)) / 100.0)),
            "importo_teorico_eur": round(importo, 2),
            "rischio_eur": round(a_quantita(importo) * distanza * cambio, 2),
            "limite": "importo_scelto",
        }

    rischio_eur = capitale * float(par.get("rischio_per_operazione_pct", 1.0)) / 100.0
    tetto_titolo = capitale * float(par.get("max_per_titolo_pct", 10.0)) / 100.0
    cassa_libera = liquidita - capitale * float(par.get("riserva_liquidita_pct", 10.0)) / 100.0

    q_rischio = int(math.floor(rischio_eur / max(distanza * cambio, 0.0001)))
    q_tetto = a_quantita(tetto_titolo)
    q_cassa = a_quantita(cassa_libera)

    quantita = min(q_rischio, q_tetto, q_cassa)
    limite = (
        "rischio" if quantita == q_rischio
        else "tetto_titolo" if quantita == q_tetto
        else "cassa"
    )
    return {
        "quantita": quantita,
        "prezzo": prezzo,
        "prezzo_eseguito": _arrotonda_prezzo(prezzo_eseguito),
        "stop": stop,
        "obiettivo": _arrotonda_prezzo(prezzo * (1.0 + float(par.get("obiettivo_pct", 15.0)) / 100.0)),
        "importo_teorico_eur": round(quantita * prezzo_eseguito * cambio, 2),
        "rischio_eur": round(quantita * distanza * cambio, 2),
        "limite": limite,
        "limiti": {"rischio": q_rischio, "tetto_titolo": q_tetto, "cassa": q_cassa},
    }


# ── Compravendita ──────────────────────────────────────────────────────
def compra(pid: str, ticker: str, importo_eur: float | None = None,
           quantita: int | None = None, motivo: str = "", manuale: bool = True) -> dict[str, Any]:
    pf = leggi(pid)
    if pf.get("stato") == "archiviato":
        raise ValueError("Portafoglio archiviato: non si compra")

    simbolo = str(ticker or "").strip().upper()
    if not simbolo:
        raise ValueError("Ticker obbligatorio")
    if any(str(p.get("ticker", "")).upper() == simbolo for p in pf.get("posizioni") or []):
        raise ValueError(f"{simbolo} e' gia' in portafoglio")

    par = pf.get("parametri", {})
    # Si puo' scrivere il nome invece del ticker: "Eni" vale "ENI.MI".
    simbolo = risolvi_titolo(simbolo)
    # Prima di tutto: questo titolo appartiene a un mercato su cui il portafoglio
    # opera? Se no, non si va avanti nemmeno a calcolare la quantita'.
    verifica_mercato_ammesso(pf, simbolo)
    riga = riga_titolo(simbolo) or {}
    nome = str(riga.get("Name") or simbolo)
    valuta = valuta_da_ticker(simbolo)
    cambio = cambio_a_eur(valuta)

    prezzo, fonte = prezzo_corrente(simbolo)
    atr = None
    try:
        atr = float(riga.get("ATR")) if riga.get("ATR") is not None else None
    except (TypeError, ValueError):
        atr = None
    if not atr or atr <= 0:
        try:
            atr_pct = float(riga.get("ATR_PCT"))
            atr = prezzo * atr_pct / 100.0
        except (TypeError, ValueError):
            atr = None

    piano = dimensiona(pf, prezzo, cambio, atr, importo_eur)
    q = int(quantita) if quantita is not None else int(piano["quantita"])
    if q <= 0:
        raise ValueError(
            "Quantita' calcolata zero: con i limiti attuali questo acquisto non si puo' fare "
            f"(limite raggiunto: {piano.get('limite')})"
        )

    prezzo_eseguito = piano["prezzo_eseguito"]
    valore_nativo = q * prezzo_eseguito
    valore_eur = valore_nativo * cambio
    comm = commissione(valore_eur)
    tobin = imposta_tobin(valore_eur, simbolo, nome)
    costo_cambio = valore_eur * CAMBIO_PCT if valuta != "EUR" else 0.0

    speso = valore_eur + comm + tobin + costo_cambio
    if speso > float(pf.get("liquidita", 0.0)) + 0.005:
        raise ValueError(
            f"Liquidita' insufficiente: servono {speso:.2f} € e ce ne sono {pf.get('liquidita', 0):.2f} €"
        )

    stop = piano["stop"]
    posizione = {
        "id": f"pos_{len(pf.get('posizioni') or []) + 1:04d}",
        "ticker": simbolo,
        "nome": nome,
        "mercato": riga.get("_mercato") or "",
        "valuta": valuta,
        "cambio_ingresso": round(cambio, 6),
        "data_ingresso": date.today().isoformat(),
        "ora_ingresso": datetime.now().strftime("%H:%M:%S"),
        "prezzo_ingresso": prezzo_eseguito,
        "quantita": q,
        "importo_investito_eur": round(valore_eur, 2),
        "commissione_ingresso_eur": comm,
        "imposta_tobin_eur": tobin,
        "costo_cambio_eur": round(costo_cambio, 2),
        "stop_iniziale": stop,
        "stop_attuale": stop,
        "obiettivo": piano["obiettivo"],
        "atr_ingresso": _arrotonda_prezzo(atr) if atr else None,
        "rischio_iniziale_eur": round(q * max(prezzo_eseguito - stop, 0.0) * cambio, 2),
        "motivo_ingresso": motivo or ("acquisto manuale" if manuale else "segnale"),
        "analisi_riferimento": riga.get("_mercato") or "",
        "prezzo_fonte": fonte,
        "manuale": bool(manuale),
    }
    pf.setdefault("posizioni", []).append(posizione)
    pf["liquidita"] = round(float(pf.get("liquidita", 0.0)) - speso, 2)
    scrivi(pf)
    _aggiungi_riga(pid, "_eventi", {
        "quando": datetime.now().isoformat(timespec="seconds"),
        "tipo": "acquisto",
        "ticker": simbolo,
        "quantita": q,
        "prezzo": prezzo_eseguito,
        "importo_eur": round(valore_eur, 2),
        "costi_eur": round(comm + tobin + costo_cambio, 2),
        "liquidita_dopo": pf["liquidita"],
    })
    return {"portafoglio": pf, "posizione": posizione, "piano": piano, "speso_eur": round(speso, 2)}


def vendi(pid: str, ticker_o_posizione: str, motivo: str = "manuale",
          quantita: int | None = None) -> dict[str, Any]:
    pf = leggi(pid)
    chiave = str(ticker_o_posizione or "").strip().upper()

    indice = None
    for i, pos in enumerate(pf.get("posizioni") or []):
        if str(pos.get("id", "")).upper() == chiave or str(pos.get("ticker", "")).upper() == chiave:
            indice = i
            break
    if indice is None:
        raise ValueError(f"{ticker_o_posizione} non e' in portafoglio")

    pos = pf["posizioni"][indice]
    q = int(quantita) if quantita is not None else int(pos["quantita"])
    if q <= 0 or q > int(pos["quantita"]):
        raise ValueError("Quantita' di vendita non valida")

    simbolo = str(pos["ticker"])
    valuta = str(pos.get("valuta", "EUR"))
    cambio = cambio_a_eur(valuta)
    prezzo, fonte = prezzo_corrente(simbolo)
    prezzo_eseguito = _arrotonda_prezzo(prezzo * (1.0 - SLIPPAGE_PCT))

    ricavo_nativo = q * prezzo_eseguito
    ricavo_eur = ricavo_nativo * cambio
    comm = commissione(ricavo_eur)
    costo_cambio = ricavo_eur * CAMBIO_PCT if valuta != "EUR" else 0.0
    incassato = ricavo_eur - comm - costo_cambio

    # Costo di acquisto della quota venduta, in proporzione.
    quota = q / float(pos["quantita"])
    costo_acquisto = round(float(pos.get("importo_investito_eur", 0.0)) * quota, 2)
    costi_acquisto = round(
        (float(pos.get("commissione_ingresso_eur", 0.0)) +
         float(pos.get("imposta_tobin_eur", 0.0)) +
         float(pos.get("costo_cambio_eur", 0.0))) * quota,
        2,
    )
    pnl_lordo = ricavo_eur - costo_acquisto
    pnl_netto = pnl_lordo - costi_acquisto - comm - costo_cambio
    rischio = float(pos.get("rischio_iniziale_eur", 0.0)) * quota

    try:
        giorni = (date.today() - date.fromisoformat(str(pos.get("data_ingresso")))).days
    except Exception:
        giorni = 0

    operazione = {
        "posizione": pos.get("id"),
        "ticker": simbolo,
        "nome": pos.get("nome"),
        "quantita": q,
        "valuta": valuta,
        "data_ingresso": pos.get("data_ingresso"),
        "prezzo_ingresso": pos.get("prezzo_ingresso"),
        "data_uscita": date.today().isoformat(),
        "ora_uscita": datetime.now().strftime("%H:%M:%S"),
        "prezzo_uscita": prezzo_eseguito,
        "motivo_uscita": motivo,
        "commissioni_totali_eur": round(costi_acquisto + comm, 2),
        "costo_cambio_totale_eur": round(costo_cambio, 2),
        "imposta_tobin_eur": round(float(pos.get("imposta_tobin_eur", 0.0)) * quota, 2),
        "pnl_lordo_eur": round(pnl_lordo, 2),
        "pnl_netto_eur": round(pnl_netto, 2),
        "pnl_pct": round(pnl_netto / costo_acquisto * 100.0, 2) if costo_acquisto else 0.0,
        "r_multiplo": round(pnl_netto / rischio, 2) if rischio else None,
        "giorni_detenuti": giorni,
        "prezzo_fonte": fonte,
        "manuale": motivo == "manuale",
    }

    if q >= int(pos["quantita"]):
        pf["posizioni"].pop(indice)
    else:
        pos["quantita"] = int(pos["quantita"]) - q
        pos["importo_investito_eur"] = round(float(pos["importo_investito_eur"]) - costo_acquisto, 2)
        pos["rischio_iniziale_eur"] = round(float(pos["rischio_iniziale_eur"]) - rischio, 2)

    pf["liquidita"] = round(float(pf.get("liquidita", 0.0)) + incassato, 2)
    scrivi(pf)
    _aggiungi_riga(pid, "_operazioni", operazione)
    _aggiungi_riga(pid, "_eventi", {
        "quando": datetime.now().isoformat(timespec="seconds"),
        "tipo": "vendita",
        "ticker": simbolo,
        "quantita": q,
        "prezzo": prezzo_eseguito,
        "incassato_eur": round(incassato, 2),
        "liquidita_dopo": pf["liquidita"],
    })
    return {"portafoglio": pf, "operazione": operazione, "incassato_eur": round(incassato, 2)}


# ── Valutazione ────────────────────────────────────────────────────────
def valuta(pf: dict[str, Any]) -> dict[str, Any]:
    """Dettaglio del portafoglio con prezzi correnti, P/L e distanza dallo stop."""
    posizioni: list[dict[str, Any]] = []
    valore_posizioni = 0.0
    investito = 0.0

    for pos in pf.get("posizioni") or []:
        voce = dict(pos)
        valuta_pos = str(pos.get("valuta", "EUR"))
        try:
            cambio = cambio_a_eur(valuta_pos)
        except Exception:
            cambio = float(pos.get("cambio_ingresso") or 1.0)
        try:
            prezzo, fonte = prezzo_corrente(str(pos["ticker"]))
            valida = True
        except Exception:
            prezzo, fonte, valida = float(pos.get("prezzo_ingresso", 0.0)), "prezzo non disponibile", False

        q = float(pos.get("quantita", 0))
        valore_eur = q * prezzo * cambio
        valore_posizioni += valore_eur
        investito += float(pos.get("importo_investito_eur", 0.0))

        costo_unitario = float(pos.get("prezzo_ingresso", 0.0)) or 0.0
        pnl_eur = (prezzo - costo_unitario) * q * cambio
        pnl_pct = (prezzo / costo_unitario - 1.0) * 100.0 if costo_unitario else 0.0
        stop = float(pos.get("stop_attuale") or 0.0)
        distanza_stop = (prezzo - stop) / prezzo * 100.0 if prezzo and stop else None

        # Il P/L del solo prezzo non basta: comprare costa. Qui si calcola anche
        # quanto resterebbe VENDENDO ADESSO, dopo commissione d'ingresso, Tobin,
        # slippage e commissione di vendita. Senza questo, una posizione appena
        # aperta sembra in perdita di pochi centesimi quando in realta' ha gia'
        # lasciato sul tavolo lo 0,3-0,4%.
        costi_ingresso = (
            float(pos.get("commissione_ingresso_eur", 0.0))
            + float(pos.get("imposta_tobin_eur", 0.0))
            + float(pos.get("costo_cambio_eur", 0.0))
        )
        ricavo_lordo = q * prezzo * cambio
        comm_vendita = commissione(ricavo_lordo)
        cambio_vendita = ricavo_lordo * CAMBIO_PCT if valuta_pos != "EUR" else 0.0
        incasso_netto = ricavo_lordo - comm_vendita - cambio_vendita
        costo_ingresso_totale = float(pos.get("importo_investito_eur", 0.0)) + costi_ingresso
        pnl_netto = incasso_netto - costo_ingresso_totale

        voce.update({
            "prezzo_corrente": _arrotonda_prezzo(prezzo),
            "cambio_corrente": round(cambio, 6),
            "valore_eur": round(valore_eur, 2),
            "pnl_eur": round(pnl_eur, 2),
            "pnl_pct": round(pnl_pct, 2),
            # "Se vendessi adesso": tutti i costi, andata e ritorno.
            "costi_ingresso_eur": round(costi_ingresso, 2),
            "costo_vendita_eur": round(comm_vendita + cambio_vendita, 2),
            "pnl_netto_eur": round(pnl_netto, 2),
            "pnl_netto_pct": round(pnl_netto / costo_ingresso_totale * 100.0, 2) if costo_ingresso_totale else 0.0,
            "distanza_stop_pct": round(distanza_stop, 2) if distanza_stop is not None else None,
            "strumento": strumento_da_mercato(str(pos.get("mercato") or "")),
            "mercato": str(pos.get("mercato") or ""),
            "prezzo_valido": valida,
            "prezzo_fonte": fonte,
        })
        posizioni.append(voce)

    liquidita = float(pf.get("liquidita", 0.0))
    totale = liquidita + valore_posizioni
    capitale_iniziale = float(pf.get("capitale_iniziale", 0.0))
    operazioni = leggi_righe(pf["id"], "_operazioni")

    chiusi = [o for o in operazioni if o.get("pnl_netto_eur") is not None]
    vinte = [o for o in chiusi if float(o["pnl_netto_eur"]) > 0]
    perse = [o for o in chiusi if float(o["pnl_netto_eur"]) <= 0]
    somma_vinte = sum(float(o["pnl_netto_eur"]) for o in vinte)
    somma_perse = abs(sum(float(o["pnl_netto_eur"]) for o in perse))

    return {
        "id": pf["id"],
        "nome": pf.get("nome", pf["id"]),
        "stato": pf.get("stato", "attivo"),
        "valuta_base": pf.get("valuta_base", "EUR"),
        "capitale_iniziale": capitale_iniziale,
        "liquidita": round(liquidita, 2),
        "valore_posizioni": round(valore_posizioni, 2),
        "valore_totale": round(totale, 2),
        "investito": round(investito, 2),
        "esposizione_pct": round(valore_posizioni / totale * 100.0, 2) if totale else 0.0,
        "pnl_totale_eur": round(totale - capitale_iniziale, 2),
        "pnl_totale_pct": round((totale / capitale_iniziale - 1.0) * 100.0, 2) if capitale_iniziale else 0.0,
        "num_posizioni": len(posizioni),
        "num_operazioni": len(chiusi),
        "statistiche": {
            "vinte": len(vinte),
            "perse": len(perse),
            "win_rate": round(len(vinte) / len(chiusi) * 100.0, 1) if chiusi else None,
            "profit_factor": round(somma_vinte / somma_perse, 2) if somma_perse > 0 else None,
            "pnl_medio_eur": round((somma_vinte - somma_perse) / len(chiusi), 2) if chiusi else None,
        },
        "parametri": pf.get("parametri", {}),
        "posizioni": posizioni,
        "creato": pf.get("creato"),
        "note": pf.get("note", ""),
        "costi": {
            "commissione_pct": COMMISSIONE_PCT,
            "commissione_min_eur": COMMISSIONE_MIN_EUR,
            "tobin_pct": TOBIN_PCT,
            "cambio_pct": CAMBIO_PCT,
            "slippage_pct": SLIPPAGE_PCT,
        },
    }


def _numero(valore: Any) -> float | None:
    """Numero da una cella dell'Excel, senza sorprese su NaN e stringhe."""
    try:
        import math

        f = float(valore)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def candidati_da_segnale(pf: dict[str, Any]) -> list[dict[str, Any]]:
    """I titoli che il profilo accetterebbe, ordinati per forza del segnale.

    Filtri della specifica (tutti obbligatori): indicazione ammessa, TECH_SCORE
    minimo, rischio ammesso, liquidita' OK, non gia' in portafoglio.
    """
    from app.services.watchlist_service import load_market_dataframe

    par = pf.get("parametri", {})
    ammessi_mercati = [str(m) for m in (par.get("mercati") or [])]
    ingressi = {str(x).strip().upper() for x in (par.get("ingressi_da") or ["ENTRA"])}
    rischi = {str(x).strip().upper() for x in (par.get("rischio_ammesso") or [])}
    tech_min = float(par.get("tech_score_min", 0.0))
    in_portafoglio = {str(pos.get("ticker", "")).upper() for pos in pf.get("posizioni") or []}

    candidati: list[dict[str, Any]] = []
    for mercato in ammessi_mercati:
        try:
            df = load_market_dataframe(mercato)
        except Exception:
            continue
        if df is None or df.empty or "Ticker" not in df.columns:
            continue

        for _, riga in df.iterrows():
            ticker = str(riga.get("Ticker") or "").strip().upper()
            if not ticker or ticker in in_portafoglio:
                continue

            indicazione = str(riga.get("Entry_Signal") or "").strip().upper()
            if indicazione not in ingressi:
                continue
            tech = _numero(riga.get("TECH_SCORE"))
            if tech is None or tech < tech_min:
                continue
            rischio = str(riga.get("Rischio_Trend") or "").strip().upper()
            if rischi and rischio not in rischi:
                continue
            liquidita = str(riga.get("Liquidity") or "").strip().upper()
            if liquidita and liquidita != "OK":
                continue

            candidati.append({
                "ticker": ticker,
                "nome": str(riga.get("Name") or ticker),
                "mercato": mercato,
                "indicazione": indicazione,
                "tech_score": tech,
                "adx": _numero(riga.get("ADX")),
                "rischio_trend": rischio,
            })

    # Ordine: prima il punteggio, poi la solidita' del trend. A parita' di tutto,
    # il ticker, cosi' due giri con gli stessi dati producono lo stesso risultato.
    candidati.sort(key=lambda c: (-c["tech_score"], -(c["adx"] or 0.0), c["ticker"]))
    return candidati


def _posizioni_aperte_oggi(pf: dict[str, Any]) -> int:
    oggi = date.today().isoformat()
    return sum(1 for pos in pf.get("posizioni") or [] if str(pos.get("data_ingresso")) == oggi)


def esegui_giro(pid: str) -> dict[str, Any]:
    """Un giro completo di soli ingressi, decisi dal sistema.

    Non vende: le uscite automatiche sono la fase 2. Ma prima di comprare
    controlla tutti i limiti, e ogni rinuncia viene registrata.
    """
    pf = leggi(pid)
    if pf.get("stato") != "attivo":
        raise ValueError(f"Il portafoglio e' '{pf.get('stato')}': mettilo attivo per eseguire un giro")

    par = pf.get("parametri", {})
    max_posizioni = int(par.get("max_posizioni", 12))
    esposizione_max = float(par.get("esposizione_max_pct", 90.0))
    max_oggi = int(par.get("max_nuove_posizioni_giorno", 3))
    minimo_ordine = float(par.get("liquidita_minima_ordine_eur", 300.0))
    gia_oggi = _posizioni_aperte_oggi(pf)

    candidati = candidati_da_segnale(pf)
    eseguiti: list[dict[str, Any]] = []
    scarti: list[dict[str, Any]] = []
    analisi_usate: dict[str, str] = {}

    for candidato in candidati:
        ticker = candidato["ticker"]

        # Ogni limite viene controllato PRIMA di comprare, e il motivo viene
        # scritto: senza registro, fra un mese non si sapra' perche' un titolo
        # promettente non e' entrato.
        if len(pf.get("posizioni") or []) >= max_posizioni:
            scarti.append({"ticker": ticker, "motivo": "limite_posizioni",
                           "dettaglio": f"{len(pf.get('posizioni') or [])} posizioni su {max_posizioni}"})
            continue
        if gia_oggi + len(eseguiti) >= max_oggi:
            scarti.append({"ticker": ticker, "motivo": "limite_giornaliero",
                           "dettaglio": f"massimo {max_oggi} nuove posizioni al giorno"})
            continue
        try:
            totale = capitale_totale(pf)
            esposizione = 0.0
            if totale > 0:
                valore = sum(
                    float(p.get("importo_investito_eur", 0.0)) for p in pf.get("posizioni") or []
                )
                esposizione = valore / totale * 100.0
            if esposizione >= esposizione_max:
                scarti.append({"ticker": ticker, "motivo": "esposizione_massima",
                               "dettaglio": f"{esposizione:.1f}% su {esposizione_max:.1f}%"})
                continue
        except Exception:
            pass

        # Quanto comprare, con i tre limiti che concorrono.
        try:
            riga = riga_titolo(ticker) or {}
            # "codice_valuta" e non "valuta": dentro questa funzione "valuta" e'
            # anche il nome della funzione che calcola il dettaglio, e una variabile
            # locale la nasconderebbe (errore reale: "'str' object is not callable").
            codice_valuta = valuta_da_ticker(ticker)
            cambio = cambio_a_eur(codice_valuta)
            prezzo, _fonte = prezzo_corrente(ticker)
            atr = _numero(riga.get("ATR"))
            if not atr:
                atr_pct = _numero(riga.get("ATR_PCT"))
                atr = prezzo * atr_pct / 100.0 if atr_pct else None
            piano = dimensiona(pf, prezzo, cambio, atr)
            quantita = int(piano["quantita"])
            importo = float(piano["importo_teorico_eur"])
        except Exception as errore:
            scarti.append({"ticker": ticker, "motivo": "prezzo_non_disponibile", "dettaglio": str(errore)})
            continue

        if quantita <= 0:
            scarti.append({"ticker": ticker, "motivo": "quantita_zero",
                           "dettaglio": f"limite raggiunto: {piano.get('limite')}"})
            continue
        if importo < minimo_ordine:
            scarti.append({"ticker": ticker, "motivo": "ordine_troppo_piccolo",
                           "dettaglio": f"{importo:.0f} € sotto il minimo di {minimo_ordine:.0f} €"})
            continue

        try:
            esito = compra(pid, ticker, quantita=quantita,
                           motivo=f"segnale {candidato['indicazione']} · TECH {round(candidato['tech_score'])}")
        except Exception as errore:
            scarti.append({"ticker": ticker, "motivo": "acquisto_non_riuscito", "dettaglio": str(errore)})
            continue

        pf = esito["portafoglio"]
        posizione = esito["posizione"]
        eseguiti.append({
            "ticker": ticker,
            "nome": candidato["nome"],
            "mercato": candidato["mercato"],
            "quantita": posizione["quantita"],
            "prezzo": posizione["prezzo_ingresso"],
            "importo_eur": posizione["importo_investito_eur"],
            "tech_score": round(candidato["tech_score"], 1),
            "indicazione": candidato["indicazione"],
            "stop": posizione["stop_iniziale"],
        })
        analisi_usate[candidato["mercato"]] = str(riga.get("Date") or "")[:10]

    for voce in scarti:
        _aggiungi_riga(pid, "_scarti", {
            "quando": datetime.now().isoformat(timespec="seconds"),
            "ticker": voce["ticker"],
            "motivo": voce["motivo"],
            "dettaglio": voce.get("dettaglio", ""),
            "portafoglio": pid,
        })

    pf = leggi(pid)
    pf["ultimo_giro"] = datetime.now().isoformat(timespec="seconds")
    if analisi_usate:
        pf["analisi_finale_usata"] = ", ".join(f"{m} {d}" for m, d in sorted(analisi_usate.items()))
    scrivi(pf)

    return {
        "portafoglio": valuta(pf),
        "eseguiti": eseguiti,
        "scarti": scarti,
        "candidati_valutati": len(candidati),
        "analisi_usate": analisi_usate,
        "liquidita_dopo": pf.get("liquidita"),
    }


def anteprima_acquisto(pid: str, ticker: str, importo_eur: float | None = None) -> dict[str, Any]:
    """Cosa succederebbe comprando adesso, senza comprare.

    L'interfaccia deve poter mostrare quantita', costo e perdita massima PRIMA
    della conferma: un acquisto che sorprende e' un acquisto sbagliato.
    """
    pf = leggi(pid)
    simbolo = str(ticker or "").strip().upper()
    if not simbolo:
        raise ValueError("Ticker obbligatorio")
    # Anche qui: nome o ticker, indifferente.
    simbolo = risolvi_titolo(simbolo)
    verifica_mercato_ammesso(pf, simbolo)
    riga = riga_titolo(simbolo) or {}
    nome = str(riga.get("Name") or simbolo)
    valuta = valuta_da_ticker(simbolo)
    cambio = cambio_a_eur(valuta)
    prezzo, fonte = prezzo_corrente(simbolo)

    atr = None
    try:
        atr = float(riga.get("ATR")) if riga.get("ATR") is not None else None
    except (TypeError, ValueError):
        atr = None
    if not atr or atr <= 0:
        try:
            atr = prezzo * float(riga.get("ATR_PCT")) / 100.0
        except (TypeError, ValueError):
            atr = None

    piano = dimensiona(pf, prezzo, cambio, atr, importo_eur)
    q = int(piano["quantita"])
    valore_eur = q * piano["prezzo_eseguito"] * cambio
    comm = commissione(valore_eur)
    tobin = imposta_tobin(valore_eur, simbolo, nome)
    costo_cambio = valore_eur * CAMBIO_PCT if valuta != "EUR" else 0.0

    return {
        "ticker": simbolo,
        "nome": nome,
        "valuta": valuta,
        "prezzo": piano["prezzo"],
        "prezzo_eseguito": piano["prezzo_eseguito"],
        "cambio": round(cambio, 6),
        "quantita": q,
        "importo_eur": round(valore_eur, 2),
        "commissione_eur": comm,
        "imposta_tobin_eur": tobin,
        "costo_cambio_eur": round(costo_cambio, 2),
        "totale_eur": round(valore_eur + comm + tobin + costo_cambio, 2),
        "stop": piano["stop"],
        "obiettivo": piano["obiettivo"],
        "perdita_massima_eur": round(q * max(piano["prezzo_eseguito"] - piano["stop"], 0.0) * cambio, 2),
        "limite": piano.get("limite"),
        "limiti": piano.get("limiti"),
        "liquidita_eur": round(float(pf.get("liquidita", 0.0)), 2),
        "prezzo_fonte": fonte,
        "atr": _arrotonda_prezzo(atr) if atr else None,
        "indicazione": riga.get("Entry_Signal"),
        "tech_score": riga.get("TECH_SCORE"),
        "rischio_trend": riga.get("Rischio_Trend"),
        "ordine_troppo_piccolo": bool(
            valore_eur < float(pf.get("parametri", {}).get("liquidita_minima_ordine_eur", 300.0))
        ),
    }


def elimina(pid: str) -> None:
    """Archivia invece di cancellare: lo storico delle operazioni non si perde."""
    pf = leggi(pid)
    pf["stato"] = "archiviato"
    scrivi(pf)
