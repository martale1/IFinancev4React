import { useMemo, useState } from "react";
import type { WatchlistRow } from "../types";
import mib30Sectors from "../data/mib30_sectors.json";
import { ORDINE_ETC, ORDINE_TIPI, isLiquido, tipoEtc, tipoEtf } from "../etfTypes";

/**
 * Heatmap: il COLORE indica la decisione, non l'entita' del movimento.
 *
 * Prima le tessere erano colorate con `PCTV_1D` (quanto si e' mosso oggi) ma
 * dentro scrivevano `Market_Phase`. Il risultato era che i titoli in ribasso che
 * oggi rimbalzavano apparivano VERDI e intensi, con scritto RIBASSO: le tessere
 * piu' accese della mappa erano proprio quelle che il resto del sistema
 * classifica come EVITA. Misurato sui MIB30:
 *
 *   LDO.MI   +1,92%  RIBASSO  EVITA  ADX 40   -> verde intenso
 *   STLAM.MI +2,63%  RIBASSO  EVITA  ADX 25   -> verde intenso
 *   G.MI     +1,16%  RIBASSO  EVITA  ADX 32   -> verde
 *
 * Inoltre il colore non discriminava: l'80% dei titoli era "in rialzo", quindi
 * quasi tutto era verde.
 *
 * Ora il colore e' l'indicazione (i quattro colori delle card), la variazione
 * resta scritta sulla tessera, e i riepiloghi contano le indicazioni invece di
 * "Sopra SAR" e "Alligator Up", che venivano dal modello precedente.
 *
 * La modalita' "Trend e forza" mostra i QUATTRO ASSI veri invece delle 4
 * conferme di prima (SAR, Alligator, ADX >= 20, DI+): quel punteggio era una
 * scala a parte, non coincideva con le indicazioni e usava ADX >= 20 mentre gli
 * assi usano >= 22.
 */

type PeriodKey = "PCTV_1D" | "PCTV_5D" | "PCTV_10D" | "PCTV_30D" | "PCTV_180D";
type ViewMode = "indicazioni" | "performance" | "assi";
type LayoutMode = "sections" | "sectorGrid";
type Props = { market: string; rows: WatchlistRow[]; alertMap: Record<string, boolean>; loading?: boolean; error?: string; onChart: (row: WatchlistRow) => void };

const PERIODS: Array<{ key: PeriodKey; label: string }> = [
  { key: "PCTV_1D", label: "1D" }, { key: "PCTV_5D", label: "5D" }, { key: "PCTV_10D", label: "10D" },
  { key: "PCTV_30D", label: "30D" }, { key: "PCTV_180D", label: "180D" },
];
const SECTORS = mib30Sectors as Record<string, string>;

/** I quattro colori delle indicazioni, gli stessi delle card e delle tessere. */
const COLORE_INDICAZIONE: Record<string, string> = {
  ENTRA: "#4ade80",
  OSSERVA: "#93c5fd",
  ATTENDI: "#cbd5e1",
  EVITA: "#fca5a5",
};
const INDICAZIONI = ["ENTRA", "OSSERVA", "ATTENDI", "EVITA"] as const;
/** Un valore mancante non deve sparire dalla mappa: colore neutro e leggibile. */
const COLORE_SCONOSCIUTO = "#94a3b8";

function num(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") { const parsed = Number(value.replace(",", ".").trim()); return Number.isFinite(parsed) ? parsed : null; }
  return null;
}
const tickerOf = (row: WatchlistRow) => String(row.Ticker ?? "").trim().toUpperCase();
const alertKey = (market: string, ticker: string) => `${market.trim().toUpperCase()}::${ticker.trim().toUpperCase()}`;
/** Testo scuro sulle tessere chiare: i quattro colori sono tutti pastello. */
const TESTO_SCURO = "#0d1b2a";

