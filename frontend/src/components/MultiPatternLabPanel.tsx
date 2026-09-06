import { useState, useEffect, useMemo, useRef } from "react";
import type { WatchlistRow, QuickAlertField } from "../types";
import WatchlistCard from "./WatchlistCard";

type QuickAlertConfig = {
  field: QuickAlertField;
  op: ">" | "<" | "==" | "!=";
  value: number | string | null;
};

interface MultiPatternLabPanelProps {
  market: string;
  onOpenInteractiveChart?: (row: WatchlistRow) => void;
  onChart: (row: WatchlistRow) => void;
  onAi: (row: WatchlistRow) => void;
  aiActiveChatMap: Record<string, boolean>;
  aiAlertCardMap: Record<string, {
    ruleId: string; enabled: boolean; verified: number; total: number; summary: string;
    conditions: Array<{ verified: boolean; field: string; op: string; value: unknown; actual: unknown; description?: string }>;
  }>;
  aiLevelCardMap: Record<string, Array<{ ruleId: string; enabled: boolean; type: string; price: number; trigger: string; verified: boolean; actual: unknown }>>;
  onToggleAiAlert: (sourceMarket: string, ruleId: string, enabled: boolean) => Promise<void>;
  onDeleteAiAlert: (sourceMarket: string, ruleId: string) => Promise<void>;
  onResultsChange?: (rows: WatchlistRow[]) => void;
  quickAlertMap: Record<string, boolean>;
  quickAlertConfigMap: Record<string, QuickAlertConfig>;
  quickAlertBusyMap: Record<string, boolean>;
  onCreateAlert: (input: {
    row: WatchlistRow;
    source_market: string;
    field: QuickAlertField;
    op: ">" | "<" | "==" | "!=";
    value: number | string;
  }) => Promise<string>;
  onRemoveAlert: (input: { row: WatchlistRow; source_market: string }) => Promise<string>;
  customWatchlists: string[];
  onAddToWatchlist: (input: { name: string; ticker: string; source_market: string }) => Promise<string>;
  currentWatchlistName: string | null;
  onRemoveFromWatchlist: (input: { name: string; ticker: string; source_market?: string }) => Promise<string>;
  minVolume?: number;
}

type ScanResult = WatchlistRow & {
  Ticker: string;
  Market: string;
  Name: string;
  Close: number;
  RSI?: number;
  Stoch_K?: number;
  Stoch_D?: number;
  Williams_R?: number;
  MACD?: number;
  ADX?: number;
  SAR?: number;
  SMA200?: number;
  Pattern_Days_Ago: number;
  Signal_Var_Pct: number;
  Daily_Var_Pct: number;
  Is_Daily_Var: boolean;
  Pattern_Type: string;
  Dist_From_High?: number;   // % sotto il massimo 1Y (es. -8.5 = 8.5% sotto il max)
  Range_Pct?: number;        // posizione 0-100% nel range min-max 1Y
  High_1Y?: number;
  Low_1Y?: number;
};

interface BacktestResults {
  metrics: {
    "Start Date": string;
    "End Date": string;
    "Duration (days)": number;
    "Initial Capital": number;
    "End Value": number;
    "Total Return (%)": number;
    "Benchmark Return (%)": number;
    "Max Drawdown (%)": number;
    "Total Trades": number;
    "Win Rate (%)": number;
    "Sharpe Ratio": number;
    "Sortino Ratio": number;
    "Profit Factor": number;
    "Expectancy": number;
    "Signal Today": string;
    Ticker: string;
    Pattern: string;
  };
  commentary: string;
  buy_rule: string;
  sell_rule: string;
}

const PATTERN_TABS = [
  { id: "S2",       label: "🟢 S2",        desc: "willR+Stoch",  color: "#4ade80" },
  { id: "S3",       label: "🔵 S3",        desc: "MACD Cross",   color: "#38bdf8" },
  { id: "S4",       label: "🟣 S4",        desc: "EMA+RSI+Vol",  color: "#a78bfa" },
  { id: "S5",       label: "🌸 S5",        desc: "RSI Oversold", color: "#f472b6" },
  { id: "S6",       label: "🌟 S6",        desc: "Golden Cross", color: "#fbbf24" },
  { id: "S7_EARLY", label: "🟡 S7 Early", desc: "SAR+Alligator+DI", color: "#fbbf24" },
  { id: "S7_CONFIRMED", label: "🟢 S7 Conf.", desc: "ADX≥20+EMA", color: "#34d399" },
  { id: "S7_STRONG", label: "🟢🟢 S7 Strong", desc: "ADX≥25+Trend+Vol", color: "#22c55e" },
  { id: "S8",       label: "🟪 S8",        desc: "Volume Breakout", color: "#c084fc" },
  { id: "Combined", label: "✨ Comb.",      desc: "S2 & S3",      color: "#fbbf24" },
  { id: "S2_or_S3", label: "🔥 Qualsiasi", desc: "S2 o S3",      color: "#f97316" },
] as const;

const SCAN_MARKETS = ["MIB30", "DAX", "ETC", "ETF", "Preferite", "US_Others", "US_ETF", "Crypto"] as const;
const DEFAULT_SCAN_MARKETS = ["MIB30", "DAX", "ETC", "Preferite"];

