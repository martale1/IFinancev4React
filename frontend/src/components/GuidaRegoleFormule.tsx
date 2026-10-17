/**
 * Guida delle regole e delle formule dei pattern.
 *
 * Era scritta dentro la pagina Multi-Pattern Lab. Estratta qui perche' serve in
 * due punti (Laboratorio e fondo degli Highlights): una copia sola, cosi' le due
 * non possono raccontare cose diverse.
 *
 * Non ha props: sono solo testo e stili in linea, nessun dato del server.
 */
export default function GuidaRegoleFormule() {
  return (
    <>
    {/* ══════════════ GUIDA REGOLE E FORMULE (fondo pagina) ══════════════ */}
          <details style={{
            marginTop: "1rem",
            background: "rgba(8,18,34,0.4)",
            border: "1px solid rgba(184,216,246,0.1)",
            borderRadius: "10px",
            padding: "0.7rem 0.9rem",
          }}
          >
            <summary style={{ fontSize: "0.8rem", fontWeight: 600, color: "#b8d4ee", cursor: "pointer", userSelect: "none" }}>
              📖 Guida Regole e Formule (espandi)
            </summary>
            <div style={{ marginTop: "0.7rem", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", fontSize: "0.78rem", lineHeight: "1.4", color: "#b8d4ee" }}>

                                {/* Colonna 1 */}
                                <div>
                                  <h4 style={{ color: "#4ade80", margin: "0 0 0.3rem 0", fontSize: "0.82rem" }}>🟢 S2 (Williams %R + Stoch)</h4>
                                  <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                                    <li>WR in crescita &amp; WR &gt; -80</li>
                                    <li>Stoch K cross &gt; 20, K &gt; D</li>
                                    <li>Stoch K (ieri) &lt; 35 &amp; K oggi &lt; 50</li>
                                  </ul>
                                  <h4 style={{ color: "#38bdf8", margin: "0.6rem 0 0.3rem 0", fontSize: "0.82rem" }}>🔵 S3 (MACD Crossover)</h4>
                                  <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                                    <li>MACD cross &gt; Signal</li>
                                    <li>MACD in pendenza positiva</li>
                                    <li>Istogramma &gt; 0 e crescente</li>
                                  </ul>
                                </div>
                                {/* Colonna 2 */}
                                <div>
                                  <h4 style={{ color: "#a78bfa", margin: "0 0 0.3rem 0", fontSize: "0.82rem" }}>🟣 S4 (EMA Momentum + Vol)</h4>
                                  <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                                    <li>EMA9 &gt; EMA21</li>
                                    <li>RSI tra 55 e 70, crescente</li>
                                    <li>MACD &gt; Signal</li>
                                    <li>Volume &gt; Media(20) × 1.5</li>
                                  </ul>
                                  <h4 style={{ color: "#f472b6", margin: "0.6rem 0 0.3rem 0", fontSize: "0.82rem" }}>🌸 S5 (RSI Oversold + Stoch)</h4>
                                  <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                                    <li>RSI &lt; 30 (zona ipervenduta)</li>
                                    <li>Stoch K incrocia sopra D</li>
                                    <li>K(ieri) ≤ D(ieri) → K(oggi) &gt; D(oggi)</li>
                                  </ul>
                                </div>
                                {/* Colonna 3 */}
                                <div>
                                  <h4 style={{ color: "#facc15", margin: "0 0 0.3rem 0", fontSize: "0.82rem" }}>⭐ S6 (Golden Cross EMA)</h4>
                                  <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                                    <li>EMA30 incrocia sopra EMA50</li>
                                    <li>ADX &gt; 25 (trend forte)</li>
                                    <li>Segnale solo all'ingresso del cross</li>
                                  </ul>
                                  <h4 style={{ color: "#f87171", margin: "0.6rem 0 0.3rem 0", fontSize: "0.82rem" }}>🛡️ Filtri Ausiliari</h4>
                                  <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                                    <li>SAR: Close &gt; SAR</li>
                                    <li>Trend: Close &gt; SMA200</li>
                                  </ul>
                                </div>
                                {/* Colonna 4 */}
                                <div>
                                  <h4 style={{ color: "#fbbf24", margin: "0 0 0.3rem 0", fontSize: "0.82rem" }}>🟡 S7 Early (Alligator Bull)</h4>
                                  <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                                    <li>Close &gt; SAR, Uptrend/Uptrend-</li>
                                    <li>DI+ &gt; DI-</li>
                                    <li>Segnale solo all'ingresso nel livello</li>
                                  </ul>
                                  <h4 style={{ color: "#34d399", margin: "0.6rem 0 0.3rem 0", fontSize: "0.82rem" }}>🟢 S7 Confirmed</h4>
                                  <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                                    <li>Uptrend pieno, EMA30 &gt; EMA50</li>
                                    <li>ADX ≥ 20</li>
                                  </ul>
                                  <h4 style={{ color: "#22c55e", margin: "0.6rem 0 0.3rem 0", fontSize: "0.82rem" }}>🟢🟢 S7 Strong</h4>
                                  <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                                    <li>ADX ≥ 25, sopra SMA200</li>
                                    <li>Volume ≥ MA20</li>
                                  </ul>
                                  <h4 style={{ color: "#60a5fa", margin: "0.6rem 0 0.3rem 0", fontSize: "0.82rem" }}>📦 S8 (Volume Breakout)</h4>
                                  <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                                    <li>Candela rialzista (Close &gt; Open)</li>
                                    <li>Volume &gt; Media(20) × 1.5</li>
                                  </ul>
                                </div>
                                {/* Colonna 5 */}
                                <div>
                                  <h4 style={{ color: "#fb923c", margin: "0 0 0.3rem 0", fontSize: "0.82rem" }}>🟠 S9 Early (Sell-off + primo rimbalzo)</h4>
                                  <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                                    <li>≥ 4 candele rosse nelle ultime 6 sedute</li>
                                    <li>Rendimento 10g ≤ −7% oppure drawdown 20g ≤ −10%</li>
                                    <li>Candela verde (Close &gt; Open)</li>
                                    <li>RSI e Stoch/MACD in recupero</li>
                                  </ul>
                                  <h4 style={{ color: "#f97316", margin: "0.6rem 0 0.3rem 0", fontSize: "0.82rem" }}>🟠 S9 Confirmed (Rimbalzo confermato)</h4>
                                  <ul style={{ paddingLeft: "1rem", margin: 0 }}>
                                    <li>Tutte le condizioni S9 Early</li>
                                    <li>Chiusura sopra il massimo della seduta precedente</li>
                                    <li>Volume ≥ 1,2× MA20</li>
                                  </ul>
          
                                </div>
                          
            </div>
          </details>
    </>
  );
}
