/**
 * Cruscotto degli Highlights: quattro blocchi che dicono cosa guardare.
 *
 * I blocchi ricevono TUTTI i titoli e decidono qui quante righe mostrarne: il
 * conteggio nella casella e' il totale vero. Prima il taglio avveniva nei dati e
 * il numero mostrava le righe visibili (massimo 5), quindi in "MIB30 + DAX" non
 * era la somma di MIB30 e DAX.
 *
 * Ogni riga apre il grafico; il pulsante `+ Monitor` la aggiunge al monitoraggio
 * senza aprire il grafico.
 */
import { useMemo, useState } from "react";

import { aUnPasso, fortiMaFrenati, prontiAdesso, type VoceHighlight } from "../highlights";
import { toNum } from "../format";
import type { WatchlistRow } from "../types";

/** Righe visibili per blocco prima di "mostra tutti". */
const VISIBILI = 5;
/** Righe visibili per gruppo, nei "forti ma frenati". */
const VISIBILI_GRUPPO = 3;

/**
 * Le variazioni percentuali mostrate su ogni riga: 1, 5, 10 e 30 sedute.
 *
 * Sono le stesse colonne che il backend calcola da sempre (`PCTV_1D` e simili) e
 * che la card della tab All mostra gia': qui servono perche' il motivo da solo
 * dice cosa manca, non come si sta muovendo il titolo.
 */
const VARIAZIONI: Array<{ key: string; label: string }> = [
  { key: "PCTV_1D", label: "1D" },
  { key: "PCTV_5D", label: "5D" },
  { key: "PCTV_10D", label: "10D" },
  { key: "PCTV_30D", label: "30D" },
];

/** Prezzo con i decimali che servono: le cifre piccole (ETF a 0,64) sparirebbero
 *  con due soli decimali, i titoli grandi non ne vogliono tre. */
function prezzo(valore: number): string {
  const dec = Math.abs(valore) < 5 ? 3 : 2;
  return valore.toLocaleString("it-IT", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

/** Una riga di titolo dentro un blocco: cliccabile per il grafico, con il
 *  pulsante per il monitoraggio. */
function RigaVoce({
  voce,
  onChart,
  onMonitor,
  inMonitor,
}: {
  voce: VoceHighlight;
  onChart: (row: WatchlistRow) => void;
  onMonitor: (row: WatchlistRow) => void;
  /** Gia' in monitoraggio: il pulsante si evidenzia e un clic lo toglie. */
  inMonitor: boolean;
}) {
  const score = toNum(voce.row.TECH_SCORE);
  const chiusura = toNum(voce.row.Close);
  const variazioni = VARIAZIONI.map((v) => ({ ...v, valore: toNum(voce.row[v.key]) }));
  const qualcuna = variazioni.some((v) => v.valore !== null);

  return (
    // Un div e non un button: dentro c'e' un altro pulsante, e un bottone dentro
    // un bottone non e' valido. Il clic sulla riga apre il grafico; il pulsante
    // Monitor ferma la propagazione.
    <div
      className="hl-riga"
      role="button"
      tabIndex={0}
      onClick={() => onChart(voce.row)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onChart(voce.row);
        }
      }}
      title="Apri il grafico"
    >
      <span className="hl-ticker">{voce.ticker}</span>
      <span className="hl-nome">{voce.nome || "—"}</span>
      {chiusura !== null ? <span className="hl-prezzo">{prezzo(chiusura)}</span> : null}

      <span className="hl-azioni">
        {score !== null ? <span className="hl-score">TECH {Math.round(score)}</span> : null}
        <button
          type="button"
          className={inMonitor ? "hl-monitor attivo" : "hl-monitor"}
          onClick={(e) => {
            e.stopPropagation();
            onMonitor(voce.row);
          }}
          title={inMonitor ? "Già in monitoraggio: clicca per toglierlo" : "Aggiungi al monitoraggio"}
        >
          {inMonitor ? "✓ Monitor" : "+ Monitor"}
        </button>
      </span>

      {qualcuna ? (
        <span className="hl-variazioni">
          {variazioni.map((v) => (
            <span
              className="hl-var"
              key={v.key}
              title={
                v.valore === null
                  ? `Variazione ${v.label}: non disponibile`
                  : `Variazione a ${v.label}: ${v.valore >= 0 ? "+" : ""}${v.valore.toFixed(2)}%`
              }
            >
              <small>{v.label}</small>
              <b className={v.valore === null ? "neutral" : v.valore > 0 ? "positive" : v.valore < 0 ? "negative" : "neutral"}>
                {v.valore === null ? "—" : `${v.valore >= 0 ? "+" : ""}${v.valore.toFixed(2)}%`}
              </b>
            </span>
          ))}
        </span>
      ) : null}

      <span className="hl-motivo">{voce.motivo}</span>
    </div>
  );
}

