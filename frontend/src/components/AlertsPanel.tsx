import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AlertRule } from "../types";
import { deleteAlertRule, fetchAlerts, runAlerts, setAlertRuleEnabled } from "../api";

type Props = {
  market: string;
  onOpenChart?: (ticker: string) => void;
};

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

export default function AlertsPanel({ market, onOpenChart }: Props) {
  const qc = useQueryClient();
  const alertsQuery = useQuery({
    queryKey: ["alerts", market],
    queryFn: () => fetchAlerts(market),
    refetchInterval: 15000,
  });

  const runMutation = useMutation({
    mutationFn: () => runAlerts({ market, telegram_channel: 5, run_only_this_market: true }),
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

  const aiRules = useMemo(() => rules.filter((r) => String(r.source ?? "").toLowerCase().startsWith("ai")), [rules]);
  const aiRows = useMemo(
    () => (alertsQuery.data?.table ?? []).filter((row) => String(row.Source ?? "").toLowerCase().startsWith("ai")),
    [alertsQuery.data?.table]
  );

  const personalRules = rules.filter((rule) => !aiRules.includes(rule));
  const firedRows = (alertsQuery.data?.table ?? []).filter((row) =>
    asNum(row.Fired_Total) > 0 || asNum(row.Fired_Today) > 0
  ).sort((a, b) => String(b.Last_Alert ?? "").localeCompare(String(a.Last_Alert ?? "")));

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

  return (
    <section className="alerts">
      <div className="alerts-head">
        <h2>Alerts</h2>
        <button className="btn" onClick={() => runMutation.mutate()} disabled={runMutation.isPending}>
          {runMutation.isPending ? "Esecuzione..." : "Run AlertEngine"}
        </button>
      </div>
      {runMutation.isError ? <p className="err">Run error: {String(runMutation.error)}</p> : null}

      <section className="alert-section alert-fired-summary">
        <div className="active-alerts-heading"><div><strong>🔔 Alert scattati</strong><span>Ultimi titoli e condizioni che hanno generato un alert</span></div><span className="enabled-badge active">{firedRows.length} attivi</span></div>
        {!firedRows.length ? <p className="muted">Nessun alert scattato.</p> : (
          <div className="fired-alert-cards">
            {firedRows.slice(0, 12).map((row, i) => {
              const rule = rulesById.get(normalizeRuleId(row.RuleID));
              const statuses = conditionStatus(row);
              const conditionText = statuses.length
                ? statuses.map((c) => `${c.field} ${c.op} ${String(c.value)} · valore rilevato: ${c.actual == null ? "n/d" : String(c.actual)}${c.verified ? " ✓" : ""}`).join(" · ")
                : (rule?.when?.all ?? []).map((c) => `${c.field} ${c.op} ${String(c.value)}`).join(" · ") || "Condizione non disponibile";
              const metricText = [
                ["ADX", row.ADX], ["DI+", row.PLUS_DI ?? row.DI_plus], ["DI−", row.MINUS_DI ?? row.DI_minus],
              ].filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== "")
                .map(([label, value]) => `${label}: ${String(value)}`).join(" · ");
              return <article className="fired-alert-card" key={`summary-${String(row.RuleID)}-${String(row.Ticker)}-${i}`}>
                <div><strong>{String(row.Ticker ?? "-")}</strong><span>{String(row.Last_Alert ?? "-")}</span></div>
                <p>{conditionText}</p>
                {metricText ? <small className="fired-alert-metrics">Indicatori: {metricText}</small> : null}
                <button className="btn ghost" type="button" onClick={() => onOpenChart?.(String(row.Ticker ?? ""))} disabled={!onOpenChart}>Apri grafico</button>
              </article>;
            })}
          </div>
        )}
      </section>

      <section className="alert-section">
        <h3>Alert AI</h3>
        <p className="muted">Condizioni e livelli proposti dalle analisi AI. Regole: {aiRules.length}</p>
        {aiRules.length === 0 ? <p className="muted">Nessun alert AI.</p> : (
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
                      <td><span className={rule?.enabled ? "enabled-badge active" : "enabled-badge inactive"}>{rule?.enabled ? "Attivo" : "Disabilitato"}</span></td>
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
      </section>

      {runMutation.data ? <pre className="json">{JSON.stringify(runMutation.data, null, 2)}</pre> : null}
      {alertsQuery.isLoading ? <p>Carico alerts...</p> : null}
      {alertsQuery.isError ? <p className="err">{String(alertsQuery.error)}</p> : null}
      {alertsQuery.data ? (
        <>
          <section className="alert-section">
          <h3>Alert personalizzati</h3>
          <p className="muted">Condizioni e livelli impostati dalle schede titolo o da altre regole personalizzate.</p>
          <p className="muted">{personalRules.length ? `Regole: ${personalRules.length}` : "Nessun alert personalizzato."}</p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Regola</th>
                  <th>Stato</th>
                  <th>Invii oggi / limite</th>
                  <th>Titoli</th>
                  <th>Condizione</th>
                  <th>Azioni</th>
                </tr>
              </thead>
              <tbody>
                {personalRules.map((r, i) => {
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
                          {r.enabled ? "Attivo" : "Disabilitato"}
                        </span>
                      </td>
                      <td>{todayRatio}</td>
                      <td>{scopeLabel || "-"}</td>
                      <td>{conditionsLabel || "-"}</td>
                      <td className="actions-cell">
                        <button
                          className="btn ghost"
                          type="button"
                          onClick={() => toggleMutation.mutate({ id: r.id, enabled: !r.enabled })}
                          disabled={toggleMutation.isPending}
                        >
                          {r.enabled ? "Disabilita" : "Abilita"}
                        </button>
                        <button
                          className="btn ghost"
                          type="button"
                          onClick={() => deleteMutation.mutate(r.id)}
                          disabled={deleteMutation.isPending}
                        >
                          Elimina
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          </section>
          <section className="alert-section">
          <h3>Alert scattati</h3>
          <p className="muted">Invii registrati per alert AI e personalizzati, ordinati dal piu recente. Contatori per titolo e regola.</p>
          {!firedRows.length ? <p className="muted">Nessun alert scattato.</p> : null}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Origine</th>
                  <th>Regola</th>
                  <th>Limite giornaliero</th>
                  <th>Rimanenti oggi</th>
                  <th>Inviati oggi</th>
                  <th>Inviati totali</th>
                  <th>Ultimo invio</th>
                </tr>
              </thead>
              <tbody>
                {firedRows.map((r, i) => {
                  const firedToday = asNum(r.Fired_Today);
                  const rid = normalizeRuleId(r.RuleID);
                  const rule = rulesById.get(rid);
                  const maxPerDay = resolveMaxPerDay(r, rule);
                  const remainingToday = String(Math.max(0, maxPerDay - firedToday));
                  return (
                    <tr key={`${String(r.RuleID)}-${i}`}>
                      <td>{String(r.Ticker ?? "-")}</td>
                      <td>{String(r.Source ?? rule?.source ?? "").toLowerCase().startsWith("ai") ? "AI" : "Personalizzato"}</td>
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
          </section>
        </>
      ) : null}
    </section>
  );
}

