/**
 * Cruscotto degli Highlights: quattro blocchi che dicono cosa guardare.
 *
 * Sta accanto alla pagina precedente, non al suo posto: si sceglie con un
 * pulsante, cosi' si giudica sui titoli veri invece che su una descrizione.
 *
 * I blocchi rispondono a quattro domande diverse, e per questo non sono una
 * classifica unica:
 *   - Pronti adesso      -> cosa posso fare oggi
 *   - A un passo         -> cosa sto per poter fare, e cosa manca
 *   - Forti ma frenati   -> cosa e' valido ma non ancora operabile
 *   - Nuovi oggi         -> cosa e' cambiato rispetto a ieri
 */
import { useMemo, useState } from "react";

import { aUnPasso, fortiMaFrenati, prontiAdesso, type VoceHighlight } from "../highlights";
import { toNum } from "../format";
import type { WatchlistRow } from "../types";

/** Una riga di titolo dentro un blocco: cliccabile per aprire il grafico. */
function RigaVoce({ voce, onChart }: { voce: VoceHighlight; onChart: (row: WatchlistRow) => void }) {
  const score = toNum(voce.row.TECH_SCORE);
  return (
    <button type="button" className="hl-riga" onClick={() => onChart(voce.row)} title="Apri il grafico">
      <span className="hl-ticker">{voce.ticker}</span>
      <span className="hl-nome">{voce.nome || "—"}</span>
      {score !== null ? <span className="hl-score">TECH {Math.round(score)}</span> : null}
      <span className="hl-motivo">{voce.motivo}</span>
    </button>
  );
}

/** Un blocco: titolo, conteggio, spiegazione e righe. */
function Blocco({
  titolo,
  sottotitolo,
  voci,
  vuoto,
  onChart,
}: {
  titolo: string;
  sottotitolo: string;
  voci: VoceHighlight[] | null;
  vuoto: string;
  onChart: (row: WatchlistRow) => void;
}) {
  return (
    <section className="hl-blocco">
      <header className="hl-blocco-testata">
        <h3>
          {titolo}
          {voci ? <b className="hl-conteggio">{voci.length}</b> : null}
        </h3>
        <p>{sottotitolo}</p>
      </header>
      {voci === null ? (
        <p className="hl-vuoto">{vuoto}</p>
      ) : voci.length === 0 ? (
        <p className="hl-vuoto">{vuoto}</p>
      ) : (
        <div className="hl-righe">
          {voci.map((v) => (
            <RigaVoce key={v.ticker} voce={v} onChart={onChart} />
          ))}
        </div>
      )}
    </section>
  );
}

export default function HighlightsDashboard({
  righe,
  onChart,
}: {
  righe: WatchlistRow[];
  onChart: (row: WatchlistRow) => void;
}) {
  const [mostraTuttiFrenati, setMostraTuttiFrenati] = useState(false);

  const pronti = useMemo(() => prontiAdesso(righe), [righe]);
  const passo = useMemo(() => aUnPasso(righe), [righe]);
  const frenati = useMemo(() => {
    // Ogni titolo in un blocco solo: chi e' gia' "pronto" o "a un passo" non
    // ricompare qui. Senza questo, CPR.MI (TECH 90 e a un passo) stava in due.
    const gia = new Set<string>([...pronti, ...passo].map((v) => v.ticker));
    return fortiMaFrenati(righe, gia);
  }, [righe, pronti, passo]);

  return (
    <div className="hl-cruscotto">
      <Blocco
        titolo="Pronti adesso"
        sottotitolo="Tutti e tre i requisiti soddisfatti: direzione su, forza confermata, rischio normale."
        voci={pronti}
        vuoto="Nessun titolo pronto in questo momento."
        onChart={onChart}
      />

      <Blocco
        titolo="A un passo"
        sottotitolo="Manca una sola condizione: il numero accanto dice il livello che serve per rientrare."
        voci={passo}
        vuoto="Nessun titolo vicino all'ingresso."
        onChart={onChart}
      />

      <section className="hl-blocco">
        <header className="hl-blocco-testata">
          <h3>
            Forti ma frenati
            <b className="hl-conteggio">{frenati.reduce((n, g) => n + g.voci.length, 0)}</b>
          </h3>
          <p>TECH_SCORE alto ma non operabili: raggruppati per il freno, che dice cosa aspettare.</p>
        </header>
        {frenati.length === 0 ? (
          <p className="hl-vuoto">Nessun titolo forte bloccato da un freno.</p>
        ) : (
          <div className="hl-gruppi">
            {(mostraTuttiFrenati ? frenati : frenati.slice(0, 3)).map((g) => (
              <div className="hl-gruppo" key={g.freno}>
                <div className="hl-gruppo-titolo">
                  {g.freno} <b>{g.voci.length}</b>
                </div>
                {g.voci.slice(0, 3).map((v) => (
                  <RigaVoce key={v.ticker} voce={v} onChart={onChart} />
                ))}
              </div>
            ))}
            {frenati.length > 3 ? (
              <button type="button" className="btn ghost hl-altri" onClick={() => setMostraTuttiFrenati((v) => !v)}>
                {mostraTuttiFrenati ? "Mostra solo i primi tre" : `Mostra tutti i ${frenati.length} freni`}
              </button>
            ) : null}
          </div>
        )}
      </section>

      <section className="hl-blocco">
        <header className="hl-blocco-testata">
          <h3>Nuovi oggi</h3>
          <p>Cosa è cambiato rispetto alla seduta precedente: titoli entrati in tendenza, passati a osservazione, pattern scattati.</p>
        </header>
        <p className="hl-vuoto">
          Non ancora disponibile: serve ricordare lo stato della seduta precedente. L&apos;analisi è una fotografia
          dell&apos;ultima seduta, quindi il confronto richiede un file di stato aggiornato a ogni analisi.
        </p>
      </section>
    </div>
  );
}