/** L'indicazione del titolo, normalizzata: ENTRA, OSSERVA, ATTENDI, EVITA. */
function indicazioneDi(row: WatchlistRow): string {
  const grezzo = String(row.Entry_Signal ?? "").trim().toUpperCase();
  return grezzo || "ATTENDI";
}
function coloreDi(row: WatchlistRow): string {
  return COLORE_INDICAZIONE[indicazioneDi(row)] ?? COLORE_SCONOSCIUTO;
}
function assiDi(row: WatchlistRow): string {
  const due = (v: unknown, fallback: string) => {
    const s = String(v ?? "").trim();
    return s ? s.replace(/^FORTE_/, "").replace(/^FORTE/, "FORTE ") : fallback;
  };
  return `${due(row.Direzione_Trend, "?")} · ${due(row.Forza_Trend, "?")} · ${due(row.Momento_Trend, "?")} · ${due(row.Rischio_Trend, "?")}`;
}
function median(values: number[]): number | null {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b); const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}
function contaIndicazioni(rows: WatchlistRow[]): Record<string, number> {
  const out: Record<string, number> = { ENTRA: 0, OSSERVA: 0, ATTENDI: 0, EVITA: 0 };
  rows.forEach((row) => { const k = indicazioneDi(row); out[k] = (out[k] ?? 0) + 1; });
  return out;
}

