/**
 * Piè di pagina con la provenienza dei dati: file Excel e ora dell'analisi.
 *
 * Sta in fondo a ogni pagina perche' e' l'informazione che serve per giudicare
 * tutto il resto: le indicazioni che leggi valgono quanto l'analisi da cui
 * vengono. Prima stava sotto la Guida, dove si vede solo in una tab; qui invece
 * e' sempre raggiungibile, e non ripete nulla perche' la Guida non la mostra piu'.
 *
 * Il percorso e' mostrato come SOLO NOME DEL FILE: il percorso intero
 * ("C:\\Users\\...\\ETF_TA_Analyses.xlsx") non aggiunge informazione e su
 * telefono occupa tre righe. Il percorso completo resta nel suggerimento.
 */
export default function FooterAnalisi({
  percorso,
  ts,
}: {
  /** Percorso del file, come lo restituisce il backend. */
  percorso?: string | null;
  /** Ora dell'analisi (ISO o gia' formattata). */
  ts?: string | null;
}) {
  // Senza dati non si mostra nulla: meglio niente che un piè di pagina vuoto.
  if (!percorso && !ts) return null;

  const soloNome = (percorso || "").split(/[\\/]/).pop() || "";

  return (
    <footer className="app-footer">
      {soloNome ? (
        <span className="app-footer-voce" title={percorso ?? undefined}>
          <b>Analisi</b> {soloNome}
        </span>
      ) : null}
      {ts ? (
        <span className="app-footer-voce">
          <b>Ora</b> {ts}
        </span>
      ) : null}
    </footer>
  );
}

