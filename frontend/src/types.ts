export type WatchlistRow = Record<string, unknown> & {
  Ticker?: string;
  Name?: string;
  Date?: string | Date;
  Action?: string;
  Market_Phase?: string;
  Trend_Phase_Detail?: string;
  Entry_Signal?: "ENTRA" | "OSSERVA" | "ATTENDI" | "EVITA";
  Entry_Reason?: string;
  Close?: number;
  PCTV_1D?: number;
  PCTV_5D?: number;
  PCTV_10D?: number;
  PCTV_30D?: number;
  PCTV_180D?: number;
  RSI?: number;
  Stoch_K?: number;
  SIG_MA_SAR?: number;
  MACD?: number;
  MACD_Hist?: number;
  MACD_vs_Signal?: number;
  TECH_SCORE?: number;
  Volume?: number;
  Trend_Stop_Level?: number;
  CE_Long?: number;
  Pullback_Stop_Level?: number;
  Profit_Protect_Level?: number;
  Signal6?: string;
  Signal6_Trend_Days?: number;
  Liquidity?: string;
  Pattern_S2_Days_Ago?: number;
  Pattern_S3_Days_Ago?: number;
  Pattern_S4_Days_Ago?: number;
  Pattern_Combined_Days_Ago?: number;
  Pattern_Type?: string;
  Pattern_Days_Ago?: number;
};

export type WatchlistResponse = {
  market: string;
  tab: string;
  source_file?: string | null;
  source_path?: string | null;
  source_updated_at?: string | null;
  page: number;
  page_size: number;
  total_rows: number;
  total_pages: number;
  items: WatchlistRow[];
};

export type AlertsResponse = {
  market: string;
  rules: AlertRule[];
  defaults: Record<string, unknown>;
  version: number;
  table: Array<Record<string, unknown>>;
};

export type AlertCondition = {
  field: string;
  op: "==" | "!=" | ">" | ">=" | "<" | "<=";
  value: string | number;
};

export type AlertRule = {
  id: string;
  enabled: boolean;
  scope?: {
    tickers?: string[];
    where?: AlertCondition[];
  };
  when?: {
    all?: AlertCondition[];
  };
  cooldown_minutes?: number;
  max_per_day?: number;
  min_gap_minutes?: number;
  message?: {
    title?: string;
    body?: string;
  };
};

export type AlertWriteResponse = {
  status: string;
  rules_count: number;
};

export type RunAlertsResponse = {
  status: string;
  markets: string[];
  results: Record<string, string>;
};

export type CustomWatchlistInfo = {
  name: string;
  size: number;
};

export type CustomWatchlistsResponse = {
  watchlists: CustomWatchlistInfo[];
};

export type CustomWatchlistCreateResponse = {
  status: string;
  name: string;
};

export type CustomWatchlistAddItemResponse = {
  status: string;
  name: string;
  ticker: string;
  source_market: string;
};

export type CustomWatchlistRemoveItemResponse = {
  status: string;
  name: string;
  ticker: string;
  source_market?: string | null;
  removed?: number;
};

export type AiChatMessage = {
  role: "user" | "assistant" | string;
  content: string;
};

export type AiChatResponse = {
  session_id: string;
  answer: string;
  mode: string;
  messages: AiChatMessage[];
  tool_results: Array<Record<string, unknown>>;
};

// Tipo condiviso per i campi degli alert rapidi — definito qui per evitare
// duplicati incompatibili tra WatchlistCard, MultiPatternLabPanel, ChartModal
export type QuickAlertField =
  | "Close"
  | "MACD_vs_Signal"
  | "MACD"
  | "MACD_Hist"
  | "RSI"
  | "SIG_MA_SAR"
  | "Williams_R"
  | "Stoch_K"
  | "Stoch_D"
  | "Stoch_KvsD"
  | "ADX"
  | "PLUS_DI"
  | "MINUS_DI"
  | "DI_diff"
  | "Signal6";
