import { useEffect, useMemo, useState, type ReactNode } from "react";
import type { WatchlistRow, QuickAlertField } from "../types";
import { analyzeChartImage } from "../api";


function quickAlertFieldLabel(field: QuickAlertField): string {
  if (field === "Close") return "prezzo";
  if (field === "MACD_vs_Signal") return "S3 (MACD-Signal)";
  if (field === "MACD_Hist") return "Istogramma MACD";
  if (field === "SIG_MA_SAR") return "SARMA";
  if (field === "Williams_R") return "willR";
  if (field === "Stoch_K") return "Stocastico %K";
  if (field === "Stoch_D") return "Stocastico %D";
  if (field === "Stoch_KvsD") return "Sk−Sd  (>0 = Sk sopra Sd, <0 = Sk sotto Sd)";
  if (field === "ADX") return "ADX (forza del trend)";
  if (field === "PLUS_DI") return "DI+ (forza rialzista)";
  if (field === "MINUS_DI") return "DI− (forza ribassista)";
  if (field === "DI_diff") return "DI+−DI−  (>0 = DI+ sopra DI−, trend rialzista)";
  if (field === "Signal6") return "Alligator";
  return field;
}

function toNum(v: unknown): number | null {
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  if (typeof v === "string") {
    const x = Number(v.replace(",", ".").trim());
    return Number.isNaN(x) ? null : x;
  }
  return null;
}

function num(v: unknown, digits = 2): string {
  const n = toNum(v);
  if (n === null) return "-";
  return n.toFixed(digits);
}