/** Un blocco: titolo, conteggio TOTALE, spiegazione e righe. */
function Blocco({
  titolo,
  sottotitolo,
  voci,
  vuoto,
  onChart,
  onMonitor,
  onIsMonitored,
}: {
  titolo: string;
  sottotitolo: string;
  voci: VoceHighlight[] | null;
  vuoto: string;
  onChart: (row: WatchlistRow) => void;
  onMonitor: (row: WatchlistRow) => void;
  onIsMonitored: (row: WatchlistRow) => boolean;
}) {
  const [espanso, setEspanso] = useState(false);
  const totale = voci ? voci.length : 0;
  const visibili = voci ? (espanso ? voci : voci.slice(0, VISIBILI)) : [];
  const resto = totale - visibili.length;

  return (
    <section className="hl-blocco">
      <header className="hl-blocco-testata">
        <h3>
          {titolo}
          {voci ? <b className="hl-conteggio">{totale}</b> : null}
        </h3>
        <p>{sottotitolo}</p>
      </header>
      {voci === null || totale === 0 ? (
        <p className="hl-vuoto">{vuoto}</p>
      ) : (
        <>
          <div className="hl-righe">
            {visibili.map((v) => (
              <RigaVoce key={v.ticker} voce={v} onChart={onChart} onMonitor={onMonitor} inMonitor={onIsMonitored(v.row)} />
            ))}
          </div>
          {resto > 0 ? (
            <button type="button" className="btn ghost hl-altri" onClick={() => setEspanso((x) => !x)}>
              {espanso ? `Mostra solo ${VISIBILI}` : `Mostra tutti i ${totale} (altri ${resto})`}
            </button>
          ) : null}
        </>
      )}
    </section>
  );
}

export default function HighlightsDashboard({
  righe,
  onChart,
  onMonitor,
  onIsMonitored,
}: {
  righe: WatchlistRow[];
  onChart: (row: WatchlistRow) => void;
  onMonitor: (row: WatchlistRow) => void;
  onIsMonitored: (row: WatchlistRow) => boolean;
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

  const totaleFrenati = frenati.reduce((n, g) => n + g.voci.length, 0);
  const gruppiVisibili = mostraTuttiFrenati ? frenati : frenati.slice(0, 3);

  return (
    <div className="hl-cruscotto">
      <Blocco
        titolo="Pronti adesso"
        sottotitolo="Tutti e tre i requisiti soddisfatti: direzione su, forza confermata, rischio normale."
        voci={pronti}
        vuoto="Nessun titolo pronto in questo momento."
        onChart={onChart}
        onMonitor={onMonitor}
        onIsMonitored={onIsMonitored}
      />

      <Blocco
        titolo="A un passo"
        sottotitolo="Manca una sola condizione: il numero accanto dice il livello che serve per rientrare."
        voci={passo}
        vuoto="Nessun titolo vicino all'ingresso."
        onChart={onChart}
        onMonitor={onMonitor}
        onIsMonitored={onIsMonitored}
      />

      <section className="hl-blocco">
        <header className="hl-blocco-testata">
          <h3>
            Forti ma frenati
            <b className="hl-conteggio">{totaleFrenati}</b>
          </h3>
          <p>TECH_SCORE alto ma non operabili: raggruppati per il freno, che dice cosa aspettare.</p>
        </header>
        {frenati.length === 0 ? (
          <p className="hl-vuoto">Nessun titolo forte bloccato da un freno.</p>
        ) : (
          <div className="hl-gruppi">
            {gruppiVisibili.map((g) => {
              const dentro = mostraTuttiFrenati ? g.voci : g.voci.slice(0, VISIBILI_GRUPPO);
              return (
                <div className="hl-gruppo" key={g.freno}>
                  <div className="hl-gruppo-titolo">
                    {g.freno} <b>{g.voci.length}</b>
                  </div>
                  {dentro.map((v) => (
                    <RigaVoce key={v.ticker} voce={v} onChart={onChart} onMonitor={onMonitor} inMonitor={onIsMonitored(v.row)} />
                  ))}
                </div>
              );
            })}
            {frenati.length > 3 || frenati.some((g) => g.voci.length > VISIBILI_GRUPPO) ? (
              <button type="button" className="btn ghost hl-altri" onClick={() => setMostraTuttiFrenati((v) => !v)}>
                {mostraTuttiFrenati ? "Mostra solo i primi" : `Mostra tutti (${totaleFrenati} titoli, ${frenati.length} freni)`}
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
