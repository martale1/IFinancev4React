import { useEffect, useState } from "react";
import type { WatchlistRow, QuickAlertField } from "../types";


function quickAlertFieldLabel(field: QuickAlertField): string {
  if (field === "Close") return "prezzo";
  if (field === "MACD_vs_Signal") return "S3 (MACD-Signal)";
  if (field === "MACD_Hist") return "Istogramma MACD";
  if (field === "SIG_MA_SAR") return "SARMA";
  if (field === "SAR_Above_Price") return "Parabolic SAR rispetto al prezzo";
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

type Props = {
  row: WatchlistRow;
  onChart: (row: WatchlistRow) => void;
  onAi: (row: WatchlistRow) => void;
  aiActive: boolean;
  aiAlertInfo?: {
    ruleId: string; enabled: boolean; verified: number; total: number; summary: string;
    conditions: Array<{ verified: boolean; field: string; op: string; value: unknown; actual: unknown }>;
  } | null;
  aiLevelAlerts?: Array<{ ruleId: string; enabled: boolean; type: string; price: number; trigger: string; verified: boolean; actual: unknown }>;
  onToggleAiAlert?: (sourceMarket: string, ruleId: string, enabled: boolean) => Promise<void>;
  onDeleteAiAlert?: (sourceMarket: string, ruleId: string) => Promise<void>;
  sourceMarket: string;
  alertSet: boolean;
  alertConfig: {
    field: QuickAlertField;
    op: ">" | "<" | "==" | "!=";
    value: number | string | null;
  } | null;
  alertBusy: boolean;
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
};

type CheckItem = {
  ok: boolean;
  label: string;
  extra?: string;
};

const RULES = {
  adxMin: 20,
  rsiBuyMin: 45,
  rsiSellMax: 50,
  techBuyMin: 65,
  techSellMax: 35,
  macdBuyMaxDays: 100,
  macdSellValue: -1
};

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

function pct(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "-";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

function pctColor(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "#9fb7cf";
  if (n > 0) return "#22c55e";
  if (n < 0) return "#ef4444";
  return "#f59e0b";
}

function techColor(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "#9fb7cf";
  if (n >= 65) return "#22c55e";
  if (n <= 35) return "#ef4444";
  return "#f59e0b";
}

function s3Color(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "#9fb7cf";
  if (n > 0) return "#22c55e";
  if (n < 0) return "#ef4444";
  return "#f59e0b";
}

function alligatorColor(v: string | undefined): string {
  if (!v) return "#9fb7cf";
  const s = v.toLowerCase();
  if (s.includes("uptrend") || s.includes("wakeup")) return "#22c55e";
  if (s.includes("downtrend")) return "#ef4444";
  if (s.includes("sleep")) return "#9fb7cf";
  return "#f59e0b";
}

function fmtVol(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "-";
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2).replace(".", ",")}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2).replace(".", ",")}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1).replace(".", ",")}K`;
  return `${Math.round(n)}`;
}

function fmtPrice(v: unknown, digits = 3): string {
  const n = toNum(v);
  if (n === null) return "-";
  return n.toLocaleString("it-IT", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });
}

function fmtRisk(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "-";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2).replace(".", ",")}%`;
}

function riskClass(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "risk-na";
  const a = Math.abs(n);
  if (a <= 2) return "risk-low";
  if (a <= 5) return "risk-mid";
  return "risk-high";
}

function toBool(v: unknown): boolean | null {
  if (typeof v === "boolean") return v;
  if (typeof v === "number") return v !== 0;
  if (typeof v === "string") {
    const s = v.trim().toLowerCase();
    if (["true", "1", "yes", "y"].includes(s)) return true;
    if (["false", "0", "no", "n"].includes(s)) return false;
  }
  return null;
}

function entrySignalClass(signal: string): string {
  const value = signal.trim().toUpperCase();
  if (value === "ENTRA") return "action-buy";
  if (value === "OSSERVA") return "action-add";
  if (value === "EVITA") return "action-sell";
  return "action-wait";
}

function deriveEntrySignal(row: WatchlistRow): "ENTRA" | "OSSERVA" | "ATTENDI" | "EVITA" {
  const supplied = String(row.Entry_Signal ?? "").trim().toUpperCase();
  if (["ENTRA", "OSSERVA", "ATTENDI", "EVITA"].includes(supplied)) {
    return supplied as "ENTRA" | "OSSERVA" | "ATTENDI" | "EVITA";
  }

  const action = String(row.Action ?? "").trim().toUpperCase();
  const phase = String(row.Market_Phase ?? "").trim().toUpperCase();
  const detail = String(row.Trend_Phase_Detail ?? "").trim().toUpperCase();
  const liquidity = String(row.Liquidity ?? "").trim().toUpperCase();
  const invalidated = toBool(row.Pullback_Invalidation) === true;
  const risk =
    ["SELL", "EXIT", "AVOID"].includes(action) ||
    ["DOWNTREND", "REVERSAL_RISK"].includes(phase) ||
    ["PULLBACK_RISKY", "REVERSAL_RISK", "DOWNTREND"].includes(detail) ||
    invalidated ||
    liquidity === "AVOID";

  if (risk) return "EVITA";
  if (action === "BUY" && liquidity === "OK") return "ENTRA";
  if (
    liquidity === "OK" &&
    (action === "ADD" || ["EARLY_TREND", "EXPANSION", "BREAKOUT_FRESH", "PULLBACK_HEALTHY", "PULLBACK_NORMAL"].includes(detail))
  ) return "OSSERVA";
  return "ATTENDI";
}

