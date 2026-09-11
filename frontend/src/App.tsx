import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AlertsPanel from "./components/AlertsPanel";
import MultiPatternLabPanel from "./components/MultiPatternLabPanel";
import AiChatPanel from "./components/AiChatPanel";
import AiTickerModal from "./components/AiTickerModal";
import ChartModal from "./components/ChartModal";
import RuleGuide from "./components/RuleGuide";
import WatchlistCard from "./components/WatchlistCard";
import WatchlistsPanel from "./components/WatchlistsPanel";
import ListManagerPanel from "./components/ListManagerPanel";
import PatternManagerPanel from "./components/PatternManagerPanel";
import MarketHeatmapPanel from "./components/MarketHeatmapPanel";
import type { AlertRule, WatchlistRow, QuickAlertField } from "./types";

import {
  addTickerToCustomWatchlist,
  deleteAlertRule,
  chartUrl,
  createCustomWatchlist,
  fetchAlerts,
  fetchCustomWatchlists,
  fetchMarkets,
  fetchWatchlist,
  removeTickerFromCustomWatchlist,
  setAlertRuleEnabled,
  upsertAlertRule,
} from "./api";

const tabs = [
  "All",
  "Liste",
  "Analizza",
  "🔥 Heatmap",
  "Alerts",
  "AI chat",
  "🧪 Multi-Pattern Lab",
  "🔧 Gestione Pattern",
  "Opportunità",
  "Da osservare",
  "Attendi",
  "Da evitare",
  "Migliori (1D)",
  "Migliori (5D)",
  "Peggiori (1D)",
  "Peggiori (5D)"
];

const entrySignalOptions = ["ENTRA", "OSSERVA", "ATTENDI", "EVITA"];
const marketPhaseOptions = ["BREAKOUT", "UPTREND", "PULLBACK", "RANGE", "DOWNTREND", "REVERSAL_RISK"];
const trendPhaseDetailOptions = [
  "EARLY_TREND",
  "EXPANSION",
  "MATURE_TREND",
  "OVEREXTENDED",
  "UPTREDING_COOLING",
  "UPTREND_GENERIC",
  "PULLBACK_HEALTHY",
  "PULLBACK_NORMAL",
  "PULLBACK_RISKY",
  "BREAKOUT_FRESH",
  "BREAKOUT_EXTENDED",
  "RANGE",
  "DOWNTREND",
  "REVERSAL_RISK",
];

function normalizeRuleId(v: unknown): string {
  return String(v ?? "")
    .trim()
    .replace(/\s+/g, " ")
    .toUpperCase();
}

function quickAlertRuleId(ticker: string): string {
  const normalizedTicker = String(ticker ?? "")
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return `CARD_ALERT_${normalizedTicker}`;
}

function alertKey(market: string, ticker: string): string {
  return `${String(market).trim().toUpperCase()}::${String(ticker).trim().toUpperCase()}`;
}

function quickAlertFieldLabel(field: QuickAlertField): string {
  if (field === "MACD_vs_Signal") return "S3";
  if (field === "MACD_Hist") return "Hist";
  if (field === "SIG_MA_SAR") return "SARMA";
  if (field === "SAR_Above_Price") return "SAR rispetto al prezzo";
  if (field === "Williams_R") return "willR";
  if (field === "Stoch_KvsD") return "Sk-Sd";
  if (field === "DI_diff") return "DI+-DI-";
  return field;
}


function filterLabel(v: string): string {
  return v.replace(/_/g, " ");
}

function trendDetailForTab(tabName: string): string {
  const t = String(tabName || "").trim().toLowerCase();
  if (t === "early trend") return "EARLY_TREND";
  if (t === "expansion") return "EXPANSION";
  return "";
}

type QuickAlertConfig = {
  field: QuickAlertField;
  op: ">" | "<" | "==" | "!=";
  value: number | string | null;
};

type AiAlertCardInfo = {
  ruleId: string; enabled: boolean; verified: number; total: number; summary: string;
  conditions: Array<{ verified: boolean; field: string; op: string; value: unknown; actual: unknown; description?: string }>;
};
type AiLevelCardInfo = { ruleId: string; enabled: boolean; type: string; price: number; trigger: string; verified: boolean; actual: unknown };

