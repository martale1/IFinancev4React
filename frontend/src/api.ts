import type {
  AlertRule,
  AlertWriteResponse,
  AlertsResponse,
  CustomWatchlistAddItemResponse,
  CustomWatchlistCreateResponse,
  CustomWatchlistRemoveItemResponse,
  CustomWatchlistsResponse,
  AiChatResponse,
  OpportunitiesResponse,
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

export async function fetchOpportunities(params: {
  market: string;
  mode: string;
  limit?: number;
  window?: number;
  order?: string;
}): Promise<OpportunitiesResponse> {
  const q = new URLSearchParams({
    market: params.market,
    mode: params.mode,
    limit: String(params.limit ?? 20),
    window: String(params.window ?? 10),
    order: params.order ?? "ready",
  });
  const resp = await fetch(`${API_BASE}/opportunities?${q.toString()}`);
  return parseJson<OpportunitiesResponse>(resp);
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
  action: string;
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
    action: params.action,
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
  levels?: { sl1?: number | null; sl2?: number | null; pbStop?: number | null; ppLevel?: number | null; recoveryTrigger?: number | null }
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
    if (typeof levels.recoveryTrigger === "number") q.set("recovery_trigger", String(levels.recoveryTrigger));
  }
  return `${API_BASE}/charts/${encodeURIComponent(ticker)}?${q.toString()}`;
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