function phaseClass(phase: string): string {
  const p = phase.trim().toUpperCase();
  if (p === "UPTREND" || p === "BREAKOUT") return "phase-bull";
  if (p === "PULLBACK") return "phase-pullback";
  if (p === "DOWNTREND" || p === "REVERSAL_RISK") return "phase-bear";
  if (p === "RANGE") return "phase-range";
  return "phase-default";
}

function detailLabel(detail: string): string {
  return detail
    .trim()
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .toUpperCase();
}

function buyChecklist(row: WatchlistRow): CheckItem[] {
  const adx = toNum(row.ADX);
  const pdi = toNum(row.PLUS_DI);
  const mdi = toNum(row.MINUS_DI);
  const macdVsSig = toNum(row.MACD_vs_Signal);
  const rsi = toNum(row.RSI);
  const close = toNum(row.Close);
  const ema30 = toNum(row.EMA_30);
  const ema50 = toNum(row.EMA_50);
  const tech = toNum(row.TECH_SCORE);
  const sarAbove = toBool(row.SAR_Above_Price);
  const phase = String(row.Market_Phase ?? "").trim().toUpperCase();

  return [
    {
      ok: ["BREAKOUT", "UPTREND", "PULLBACK"].includes(phase),
      label: "Phase in {BREAKOUT, UPTREND, PULLBACK}",
      extra: phase || "-"
    },
    {
      ok: String(row.Liquidity ?? "").trim().toUpperCase() === "OK",
      label: "Liquidity = OK"
    },
    {
      ok: adx !== null && adx >= RULES.adxMin,
      label: `ADX >= ${RULES.adxMin}`,
      extra: `ADX=${num(adx, 1)}`
    },
    {
      ok: String(row.ADX_Trend ?? "").trim() === "Bullish",
      label: "ADX_Trend = Bullish",
      extra: String(row.ADX_Trend ?? "-")
    },
    {
      ok: pdi !== null && mdi !== null && pdi > mdi,
      label: "+DI > -DI",
      extra: `+DI=${num(pdi, 1)} / -DI=${num(mdi, 1)}`
    },
    {
      ok: macdVsSig !== null && macdVsSig > 0 && macdVsSig <= RULES.macdBuyMaxDays,
      label: `0 < MACD_vs_Signal <= ${RULES.macdBuyMaxDays}`,
      extra: `${num(macdVsSig, 0)}`
    },
    {
      ok: String(row.MACDH_Trend ?? "").trim() === "Up",
      label: "MACDH_Trend = Up",
      extra: String(row.MACDH_Trend ?? "-")
    },
    {
      ok: rsi !== null && rsi >= RULES.rsiBuyMin,
      label: `RSI >= ${RULES.rsiBuyMin}`,
      extra: `RSI=${num(rsi, 1)}`
    },
    {
      ok: String(row.RSI_Trend ?? "").trim() === "Up",
      label: "RSI_Trend = Up",
      extra: String(row.RSI_Trend ?? "-")
    },
    {
      ok: close !== null && ema30 !== null && ema50 !== null && close > ema30 && close > ema50,
      label: "Close > EMA_30 & EMA_50",
      extra: `C=${num(close, 3)} / EMA30=${num(ema30, 3)} / EMA50=${num(ema50, 3)}`
    },
    {
      ok: sarAbove === false,
      label: "SAR sotto prezzo (SAR_Above_Price = No)",
      extra: sarAbove === null ? "-" : sarAbove ? "Yes" : "No"
    },
    {
      ok: tech !== null && tech >= RULES.techBuyMin,
      label: `TECH_SCORE >= ${RULES.techBuyMin}`,
      extra: `${num(tech, 0)}`
    }
  ];
}

