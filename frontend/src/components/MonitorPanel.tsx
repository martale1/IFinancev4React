import { useState, useMemo } from "react";
import type { WatchlistRow, MonitorResponse, QuickAlertField } from "../types";
import { AxisTiles } from "./AxisTiles";
import { DenseList } from "./DenseList";
import { MarketChips } from "./MarketChips";
import { ordinaPerRango, testa, testaIndicazione, ANELLO_FASE, ANELLO_RISCHIO, type Dimensione } from "../ranking";
import { pctClass as tablePctClass, signalClass as tableSignalClass } from "./WatchlistTable";

type QuickAlertConfig = {
  field: QuickAlertField;
  op: ">" | "<" | "==" | "!=";
  value: number | string | null;
};

type MonitorView = "cards" | "table" | "list";

/** Tabella del monitor: colonne allineate a quelle usate per il tab All. */
function MonitorTable({
  rows,
  onChart,
  onAi,
  onNews,
  onOpenNoteModal,
  onRemoveMonitor,
  openAlertBox,
  alertMap,
}: {
  rows: WatchlistRow[];
  onChart: (row: WatchlistRow) => void;
  onAi: (row: WatchlistRow) => void;
  onNews: (ticker: string) => void;
  onOpenNoteModal: (row: WatchlistRow) => void;
  onRemoveMonitor: (ticker: string, sourceMarket?: string) => Promise<void>;
  openAlertBox: (row: WatchlistRow) => void;
  alertMap: Record<string, boolean>;
}) {
  return (
    <div className="watchlist-table-wrap">
      <table className="watchlist-table">
        <thead>
          <tr>
            <th>Titolo</th>
            <th>Indicazione</th>
            <th>Fase</th>
            <th>Prezzo</th>
            <th>1D</th>
            <th>5D</th>
            <th>30D</th>
            <th>Direzione</th>
            <th>Forza</th>
            <th>Momento</th>
            <th>Rischio</th>
            <th>TECH</th>
            <th>ADX</th>
            <th>Liquidità</th>
            <th>Nota</th>
            <th>Azioni</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const ticker = String(row.Ticker ?? "-").trim();
            const source = String(row.WL_Source_Market || "MIB30");
            const key = `${source}::${ticker.toUpperCase()}`;
            const signal = String(row.Entry_Signal ?? "ATTENDI").toUpperCase();
            const note = String(row.Monitor_Note || "").trim();
            const phase = String(row.Market_Phase ?? "-").replace(/_/g, " ");
            const liquidity = String(row.Liquidity ?? "-");
            const direzione = String(row.Direzione_Trend ?? "-");
            const forza = String(row.Forza_Trend ?? "-").replace("FORTE_", "");
            const momento = String(row.Momento_Trend ?? "-");
            const rischio = String(row.Rischio_Trend ?? "-");
            const segno = (v: string) => v === "SU" || v === "FORTE_SU" || v === "CRESCENTE" || v === "NORMALE";
            const segnoNegativo = (v: string) => v === "GIU" || v === "FORTE_GIU" || v === "CALANTE" || v === "ESTREMO";
            return (
              <tr key={`${source}-${ticker}-${index}`}>
                <td className="ticker-cell">
                  <strong>{ticker}</strong>
                  <small>{String(row.Name ?? "-")} · {source}</small>
                </td>
                <td><span className={`table-signal ${tableSignalClass(signal)}`}>{signal}</span></td>
                <td><span className="scenario-label">{phase}</span></td>
                <td className="numeric">{num(row.Close, 3)}</td>
                <td className={`numeric ${tablePctClass(row.PCTV_1D)}`}>{pct(row.PCTV_1D)}</td>
                <td className={`numeric ${tablePctClass(row.PCTV_5D)}`}>{pct(row.PCTV_5D)}</td>
                <td className={`numeric ${tablePctClass(row.PCTV_30D)}`}>{pct(row.PCTV_30D)}</td>
                <td><span className={segno(direzione) ? "positive" : segnoNegativo(direzione) ? "negative" : ""}>{direzione}</span></td>
                <td><span className={segno(forza) ? "positive" : segnoNegativo(forza) ? "negative" : ""}>{forza}</span></td>
                <td><span className={segno(momento) ? "positive" : segnoNegativo(momento) ? "negative" : ""}>{momento}</span></td>
                <td><span className={segno(rischio) ? "positive" : segnoNegativo(rischio) ? "negative" : ""}>{rischio}</span></td>
                <td className="numeric">{num(row.TECH_SCORE, 0)}</td>
                <td className="numeric">{num(row.ADX, 1)}</td>
                <td>
                  <span className={liquidity.toUpperCase() === "OK" ? "positive" : "negative"}>{liquidity}</span>
                </td>
                <td className="monitor-note-cell" title={note}>{note || "-"}</td>
                <td className="table-actions">
                  <button className="btn" onClick={() => onChart(row)}>Grafico</button>
                  <button className="btn ghost" onClick={() => onAi(row)}>AI</button>
                  <button className="btn ghost" onClick={() => onNews(ticker)}>News</button>
                  <button className="btn ghost" onClick={() => onOpenNoteModal(row)}>Dettagli</button>
                  <button className={alertMap[key] ? "btn alert-on" : "btn ghost"} onClick={() => openAlertBox(row)}>
                    {alertMap[key] ? "Alert ON" : "Alert"}
                  </button>
                  <button className="btn ghost danger" onClick={() => { void onRemoveMonitor(ticker, source); }}>Rimuovi</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

type Props = {
  monitorData: MonitorResponse | undefined;
  isLoading: boolean;
  markets: string[];
  onAddMonitor: (ticker: string, sourceMarket?: string, note?: string) => Promise<{
    status: string;
    ticker: string;
    name?: string;
    source_market: string;
    moved_from_market?: string | null;
  }>;
  onRemoveMonitor: (ticker: string, sourceMarket?: string) => Promise<void>;
  onOpenNoteModal: (row: WatchlistRow) => void;
  onChart: (row: WatchlistRow) => void;
  onAi: (row: WatchlistRow) => void;
  onNews: (ticker: string) => void;
  alertMap: Record<string, boolean>;
  alertConfigMap: Record<string, QuickAlertConfig>;
  alertBusyMap: Record<string, boolean>;
  onCreateAlert: (input: { row: WatchlistRow; source_market: string; field: QuickAlertField; op: ">" | "<" | "==" | "!="; value: number | string }) => Promise<string>;
  onRemoveAlert: (input: { row: WatchlistRow; source_market: string }) => Promise<string>;
};

function toNum(v: unknown): number | null {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function num(v: unknown, digits = 1): string {
  const n = toNum(v);
  if (n === null) return "-";
  return n.toLocaleString("it-IT", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function pct(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "-";
  return `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;
}

function pctColor(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "#9fb7cf";
  if (n > 0) return "#22c55e";
  if (n < 0) return "#ff4d5a";
  return "#cfe5fa";
}

function techColor(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "#9fb7cf";
  if (n >= 60) return "#22c55e";
  if (n <= 40) return "#ff4d5a";
  return "#f59e0b";
}

function s3Color(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "#9fb7cf";
  if (n > 0) return "#22c55e";
  if (n < 0) return "#ff4d5a";
  return "#9fb7cf";
}

function alligatorColor(v: unknown): string {
  const s = String(v ?? "").toLowerCase();
  if (s.includes("uptrend") || s.includes("wakeup")) return "#22c55e";
  if (s.includes("downtrend")) return "#ff4d5a";
  if (s.includes("sleep")) return "#9fb7cf";
  return "#f59e0b";
}

function fmtVol(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "-";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2).replace(".", ",")}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1).replace(".", ",")}K`;
  return String(Math.round(n));
}

function entrySignalClass(sig: unknown): string {
  const s = String(sig ?? "").trim().toUpperCase();
  if (s === "ENTRA") return "action-buy";
  if (s === "OSSERVA") return "action-add";
  if (s === "EVITA") return "action-sell";
  return "action-wait";
}

export default function MonitorPanel({
  monitorData,
  isLoading,
  markets,
  onAddMonitor,
  onRemoveMonitor,
  onOpenNoteModal,
  onChart,
  onAi,
  onNews,
  alertMap,
  alertConfigMap,
  alertBusyMap,
  onCreateAlert,
  onRemoveAlert,
}: Props) {
  const [newTicker, setNewTicker] = useState("");
  const [newMarket, setNewMarket] = useState("MIB30");
  const [newNote, setNewNote] = useState("");
  const [adding, setAdding] = useState(false);
  const [filterText, setFilterText] = useState("");
  const [error, setError] = useState("");
  const [added, setAdded] = useState("");
  const [alertRow, setAlertRow] = useState<WatchlistRow | null>(null);
  const [alertField, setAlertField] = useState<QuickAlertField>("Close");
  const [alertOp, setAlertOp] = useState<">" | "<" | "==" | "!=">(">");
  const [alertValue, setAlertValue] = useState("");
  const [alertMsg, setAlertMsg] = useState("");
  // Nella vista Schede le azioni secondarie stanno in un menu: qui memorizzo
  // quale card lo ha aperto (chiave mercato-ticker).
  const [actionsFor, setActionsFor] = useState<string | null>(null);
  const [view, setView] = useState<MonitorView>(() => {
    const chiave = "ifinance-monitor-view";
    const chiaveVersione = "ifinance-monitor-view-default";
    const versione = "2";
    const telefono = typeof window.matchMedia === "function"
      && window.matchMedia("(max-width: 700px)").matches;

    let salvata: string | null = null;
    try {
      // Migrazione una tantum: chi aveva gia' una scelta salvata se la ritrova
      // "cards" anche sul telefono e non vedrebbe mai la lista densa, perche' la
      // scelta salvata vince sul predefinito. Alla prima apertura dopo questo
      // aggiornamento si riparte dal predefinito (lista sul telefono); da li' in
      // poi la scelta dell'utente vince di nuovo, perche' la versione e' salvata.
      if (window.localStorage.getItem(chiaveVersione) !== versione) {
        window.localStorage.setItem(chiaveVersione, versione);
        window.localStorage.removeItem(chiave);
      }
      salvata = window.localStorage.getItem(chiave);
    } catch {
      salvata = null;
    }

    if (salvata === "cards" || salvata === "table" || salvata === "list") return salvata;
    // Sul telefono la lista densa: misurata 47 px per riga contro 385 di una
    // scheda (18 righe per schermata contro 2,2). Sul PC restano le schede.
    return telefono ? "list" : "cards";
  });

  function changeView(next: MonitorView) {
    setView(next);
    window.localStorage.setItem("ifinance-monitor-view", next);
  }

  const items = useMemo(() => monitorData?.items || [], [monitorData]);

  /**
   * Filtro a tessera, sullo stesso principio di Highlights: i conteggi riguardano
   * sempre TUTTI i titoli monitorati, mentre il clic restringe l'elenco mostrato.
   */
  // Mercato da mostrare: "Tutti" di base, cosi' la pagina non resta mai vuota
  // (i titoli monitorati possono essere di mercati diversi).
  const [mercatoMostrato, setMercatoMostrato] = useState("Tutti");

  // Testa dell'ordinamento: il valore scelto con un clic su una tessera.
  // Non e' un filtro: nessun titolo viene nascosto, cambia solo l'ordine.
  // Si parte senza scelta: la testa la decide il ripiego automatico (ENTRA, e se
  // non c'e' OSSERVA, poi ATTENDI, poi EVITA). Se fosse "ENTRA" a priori, su un
  // mercato senza titoli ENTRA la prima riga sarebbe un gruppo vuoto.
  const [rango, setRango] = useState<{ indicazione: string | null; fase: string | null; rischio: string | null }>({
    indicazione: null,
    fase: null,
    rischio: null,
  });
  // Su quale dimensione si e' cliccato per ultimo: e' quella che ordina per prima.
  const [dimensione, setDimensione] = useState<Dimensione>("indicazione");

  const filteredItems = useMemo(() => {
    const term = filterText.trim().toLowerCase();
    return items.filter((row) => {
      if (mercatoMostrato !== "Tutti" && String(row.WL_Source_Market ?? "") !== mercatoMostrato) return false;
      if (!term) return true;
      const tk = String(row.Ticker || "").toLowerCase();
      const nm = String(row.Name || "").toLowerCase();
      const note = String(row.Monitor_Note || "").toLowerCase();
      const mkt = String(row.WL_Source_Market || "").toLowerCase();
      return tk.includes(term) || nm.includes(term) || note.includes(term) || mkt.includes(term);
    });
  }, [items, filterText, mercatoMostrato]);

  // L'ordinamento agisce su cio' che si vede, dopo la ricerca: non cambia quali
  // titoli compaiono, solo in che ordine.
  // Testa effettiva dell'ordinamento: quella scelta, oppure il primo valore
  // presente partendo da ENTRA (vedi testaIndicazione). Serve perche' le tessere
  // non hanno una "naturale" come la barra: senza, nessuna risulterebbe in testa.
  // La freccia sta sulla tessera che comanda l'ordine: quella della dimensione
  // scelta, con il valore in testa dopo il ripiego sui valori presenti.
  const testaAttiva = dimensione === "fase"
    ? { kind: "fase" as const, value: testa(filteredItems, "Market_Phase", ANELLO_FASE, rango.fase) }
    : dimensione === "rischio"
      ? { kind: "rischio" as const, value: testa(filteredItems, "Rischio_Trend", ANELLO_RISCHIO, rango.rischio) }
      : { kind: "indicazione" as const, value: testaIndicazione(filteredItems, rango.indicazione) };

  const righeOrdinate = useMemo(
    () => ordinaPerRango(filteredItems, rango, dimensione),
    [filteredItems, rango, dimensione],
  );

  // Statistics
  const totalCount = items.length;
  const entraCount = items.filter((r) => r.Entry_Signal === "ENTRA").length;
  const osservaCount = items.filter((r) => r.Entry_Signal === "OSSERVA").length;
  const withNotesCount = items.filter((r) => String(r.Monitor_Note || "").trim().length > 0).length;

  const handleQuickAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const typed = newTicker.trim();
    if (!typed) return;
    try {
      setAdding(true);
      setError("");
      setAdded("");
      // Il testo può essere un ticker o il nome del titolo: il backend lo risolve
      // e conferma quale titolo è stato registrato.
      const result = await onAddMonitor(typed, newMarket, newNote.trim());
      const resolved = result?.ticker && result.ticker.toUpperCase() !== typed.toUpperCase();
      const details = `${result.ticker}${result.name ? ` · ${result.name}` : ""} (${result.source_market})`;
      const moved = result.moved_from_market
        ? ` Il titolo è nel mercato ${result.source_market}, non in ${result.moved_from_market}.`
        : "";
      setAdded(
        (resolved ? `"${typed}" → aggiunto ${details}` : `${details} aggiunto al monitor`) + `.${moved}`
      );
      setNewTicker("");
      setNewNote("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Errore durante l'aggiunta");
    } finally {
      setAdding(false);
    }
  };

  const openAlertBox = (row: WatchlistRow) => {
    const close = toNum(row.Close);
    const cfg = alertConfigMap[`${String(row.WL_Source_Market || "MIB30")}::${String(row.Ticker || "").toUpperCase()}`];
    setAlertRow(row);
    setAlertMsg("");
    setAlertField(cfg?.field ?? "Close");
    setAlertOp(cfg?.op ?? ">");
    setAlertValue(cfg?.value != null ? String(cfg.value) : close != null ? String(close) : "");
  };

  const saveAlert = async () => {
    if (!alertRow) return;
    const sourceMarket = String(alertRow.WL_Source_Market || "MIB30");
    const n = Number(alertValue.replace(",", "."));
    const value: number | string = alertField === "Signal6" ? alertValue : n;
    if (alertField !== "Signal6" && !Number.isFinite(n)) {
      setAlertMsg("Valore alert non valido.");
      return;
    }
    try {
      const result = await onCreateAlert({ row: alertRow, source_market: sourceMarket, field: alertField, op: alertOp, value });
      setAlertMsg(result);
    } catch (err: unknown) {
      setAlertMsg(err instanceof Error ? err.message : String(err));
    }
  };

  const deleteAlert = async () => {
    if (!alertRow) return;
    const sourceMarket = String(alertRow.WL_Source_Market || "MIB30");
    try {
      const result = await onRemoveAlert({ row: alertRow, source_market: sourceMarket });
      setAlertMsg(result);
      setAlertRow(null);
    } catch (err: unknown) {
      setAlertMsg(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="monitor-panel" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Intestazione compatta: titolo + KPI come pillole su una sola riga */}
      <div className="monitor-header">
        <div className="monitor-header-title">
          <h2>🎯 Titoli in Monitoraggio Attivo</h2>
          <p className="muted">Nota operativa e segnali aggiornati in tempo reale.</p>
        </div>
          {/* Contatori informativi: non filtrano piu' l'elenco. Per scegliere
              cosa vedere prima si usano le tessere degli assi qui sotto. */}
          <div className="monitor-header-kpis">
            <span className="monitor-kpi"><b>{totalCount}</b> monitorati</span>
            <span className={`monitor-kpi ${entraCount ? "kpi-enter" : ""}`}><b>{entraCount}</b> entra</span>
            <span className={`monitor-kpi ${osservaCount ? "kpi-watch" : ""}`}><b>{osservaCount}</b> osserva</span>
            <span className="monitor-kpi"><b>{withNotesCount}</b> con note</span>
          </div>
      </div>

      {/* Aggiunta di un titolo: in alto e richiudibile, perche' su telefono i
          quattro campi occupavano meta' schermo. Si apre da solo se c'e' un
          messaggio da leggere, cosi' non passa inosservato. */}
      <details className="monitor-add-compact" open={Boolean(error || added)}>
        <summary>
          <span>➕ Aggiungi un titolo al monitor</span>
        </summary>
        <form className="monitor-add-form" onSubmit={handleQuickAdd}>
          <input
            className="monitor-ticker-input"
            type="text"
            placeholder="Ticker o nome (es. LTMC.MI, Lottomatica)"
            value={newTicker}
            onChange={(e) => { setNewTicker(e.target.value); if (added) setAdded(""); if (error) setError(""); }}
            required
          />
          <select
            className="monitor-market-select"
            value={newMarket}
            onChange={(e) => setNewMarket(e.target.value)}
          >
            {markets.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          <input
            className="monitor-note-input"
            type="text"
            placeholder="Nota opzionale (es. breakout sopra 12.20)"
            value={newNote}
            onChange={(e) => setNewNote(e.target.value)}
          />
          <button type="submit" className="btn primary monitor-add-button" disabled={adding || !newTicker.trim()}>
            {adding ? "Aggiungo..." : "+ Aggiungi a Monitor"}
          </button>
        </form>
      </details>

      {error && <div className="error-banner">{error}</div>}
      {added && <div className="monitor-added-banner" role="status">{added}</div>}

      {/* Fotografia dei titoli monitorati: componente condiviso con la tab All,
          cosi' i due posti non possono divergere. I conteggi riguardano sempre
          tutti i titoli; il clic mette quel valore IN TESTA all'ordine, senza
          nascondere nulla. */}
      <AxisTiles
        items={items}
        active={testaAttiva}
        onSelect={(selezione) => {
          // La dimensione cliccata comanda l'ordine da qui in avanti.
          setDimensione(selezione.kind);
          setRango((corrente) => ({
            ...corrente,
            [selezione.kind]: selezione.value,
          }));
        }}
      />


      {/* Filter / Search inside Monitor + selettore visualizzazione */}
      {items.length > 0 && (
        <div className="monitor-filter-row">
          <div className="view-switch" role="group" aria-label="Visualizzazione monitor">
            <button className={view === "cards" ? "active" : ""} aria-pressed={view === "cards"} onClick={() => changeView("cards")}>Schede</button>
            <button className={view === "table" ? "active" : ""} aria-pressed={view === "table"} onClick={() => changeView("table")}>Tabella</button>
            <button className={view === "list" ? "active" : ""} aria-pressed={view === "list"} onClick={() => changeView("list")}>Lista</button>
          </div>
          {/* Scelta del mercato, come nella tab All. Solo mercati veri: le liste
              personali arrivano dal backend come "WL:nome" e qui non servono. */}
          <MarketChips
            markets={["Tutti", ...markets.filter((m) => m !== "Preferite" && !m.startsWith("WL:"))]}
            market={mercatoMostrato}
            onSelect={setMercatoMostrato}
            nomeProprio={() => null}
          />
          <input
            className="monitor-filter-input"
            type="text"
            placeholder="🔍 Filtra nei titoli monitorati..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
          />
          <div className="monitor-filter-count" style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
            {filteredItems.length === totalCount
              ? `${totalCount} titoli monitorati`
              : `Visualizzati ${filteredItems.length} di ${totalCount} titoli`}
          </div>
        </div>
      )}

      {alertRow ? (() => {
        const src = String(alertRow.WL_Source_Market || "MIB30");
        const tk = String(alertRow.Ticker || "").toUpperCase();
        const key = `${src}::${tk}`;
        const busy = Boolean(alertBusyMap[key]);
        const active = Boolean(alertMap[key]);
        return (
          <div className="modal-backdrop" onClick={() => setAlertRow(null)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
              <div className="modal-header">
                <div><h3 style={{ margin: 0 }}>🔔 Alert rapido</h3><div style={{ color: "var(--text-muted)", marginTop: 4 }}>{tk} · {src}</div></div>
                <button className="btn-close" onClick={() => setAlertRow(null)}>✕</button>
              </div>
              <div className="modal-body" style={{ display: "grid", gap: 10 }}>
                <select value={alertField} onChange={(e) => setAlertField(e.target.value as QuickAlertField)}>
                  <option value="Close">Close</option>
                  <option value="RSI">RSI</option>
                  <option value="Williams_R">Williams %R</option>
                  <option value="MACD_vs_Signal">S3</option>
                  <option value="SIG_MA_SAR">SARMA</option>
                  <option value="Stoch_KvsD">Stoch K-D</option>
                  <option value="DI_diff">DI+ - DI-</option>
                </select>
                <div className="watchlist-mode">
                  <button className={alertOp === ">" ? "quick-bar active" : "quick-bar"} onClick={() => setAlertOp(">")}>&gt;</button>
                  <button className={alertOp === "<" ? "quick-bar active" : "quick-bar"} onClick={() => setAlertOp("<")}>&lt;</button>
                </div>
                <input value={alertValue} onChange={(e) => setAlertValue(e.target.value)} placeholder="Valore soglia" />
                {alertMsg ? <div className="muted">{alertMsg}</div> : null}
              </div>
              <div className="modal-footer" style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                {active ? <button className="btn ghost remove-btn" disabled={busy} onClick={deleteAlert}>Rimuovi alert</button> : <div />}
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="btn ghost" onClick={() => setAlertRow(null)}>Chiudi</button>
                  <button className="btn primary" disabled={busy} onClick={saveAlert}>{active ? "Aggiorna alert" : "Crea alert"}</button>
                </div>
              </div>
            </div>
          </div>
        );
      })() : null}

      {/* Monitor cards */}
      {isLoading ? (
        <div style={{ textAlign: "center", padding: 40, color: "var(--text-muted)" }}>
          Caricamento dati monitor in corso...
        </div>
      ) : filteredItems.length === 0 ? (
        <div style={{ textAlign: "center", padding: "50px 20px", background: "var(--bg-card, #262626)", borderRadius: 10, border: "1px solid var(--border-color, #333)" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: 10 }}>🎯</div>
          {items.length > 0 ? (
            /* Ci sono titoli monitorati, ma nessuno corrisponde a cio' che stai
               guardando: non dire "non hai titoli", sarebbe falso. */
            <>
              <h3 style={{ margin: "0 0 8px 0" }}>Nessun titolo per questa selezione</h3>
              <p style={{ color: "var(--text-muted)", margin: "0 0 16px 0", maxWidth: 460, marginLeft: "auto", marginRight: "auto" }}>
                Hai <strong>{items.length}</strong> titoli monitorati, ma nessuno corrisponde
                {mercatoMostrato !== "Tutti" ? <> al mercato <strong>{mercatoMostrato}</strong></> : null}
                {filterText.trim() ? <> alla ricerca <strong>“{filterText.trim()}”</strong></> : null}.
              </p>
              <div style={{ display: "flex", gap: ".5rem", justifyContent: "center", flexWrap: "wrap" }}>
                {mercatoMostrato !== "Tutti" ? (
                  <button type="button" className="btn ghost" onClick={() => setMercatoMostrato("Tutti")}>Mostra tutti i mercati</button>
                ) : null}
                {filterText.trim() ? (
                  <button type="button" className="btn ghost" onClick={() => setFilterText("")}>Togli la ricerca</button>
                ) : null}
              </div>
            </>
          ) : (
            <>
              <h3 style={{ margin: "0 0 8px 0" }}>Nessun titolo in monitoraggio</h3>
              <p style={{ color: "var(--text-muted)", margin: "0 0 16px 0", maxWidth: 460, marginLeft: "auto", marginRight: "auto" }}>
                Aggiungi i tuoi titoli chiave premendo il pulsante <strong>+ Monitor</strong> sulle card delle watchlist o inserendo il ticker qui sopra.
              </p>
            </>
          )}
        </div>
      ) : view === "list" ? (
        <>
        {/* Nessuna barra "Ordina per": in lista l'ordine lo decide la tessera
            cliccata, che mette il suo valore in testa. */}
        <DenseList
          rows={righeOrdinate}
          emptyText="Nessun titolo monitorato corrisponde al filtro."
          renderActions={(row) => {
            const tk = String(row.Ticker || "").trim();
            const src = String(row.WL_Source_Market || "MIB30");
            const chiaveAlert = `${src}::${tk.toUpperCase()}`;
            return (
              <>
                <button type="button" className="btn" onClick={() => onChart(row)}>Grafico</button>
                <button type="button" className="btn ghost" onClick={() => onAi(row)}>AI</button>
                <button type="button" className="btn ghost" onClick={() => onNews(tk)}>News</button>
                <button type="button" className="btn ghost" onClick={() => onOpenNoteModal(row)}>Dettagli</button>
                <button
                  type="button"
                  className={alertMap[chiaveAlert] ? "btn alert-on" : "btn ghost"}
                  onClick={() => openAlertBox(row)}
                >
                  {alertMap[chiaveAlert] ? "Alert ON" : "Alert"}
                </button>
              </>
            );
          }}
        />
        </>
      ) : view === "table" ? (
        <MonitorTable
          rows={filteredItems}
          onChart={onChart}
          onAi={onAi}
          onNews={onNews}
          onOpenNoteModal={onOpenNoteModal}
          onRemoveMonitor={onRemoveMonitor}
          openAlertBox={openAlertBox}
          alertMap={alertMap}
        />
      ) : (
        <div className="monitor-card-grid">
          {filteredItems.map((row) => {
            const tk = String(row.Ticker || "").trim();
            const nm = String(row.Name || tk);
            const src = String(row.WL_Source_Market || "MIB30");
            const note = String(row.Monitor_Note || "").trim();
            const phase = String(row.Market_Phase || "-");
            const detail = String(row.Trend_Phase_Detail || "").replace(/_/g, " ");
            const entry = String(row.Entry_Signal || "ATTENDI").toUpperCase();

            return (
              <article className="monitor-card" key={`${src}-${tk}`}>
                <header className="monitor-card-head">
                  <div className="monitor-card-id">
                    <strong>{tk}</strong>
                    <span>{nm}</span>
                    <small>{src}</small>
                  </div>
                  <div className="monitor-card-price">
                    <b>{num(row.Close, 3)}</b>
                    <em style={{ color: pctColor(row.PCTV_1D) }}>{pct(row.PCTV_1D)}</em>
                  </div>
                </header>

                {/* Riga decisionale: segnale, fase e nota in evidenza */}
                <div className="monitor-card-signal">
                  <span
                    className={`pill ${entrySignalClass(entry)}`}
                    title="Indicazione d'ingresso: sintesi di azione operativa, stato di mercato e liquidità"
                  >
                    {entry === "ENTRA" ? "✓ ENTRA" : entry === "OSSERVA" ? "◉ OSSERVA" : entry === "EVITA" ? "✕ EVITA" : "○ ATTENDI"}
                  </span>
                  <span className="monitor-phase" title="Stato di mercato calcolato dal trading state">
                    {phase}{detail && detail !== phase && phase.toUpperCase() !== "LATERALE" ? ` · ${detail}` : ""}
                  </span>
                  <span className="monitor-liq" title="Liquidità del titolo (OK / LOW / AVOID)">
                    LIQ <b className={String(row.Liquidity ?? "").toUpperCase() === "OK" ? "good" : "bad"}>{String(row.Liquidity ?? "-")}</b>
                  </span>
                </div>
                {note ? <p className="monitor-note">📝 {note}</p> : null}

                {/* Metriche raggruppate per uso: livelli in tono neutro, solo i
                    giudizi (variazioni, direzione) hanno colore semantico. */}
                <div className="monitor-groups">
                  <div className="monitor-group">
                    <span className="monitor-group-title">Trend</span>
                    <div className="monitor-metrics">
                      <span>ADX <b>{num(row.ADX, 1)}</b></span>
                      <span>DI+ <b className="good">{num(row.PLUS_DI, 1)}</b></span>
                      <span>DI− <b className="bad">{num(row.MINUS_DI, 1)}</b></span>
                      <span>SARMA <b className={(toNum(row.SIG_MA_SAR) ?? 0) >= 0 ? "good" : "bad"}>{num(row.SIG_MA_SAR, 0)}</b></span>
                      <span>Alligator <b style={{ color: alligatorColor(row.Signal6) }}>{String(row.Signal6 ?? "-")}{row.Signal6_Trend_Days !== undefined ? ` (${row.Signal6_Trend_Days}g)` : ""}</b></span>
                    </div>
                  </div>

                  <div className="monitor-group">
                    <span className="monitor-group-title">Momentum</span>
                    <div className="monitor-metrics">
                      <span>RSI <b>{num(row.RSI, 0)}</b></span>
                      <span>Stoch <b>{num(row.Stoch_K, 0)}/{num(row.Stoch_D, 0)}</b></span>
                      <span>willR <b>{num(row.Williams_R, 0)}</b></span>
                      <span>MACD <b style={{ color: s3Color(row.MACD_vs_Signal) }}>{num(row.MACD, 3)}</b></span>
                      <span title="Striscia MACD sopra/sotto il segnale">MACD−Signal <b style={{ color: s3Color(row.MACD_vs_Signal) }}>{num(row.MACD_vs_Signal, 0)}</b></span>
                    </div>
                  </div>

                  <div className="monitor-group">
                    <span className="monitor-group-title">Performance e contesto</span>
                    <div className="monitor-metrics">
                      <span>1D <b style={{ color: pctColor(row.PCTV_1D) }}>{pct(row.PCTV_1D)}</b></span>
                      <span>5D <b style={{ color: pctColor(row.PCTV_5D) }}>{pct(row.PCTV_5D)}</b></span>
                      <span>10D <b style={{ color: pctColor(row.PCTV_10D) }}>{pct(row.PCTV_10D)}</b></span>
                      <span>30D <b style={{ color: pctColor(row.PCTV_30D) }}>{pct(row.PCTV_30D)}</b></span>
                      <span>180D <b style={{ color: pctColor(row.PCTV_180D) }}>{pct(row.PCTV_180D)}</b></span>
                      <span>TECH <b style={{ color: techColor(row.TECH_SCORE) }}>{num(row.TECH_SCORE, 0)}</b></span>
                      <span>VOL <b>{fmtVol(row.Volume)}</b></span>
                    </div>
                  </div>

                  <div className="monitor-group">
                    <span className="monitor-group-title">Pattern</span>
                    <div className="monitor-metrics">
                      <span>S2 <b>{num(row.Pattern_S2_Days_Ago, 0)}g</b></span>
                      <span title="Sedute trascorse dall'ultimo pattern S3">S3 <b>{num(row.Pattern_S3_Days_Ago, 0)}g fa</b></span>
                      <span>S4 <b>{num(row.Pattern_S4_Days_Ago, 0)}g</b></span>
                      <span>S8 <b>{num(row.Pattern_S8_Days_Ago, 0)}g</b></span>
                    </div>
                  </div>
                </div>

                {/* Azioni: una primaria, il resto nel menu per non rubare la scena */}
                <div className="monitor-card-actions">
                  <button type="button" className="btn primary" onClick={(e) => { e.stopPropagation(); onChart(row); }}>Grafico</button>
                  <button type="button" className="btn ghost" onClick={(e) => { e.stopPropagation(); setActionsFor(actionsFor === `${src}-${tk}` ? null : `${src}-${tk}`); }}>
                    ⋯ Altro
                  </button>
                  <button type="button" className="btn ghost danger" onClick={(e) => { e.stopPropagation(); onRemoveMonitor(tk, src); }}>Rimuovi</button>
                </div>
                {actionsFor === `${src}-${tk}` ? (
                  <div className="monitor-card-more">
                    <button type="button" className="btn ghost" onClick={() => { setActionsFor(null); onAi(row); }}>AI</button>
                    <button type="button" className="btn ghost" onClick={() => { setActionsFor(null); onNews(tk); }}>News</button>
                    <button type="button" className="btn ghost" onClick={() => { setActionsFor(null); onOpenNoteModal(row); }}>Dettagli</button>
                    <button type="button" className={alertMap[`${src}::${tk.toUpperCase()}`] ? "btn alert-on" : "btn ghost"} onClick={() => { setActionsFor(null); openAlertBox(row); }}>
                      {alertMap[`${src}::${tk.toUpperCase()}`] ? "Alert ON" : "Alert"}
                    </button>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}