export default function App() {
  const qc = useQueryClient();
  const marketsQuery = useQuery({ queryKey: ["markets"], queryFn: fetchMarkets });
  const customWatchlistsQuery = useQuery({ queryKey: ["custom-watchlists"], queryFn: fetchCustomWatchlists });
  const [market, setMarket] = useState("MIB30");
  const [tab, setTab] = useState("All");
  const [minVolume, setMinVolume] = useState(2000);
  const [entrySignalFilter, setEntrySignalFilter] = useState("");
  const [marketPhaseFilter, setMarketPhaseFilter] = useState("");
  const [trendPhaseDetailFilter, setTrendPhaseDetailFilter] = useState("");
  const [showStateFilters, setShowStateFilters] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [rankN] = useState(15);

  const [chartTicker, setChartTicker] = useState("");
  const [chartRow, setChartRow] = useState<WatchlistRow | null>(null);
  const [isQuickChart, setIsQuickChart] = useState(false);
  const [aiTickerRow, setAiTickerRow] = useState<WatchlistRow | null>(null);
  const [aiTickerMarket, setAiTickerMarket] = useState("");
  const [aiActiveChatMap, setAiActiveChatMap] = useState<Record<string, boolean>>({});
  const [chartLevels, setChartLevels] = useState<{
    sl1: number | null;
    sl2: number | null;
    pbStop: number | null;
    ppLevel: number | null;
  }>({ sl1: null, sl2: null, pbStop: null, ppLevel: null });
  const [chartSnapshot, setChartSnapshot] = useState<{
    date: string | null;
    close: number | null;
  }>({ date: null, close: null });
  const [chartBars, setChartBars] = useState(70);
  const [chartType, setChartType] = useState<"candlestick" | "line">("candlestick");
  const [quickAlertMap, setQuickAlertMap] = useState<Record<string, boolean>>({});
  const [quickAlertConfigMap, setQuickAlertConfigMap] = useState<Record<string, QuickAlertConfig>>({});
  const [aiAlertCardMap, setAiAlertCardMap] = useState<Record<string, AiAlertCardInfo>>({});
  const [aiLevelCardMap, setAiLevelCardMap] = useState<Record<string, AiLevelCardInfo[]>>({});
  const [multiPatternRows, setMultiPatternRows] = useState<WatchlistRow[]>([]);
  const [alertsRefreshNonce, setAlertsRefreshNonce] = useState(0);
  const [quickAlertBusyMap, setQuickAlertBusyMap] = useState<Record<string, boolean>>({});
  const [quickChartInput, setQuickChartInput] = useState("");
  const [globalSearchRow, setGlobalSearchRow] = useState<WatchlistRow | null>(null);
  const [globalSearchMessage, setGlobalSearchMessage] = useState("");
  const [globalSearchBusy, setGlobalSearchBusy] = useState(false);

  const globalTicker = String(globalSearchRow?.Ticker ?? "");
  const globalMarket = String(globalSearchRow?.WL_Source_Market ?? "");
  useEffect(() => {
    if (!globalTicker || !globalMarket) return;
    let cancelled = false;
    const refresh = async () => {
      if (document.hidden) return;
      try {
        const response = await fetch(`/api/watchlist/focus?market=${encodeURIComponent(globalMarket)}&ticker=${encodeURIComponent(globalTicker)}`, { cache: "no-store" });
        if (!response.ok) return;
        const data = await response.json();
        if (!cancelled && data.item) setGlobalSearchRow((current) =>
          current?.Ticker === globalTicker && current?.WL_Source_Market === globalMarket
            ? { ...data.item, WL_Source_Market: data.item.WL_Source_Market ?? globalMarket }
            : current);
      } catch (error) { console.warn("Aggiornamento scheda non riuscito:", error); }
    };
    const timer = window.setInterval(refresh, 60_000);
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [globalTicker, globalMarket]);

  useEffect(() => {
    const refresh = () => setAlertsRefreshNonce((v) => v + 1);
    window.addEventListener("ifinance-alerts-changed", refresh);
    return () => window.removeEventListener("ifinance-alerts-changed", refresh);
  }, []);

  const [sortKey, setSortKey] = useState<string | null>("MACD_vs_Signal");
  const [sortDir, setSortDir] = useState<"asc" | "desc" | null>("asc");

  function handleSort(key: string) {
    if (key === "MACD_vs_Signal" || key === "SIG_MA_SAR") {
      if (sortKey === key) {
        setSortKey(null);
        setSortDir(null);
      } else {
        setSortKey(key);
        setSortDir("asc");
      }
      setPage(1);
      return;
    }
    const preferredDirection: "asc" | "desc" = ["MACD_vs_Signal", "SIG_MA_SAR"].includes(key) ? "asc" : "desc";
    if (sortKey !== key) {
      setSortKey(key);
      setSortDir(preferredDirection);
    } else {
      if (sortDir === preferredDirection) {
        setSortDir(preferredDirection === "asc" ? "desc" : "asc");
      } else {
        setSortKey(null);
        setSortDir(null);
      }
    }
    setPage(1);
  }

  function toNum(v: unknown): number | null {
    if (typeof v === "number" && Number.isFinite(v)) return v;
    if (typeof v === "string") {
      const n = Number(v.replace(",", ".").trim());
      return Number.isFinite(n) ? n : null;
    }
    return null;
  }

  function openChart(row: WatchlistRow) {
    const ticker = String(row.Ticker ?? "");
    if (!ticker) return;
    setIsQuickChart(false);
    setChartTicker(ticker);
    setChartRow(row);
    setChartLevels({
      sl1: toNum(row.Trend_Stop_Level),
      sl2: toNum(row.CE_Long),
      pbStop: toNum(row.Pullback_Stop_Level),
      ppLevel: toNum(row.Profit_Protect_Level)
    });
    const rawDate = row.Date;
    const dateText =
      rawDate instanceof Date
        ? rawDate.toISOString().slice(0, 10)
        : rawDate
          ? String(rawDate).slice(0, 10)
          : null;
    setChartSnapshot({ date: dateText, close: toNum(row.Close) });
  }

  async function findTickerAcrossMarkets(rawTicker: string): Promise<WatchlistRow | null> {
    const t = rawTicker.trim().toUpperCase();
    if (!t) return null;

    // Read the current workbook even when this ticker is already displayed.
    const allMarkets = marketsQuery.data ?? [market];
    const marketsToSearch = [market, ...allMarkets.filter((candidate) => candidate !== market)];
    for (const candidateMarket of marketsToSearch) {
      try {
        const res = await fetch(
          `/api/watchlist/focus?market=${encodeURIComponent(candidateMarket)}&ticker=${encodeURIComponent(t)}`,
          { cache: "no-store" }
        );
        if (!res.ok) continue;
        const focusData = await res.json();
        if (focusData?.item) {
          return { ...focusData.item, WL_Source_Market: focusData.item.WL_Source_Market ?? candidateMarket };
        }
      } catch (err) {
        console.warn(`Ricerca ticker fallita nel mercato ${candidateMarket}:`, err);
      }
    }
    return null;
  }

  async function handleShowGlobalCard(rawTicker: string) {
    const t = rawTicker.trim().toUpperCase();
    if (!t || globalSearchBusy) return;
    setGlobalSearchBusy(true);
    setGlobalSearchMessage("");
    try {
      const found = await findTickerAcrossMarkets(t);
      setGlobalSearchRow(found);
      if (!found) setGlobalSearchMessage(`${t} non è presente nei database dei mercati. Puoi comunque aprire il grafico.`);
    } finally {
      setGlobalSearchBusy(false);
    }
  }

  async function handleOpenQuickChart(rawTicker: string) {
    const t = rawTicker.trim().toUpperCase();
    if (!t || globalSearchBusy) return;
    setGlobalSearchBusy(true);
    setGlobalSearchMessage("");
    try {
      const found = await findTickerAcrossMarkets(t);
      if (found) {
        setGlobalSearchRow(found);
        openChart(found);
        return;
      }

      const dummyRow: WatchlistRow = { Ticker: t, Name: t, Close: 0, Action: "WATCH", Market_Phase: "RANGE", WL_Source_Market: market };
      setChartTicker(t);
      setChartRow(dummyRow);
      setChartLevels({ sl1: null, sl2: null, pbStop: null, ppLevel: null });
      setChartSnapshot({ date: null, close: null });
      setIsQuickChart(true);
    } finally {
      setGlobalSearchBusy(false);
    }
  }

  function openTickerAi(row: WatchlistRow) {
    setAiTickerRow(row);
    setAiTickerMarket(String(row.WL_Source_Market ?? market));
  }

  function setTickerAiActivity(sourceMarket: string, ticker: string, active: boolean) {
    const source = String(sourceMarket ?? "").trim();
    const symbol = String(ticker ?? "").trim();
    if (!source || !symbol) return;
    const key = alertKey(source, symbol);
    setAiActiveChatMap((prev) => ({ ...prev, [key]: active }));
  }

  const quickTrendDetail = trendDetailForTab(tab);
  const effectiveTrendPhaseDetailFilter = quickTrendDetail || trendPhaseDetailFilter;
  const tabForApi = quickTrendDetail ? "All" : tab;
  const activeFilterCount = [entrySignalFilter, marketPhaseFilter, effectiveTrendPhaseDetailFilter].filter(Boolean).length;

  const watchlistQuery = useQuery({
    queryKey: ["watchlist", market, tabForApi, minVolume, entrySignalFilter, marketPhaseFilter, effectiveTrendPhaseDetailFilter, page, pageSize, rankN, sortKey, sortDir],
    queryFn: () => fetchWatchlist({
      market,
      tab: tabForApi,
      search: "",
      minVolume,
      entrySignal: entrySignalFilter,
      marketPhase: marketPhaseFilter,
      trendPhaseDetail: effectiveTrendPhaseDetailFilter,
      page,
      pageSize,
      rankN,
      sortKey,
      sortDir
    }),
    refetchInterval: 60_000,
    enabled: tab !== "Alerts" && tab !== "AI chat" && tab !== "🧪 Multi-Pattern Lab" && tab !== "Analizza" && tab !== "Liste" && tab !== "🔥 Heatmap"
  });

  const heatmapQuery = useQuery({
    queryKey: ["heatmap", market, minVolume, entrySignalFilter, marketPhaseFilter, effectiveTrendPhaseDetailFilter],
    queryFn: () => fetchWatchlist({
      market,
      tab: "All",
      search: "",
      minVolume,
      entrySignal: entrySignalFilter,
      marketPhase: marketPhaseFilter,
      trendPhaseDetail: effectiveTrendPhaseDetailFilter,
      page: 1,
      pageSize: 200,
      rankN: 100,
    }),
    refetchInterval: 60_000,
    enabled: tab === "🔥 Heatmap",
  });

  const addToWatchlistMutation = useMutation({
    mutationFn: async (input: { name: string; ticker: string; source_market: string }) => {
      await createCustomWatchlist(input.name);
      return addTickerToCustomWatchlist(input);
    },
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["custom-watchlists"] }),
        qc.invalidateQueries({ queryKey: ["markets"] }),
      ]);
    },
  });

  const removeFromWatchlistMutation = useMutation({
    mutationFn: async (input: { name: string; ticker: string; source_market?: string }) => {
      return removeTickerFromCustomWatchlist(input);
    },
    onSuccess: async () => {
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["watchlist"] }),
        qc.invalidateQueries({ queryKey: ["custom-watchlists"] }),
      ]);
    },
  });

  const chartImage = useMemo(() => {
    if (!chartTicker) return "";
    return chartUrl(chartTicker, chartBars, chartType, chartLevels, {
      close: toNum(chartRow?.Close) ?? chartSnapshot.close,
      pct1d: toNum(chartRow?.PCTV_1D),
      date: chartSnapshot.date,
    });
  }, [chartTicker, chartBars, chartType, chartLevels, chartRow, chartSnapshot]);

  function fmtSourceTs(v?: string | null): string {
    if (!v) return "-";
    const d = new Date(v);
    if (Number.isNaN(d.getTime())) return v;
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    const ss = String(d.getSeconds()).padStart(2, "0");
    return `${y}-${m}-${day} ${hh}:${mm}:${ss}`;
  }

  const customWatchlistNames = useMemo(
    () => (customWatchlistsQuery.data?.watchlists ?? []).map((x) => x.name),
    [customWatchlistsQuery.data]
  );

  useEffect(() => {
    const activeItems = tab === "🧪 Multi-Pattern Lab" ? multiPatternRows : (watchlistQuery.data?.items ?? []);
    if (!activeItems.length || tab === "Alerts") {
      setQuickAlertMap({});
      setQuickAlertConfigMap({});
      setAiAlertCardMap({});
      setAiLevelCardMap({});
      return;
    }

    let cancelled = false;
    const items = activeItems;
    const rows = items
      .map((row) => {
        const source = String(row.WL_Source_Market ?? market).trim();
        const ticker = String(row.Ticker ?? "").trim();
        return { source, ticker };
      })
      .filter((x) => x.source && x.ticker);

    const uniqueMarkets = [...new Set(rows.map((x) => x.source))];

    (async () => {
      const byMarket = new Map<string, Awaited<ReturnType<typeof fetchAlerts>>>();
      await Promise.all(
        uniqueMarkets.map(async (mkt) => {
          try {
            const data = await fetchAlerts(mkt);
            byMarket.set(mkt, data);
          } catch {
            byMarket.set(mkt, { market: mkt, rules: [], defaults: {}, version: 1, table: [] });
          }
        })
      );

      const next: Record<string, boolean> = {};
      const nextCfg: Record<string, QuickAlertConfig> = {};
      const nextAi: Record<string, AiAlertCardInfo> = {};
      const nextLevels: Record<string, AiLevelCardInfo[]> = {};
      for (const x of rows) {
        const rid = normalizeRuleId(quickAlertRuleId(x.ticker));
        const alertData = byMarket.get(x.source);
        const rules = alertData?.rules ?? [];
        const foundEnabled = rules.find((r) => normalizeRuleId(r.id) === rid && Boolean(r.enabled));
        const foundAny = rules.find((r) => normalizeRuleId(r.id) === rid);
        const found = foundEnabled ?? foundAny;
        const exists = Boolean(foundEnabled);
        const k = alertKey(x.source, x.ticker);
        next[k] = exists;

        const cond = found?.when?.all?.[0];
        const fieldRaw = String(cond?.field ?? "").trim();
        const opRaw = String(cond?.op ?? "").trim();
        const valRaw = cond?.value;
        const field: QuickAlertConfig["field"] =
          fieldRaw === "MACD_vs_Signal" ? "MACD_vs_Signal"
          : fieldRaw === "MACD" ? "MACD"
          : fieldRaw === "MACD_Hist" ? "MACD_Hist"
          : fieldRaw === "RSI" ? "RSI"
          : fieldRaw === "SIG_MA_SAR" ? "SIG_MA_SAR"
          : fieldRaw === "Williams_R" ? "Williams_R"
          : fieldRaw === "Signal6" ? "Signal6"
          : fieldRaw === "Stoch_K" ? "Stoch_K"
          : fieldRaw === "Stoch_D" ? "Stoch_D"
          : fieldRaw === "Stoch_KvsD" ? "Stoch_KvsD"
          : fieldRaw === "ADX" ? "ADX"
          : fieldRaw === "PLUS_DI" ? "PLUS_DI"
          : fieldRaw === "MINUS_DI" ? "MINUS_DI"
          : fieldRaw === "DI_diff" ? "DI_diff"
          : "Close";
        const op: QuickAlertConfig["op"] =
          opRaw === "<" ? "<"
          : opRaw === "==" ? "=="
          : opRaw === "!=" ? "!="
          : ">";
        const value = fieldRaw === "Signal6" ? String(valRaw ?? "").trim() : toNum(valRaw);

        nextCfg[k] = { field, op, value };

        const aiRule = rules.find((r) => r.source === "ai" && (r.scope?.tickers ?? []).some((t) => String(t).trim().toUpperCase() === x.ticker.toUpperCase()));
        if (aiRule) {
          const aiRow = (alertData?.table ?? []).find((r) => String(r.RuleID) === aiRule.id && String(r.Ticker).trim().toUpperCase() === x.ticker.toUpperCase());
          let statuses: Array<{ verified?: boolean; field?: string; op?: string; value?: unknown; actual?: unknown }> = [];
          try { statuses = JSON.parse(String(aiRow?.Condition_Status ?? "[]")); } catch { statuses = []; }
          const configuredConditions = aiRule.when?.all ?? [];
          const conditions = configuredConditions.map((condition, index) => {
            const status = statuses[index] ?? statuses.find((item) => item.field === condition.field && item.op === condition.op && String(item.value) === String(condition.value));
            const aiCondition = aiRule.ai_conditions?.[index];
            return {
              verified: Boolean(status?.verified), field: condition.field, op: condition.op, value: condition.value,
              actual: status?.actual, description: aiCondition?.description,
            };
          });
          const verified = conditions.filter((condition) => condition.verified).length;
          nextAi[k] = {
            ruleId: aiRule.id, enabled: Boolean(aiRule.enabled), verified, total: conditions.length,
            summary: conditions.map((condition) => `${condition.verified ? "✓" : "○"} ${condition.field} ${condition.op} ${String(condition.value)}`).join("\n"),
            conditions,
          };
        }
        const levelRules = rules.filter((r) => r.source === "ai_level" && (r.scope?.tickers ?? []).some((t) => String(t).trim().toUpperCase() === x.ticker.toUpperCase()));
        nextLevels[k] = levelRules.map((rule) => {
          const tableRow = (alertData?.table ?? []).find((r) => String(r.RuleID) === rule.id && String(r.Ticker).trim().toUpperCase() === x.ticker.toUpperCase());
          let status: any = {};
          try { status = JSON.parse(String(tableRow?.Condition_Status ?? "[]"))[0] ?? {}; } catch { status = {}; }
          const meta = (rule as any).ai_level ?? {};
          return { ruleId: rule.id, enabled: Boolean(rule.enabled), type: String(meta.type ?? "level"), price: Number(meta.price ?? status.value ?? 0), trigger: String(meta.trigger ?? status.op ?? ""), verified: Boolean(status.verified), actual: status.actual };
        });
      }

      if (!cancelled) {
        setQuickAlertMap(next);
        setQuickAlertConfigMap(nextCfg);
        setAiAlertCardMap(nextAi);
        setAiLevelCardMap(nextLevels);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [watchlistQuery.data?.items, multiPatternRows, market, tab, alertsRefreshNonce]);

  async function handleAddToWatchlist(input: { name: string; ticker: string; source_market: string }): Promise<string> {
    const out = await addToWatchlistMutation.mutateAsync(input);
    if (out.status === "exists") return `${input.ticker} già presente in ${input.name}`;
    return `${input.ticker} aggiunto a ${input.name}`;
  }

  function parseCurrentWatchlistName(m: string): string | null {
    const s = String(m || "").trim();
    if (!s.toUpperCase().startsWith("WL:")) return null;
    return s.slice(3).trim() || null;
  }

  async function handleRemoveFromWatchlist(input: { name: string; ticker: string; source_market?: string }): Promise<string> {
    const out = await removeFromWatchlistMutation.mutateAsync(input);
    if (out.status === "not_found") return `${input.ticker} non presente in ${input.name}`;
    return `${input.ticker} rimosso da ${input.name}`;
  }

  function setAlertBusy(sourceMarket: string, ticker: string, value: boolean) {
    const k = alertKey(sourceMarket, ticker);
    setQuickAlertBusyMap((prev) => ({ ...prev, [k]: value }));
  }

  async function handleRemoveQuickAlert(input: { row: WatchlistRow; source_market: string }): Promise<string> {
    const sourceMarket = String(input.source_market ?? "").trim();
    const ticker = String(input.row.Ticker ?? "").trim();
    if (!sourceMarket || !ticker) return "Ticker o mercato non validi.";
    if (sourceMarket.toUpperCase().startsWith("WL:")) {
      return "Per gli alert usa il mercato sorgente (MIB30/ETF/ETC/Preferite).";
    }

    const key = alertKey(sourceMarket, ticker);
    const rid = quickAlertRuleId(ticker);

    setAlertBusy(sourceMarket, ticker, true);
    try {
      await deleteAlertRule(sourceMarket, rid);
      setQuickAlertMap((prev) => ({ ...prev, [key]: false }));
      setQuickAlertConfigMap((prev) => ({ ...prev, [key]: { field: "Close", op: ">", value: null } }));
      await qc.invalidateQueries({ queryKey: ["alerts", sourceMarket] });
      return `Alert rimosso per ${ticker} (${sourceMarket}).`;
    } finally {
      setAlertBusy(sourceMarket, ticker, false);
    }
  }

  async function handleToggleAiAlert(sourceMarket: string, ruleId: string, enabled: boolean): Promise<void> {
    await setAlertRuleEnabled(sourceMarket, ruleId, enabled);
    await qc.invalidateQueries({ queryKey: ["alerts", sourceMarket] });
    window.dispatchEvent(new Event("ifinance-alerts-changed"));
  }

  async function handleDeleteAiAlert(sourceMarket: string, ruleId: string): Promise<void> {
    await deleteAlertRule(sourceMarket, ruleId);
    await qc.invalidateQueries({ queryKey: ["alerts", sourceMarket] });
    window.dispatchEvent(new Event("ifinance-alerts-changed"));
  }

  async function handleCreateQuickAlert(input: {
    row: WatchlistRow;
    source_market: string;
    field: QuickAlertField;
    op: ">" | "<" | "==" | "!=";
    value: number | string;
  }): Promise<string> {
    const sourceMarket = String(input.source_market ?? "").trim();
    const ticker = String(input.row.Ticker ?? "").trim();
    if (!sourceMarket || !ticker) return "Ticker o mercato non validi.";
    if (sourceMarket.toUpperCase().startsWith("WL:")) {
      return "Per gli alert usa il mercato sorgente (MIB30/ETF/ETC/Preferite).";
    }

    const key = alertKey(sourceMarket, ticker);
    const rid = quickAlertRuleId(ticker);

    setAlertBusy(sourceMarket, ticker, true);
    try {
      let finalValue = input.value;
      if (typeof finalValue === "number") {
        if (input.field === "Williams_R" && finalValue > 0) {
          finalValue = -finalValue;
        }
      }

      const payload: AlertRule = {
        id: rid,
        enabled: true,
        scope: { tickers: [ticker] },
        when: { all: [{ field: input.field, op: input.op, value: finalValue }] },
        cooldown_minutes: 0,
        max_per_day: 3,
        min_gap_minutes: 0,
        message: {
          title: "🔔 Alert {{Ticker}}",
          body: "Close: {{Close}}\nRSI: {{RSI}}\nwillR: {{Williams_R}}\nSARMA: {{SIG_MA_SAR}}\nMACD: {{MACD}}\nS3: {{MACD_vs_Signal}}\nAction: {{Action}}\nTECH: {{TECH_SCORE}}\nAlligator: {{Signal6}}"
        }
      };

      await upsertAlertRule(sourceMarket, payload);
      setQuickAlertMap((prev) => ({ ...prev, [key]: true }));
      setQuickAlertConfigMap((prev) => ({
        ...prev,
        [key]: { field: input.field, op: input.op, value: finalValue },
      }));
      await qc.invalidateQueries({ queryKey: ["alerts", sourceMarket] });
      const label = quickAlertFieldLabel(input.field);
      return `Alert creato per ${ticker} (${sourceMarket}) su ${label} ${input.op} ${finalValue}.`;
    } finally {
      setAlertBusy(sourceMarket, ticker, false);
    }
  }

  const sortedWatchlistItems = useMemo(() => {
    if (!watchlistQuery.data?.items) return [];
    const items = [...watchlistQuery.data.items];
    if (!sortKey || !sortDir) return items;
    return items.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];

      // Handle null/undefined values
      if ((av === undefined || av === null) && (bv === undefined || bv === null)) return 0;
      if (av === undefined || av === null) return 1;
      if (bv === undefined || bv === null) return -1;

      if (sortKey === "MACD_vs_Signal" || sortKey === "SIG_MA_SAR") {
        const sortableNumber = (value: unknown): number | null => {
          if (typeof value === "number") return Number.isFinite(value) ? value : null;
          const text = String(value).trim().replace(",", ".");
          const direct = Number(text);
          if (Number.isFinite(direct)) return direct;
          const match = text.match(/[+-]?\d+(?:\.\d+)?/);
          if (!match) return null;
          const parsed = Number(match[0]);
          if (!Number.isFinite(parsed)) return null;
          if (parsed === 0 && text.startsWith("<")) return -Number.EPSILON;
          if (parsed === 0 && text.startsWith(">")) return Number.EPSILON;
          return parsed;
        };
        const aNumber = sortableNumber(av);
        const bNumber = sortableNumber(bv);
        const aMissing = aNumber === null;
        const bMissing = bNumber === null;
        if (aMissing && bMissing) return 0;
        if (aMissing) return 1;
        if (bMissing) return -1;

        // SARMA: prima i positivi crescenti (1, 2, 3...), poi i negativi;
        // lo zero, non significativo, resta sempre in fondo.
        // S3 mantiene invece zero e positivi prima dei negativi.
        const group = (value: number) => {
          if (sortKey === "SIG_MA_SAR") {
            if (value > 0) return 0;
            if (value < 0) return 1;
            return 2;
          }
          return value >= 0 ? 0 : 1;
        };
        const aGroup = group(aNumber);
        const bGroup = group(bNumber);
        return aGroup !== bGroup ? aGroup - bGroup : aNumber - bNumber;
      }

      // Handle string vs number
      if (typeof av === "string" && typeof bv === "string") {
        return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      return sortDir === "asc" ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
  }, [watchlistQuery.data?.items, sortKey, sortDir]);

  return (
    <main className="app">
      <header className="hero app-header">
        <h1>IFinancev4 AI</h1>
        <div className="global-search-control" role="search" aria-label="Ricerca globale titoli">
          <label>
            Cerca titolo · tutti i mercati
            <input
              value={quickChartInput}
              onChange={(e) => setQuickChartInput(e.target.value)}
              placeholder="Ticker o nome, es. FCT o Fincantieri"
              onKeyDown={(e) => {
                if (e.key === "Enter" && quickChartInput.trim()) handleShowGlobalCard(quickChartInput);
              }}
            />
          </label>
          <button className="btn ghost" disabled={globalSearchBusy || !quickChartInput.trim()}
            onClick={() => handleShowGlobalCard(quickChartInput)}>
            {globalSearchBusy ? "Cerco…" : "Scheda"}
          </button>
          <button className="btn" disabled={globalSearchBusy || !quickChartInput.trim()}
            onClick={() => handleOpenQuickChart(quickChartInput)}>Grafico</button>
        </div>
      </header>
      {(globalSearchRow || globalSearchMessage) ? (
        <section className="global-search-result">
          <div className="global-search-result-head">
            <div>
              <strong>{globalSearchRow ? `${globalSearchRow.Ticker} · ${globalSearchRow.Name}` : "Risultato ricerca globale"}</strong>
              {globalSearchRow ? <span>Mercato: {String(globalSearchRow.WL_Source_Market ?? market)}</span> : null}
            </div>
            <button className="btn ghost" onClick={() => { setGlobalSearchRow(null); setGlobalSearchMessage(""); }}>Chiudi</button>
          </div>
          {globalSearchMessage ? <p className="muted">{globalSearchMessage}</p> : null}
          {globalSearchRow ? (
            <div className="global-search-card">
              <WatchlistCard
                row={globalSearchRow}
                onChart={openChart}
                onAi={openTickerAi}
                aiActive={Boolean(aiActiveChatMap[alertKey(String(globalSearchRow.WL_Source_Market ?? market), String(globalSearchRow.Ticker ?? ""))])}
                aiAlertInfo={aiAlertCardMap[alertKey(String(globalSearchRow.WL_Source_Market ?? market), String(globalSearchRow.Ticker ?? ""))] ?? null}
                aiLevelAlerts={aiLevelCardMap[alertKey(String(globalSearchRow.WL_Source_Market ?? market), String(globalSearchRow.Ticker ?? ""))] ?? []}
                onToggleAiAlert={handleToggleAiAlert}
                onDeleteAiAlert={handleDeleteAiAlert}
                sourceMarket={String(globalSearchRow.WL_Source_Market ?? market)}
                alertSet={Boolean(quickAlertMap[alertKey(String(globalSearchRow.WL_Source_Market ?? market), String(globalSearchRow.Ticker ?? ""))])}
                alertConfig={quickAlertConfigMap[alertKey(String(globalSearchRow.WL_Source_Market ?? market), String(globalSearchRow.Ticker ?? ""))] ?? null}
                alertBusy={Boolean(quickAlertBusyMap[alertKey(String(globalSearchRow.WL_Source_Market ?? market), String(globalSearchRow.Ticker ?? ""))])}
                onCreateAlert={handleCreateQuickAlert}
                onRemoveAlert={handleRemoveQuickAlert}
                customWatchlists={customWatchlistNames}
                onAddToWatchlist={handleAddToWatchlist}
                currentWatchlistName={parseCurrentWatchlistName(String(globalSearchRow.WL_Source_Market ?? market))}
                onRemoveFromWatchlist={handleRemoveFromWatchlist}
              />
            </div>
          ) : null}
        </section>
      ) : null}
      <nav className="market-navigation" aria-label="Selezione mercato e liste">
        <button className="btn ghost" onClick={() => setTab("Liste")}>Gestisci liste</button>
        {[{ label: "Mercati", personal: false }, { label: "Le mie liste", personal: true }].map((group) => {
          const options = (marketsQuery.data ?? ["MIB30"]).filter((m) =>
            (m === "Preferite" || Boolean(parseCurrentWatchlistName(m))) === group.personal);
          if (!options.length) return null;
          return (
            <div className="market-navigation-row" key={group.label}>
              <span className="market-group-label">{group.label}</span>
              <div className="market-options" role="group" aria-label={group.label}>
                {options.map((m) => (
                  <button key={m} className={`market-option${market === m ? " selected" : ""}`}
                    aria-pressed={market === m}
                    onClick={() => { setMarket(m); setPage(1); }}>
                    {parseCurrentWatchlistName(m) ?? m.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </nav>
      <div className="filter-toggle-row market-list-toolbar">
        <strong className="current-market">{parseCurrentWatchlistName(market) ?? market.replace(/_/g, " ")}</strong>
        <label className="volume-filter">
          Volume minimo
          <input type="number" min="0" value={minVolume}
            onChange={(e) => { setMinVolume(Math.max(0, Number(e.target.value) || 0)); setPage(1); }} />
        </label>
        <button
          className={showStateFilters || activeFilterCount ? "btn filter-toggle active" : "btn ghost filter-toggle"}
          onClick={() => setShowStateFilters((v) => !v)}
        >
          {showStateFilters ? "Nascondi filtri" : activeFilterCount ? `Filtri (${activeFilterCount})` : "Filtri"}
        </button>
      </div>

      {showStateFilters ? (
        <section className="state-filters" aria-label="Filtri stato card">
          <label>
            Segnale ingresso
            <select
              value={entrySignalFilter}
              onChange={(e) => {
                setEntrySignalFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Tutte</option>
              {entrySignalOptions.map((v) => (
                <option key={v} value={v}>{filterLabel(v)}</option>
              ))}
            </select>
          </label>
          <label>
            Market phase
            <select
              value={marketPhaseFilter}
              onChange={(e) => {
                setMarketPhaseFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Tutte</option>
              {marketPhaseOptions.map((v) => (
                <option key={v} value={v}>{filterLabel(v)}</option>
              ))}
            </select>
          </label>
          <label>
            Trend detail
            <select
              value={effectiveTrendPhaseDetailFilter}
              onChange={(e) => {
                setTrendPhaseDetailFilter(e.target.value);
                if (quickTrendDetail) setTab("All");
                setPage(1);
              }}
            >
              <option value="">Tutti</option>
              {trendPhaseDetailOptions.map((v) => (
                <option key={v} value={v}>{filterLabel(v)}</option>
              ))}
            </select>
          </label>
          <button
            className="btn ghost"
            disabled={!entrySignalFilter && !marketPhaseFilter && !effectiveTrendPhaseDetailFilter}
            onClick={() => {
              setEntrySignalFilter("");
              setMarketPhaseFilter("");
              setTrendPhaseDetailFilter("");
              if (quickTrendDetail) setTab("All");
              setPage(1);
            }}
          >
            Reset filtri
          </button>
        </section>
      ) : null}
      <RuleGuide />

      <nav className="tabs" aria-label="Sezioni principali">
        {tabs.map((t) => (
          <button
            key={t}
            className={tab === t ? "tab active" : "tab"}
            onClick={() => {
              setTab(t);
              if (trendDetailForTab(t)) {
                setTrendPhaseDetailFilter("");
              }
              setPage(1);
            }}
          >
            {t}
          </button>
        ))}
      </nav>
      {tab !== "Alerts" && tab !== "AI chat" && tab !== "🧪 Multi-Pattern Lab" && tab !== "Analizza" && tab !== "Liste" && watchlistQuery.data ? (
        <div className="source-meta">
          Last update: {fmtSourceTs(watchlistQuery.data.source_updated_at)} · Source:{" "}
          <span className="source-path">{watchlistQuery.data.source_path ?? watchlistQuery.data.source_file ?? "-"}</span>
        </div>
      ) : null}

      {tab === "Alerts" ? <AlertsPanel market={market} /> : null}
      {tab === "AI chat" ? <AiChatPanel market={market} /> : null}
      {tab === "🧪 Multi-Pattern Lab" ? (
        <MultiPatternLabPanel
          market={market}
          minVolume={minVolume}
          onOpenInteractiveChart={(scanRow) => {
            // Cerca la riga nella watchlist per avere i dati completi (PCTV, SL, ecc.)
            // Se non la trova, usa comunque i dati del scan result (che ha già PCTV_1D, ecc.)
            const foundRow = watchlistQuery.data?.items?.find(
              (r) => String(r.Ticker).toUpperCase() === String(scanRow.Ticker).toUpperCase()
            );
            // Merge: watchlist row ha priorità (più completa), altrimenti usa scanRow
            const mergedRow: WatchlistRow = foundRow
              ? { ...scanRow, ...foundRow }
              : scanRow;
            mergedRow.WL_Source_Market = mergedRow.WL_Source_Market ?? scanRow.Market ?? market;
            setChartTicker(scanRow.Ticker ?? "");
            setChartRow(mergedRow);
            setChartLevels({ sl1: null, sl2: null, pbStop: null, ppLevel: null });
            setChartSnapshot({ date: null, close: scanRow.Close ?? null });
            setIsQuickChart(false);   // mostra sempre la stats bar con le percentuali
          }}
          onChart={openChart}
          onAi={openTickerAi}
          aiActiveChatMap={aiActiveChatMap}
          aiAlertCardMap={aiAlertCardMap}
          aiLevelCardMap={aiLevelCardMap}
          onToggleAiAlert={handleToggleAiAlert}
          onDeleteAiAlert={handleDeleteAiAlert}
          onResultsChange={setMultiPatternRows}
          quickAlertMap={quickAlertMap}
          quickAlertConfigMap={quickAlertConfigMap}
          quickAlertBusyMap={quickAlertBusyMap}
          onCreateAlert={handleCreateQuickAlert}
          onRemoveAlert={handleRemoveQuickAlert}
          customWatchlists={customWatchlistNames}
          onAddToWatchlist={handleAddToWatchlist}
          currentWatchlistName={parseCurrentWatchlistName(market)}
          onRemoveFromWatchlist={handleRemoveFromWatchlist}
        />
      ) : null}
      {tab === "Liste" && <WatchlistsPanel initialMarket={market} markets={marketsQuery.data ?? ["MIB30", "Preferite"]}
        onOpen={(m) => { setMarket(m); setPage(1); setTab("All"); }}
        onDeleted={(m) => { if (market === m) { setMarket("MIB30"); setPage(1); } if (globalSearchRow?.WL_Source_Market === m) setGlobalSearchRow(null); }} />}
      {tab === "Analizza" ? (
        <ListManagerPanel initialMarket={market} markets={marketsQuery.data ?? []} />
      ) : null}
      {tab === "🔧 Gestione Pattern" ? (
        <PatternManagerPanel />
      ) : null}
      {tab === "🔥 Heatmap" ? (
        <MarketHeatmapPanel
          market={market}
          rows={heatmapQuery.data?.items ?? []}
          alertMap={quickAlertMap}
          loading={heatmapQuery.isLoading}
          error={heatmapQuery.isError ? String(heatmapQuery.error) : undefined}
          onChart={openChart}
        />
      ) : null}

      {tab !== "Alerts" && tab !== "AI chat" && tab !== "🧪 Multi-Pattern Lab" && tab !== "Analizza" && tab !== "Liste" && tab !== "🔧 Gestione Pattern" && tab !== "🔥 Heatmap" && watchlistQuery.isLoading ? <p>Carico watchlist...</p> : null}
      {tab !== "Alerts" && tab !== "AI chat" && tab !== "🧪 Multi-Pattern Lab" && tab !== "Analizza" && tab !== "Liste" && tab !== "🔧 Gestione Pattern" && tab !== "🔥 Heatmap" && watchlistQuery.isError ? <p className="err">{String(watchlistQuery.error)}</p> : null}

      {tab !== "Alerts" && tab !== "AI chat" && tab !== "🧪 Multi-Pattern Lab" && tab !== "Analizza" && tab !== "Liste" && tab !== "🔧 Gestione Pattern" && tab !== "🔥 Heatmap" && watchlistQuery.data ? (
        <>
          <div style={{
            display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap",
            background: "rgba(10, 25, 47, 0.35)", border: "1px solid rgba(184, 216, 246, 0.12)",
            borderRadius: "10px", padding: "0.5rem 0.8rem", margin: "0.5rem 0 1rem 0"
          }}>
            <span style={{ fontSize: "0.78rem", fontWeight: "bold", color: "#8cb4d9", marginRight: "0.4rem" }}>
              ⇅ Ordina per:
            </span>
            {[
              { label: "Ticker", key: "Ticker" },
              { label: "Prezzo", key: "Close" },
              { label: "Var. Giorn. (1D)", key: "PCTV_1D" },
              { label: "Var. 5D", key: "PCTV_5D" },
              { label: "TECH SCORE", key: "TECH_SCORE" },
              { label: "S3", key: "MACD_vs_Signal" },
              { label: "SARMA", key: "SIG_MA_SAR" },
              { label: "RSI", key: "RSI" },
              { label: "willR", key: "Williams_R" },
            ].map((opt) => {
              const active = sortKey === opt.key;
              return (
                <button
                  key={opt.key}
                  onClick={() => handleSort(opt.key)}
                  style={{
                    padding: "0.3rem 0.6rem", borderRadius: "6px", fontSize: "0.76rem", fontWeight: 600,
                    cursor: "pointer",
                    background: active ? "rgba(96,165,250,0.18)" : "rgba(255,255,255,0.03)",
                    border: `1px solid ${active ? "rgba(96,165,250,0.4)" : "rgba(255,255,255,0.1)"}`,
                    color: active ? "#60a5fa" : "#cfe5fa",
                    transition: "all 0.15s ease", outline: "none",
                    display: "flex", alignItems: "center", gap: "0.25rem"
                  }}
                >
                  {opt.label}
                  {active && (sortDir === "asc" ? "▲" : "▼")}
                </button>
              );
            })}
            {sortKey && (
              <button
                onClick={() => { setSortKey(null); setSortDir(null); }}
                style={{
                  background: "transparent", border: "none", color: "#f87171",
                  fontSize: "0.75rem", cursor: "pointer", fontWeight: "bold", outline: "none"
                }}
              >
                Reset
              </button>
            )}
          </div>
          <section className="grid">
            {sortedWatchlistItems.map((row, idx) => (
              <WatchlistCard
                key={`${String(row.Ticker)}-${idx}`}
                row={row}
                onChart={openChart}
                onAi={openTickerAi}
                aiActive={Boolean(aiActiveChatMap[alertKey(String(row.WL_Source_Market ?? market), String(row.Ticker ?? ""))])}
                aiAlertInfo={aiAlertCardMap[alertKey(String(row.WL_Source_Market ?? market), String(row.Ticker ?? ""))] ?? null}
                aiLevelAlerts={aiLevelCardMap[alertKey(String(row.WL_Source_Market ?? market), String(row.Ticker ?? ""))] ?? []}
                onToggleAiAlert={handleToggleAiAlert}
                onDeleteAiAlert={handleDeleteAiAlert}
                sourceMarket={String(row.WL_Source_Market ?? market)}
                alertSet={Boolean(quickAlertMap[alertKey(String(row.WL_Source_Market ?? market), String(row.Ticker ?? ""))])}
                alertConfig={quickAlertConfigMap[alertKey(String(row.WL_Source_Market ?? market), String(row.Ticker ?? ""))] ?? null}
                alertBusy={Boolean(quickAlertBusyMap[alertKey(String(row.WL_Source_Market ?? market), String(row.Ticker ?? ""))])}
                onCreateAlert={handleCreateQuickAlert}
                onRemoveAlert={handleRemoveQuickAlert}
                customWatchlists={customWatchlistNames}
                onAddToWatchlist={handleAddToWatchlist}
                currentWatchlistName={parseCurrentWatchlistName(market)}
                onRemoveFromWatchlist={handleRemoveFromWatchlist}
              />
            ))}
          </section>
          <footer className="pager">
            <button className="btn ghost" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
              Prev
            </button>
            <span>
              Pagina {watchlistQuery.data.page} / {watchlistQuery.data.total_pages} · {watchlistQuery.data.total_rows} titoli
            </span>
            <button
              className="btn ghost"
              disabled={page >= watchlistQuery.data.total_pages}
              onClick={() => setPage((p) => Math.min(watchlistQuery.data.total_pages, p + 1))}
            >
              Next
            </button>
          </footer>
        </>
      ) : null}

      <ChartModal
        open={Boolean(chartTicker)}
        ticker={chartTicker}
        snapshotClose={chartSnapshot.close}
        levels={chartLevels}
        bars={chartBars}
        chartType={chartType}
        onBarsChange={setChartBars}
        onTypeChange={setChartType}
        imageUrl={chartImage}
        row={chartRow}
        isQuickChart={isQuickChart}
        sourceMarket={String(chartRow?.WL_Source_Market ?? market)}
        alertSet={Boolean(chartRow && quickAlertMap[alertKey(String(chartRow.WL_Source_Market ?? market), String(chartRow.Ticker ?? ""))])}
        alertConfig={chartRow ? (quickAlertConfigMap[alertKey(String(chartRow.WL_Source_Market ?? market), String(chartRow.Ticker ?? ""))] ?? null) : null}
        alertBusy={Boolean(chartRow && quickAlertBusyMap[alertKey(String(chartRow.WL_Source_Market ?? market), String(chartRow.Ticker ?? ""))])}
        aiLevelAlerts={chartRow ? (aiLevelCardMap[alertKey(String(chartRow.WL_Source_Market ?? market), String(chartRow.Ticker ?? ""))] ?? []) : []}
        aiAlertInfo={chartRow ? (aiAlertCardMap[alertKey(String(chartRow.WL_Source_Market ?? market), String(chartRow.Ticker ?? ""))] ?? null) : null}
        onCreateAlert={handleCreateQuickAlert}
        onRemoveAlert={handleRemoveQuickAlert}
        onClose={() => {
          setChartTicker("");
          setChartRow(null);
          setChartLevels({ sl1: null, sl2: null, pbStop: null, ppLevel: null });
          setChartSnapshot({ date: null, close: null });
          setIsQuickChart(false);
        }}
      />
      <AiTickerModal
        open={Boolean(aiTickerRow)}
        row={aiTickerRow}
        market={aiTickerMarket || market}
        aiLevelAlerts={aiTickerRow ? (aiLevelCardMap[alertKey(aiTickerMarket || market, String(aiTickerRow.Ticker ?? ""))] ?? []) : []}
        aiAlertInfo={aiTickerRow ? (aiAlertCardMap[alertKey(aiTickerMarket || market, String(aiTickerRow.Ticker ?? ""))] ?? null) : null}
        onChatActivity={setTickerAiActivity}
        onClose={() => {
          setAiTickerRow(null);
          setAiTickerMarket("");
        }}
      />
    </main>
  );
}