function sellChecklist(row: WatchlistRow): CheckItem[] {
  const adx = toNum(row.ADX);
  const pdi = toNum(row.PLUS_DI);
  const mdi = toNum(row.MINUS_DI);
  const macdVsSig = toNum(row.MACD_vs_Signal);
  const rsi = toNum(row.RSI);
  const close = toNum(row.Close);
  const ema30 = toNum(row.EMA_30);
  const ema50 = toNum(row.EMA_50);
  const tech = toNum(row.TECH_SCORE);
  const sarAbove = toBool(row.SAR_Above_Price);
  const phase = String(row.Market_Phase ?? "").trim().toUpperCase();

  return [
    {
      ok: ["DOWNTREND", "REVERSAL_RISK"].includes(phase),
      label: "Phase in {DOWNTREND, REVERSAL_RISK}",
      extra: phase || "-"
    },
    {
      ok: String(row.Liquidity ?? "").trim().toUpperCase() === "OK",
      label: "Liquidity = OK"
    },
    {
      ok: adx !== null && adx >= RULES.adxMin,
      label: `ADX >= ${RULES.adxMin}`,
      extra: `ADX=${num(adx, 1)}`
    },
    {
      ok: String(row.ADX_Trend ?? "").trim() === "Bearish",
      label: "ADX_Trend = Bearish",
      extra: String(row.ADX_Trend ?? "-")
    },
    {
      ok: pdi !== null && mdi !== null && mdi > pdi,
      label: "-DI > +DI",
      extra: `-DI=${num(mdi, 1)} / +DI=${num(pdi, 1)}`
    },
    {
      ok: macdVsSig !== null && macdVsSig === RULES.macdSellValue,
      label: `MACD_vs_Signal = ${RULES.macdSellValue}`,
      extra: `${num(macdVsSig, 0)}`
    },
    {
      ok: String(row.MACDH_Trend ?? "").trim() === "Down",
      label: "MACDH_Trend = Down",
      extra: String(row.MACDH_Trend ?? "-")
    },
    {
      ok: rsi !== null && rsi <= RULES.rsiSellMax,
      label: `RSI <= ${RULES.rsiSellMax}`,
      extra: `RSI=${num(rsi, 1)}`
    },
    {
      ok: String(row.RSI_Trend ?? "").trim() === "Down",
      label: "RSI_Trend = Down",
      extra: String(row.RSI_Trend ?? "-")
    },
    {
      ok: close !== null && ema30 !== null && ema50 !== null && close < ema30 && close < ema50,
      label: "Close < EMA_30 & EMA_50",
      extra: `C=${num(close, 3)} / EMA30=${num(ema30, 3)} / EMA50=${num(ema50, 3)}`
    },
    {
      ok: sarAbove === true,
      label: "SAR sopra prezzo (SAR_Above_Price = Yes)",
      extra: sarAbove === null ? "-" : sarAbove ? "Yes" : "No"
    },
    {
      ok: tech !== null && tech <= RULES.techSellMax,
      label: `TECH_SCORE <= ${RULES.techSellMax}`,
      extra: `${num(tech, 0)}`
    }
  ];
}

