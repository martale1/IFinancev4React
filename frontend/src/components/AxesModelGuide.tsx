/**
 * Spiegazione del modello: una tabella sola, con le quattro indicazioni.
 *
 * PRIMA erano sei sezioni (assi, TECH_SCORE, fasi, indicazione, liquidita',
 * tutte le diciture) e due di esse ripetevano le stesse cose: per rispondere a
 * una domanda sola — "cosa significa OSSERVA?" — si dovevano attraversare ~200
 * righe.
 *
 * ORA c'e' una tabella: ogni riga e' un'indicazione, con la sua regola e cosa
 * manca per passare a ENTRA. E' la forma piu' corta che tiene tutte le
 * informazioni, e su telefono si scorre invece di leggere.
 *
 * Le regole sono quelle di `four_axes.py` (compute_axes, phase_from_axes,
 * indication_from_axes): se cambiano le soglie la', vanno cambiate qui.
 * Verificato sul codice e su 996 titoli: le quattro indicazioni si escludono
 * sempre a vicenda, quindi non c'e' un ordine di priorita' da ricordare.
 *
 * Il TECH_SCORE non compare di proposito: e' un riassunto numerico da 0 a 100 e
 * NON decide l'indicazione (la soglia `tech_buy: 65` in four_axes.py non viene
 * applicata da nessuna parte). Citarlo faceva credere il contrario.
 */

const CONDIZIONI: {
  indicazione: string;
  emoji: string;
  classe: string;
  significato: string;
  regola: string;
  manca: string;
}[] = [
  {
    indicazione: "ENTRA",
    emoji: "🟢",
    classe: "guida-entra",
    significato: "valuta l'ingresso",
    regola: "direzione SU + forza FORTE_SU + momento non CALANTE + rischio NORMALE",
    manca: "è la condizione piena: non manca nulla",
  },
  {
    indicazione: "OSSERVA",
    emoji: "🔵",
    classe: "guida-osserva",
    significato: "sale, ma non è pronto",
    regola: "direzione SU, oppure fase RIPRESA",
    manca: "che la forza arrivi a FORTE_SU (ADX ≥ 22) e il rischio torni NORMALE (ATR < 3%), senza che il momento diventi CALANTE",
  },
  {
    indicazione: "ATTENDI",
    emoji: "⚪",
    classe: "guida-attendi",
    significato: "fermo, laterale",
    regola: "direzione PIATTA",
    manca: "che la direzione diventi SU",
  },
  {
    indicazione: "EVITA",
    emoji: "🔴",
    classe: "guida-evita",
    significato: "scende con forza",
    regola: "direzione GIU + forza FORTE_GIU",
    manca: "che la direzione torni SU e la forza non sia più FORTE_GIU",
  },
];

export function AxesModelGuide() {
  return (
    <>
      <table className="guida-tabella">
        <thead>
          <tr>
            <th>Indicazione</th>
            <th>Significato</th>
            <th>La regola</th>
            <th>Cosa manca per passare a 🟢 ENTRA</th>
          </tr>
        </thead>
        <tbody>
          {CONDIZIONI.map((c) => (
            <tr key={c.indicazione}>
              <td className={c.classe} data-etichetta="Indicazione">
                {c.emoji} <b>{c.indicazione}</b>
              </td>
              <td data-etichetta="Significato">{c.significato}</td>
              <td data-etichetta="La regola">{c.regola}</td>
              <td data-etichetta="Cosa manca per ENTRA">{c.manca}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Le parole usate nelle regole: senza queste la tabella non si legge.
          Una riga sola, non una sezione. */}
      <p className="guida-parole">
        Le quattro <b>si escludono sempre</b> a vicenda. Le parole delle regole:{" "}
        <b>SU</b> / <b>GIU</b> / <b>PIATTA</b> = prezzo sopra / sotto / sulla EMA50 ·{" "}
        <b>FORTE_SU</b> / <b>FORTE_GIU</b> = ADX ≥ 22 con DI+ o DI− prevalente ·{" "}
        <b>CRESCENTE</b> / <b>STABILE</b> / <b>CALANTE</b> = MACD rispetto a 3 sedute fa ·{" "}
        <b>NORMALE</b> / <b>TESO</b> / <b>ESTREMO</b> = ATR o distanza dalla media (da 3% teso,
        da 5% estremo).
      </p>
    </>
  );
}
