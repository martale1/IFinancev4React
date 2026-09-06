import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AlertCondition, AlertRule } from "../types";
import { deleteAlertRule, fetchAlerts, runAlerts, setAlertRuleEnabled, upsertAlertRule } from "../api";

type Props = {
  market: string;
};

type Mode = "ticker_list" | "market_wide";

const FIELD_OPTIONS = [
  "Action",
  "Market_Phase",
  "TECH_SCORE",
  "MACD",
  "MACD_vs_Signal",
  "PCTV_1D",
  "PCTV_5D",
  "PCTV_10D",
  "PCTV_30D",
  "PCTV_180D",
  "RSI",
  "SIG_MA_SAR",
  "SAR_Above_Price",
  "ADX",
  "Close",
  "Volume",
  "Signal6",
  "Liquidity",
];

const OP_OPTIONS: AlertCondition["op"][] = ["==", "!=", ">", ">=", "<", "<="];

function parseMaybeNumber(v: string): string | number {
  const s = (v || "").trim().replace(",", ".");
  if (!s) return "";
  const n = Number(s);
  return Number.isFinite(n) ? n : v.trim();
}

function asNum(v: unknown): number {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string") {
    const n = Number(v.trim());
    return Number.isFinite(n) ? n : 0;
  }
  return 0;
}

function normalizeRuleId(v: unknown): string {
  return String(v ?? "")
    .trim()
    .replace(/\s+/g, " ")
    .toUpperCase();
}