export default function MarketHeatmapPanel({ market, rows, alertMap, loading, error, onChart }: Props) {
  const [period, setPeriod] = useState<PeriodKey>("PCTV_1D");
  const [mode, setMode] = useState<ViewMode>("indicazioni");
  const [layout, setLayout] = useState<LayoutMode>("sectorGrid");
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const isMib = market.toUpperCase() === "MIB30";
  const isEtf = market.toUpperCase() === "ETF";
  const isEtc = market.toUpperCase() === "ETC";
  // ETF ed ETC si raggruppano per tipologia: sono "panieri", e 419 ETF o 93 ETC
  // in un blocco unico non si leggono. Il DAX sono 40 aziende singole e resta
  // piatto, come gli altri mercati.
  const perTipologia = isEtf || isEtc;
  // Sigla per i testi: il filtro ora vale per ETF ed ETC, non solo per gli ETF.
  const sigla = isEtc ? "ETC" : "ETF";
  // Il filtro esiste dove ci sono davvero titoli non negoziabili: sugli ETF
  // (364 su 783) e sugli ETC (57 su 93). Sul DAX tutti e 40 sono liquidi,
  // quindi li' non comparirebbe comunque e non lo aggiungo.
  const [soloLiquidi, setSoloLiquidi] = useState(true);
  const soloLiquidiAttivo = perTipologia && soloLiquidi;

  const mappedRows = useMemo(
    () => isMib ? rows.filter((row) => Boolean(SECTORS[tickerOf(row)])) : rows,
    [isMib, rows],
  );
  const liquidi = useMemo(
    () => mappedRows.filter((row) => isLiquido(row as Record<string, unknown>)),
    [mappedRows],
  );
  const mostrati = soloLiquidiAttivo ? liquidi : mappedRows;
  const nascosti = mappedRows.length - liquidi.length;

  const groups = useMemo(() => {
    if (perTipologia) {
      // Non esiste una colonna di categoria: il gruppo e' la tipologia dedotta
      // dal nome (vedi etfTypes.ts). L'ordine e' quello dichiarato, non
      // alfabetico, cosi' i gruppi grandi restano in alto.
      const chiave = (row: WatchlistRow) =>
        isEtc ? tipoEtc(row as Record<string, unknown>) : tipoEtf(row as Record<string, unknown>);
      const ordine = isEtc ? ORDINE_ETC : ORDINE_TIPI;
      const perTipo = new Map<string, WatchlistRow[]>();
      mostrati.forEach((row) => {
        const t = chiave(row);
        perTipo.set(t, [...(perTipo.get(t) ?? []), row]);
      });
      return ordine
        .filter((t) => (perTipo.get(t)?.length ?? 0) > 0)
        .map((t) => [t, perTipo.get(t) as WatchlistRow[]] as [string, WatchlistRow[]]);
    }
    const result = new Map<string, WatchlistRow[]>();
    mostrati.forEach((row) => {
      const settore = isMib ? SECTORS[tickerOf(row)] : "Tutti i titoli";
      result.set(settore, [...(result.get(settore) ?? []), row]);
    });
    return [...result.entries()].sort(([a], [b]) => a.localeCompare(b, "it"));
  }, [isEtc, isMib, perTipologia, mostrati]);
  const visibleGroups = selectedSector ? groups.filter(([sector]) => sector === selectedSector) : groups;

  // Conteggi complessivi per indicazione: sostituiscono "80% in rialzo / sopra
  // SAR / Alligator Up", che descrivevano il movimento o il modello precedente.
  const totali = useMemo(() => contaIndicazioni(mostrati), [mostrati]);
  const stats = useMemo(() => {
    const values = mostrati.map((row) => num(row[period])).filter((value): value is number => value !== null);
    // La scala del colore si calcola UNA volta: dentro il ciclo delle tessere
    // sarebbe O(n^2), e con un mercato da 1684 titoli si sente.
    const sortedAbs = values.map(Math.abs).sort((a, b) => a - b);
    return {
      alerts: mostrati.filter((row) => alertMap[alertKey(String(row.WL_Source_Market ?? market), tickerOf(row))]).length,
      scala: Math.max(sortedAbs[Math.max(0, Math.ceil(sortedAbs.length * 0.9) - 1)] ?? 0, 0.25),
    };
  }, [alertMap, mostrati, market, period]);

  if (loading) return <p>Carico heatmap {market}...</p>;
  if (error) return <p className="err">{error}</p>;
  if (!rows.length) return <p>Nessun titolo disponibile per la heatmap di {market}.</p>;
  const etichettaPeriodo = (PERIODS.find((p) => p.key === period)?.label ?? "").toLowerCase();

  return <section className="heatmap-panel">
    <div className="heatmap-header">
      <div><h2>Heatmap · {market}{isMib ? " per settore" : perTipologia ? " per tipologia" : ""}</h2><div className="muted">Dati dall'ultimo Excel di analisi. Clicca un titolo per aprire il grafico.</div></div>
      <div className="heatmap-controls">
        <div className="heatmap-periods" aria-label="Cosa mostra il colore">
          <button className={mode === "indicazioni" ? "quick-bar active" : "quick-bar"} onClick={() => setMode("indicazioni")}>Indicazioni</button>
          <button className={mode === "performance" ? "quick-bar active" : "quick-bar"} onClick={() => setMode("performance")}>Performance</button>
          <button className={mode === "assi" ? "quick-bar active" : "quick-bar"} onClick={() => setMode("assi")}>Trend e forza</button>
        </div>
        {/* Il filtro esiste dove ci sono titoli non negoziabili: ETF (364 su
            783) ed ETC (57 su 93). Sul DAX tutti e 40 sono liquidi, quindi li'
            non comparirebbe comunque. */}
        {perTipologia ? (
          <div className="heatmap-periods" aria-label="Filtro liquidità">
            <button
              className={soloLiquidi ? "quick-bar active" : "quick-bar"}
              onClick={() => { setSoloLiquidi(!soloLiquidi); setSelectedSector(null); }}
              title={soloLiquidi
                ? `Mostrati solo i ${liquidi.length} ${sigla} negoziabili: ${nascosti} illiquidi nascosti. Premi per vederli tutti.`
                : `Mostrati tutti i ${mappedRows.length} ${sigla}, compresi i ${nascosti} illiquidi.`}
              aria-pressed={soloLiquidi}
            >
              Solo liquidi{soloLiquidi ? ` · ${liquidi.length}` : ""}
            </button>
          </div>
        ) : null}
        {isMib ? <div className="heatmap-periods heatmap-layout-switch" aria-label="Formato heatmap">
          <button className={layout === "sections" ? "quick-bar active" : "quick-bar"} onClick={() => setLayout("sections")}>☰ Sezioni</button>
          <button className={layout === "sectorGrid" ? "quick-bar active" : "quick-bar"} onClick={() => setLayout("sectorGrid")}>▦ Griglia settoriale</button>
        </div> : null}
        {/* Il periodo riguarda la variazione, che resta scritta anche quando il
            colore e' l'indicazione: serve in tutte le modalita' tranne gli assi. */}
        {mode !== "assi" ? <div className="heatmap-periods" aria-label="Periodo della variazione">{PERIODS.map((item) => <button key={item.key} className={period === item.key ? "quick-bar active" : "quick-bar"} onClick={() => setPeriod(item.key)}>{item.label}</button>)}</div> : null}
      </div>
    </div>

    {/* In alto i conteggi delle indicazioni: e' il dato con cui si decide. */}
    <div className="heatmap-summary">
      {INDICAZIONI.map((ind) => <div key={ind}>
        <strong style={{ color: COLORE_INDICAZIONE[ind] }}>{totali[ind] ?? 0}</strong>
        <span>{" "}{ind.toLowerCase()}</span>
      </div>)}
      <div><strong>{stats.alerts}</strong><span> alert attivi</span></div>
    </div>

    {(isMib || perTipologia) && groups.length > 1 ? <div className="sector-filter-row">
      <button className={!selectedSector ? "sector-filter active" : "sector-filter"} onClick={() => setSelectedSector(null)}>
        {perTipologia ? "Tutte le tipologie" : "Tutti i settori"}
      </button>
      {groups.map(([sector, items]) => <button key={sector} className={selectedSector === sector ? "sector-filter active" : "sector-filter"} onClick={() => setSelectedSector(selectedSector === sector ? null : sector)}>{sector} <small>{items.length}</small></button>)}
    </div> : null}

    <div className={`sector-groups ${layout === "sectorGrid" && isMib ? "grid-layout" : "sections-layout"}`}>{visibleGroups.map(([sector, sectorRows]) => {
      const values = sectorRows.map((row) => num(row[period])).filter((value): value is number => value !== null);
      const sectorMedian = median(values);
      const perIndicazione = contaIndicazioni(sectorRows);
      const sorted = [...sectorRows].sort((a, b) => (num(b[period]) ?? -Infinity) - (num(a[period]) ?? -Infinity));
      const sectorAlerts = sectorRows.filter((row) => alertMap[alertKey(String(row.WL_Source_Market ?? market), tickerOf(row))]).length;
      return <article className="sector-group" key={sector}>
        <div className="sector-heading"><button onClick={() => (isMib || perTipologia) && setSelectedSector(selectedSector === sector ? null : sector)} title={perTipologia ? "Mostra solo questa tipologia" : "Mostra solo questo settore"}><strong>{sector}</strong><span>{sectorRows.length} titoli</span></button>
          <div className={`sector-median ${(sectorMedian ?? 0) >= 0 ? "positive" : "negative"}`}>Mediana {sectorMedian === null ? "n/d" : `${sectorMedian >= 0 ? "+" : ""}${sectorMedian.toFixed(2)}%`}</div></div>

        {/* Le tipologie sono dedotte dal nome, non lette da una colonna: quando
            non si riconosce il nome lo si dichiara, invece di far sembrare
            precisa una stima che non lo e'. */}
        {perTipologia && sector === "Non riconosciuto" ? (
          <p className="heatmap-excluded">
            Tipologia non deducibile dal nome (nomi troncati dai fornitori, es. «CRP BD», «EQU»).
            Riconosciute per nome: il {isEtc ? "96%" : "79%"} dei titoli.
          </p>
        ) : null}

        {/* Riepilogo: le indicazioni del settore, cioe' come e' messo davvero,
            poi la variazione (che ora non e' piu' il colore) e i dettagli. */}
        <div className="sector-conteggi">
          {INDICAZIONI.map((ind) => <span key={ind} className={perIndicazione[ind] ? "conteggio acceso" : "conteggio"} style={perIndicazione[ind] ? { color: COLORE_INDICAZIONE[ind], borderColor: COLORE_INDICAZIONE[ind] } : undefined}>
            <b>{perIndicazione[ind] ?? 0}</b> {ind.toLowerCase()}
          </span>)}
        </div>

        <details className="sector-details"><summary>Riepilogo settore</summary><div>
          <span>Variazione {etichettaPeriodo} mediana <b>{sectorMedian === null ? "n/d" : `${sectorMedian >= 0 ? "+" : ""}${sectorMedian.toFixed(2)}%`}</b></span>
          <span>Positivi <b>{sectorRows.filter((row) => (num(row[period]) ?? 0) > 0).length}/{sectorRows.length}</b></span>
          <span>Alert <b>{sectorAlerts}</b></span>
          <span>Migliore <b>{tickerOf(sorted[0])} {num(sorted[0]?.[period])?.toFixed(2) ?? "n/d"}%</b></span><span>Peggiore <b>{tickerOf(sorted[sorted.length - 1] ?? {})} {num(sorted[sorted.length - 1]?.[period])?.toFixed(2) ?? "n/d"}%</b></span>
        </div></details>

        <div className="heatmap-grid">{sectorRows.map((row) => {
          const ticker = tickerOf(row) || "-"; const value = num(row[period]);
          const sourceMarket = String(row.WL_Source_Market ?? market); const hasAlert = Boolean(alertMap[alertKey(sourceMarket, ticker)]);
          const variazione = value === null ? "n/d" : `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
          const ind = indicazioneDi(row);
          // In "Performance" il colore torna a essere l'entita' del movimento,
          // come prima: la modalita' esiste ancora, non e' piu' quella di default.
          const intensita = value === null ? 0 : Math.min(Math.abs(value) / stats.scala, 1);
          const sfondo = mode === "performance"
            ? (value === null ? "rgba(100,116,139,.28)" : value >= 0 ? `rgba(22,163,74,${0.18 + intensita * 0.7})` : `rgba(220,38,38,${0.18 + intensita * 0.7})`)
            : coloreDi(row);
          const testoSfondo = mode === "performance" ? undefined : TESTO_SCURO;
          return <button key={`${sourceMarket}-${ticker}`} className={hasAlert ? "heatmap-tile has-alert" : "heatmap-tile"} style={{ background: sfondo, color: testoSfondo }} onClick={() => onChart(row)} title={`${String(row.Name ?? ticker)} · ${variazione} · ${ind} · clicca per il grafico`}>
            <span className="heatmap-ticker">{ticker} <small className={mode === "performance" ? (value !== null && value >= 0 ? "positive" : "negative") : ""} style={mode === "performance" ? undefined : { color: TESTO_SCURO, opacity: .85 }}>{variazione}</small></span>
            <span className="heatmap-value">{ind}</span>
            <span className="heatmap-phase">{mode === "assi" ? assiDi(row) : `variazione ${etichettaPeriodo}`}</span>
            {hasAlert ? <span className="heatmap-alert">🔔</span> : null}
          </button>;
        })}</div>
      </article>;
    })}</div>

    {(isMib && rows.length > mappedRows.length) || (soloLiquidiAttivo && nascosti > 0) ? (
      <p className="heatmap-excluded">
        {isMib && rows.length > mappedRows.length
          ? `${rows.length - mappedRows.length} elementi non appartenenti al mapping MIB esclusi dalla vista settoriale. `
          : ""}
        {soloLiquidiAttivo && nascosti > 0
          ? `${nascosti} ${sigla} non mostrati perché illiquidi (liquidità non OK). Usa "Solo liquidi" per vederli.`
          : ""}
      </p>
    ) : null}

    {/* Legenda: in "Performance" e' una scala, nelle altre e' l'elenco dei colori. */}
    {mode === "performance"
      ? <div className="heatmap-legend"><span>Ribasso forte</span><i className="legend-red"/><i className="legend-neutral"/><i className="legend-green"/><span>Rialzo forte</span></div>
      : <div className="heatmap-legend heatmap-legend-indicazioni">
        {INDICAZIONI.map((ind) => <span key={ind} className="voce"><i style={{ background: COLORE_INDICAZIONE[ind] }} />{ind.toLowerCase()}</span>)}
        <span className="muted">ogni tessera mostra la variazione {etichettaPeriodo}</span>
      </div>}
  </section>;
}
