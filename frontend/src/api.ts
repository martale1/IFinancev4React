import type {
  AlertRule,
  AlertWriteResponse,
  AlertsResponse,
  CustomWatchlistAddItemResponse,
  CustomWatchlistCreateResponse,
  CustomWatchlistRemoveItemResponse,
  CustomWatchlistsResponse,
  AiChatResponse,
  AiProposedCondition,
  AiCriticalLevel,
  RunAlertsResponse,
  WatchlistResponse
} from "./types";

const API_BASE = "/api";

async function parseJson<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`;
    try {
      const data = await resp.json();
      detail = data?.detail ?? data?.error ?? detail;
    } catch {
      // no-op
    }
    throw new Error(detail);
  }
  return resp.json() as Promise<T>;
}

export async function fetchMarkets(): Promise<string[]> {
  const resp = await fetch(`${API_BASE}/markets`);
  const data = await parseJson<{ markets: string[] }>(resp);
  return data.markets;
}

export async function fetchCustomWatchlists(): Promise<CustomWatchlistsResponse> {
  const resp = await fetch(`${API_BASE}/custom-watchlists`);
  return parseJson<CustomWatchlistsResponse>(resp);
}

export async function createCustomWatchlist(name: string): Promise<CustomWatchlistCreateResponse> {
  const resp = await fetch(`${API_BASE}/custom-watchlists`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name })
  });
  return parseJson<CustomWatchlistCreateResponse>(resp);
}

export async function addTickerToCustomWatchlist(input: {
  name: string;
  ticker: string;
  source_market: string;
}): Promise<CustomWatchlistAddItemResponse> {
  const resp = await fetch(`${API_BASE}/custom-watchlists/add-item`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
  return parseJson<CustomWatchlistAddItemResponse>(resp);
}

export async function removeTickerFromCustomWatchlist(input: {
  name: string;
  ticker: string;
  source_market?: string;
}): Promise<CustomWatchlistRemoveItemResponse> {
  const resp = await fetch(`${API_BASE}/custom-watchlists/remove-item`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
  return parseJson<CustomWatchlistRemoveItemResponse>(resp);
}

export async function fetchWatchlist(params: {
  market: string;
  tab: string;
  page: number;
  pageSize: number;
  search: string;
  minVolume: number;
  entrySignal: string;
  marketPhase: string;
  trendPhaseDetail: string;
  rankN: number;
}): Promise<WatchlistResponse> {
  const q = new URLSearchParams({
    market: params.market,
    tab: params.tab,
    page: String(params.page),
    page_size: String(params.pageSize),
    search: params.search,
    min_volume: String(params.minVolume),
    entry_signal: params.entrySignal,
    market_phase: params.marketPhase,
    trend_phase_detail: params.trendPhaseDetail,
    rank_n: String(params.rankN)
  });
  const resp = await fetch(`${API_BASE}/watchlist?${q.toString()}`);
  return parseJson<WatchlistResponse>(resp);
}

export async function fetchAlerts(market: string): Promise<AlertsResponse> {
  const resp = await fetch(`${API_BASE}/alerts/${encodeURIComponent(market)}`);
  return parseJson<AlertsResponse>(resp);
}

export async function runAlerts(input: { market: string; telegram_channel: number; run_only_this_market: boolean }): Promise<RunAlertsResponse> {
  const resp = await fetch(`${API_BASE}/alerts/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
  return parseJson<RunAlertsResponse>(resp);
}

export async function upsertAlertRule(market: string, payload: AlertRule): Promise<AlertWriteResponse> {
  const resp = await fetch(`${API_BASE}/alerts/${encodeURIComponent(market)}/upsert`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ payload })
  });
  return parseJson<AlertWriteResponse>(resp);
}

export async function setAlertRuleEnabled(market: string, ruleId: string, enabled: boolean): Promise<AlertWriteResponse> {
  const resp = await fetch(`${API_BASE}/alerts/${encodeURIComponent(market)}/${encodeURIComponent(ruleId)}/enabled`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled })
  });
  return parseJson<AlertWriteResponse>(resp);
}

export async function deleteAlertRule(market: string, ruleId: string): Promise<AlertWriteResponse> {
  const resp = await fetch(`${API_BASE}/alerts/${encodeURIComponent(market)}/${encodeURIComponent(ruleId)}`, {
    method: "DELETE"
  });
  return parseJson<AlertWriteResponse>(resp);
}

export async function sendAiChat(input: { session_id: string; message: string; model?: string }): Promise<AiChatResponse> {
  const resp = await fetch(`${API_BASE}/ai/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
  return parseJson<AiChatResponse>(resp);
}

export function chartUrl(
  ticker: string,
  bars: number,
  chartType: "candlestick" | "line",
  levels?: { sl1?: number | null; sl2?: number | null; pbStop?: number | null; ppLevel?: number | null },
  latest?: { close?: number | null; pct1d?: number | null; date?: string | null }
): string {
  const q = new URLSearchParams({
    bars: String(bars),
    chart_type: chartType,
    _: String(Date.now())
  });
  if (levels) {
    if (typeof levels.sl1 === "number") q.set("sl1", String(levels.sl1));
    if (typeof levels.sl2 === "number") q.set("sl2", String(levels.sl2));
    if (typeof levels.pbStop === "number") q.set("pb_stop", String(levels.pbStop));
    if (typeof levels.ppLevel === "number") q.set("pp_level", String(levels.ppLevel));
  }
  if (latest) {
    if (typeof latest.close === "number") q.set("latest_close", String(latest.close));
    if (typeof latest.pct1d === "number") q.set("latest_pct_1d", String(latest.pct1d));
    if (latest.date) q.set("latest_date", latest.date);
  }
  return `${API_BASE}/charts/${encodeURIComponent(ticker)}?${q.toString()}`;
}

export async function createAiAlert(market: string, input: { ticker: string; conditions: AiProposedCondition[]; title?: string }): Promise<{ status: string; rule: AlertRule }> {
  const resp = await fetch(`${API_BASE}/alerts/${encodeURIComponent(market)}/ai`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
  return parseJson<{ status: string; rule: AlertRule }>(resp);
}

export async function createAiLevelAlert(market: string, input: { ticker: string; level: AiCriticalLevel }): Promise<{ status: string; rule: AlertRule }> {
  const resp = await fetch(`${API_BASE}/alerts/${encodeURIComponent(market)}/ai-level`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input)
  });
  return parseJson<{ status: string; rule: AlertRule }>(resp);
}

export async function analyzeChartImage(input: {
  ticker: string;
  market: string;
  bars: number;
  chart_type: string;
  levels: Record<string, number | null | undefined> | null;
  model?: string;
  analysis_type?: string;
}): Promise<{ ticker: string; analysis: string }> {
  const resp = await fetch(`${API_BASE}/ai/analyze-chart`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input)
  });
  return parseJson<{ ticker: string; analysis: string }>(resp);
}

