import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { analyzeChartImage, createAiAlert, createAiLevelAlert, sendAiChat } from "../api";
import type { AiChatMessage, AiCriticalLevel, AiProposedCondition, WatchlistRow } from "../types";

const ANALYSIS_MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-5.5", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano"];
function savedAnalysisModel(): string {
  const saved = window.localStorage.getItem("ifinance-openai-model") || "gpt-4o-mini";
  return ANALYSIS_MODELS.includes(saved) ? saved : "gpt-4o-mini";
}

type Props = {
  open: boolean;
  row: WatchlistRow | null;
  market: string;
  onClose: () => void;
  onChatActivity?: (market: string, ticker: string, active: boolean) => void;
  aiLevelAlerts?: Array<{ ruleId: string; enabled: boolean; type: string; price: number; trigger: string; verified: boolean; actual: unknown }>;
  aiAlertInfo?: { ruleId: string; enabled: boolean; verified: number; total: number } | null;
};

type TickerAiSession = {
  sessionId: string;
  messages: AiChatMessage[];
};

const PRESET_QUESTIONS = [
  "Sintesi veloce",
  "Perche questa classificazione?",
  "Entrata ora: si/no?",
  "Rischi principali",
  "Livelli operativi",
  "Cosa deve migliorare?",
];