export default function AlertsPanel({ market }: Props) {
  const qc = useQueryClient();
  const [mode, setMode] = useState<Mode>("ticker_list");
  const [ruleId, setRuleId] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [tickersCsv, setTickersCsv] = useState("");
  const [conditions, setConditions] = useState<AlertCondition[]>([
    { field: "Action", op: "==", value: "BUY" },
  ]);
  const [cooldownMinutes, setCooldownMinutes] = useState(0);
  const [maxPerDay, setMaxPerDay] = useState(3);
  const [minGapMinutes, setMinGapMinutes] = useState(0);
  const [formError, setFormError] = useState("");
  const [formOk, setFormOk] = useState("");

  const alertsQuery = useQuery({
    queryKey: ["alerts", market],
    queryFn: () => fetchAlerts(market),
  });

  const runMutation = useMutation({
    mutationFn: () => runAlerts({ market, telegram_channel: 5, run_only_this_market: true }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts", market] });
    },
  });

  const upsertMutation = useMutation({
    mutationFn: (payload: AlertRule) => upsertAlertRule(market, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts", market] });
    },
  });

  const toggleMutation = useMutation({
    mutationFn: (x: { id: string; enabled: boolean }) => setAlertRuleEnabled(market, x.id, x.enabled),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts", market] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAlertRule(market, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts", market] });
    },
  });

  const rules = alertsQuery.data?.rules ?? [];
  const rulesById = useMemo(() => {
    const m = new Map<string, AlertRule>();
    for (const r of rules) {
      if (r?.id) m.set(normalizeRuleId(r.id), r);
    }
    return m;
  }, [rules]);
  const rowsByRuleId = useMemo(() => {
    const m = new Map<string, Array<Record<string, unknown>>>();
    for (const row of alertsQuery.data?.table ?? []) {
      const rid = normalizeRuleId(row.RuleID);
      if (!rid) continue;
      const arr = m.get(rid) ?? [];
      arr.push(row);
      m.set(rid, arr);
    }
    return m;
  }, [alertsQuery.data?.table]);

  const defaults = useMemo(() => alertsQuery.data?.defaults ?? {}, [alertsQuery.data?.defaults]);
  const aiRules = useMemo(() => rules.filter((r) => String(r.source ?? "").startsWith("ai")), [rules]);
  const aiRows = useMemo(
    () => (alertsQuery.data?.table ?? []).filter((row) => String(row.Source ?? "").toLowerCase().startsWith("ai")),
    [alertsQuery.data?.table]
  );

  function conditionStatus(row: Record<string, unknown>): Array<{ field: string; op: string; value: unknown; actual: unknown; verified: boolean }> {
    try {
      const parsed = JSON.parse(String(row.Condition_Status ?? "[]"));
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  function resolveMaxPerDay(row: Record<string, unknown>, rule: AlertRule | undefined): number {
    const maxPerDayCandidates = [
      row.Max_Per_Day,
      rule?.max_per_day,
      alertsQuery.data?.defaults?.max_per_day,
      3,
    ];
    let maxPerDay = 3;
    for (const c of maxPerDayCandidates) {
      if (c === null || c === undefined) continue;
      const s = String(c).trim();
      if (!s) continue;
      const n = asNum(c);
      if (Number.isFinite(n) && n > 0) {
        maxPerDay = n;
        break;
      }
    }
    return maxPerDay;
  }

  function makeRuleId(): string {
    const firstCond = conditions[0];
    const condStr = firstCond ? `${firstCond.field}_${String(firstCond.value).replace(/\s+/g, "_")}` : "RULE";
    const base = `${market}_${condStr}`.toUpperCase();
    const ts = Date.now().toString().slice(-6);
    return `${base}_${ts}`;
  }

  function resetForm() {
    setRuleId("");
    setEnabled(true);
    setTickersCsv("");
    setConditions([{ field: "Action", op: "==", value: "BUY" }]);
    setCooldownMinutes(Number(defaults.cooldown_minutes ?? 0));
    setMaxPerDay(Number(defaults.max_per_day ?? 3));
    setMinGapMinutes(Number(defaults.min_gap_minutes ?? 0));
    setFormError("");
    setFormOk("");
    setMode("ticker_list");
  }

  function loadRuleToForm(r: AlertRule) {
    setRuleId(String(r.id ?? ""));
    setEnabled(Boolean(r.enabled));
    const tickers = r.scope?.tickers ?? [];
    const where = r.scope?.where ?? [];
    const conds = r.when?.all ?? where;
    setMode(tickers.length > 0 ? "ticker_list" : "market_wide");
    setTickersCsv(tickers.join(", "));
    
    if (conds && conds.length > 0) {
      setConditions(conds.map((c) => ({
        field: String(c.field ?? "Action"),
        op: (c.op as AlertCondition["op"]) ?? "==",
        value: String(c.value ?? "")
      })));
    } else {
      setConditions([{ field: "Action", op: "==", value: "BUY" }]);
    }
    
    setCooldownMinutes(Number(r.cooldown_minutes ?? defaults.cooldown_minutes ?? 0));
    setMaxPerDay(Number(r.max_per_day ?? defaults.max_per_day ?? 3));
    setMinGapMinutes(Number(r.min_gap_minutes ?? defaults.min_gap_minutes ?? 0));
    setFormError("");
    setFormOk("Regola caricata nel form.");
  }

  async function onSaveRule() {
    setFormError("");
    setFormOk("");
    const id = (ruleId || "").trim() || makeRuleId();
    if (!id) {
      setFormError("Rule ID mancante.");
      return;
    }
    if (conditions.length === 0) {
      setFormError("Aggiungi almeno una condizione.");
      return;
    }
    
    const parsedConditions = conditions.map((c) => ({
      field: c.field.trim(),
      op: c.op,
      value: parseMaybeNumber(String(c.value)),
    }));

    for (const cond of parsedConditions) {
      if (!cond.field) {
        setFormError("Campo condizione mancante in uno degli elementi.");
        return;
      }
    }

    let scope: AlertRule["scope"] = {};
    if (mode === "ticker_list") {
      const tickers = tickersCsv
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean);
      if (tickers.length === 0) {
        setFormError("Inserisci almeno un ticker (separati da virgola).");
        return;
      }
      scope = { tickers };
    } else {
      scope = { where: parsedConditions };
    }

    const payload: AlertRule = {
      id,
      enabled,
      scope,
      when: { all: parsedConditions },
      cooldown_minutes: Number(cooldownMinutes) || 0,
      max_per_day: Math.max(1, Number(maxPerDay) || 1),
      min_gap_minutes: Math.max(0, Number(minGapMinutes) || 0),
      message: {
        title: "🔔 Alert {{Ticker}}",
        body: "Close: {{Close}}\nSAR: {{SAR}}\nSAR sopra prezzo: {{SAR_Above_Price}}\nRSI: {{RSI}}\nSARMA: {{SIG_MA_SAR}}\nMACD: {{MACD}}\nS3: {{MACD_vs_Signal}}\nAction: {{Action}}\nTECH: {{TECH_SCORE}}",
      },
    };

    try {
      await upsertMutation.mutateAsync(payload);
      setRuleId(id);
      setFormOk(`Regola salvata: ${id}`);
    } catch (e) {
      setFormError(String(e));
    }
  }

  return (
    <section className="alerts">
      <div className="alerts-head">
        <h2>Alerts</h2>
        <button className="btn" onClick={() => runMutation.mutate()} disabled={runMutation.isPending}>
          {runMutation.isPending ? "Esecuzione..." : "Run AlertEngine"}
        </button>
      </div>
      {runMutation.isError ? <p className="err">Run error: {String(runMutation.error)}</p> : null}

      <div className="alert-form" style={{ marginBottom: "1rem" }}>
        <h3>🤖 Alert AI</h3>
        <p className="muted">Regole create esplicitamente dalle condizioni proposte nelle analisi AI.</p>
        {aiRules.length === 0 ? <p className="muted">Nessun alert AI attivo.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Titolo</th><th>Avanzamento</th><th>Dettaglio condizioni</th><th>Stato</th><th>Azioni</th></tr></thead>
              <tbody>
                {aiRows.map((row, i) => {
                  const statuses = conditionStatus(row);
                  const verified = statuses.filter((c) => c.verified).length;
                  const rule = rulesById.get(normalizeRuleId(row.RuleID));
                  return (
                    <tr key={`ai-${String(row.RuleID)}-${String(row.Ticker)}-${i}`}>
                      <td><strong>{String(row.Ticker ?? "-")}</strong><br /><small>{String(row.Source) === "ai_level" ? "Livello critico AI" : "Setup condizioni AI"} · {String(row.RuleID ?? "-")}</small></td>
                      <td><span className={`enabled-badge ${statuses.length > 0 && verified === statuses.length ? "active" : "inactive"}`}>{verified}/{statuses.length}</span></td>
                      <td>
                        {statuses.map((c, idx) => (
                          <div key={idx} style={{ color: c.verified ? "#22c55e" : "#f59e0b", whiteSpace: "nowrap" }}>
                            {c.verified ? "✓" : "○"} {c.field} {c.op} {String(c.value)} <small>(ora: {c.actual == null ? "n/d" : String(c.actual)})</small>
                          </div>
                        ))}
                      </td>
                      <td>{rule?.enabled ? "Attivo" : "Disabilitato"}</td>
                      <td className="actions-cell">
                        <button className="btn ghost" onClick={() => rule && toggleMutation.mutate({ id: rule.id, enabled: !rule.enabled })}>{rule?.enabled ? "Disabilita" : "Abilita"}</button>
                        <button className="btn ghost" onClick={() => rule && deleteMutation.mutate(rule.id)}>Elimina</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="alert-form">
        <h3>Nuovo alert / Modifica alert</h3>
        <div className="alert-grid">
          <label>
            Rule ID
            <input value={ruleId} placeholder="es. BUY_STMMI" onChange={(e) => setRuleId(e.target.value)} />
          </label>
          <label>
            Mode
            <select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
              <option value="ticker_list">Ticker list</option>
              <option value="market_wide">Market-wide</option>
            </select>
          </label>
          <label>
            Enabled
            <select value={enabled ? "1" : "0"} onChange={(e) => setEnabled(e.target.value === "1")}>
              <option value="1">true</option>
              <option value="0">false</option>
            </select>
          </label>
          <label>
            Tickers (csv)
            <input
              value={tickersCsv}
              placeholder="es. STMMI.MI, ENEL.MI"
              onChange={(e) => setTickersCsv(e.target.value)}
              disabled={mode !== "ticker_list"}
            />
          </label>
          <label>
            cooldown_minutes
            <input type="number" value={cooldownMinutes} min={0} onChange={(e) => setCooldownMinutes(Number(e.target.value) || 0)} />
          </label>
          <label>
            max_per_day
            <input type="number" value={maxPerDay} min={1} onChange={(e) => setMaxPerDay(Number(e.target.value) || 1)} />
          </label>
          <label>
            min_gap_minutes
            <input type="number" value={minGapMinutes} min={0} onChange={(e) => setMinGapMinutes(Number(e.target.value) || 0)} />
          </label>
        </div>

        <div className="conditions-list">
          <div className="conditions-header">
            <h4>Condizioni (Tutte devono essere soddisfatte - AND)</h4>
            <button
              type="button"
              className="btn"
              onClick={() => setConditions([...conditions, { field: "Action", op: "==", value: "BUY" }])}
            >
              + Aggiungi Condizione
            </button>
          </div>
          {conditions.map((cond, idx) => (
            <div key={idx} className="condition-row">
              <select
                value={cond.field}
                onChange={(e) => {
                  const copy = [...conditions];
                  copy[idx].field = e.target.value;
                  if (e.target.value === "SAR_Above_Price") {
                    copy[idx].op = "==";
                    copy[idx].value = 0;
                  }
                  setConditions(copy);
                }}
              >
                {FIELD_OPTIONS.map((f) => (
                  <option key={f} value={f}>
                    {f === "SAR_Above_Price" ? "Parabolic SAR sopra/sotto prezzo" : f}
                  </option>
                ))}
              </select>
              <select
                value={cond.op}
                onChange={(e) => {
                  const copy = [...conditions];
                  copy[idx].op = e.target.value as AlertCondition["op"];
                  setConditions(copy);
                }}
              >
                {(cond.field === "SAR_Above_Price" ? ["=="] : OP_OPTIONS).map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
              {cond.field === "SAR_Above_Price" ? (
                <select
                  value={String(cond.value)}
                  onChange={(e) => {
                    const copy = [...conditions];
                    copy[idx].value = Number(e.target.value);
                    setConditions(copy);
                  }}
                >
                  <option value="0">SAR sotto il prezzo</option>
                  <option value="1">SAR sopra il prezzo</option>
                </select>
              ) : (
                <input
                  value={cond.value}
                  placeholder="es. BUY, 65, -1"
                  onChange={(e) => {
                    const copy = [...conditions];
                    copy[idx].value = e.target.value;
                    setConditions(copy);
                  }}
                />
              )}
              <button
                type="button"
                className="btn ghost remove-btn"
                onClick={() => {
                  setConditions(conditions.filter((_, i) => i !== idx));
                }}
                disabled={conditions.length <= 1}
              >
                Rimuovi
              </button>
            </div>
          ))}
        </div>
        <div className="alert-actions">
          <button className="btn" onClick={onSaveRule} disabled={upsertMutation.isPending}>
            {upsertMutation.isPending ? "Salvataggio..." : "Salva regola"}
          </button>
          <button className="btn ghost" onClick={resetForm} type="button">
            Reset
          </button>
        </div>
        {formError ? <p className="err">{formError}</p> : null}
        {formOk ? <p className="muted">{formOk}</p> : null}
      </div>

      {runMutation.data ? <pre className="json">{JSON.stringify(runMutation.data, null, 2)}</pre> : null}
      {alertsQuery.isLoading ? <p>Carico alerts...</p> : null}
      {alertsQuery.isError ? <p className="err">{String(alertsQuery.error)}</p> : null}
      {alertsQuery.data ? (
        <>
          <p className="muted">Rules: {rules.length}</p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>RuleID</th>
                  <th>Status</th>
                  <th>Today</th>
                  <th>Scope</th>
                  <th>Condizione</th>
                  <th>Azioni</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((r, i) => {
                  const conditionsLabel = (r.when?.all ?? [])
                    .map((c) => `${c.field} ${c.op} ${String(c.value)}`)
                    .join(" AND ");
                  const ridNorm = normalizeRuleId(r.id);
                  const rowsForRule = rowsByRuleId.get(ridNorm) ?? [];
                  const isSingleTickerRule = (r.scope?.tickers?.length ?? 0) === 1 && (r.scope?.where?.length ?? 0) === 0;
                  let todayRatio = "-";
                  if (isSingleTickerRule && rowsForRule.length > 0) {
                    const row = rowsForRule[0];
                    const firedToday = asNum(row.Fired_Today);
                    const maxPerDay = resolveMaxPerDay(row, r);
                    todayRatio = `${firedToday}/${maxPerDay}`;
                  }
                  const scopeLabel = r.scope?.tickers?.length
                    ? r.scope.tickers.join(", ")
                    : (r.scope?.where ?? []).map((c) => `${c.field} ${c.op} ${String(c.value)}`).join(" AND ");
                  return (
                    <tr key={`${r.id}-${i}`}>
                      <td>{r.id}</td>
                      <td>
                        <span className={r.enabled ? "enabled-badge active" : "enabled-badge inactive"}>
                          {r.enabled ? "Enabled" : "Disabled"}
                        </span>
                      </td>
                      <td>{todayRatio}</td>
                      <td>{scopeLabel || "-"}</td>
                      <td>{conditionsLabel || "-"}</td>
                      <td className="actions-cell">
                        <button className="btn ghost" type="button" onClick={() => loadRuleToForm(r)}>
                          Edit
                        </button>
                        <button
                          className="btn ghost"
                          type="button"
                          onClick={() => toggleMutation.mutate({ id: r.id, enabled: !r.enabled })}
                          disabled={toggleMutation.isPending}
                        >
                          {r.enabled ? "Disable" : "Enable"}
                        </button>
                        <button
                          className="btn ghost"
                          type="button"
                          onClick={() => deleteMutation.mutate(r.id)}
                          disabled={deleteMutation.isPending}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>RuleID</th>
                  <th>Max/Day</th>
                  <th>Remaining Today</th>
                  <th>Sent Today</th>
                  <th>Sent Total</th>
                  <th>Last Alert</th>
                </tr>
              </thead>
              <tbody>
                {alertsQuery.data.table.slice(0, 200).map((r, i) => {
                  const firedToday = asNum(r.Fired_Today);
                  const rid = normalizeRuleId(r.RuleID);
                  const rule = rulesById.get(rid);
                  const maxPerDay = resolveMaxPerDay(r, rule);
                  const remainingToday = String(Math.max(0, maxPerDay - firedToday));
                  return (
                    <tr key={`${String(r.RuleID)}-${i}`}>
                      <td>{String(r.Ticker ?? "-")}</td>
                      <td>{String(r.RuleID ?? "-")}</td>
                      <td>{String(maxPerDay)}</td>
                      <td>{remainingToday}</td>
                      <td>{String(r.Fired_Today ?? "0")}</td>
                      <td>{String(r.Fired_Total ?? "0")}</td>
                      <td>{String(r.Last_Alert ?? "-")}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </section>
  );
}

