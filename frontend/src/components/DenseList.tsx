import { useState, type ReactNode } from "react";
import type { WatchlistRow } from "../types";
import { num, pct, pctClass, percheNonEntra, toNum } from "../format";

/**
 * Lista compatta riutilizzabile: una riga per titolo, espandibile sul posto.
 *
 * Nata per il Monitor (dove una scheda alta 385 px rendeva necessarie 9 schermate
 * con 20 titoli, mentre una riga da 47 px ne fa vedere 18 per schermata), e ora
 * condivisa con la tab All cosi' le due viste non possono divergere.
 *
 * I colori seguono le stesse regole delle schede: verde favorevole, rosso
 * sfavorevole, grigio neutro.
 */

/** Verde favorevole, rosso sfavorevole, grigio neutro. */
export function statoClass(valore: unknown): string {
  const v = String(valore ?? "").toUpperCase();
  if (["SU", "FORTE_SU", "CRESCENTE", "NORMALE", "OK", "BUY", "ADD"].includes(v)) return "good";
  if (["GIU", "FORTE_GIU", "CALANTE", "TESO", "ESTREMO", "AVOID", "EXIT", "SELL", "REDUCE"].includes(v)) return "bad";
  return "";
}

/** TECH: verde se sostiene, rosso se debole, grigio in mezzo. */
export function techClass(valore: unknown): string {
  const n = toNum(valore);
  if (n === null) return "";
  if (n >= 65) return "good";
  if (n <= 35) return "bad";
  return "";
}

/** Colore per la striscia MACD: positiva sopra zero, negativa sotto. */
export function s3Color(valore: unknown): string {
  const n = toNum(valore);
  if (n === null || n === 0) return "#9fb7cf";
  return n > 0 ? "#22c55e" : "#ff4d5a";
}

