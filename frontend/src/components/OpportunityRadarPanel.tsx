import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchOpportunities } from "../api";
import type { OpportunityRow } from "../types";

type Props = {
  currentMarket: string;
  onChart: (row: OpportunityRow) => void;
};

const MODES = [
  { id: "balanced", label: "Bilanciato", desc: "Segnali, trend, liquidità e rischio" },
  { id: "reversal", label: "Reversal", desc: "S2 e RSI Oversold" },
  { id: "early_trend", label: "Trend iniziale", desc: "S3, Golden Cross e Alligator" },
  { id: "momentum", label: "Momentum", desc: "S4 e Volume Breakout" },
];

function fmt(value: number, digits = 2): string {
  return Number.isFinite(value) ? value.toFixed(digits) : "-";
}

function compact(value: number): string {
  if (!Number.isFinite(value)) return "-";
  return new Intl.NumberFormat("it-IT", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function ageLabel(days: number): string {
  if (days === 0) return "oggi";
  if (days === 1) return "ieri";
  return `${days}g fa`;
}

export default function OpportunityRadarPanel({ currentMarket, onChart }: Props) {
  const [scope, setScope] = useState("ALL");
  const [mode, setMode] = useState("balanced");
  const [window, setWindow] = useState(10);
  const query = useQuery({
    queryKey: ["opportunities", scope, mode, window],
    queryFn: () => fetchOpportunities({ market: scope, mode, limit: 20, window }),
  });

  const cardStyle = {
    background: "rgba(8, 20, 37, 0.82)", border: "1px solid rgba(96,165,250,0.2)",
    borderRadius: "14px", padding: "0.9rem", boxShadow: "0 10px 28px rgba(0,0,0,0.18)",
  } as const;

  return (
    <section style={{ display: "grid", gap: "1rem", marginTop: "1rem" }}>
      <header style={{ ...cardStyle, display: "grid", gap: "0.8rem" }}>
        <div>
          <h2 style={{ margin: 0, color: "#dbeafe" }}>Opportunity Radar</h2>
          <p style={{ margin: "0.35rem 0 0", color: "#93b7d8", fontSize: "0.9rem" }}>
            Ranking sperimentale dei segnali recenti. Ogni punteggio mostra conferme e rischi che lo compongono.
          </p>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.55rem", alignItems: "center" }}>
          <select value={scope} onChange={(event) => setScope(event.target.value)}>
            <option value="ALL">Tutti i mercati</option>
            <option value={currentMarket}>Mercato corrente: {currentMarket}</option>
          </select>
          <select value={window} onChange={(event) => setWindow(Number(event.target.value))}>
            <option value={5}>Segnali ultimi 5 giorni</option>
            <option value={10}>Segnali ultimi 10 giorni</option>
            <option value={20}>Segnali ultimi 20 giorni</option>
          </select>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
          {MODES.map((item) => (
            <button key={item.id} className={mode === item.id ? "btn" : "btn ghost"} onClick={() => setMode(item.id)}>
              {item.label} <span style={{ opacity: 0.7, fontSize: "0.72rem" }}>· {item.desc}</span>
            </button>
          ))}
        </div>
      </header>

      {query.isLoading ? <div style={cardStyle}>Calcolo ranking dai file Excel...</div> : null}
      {query.isError ? <div className="err" style={cardStyle}>{String(query.error)}</div> : null}

      {query.data ? (
        <>
          <div style={{ color: "#8fb3d4", fontSize: "0.82rem" }}>
            {query.data.total_candidates} candidati con almeno un segnale nella finestra · Top {query.data.results.length}
          </div>
          {query.data.results.length === 0 ? <div style={cardStyle}>Nessun candidato per questa combinazione.</div> : null}
          <div style={{ display: "grid", gap: "0.75rem" }}>
            {query.data.results.map((row, index) => (
              <article key={`${row.Ticker}-${row.Market}`} style={cardStyle}>
                <div style={{ display: "flex", gap: "0.8rem", justifyContent: "space-between", flexWrap: "wrap" }}>
                  <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
                    <div style={{ width: 48, height: 48, borderRadius: "50%", display: "grid", placeItems: "center", background: row.Score >= 65 ? "#166534" : row.Score >= 45 ? "#854d0e" : "#334155", color: "white", fontWeight: 800 }}>
                      {fmt(row.Score, 0)}
                    </div>
                    <div>
                      <div style={{ color: "#f8fafc", fontWeight: 800 }}>#{index + 1} {row.Ticker}</div>
                      <div style={{ color: "#93b7d8", fontSize: "0.8rem" }}>{row.Name} · {row.Markets.join(", ")}</div>
                    </div>
                  </div>
                  <button className="btn ghost" onClick={() => onChart(row)}>Apri grafico</button>
                </div>

                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.45rem", marginTop: "0.75rem" }}>
                  {row.signals.map((signal) => (
                    <span key={signal.id} style={{ padding: "0.25rem 0.5rem", borderRadius: 999, background: "rgba(59,130,246,0.18)", color: "#bfdbfe", fontSize: "0.76rem" }}>
                      {signal.label} · {ageLabel(signal.days_ago)}
                    </span>
                  ))}
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))", gap: "0.45rem", marginTop: "0.75rem", color: "#cbd5e1", fontSize: "0.8rem" }}>
                  <span>Prezzo <b>{fmt(row.Close, 3)}</b></span><span>1D <b>{fmt(row.PCTV_1D)}%</b></span>
                  <span>5D <b>{fmt(row.PCTV_5D)}%</b></span><span>RSI <b>{fmt(row.RSI, 1)}</b></span>
                  <span>ADX <b>{fmt(row.ADX, 1)}</b></span><span>ATR <b>{fmt(row.ATR_PCT, 1)}%</b></span>
                  <span title={new Intl.NumberFormat("it-IT").format(row.Volume)}>Volume <b>{compact(row.Volume)}</b></span>
                  <span title={`€ ${new Intl.NumberFormat("it-IT").format(row.Turnover)}`}>Controvalore <b>€ {compact(row.Turnover)}</b></span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "0.65rem", marginTop: "0.75rem" }}>
                  <div style={{ color: "#86efac", fontSize: "0.78rem" }}>{row.reasons.slice(0, 4).map((reason) => <div key={reason}>+ {reason}</div>)}</div>
                  <div style={{ color: "#fca5a5", fontSize: "0.78rem" }}>{row.risks.slice(0, 4).map((risk) => <div key={risk}>− {risk}</div>)}</div>
                </div>
              </article>
            ))}
          </div>
          <p style={{ color: "#7899b8", fontSize: "0.75rem" }}>{query.data.disclaimer}</p>
        </>
      ) : null}
    </section>
  );
}