function makeSessionId(ticker: string): string {
  return `card-${ticker || "ticker"}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function makeTickerSession(ticker: string): TickerAiSession {
  return {
    sessionId: makeSessionId(ticker),
    messages: [],
  };
}

function extractAiConditions(content: string): AiProposedCondition[] {
  const blocks = normalizeAiMarkdown(content).match(/```(?:json)?\s*([\s\S]*?)```/gi) ?? [];
  for (const block of blocks) {
    try {
      const parsed = JSON.parse(block.replace(/^```(?:json)?\s*/i, "").replace(/```$/i, "").trim());
      if (Array.isArray(parsed?.conditions)) return parsed.conditions;
    } catch { /* try next block */ }
  }
  return [];
}

function extractAiLevels(content: string): AiCriticalLevel[] {
  const blocks = normalizeAiMarkdown(content).match(/```(?:json)?\s*([\s\S]*?)```/gi) ?? [];
  for (const block of blocks) {
    try {
      const parsed = JSON.parse(block.replace(/^```(?:json)?\s*/i, "").replace(/```$/i, "").trim());
      if (Array.isArray(parsed?.critical_levels)) return parsed.critical_levels;
    } catch { /* next */ }
  }
  return [];
}

function isAiLevelAlreadyCrossed(level: AiCriticalLevel, currentPrice: number | null): boolean {
  return currentPrice !== null && Number.isFinite(currentPrice)
    && (level.trigger === ">" ? currentPrice >= Number(level.price) : currentPrice <= Number(level.price));
}

function toNum(v: unknown): number | null {
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  if (typeof v === "string") {
    const x = Number(v.replace(",", ".").trim());
    return Number.isNaN(x) ? null : x;
  }
  return null;
}

function field(row: WatchlistRow, key: string): string {
  const v = row[key];
  if (v === null || v === undefined || v === "") return "-";
  return String(v);
}

function buildPrompt(row: WatchlistRow, market: string, question: string, showObservedData: boolean): string {
  const ticker = field(row, "Ticker");
  const name = field(row, "Name");
  const questionText = question.toLowerCase();
  const marketPhase = field(row, "Market_Phase").toUpperCase();
  const trendDetail = field(row, "Trend_Phase_Detail").toUpperCase();
  const isEntryQuestion = questionText.includes("entrata ora");
  const isLevelQuestion =
    isEntryQuestion ||
    questionText.includes("ingresso") ||
    questionText.includes("entrare") ||
    questionText.includes("trigger") ||
    questionText.includes("stop") ||
    questionText.includes("livell");
  const isBreakoutContext = marketPhase === "BREAKOUT" || trendDetail.includes("BREAKOUT") || questionText.includes("breakout");
  return [
    `Analizza il ticker ${ticker} (${name}) nel mercato ${market}.`,
    showObservedData
      ? "Usa i dati osservati della card e, se utile, recupera anche il dettaglio dall'Excel."
      : "I dati osservati della card sono gia' stati forniti nella conversazione: usali come contesto, ma non ripeterli nella risposta.",
    "",
    showObservedData ? "Dati card da mostrare se utili:" : "Dati card solo per contesto interno, da NON ristampare:",
    `- Segnale ingresso: ${field(row, "Entry_Signal")}`,
    `- Motivo ingresso: ${field(row, "Entry_Reason")}`,
    `- Contesto tecnico: ${field(row, "Market_Phase")}`,
    `- Trend_Phase_Detail: ${field(row, "Trend_Phase_Detail")}`,
    `- Close: ${field(row, "Close")}`,
    `- TECH_SCORE: ${field(row, "TECH_SCORE")}`,
    `- RSI: ${field(row, "RSI")}`,
    `- Stoch_K / Stoch_D: ${field(row, "Stoch_K")} / ${field(row, "Stoch_D")}`,
    `- MACD_vs_Signal: ${field(row, "MACD_vs_Signal")}`,
    `- MACD: ${field(row, "MACD")}`,
    `- SIG_MA_SAR: ${field(row, "SIG_MA_SAR")}`,
    `- Volume: ${field(row, "Volume")}`,
    `- Trend_Stop_Level: ${field(row, "Trend_Stop_Level")}`,
    `- CE_Long: ${field(row, "CE_Long")}`,
    `- Pullback_Entry_Level: ${field(row, "Pullback_Entry_Level")}`,
    `- Pullback_Stop_Level: ${field(row, "Pullback_Stop_Level")}`,
    "",
    `Domanda: ${question}`,
    "",
    showObservedData
      ? "Questa e' la prima domanda della chat sul ticker: puoi includere una sezione Dati osservati se aiuta la lettura."
      : "Questa NON e' la prima domanda della chat sul ticker: non creare la sezione Dati osservati e non ripetere l'elenco degli indicatori gia' mostrati. Rispondi direttamente alla nuova domanda, richiamando solo i livelli o i segnali indispensabili.",
    "",
    isLevelQuestion
      ? [
          "Regola dati per domande operative su ingresso, trigger, stop o livelli:",
          "- Prima di indicare range, trigger price, resistenze, supporti o stop, usa il tool get_price_sequence per leggere almeno gli ultimi 70 dati giornalieri OHLCV del ticker.",
          "- Ricava i livelli da massimi/minimi recenti, chiusure, retest, supporti, resistenze e range delle ultime sedute.",
          "- Non scrivere 'resistenza non presente nei dati' se puoi stimarla dalla serie prezzi scaricata.",
          "- Se il tool prezzi non e' disponibile o fallisce, dichiaralo e separa chiaramente i livelli presi dalla card dalle stime tecniche.",
          "",
        ].join("\n")
      : "",
    isEntryQuestion
      ? [
          "Regola specifica per la domanda Entrata ora:",
          "- Devi rispondere prima con SI, NO oppure SOLO AGGRESSIVA.",
          "- Se la risposta e' NO, indica comunque i livelli/prezzi di ingresso da attendere e quali condizioni tecniche devono migliorare.",
          "- Se la risposta e' SI o SOLO AGGRESSIVA, indica prezzo/zona di ingresso, stop loss operativo e cosa invaliderebbe il setup.",
          "- In ogni caso valuta anche uno scenario condizionale: entrare solo se il prezzo supera, recupera o tiene un livello preciso.",
          "- Per lo scenario condizionale indica trigger price, range di ingresso, condizione di conferma e stop loss.",
          "- Esempi di trigger validi: superamento di resistenza, recupero di media mobile, tenuta su supporto, retest positivo, ritorno sopra livello breakout.",
          "- Usa livelli gia' presenti nei dati se disponibili: Pullback_Entry_Level, Pullback_Stop_Level, Trend_Stop_Level, CE_Long, Close.",
          "- Se un livello manca, proponi una zona ragionata usando supporti, stop, pullback o prezzo corrente, ma dichiaralo come stima.",
          "",
        ].join("\n")
      : "",
    isBreakoutContext
      ? [
          "Regola specifica per contesto BREAKOUT:",
          "- Non limitarti a dire che il breakout e' valido o non valido.",
          "- Indica una zona/range di ingresso operativo, distinguendo se possibile tra ingresso immediato e ingresso su retest/pullback.",
          "- Specifica la condizione che deve confermare l'ingresso: tenuta sopra livello breakout, chiusura sopra resistenza, volumi, momentum, RSI/Stoch, MACD o ADX.",
          "- Indica il livello che invaliderebbe il breakout e lo stop loss coerente con quel livello.",
          "- Se il breakout e' gia' esteso, preferisci indicare il range da attendere su retest invece di inseguire il prezzo.",
          "- Usa Close, Pullback_Entry_Level, Pullback_Stop_Level, Trend_Stop_Level e CE_Long se disponibili; se mancano, dichiara il range come stima.",
          "",
        ].join("\n")
      : "",
    "Rispondi in italiano, in modo operativo e sintetico. Se parli di entrata, separa osservazioni nuove, interpretazione e rischi.",
  ].join("\n");
}

function renderInline(text: string, context: "body" | "list" = "body"): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, idx) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={idx} className={context === "list" ? "ai-label" : undefined}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function normalizeAiMarkdown(content: string): string {
  let text = String(content || "").replace(/^\s*```(?:markdown|md)\s*\r?\n/i, "");
  return text.replace(/\r?\n```\s*\r?\n(?=```json\b)/i, "\n");
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
            <table style={{ background: "rgba(10,22,38,0.55)", border: "1px solid rgba(174,216,249,0.23)", width: "100%" }}>
              <thead>
                <tr>
                  <th style={{ color: "#38bdf8", padding: "6px" }}>Indicatore</th>
                  <th style={{ color: "#38bdf8", padding: "6px" }}>Trigger</th>
                  <th style={{ color: "#38bdf8", padding: "6px" }}>Descrizione Condizione</th>
                </tr>
              </thead>
              <tbody>
                {parsed.conditions.map((c: any, i: number) => (
                  <tr key={i}>
                    <td style={{ fontWeight: "bold", padding: "6px" }}>{c.indicator}</td>
                    <td style={{ color: "#fbbf24", fontFamily: "monospace", padding: "6px" }}>{c.trigger}</td>
                    <td style={{ color: "#cbd5e1", padding: "6px" }}>{c.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        if (Array.isArray(parsed.critical_levels) && parsed.critical_levels.length) {
          nodes.push(
            <div key={`levels-table-${nodes.length}`} className="table-wrap" style={{ marginTop: "0.6rem" }}>
              <table><thead><tr><th>Livello critico AI</th><th>Prezzo</th><th>Trigger</th><th>Descrizione</th></tr></thead>
                <tbody>{parsed.critical_levels.map((l: AiCriticalLevel, i: number) => <tr key={i}><td>{l.type === "support" ? "Supporto" : "Resistenza"}</td><td>{l.price}</td><td>{l.trigger}</td><td>{l.description ?? ""}</td></tr>)}</tbody>
              </table>
            </div>
          );
        }
        codeContent = "";
        return;
      }
    } catch {
      // no-op, fall back to standard pre box
    }
    nodes.push(
      <pre key={`pre-${nodes.length}`} className="json" style={{ margin: "0.6rem 0", background: "rgba(8,18,34,0.85)", padding: "8px" }}>
        <code>{codeContent.trim()}</code>
      </pre>
    );
    codeContent = "";
  }

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

  const lines = normalizeAiMarkdown(content).split("\n");
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

    const mdHeading = line.match(/^#{1,6}\s+(.+)/);
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

export default function AiTickerModal({ open, row, market, onClose, onChatActivity, aiLevelAlerts = [], aiAlertInfo }: Props) {
  const queryClient = useQueryClient();
  const ticker = String(row?.Ticker ?? "");
  const sessionKey = ticker ? `${market}::${ticker}` : "";
  const [sessions, setSessions] = useState<Record<string, TickerAiSession>>({});
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const messages = sessionKey ? sessions[sessionKey]?.messages ?? [] : [];
  const [model, setModel] = useState(savedAnalysisModel);
  const [aiAlertBusy, setAiAlertBusy] = useState(false);
  const [aiAlertMessage, setAiAlertMessage] = useState("");
  const aiAlertActive = Boolean(aiAlertInfo?.enabled);
  const isLevelActive = (level: AiCriticalLevel) => aiLevelAlerts.some((saved) =>
    saved.enabled && saved.type === level.type && saved.trigger === level.trigger && Math.abs(saved.price - level.price) < 0.000001
  );

  useEffect(() => {
    if (!open || !sessionKey) return;
    setSessions((prev) => (prev[sessionKey] ? prev : { ...prev, [sessionKey]: makeTickerSession(ticker) }));
    setInput("");
    setError("");
    setBusy(false);
    setAiAlertMessage("");
    setModel(savedAnalysisModel());
  }, [open, sessionKey, ticker]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, busy]);

  const subtitle = useMemo(() => {
    if (!row) return "";
    const parts = [field(row, "Entry_Signal"), field(row, "Market_Phase"), field(row, "Trend_Phase_Detail")].filter((v) => v && v !== "-");
    return parts.join(" - ");
  }, [row]);

  function appendMessage(key: string, fallbackSession: TickerAiSession, message: AiChatMessage) {
    setSessions((prev) => {
      const current = prev[key] ?? fallbackSession;
      return {
        ...prev,
        [key]: {
          ...current,
          messages: [...current.messages, message],
        },
      };
    });
  }

  function clearChat() {
    if (!sessionKey) return;
    setSessions((prev) => ({ ...prev, [sessionKey]: makeTickerSession(ticker) }));
    onChatActivity?.(market, ticker, false);
    setInput("");
    setError("");
    setBusy(false);
  }

  async function submit(question: string) {
    if (!row || busy || !sessionKey) return;
    const q = question.trim();
    if (!q) return;
    const sessionForRequest = sessions[sessionKey] ?? makeTickerSession(ticker);
    const showObservedData = sessionForRequest.messages.length === 0;
    setBusy(true);
    setError("");
    setInput("");
    appendMessage(sessionKey, sessionForRequest, { role: "user", content: q });
    onChatActivity?.(market, ticker, true);
    try {
      const resp = await sendAiChat({ session_id: sessionForRequest.sessionId, message: buildPrompt(row, market, q, showObservedData), model, history: sessionForRequest.messages });
      const assistant = resp.answer ? { role: "assistant", content: resp.answer } : [...resp.messages].reverse().find((m) => m.role !== "user") ?? null;
      if (assistant) appendMessage(sessionKey, sessionForRequest, assistant);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function runGraphAnalysis(analysisType: "detailed" | "concise") {
    if (!row || busy || !sessionKey) return;
    const sessionForRequest = sessions[sessionKey] ?? makeTickerSession(ticker);
    setBusy(true);
    setError("");
    
    const queryText = `Esegui analisi grafica ${analysisType === "detailed" ? "di dettaglio" : "semplificata"}`;
    appendMessage(sessionKey, sessionForRequest, { role: "user", content: queryText });
    onChatActivity?.(market, ticker, true);
    
    try {
      const resp = await analyzeChartImage({
        ticker,
        market,
        bars: 70,
        chart_type: "candlestick",
        levels: {
          sl1: toNum(row.Trend_Stop_Level),
          sl2: toNum(row.CE_Long),
          pbStop: toNum(row.Pullback_Stop_Level),
          ppLevel: toNum(row.Profit_Protect_Level)
        },
        model,
        analysis_type: analysisType,
        current_price: toNum(row.Close)
      });
      
      appendMessage(sessionKey, sessionForRequest, {
        role: "assistant",
        content: resp.analysis
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function activateConditions(conditions: AiProposedCondition[]) {
    if (!conditions.length) return;
    setAiAlertBusy(true);
    setAiAlertMessage("");
    try {
      const result = await createAiAlert(market, { ticker, conditions, title: `🤖 Alert AI ${ticker}` });
      await queryClient.invalidateQueries({ queryKey: ["alerts", market] });
      window.dispatchEvent(new Event("ifinance-alerts-changed"));
      setAiAlertMessage(`Alert ${result.rule.id} attivato.`);
    } catch (e) {
      setAiAlertMessage(`Impossibile attivare: ${String(e)}`);
    } finally {
      setAiAlertBusy(false);
    }
  }

  async function activateLevel(level: AiCriticalLevel) {
    const currentPrice = toNum(row?.Close);
    if (isAiLevelAlreadyCrossed(level, currentPrice)) {
      setAiAlertMessage(`Livello già superato dal prezzo corrente (${currentPrice}).`);
      return;
    }
    setAiAlertBusy(true); setAiAlertMessage("");
    try {
      const result = await createAiLevelAlert(market, { ticker, level, current_price: currentPrice });
      await queryClient.invalidateQueries({ queryKey: ["alerts", market] });
      window.dispatchEvent(new Event("ifinance-alerts-changed"));
      setAiAlertMessage(`Alert livello ${result.rule.id} attivato.`);
    } catch (e) { setAiAlertMessage(`Impossibile attivare: ${String(e)}`); }
    finally { setAiAlertBusy(false); }
  }

  async function activateAllLevels(levels: AiCriticalLevel[]) {
    if (!levels.length) return;
    setAiAlertBusy(true); setAiAlertMessage("");
    try {
      const currentPrice = toNum(row?.Close);
      const actionable = levels.filter((level) => !isAiLevelAlreadyCrossed(level, currentPrice));
      if (!actionable.length) throw new Error("Tutti i livelli proposti sono già stati superati.");
      await Promise.all(actionable.map((level) => createAiLevelAlert(market, { ticker, level, current_price: currentPrice })));
      await queryClient.invalidateQueries({ queryKey: ["alerts", market] });
      window.dispatchEvent(new Event("ifinance-alerts-changed"));
      setAiAlertMessage(`${levels.length} alert sui livelli AI attivati.`);
    } catch (e) { setAiAlertMessage(`Impossibile attivare tutti i livelli: ${String(e)}`); }
    finally { setAiAlertBusy(false); }
  }

  if (!open || !row) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal ai-ticker-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h3>Analisi AI {ticker}</h3>
            <p className="modal-subtitle">{subtitle}</p>
          </div>
          <div className="modal-actions" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <select
              value={model}
              onChange={(e) => {
                const val = e.target.value;
                setModel(val);
                window.localStorage.setItem("ifinance-openai-model", val);
              }}
              className="model-select"
              style={{
                padding: "6px 10px",
                borderRadius: "4px",
                border: "1px solid #ccc",
                background: "#fff",
                color: "#333",
                fontSize: "0.85rem",
                cursor: "pointer",
              }}
            >
              <option value="gpt-4o-mini">GPT-4o Mini (Default)</option>
              <option value="gpt-4o">GPT-4o (Completo)</option>
              <option value="gpt-5.5">GPT-5.5</option>
              <option value="gpt-5.4">GPT-5.4</option>
              <option value="gpt-5.4-mini">GPT-5.4 Mini</option>
              <option value="gpt-5.4-nano">GPT-5.4 Nano</option>
            </select>
            <button className="btn ghost danger" disabled={messages.length === 0} onClick={clearChat}>
              Cancella chat
            </button>
            <button className="btn ghost" onClick={onClose}>
              Chiudi
            </button>
          </div>
        </div>

        <div className="ai-ticker-presets" style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "0.5rem", borderBottom: "1px solid rgba(174,216,249,0.15)", paddingBottom: "0.6rem" }}>
          <button
            className="btn"
            style={{ background: "linear-gradient(120deg, #8b5cf6 0%, #3b82f6 100%)", borderColor: "rgba(167, 139, 250, 0.45)", padding: "0.38rem 0.7rem", fontSize: "0.82rem", fontWeight: "bold" }}
            disabled={busy}
            onClick={() => runGraphAnalysis("detailed")}
          >
            📊 Analisi di Dettaglio
          </button>
          <button
            className="btn"
            style={{ background: "linear-gradient(120deg, #10b981 0%, #059669 100%)", borderColor: "rgba(16, 185, 129, 0.45)", padding: "0.38rem 0.7rem", fontSize: "0.82rem", fontWeight: "bold" }}
            disabled={busy}
            onClick={() => runGraphAnalysis("concise")}
          >
            📊 Analisi Semplificata
          </button>
        </div>

        <div className="ai-ticker-presets">
          {PRESET_QUESTIONS.map((q) => (
            <button key={q} className="quick-bar" disabled={busy} onClick={() => submit(q)}>
              {q}
            </button>
          ))}
        </div>

        {aiLevelAlerts.length ? <div className="guide-card" style={{ margin: "0.6rem 0", padding: "0.65rem", borderColor: "rgba(245,158,11,.45)" }}>
          <strong>📍 Alert attivi su livelli AI</strong>
          {aiLevelAlerts.map((level) => <div key={level.ruleId} style={{ color: level.verified ? "#22c55e" : "#f59e0b", marginTop: "0.25rem" }}>
            {level.verified ? "✓" : "○"} {level.type === "support" ? "Supporto" : "Resistenza"} {level.price} · {level.enabled ? "Attivo" : "OFF"} · valore attuale {level.actual == null ? "n/d" : String(level.actual)}
          </div>)}
        </div> : null}

        <div className="ai-ticker-messages">
          {messages.length === 0 ? (
            <div className="ai-empty">Scegli una domanda rapida o scrivine una sul ticker.</div>
          ) : (
            messages.map((m, idx) => {
              const proposed = m.role === "user" ? [] : extractAiConditions(m.content);
              const levels = m.role === "user" ? [] : extractAiLevels(m.content);
              return (
              <div key={`${m.role}-${idx}`} className={m.role === "user" ? "ai-msg user" : "ai-msg assistant"}>
                <div className="ai-avatar">{m.role === "user" ? "Tu" : "AI"}</div>
                <div className="ai-bubble">
                  <div className="ai-role">{m.role === "user" ? "Tu" : "IFinance AI"}</div>
                  <div className="ai-content">{renderMessage(m.content)}</div>
                  {proposed.length ? <button className={`btn alert-on${aiAlertActive ? " alert-created" : ""}`} disabled={aiAlertBusy || aiAlertActive} onClick={() => activateConditions(proposed)}>{aiAlertActive ? `✓ Alert AI già attivo (${proposed.length})` : `🔔 Attiva alert AI (${proposed.length})`}</button> : null}
                  {levels.length > 1 ? (() => {
                    const activeCount = levels.filter(isLevelActive).length;
                    return <button className={`btn alert-on${activeCount === levels.length ? " alert-created" : ""}`} disabled={aiAlertBusy || activeCount === levels.length} onClick={() => activateAllLevels(levels)}>{activeCount === levels.length ? `✓ Tutti i livelli attivi (${levels.length})` : `🔔 Attiva tutti i livelli (${activeCount}/${levels.length} attivi)`}</button>;
                  })() : null}
                  {levels.map((level, i) => {
                    const crossed = isAiLevelAlreadyCrossed(level, toNum(row.Close));
                    return <button key={i} className={`btn ghost${isLevelActive(level) ? " alert-created" : ""}`} disabled={aiAlertBusy || isLevelActive(level) || crossed} title={crossed ? "Livello già superato dal prezzo corrente" : undefined} onClick={() => activateLevel(level)}>{isLevelActive(level) ? "✓ Attivo" : crossed ? "⚠ Già superato" : "🔔 Attiva"} {level.type === "support" ? "Supporto" : "Resistenza"} {level.price}</button>;
                  })}
                </div>
              </div>
              );
            })
          )}
          {aiAlertMessage ? <p className={aiAlertMessage.startsWith("Impossibile") ? "err" : "ok"}>{aiAlertMessage}</p> : null}
          {busy ? (
            <div className="ai-msg assistant">
              <div className="ai-avatar">AI</div>
              <div className="ai-bubble">
                <div className="ai-role">IFinance AI</div>
                <div className="ai-typing">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            </div>
          ) : null}
          <div ref={bottomRef} />
        </div>

        {error ? <p className="err">{error}</p> : null}

        <form
          className="ai-compose ai-ticker-compose"
          onSubmit={(e) => {
            e.preventDefault();
            submit(input);
          }}
        >
          <textarea
            rows={3}
            value={input}
            placeholder={`Domanda libera su ${ticker}...`}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit(input);
              }
            }}
          />
          <button className="btn" disabled={busy || !input.trim()}>
            {busy ? "Invio..." : "Chiedi"}
          </button>
        </form>
      </div>
    </div>
  );
}