export function DenseList({
  rows,
  renderActions,
  emptyText = "Nessun titolo da mostrare.",
  percentuale,
}: {
  rows: WatchlistRow[];
  /** Azioni mostrate nel dettaglio aperto: ogni tab passa le sue. */
  renderActions?: (row: WatchlistRow) => ReactNode;
  emptyText?: string;
  /** Percentuale da mostrare nella riga. Serve a mostrare quella su cui si sta
   *  ordinando: altrimenti ordinando per 5D i numeri sembrano in disordine. */
  percentuale?: { key: string; label: string };
}) {
  const [aperta, setAperta] = useState<string | null>(null);

  if (!rows.length) {
    return <p className="muted" style={{ padding: ".6rem .2rem" }}>{emptyText}</p>;
  }

  return (
    <div className="monitor-dense-list">
      {rows.map((row, indice) => {
        const tk = String(row.Ticker || "").trim();
        const src = String(row.WL_Source_Market || "");
        const segnale = String(row.Entry_Signal ?? "ATTENDI").toUpperCase();
        const fase = String(row.Market_Phase ?? "-");
        const direzione = String(row.Direzione_Trend ?? "-");
        const forza = String(row.Forza_Trend ?? "-").replace("FORTE_", "");
        const nota = String(row.Monitor_Note || "").trim();
        const chiave = `${src}-${tk}-${indice}`;
        const espansa = aperta === chiave;
        // Nome leggibile: si toglie il suffisso di mercato attaccato in coda
        // ("Amundi MSCI Semiconductors UCITS ETF Acc.MI") solo se coincide con
        // quello del ticker, cosi' non si taglia altro.
        // Perche' non e' ENTRA: si mostra solo sugli OSSERVA.
        const motivo = percheNonEntra(row as Record<string, unknown>);
        const nomeBreve = (() => {
          const grezzo = String(row.Name ?? "").replace(/\s+/g, " ").trim();
          if (!grezzo) return "";
          const suffisso = tk.includes(".") ? tk.slice(tk.indexOf(".")) : "";
          if (suffisso && grezzo.endsWith(suffisso)) {
            return grezzo.slice(0, -suffisso.length).trim();
          }
          return grezzo;
        })();

        return (
          <div className={`monitor-dense-item ${espansa ? "open" : ""}`} key={chiave}>
            <button
              type="button"
              className="monitor-dense-row"
              onClick={() => setAperta(espansa ? null : chiave)}
              aria-expanded={espansa}
              title={espansa ? `${tk} — chiudi i dettagli` : `${tk} — mostra tutti i dati`}
            >
              <span className={`dense-signal table-signal ${signalClass(segnale)}`}>{segnale}</span>
              <span className="dense-ticker">
                <b>{tk}</b>
                {/* Il nome sta accanto al ticker perche' "EMQQ.MI" da solo non dice
                    cosa sia. Alcuni nomi arrivano con il suffisso di mercato
                    attaccato ("... UCITS ETF Acc.MI"): si toglie solo quando
                    coincide con quello del ticker, cosi' non si taglia altro. */}
                {nomeBreve ? <em className="dense-nome" title={nomeBreve}>{nomeBreve}</em> : null}
                <small>
                  {fase} · {direzione}/{forza}
                  {nota ? " · 📝" : ""}
                </small>
              </span>
              <span className="dense-numbers">
                <b>{num(row.Close, 3)}</b>
                <small className={pctClass(row[percentuale?.key ?? "PCTV_1D"])}>
                  {percentuale ? <em className="dense-pct-label">{percentuale.label}</em> : null}
                  {pct(row[percentuale?.key ?? "PCTV_1D"])}
                </small>
              </span>
              <span className={`dense-tech ${techClass(row.TECH_SCORE)}`}>TECH {num(row.TECH_SCORE, 0)}</span>
              <span className="dense-caret" aria-hidden="true">{espansa ? "▴" : "▾"}</span>
            </button>

            {espansa ? (
              <div className="monitor-dense-detail">
                <div className="monitor-groups">
                  <div className="monitor-group">
                    <span className="monitor-group-title">Trend</span>
                    <div className="monitor-metrics">
                      <span>Direzione <b className={statoClass(direzione)}>{direzione}</b></span>
                      <span>Forza <b className={statoClass(row.Forza_Trend)}>{forza}</b></span>
                      <span>ADX <b>{num(row.ADX, 1)}</b></span>
                      <span>DI+ <b className="good">{num(row.PLUS_DI, 1)}</b></span>
                      <span>DI− <b className="bad">{num(row.MINUS_DI, 1)}</b></span>
                      <span>SARMA <b>{num(row.SIG_MA_SAR, 0)}</b></span>
                    </div>
                  </div>
                  <div className="monitor-group">
                    <span className="monitor-group-title">Momentum</span>
                    <div className="monitor-metrics">
                      <span>Momento <b className={statoClass(row.Momento_Trend)}>{String(row.Momento_Trend ?? "-")}</b></span>
                      <span>RSI <b>{num(row.RSI, 0)}</b></span>
                      <span>Stoch <b>{num(row.Stoch_K, 0)}/{num(row.Stoch_D, 0)}</b></span>
                      <span>willR <b>{num(row.Williams_R, 0)}</b></span>
                      <span>MACD−Signal <b style={{ color: s3Color(row.MACD_vs_Signal) }}>{num(row.MACD_vs_Signal, 0)}</b></span>
                      <span>Alligator <b>{String(row.Signal6 ?? "-")}</b></span>
                    </div>
                  </div>
                  <div className="monitor-group">
                    <span className="monitor-group-title">Performance</span>
                    <div className="monitor-metrics">
                      <span>1D <b className={`pct ${pctClass(row.PCTV_1D)}`}>{pct(row.PCTV_1D)}</b></span>
                      <span>5D <b className={`pct ${pctClass(row.PCTV_5D)}`}>{pct(row.PCTV_5D)}</b></span>
                      <span>10D <b className={`pct ${pctClass(row.PCTV_10D)}`}>{pct(row.PCTV_10D)}</b></span>
                      <span>30D <b className={`pct ${pctClass(row.PCTV_30D)}`}>{pct(row.PCTV_30D)}</b></span>
                      <span>180D <b className={`pct ${pctClass(row.PCTV_180D)}`}>{pct(row.PCTV_180D)}</b></span>
                      <span>VOL <b>{num(row.Volume, 0)}</b></span>
                    </div>
                  </div>
                  <div className="monitor-group">
                    <span className="monitor-group-title">Contesto</span>
                    <div className="monitor-metrics">
                      {/* L'ATR e' uno dei due numeri che decidono il rischio (soglie 3% e
                          5%): mostrarlo rende visibile perche' un titolo e' TESO o ESTREMO. */}
                      <span title={`Volatilità: ATR ${num(row.ATR_PCT, 2)}% · soglie 3% teso, 5% estremo`}>
                        Rischio <b className={statoClass(row.Rischio_Trend)}>{String(row.Rischio_Trend ?? "-")}</b>
                        {" "}<small className="atr-rischio">{toNum(row.ATR_PCT) === null ? "" : `${num(row.ATR_PCT, 2)}%`}</small>
                      </span>

                      <span>Fase <b>{fase}</b></span>
                      <span>Liquidità <b className={statoClass(row.Liquidity)}>{String(row.Liquidity ?? "-")}</b></span>
                      <span>Azioni <b className={statoClass(row.Action)}>{String(row.Action ?? "-")}</b></span>
                      {/* Nome intero: nella riga e' troncato con i puntini, qui si legge
                          tutto (gli ETF arrivano a 72 caratteri). */}
                      {nomeBreve ? <span className="dense-nome-intero">Nome <b>{nomeBreve}</b></span> : null}
                    </div>
                    {/* Fuori da .monitor-metrics, che impone nowrap sui suoi span. */}
                    {motivo ? <p className="motivo-non-entra">→ {motivo}</p> : null}
                  </div>
                </div>

                {nota ? <p className="dense-note">📝 {nota}</p> : null}

                {renderActions ? (
                  <div className="dense-actions">{renderActions(row)}</div>
                ) : null}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

/** Stesse classi della tabella, cosi' il segnale ha lo stesso aspetto ovunque. */
function signalClass(value: unknown): string {
  const signal = String(value ?? "ATTENDI").toUpperCase();
  if (signal === "ENTRA") return "enter";
  if (signal === "OSSERVA") return "watch";
  if (signal === "EVITA") return "avoid";
  return "wait";
}