function renderInline(text: string, context: "body" | "list" = "body"): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, idx) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={idx} className={context === "list" ? "ai-label" : undefined}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function renderMessage(content: string) {
  const nodes: ReactNode[] = [];
  let listItems: ReactNode[] = [];
  let inCodeBlock = false;
  let codeContent = "";

  function flushList() {
    if (!listItems.length) return;
    nodes.push(<ul key={`ul-${nodes.length}`} style={{ margin: "0.5rem 0", paddingLeft: "1.2rem" }}>{listItems}</ul>);
    listItems = [];
  }

  function flushCodeBlock() {
    if (!codeContent) return;
    try {
      const parsed = JSON.parse(codeContent.trim());
      if (parsed.conditions) {
        nodes.push(
          <div key={`json-table-${nodes.length}`} className="table-wrap" style={{ marginTop: "0.6rem", marginBottom: "0.6rem" }}>
            <table style={{ background: "rgba(10,22,38,0.55)", border: "1px solid rgba(174,216,249,0.23)" }}>
              <thead>
                <tr>
                  <th style={{ color: "#38bdf8" }}>Indicatore</th>
                  <th style={{ color: "#38bdf8" }}>Trigger</th>
                  <th style={{ color: "#38bdf8" }}>Descrizione Condizione</th>
                </tr>
              </thead>
              <tbody>
                {parsed.conditions.map((c: any, i: number) => (
                  <tr key={i}>
                    <td style={{ fontWeight: "bold" }}>{c.indicator}</td>
                    <td style={{ color: "#fbbf24", fontFamily: "monospace" }}>{c.trigger}</td>
                    <td style={{ color: "#cbd5e1" }}>{c.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        codeContent = "";
        return;
      }
    } catch {
      // no-op, fall back to standard pre box
    }
    nodes.push(
      <pre key={`pre-${nodes.length}`} className="json" style={{ margin: "0.6rem 0", background: "rgba(8,18,34,0.85)" }}>
        <code>{codeContent.trim()}</code>
      </pre>
    );
    codeContent = "";
  }

  // Track ordered list items separately
  let orderedItems: ReactNode[] = [];
  let orderedStart = 1;

  function flushOrderedList() {
    if (!orderedItems.length) return;
    nodes.push(
      <ol key={`ol-${nodes.length}`} start={orderedStart} style={{ margin: "0.5rem 0", paddingLeft: "1.4rem" }}>
        {orderedItems}
      </ol>
    );
    orderedItems = [];
    orderedStart = 1;
  }

  const lines = String(content || "").split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    if (line.startsWith("```")) {
      if (inCodeBlock) {
        inCodeBlock = false;
        flushCodeBlock();
      } else {
        flushList();
        flushOrderedList();
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeContent += lines[i] + "\n";
      continue;
    }

    const bullet = line.match(/^[-*]\s+(.+)/);
    if (bullet) {
      listItems.push(<li key={`li-${i}`} style={{ margin: "0.2rem 0" }}>{renderInline(bullet[1], "list")}</li>);
      continue;
    }

    flushList();

    const mdHeading = line.match(/^#{1,3}\s+(.+)/);
    const boldOnlyHeading = line.match(/^\*\*([^*]{1,46})\*\*:?\s*$/);
    if (mdHeading || boldOnlyHeading) {
      nodes.push(<h4 key={`h-${i}`} style={{ marginTop: "0.8rem", marginBottom: "0.4rem", color: "#38bdf8" }}>{renderInline(mdHeading?.[1] ?? boldOnlyHeading?.[1] ?? line)}</h4>);
      continue;
    }

    nodes.push(<p key={`p-${i}`} style={{ margin: "0.4rem 0", lineHeight: "1.45" }}>{renderInline(line)}</p>);
  }

  flushList();
  flushCodeBlock();
  return nodes;
}

type Props = {
  open: boolean;
  ticker: string;
  snapshotClose?: number | null;
  isQuickChart?: boolean;
  levels?: {
    sl1?: number | null;
    sl2?: number | null;
    pbStop?: number | null;
    ppLevel?: number | null;
  };
  bars: number;
  chartType: "candlestick" | "line";
  onBarsChange: (v: number) => void;
  onTypeChange: (v: "candlestick" | "line") => void;
  imageUrl: string;
  onClose: () => void;

  // Alert system props
  row?: WatchlistRow | null;
  sourceMarket?: string;
  alertSet?: boolean;
  alertConfig?: {
    field: QuickAlertField;
    op: ">" | "<" | "==" | "!=";
    value: number | string | null;
  } | null;
  alertBusy?: boolean;
  onCreateAlert?: (input: {
    row: WatchlistRow;
    source_market: string;
    field: QuickAlertField;
    op: ">" | "<" | "==" | "!=";
    value: number | string;
  }) => Promise<string>;
  onRemoveAlert?: (input: { row: WatchlistRow; source_market: string }) => Promise<string>;
};

export default function ChartModal(props: Props) {
  const MAX_AUTO_RETRIES = 2;
  const QUICK_BARS = [10, 20, 70, 200];
  const [loading, setLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [forceLineFallback, setForceLineFallback] = useState(false);

  // Alert state variables
  const [showAlertTools, setShowAlertTools] = useState(false);
  const [alertField, setAlertField] = useState<QuickAlertField>("Close");
  const [alertOp, setAlertOp] = useState<">" | "<" | "==" | "!=">(">");
  const [alertValue, setAlertValue] = useState("");
  const [alertMsg, setAlertMsg] = useState("");

  // AI state variables
  const [aiLoading, setAiLoading] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiModel, setAiModel] = useState(() => window.localStorage.getItem("ifinance-openai-vision-model") || "gpt-4o");
  const [aiAnalysisType, setAiAnalysisType] = useState<"detailed" | "concise">("detailed");

  // Local state for bars input/slider to prevent backend request storms during dragging
  const [localBars, setLocalBars] = useState(props.bars);

  // Sync localBars with props.bars when parent changes (e.g. quick-bar click)
  useEffect(() => {
    setLocalBars(props.bars);
  }, [props.bars]);

  // Debounced parent update to trigger backend only after user stops dragging
  useEffect(() => {
    const timer = setTimeout(() => {
      if (localBars !== props.bars && localBars >= 10 && localBars <= 400) {
        props.onBarsChange(localBars);
      }
    }, 350);
    return () => clearTimeout(timer);
  }, [localBars, props.bars, props.onBarsChange]);

  const sarma = props.row ? toNum(props.row.SIG_MA_SAR) : null;
  const willR = props.row ? toNum(props.row.Williams_R) : null;
  const macdHist = props.row ? toNum(props.row.MACD_Hist) : null;
  const stochK = props.row ? toNum(props.row.Stoch_K) : null;
  const stochD = props.row ? toNum(props.row.Stoch_D) : null;
  const adx = props.row ? toNum(props.row.ADX) : null;
  const plusDI = props.row ? toNum(props.row.PLUS_DI) : null;
  const minusDI = props.row ? toNum(props.row.MINUS_DI) : null;
  const close = props.snapshotClose ?? (props.row ? toNum(props.row.Close) : null);

  // 1. Chart loading state management
  useEffect(() => {
    if (!props.open) return;
    setLoading(true);
    setHasError(false);
    setRetryCount(0);
    setForceLineFallback(false);
  }, [props.open, props.ticker, props.bars, props.chartType, props.imageUrl]);

  // 2. Alert form values and AI states reset only on ticker/open change
  useEffect(() => {
    if (!props.open) return;
    setShowAlertTools(false);
    setAlertField("Close");
    setAlertOp(">");
    setAlertValue(close !== null ? String(close) : "");
    setAlertMsg("");

    // Reset AI states
    setAiLoading(false);
    setAiAnalysis(null);
    setAiError(null);
  }, [props.open, props.ticker]);

  const src = useMemo(() => {
    if (!props.imageUrl) return "";
    let url = props.imageUrl;
    if (forceLineFallback) {
      try {
        const u = new URL(url);
        u.searchParams.set("chart_type", "line");
        url = u.toString();
      } catch {
        url = url.includes("chart_type=")
          ? url.replace("chart_type=candlestick", "chart_type=line")
          : `${url}${url.includes("?") ? "&" : "?"}chart_type=line`;
      }
    }
    const sep = url.includes("?") ? "&" : "?";
    return `${url}${sep}retry=${retryCount}`;
  }, [props.imageUrl, retryCount, forceLineFallback]);

  function retry() {
    setHasError(false);
    setLoading(true);
    setRetryCount((v) => v + 1);
  }

  function fmtPrice(v?: number | null): string {
    if (typeof v !== "number" || !Number.isFinite(v)) return "-";
    return v.toLocaleString("it-IT", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
  }

  function fmtPctFromClose(level?: number | null): string {
    const c = props.snapshotClose;
    if (typeof c !== "number" || !Number.isFinite(c) || typeof level !== "number" || !Number.isFinite(level)) return "-";
    const p = ((level / c) - 1) * 100;
    const sign = p > 0 ? "+" : "";
    return `${sign}${p.toFixed(2).replace(".", ",")}%`;
  }

  function pctClass(level?: number | null): string {
    const c = props.snapshotClose;
    if (typeof c !== "number" || !Number.isFinite(c) || typeof level !== "number" || !Number.isFinite(level)) return "neutral";
    return level >= c ? "up" : "down";
  }

  function applyAlertPreset() {
    if (props.alertConfig) {
      setAlertField(props.alertConfig.field);
      setAlertOp(props.alertConfig.op);
      if (props.alertConfig.value !== null) setAlertValue(String(props.alertConfig.value));
      return;
    }
    setAlertField("Close");
    setAlertOp(">");
    if (close !== null) setAlertValue(String(close));
  }

  async function createQuickAlert() {
    if (!props.ticker || !props.row || !props.onCreateAlert || !props.sourceMarket) return;
    let v: number | string;
    if (alertField === "Signal6") {
      v = alertValue.trim();
      if (!v) {
        setAlertMsg("Valore alert non valido.");
        return;
      }
    } else {
      const parsed = toNum(alertValue);
      if (parsed === null) {
        setAlertMsg("Valore alert non valido.");
        return;
      }
      v = parsed;
    }
    setAlertMsg("");
    try {
      const result = await props.onCreateAlert({
        row: props.row,
        source_market: props.sourceMarket,
        field: alertField,
        op: alertOp,
        value: v
      });
      setAlertMsg(result);
      setShowAlertTools(false);
    } catch (e) {
      setAlertMsg(String(e));
    }
  }

  async function removeQuickAlert() {
    if (!props.ticker || !props.row || !props.onRemoveAlert || !props.sourceMarket) return;
    setAlertMsg("");
    try {
      const result = await props.onRemoveAlert({
        row: props.row,
        source_market: props.sourceMarket
      });
      setAlertMsg(result);
      setShowAlertTools(false);
    } catch (e) {
      setAlertMsg(String(e));
    }
  }

  async function handleAskAi() {
    if (!props.ticker || !props.sourceMarket) return;
    setAiLoading(true);
    setAiError(null);
    setAiAnalysis(null);
    try {
      const resp = await analyzeChartImage({
        ticker: props.ticker,
        market: props.sourceMarket,
        bars: props.bars,
        chart_type: props.chartType,
        levels: props.levels ? {
          sl1: props.levels.sl1,
          sl2: props.levels.sl2,
          pbStop: props.levels.pbStop,
          ppLevel: props.levels.ppLevel
        } : null,
        model: aiModel,
        analysis_type: aiAnalysisType
      });
      setAiAnalysis(resp.analysis);
    } catch (e) {
      setAiError(String(e));
    } finally {
      setAiLoading(false);
    }
  }

  if (!props.open) return null;
  return (
    <div className="modal-backdrop" onClick={props.onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>Grafico {props.ticker}</h3>
          <button className="btn ghost" onClick={props.onClose}>
            Chiudi
          </button>
        </div>
        <div className="controls" style={{ display: "flex", flexWrap: "wrap", gap: "1rem", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.9rem", color: "#cfe5fa" }}>Barre:</span>
            <input
              type="number"
              min={10}
              max={400}
              step={5}
              value={localBars}
              onChange={(e) => {
                let val = Number(e.target.value);
                if (val > 400) val = 400;
                if (val < 10) val = 10;
                setLocalBars(val);
              }}
              style={{ width: "70px", padding: "4px 8px", borderRadius: "6px", border: "1px solid rgba(174,216,249,0.3)", background: "rgba(10,22,38,0.72)", color: "#cfe5fa" }}
            />
            <input
              type="range"
              min={10}
              max={400}
              step={5}
              value={localBars}
              onChange={(e) => setLocalBars(Number(e.target.value))}
              style={{ width: "140px", accentColor: "#3b82f6", cursor: "pointer", height: "8px", padding: 0 }}
            />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.9rem", color: "#cfe5fa" }}>Tipo:</span>
            <select
              value={props.chartType}
              onChange={(e) => props.onTypeChange(e.target.value as "candlestick" | "line")}
              style={{ padding: "4px 8px", borderRadius: "6px", border: "1px solid rgba(174,216,249,0.3)", background: "rgba(10,22,38,0.72)", color: "#cfe5fa" }}
            >
              <option value="candlestick">candlestick</option>
              <option value="line">line</option>
            </select>
          </div>
        </div>
        <div className="quick-bars">
          {QUICK_BARS.map((n) => (
            <button
              key={n}
              className={props.bars === n ? "quick-bar active" : "quick-bar"}
              onClick={() => props.onBarsChange(n)}
              type="button"
            >
              {n} giorni
            </button>
          ))}
        </div>
        <div className="chart-levels">
          {!props.isQuickChart && (
            <>
              <span className="level-chip close">Close: {fmtPrice(props.snapshotClose)}</span>
              {props.row ? (
                <>
                  {[
                    { label: "1D", val: props.row.PCTV_1D },
                    { label: "5D", val: props.row.PCTV_5D },
                    { label: "10D", val: props.row.PCTV_10D },
                    { label: "30D", val: props.row.PCTV_30D },
                    { label: "180D", val: props.row.PCTV_180D }
                  ].map((item) => {
                    const n = toNum(item.val);
                    if (n === null) return null;
                    const sign = n > 0 ? "+" : "";
                    const color = n > 0 ? "#22c55e" : (n < 0 ? "#ef4444" : "#f59e0b");
                    return (
                      <span
                        key={item.label}
                        className="level-chip"
                        style={{
                          border: "1px solid rgba(174,216,249,0.2)",
                          color: "#cfe5fa"
                        }}
                      >
                        {item.label}: <span style={{ color, fontWeight: "bold" }}>{sign}{n.toFixed(2)}%</span>
                      </span>
                    );
                  })}
                </>
              ) : null}
            </>
          )}
          {props.levels?.sl1 != null ? (
            <span className={`level-chip ${pctClass(props.levels.sl1)}`}>SL1: {fmtPrice(props.levels.sl1)} ({fmtPctFromClose(props.levels.sl1)})</span>
          ) : null}
          {props.levels?.sl2 != null ? (
            <span className={`level-chip ${pctClass(props.levels.sl2)}`}>SL2: {fmtPrice(props.levels.sl2)} ({fmtPctFromClose(props.levels.sl2)})</span>
          ) : null}
          {props.levels?.pbStop != null ? (
            <span className={`level-chip ${pctClass(props.levels.pbStop)}`}>PB Stop: {fmtPrice(props.levels.pbStop)} ({fmtPctFromClose(props.levels.pbStop)})</span>
          ) : null}
          {props.levels?.ppLevel != null ? (
            <span className={`level-chip ${pctClass(props.levels.ppLevel)}`}>Profit Protect: {fmtPrice(props.levels.ppLevel)} ({fmtPctFromClose(props.levels.ppLevel)})</span>
          ) : null}
        </div>

        {/* Alert and AI actions row in Modal */}
        {props.row && props.onCreateAlert && props.onRemoveAlert && props.sourceMarket ? (
          <div style={{ marginTop: "0.8rem", display: "flex", gap: "0.6rem", alignItems: "center", flexWrap: "wrap" }}>
            <button
              className={props.alertSet ? "btn alert-on" : "btn ghost"}
              disabled={props.alertBusy}
              onClick={() => {
                applyAlertPreset();
                setShowAlertTools((v) => !v);
                setAlertMsg("");
              }}
              title={props.alertSet ? "Alert presente: apri per modificare o rimuovere" : "Apri opzioni alert"}
            >
              {props.alertBusy ? "..." : props.alertSet ? "🔔 Alert ON" : "🔔 Imposta Alert"}
            </button>

            {/* Ask AI Button */}
            <button
              className="btn"
              style={{ background: "linear-gradient(120deg, #8b5cf6 0%, #3b82f6 100%)", borderColor: "rgba(167, 139, 250, 0.45)", fontWeight: "bold" }}
              disabled={aiLoading}
              onClick={handleAskAi}
              title={`Chiedi ad AI (${aiModel}) un'analisi multimodale del grafico e le condizioni di ingresso futuro`}
            >
              {aiLoading ? "🧠 Analisi in corso..." : "🧠 Chiedi ad AI"}
            </button>

            <select
              value={aiModel}
              onChange={(e) => {
                const val = e.target.value;
                setAiModel(val);
                window.localStorage.setItem("ifinance-openai-vision-model", val);
              }}
              className="model-select"
              style={{
                marginLeft: "10px",
                padding: "6px 10px",
                borderRadius: "4px",
                border: "1px solid #ccc",
                background: "#fff",
                color: "#333",
                fontSize: "0.85rem",
                cursor: "pointer",
                verticalAlign: "middle"
              }}
            >
              <option value="gpt-4o">GPT-4o (Completo)</option>
              <option value="gpt-4o-mini">GPT-4o Mini (Default)</option>
              <option value="o1">o1 (Vision)</option>
              <option value="o3-mini">o3 Mini (Vision)</option>
              <option value="gpt-5.5">GPT-5.5</option>
              <option value="gpt-5.5-pro">GPT-5.5 Pro</option>
              <option value="gpt-5.4">GPT-5.4</option>
              <option value="gpt-5.4-pro">GPT-5.4 Pro</option>
              <option value="gpt-5.4-mini">GPT-5.4 Mini</option>
              <option value="gpt-5.4-nano">GPT-5.4 Nano</option>
            </select>

            <select
              value={aiAnalysisType}
              onChange={(e) => setAiAnalysisType(e.target.value as "detailed" | "concise")}
              className="model-select"
              style={{
                marginLeft: "10px",
                padding: "6px 10px",
                borderRadius: "4px",
                border: "1px solid #ccc",
                background: "#fff",
                color: "#333",
                fontSize: "0.85rem",
                cursor: "pointer",
                verticalAlign: "middle"
              }}
            >
              <option value="detailed">Analisi di Dettaglio</option>
              <option value="concise">Analisi Semplificata</option>
            </select>

            {alertMsg ? <span className="muted" style={{ fontSize: "0.85rem" }}>{alertMsg}</span> : null}
          </div>
        ) : null}

        {showAlertTools && props.row && props.sourceMarket ? (
          <div className="watchlist-tools" style={{ marginTop: "0.8rem", maxWidth: "600px" }}>
            <div className="watchlist-mode">
              <button className={alertField === "Close" ? "quick-bar active" : "quick-bar"} onClick={() => {
                setAlertField("Close");
                if (close !== null) setAlertValue(String(close));
              }}>
                Prezzo ({close !== null ? close.toFixed(2) : "-"})
              </button>
              <button className={alertField === "MACD_vs_Signal" ? "quick-bar active" : "quick-bar"} onClick={() => {
                setAlertField("MACD_vs_Signal");
                const s3 = props.row ? toNum(props.row.MACD_vs_Signal) : null;
                if (s3 !== null) setAlertValue(String(s3));
              }}>
                S3 ({props.row && props.row.MACD_vs_Signal !== undefined ? num(props.row.MACD_vs_Signal, 0) : "-"})
              </button>
              <button className={alertField === "MACD" ? "quick-bar active" : "quick-bar"} onClick={() => {
                setAlertField("MACD");
                const macd = props.row ? toNum(props.row.MACD) : null;
                if (macd !== null) setAlertValue(String(macd));
              }}>
                MACD ({props.row && props.row.MACD !== undefined ? num(props.row.MACD, 2) : "-"})
              </button>
              <button className={alertField === "RSI" ? "quick-bar active" : "quick-bar"} onClick={() => {
                setAlertField("RSI");
                const rsi = props.row ? toNum(props.row.RSI) : null;
                if (rsi !== null) setAlertValue(String(rsi));
              }}>
                RSI ({props.row && props.row.RSI !== undefined ? num(props.row.RSI, 0) : "-"})
              </button>
              <button className={alertField === "SIG_MA_SAR" ? "quick-bar active" : "quick-bar"} onClick={() => {
                setAlertField("SIG_MA_SAR");
                if (sarma !== null) setAlertValue(String(sarma));
              }}>
                SARMA ({sarma !== null && sarma > 0 ? num(sarma, 0) : "<0"})
              </button>
              <button className={alertField === "Williams_R" ? "quick-bar active" : "quick-bar"} onClick={() => {
                setAlertField("Williams_R");
                if (willR !== null) setAlertValue(String(willR));
              }}>
                willR ({props.row && props.row.Williams_R !== undefined ? num(props.row.Williams_R, 0) : "-"})
              </button>
              <button className={alertField === "MACD_Hist" ? "quick-bar active" : "quick-bar"} onClick={() => {
                setAlertField("MACD_Hist");
                setAlertOp(">");
                setAlertValue("0");
              }}>
                Hist ({macdHist !== null ? num(macdHist, 3) : "-"})
              </button>
              <button className={alertField === "Stoch_K" ? "quick-bar active" : "quick-bar"} onClick={() => {
                setAlertField("Stoch_K");
                if (stochK !== null) setAlertValue(String(Math.round(stochK)));
              }}>
                Stoch K ({stochK !== null ? num(stochK, 0) : "-"})
              </button>
              <button className={alertField === "Stoch_D" ? "quick-bar active" : "quick-bar"} onClick={() => {
                setAlertField("Stoch_D");
                if (stochD !== null) setAlertValue(String(Math.round(stochD)));
              }}>
                Stoch D ({stochD !== null ? num(stochD, 0) : "-"})
              </button>
              <button className={alertField === "Stoch_KvsD" ? "quick-bar active" : "quick-bar"} onClick={() => {
                setAlertField("Stoch_KvsD");
                setAlertOp(">");
                setAlertValue("0");
              }}>
                K−D ({stochK !== null && stochD !== null ? num(stochK - stochD, 1) : "-"})
              </button>
              <button className={alertField === "ADX" ? "quick-bar active" : "quick-bar"} onClick={() => {
                setAlertField("ADX");
                setAlertOp(">");
                if (adx !== null) setAlertValue(String(Math.round(adx)));
              }}>
                ADX ({adx !== null ? num(adx, 0) : "-"})
              </button>
              <button className={alertField === "PLUS_DI" ? "quick-bar active" : "quick-bar"} onClick={() => {
                setAlertField("PLUS_DI");
                if (plusDI !== null) setAlertValue(String(Math.round(plusDI)));
              }}>
                DI+ ({plusDI !== null ? num(plusDI, 0) : "-"})
              </button>
              <button className={alertField === "MINUS_DI" ? "quick-bar active" : "quick-bar"} onClick={() => {
                setAlertField("MINUS_DI");
                if (minusDI !== null) setAlertValue(String(Math.round(minusDI)));
              }}>
                DI− ({minusDI !== null ? num(minusDI, 0) : "-"})
              </button>
              <button className={alertField === "DI_diff" ? "quick-bar active" : "quick-bar"} onClick={() => {
                setAlertField("DI_diff");
                setAlertOp(">");
                setAlertValue("0");
              }}>
                DI+−DI− ({plusDI !== null && minusDI !== null ? num(plusDI - minusDI, 1) : "-"})
              </button>
              <button className={alertField === "Signal6" ? "quick-bar active" : "quick-bar"} onClick={() => {
                setAlertField("Signal6");
                setAlertOp("==");
                setAlertValue("Uptrend*");
              }}>
                Alligator ({props.row && props.row.Signal6 !== undefined ? String(props.row.Signal6) : "-"})
              </button>
            </div>
            {alertField === "Signal6" ? (
              <div className="watchlist-mode">
                <button className={alertOp === "==" ? "quick-bar active" : "quick-bar"} onClick={() => setAlertOp("==")}> 
                  Uguale (==)
                </button>
                <button className={alertOp === "!=" ? "quick-bar active" : "quick-bar"} onClick={() => setAlertOp("!=")}> 
                  Diverso (!=)
                </button>
              </div>
            ) : (
              <div className="watchlist-mode">
                <button className={alertOp === ">" ? "quick-bar active" : "quick-bar"} onClick={() => setAlertOp(">")}> 
                  &gt;
                </button>
                <button className={alertOp === "<" ? "quick-bar active" : "quick-bar"} onClick={() => setAlertOp("<")}> 
                  &lt;
                </button>
              </div>
            )}
            {alertField === "Signal6" ? (
              <label style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                Stato Alligator
                <select value={alertValue} onChange={(e) => setAlertValue(e.target.value)} style={{
                  width: "100%",
                  padding: "0.4rem 0.6rem",
                  borderRadius: "8px",
                  backgroundColor: "rgba(12, 28, 48, 0.7)",
                  border: "1px solid rgba(184, 216, 246, 0.25)",
                  color: "#ffffff",
                  fontSize: "0.84rem",
                  outline: "none"
                }}>
                  <option value="Uptrend">Uptrend (Sopra la Lips)</option>
                  <option value="Uptrend*">Uptrend* (Primo Giorno)</option>
                  <option value="Uptrend-">Uptrend- (Tra Teeth e Lips)</option>
                  <option value="Uptrend--">Uptrend-- (Tra Jaw e Teeth)</option>
                  <option value="Uptrend---">Uptrend--- (Sotto o uguale alla Jaw)</option>
                  <option value="Downtrend">Downtrend (Struttura ribassista)</option>
                  <option value="Downtrend*">Downtrend* (Primo Giorno)</option>
                  <option value="Downtrend_revS3Sig+">Downtrend_revS3Sig+ (Reversal 1)</option>
                  <option value="Downtrend_revS3Sig++">Downtrend_revS3Sig++ (Reversal 2)</option>
                  <option value="Downtrend_revS3Sig+++">Downtrend_revS3Sig+++ (Reversal 3)</option>
                  <option value="wakeup1">wakeup1 (Si sveglia forte)</option>
                  <option value="wakeup1-">wakeup1- (Si sveglia debole)</option>
                  <option value="wakeup2">wakeup2 (Si sveglia 2 forte)</option>
                  <option value="wakeup2*">wakeup2* (Wakeup2 primo giorno)</option>
                  <option value="wakeup2-">wakeup2- (Si sveglia 2 debole)</option>
                  <option value="sleep1">sleep1 (Dorme 1)</option>
                  <option value="sleep2">sleep2 (Dorme 2)</option>
                </select>
              </label>
            ) : (
              <label>
                Valore {quickAlertFieldLabel(alertField)} {alertField === "Williams_R" && "(es. -80 o 80)"}
                <input value={alertValue} onChange={(e) => setAlertValue(e.target.value)} placeholder="es. 27.10" />
              </label>
            )}
            <div className="row actions">
              <button className="btn" disabled={props.alertBusy || !props.ticker} onClick={createQuickAlert}>
                {props.alertBusy ? "Salvo..." : props.alertSet ? "Aggiorna alert" : "Crea alert"}
              </button>
              {props.alertSet ? (
                <button className="btn ghost remove-btn" disabled={props.alertBusy || !props.ticker} onClick={removeQuickAlert}>
                  {props.alertBusy ? "..." : "Rimuovi alert"}
                </button>
              ) : null}
            </div>
          </div>
        ) : null}

        {/* AI Analysis Result Section */}
        {aiLoading ? (
          <div className="chart-status" style={{ marginTop: "0.8rem", background: "rgba(139, 92, 246, 0.08)", borderColor: "rgba(139, 92, 246, 0.3)", display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <div className="ai-typing" style={{ padding: 0 }}><span /><span /><span /></div>
            <span style={{ color: "#c084fc", fontWeight: "bold" }}>L'Intelligenza Artificiale multimodale ({aiModel}) sta analizzando il grafico...</span>
          </div>
        ) : null}

        {aiError ? (
          <div className="chart-status chart-error" style={{ marginTop: "0.8rem" }}>
            <div>Errore durante l'analisi AI: {aiError}</div>
          </div>
        ) : null}

        {aiAnalysis ? (
          <div className="guide-card" style={{ marginTop: "0.8rem", background: "rgba(10, 22, 38, 0.8)", borderColor: "rgba(139, 92, 246, 0.35)", padding: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
              <h3 style={{ margin: 0, color: "#c084fc" }}>🧠 GenAI Multimodal Insight</h3>
              <button className="btn ghost" style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem" }} onClick={() => setAiAnalysis(null)}>
                Nascondi
              </button>
            </div>
            <div className="ai-content" style={{ fontSize: "0.92rem", color: "#e2e8f0" }}>
              {renderMessage(aiAnalysis)}
            </div>
          </div>
        ) : null}

        {forceLineFallback ? <div className="chart-snapshot stale">Fallback attivo: grafico line per stabilita.</div> : null}
        <div className="chart-wrap">
          {loading && !hasError ? <div className="chart-status">Caricamento grafico...</div> : null}
          {hasError ? (
            <div className="chart-status chart-error">
              <div>Grafico non disponibile (retry automatici esauriti).</div>
              <button className="btn ghost" onClick={retry}>
                Riprova
              </button>
            </div>
          ) : null}
          <img
            src={src}
            alt={`Chart ${props.ticker}`}
            style={{ display: hasError ? "none" : "block" }}
            onLoad={() => {
              setLoading(false);
              setHasError(false);
            }}
            onError={() => {
              if (retryCount < MAX_AUTO_RETRIES) {
                setRetryCount((v) => v + 1);
                setLoading(true);
                setHasError(false);
                return;
              }
              if (props.chartType === "candlestick" && !forceLineFallback) {
                setForceLineFallback(true);
                setRetryCount(0);
                setLoading(true);
                setHasError(false);
                props.onTypeChange("line");
                return;
              }
              setLoading(false);
              setHasError(true);
            }}
          />
        </div>
      </div>
    </div>
  );
}