export default function WatchlistCard({
  row,
  onChart,
  onAi,
  aiActive,
  aiAlertInfo,
  aiLevelAlerts = [],
  onToggleAiAlert,
  onDeleteAiAlert,
  sourceMarket,
  alertSet,
  alertConfig,
  alertBusy,
  onCreateAlert,
  onRemoveAlert,
  customWatchlists,
  onAddToWatchlist,
  currentWatchlistName,
  onRemoveFromWatchlist,
}: Props) {
  const [showDetails, setShowDetails] = useState(false);
  const [detailMode, setDetailMode] = useState<"BUY" | "SELL">("BUY");
  const [showWatchlistTools, setShowWatchlistTools] = useState(false);
  const [showLevels, setShowLevels] = useState(false);
  const [showAlertTools, setShowAlertTools] = useState(false);
  const [alertField, setAlertField] = useState<QuickAlertField>("Close");
  const [alertOp, setAlertOp] = useState<">" | "<" | "==" | "!=">(">");
  const [alertValue, setAlertValue] = useState("");
  const [useNewWatchlist, setUseNewWatchlist] = useState(false);
  const [selectedWatchlist, setSelectedWatchlist] = useState(customWatchlists[0] ?? "");
  const [newWatchlistName, setNewWatchlistName] = useState("");
  const [wlMsg, setWlMsg] = useState("");
  const [wlBusy, setWlBusy] = useState(false);
  const [alertMsg, setAlertMsg] = useState("");
  const [showAiAlertTools, setShowAiAlertTools] = useState(false);
  const [aiAlertBusy, setAiAlertBusy] = useState(false);
  const [aiAlertMsg, setAiAlertMsg] = useState("");
  const ticker = String(row.Ticker ?? "");
  const action = String(row.Action ?? "-");
  const phase = String(row.Market_Phase ?? "-");
  const trendPhaseDetail = String(row.Trend_Phase_Detail ?? "").trim();
  const entrySignal = deriveEntrySignal(row);
  const entryReason = String(row.Entry_Reason ?? "").trim();

  const buyChecks = buyChecklist(row);
  const sellChecks = sellChecklist(row);
  const checks = detailMode === "BUY" ? buyChecks : sellChecks;

  const actionU = action.trim().toUpperCase();
  const phaseU = phase.trim().toUpperCase();
  const trendPhaseDetailU = trendPhaseDetail.toUpperCase();
  const showTrendPhaseDetail =
    Boolean(trendPhaseDetailU) &&
    trendPhaseDetailU !== phaseU &&
    ["BREAKOUT", "PULLBACK", "UPTREND"].includes(phaseU);

  const close = toNum(row.Close);
  const sarma = toNum(row.SIG_MA_SAR);
  const stochK = toNum(row.Stoch_K);
  const stochD = toNum(row.Stoch_D);
  const stochColor = stochK !== null && stochD !== null && stochK > stochD ? "#22c55e" : "#ef4444";
  const adx    = toNum(row.ADX);
  const plusDI  = toNum(row.PLUS_DI);
  const minusDI = toNum(row.MINUS_DI);
  const macdVsSignal = toNum(row.MACD_vs_Signal);
  const willR = toNum(row.Williams_R);
  const willRColor = willR !== null && willR >= -80 ? "#22c55e" : "#ef4444";
  const sl1 = toNum(row.Trend_Stop_Level);
  const sl2 = toNum(row.CE_Long);
  const sar = toNum(row.SAR);
  const sl1Risk = toNum(row.SL1_RiskPct) ?? (close !== null && sl1 !== null ? ((sl1 / close - 1) * 100) : null);
  const sl2Risk = toNum(row.SL2_RiskPct) ?? (close !== null && sl2 !== null ? ((sl2 / close - 1) * 100) : null);
  const ppLevel = toNum(row.Profit_Protect_Level);

  const pbLow = toNum(row.Pullback_Entry_Zone_Low);
  const pbHigh = toNum(row.Pullback_Entry_Zone_High);
  const pbEntry = toNum(row.Pullback_Entry_Level);
  const pbStop = toNum(row.Pullback_Stop_Level);
  const pbNote = String(row.Pullback_Entry_Note ?? "").trim();
  const pbInvalid = toBool(row.Pullback_Invalidation) === true;

  const showTrendStops = ["BUY", "ADD"].includes(actionU) && ["UPTREND", "BREAKOUT"].includes(phaseU) && (sl1 !== null || sl2 !== null);
  const showPullback = phaseU === "PULLBACK" && pbLow !== null && pbHigh !== null && pbEntry !== null && pbStop !== null;
  const showProfitProtect = actionU === "REDUCE" && phaseU === "UPTREND" && ppLevel !== null;
  const hasLevels = showPullback || showTrendStops || showProfitProtect;
  const checkData = close !== null && ((sl1 !== null && sl1 > close) || (sl2 !== null && sl2 > close));
  const showOperationalConfirmation = entrySignal === "OSSERVA" || entrySignal === "ATTENDI";
  const sarAbovePrice = toBool(row.SAR_Above_Price);
  const sarBelowPrice = sarAbovePrice === false || (sarAbovePrice === null && sar !== null && close !== null && sar < close);
  const alligatorBullish = String(row.Signal6 ?? "").trim().toLowerCase().startsWith("uptrend");
  const trendConfirmed = sarBelowPrice && alligatorBullish;
  const momentumConfirmed = macdVsSignal !== null && macdVsSignal > 0 && stochK !== null && stochD !== null && stochK > stochD;
  const strengthConfirmed = adx !== null && adx >= 20 && plusDI !== null && minusDI !== null && plusDI > minusDI;

  useEffect(() => {
    setShowAlertTools(false);
    setAlertField("Close");
    setAlertOp(">");
    setAlertValue(close !== null ? String(close) : "");
    setAlertMsg("");
  }, [ticker]);

  function applyAlertPreset() {
    if (alertConfig) {
      setAlertField(alertConfig.field);
      setAlertOp(alertConfig.op);
      if (alertConfig.value !== null) setAlertValue(String(alertConfig.value));
      return;
    }
    setAlertField("Close");
    setAlertOp(">");
    if (close !== null) setAlertValue(String(close));
  }

  async function addToWatchlist() {
    const targetName = useNewWatchlist ? newWatchlistName.trim() : selectedWatchlist.trim();
    if (!ticker || !targetName) {
      setWlMsg("Seleziona o crea una watchlist.");
      return;
    }
    setWlBusy(true);
    setWlMsg("");
    try {
      const result = await onAddToWatchlist({ name: targetName, ticker, source_market: sourceMarket });
      setWlMsg(result);
      if (useNewWatchlist) {
        setSelectedWatchlist(targetName);
        setUseNewWatchlist(false);
      }
    } catch (e) {
      setWlMsg(String(e));
    } finally {
      setWlBusy(false);
    }
  }

  async function removeFromCurrentWatchlist() {
    if (!ticker || !currentWatchlistName) return;
    setWlBusy(true);
    setWlMsg("");
    try {
      const result = await onRemoveFromWatchlist({ name: currentWatchlistName, ticker, source_market: sourceMarket });
      setWlMsg(result);
    } catch (e) {
      setWlMsg(String(e));
    } finally {
      setWlBusy(false);
    }
  }

  async function removeQuickAlert() {
    if (!ticker) return;
    setAlertMsg("");
    try {
      const result = await onRemoveAlert({ row, source_market: sourceMarket });
      setAlertMsg(result);
      setShowAlertTools(false);
    } catch (e) {
      setAlertMsg(String(e));
    }
  }

  async function createQuickAlert() {
    if (!ticker) return;
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
      const result = await onCreateAlert({ row, source_market: sourceMarket, field: alertField, op: alertOp, value: v });
      setAlertMsg(result);
      setShowAlertTools(false);
    } catch (e) {
      setAlertMsg(String(e));
    }
  }

  return (
    <article className="card">
      <div className="card-head">
        <div>
          <div className="ticker">{ticker}</div>
          <div className="name">{String(row.Name ?? "-")}</div>
        </div>
        <div className="price" style={{ display: "flex", alignItems: "baseline", gap: "0.4rem" }}>
          <span>{num(row.Close, 3)}</span>
          <span style={{ fontSize: "0.85rem", fontWeight: "bold", color: pctColor(row.PCTV_1D) }}>
            {pct(row.PCTV_1D)}
          </span>
        </div>
      </div>
      <div className="row">
        <span>
          1D: <b style={{ color: pctColor(row.PCTV_1D) }}>{pct(row.PCTV_1D)}</b>
        </span>
        <span>
          5D: <b style={{ color: pctColor(row.PCTV_5D) }}>{pct(row.PCTV_5D)}</b>
        </span>
        <span>
          10D: <b style={{ color: pctColor(row.PCTV_10D) }}>{pct(row.PCTV_10D)}</b>
        </span>
        <span>
          30D: <b style={{ color: pctColor(row.PCTV_30D) }}>{pct(row.PCTV_30D)}</b>
        </span>
        <span>
          180D: <b style={{ color: pctColor(row.PCTV_180D) }}>{pct(row.PCTV_180D)}</b>
        </span>
        <span>
          TECH: <b style={{ color: techColor(row.TECH_SCORE) }}>{num(row.TECH_SCORE, 0)}</b>
        </span>
        <span>
          S3: <b style={{ color: s3Color(row.MACD_vs_Signal) }}>{num(row.MACD_vs_Signal, 0)}</b>
        </span>
        <span>
          RSI: <b style={{ color: techColor(row.RSI) }}>{num(row.RSI, 0)}</b>
        </span>
        <span>
          willR: <b style={{ color: willRColor }}>{num(row.Williams_R, 0)}</b>
        </span>
        <span>
          Sk: <b style={{ color: stochColor }}>{num(stochK, 0)}</b>
        </span>
        <span>
          Sd: <b style={{ color: stochColor }}>{num(stochD, 0)}</b>
        </span>
        <span>
          SARMA: <b style={{ color: sarma !== null && sarma > 0 ? "#22c55e" : "#ef4444" }}>{sarma !== null && sarma > 0 ? num(sarma, 0) : "<0"}</b>
        </span>
        <span>
          Alligator: <b style={{ color: alligatorColor(row.Signal6) }}>{String(row.Signal6 ?? "-")} {row.Signal6_Trend_Days !== undefined ? `(${row.Signal6_Trend_Days}d)` : ""}</b>
        </span>
        <span>
          LIQ: <b style={{ color: String(row.Liquidity ?? "").trim().toUpperCase() === "OK" ? "#22c55e" : "#ef4444" }}>{String(row.Liquidity ?? "-")}</b>
        </span>
        {toNum(row.Pattern_S2_Days_Ago) !== null && (
          <span>
            S2: <b style={{ color: toNum(row.Pattern_S2_Days_Ago) === 0 ? "#22c55e" : "#9fb7cf" }}>{num(row.Pattern_S2_Days_Ago, 0)}d</b>
          </span>
        )}
        {toNum(row.Pattern_S3_Days_Ago) !== null && (
          <span>
            S3_Pat: <b style={{ color: toNum(row.Pattern_S3_Days_Ago) === 0 ? "#22c55e" : "#9fb7cf" }}>{num(row.Pattern_S3_Days_Ago, 0)}d</b>
          </span>
        )}
        {toNum(row.Pattern_S4_Days_Ago) !== null && (
          <span>
            S4: <b style={{ color: toNum(row.Pattern_S4_Days_Ago) === 0 ? "#22c55e" : "#9fb7cf" }}>{num(row.Pattern_S4_Days_Ago, 0)}d</b>
          </span>
        )}
        {toNum(row.Pattern_Combined_Days_Ago) !== null && (
          <span>
            Comb: <b style={{ color: toNum(row.Pattern_Combined_Days_Ago) === 0 ? "#22c55e" : "#9fb7cf" }}>{num(row.Pattern_Combined_Days_Ago, 0)}d</b>
          </span>
        )}
      </div>
      <div className="pill-row">
        <span className={`pill ${entrySignalClass(entrySignal)}`} title={entryReason}>
          {entrySignal === "ENTRA" ? "✓ ENTRA" : entrySignal === "OSSERVA" ? "◉ OSSERVA" : entrySignal === "EVITA" ? "✕ EVITA" : "○ ATTENDI"}
        </span>
        {row.Pattern_Type && (
          <span className="pill" style={{ backgroundColor: "rgba(167, 139, 250, 0.2)", color: "#c084fc", border: "1px solid rgba(167, 139, 250, 0.4)", fontWeight: "bold" }}>
            🧪 {String(row.Pattern_Type)} ({row.Pattern_Days_Ago === 0 ? "Oggi" : row.Pattern_Days_Ago === 1 ? "Ieri" : `${row.Pattern_Days_Ago}d fa`})
          </span>
        )}
      </div>
      <div className="row muted">
        Contesto tecnico: <b className={phaseClass(phase)}>{phase}</b>
        {showTrendPhaseDetail ? <> · {detailLabel(trendPhaseDetail)}</> : null}
        {entryReason ? <> · {entryReason}</> : null}
      </div>
      {showOperationalConfirmation ? (
        <details
          style={{
            marginTop: "0.35rem",
            border: "1px solid rgba(96,165,250,0.25)",
            borderRadius: "8px",
            background: "rgba(30,64,175,0.08)",
            fontSize: "0.78rem",
            lineHeight: 1.45,
          }}
        >
          <summary style={{ padding: "0.4rem 0.55rem", color: "#93c5fd", fontWeight: 700, cursor: "pointer" }}>
            Conferma operativa
          </summary>
          <div style={{ padding: "0 0.55rem 0.5rem" }}>
            <div style={{ color: trendConfirmed ? "#4ade80" : "#fbbf24" }}>
              {trendConfirmed ? "✓" : "○"} Trend: SAR &lt; prezzo + Alligator rialzista
            </div>
            <div style={{ color: momentumConfirmed ? "#4ade80" : "#fbbf24" }}>
              {momentumConfirmed ? "✓" : "○"} Momentum: MACD &gt; segnale + Sk &gt; Sd
            </div>
            <div style={{ color: strengthConfirmed ? "#4ade80" : "#fbbf24" }}>
              {strengthConfirmed ? "✓" : "○"} Forza: ADX ≥ 20 + DI+ &gt; DI−
            </div>
            <div className="muted" style={{ marginTop: "0.2rem" }}>
              {trendConfirmed && momentumConfirmed && strengthConfirmed
                ? "Conferme tecniche complete: valutare ingresso, livelli e rischio."
                : "Attendere che le condizioni mancanti diventino verdi."}
            </div>
          </div>
        </details>
      ) : null}
      <div className="row muted">VOL: {fmtVol(row.Volume)}</div>

      {hasLevels && showLevels && showPullback ? (
        <div className={`level-strip ${pbInvalid ? "level-warn" : "level-pullback"}`}>
          <div className="level-title">PULLBACK</div>
          <div className="level-main">
            Zona: <b>{fmtPrice(pbLow, 2)} - {fmtPrice(pbHigh, 2)}</b> · EntryRef: <b>{fmtPrice(pbEntry, 2)}</b> · Stop:{" "}
            <b>{fmtPrice(pbStop, 2)}</b>
          </div>
          <div className="level-sub">{pbNote || "-"}</div>
        </div>
      ) : null}

      {hasLevels && showLevels && showTrendStops ? (
        <div className="level-strip level-stop">
          <div className="level-title">STOP LEVELS</div>
          <div className="level-main">
            {sl1 !== null ? (
              <span className="stop-line sl1">
                SL1: <b>{fmtPrice(sl1, 2)}</b> <span className={`risk-pill ${riskClass(sl1Risk)}`}>{fmtRisk(sl1Risk)}</span>
              </span>
            ) : null}
            {sl2 !== null ? (
              <span className="stop-line sl2">
                {" "}· SL2: <b>{fmtPrice(sl2, 2)}</b> <span className={`risk-pill ${riskClass(sl2Risk)}`}>{fmtRisk(sl2Risk)}</span>
              </span>
            ) : null}
          </div>
          {checkData ? <div className="level-sub warn">CHECK DATA: stop sopra il prezzo</div> : null}
        </div>
      ) : null}

      {hasLevels && showLevels && showProfitProtect ? (
        <div className="level-strip level-protect">
          <div className="level-title">PROFIT PROTECT</div>
          <div className="level-main">
            Livello: <b>{fmtPrice(ppLevel, 2)}</b>
          </div>
        </div>
      ) : null}

      <div className="row actions">
        {aiAlertInfo ? (
          <button
            type="button"
            className={`enabled-badge ${aiAlertInfo.enabled ? "active" : "inactive"}`}
            title={`Alert basato sulle condizioni generate dall'AI\n${aiAlertInfo.summary}`}
            style={{ alignSelf: "center", whiteSpace: "nowrap", cursor: "pointer" }}
            onClick={() => { setShowAiAlertTools((v) => !v); setAiAlertMsg(""); }}
          >
            🤖 Alert AI {aiAlertInfo.verified}/{aiAlertInfo.total}{aiAlertInfo.enabled ? "" : " OFF"}
          </button>
        ) : null}
        {aiLevelAlerts.length ? (
          <button type="button" className="enabled-badge active" style={{ cursor: "pointer", whiteSpace: "nowrap" }} onClick={() => { setShowAiAlertTools((v) => !v); setAiAlertMsg(""); }}>
            📍 Livelli AI {aiLevelAlerts.filter((l) => l.verified).length}/{aiLevelAlerts.length}
          </button>
        ) : null}
        <button className="btn" disabled={!ticker} onClick={() => ticker && onChart(row)}>
          Grafico
        </button>
        <button
          className={aiActive ? "btn ai-card-btn active" : "btn ghost ai-card-btn"}
          disabled={!ticker}
          onClick={() => ticker && onAi(row)}
          title={aiActive ? "Chat AI attiva per questo ticker" : "Apri analisi AI"}
        >
          AI{aiActive ? " attiva" : ""}
        </button>
        <button className="btn ghost" onClick={() => setShowDetails((v) => !v)}>
          {showDetails ? "Nascondi dettagli" : "Dettagli"}
        </button>
        {hasLevels ? (
          <button className="btn ghost" onClick={() => setShowLevels((v) => !v)}>
            {showLevels ? "Nascondi livelli" : "Livelli"}
          </button>
        ) : null}
        <button
          className={alertSet ? "btn alert-on" : "btn ghost"}
          disabled={alertBusy || !ticker}
          onClick={() => {
            applyAlertPreset();
            setShowAlertTools((v) => !v);
            setAlertMsg("");
          }}
          title={alertSet ? "Alert presente: apri per modificare o rimuovere" : "Apri opzioni alert"}
        >
          {alertBusy ? "..." : alertSet ? "Alert ON" : "Alert"}
        </button>
        <button
          className={showWatchlistTools ? "btn active" : "btn ghost"}
          onClick={() => setShowWatchlistTools((v) => !v)}
          title="Aggiungi a preferite/watchlist"
        >
          {showWatchlistTools ? "Chiudi Watchlist" : "＋ Watchlist"}
        </button>
        {currentWatchlistName ? (
          <button className="btn ghost icon-btn remove-btn" disabled={wlBusy} onClick={removeFromCurrentWatchlist} title={`Rimuovi da ${currentWatchlistName}`}>
            -
          </button>
        ) : null}
      </div>
      {showAiAlertTools && (aiAlertInfo || aiLevelAlerts.length) ? (
        <div className="ai-alerts-activated-summary card-ai-alert-summary">
          <div className="active-alerts-heading">
            <div><strong>Alert AI</strong><span>{aiAlertInfo ? "1 regola" : "0 regole"} · {aiLevelAlerts.length} livelli</span></div>
            <span className="active-status-pill">● {aiAlertInfo?.enabled || aiLevelAlerts.some((level) => level.enabled) ? "Monitoraggio attivo" : "Monitoraggio sospeso"}</span>
          </div>
          {aiAlertInfo ? <div className="active-rule-card">
            <div className="active-rule-card-heading">
              <div><strong>🤖 {aiAlertInfo.ruleId}</strong><span>{aiAlertInfo.conditions.length} condizioni collegate in AND</span></div>
              <div className="compact-alert-actions">
                <button className="compact-toggle-btn" disabled={aiAlertBusy || !onToggleAiAlert} onClick={async () => {
                  if (!onToggleAiAlert) return; setAiAlertBusy(true); setAiAlertMsg("");
                  try { await onToggleAiAlert(sourceMarket, aiAlertInfo.ruleId, !aiAlertInfo.enabled); } catch (e) { setAiAlertMsg(String(e)); } finally { setAiAlertBusy(false); }
                }}>{aiAlertInfo.enabled ? "Disabilita" : "Abilita"}</button>
                <button className="compact-remove-btn" disabled={aiAlertBusy || !onDeleteAiAlert} onClick={async () => {
                  if (!onDeleteAiAlert) return; setAiAlertBusy(true); setAiAlertMsg("");
                  try { await onDeleteAiAlert(sourceMarket, aiAlertInfo.ruleId); setShowAiAlertTools(false); } catch (e) { setAiAlertMsg(String(e)); } finally { setAiAlertBusy(false); }
                }}>Rimuovi</button>
              </div>
            </div>
            <div className="active-condition-grid">{aiAlertInfo.conditions.map((condition, index) => <div key={`${condition.field}-${index}`} className={`active-condition-chip ${condition.verified ? "verified" : "pending"}`}>
              <b>{condition.verified ? "✓" : index + 1}</b><span><strong>{condition.field} {condition.op} {String(condition.value)}</strong><small>Valore attuale: {condition.actual == null ? "n/d" : String(condition.actual)}</small></span>
            </div>)}</div>
          </div> : null}
          {aiLevelAlerts.map((level) => <div key={level.ruleId} className="activated-level-control">
            <span className={level.verified ? "level-state verified" : "level-state pending"}>{level.verified ? "✓" : "○"}</span>
            <span><strong>{level.type === "support" ? "Supporto" : "Resistenza"} {level.price}</strong><small>Close {level.trigger} {level.price} · ora {level.actual == null ? "n/d" : String(level.actual)} · {level.enabled ? "Attivo" : "OFF"}</small></span>
            <div className="compact-alert-actions">
              <button className="compact-toggle-btn" disabled={aiAlertBusy || !onToggleAiAlert} onClick={async () => {
                if (!onToggleAiAlert) return; setAiAlertBusy(true); setAiAlertMsg("");
                try { await onToggleAiAlert(sourceMarket, level.ruleId, !level.enabled); } catch (e) { setAiAlertMsg(String(e)); } finally { setAiAlertBusy(false); }
              }}>{level.enabled ? "Disabilita" : "Abilita"}</button>
              <button className="compact-remove-btn" disabled={aiAlertBusy || !onDeleteAiAlert} onClick={async () => {
                if (!onDeleteAiAlert) return; setAiAlertBusy(true); setAiAlertMsg("");
                try { await onDeleteAiAlert(sourceMarket, level.ruleId); } catch (e) { setAiAlertMsg(String(e)); } finally { setAiAlertBusy(false); }
              }}>Rimuovi</button>
            </div>
          </div>)}
          {aiAlertMsg ? <p className="err">{aiAlertMsg}</p> : null}
        </div>
      ) : null}
      {showWatchlistTools ? (
        <div className="watchlist-tools">
          <div className="watchlist-mode">
            <button className={!useNewWatchlist ? "quick-bar active" : "quick-bar"} onClick={() => setUseNewWatchlist(false)}>
              Esistente
            </button>
            <button className={useNewWatchlist ? "quick-bar active" : "quick-bar"} onClick={() => setUseNewWatchlist(true)}>
              Nuova
            </button>
          </div>
          {!useNewWatchlist ? (
            <label>
              Watchlist
              <select value={selectedWatchlist} onChange={(e) => setSelectedWatchlist(e.target.value)}>
                <option value="">Seleziona...</option>
                {customWatchlists.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <label>
              Nome nuova watchlist
              <input value={newWatchlistName} onChange={(e) => setNewWatchlistName(e.target.value)} placeholder="es. Momentum Italia" />
            </label>
          )}
          <button className="btn" disabled={wlBusy || !ticker} onClick={addToWatchlist}>
            {wlBusy ? "Salvo..." : "Salva in watchlist"}
          </button>
          {wlMsg ? <div className="muted">{wlMsg}</div> : null}
        </div>
      ) : null}
      {showAlertTools ? (
        <div className="watchlist-tools">
          <div className="watchlist-mode">
            <button className={alertField === "Close" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("Close");
              if (close !== null) setAlertValue(String(close));
            }}>
              Prezzo
            </button>
            <button className={alertField === "MACD_vs_Signal" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("MACD_vs_Signal");
              const s3 = toNum(row.MACD_vs_Signal);
              if (s3 !== null) setAlertValue(String(s3));
            }}>
              S3
            </button>
            <button className={alertField === "MACD" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("MACD");
              const macd = toNum(row.MACD);
              if (macd !== null) setAlertValue(String(macd));
            }}>
              MACD
            </button>
            <button className={alertField === "RSI" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("RSI");
              const rsi = toNum(row.RSI);
              if (rsi !== null) setAlertValue(String(rsi));
            }}>
              RSI
            </button>
            <button className={alertField === "SIG_MA_SAR" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("SIG_MA_SAR");
              if (sarma !== null) setAlertValue(String(sarma));
            }}>
              SARMA
            </button>
            <button className={alertField === "SAR_Above_Price" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("SAR_Above_Price");
              setAlertOp("==");
              setAlertValue("0");
            }}>
              SAR vs Prezzo
            </button>
            <button className={alertField === "Williams_R" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("Williams_R");
              if (willR !== null) setAlertValue(String(willR));
            }}>
              willR
            </button>
            <button className={alertField === "MACD_Hist" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("MACD_Hist");
              setAlertOp(">");
              setAlertValue("0");
            }}>
              Hist
            </button>
            <button className={alertField === "Stoch_K" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("Stoch_K");
              if (stochK !== null) setAlertValue(String(Math.round(stochK)));
            }}>
              Sk
            </button>
            <button className={alertField === "Stoch_D" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("Stoch_D");
              if (stochD !== null) setAlertValue(String(Math.round(stochD)));
            }}>
              Sd
            </button>
            <button className={alertField === "Stoch_KvsD" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("Stoch_KvsD");
              setAlertOp(">");
              setAlertValue("0");
            }}>
              Sk&gt;Sd
            </button>
            <button className={alertField === "ADX" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("ADX");
              setAlertOp(">");
              if (adx !== null) setAlertValue(String(Math.round(adx)));
            }}>
              ADX
            </button>
            <button className={alertField === "DI_diff" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("DI_diff");
              setAlertOp(">");
              setAlertValue("0");
            }}>
              DI+&gt;DI−
            </button>
            <button className={alertField === "PLUS_DI" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("PLUS_DI");
              if (plusDI !== null) setAlertValue(String(Math.round(plusDI)));
            }}>
              DI+
            </button>
            <button className={alertField === "MINUS_DI" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("MINUS_DI");
              if (minusDI !== null) setAlertValue(String(Math.round(minusDI)));
            }}>
              DI−
            </button>
            <button className={alertField === "Signal6" ? "quick-bar active" : "quick-bar"} onClick={() => {
              setAlertField("Signal6");
              setAlertOp("==");
              setAlertValue("Uptrend*");
            }}>
              Alligator
            </button>
          </div>
          {alertField === "SAR_Above_Price" ? null : alertField === "Signal6" ? (
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
          {alertField === "SAR_Above_Price" ? (
            <label style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
              Posizione Parabolic SAR
              <select value={alertValue} onChange={(e) => setAlertValue(e.target.value)}>
                <option value="0">SAR &lt; Prezzo (segnale rialzista)</option>
                <option value="1">SAR &gt; Prezzo (segnale ribassista)</option>
              </select>
            </label>
          ) : alertField === "Signal6" ? (
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
            <button className="btn" disabled={alertBusy || !ticker} onClick={createQuickAlert}>
              {alertBusy ? "Salvo..." : alertSet ? "Aggiorna alert" : "Crea alert"}
            </button>
            {alertSet ? (
              <button className="btn ghost remove-btn" disabled={alertBusy || !ticker} onClick={removeQuickAlert}>
                {alertBusy ? "..." : "Rimuovi alert"}
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
      {alertMsg ? <div className="muted">{alertMsg}</div> : null}
      {alertSet ? (
        <div
          style={{
            marginTop: "0.35rem",
            color: "#4ade80",
            fontSize: "0.82rem",
            fontWeight: 700,
          }}
        >
          🔔 Alert attivo
          {alertConfig
            ? `: ${quickAlertFieldLabel(alertConfig.field)} ${alertConfig.op} ${String(alertConfig.value ?? "-")}`
            : ""}
        </div>
      ) : null}
      {showDetails ? (
        <div className="tech-details-wrap">
          <div className="tech-tabs">
            <button
              className={detailMode === "BUY" ? "tech-tab active buy" : "tech-tab buy"}
              onClick={() => setDetailMode("BUY")}
            >
              BUY checklist
            </button>
            <button
              className={detailMode === "SELL" ? "tech-tab active sell" : "tech-tab sell"}
              onClick={() => setDetailMode("SELL")}
            >
              SELL checklist
            </button>
          </div>
          <ul className="tech-checklist">
            {checks.map((c, i) => (
              <li key={`${detailMode}-${i}`}>
                <span className={c.ok ? "ok" : "ko"}>{c.ok ? "✅" : "❌"}</span>
                <b>{c.label}</b>
                {c.extra ? <span className="extra"> ({c.extra})</span> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </article>
  );
}