export default function MultiPatternLabPanel({
  market,
  onOpenInteractiveChart,
  onChart,
  onAi,
  aiActiveChatMap,
  aiAlertCardMap,
  aiLevelCardMap,
  onToggleAiAlert,
  onDeleteAiAlert,
  onResultsChange,
  quickAlertMap,
  quickAlertConfigMap,
  quickAlertBusyMap,
  onCreateAlert,
  onRemoveAlert,
  customWatchlists,
  onAddToWatchlist,
  currentWatchlistName,
  onRemoveFromWatchlist,
  minVolume = 2000,
}: MultiPatternLabPanelProps) {
  const [pattern, setPattern] = useState<string>("S2");
  const [labMarkets, setLabMarkets] = useState<string[]>(DEFAULT_SCAN_MARKETS);
  const labMarket = labMarkets.length === SCAN_MARKETS.length ? "ALL" : labMarkets.join(",");
  const [useSar, setUseSar] = useState(true);
  const [useSma200, setUseSma200] = useState(false);
  const [lookback, setLookback] = useState<number>(3);
  const [configOpen, setConfigOpen] = useState(false);
  const [customPatterns, setCustomPatterns] = useState<any[]>([]);

  useEffect(() => {
    fetch("/api/scanner/custom-patterns")
      .then((res) => {
        if (!res.ok) throw new Error("Fetch fallito");
        return res.json();
      })
      .then((data) => {
        if (data && data.patterns) {
          setCustomPatterns(data.patterns);
        }
      })
      .catch((err) => console.error("Errore fetch custom patterns:", err));
  }, []);

  const allTabs = useMemo(() => {
    const builtinAliases = new Set([
      "custom_rsi_oversold", "custom_golden_cross",
      "custom_bullish_alligator", "custom_volume_breakout",
    ]);
    const customTabs = customPatterns.filter((p) => !builtinAliases.has(p.id)).map((p) => ({
      id: p.id,
      label: `🔧 ${p.label}`,
      desc: p.desc,
      color: p.color || "#6b7280",
    }));
    return [...PATTERN_TABS, ...customTabs];
  }, [customPatterns]);

  const [isScanning, setIsScanning] = useState(false);
  const [scanResults, setScanResults] = useState<ScanResult[] | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);
  const [fallbackWarnings, setFallbackWarnings] = useState<string[]>([]);
  // Progress tracking for SSE streaming scans (custom patterns)
  const [scanProgress, setScanProgress] = useState<{ done: number; total: number; market: string } | null>(null);
  // AbortController ref to cancel in-flight SSE streams when user changes params
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    onResultsChange?.((scanResults ?? []).map((row) => ({
      ...row,
      WL_Source_Market: row.WL_Source_Market ?? row.Market ?? market,
    })));
  }, [scanResults, market, onResultsChange]);

  // ─── Sorting ────────────────────────────────────────────────────────────────
  type SortDir = "asc" | "desc" | null;
  const [sortKey, setSortKey] = useState<keyof ScanResult | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);

  function handleSort(key: keyof ScanResult) {
    setSortKey(prev => {
      if (prev !== key) { setSortDir("desc"); return key; }
      // Cycle: desc → asc → none
      setSortDir(d => d === "desc" ? "asc" : d === "asc" ? null : "desc");
      return prev;
    });
  }

  const filteredResults = useMemo(() => {
    if (!scanResults) return [];
    return scanResults.filter((row) => {
      // 1. Min Volume filter
      if (minVolume !== undefined && minVolume > 0) {
        const vol = typeof row.Volume === "number" ? row.Volume : (Number(row.Volume) || 0);
        if (vol < minVolume) return false;
      }
      return true;
    });
  }, [scanResults, minVolume]);

  const sortedResults: ScanResult[] = useMemo(() => {
    if (!sortKey || !sortDir) return filteredResults;
    return [...filteredResults].sort((a, b) => {
      const av = a[sortKey] ?? (sortDir === "desc" ? -Infinity : Infinity);
      const bv = b[sortKey] ?? (sortDir === "desc" ? -Infinity : Infinity);
      if (typeof av === "string" && typeof bv === "string")
        return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      return sortDir === "asc" ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
  }, [filteredResults, sortKey, sortDir]);

  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [isBacktesting, setIsBacktesting] = useState(false);
  const [backtestResults, setBacktestResults] = useState<BacktestResults | null>(null);
  const [backtestError, setBacktestError] = useState<string | null>(null);

  const [bars, setBars] = useState(70);
  const [localBars, setLocalBars] = useState(70);
  const [chartType, setChartType] = useState<"candlestick" | "line">("candlestick");

  // Sync localBars with bars when bars changes (e.g. quick-bar click)
  useEffect(() => {
    setLocalBars(bars);
  }, [bars]);

  // Debounced update to bars to trigger backend rendering only after dragging stops
  useEffect(() => {
    const timer = setTimeout(() => {
      if (localBars !== bars && localBars >= 10 && localBars <= 400) {
        setBars(localBars);
      }
    }, 350);
    return () => clearTimeout(timer);
  }, [localBars, bars]);

  // Alert States
  const [activeAlertTicker, setActiveAlertTicker] = useState<string | null>(null);
  const [activeAlertMarket, setActiveAlertMarket] = useState<string | null>(null);
  const [alertRow, setAlertRow] = useState<any | null>(null);
  const [isLoadingAlertRow, setIsLoadingAlertRow] = useState(false);
  const [alertError, setAlertError] = useState<string | null>(null);
  const [alertMsg, setAlertMsg] = useState<string | null>(null);
  const [alertField, setAlertField] = useState<QuickAlertField>("Close");
  const [alertOp, setAlertOp] = useState<">" | "<" | "==" | "!=">(">");
  const [alertSet, setAlertSet] = useState(false);
  const [alertValue, setAlertValue] = useState("");
  const [alertBusy, setAlertBusy] = useState(false);

  function closeAlertModal() {
    setActiveAlertTicker(null);
    setActiveAlertMarket(null);
    setAlertRow(null);
    setAlertError(null);
    setAlertMsg(null);
  }

  useEffect(() => {
    if (!activeAlertTicker) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeAlertModal();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [activeAlertTicker]);

  // Set of built-in pattern IDs that use the fast pre-calculated Excel path
  const BUILTIN_PATTERNS = new Set([
    "S2", "S3", "S4", "S5", "S6", "S7", "S7_EARLY", "S7_CONFIRMED", "S7_STRONG", "S8", "Combined", "S2_or_S3",
    "custom_rsi_oversold", "custom_golden_cross", "custom_bullish_alligator", "custom_volume_breakout"
  ]);

  async function handleScan() {
    // Cancel any previous in-flight scan
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    setIsScanning(true);
    setScanError(null);
    setFallbackWarnings([]);
    setScanResults(null);
    setScanProgress(null);
    setSelectedTicker(null);
    setBacktestResults(null);

    const isCustomPattern = !BUILTIN_PATTERNS.has(pattern);

    if (isCustomPattern) {
      // ── SSE streaming path for custom patterns ──────────────────────────────
      try {
        const url = `/api/scanner/scan-stream?market=${encodeURIComponent(labMarket)}&pattern=${encodeURIComponent(pattern)}&use_sar=${useSar}&use_sma200=${useSma200}&lookback=${lookback}`;
        const res = await fetch(url, { signal: controller.signal });
        if (!res.ok) throw new Error(`Scansione fallita con status: ${res.status}`);
        if (!res.body) throw new Error("Stream non disponibile");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let foundAny = false;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          // Process complete SSE lines (split on double newline)
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? ""; // keep incomplete last chunk

          for (const part of parts) {
            const line = part.trim();
            if (!line.startsWith("data: ")) continue;
            try {
              const event = JSON.parse(line.slice(6));
              if (event.type === "market_start") {
                setScanProgress({ done: 0, total: event.total, market: event.market });
              } else if (event.type === "result") {
                foundAny = true;
                setScanResults((prev) => [...(prev ?? []), event.data as ScanResult]);
                setScanProgress({ done: event.done, total: event.total, market: event.market });
              } else if (event.type === "progress") {
                setScanProgress({ done: event.done, total: event.total, market: event.market });
              } else if (event.type === "done") {
                if (!foundAny) {
                  setScanError("Nessun titolo corrisponde al pattern e ai filtri selezionati.");
                }
                setScanProgress(null);
                setIsScanning(false);
                return;
              }
            } catch {
              // malformed event line — skip
            }
          }
        }

        // Stream ended without 'done' event
        if (!foundAny) {
          setScanError("Nessun titolo corrisponde al pattern e ai filtri selezionati.");
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          setScanError(err.message ?? "Errore sconosciuto durante la scansione.");
        }
      } finally {
        setScanProgress(null);
        setIsScanning(false);
      }
    } else {
      // ── Standard JSON path for built-in patterns (S2/S3/S4 etc.) ───────────
      try {
        const res = await fetch(
          `/api/scanner/scan?market=${encodeURIComponent(labMarket)}&pattern=${encodeURIComponent(pattern)}&use_sar=${useSar}&use_sma200=${useSma200}&lookback=${lookback}`,
          { signal: controller.signal }
        );
        if (!res.ok) throw new Error(`Scansione fallita con status: ${res.status}`);
        const data = await res.json();
        setScanResults(data.results ?? []);
        setFallbackWarnings(data.fallback_warnings ?? []);
        if ((data.results ?? []).length === 0) {
          setScanError("Nessun titolo corrisponde al pattern e ai filtri selezionati.");
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          setScanError(err.message ?? "Errore sconosciuto durante la scansione.");
        }
      } finally {
        setIsScanning(false);
      }
    }
  }

  // La scansione parte soltanto dal pulsante. Quando cambia un parametro,
  // annulla l'eventuale richiesta precedente e torna al prompt iniziale.
  useEffect(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsScanning(false);
    setScanProgress(null);
    setScanResults(null);
    setScanError(null);
    setFallbackWarnings([]);
    setSelectedTicker(null);
    setBacktestResults(null);
  }, [pattern, labMarket, useSar, useSma200, lookback]);

  useEffect(() => () => abortRef.current?.abort(), []);

  // Cambia pattern e cancella immediatamente i risultati vecchi
  function handlePatternChange(newPattern: string) {
    if (newPattern === pattern) return;
    setPattern(newPattern);
    setScanResults(null);
    setScanError(null);
    setSelectedTicker(null);
    setBacktestResults(null);
  }

  async function handleSelectRow(ticker: string) {
    setSelectedTicker(ticker);
    setIsBacktesting(true);
    setBacktestError(null);
    setBacktestResults(null);

    try {
      const res = await fetch(
        `/api/scanner/backtest?ticker=${encodeURIComponent(ticker)}&pattern=${pattern}&use_sar=${useSar}&use_sma200=${useSma200}`
      );
      if (!res.ok) throw new Error(`Calcolo backtest fallito con status: ${res.status}`);
      const data = await res.json();
      setBacktestResults(data);
    } catch (err: any) {
      setBacktestError(err.message ?? "Errore durante il caricamento del backtest.");
    } finally {
      setIsBacktesting(false);
    }
  }

  async function handleOpenAlert(ticker: string, tickerMarket?: string) {
    const targetM = tickerMarket || market;
    setActiveAlertTicker(ticker);
    setActiveAlertMarket(targetM);
    setIsLoadingAlertRow(true);
    setAlertError(null);
    setAlertRow(null);
    setAlertMsg(null);
    setAlertSet(false);

    try {
      const resFocus = await fetch(
        `/api/watchlist/focus?market=${encodeURIComponent(targetM)}&ticker=${encodeURIComponent(ticker)}`
      );
      if (!resFocus.ok) throw new Error(`Impossibile caricare i dati dettagliati per ${ticker}: ${resFocus.statusText}`);
      const focusData = await resFocus.json();
      const rowItem = focusData.item;
      setAlertRow(rowItem);
      setAlertField("Close");
      setAlertOp(">");
      if (rowItem?.Close !== undefined) setAlertValue(String(rowItem.Close));

      const resAlerts = await fetch(`/api/alerts/${encodeURIComponent(targetM)}`);
      if (resAlerts.ok) {
        const alertData = await resAlerts.json();
        const rules = alertData.rules || [];
        const normalizedTicker = ticker.trim().toUpperCase().replace(/[^A-Z0-9]+/g, "_").replace(/^_+|_+$/g, "");
        const rid = `CARD_ALERT_${normalizedTicker}`;
        const found = rules.find((r: any) => String(r.id).trim().toUpperCase() === rid.toUpperCase());
        if (found) {
          setAlertSet(true);
          const firstCond = found.when?.all?.[0];
          if (firstCond) {
            setAlertField(firstCond.field || "Close");
            setAlertOp(firstCond.op || ">");
            if (firstCond.value !== undefined) setAlertValue(String(firstCond.value));
          }
        }
      }
    } catch (err: any) {
      setAlertError(err.message || "Errore nel caricamento dei dati di alert.");
    } finally {
      setIsLoadingAlertRow(false);
    }
  }

  async function createQuickAlert() {
    if (!activeAlertTicker || !alertRow) return;
    const targetM = activeAlertMarket || market;
    let val: number | string;
    if (alertField === "Signal6") {
      val = alertValue.trim();
      if (!val) { setAlertMsg("Valore alert non valido."); return; }
    } else {
      let parsed = Number(alertValue.replace(",", ".").trim());
      if (Number.isNaN(parsed)) { setAlertMsg("Valore alert non valido."); return; }
      if (alertField === "Williams_R" && parsed > 0) parsed = -parsed;
      val = parsed;
    }

    setAlertBusy(true);
    setAlertMsg(null);
    try {
      const normalizedTicker = activeAlertTicker.trim().toUpperCase().replace(/[^A-Z0-9]+/g, "_").replace(/^_+|_+$/g, "");
      const rid = `CARD_ALERT_${normalizedTicker}`;
      const payload = {
        id: rid, enabled: true,
        scope: { tickers: [activeAlertTicker] },
        when: { all: [{ field: alertField, op: alertOp, value: val }] },
        cooldown_minutes: 0, max_per_day: 3, min_gap_minutes: 0,
        message: {
          title: "🔔 Alert {{Ticker}}",
          body: "Close: {{Close}}\nRSI: {{RSI}}\nwillR: {{Williams_R}}\nSARMA: {{SIG_MA_SAR}}\nMACD: {{MACD}}\nS3: {{MACD_vs_Signal}}\nAction: {{Action}}\nTECH: {{TECH_SCORE}}\nAlligator: {{Signal6}}"
        }
      };
      const res = await fetch(`/api/alerts/${encodeURIComponent(targetM)}/upsert`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payload })
      });
      if (!res.ok) throw new Error(`Errore nel salvataggio dell'alert: ${res.statusText}`);
      setAlertSet(true);
      setAlertMsg(`Alert salvato per ${activeAlertTicker} (${alertField} ${alertOp} ${val})!`);
    } catch (err: any) {
      setAlertMsg(`Errore: ${err.message || err}`);
    } finally {
      setAlertBusy(false);
    }
  }

  async function removeQuickAlert() {
    if (!activeAlertTicker) return;
    const targetM = activeAlertMarket || market;
    setAlertBusy(true);
    setAlertMsg(null);
    try {
      const normalizedTicker = activeAlertTicker.trim().toUpperCase().replace(/[^A-Z0-9]+/g, "_").replace(/^_+|_+$/g, "");
      const rid = `CARD_ALERT_${normalizedTicker}`;
      const res = await fetch(`/api/alerts/${encodeURIComponent(targetM)}/${encodeURIComponent(rid)}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`Errore rimozione: ${res.statusText}`);
      setAlertSet(false);
      setAlertField("Close");
      setAlertOp(">");
      if (alertRow?.Close !== undefined) setAlertValue(String(alertRow.Close));
      setAlertMsg(`Alert rimosso per ${activeAlertTicker}.`);
    } catch (err: any) {
      setAlertMsg(`Errore: ${err.message || err}`);
    } finally {
      setAlertBusy(false);
    }
  }

  function renderMarkdown(text: string) {
    if (!text) return null;
    return text.split("\n").map((line, idx) => {
      const clean = line.trim();
      if (!clean) return <div key={idx} style={{ height: "0.6rem" }} />;
      if (clean.startsWith("### ")) return <h3 key={idx} style={{ marginTop: "1.2rem", marginBottom: "0.5rem", color: "#ffffff", fontSize: "1.1rem", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "0.3rem" }}>{clean.slice(4)}</h3>;
      if (clean.startsWith("#### ")) return <h4 key={idx} style={{ marginTop: "0.9rem", marginBottom: "0.4rem", color: "#8cb4d9", fontSize: "0.95rem" }}>{clean.slice(5)}</h4>;
      if (clean.startsWith("- ")) {
        const parts = clean.slice(2).split("**");
        return <li key={idx} style={{ marginLeft: "1.2rem", marginBottom: "0.35rem", color: "#b8d4ee", listStyleType: "disc", fontSize: "0.88rem" }}>{parts.map((p, i) => i % 2 === 1 ? <strong key={i} style={{ color: "#ffffff", fontWeight: 700 }}>{p}</strong> : p)}</li>;
      }
      if (clean.startsWith("🟢")) return <p key={idx} style={{ color: "#4ade80", backgroundColor: "rgba(34,197,94,0.12)", border: "1px solid rgba(74,222,128,0.3)", borderRadius: "8px", padding: "0.6rem 0.8rem", margin: "0.8rem 0", fontSize: "0.9rem", fontWeight: 600 }}>{clean}</p>;
      if (clean.startsWith("🟡")) return <p key={idx} style={{ color: "#fbbf24", backgroundColor: "rgba(245,158,11,0.12)", border: "1px solid rgba(251,191,36,0.3)", borderRadius: "8px", padding: "0.6rem 0.8rem", margin: "0.8rem 0", fontSize: "0.9rem", fontWeight: 600 }}>{clean}</p>;
      if (clean.startsWith("🔴")) return <p key={idx} style={{ color: "#f87171", backgroundColor: "rgba(239,68,68,0.12)", border: "1px solid rgba(248,113,113,0.3)", borderRadius: "8px", padding: "0.6rem 0.8rem", margin: "0.8rem 0", fontSize: "0.9rem", fontWeight: 600 }}>{clean}</p>;
      const parts = clean.split("**");
      if (parts.length > 1) return <p key={idx} style={{ margin: "0.4rem 0", color: "#dbe8f6", fontSize: "0.88rem", lineHeight: "1.45" }}>{parts.map((p, i) => i % 2 === 1 ? <strong key={i} style={{ color: "#ffffff", fontWeight: 700 }}>{p}</strong> : p)}</p>;
      return <p key={idx} style={{ margin: "0.4rem 0", color: "#dbe8f6", fontSize: "0.88rem", lineHeight: "1.45" }}>{clean}</p>;
    });
  }

  // ─── Derived label for active config ─────────────────────────────────────────
  const activePatternLabel = allTabs.find(t => t.id === pattern)?.label ?? pattern;
  const marketLabel = labMarket === "ALL" ? "Tutti i Mercati" : labMarkets.join(" + ");
  const lookbackLabel = lookback === 1 ? "Solo Oggi" : `Ultimi ${lookback}gg`;
  const filterLabel = [useSar ? "SAR" : null, useSma200 ? "SMA200" : null].filter(Boolean).join(", ") || "Nessuno";

  return (
    <div style={{ marginTop: "1rem", display: "grid", gap: "1rem", maxWidth: "100%", overflow: "hidden" }}>

      {/* ══════════════ HEADER COMPATTO ══════════════ */}
      <section className="hero" style={{ flexDirection: "column", gap: "0.7rem", alignItems: "stretch", padding: "1rem 1.2rem" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem" }}>
          <div>
            <h2 style={{ fontSize: "1.15rem", margin: 0, color: "#ffffff" }}>🧪 Laboratorio Multi-Pattern</h2>
            <p style={{ fontSize: "0.78rem", color: "#8cb4d9", margin: "0.2rem 0 0 0" }}>
              Scansione pattern di inversione (S2–S4) con simulazione vectorbt istantanea.
            </p>
          </div>
          {/* Config toggle */}
          <button
            onClick={() => setConfigOpen(o => !o)}
            style={{
              display: "flex", alignItems: "center", gap: "0.4rem",
              padding: "0.35rem 0.8rem", borderRadius: "8px", cursor: "pointer",
              background: configOpen ? "rgba(96,165,250,0.15)" : "rgba(255,255,255,0.06)",
              border: `1px solid ${configOpen ? "rgba(96,165,250,0.4)" : "rgba(255,255,255,0.12)"}`,
              color: configOpen ? "#60a5fa" : "#b8d4ee", fontSize: "0.8rem", fontWeight: 600,
              transition: "all 0.2s ease"
            }}
          >
            ⚙️ Configurazione
            <span style={{ fontSize: "0.65rem", opacity: 0.7, marginLeft: "0.1rem" }}>
              {configOpen ? "▲" : "▼"}
            </span>
          </button>
        </div>

        {/* Config summary badge row (always visible) */}
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
          {[
            { icon: "🌐", val: marketLabel },
            { icon: "📅", val: lookbackLabel },
            { icon: "🛡️", val: `Filtri: ${filterLabel}` },
          ].map((b, i) => (
            <span key={i} style={{
              fontSize: "0.75rem", padding: "0.2rem 0.55rem", borderRadius: "20px",
              background: "rgba(96,165,250,0.08)", border: "1px solid rgba(96,165,250,0.18)",
              color: "#8cb4d9", display: "flex", alignItems: "center", gap: "0.3rem"
            }}>
              {b.icon} {b.val}
            </span>
          ))}
        </div>

        {/* ── Pannello Configurazione Collassabile ── */}
        {configOpen && (
          <div style={{
            display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
            gap: "0.8rem", marginTop: "0.2rem",
            borderTop: "1px solid rgba(184,216,246,0.12)", paddingTop: "0.8rem",
            animation: "fadeIn 0.15s ease"
          }}>
            {/* Mercato */}
            <div style={cfgBoxStyle}>
              <span style={cfgLabelStyle}>🌐 Ambito Scansione</span>
              <label style={checkboxLabelStyle}>
                <input
                  type="checkbox"
                  checked={labMarkets.length === SCAN_MARKETS.length}
                  onChange={(e) => setLabMarkets(e.target.checked ? [...SCAN_MARKETS] : ["MIB30"])}
                  style={{ cursor: "pointer", accentColor: "#60a5fa" }}
                />
                <strong>✨ Tutti i mercati</strong>
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "0.35rem" }}>
                {SCAN_MARKETS.map((marketName) => (
                  <label key={marketName} style={checkboxLabelStyle}>
                    <input
                      type="checkbox"
                      checked={labMarkets.includes(marketName)}
                      onChange={(e) => {
                        setLabMarkets((current) => {
                          if (e.target.checked) return [...current, marketName];
                          if (current.length === 1) return current;
                          return current.filter((item) => item !== marketName);
                        });
                      }}
                      style={{ cursor: "pointer", accentColor: "#60a5fa" }}
                    />
                    <span>{marketName}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Lookback */}
            <div style={cfgBoxStyle}>
              <span style={cfgLabelStyle}>📅 Anzianità Segnale</span>
              <select value={lookback} onChange={(e) => setLookback(Number(e.target.value))} style={selectStyle}>
                <option value={1}>Solo Oggi (Fresco)</option>
                <option value={2}>Fino a Ieri (2gg)</option>
                <option value={3}>Ultimi 3 giorni</option>
                <option value={5}>Ultimi 5 giorni</option>
                <option value={10}>Ultimi 10 giorni</option>
              </select>
            </div>

            {/* Filtri */}
            <div style={{ ...cfgBoxStyle, justifyContent: "center" }}>
              <span style={cfgLabelStyle}>🛡️ Filtri Ausiliari</span>
              <label style={checkboxLabelStyle}>
                <input type="checkbox" checked={useSar} onChange={(e) => setUseSar(e.target.checked)} style={{ cursor: "pointer", accentColor: "#60a5fa" }} />
                <span>Richiedi Close &gt; SAR</span>
              </label>
              <label style={checkboxLabelStyle}>
                <input type="checkbox" checked={useSma200} onChange={(e) => setUseSma200(e.target.checked)} style={{ cursor: "pointer", accentColor: "#60a5fa" }} />
                <span>Richiedi Close &gt; SMA200</span>
              </label>
            </div>

            {/* Guida regole */}
            <div style={{ ...cfgBoxStyle, gridColumn: "1 / -1" }}>
              <details style={{ width: "100%" }}>
                <summary style={{ fontSize: "0.8rem", fontWeight: 600, color: "#b8d4ee", cursor: "pointer", userSelect: "none" }}>
                  📖 Guida Regole e Formule (espandi)
                </summary>
                <div style={{ marginTop: "0.7rem", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", fontSize: "0.78rem", lineHeight: "1.4", color: "#b8d4ee" }}>
                  <div>
                    <h4 style={{ color: "#4ade80", margin: "0 0 0.3rem 0", fontSize: "0.82rem" }}>🟢 S2 (Williams %R + Stoch)</h4>
                    <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                      <li>WR in crescita &amp; WR &gt; -80</li>
                      <li>Stoch K cross &gt; 20, K &gt; D</li>
                    </ul>
                    <h4 style={{ color: "#fbbf24", margin: "0.6rem 0 0.3rem 0", fontSize: "0.82rem" }}>✨ Combined (S2 &amp; S3)</h4>
                    <p style={{ margin: 0 }}>Tutte le condizioni S2 e S3 nello stesso giorno.</p>
                  </div>
                  <div>
                    <h4 style={{ color: "#38bdf8", margin: "0 0 0.3rem 0", fontSize: "0.82rem" }}>🔵 S3 (MACD Crossover)</h4>
                    <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                      <li>MACD cross &gt; Signal</li>
                      <li>MACD in pendenza positiva</li>
                      <li>Istogramma &gt; 0 e crescente</li>
                    </ul>
                    <h4 style={{ color: "#f87171", margin: "0.6rem 0 0.3rem 0", fontSize: "0.82rem" }}>🛡️ Filtri Ausiliari</h4>
                    <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                      <li>SAR: Close &gt; SAR</li>
                      <li>Trend: Close &gt; SMA200</li>
                    </ul>
                  </div>
                  <div>
                    <h4 style={{ color: "#a78bfa", margin: "0 0 0.3rem 0", fontSize: "0.82rem" }}>🟣 S4 (EMA Momentum + Vol)</h4>
                    <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                      <li>EMA9 &gt; EMA21</li>
                      <li>RSI tra 55 e 70, crescente</li>
                      <li>MACD &gt; Signal</li>
                      <li>Volume &gt; Media(20) × 1.5</li>
                    </ul>
                    <h4 style={{ color: "#34d399", margin: "0.6rem 0 0.3rem 0", fontSize: "0.82rem" }}>🐊 S7 (Alligator Bull)</h4>
                    <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                      <li>Early: Close &gt; SAR, Uptrend/Uptrend-, DI+ &gt; DI-</li>
                      <li>Confirmed: Uptrend pieno, EMA30 &gt; EMA50, ADX ≥ 20</li>
                      <li>Strong: ADX ≥ 25, sopra SMA200, volume ≥ MA20</li>
                      <li>Il segnale scatta solo all'ingresso nel livello</li>
                    </ul>
                  </div>
                </div>
              </details>
            </div>
          </div>
        )}
      </section>

      {/* ══════════════ PATTERN TABS + SCAN BUTTON ══════════════ */}
      <div style={{
        display: "flex", alignItems: "center", gap: "0.5rem",
        background: "rgba(10, 25, 47, 0.45)",
        border: "1px solid rgba(184, 216, 246, 0.14)",
        borderRadius: "14px", padding: "0.5rem 0.6rem",
        backdropFilter: "blur(10px)", flexWrap: "wrap"
      }}>
        {/* Pattern selector pills */}
        <div style={{ display: "flex", gap: "0.3rem", flex: "1 1 auto", overflowX: "auto", scrollbarWidth: "none" as any }}>
          {allTabs.map((t) => {
            const active = pattern === t.id;
            return (
              <button
                key={t.id}
                onClick={() => handlePatternChange(t.id as any)}
                style={{
                  flex: "0 0 auto",
                  display: "flex", flexDirection: "column", alignItems: "center",
                  padding: "0.5rem 0.7rem", borderRadius: "10px", border: "none",
                  cursor: "pointer",
                  background: active ? `rgba(${hexToRgb(t.color)}, 0.15)` : "transparent",
                  boxShadow: active ? `0 0 0 1.5px ${t.color}55` : "none",
                  transition: "all 0.18s ease", outline: "none",
                }}
              >
                <span style={{ fontSize: "0.85rem", fontWeight: 700, color: active ? "#ffffff" : "#b8d4ee", whiteSpace: "nowrap" }}>
                  {t.label}
                </span>
                <span style={{ fontSize: "0.66rem", color: active ? t.color : "#8cb4d9", marginTop: "0.1rem", whiteSpace: "nowrap" }}>
                  {t.desc}
                </span>
              </button>
            );
          })}
        </div>

        {/* ── SCAN BUTTON ── */}
        <button
          className="btn"
          disabled={isScanning}
          onClick={handleScan}
          style={{
            flex: "0 0 auto", height: "48px", minWidth: "190px",
            fontWeight: 700, letterSpacing: "0.03em", fontSize: "0.88rem",
            background: "linear-gradient(135deg, #3b82f6 0%, #6366f1 50%, #1e40af 100%)",
            backgroundSize: "200% 200%",
            animation: isScanning ? "shimmerBtn 2s ease infinite, glowPulse 1.5s ease-in-out infinite" : "none",
            border: isScanning ? "1px solid rgba(99,102,241,0.7)" : "1px solid rgba(59,130,246,0.5)",
            borderRadius: "10px", color: "#ffffff", cursor: isScanning ? "wait" : "pointer",
            display: "flex", alignItems: "center", justifyContent: "center", gap: "0.5rem",
            transition: "border 0.2s ease",
            boxShadow: isScanning
              ? "0 0 0 3px rgba(99,102,241,0.3), 0 4px 20px rgba(59,130,246,0.5)"
              : "0 2px 12px rgba(59,130,246,0.35)",
          }}
        >
          {isScanning ? (
            <>
              <span style={{
                width: "16px", height: "16px", borderRadius: "50%",
                border: "2.5px solid rgba(255,255,255,0.3)",
                borderTopColor: "#ffffff",
                animation: "spin 0.75s linear infinite",
                display: "inline-block", flexShrink: 0,
              }} />
              {scanProgress
                ? `${scanProgress.market}: ${scanProgress.done}/${scanProgress.total}`
                : "Analisi in corso..."}
            </>
          ) : (
            <>🔍 Avvia Scansione</>
          )}
        </button>
      </div>

      {fallbackWarnings.length > 0 && (
        <div role="alert" style={{
          padding: "0.75rem 1rem", borderRadius: "10px",
          background: "rgba(245,158,11,0.14)", border: "1px solid rgba(245,158,11,0.45)",
          color: "#fbbf24", fontSize: "0.82rem", lineHeight: 1.45,
        }}>
          <strong>⚠️ Fallback Yahoo Finance attivato.</strong>
          {fallbackWarnings.map((warning) => <div key={warning}>{warning}</div>)}
        </div>
      )}

      {/* ── Prompt iniziale / dopo cambio pattern ── */}
      {!isScanning && !scanResults && !scanError && (
        <div style={{
          textAlign: "center", padding: "2.5rem 1rem",
          background: "rgba(7,17,32,0.45)", borderRadius: "16px",
          border: "1px solid rgba(96,165,250,0.12)",
          animation: "fadeIn 0.2s ease"
        }}>
          <span style={{ fontSize: "2rem", display: "block", marginBottom: "0.5rem" }}>🔍</span>
          <p style={{ margin: 0, fontSize: "1rem", color: "#cfe5fa", fontWeight: 600 }}>
            Premi <strong style={{ color: "#60a5fa" }}>Avvia Scansione</strong> per cercare i titoli con pattern <strong style={{ color: allTabs.find(t => t.id === pattern)?.color ?? "#fff" }}>{activePatternLabel}</strong>
          </p>
          <p style={{ margin: "0.4rem 0 0 0", fontSize: "0.8rem", color: "#8cb4d9" }}>
            Mercato: {marketLabel} · {lookbackLabel} · Filtri: {filterLabel}
          </p>
        </div>
      )}

      {/* ══════════════ RISULTATI SCANSIONE ══════════════ */}
      {scanError && !isScanning && (
        <div style={{ padding: "0.8rem 1rem", borderRadius: "12px", border: "1px solid rgba(239,68,68,0.2)", backgroundColor: "rgba(239,68,68,0.06)", color: "#fca5a5", fontSize: "0.88rem" }}>
          {scanError}
        </div>
      )}

      {isScanning && (
        <div style={{ textAlign: "center", padding: "2.5rem 1.5rem", background: "rgba(7,17,32,0.65)", borderRadius: "16px", border: "1px solid rgba(59,130,246,0.25)", animation: "fadeIn 0.3s ease", position: "relative", overflow: "hidden" }}>
          {/* Barra luminosa in cima */}
          <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: "3px", background: "linear-gradient(90deg, transparent 0%, #3b82f6 50%, #6366f1 80%, transparent 100%)", backgroundSize: "200% 100%", animation: "shimmerBtn 1.8s linear infinite" }} />

          {/* Icona con anelli radar */}
          <div style={{ position: "relative", width: "60px", height: "60px", margin: "0 auto 1.2rem", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span style={{ fontSize: "1.6rem", zIndex: 1, position: "relative" }}>🔍</span>
            <span style={{ position: "absolute", inset: 0, borderRadius: "50%", border: "2px solid rgba(59,130,246,0.8)", animation: "radarPulse 1.8s ease-out infinite" }} />
            <span style={{ position: "absolute", inset: 0, borderRadius: "50%", border: "2px solid rgba(99,102,241,0.6)", animation: "radarPulse 1.8s ease-out infinite 0.6s" }} />
            <span style={{ position: "absolute", inset: 0, borderRadius: "50%", border: "2px solid rgba(139,92,246,0.4)", animation: "radarPulse 1.8s ease-out infinite 1.2s" }} />
          </div>

          {/* Progress bar indeterminata */}
          <div style={{ width: "100%", maxWidth: "300px", margin: "0 auto 1rem", height: "4px", background: "rgba(59,130,246,0.15)", borderRadius: "4px", overflow: "hidden", position: "relative" }}>
            <div style={{ width: "45%", height: "100%", borderRadius: "4px", background: "linear-gradient(90deg, rgba(59,130,246,0), #3b82f6, #6366f1, rgba(99,102,241,0))", animation: "progressScan 1.6s ease-in-out infinite", position: "absolute" }} />
          </div>

          <span style={{ fontSize: "1rem", display: "block", color: "#60a5fa", fontWeight: 700, marginBottom: "0.35rem" }}>Scansione mercati in corso...</span>
          <span style={{ fontSize: "0.82rem", color: "#8cb4d9", display: "block" }}>
            Pattern: <strong style={{ color: "#a5f3fc" }}>{activePatternLabel}</strong> · Mercato: <strong style={{ color: "#a5f3fc" }}>{marketLabel}</strong>
          </span>
        </div>
      )}

      {!isScanning && scanResults && (
        filteredResults.length > 0 ? (
          <section className="card" style={{ padding: "0.9rem", overflow: "hidden", maxWidth: "100%" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.6rem", flexWrap: "wrap", gap: "0.4rem" }}>
              <h3 style={{ margin: 0, fontSize: "1rem", color: "#cfe5fa" }}>
                🎯 {filteredResults.length} titoli trovati · <span style={{ color: "#60a5fa" }}>{marketLabel}</span>
              </h3>
              <span style={{ fontSize: "0.75rem", color: "#8cb4d9" }}>
                Clicca riga → backtest istantaneo
              </span>
            </div>

            <div className="table-wrap" style={{ maxHeight: "560px", overflowX: "auto", width: "100%" }}>
              <table>
                <thead>
                  <tr>
                    {([
                      { label: "Ticker",     key: "Ticker"          },
                      ...(labMarkets.length > 1 ? [{ label: "Mercato", key: "Market" }] : []),
                      { label: "Nome",       key: "Name"            },
                      { label: "Prezzo",     key: "Close"           },
                      { label: "Segnale fa", key: "Pattern_Days_Ago" },
                      { label: "Pattern",    key: null               },
                      { label: "Var. Giorn.",key: "Daily_Var_Pct"   },
                      { label: "Var. Seg.",  key: "Signal_Var_Pct"  },
                      { label: "Stoch_K",    key: "Stoch_K"         },
                      { label: "Stoch_D",    key: "Stoch_D"         },
                      { label: "Will %R",    key: "Williams_R"      },
                      { label: "MACD",       key: "MACD"            },
                      { label: "ADX",        key: "ADX"             },
                      { label: "SAR",        key: "SAR"             },
                      { label: "Pos. 1Y%",   key: "Range_Pct"       },
                      { label: "Δ Max 1Y",   key: "Dist_From_High"  },
                    ] as { label: string; key: keyof ScanResult | null }[]).map((col) => (
                      <th
                        key={col.label}
                        onClick={col.key ? () => handleSort(col.key as keyof ScanResult) : undefined}
                        style={{
                          cursor: col.key ? "pointer" : "default",
                          userSelect: "none",
                          whiteSpace: "nowrap",
                          color: sortKey === col.key && sortDir ? "#60a5fa" : undefined,
                          transition: "color 0.15s",
                        }}
                        title={col.key ? `Ordina per ${col.label}` : undefined}
                      >
                        {col.label}
                        {col.key && (
                          <span style={{ marginLeft: "0.25rem", fontSize: "0.7rem", opacity: sortKey === col.key && sortDir ? 1 : 0.25 }}>
                            {sortKey === col.key && sortDir === "asc"  ? "▲"
                             : sortKey === col.key && sortDir === "desc" ? "▼"
                             : "⇅"}
                          </span>
                        )}
                      </th>
                    ))}
                    <th style={{ width: "6%", textAlign: "center" }}>Alert</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedResults.map((row) => (
                    <tr
                      key={row.Ticker}
                      onClick={() => handleSelectRow(row.Ticker)}
                      className={selectedTicker === row.Ticker ? "active-row" : ""}
                      style={{
                        cursor: "pointer",
                        backgroundColor: selectedTicker === row.Ticker ? "rgba(38,103,169,0.22)" : "transparent",
                        transition: "background-color 0.15s"
                      }}
                    >
                      <td style={{ fontWeight: "bold", color: "#ffffff" }}>
                        <span
                          onClick={(e) => { e.stopPropagation(); onOpenInteractiveChart?.(row); }}
                          style={{ textDecoration: "underline", cursor: "pointer", color: "#60a5fa" }}
                          title="Grafico interattivo"
                        >
                          {row.Ticker}
                        </span>
                      </td>
                      {labMarkets.length > 1 && <td style={{ fontWeight: "bold", color: "#38bdf8" }}>{row.Market}</td>}
                      <td style={{ color: "#8cb4d9" }}>{row.Name}</td>
                      <td style={{ fontWeight: 800 }}>{row.Close.toFixed(3)}</td>
                      <td style={{ fontWeight: "bold", color: row.Pattern_Days_Ago === 0 ? "#4ade80" : row.Pattern_Days_Ago === 1 ? "#fbbf24" : "#94a3b8" }}>
                        {row.Pattern_Days_Ago === 0 ? "Oggi" : row.Pattern_Days_Ago === 1 ? "Ieri" : `${row.Pattern_Days_Ago}gg fa`}
                      </td>
                      {(() => {
                        const displayPt = row.Pattern_Type || pattern;
                        const ptColor =
                          displayPt === "S2 & S3" || displayPt === "Combined" ? "#4ade80"
                          : displayPt === "S2"       ? "#60a5fa"
                          : displayPt === "S3"       ? "#38bdf8"
                          : displayPt === "S4"       ? "#a78bfa"
                          : displayPt === "S2_or_S3" ? "#f97316"
                          : displayPt.includes("RSI") || displayPt.includes("S5") ? "#f472b6"
                          : displayPt.includes("Golden") || displayPt.includes("S6") ? "#fbbf24"
                          : displayPt.includes("Alligator") || displayPt.includes("S7") ? "#34d399"
                          : displayPt.includes("Volume") || displayPt.includes("S8") ? "#c084fc"
                          : "#fbbf24";
                        return (
                          <td style={{ fontWeight: "bold", color: ptColor }}>
                            {displayPt}
                          </td>
                        );
                      })()}
                      <td style={{ fontWeight: "bold", color: !row.Daily_Var_Pct ? "#94a3b8" : row.Daily_Var_Pct > 0 ? "#4ade80" : "#f87171" }}>
                        {row.Daily_Var_Pct !== undefined ? `${row.Daily_Var_Pct >= 0 ? "+" : ""}${row.Daily_Var_Pct.toFixed(2)}%` : "-"}
                      </td>
                      <td style={{ fontWeight: "bold", color: !row.Signal_Var_Pct ? "#94a3b8" : row.Signal_Var_Pct > 0 ? "#4ade80" : "#f87171" }}>
                        {row.Signal_Var_Pct !== undefined ? `${row.Signal_Var_Pct >= 0 ? "+" : ""}${row.Signal_Var_Pct.toFixed(2)}%` : "-"}
                      </td>
                      <td style={{ color: row.Stoch_K && row.Stoch_K < 20 ? "#f87171" : "#4ade80" }}>{row.Stoch_K ? row.Stoch_K.toFixed(2) : "-"}</td>
                      <td style={{ color: row.Stoch_D && row.Stoch_D < 20 ? "#f87171" : "#4ade80" }}>{row.Stoch_D ? row.Stoch_D.toFixed(2) : "-"}</td>
                      <td style={{ color: row.Williams_R && row.Williams_R < -80 ? "#f87171" : "#dbe8f6" }}>{row.Williams_R ? row.Williams_R.toFixed(2) : "-"}</td>
                      <td>{row.MACD ? row.MACD.toFixed(3) : "-"}</td>
                      <td style={{ color: row.ADX && row.ADX >= 25 ? "#60a5fa" : "#9fb7cf" }}>{row.ADX ? row.ADX.toFixed(1) : "-"}</td>
                      <td style={{ fontSize: "0.8rem", color: "#9fb7cf" }}>{row.SAR ? row.SAR.toFixed(3) : "-"}</td>
                      {/* ── Posizione nel range 1Y ── */}
                      <td style={{ textAlign: "center" }}>
                        {row.Range_Pct !== undefined ? (() => {
                          const rp = row.Range_Pct as number;
                          const col = rp >= 85 ? "#f87171" : rp >= 65 ? "#fb923c" : rp >= 40 ? "#fbbf24" : "#4ade80";
                          return (
                            <span style={{
                              display: "inline-block", padding: "0.15rem 0.45rem",
                              borderRadius: "10px", fontSize: "0.78rem", fontWeight: 700,
                              background: `${col}22`, border: `1px solid ${col}55`, color: col
                            }}>
                              {rp.toFixed(0)}%
                            </span>
                          );
                        })() : "-"}
                      </td>
                      {/* ── Distanza dal massimo 1Y ── */}
                      <td style={{
                        fontSize: "0.8rem", fontWeight: 600,
                        color: row.Dist_From_High !== undefined
                          ? (row.Dist_From_High as number) > -5  ? "#f87171"
                          : (row.Dist_From_High as number) > -15 ? "#fbbf24"
                          : "#4ade80"
                          : "#9fb7cf"
                      }}>
                        {row.Dist_From_High !== undefined ? `${(row.Dist_From_High as number).toFixed(1)}%` : "-"}
                      </td>
                      <td style={{ textAlign: "center" }} onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => handleOpenAlert(row.Ticker, row.Market)}
                          style={{ background: "transparent", border: "none", cursor: "pointer", fontSize: "1.1rem", padding: "0.2rem", lineHeight: "1", outline: "none" }}
                          title="Configura alert"
                        >🔔</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Watchlist Cards Grid */}
            <div style={{ marginTop: "1.5rem", borderTop: "1px solid rgba(184,216,246,0.12)", paddingTop: "1.2rem" }}>
              <h4 style={{ margin: "0 0 1rem 0", color: "#ffffff", fontSize: "1rem" }}>
                🗂️ Schede Dettaglio ({filteredResults.length} titoli)
              </h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "1.2rem", width: "100%" }}>
                {sortedResults.map((row, idx) => {
                  const rowKey = `${row.Ticker}-${idx}`;
                  const rowMarket = row.Market || market;
                  const key = `${String(rowMarket).trim().toUpperCase()}::${String(row.Ticker).trim().toUpperCase()}`;
                  return (
                    <WatchlistCard
                      key={rowKey}
                      row={row}
                      onChart={onChart}
                      onAi={onAi}
                      aiActive={Boolean(aiActiveChatMap[key])}
                      aiAlertInfo={aiAlertCardMap[key] ?? null}
                      aiLevelAlerts={aiLevelCardMap[key] ?? []}
                      onToggleAiAlert={onToggleAiAlert}
                      onDeleteAiAlert={onDeleteAiAlert}
                      sourceMarket={String(rowMarket)}
                      alertSet={Boolean(quickAlertMap[key])}
                      alertConfig={quickAlertConfigMap[key] ?? null}
                      alertBusy={Boolean(quickAlertBusyMap[key])}
                      onCreateAlert={onCreateAlert}
                      onRemoveAlert={onRemoveAlert}
                      customWatchlists={customWatchlists}
                      onAddToWatchlist={onAddToWatchlist}
                      currentWatchlistName={currentWatchlistName}
                      onRemoveFromWatchlist={onRemoveFromWatchlist}
                    />
                  );
                })}
              </div>
            </div>
          </section>
        ) : (
          <div style={{
            textAlign: "center", padding: "2.5rem 1rem",
            background: "rgba(7,17,32,0.45)", borderRadius: "16px",
            border: "1px solid rgba(96,165,250,0.12)",
            animation: "fadeIn 0.2s ease"
          }}>
            <span style={{ fontSize: "2rem", display: "block", marginBottom: "0.5rem" }}>⚠️</span>
            <p style={{ margin: 0, fontSize: "1rem", color: "#cfe5fa", fontWeight: 600 }}>
              Nessun titolo corrisponde ai criteri di filtraggio.
            </p>
            <p style={{ margin: "0.4rem 0 0 0", fontSize: "0.8rem", color: "#8cb4d9" }}>
              Prova ad abbassare il volume minimo (attualmente {minVolume}).
            </p>
          </div>
        )
      )}

      {/* ══════════════ QUICK ALERT MODAL ══════════════ */}
      {activeAlertTicker && (
        <div
          role="presentation"
          onMouseDown={(event) => { if (event.target === event.currentTarget) closeAlertModal(); }}
          style={{
            position: "fixed", inset: 0, zIndex: 1200,
            display: "flex", alignItems: "center", justifyContent: "center",
            padding: "1.25rem", background: "rgba(2,8,18,0.78)",
            backdropFilter: "blur(5px)",
          }}
        >
        <section
          role="dialog"
          aria-modal="true"
          aria-label={`Alert rapido ${activeAlertTicker}`}
          className="card"
          style={{
            padding: "1.2rem", width: "min(920px, 96vw)", maxHeight: "88vh",
            overflowY: "auto", border: "1px solid rgba(96,165,250,0.45)",
            background: "#0a192f", boxShadow: "0 24px 80px rgba(0,0,0,0.55)",
          }}
        >
          <h3 style={{ margin: "0 0 0.8rem 0", fontSize: "1rem", color: "#cfe5fa", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>🔔 Alert Rapido: <strong style={{ color: "#ffffff" }}>{activeAlertTicker}</strong></span>
            <button onClick={closeAlertModal} style={{ background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.15)", color: "#fff", padding: "0.2rem 0.5rem", borderRadius: "6px", fontSize: "0.78rem", cursor: "pointer" }}>Chiudi</button>
          </h3>

          {isLoadingAlertRow ? (
            <p style={{ margin: 0, fontSize: "0.88rem" }}>Caricamento dati...</p>
          ) : alertError ? (
            <p style={{ margin: 0, color: "#fca5a5", fontSize: "0.88rem" }}>{alertError}</p>
          ) : alertRow ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.6rem 1.2rem", background: "rgba(8,18,34,0.4)", padding: "0.6rem 0.8rem", borderRadius: "8px", fontSize: "0.82rem", border: "1px solid rgba(184,216,246,0.1)" }}>
                <span>Prezzo: <strong style={{ color: "#fff" }}>{alertRow.Close?.toFixed(3)}</strong></span>
                <span>S3: <strong style={{ color: alertRow.MACD_vs_Signal > 0 ? "#22c55e" : "#ef4444" }}>{alertRow.MACD_vs_Signal ?? "-"}</strong></span>
                <span>RSI: <strong style={{ color: alertRow.RSI >= 45 ? "#22c55e" : "#ef4444" }}>{alertRow.RSI?.toFixed(1) ?? "-"}</strong></span>
                <span>willR: <strong style={{ color: alertRow.Williams_R >= -80 ? "#22c55e" : "#ef4444" }}>{alertRow.Williams_R?.toFixed(1) ?? "-"}</strong></span>
                <span>SARMA: <strong style={{ color: alertRow.SIG_MA_SAR > 0 ? "#22c55e" : "#ef4444" }}>{alertRow.SIG_MA_SAR ?? "-"}</strong></span>
                {alertRow.Pattern_S2_Days_Ago !== undefined && (
                  <span>S2: <strong style={{ color: alertRow.Pattern_S2_Days_Ago === 0 ? "#22c55e" : "#8cb4d9" }}>{alertRow.Pattern_S2_Days_Ago}d</strong></span>
                )}
                {alertRow.Pattern_S3_Days_Ago !== undefined && (
                  <span>S3_Pat: <strong style={{ color: alertRow.Pattern_S3_Days_Ago === 0 ? "#22c55e" : "#8cb4d9" }}>{alertRow.Pattern_S3_Days_Ago}d</strong></span>
                )}
                {alertRow.Pattern_S4_Days_Ago !== undefined && (
                  <span>S4: <strong style={{ color: alertRow.Pattern_S4_Days_Ago === 0 ? "#22c55e" : "#8cb4d9" }}>{alertRow.Pattern_S4_Days_Ago}d</strong></span>
                )}
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                  {[
                    { field: "Close", label: "Prezzo", val: alertRow.Close },
                    { field: "MACD_vs_Signal", label: "S3", val: alertRow.MACD_vs_Signal },
                    { field: "MACD", label: "MACD", val: alertRow.MACD },
                    { field: "RSI", label: "RSI", val: alertRow.RSI },
                    { field: "SIG_MA_SAR", label: "SARMA", val: alertRow.SIG_MA_SAR },
                    { field: "SAR_Above_Price", label: "SAR vs Prezzo", val: 0 },
                    { field: "Williams_R", label: "willR", val: alertRow.Williams_R },
                    { field: "Signal6", label: "Alligator", val: alertRow.Signal6 }
                  ].map((preset) => (
                    <button key={preset.field} onClick={() => { setAlertField(preset.field as QuickAlertField); setAlertOp(preset.field === "Signal6" || preset.field === "SAR_Above_Price" ? "==" : ">"); if (preset.val !== undefined && preset.val !== null) setAlertValue(String(preset.val)); }} style={{ padding: "0.3rem 0.6rem", borderRadius: "6px", fontSize: "0.78rem", fontWeight: 600, cursor: "pointer", background: alertField === preset.field ? "rgba(96,165,250,0.25)" : "rgba(255,255,255,0.05)", border: `1px solid ${alertField === preset.field ? "rgba(96,165,250,0.5)" : "rgba(255,255,255,0.15)"}`, color: alertField === preset.field ? "#60a5fa" : "#cfe5fa" }}>
                      {preset.label}
                    </button>
                  ))}
                </div>
                <div style={{ display: "flex", gap: "0.4rem" }}>
                  {alertField === "SAR_Above_Price" ? null : alertField === "Signal6" ? (
                    (["==", "!="] as const).map((o) => (
                      <button key={o} onClick={() => setAlertOp(o)} style={{ padding: "0.25rem 0.6rem", borderRadius: "6px", fontSize: "0.8rem", fontWeight: "bold", cursor: "pointer", width: "36px", background: alertOp === o ? "rgba(96,165,250,0.25)" : "rgba(255,255,255,0.05)", border: `1px solid ${alertOp === o ? "rgba(96,165,250,0.5)" : "rgba(255,255,255,0.15)"}`, color: alertOp === o ? "#60a5fa" : "#cfe5fa" }}>{o}</button>
                    ))
                  ) : (
                    ([">", "<"] as const).map((o) => (
                      <button key={o} onClick={() => setAlertOp(o)} style={{ padding: "0.25rem 0.6rem", borderRadius: "6px", fontSize: "0.8rem", fontWeight: "bold", cursor: "pointer", width: "36px", background: alertOp === o ? "rgba(96,165,250,0.25)" : "rgba(255,255,255,0.05)", border: `1px solid ${alertOp === o ? "rgba(96,165,250,0.5)" : "rgba(255,255,255,0.15)"}`, color: alertOp === o ? "#60a5fa" : "#cfe5fa" }}>{o}</button>
                    ))
                  )}
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "1rem", alignItems: "end", marginTop: "0.3rem" }}>
                  {alertField === "SAR_Above_Price" ? (
                    <label style={{ display: "flex", flexDirection: "column", gap: "0.3rem", flex: 1 }}>
                      Posizione Parabolic SAR
                      <select value={alertValue} onChange={(e) => setAlertValue(e.target.value)}>
                        <option value="0">SAR &lt; Prezzo (rialzista)</option>
                        <option value="1">SAR &gt; Prezzo (ribassista)</option>
                      </select>
                    </label>
                  ) : alertField === "Signal6" ? (
                    <label style={{ display: "flex", flexDirection: "column", gap: "0.3rem", fontSize: "0.82rem", color: "#cfe5fa" }}>
                      Stato Alligator
                      <select value={alertValue} onChange={(e) => setAlertValue(e.target.value)} style={{ padding: "0.4rem 0.6rem", borderRadius: "8px", backgroundColor: "rgba(12,28,48,0.8)", border: "1px solid rgba(184,216,246,0.2)", color: "#fff", fontSize: "0.85rem", outline: "none", width: "100%", minWidth: "160px" }}>
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
                    <label style={{ display: "flex", flexDirection: "column", gap: "0.3rem", fontSize: "0.82rem", color: "#cfe5fa" }}>
                      Valore {alertField}
                      <input type="text" value={alertValue} onChange={(e) => setAlertValue(e.target.value)} style={{ padding: "0.4rem 0.6rem", borderRadius: "8px", backgroundColor: "rgba(12,28,48,0.8)", border: "1px solid rgba(184,216,246,0.2)", color: "#fff", fontSize: "0.85rem", outline: "none" }} />
                    </label>
                  )}
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <button onClick={createQuickAlert} disabled={alertBusy} style={{ padding: "0.45rem 1rem", borderRadius: "8px", background: "linear-gradient(135deg,#3b82f6,#1d4ed8)", border: "1px solid rgba(59,130,246,0.4)", color: "#fff", fontSize: "0.82rem", fontWeight: "bold", cursor: "pointer" }}>
                      {alertBusy ? "Salvo..." : alertSet ? "Aggiorna" : "Crea Alert"}
                    </button>
                    {alertSet && (
                      <button onClick={removeQuickAlert} disabled={alertBusy} style={{ padding: "0.45rem 1rem", borderRadius: "8px", background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.4)", color: "#fca5a5", fontSize: "0.82rem", fontWeight: "bold", cursor: "pointer" }}>
                        Rimuovi
                      </button>
                    )}
                  </div>
                </div>
                {alertMsg && <p style={{ margin: "0.3rem 0 0 0", fontSize: "0.8rem", color: alertMsg.toLowerCase().includes("errore") || alertMsg.includes("non valid") ? "#fca5a5" : "#4ade80", fontWeight: "bold" }}>{alertMsg}</p>}
              </div>
            </div>
          ) : null}
        </section>
        </div>
      )}

      {/* ══════════════ BACKTEST ══════════════ */}
      {isBacktesting && (
        <div style={{ textAlign: "center", padding: "2rem", background: "rgba(7,17,32,0.6)", borderRadius: "16px", border: "1px solid rgba(190,220,248,0.1)" }}>
          <span style={{ fontSize: "1.2rem", display: "block" }}>⏳ Elaborazione backtest vectorbt...</span>
          <span style={{ fontSize: "0.85rem", color: "#8cb4d9", marginTop: "0.5rem", display: "block" }}>Download &amp; calcolo dinamico a 2 anni su {selectedTicker}</span>
        </div>
      )}

      {backtestError && (
        <div style={{ padding: "1rem", borderRadius: "12px", border: "1px solid rgba(239,68,68,0.2)", backgroundColor: "rgba(239,68,68,0.06)", color: "#fca5a5", fontSize: "0.88rem" }}>{backtestError}</div>
      )}

      {backtestResults && selectedTicker && (
        <section className="card" style={{ display: "grid", gap: "1rem" }}>
          <div style={{ borderBottom: "1px solid rgba(184,216,246,0.15)", paddingBottom: "0.6rem" }}>
            <h3 style={{ margin: 0, fontSize: "1.1rem", color: "#ffffff" }}>
              🏆 Backtest Quantitativo · <span style={{ color: "#60a5fa" }}>{selectedTicker}</span>
            </h3>
            <p style={{ margin: "0.2rem 0 0 0", fontSize: "0.78rem", color: "#8cb4d9" }}>
              BUY: <code>{backtestResults.buy_rule}</code> &nbsp;|&nbsp; SELL: <code>{backtestResults.sell_rule}</code>
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem" }}>
            {[
              { label: "RENDIMENTO NETTO", val: `${backtestResults.metrics["Total Return (%)"].toFixed(2)}%`, color: backtestResults.metrics["Total Return (%)"] >= 0 ? "#4ade80" : "#f87171" },
              { label: "BENCHMARK (B&H)", val: `${backtestResults.metrics["Benchmark Return (%)"].toFixed(2)}%`, color: "#e6eef8" },
              { label: "SHARPE RATIO", val: backtestResults.metrics["Sharpe Ratio"].toFixed(2), color: backtestResults.metrics["Sharpe Ratio"] >= 1 ? "#60a5fa" : backtestResults.metrics["Sharpe Ratio"] >= 0.5 ? "#fbbf24" : "#f87171" },
              { label: "MAX DRAWDOWN", val: `${backtestResults.metrics["Max Drawdown (%)"].toFixed(2)}%`, color: "#f87171" },
              { label: "TRADE ESEGUITI", val: String(backtestResults.metrics["Total Trades"]), color: "#e6eef8" },
              { label: "WIN RATE", val: `${backtestResults.metrics["Win Rate (%)"].toFixed(2)}%`, color: backtestResults.metrics["Win Rate (%)"] >= 50 ? "#4ade80" : "#fbbf24" },
              { label: "PROFIT FACTOR", val: backtestResults.metrics["Profit Factor"].toFixed(2), color: backtestResults.metrics["Profit Factor"] >= 1.2 ? "#4ade80" : "#dbe8f6" },
              { label: "SEGNALE OGGI", val: backtestResults.metrics["Signal Today"], color: backtestResults.metrics["Signal Today"].includes("🟢") ? "#4ade80" : backtestResults.metrics["Signal Today"].includes("🔴") ? "#f87171" : "#cbd5e1" },
            ].map((m, i) => (
              <div key={i} style={{ background: "rgba(8,18,34,0.6)", padding: "0.6rem 0.8rem", borderRadius: "10px", border: "1px solid rgba(184,216,246,0.1)" }}>
                <span style={{ fontSize: "0.72rem", color: "#8cb4d9", display: "block" }}>{m.label}</span>
                <strong style={{ fontSize: "1.1rem", color: m.color }}>{m.val}</strong>
              </div>
            ))}
          </div>

          {/* Grafico */}
          <div style={{ background: "rgba(8,18,34,0.3)", padding: "1rem", borderRadius: "12px", border: "1px solid rgba(184,216,246,0.1)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.8rem", flexWrap: "wrap", gap: "0.5rem" }}>
              <h4 style={{ margin: 0, fontSize: "0.95rem", color: "#fff" }}>📈 Alligator Dashboard (vectorbt)</h4>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
                <div style={{ display: "flex", gap: "2px" }}>
                  {[10, 20, 70, 200].map((d, i, arr) => (
                    <button key={d} className={`btn ghost icon-btn ${bars === d ? "active" : ""}`} onClick={() => setBars(d)} style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem", borderRadius: i === 0 ? "6px 0 0 6px" : i === arr.length - 1 ? "0 6px 6px 0" : "0" }}>{d}g</button>
                  ))}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                  <input type="number" min={10} max={400} step={5} value={localBars} onChange={(e) => { let v = Number(e.target.value); if (v > 400) v = 400; if (v < 10) v = 10; setLocalBars(v); }} style={{ width: "60px", fontSize: "0.75rem", padding: "0.25rem 0.4rem", height: "30px", borderRadius: "8px", border: "1px solid rgba(184,216,246,0.2)", background: "rgba(10,22,38,0.7)", color: "#cfe5fa" }} />
                  <input type="range" min={10} max={400} step={5} value={localBars} onChange={(e) => setLocalBars(Number(e.target.value))} style={{ width: "100px", accentColor: "#3b82f6", cursor: "pointer", height: "30px" }} />
                </div>
                <select value={chartType} onChange={(e) => setChartType(e.target.value as any)} style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem", height: "30px", borderRadius: "8px" }}>
                  <option value="candlestick">Candlestick</option>
                  <option value="line">Line</option>
                </select>
              </div>
            </div>
            <div style={{ textAlign: "center", overflow: "hidden", borderRadius: "10px", border: "1px solid rgba(184,216,246,0.1)", background: "#040a14", minHeight: "400px", display: "grid", placeItems: "center" }}>
              <img
                src={`/api/scanner/backtest/chart?ticker=${encodeURIComponent(selectedTicker)}&pattern=${pattern}&use_sar=${useSar}&use_sma200=${useSma200}&bars=${bars}&chart_type=${chartType}&t=${Date.now()}`}
                alt={`Chart ${selectedTicker}`}
                style={{ width: "100%", height: "auto", display: "block" }}
                loading="lazy"
              />
            </div>
          </div>

          {/* AI Commentary */}
          <div style={{ background: "rgba(12,28,48,0.4)", border: "1px solid rgba(187,219,247,0.15)", padding: "1rem", borderRadius: "12px" }}>
            {renderMarkdown(backtestResults.commentary)}
          </div>
        </section>
      )}

      {/* CSS inline per animazioni */}
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes shimmerBtn {
          0%   { background-position: 0% 50%; }
          50%  { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        @keyframes glowPulse {
          0%, 100% { box-shadow: 0 0 0 3px rgba(99,102,241,0.3), 0 4px 20px rgba(59,130,246,0.4); }
          50%       { box-shadow: 0 0 0 6px rgba(99,102,241,0.55), 0 6px 35px rgba(59,130,246,0.8); }
        }
        @keyframes progressScan {
          0%   { left: -45%; }
          100% { left: 110%; }
        }
        @keyframes radarPulse {
          0%   { transform: scale(1);   opacity: 0.9; }
          100% { transform: scale(2.8); opacity: 0;   }
        }
      `}</style>
    </div>
  );
}

// ─── Utility styles ─────────────────────────────────────────────────────────
const cfgBoxStyle: React.CSSProperties = {
  background: "rgba(8,18,34,0.4)", padding: "0.7rem 0.9rem",
  borderRadius: "10px", border: "1px solid rgba(184,216,246,0.1)",
  display: "flex", flexDirection: "column", gap: "0.5rem",
};

const cfgLabelStyle: React.CSSProperties = {
  fontSize: "0.79rem", fontWeight: 700, color: "#cfe5fa", display: "block",
};

const selectStyle: React.CSSProperties = {
  width: "100%", padding: "0.38rem 0.6rem", borderRadius: "8px",
  backgroundColor: "rgba(12,28,48,0.7)", border: "1px solid rgba(184,216,246,0.25)",
  color: "#ffffff", fontSize: "0.83rem", cursor: "pointer", outline: "none",
  transition: "border-color 0.2s",
};

const checkboxLabelStyle: React.CSSProperties = {
  display: "flex", alignItems: "center", gap: "0.5rem",
  cursor: "pointer", fontSize: "0.83rem", color: "#b8d4ee",
};

// ─── Helper: hex color to "r,g,b" string ────────────────────────────────────
function hexToRgb(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `${r},${g},${b}`;
}
