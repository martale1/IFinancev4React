/**
 * Pulsante e pannello dei livelli di uscita, riusabile su qualsiasi card o riga.
 *
 * Nella card della watchlist (`WatchlistCard`) il pannello era scritto a mano.
 * Servendo anche alla card della tab Monitor e alle righe della Lista, il codice
 * e' stato raccolto qui: un solo posto da correggere.
 *
 * PERCHE' SERVE: il sistema calcola gli stop solo quando suggerisce un'operazione
 * (`four_axes._levels_from_axes`): `Trend_Stop_Level` (EMA50) esiste solo se
 * l'azione e' BUY o ADD, `Profit_Protect_Level` solo se e' REDUCE. Quando l'azione
 * diventa HOLD — cioe' proprio quando hai una posizione aperta e il titolo si e'
 * allontanato — i livelli spariscono. Qui si CALCOLANO dai numeri della riga.
 *
 * LIMITE DICHIARATO NEL PANNELLO: sono livelli misurati dal prezzo di oggi. Senza
 * il prezzo di carico non dicono se si esce in profitto o in perdita.
 */
import { useState } from "react";

import { livelliUscita, piuLontano, piuVicino } from "../livelliUscita";

/** Formatta un prezzo con 3 decimali, in italiano. */
function prezzo(v: number): string {
  return v.toLocaleString("it-IT", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
}

export default function UscitaButton({
  row,
  className = "btn ghost",
}: {
  row: Record<string, unknown>;
  /** Classe del pulsante, per adattarsi al contesto (card o riga). */
  className?: string;
}) {
  const [aperto, setAperto] = useState(false);
  const livelli = aperto ? livelliUscita(row) : [];
  const stretto = piuVicino(livelli);
  const ampio = piuLontano(livelli);

  return (
    <>
      <button
        type="button"
        className={aperto ? "btn active" : className}
        onClick={() => setAperto((v) => !v)}
        title="Livelli di uscita calcolati dai dati della card: chandelier, SAR, strutturale, volatilità"
      >
        {aperto ? "Nascondi uscita" : "🛡 Uscita"}
      </button>

      {aperto ? (
        <div className="level-strip level-stop">
          <div className="level-title">USCITA · calcolata ora sul prezzo di oggi</div>
          {livelli.length ? (
            <>
              <div className="level-main uscita-righe">
                {livelli.map((l) => (
                  <span className="uscita-riga" key={`${l.nome}-${l.tipo}`}>
                    <span className="uscita-nome">{l.nome}</span>
                    <span className="uscita-tipo">{l.tipo}</span>
                    <b>{prezzo(l.livello)}</b>
                    <span className="uscita-dist">{l.distanzaPct.toFixed(2)}%</span>
                  </span>
                ))}
              </div>
              <div className="level-sub">
                Più stretto: <b>{stretto?.nome}</b> a {prezzo(stretto?.livello ?? 0)} ({stretto?.distanzaPct.toFixed(2)}%)
                {" · "}più ampio: <b>{ampio?.nome}</b> a {prezzo(ampio?.livello ?? 0)} ({ampio?.distanzaPct.toFixed(2)}%)
              </div>
            </>
          ) : (
            <div className="level-sub">Dati insufficienti per calcolare i livelli su questo titolo.</div>
          )}
          <div className="level-sub warn">
            Livelli misurati dal prezzo di oggi: senza il prezzo di carico non dicono se esci in profitto o in perdita.
          </div>
        </div>
      ) : null}
    </>
  );
}
