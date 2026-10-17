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
import { signalClass, toNum } from "../format";
import type { WatchlistRow } from "../types";
import type { Cambio } from "../api";

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

/** Variazione percentuale con la virgola italiana.
 *
 * PERCHE': nel resto dell'app i numeri usano la virgola (qui il prezzo e'
 * "50,42"), ma in questo blocco le percentuali uscivano con il punto
 * ("+4.73%"). Due formati nella stessa riga si leggono male. */
function percentuale(valore: number): string {
  const segno = valore > 0 ? "+" : "";
  return `${segno}${valore.toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

/** Una riga di titolo dentro un blocco: cliccabile per il grafico, con il
 *  pulsante per il monitoraggio. */
function RigaVoce({
  voce,
  onScheda,
  onMonitor,
  inMonitor,
}: {
  voce: VoceHighlight;
  onScheda: (row: WatchlistRow) => void;
  onMonitor: (row: WatchlistRow) => void;
  /** Gia' in monitoraggio: il pulsante si evidenzia e un clic lo toglie. */
  inMonitor: boolean;
}) {
  // Le condizioni stanno chiuse: la riga resta bassa. Chi le vuole le apre
  // con il triangolino, una riga alla volta.
  const [mostraCondizioni, setMostraCondizioni] = useState(false);
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
      onClick={() => onScheda(voce.row)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onScheda(voce.row);
        }
      }}
      title="Apri la scheda del titolo"
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
        {voce.motivo ? (
          <button
            type="button"
            className={mostraCondizioni ? "hl-condizioni aperta" : "hl-condizioni"}
            aria-expanded={mostraCondizioni}
            aria-label={mostraCondizioni ? "Nascondi le condizioni" : "Mostra le condizioni"}
            onClick={(e) => {
              e.stopPropagation();
              setMostraCondizioni((v) => !v);
            }}
            title={mostraCondizioni ? "Nascondi le condizioni" : "Mostra le condizioni verificate"}
          >
            {mostraCondizioni ? "▾" : "▸"}
          </button>
        ) : null}
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
                  : `Variazione a ${v.label}: ${percentuale(v.valore)}`
              }
            >
              <small>{v.label}</small>
              <b className={v.valore === null ? "neutral" : v.valore > 0 ? "positive" : v.valore < 0 ? "negative" : "neutral"}>
                {v.valore === null ? "—" : percentuale(v.valore)}
              </b>
            </span>
          ))}
        </span>
      ) : null}

      {/* Le condizioni, quando le apri: qui si legge la frase intera, che e' il
          motivo per cui il titolo e' (o non e') pronto. */}
      {mostraCondizioni && voce.motivo ? (
        <span className="hl-motivo">{voce.motivo}</span>
      ) : null}
    </div>
  );
}

/** Un blocco: titolo, conteggio TOTALE, spiegazione e righe. */
function Blocco({
  titolo,
  sottotitolo,
  voci,
  vuoto,
  onScheda,
  onMonitor,
  onIsMonitored,
}: {
  titolo: string;
  sottotitolo: string;
  voci: VoceHighlight[] | null;
  vuoto: string;
  onScheda: (row: WatchlistRow) => void;
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
              <RigaVoce key={v.ticker} voce={v} onScheda={onScheda} onMonitor={onMonitor} inMonitor={onIsMonitored(v.row)} />
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
  onScheda,
  onMonitor,
  onIsMonitored,
  cambi,
  cambiData,
}: {
  righe: WatchlistRow[];
  onScheda: (row: WatchlistRow) => void;
  onMonitor: (row: WatchlistRow) => void;
  onIsMonitored: (row: WatchlistRow) => boolean;
  /** Cosa e' cambiato rispetto alla seduta precedente. */
  cambi: Cambio[];
  /** Data dell'analisi a cui si riferiscono i cambiamenti. */
  cambiData: string;
}) {
  const [mostraTuttiFrenati, setMostraTuttiFrenati] = useState(false);
  const [mostraTuttiCambi, setMostraTuttiCambi] = useState(false);

  const pronti = useMemo(() => prontiAdesso(righe), [righe]);
  const passo = useMemo(() => aUnPasso(righe), [righe]);
  const frenati = useMemo(() => {
    // Ogni titolo in un blocco solo: chi e' gia' "pronto" o "a un passo" non
    // ricompare qui. Senza questo, CPR.MI (TECH 90 e a un passo) stava in due.
    const gia = new Set<string>([...pronti, ...passo].map((v) => v.ticker));
    return fortiMaFrenati(righe, gia);
  }, [righe, pronti, passo]);

  // Per aprire il grafico da un cambiamento serve la riga completa del titolo.
  const perTicker = useMemo(() => {
    const mappa = new Map<string, WatchlistRow>();
    for (const riga of righe) {
      const tk = String(riga.Ticker ?? "").toUpperCase();
      if (tk) mappa.set(tk, riga);
    }
    return mappa;
  }, [righe]);

  const totaleFrenati = frenati.reduce((n, g) => n + g.voci.length, 0);
  const gruppiVisibili = mostraTuttiFrenati ? frenati : frenati.slice(0, 3);

  return (
    <div className="hl-cruscotto">
      <Blocco
        titolo="Pronti adesso"
        sottotitolo="Tutti e tre i requisiti soddisfatti: direzione su, forza confermata, rischio normale."
        voci={pronti}
        vuoto="Nessun titolo pronto in questo momento."
        onScheda={onScheda}
        onMonitor={onMonitor}
        onIsMonitored={onIsMonitored}
      />

      <Blocco
        titolo="A un passo"
        sottotitolo="Manca una sola condizione: il numero accanto dice il livello che serve per rientrare."
        voci={passo}
        vuoto="Nessun titolo vicino all'ingresso."
        onScheda={onScheda}
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
                    <RigaVoce key={v.ticker} voce={v} onScheda={onScheda} onMonitor={onMonitor} inMonitor={onIsMonitored(v.row)} />
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
          <h3>
            Nuovi oggi
            {cambi.length ? <b className="hl-conteggio">{cambi.length}</b> : null}
          </h3>
          <p>
            Cosa è cambiato rispetto alla seduta precedente
            {cambiData ? ` (analisi del ${cambiData})` : ""}: indicazioni cambiate, fasi nuove, pattern scattati.
          </p>
        </header>
        {cambi.length === 0 ? (
          <p className="hl-vuoto">
            Nessun cambiamento rispetto alla seduta precedente. Il confronto si attiva quando arriva una nuova
            analisi: se è la prima volta, la seduta in corso fa da riferimento per la prossima.
          </p>
        ) : (
          <div className="hl-righe">
            {(mostraTuttiCambi ? cambi : cambi.slice(0, 6)).map((c) => {
              const riga = perTicker.get(c.ticker.toUpperCase());
              const stato = String(c.indicazione ?? riga?.Entry_Signal ?? "").trim().toUpperCase();
              // Il grafico si apre solo se il titolo e' fra le righe caricate:
              // senza riga non ci sarebbe nulla da mostrare.
              const apribile = Boolean(riga);
              return (
                <div
                  className={`hl-riga hl-cambio ${apribile ? "apribile" : ""}`}
                  key={`${c.market ?? ""}-${c.ticker}-${c.tipo}`}
                  role={apribile ? "button" : undefined}
                  tabIndex={apribile ? 0 : undefined}
                  onClick={apribile && riga ? () => onScheda(riga) : undefined}
                  onKeyDown={
                    apribile && riga
                      ? (e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            onScheda(riga);
                          }
                        }
                      : undefined
                  }
                  title={apribile ? "Apri la scheda del titolo" : undefined}
                >
                  <span className="hl-ticker">{c.ticker}</span>
                  {/* Solo l'indicazione, con il badge della pagina Monitor:
                      "ATTENDI PATTERN" era rumore — il tipo si legge nel testo. */}
                  {stato ? (
                    <span className={`table-signal ${signalClass(stato)}`}>{stato}</span>
                  ) : null}
                  <span className="hl-cambi-testo">{c.testo}</span>
                </div>
              );
            })}
          </div>
        )}
        {cambi.length > 6 ? (
          <button type="button" className="btn ghost hl-altri" onClick={() => setMostraTuttiCambi((v) => !v)}>
            {mostraTuttiCambi ? "Mostra solo i primi 6" : `Mostra tutti i ${cambi.length}`}
          </button>
        ) : null}
      </section>
    </div>
  );
}
