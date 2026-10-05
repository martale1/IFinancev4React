/**
 * Spiegazione del modello (assi, fasi, indicazione, TECH_SCORE).
 *
 * Vive in un componente solo perché la usano due posti — la legenda del tab All
 * e la guida della tab Indicatori — e una spiegazione duplicata diverge sempre
 * dal calcolo. I numeri qui sono quelli di `four_axes.py`: se cambiano le
 * soglie là, vanno cambiati qui (e il pannello Indicatori cita le stesse).
 */
export function AxesModelGuide() {
  return (
    <>
      <section className="indicators-guide-block">
        <h3>1 · I quattro assi (dove sta andando il titolo)</h3>
        <p className="indicators-guide-note">
          Ogni asse è indipendente e si legge da solo. Prima erano diciannove indicatori
          che confluivano in un unico numero, senza che si capisse da dove venisse.
        </p>
        <dl className="indicators-guide-details">
          <dt>Direzione</dt>
          <dd>
            <b>SU</b> prezzo sopra la media (EMA50) con pendenza, oppure ADX ≥ 22 ·
            {" "}<b>PIATTO</b> prezzo intorno alla media senza pendenza ·
            {" "}<b>GIU</b> sotto la media. Dice <i>dove</i> va, non quanto forte.
          </dd>
          <dt>Forza</dt>
          <dd>
            <b>FORTE SU / FORTE GIU</b> ADX ≥ 22 con DI+ e DI− orientati ·
            {" "}<b>DEBOLE</b> movimento poco convincente. È la forza del trend, non la sua direzione.
          </dd>
          <dt>Momento</dt>
          <dd>
            <b>CRESCENTE</b> l'istogramma MACD si allontana dallo zero ·
            {" "}<b>STABILE</b> fermo · <b>CALANTE</b> si avvicina.
            Misura <i>solo</i> il MACD: l'RSI può scendere mentre il momento sale.
          </dd>
          <dt>Rischio</dt>
          <dd>
            <b>NORMALE</b> · <b>TESO</b> se ATR ≥ 3% <i>oppure</i> distanza dalla media ≥ 5% ·
            {" "}<b>ESTREMO</b> se ATR ≥ 5% <i>oppure</i> distanza ≥ 9%.
            Dice quanto è teso il titolo, non quanto è buono.
          </dd>
        </dl>
      </section>

      <section className="indicators-guide-block">
        <h3>2 · Il TECH_SCORE (punteggio 0-100)</h3>
        <p className="indicators-guide-note">
          È la <b>somma visibile</b> dei quattro assi. Nessun peso occulto, nessuna media di
          indicatori ridondanti: a parità di assi il punteggio è sempre lo stesso.
        </p>
        <table className="indicators-guide-table">
          <thead>
            <tr><th>Asse</th><th>Valore</th><th>Punti</th></tr>
          </thead>
          <tbody>
            <tr><td>Direzione</td><td>SU · PIATTO · GIU</td><td>+60 · 0 · −60</td></tr>
            <tr><td>Forza</td><td>FORTE_SU · DEBOLE · FORTE_GIU</td><td>+35 · 0 · −35</td></tr>
            <tr><td>Momento</td><td>CRESCENTE · STABILE · CALANTE</td><td>+35 · 0 · −35</td></tr>
            <tr><td>Rischio</td><td>NORMALE · TESO · ESTREMO</td><td>0 · −10 · −20</td></tr>
          </tbody>
        </table>
        <p className="indicators-guide-note">
          <b>TECH_SCORE = 50 + somma × 50/150</b>, limitato a 0-100.<br />
          L'ancora è esatta: <b>50 = nessuna convinzione e nessun rischio</b> (titolo laterale, forza debole,
          momento stabile, rischio normale). La direzione pesa più di forza e momento perché è l'unica che
          dice <i>dove</i> si va; il rischio può solo abbassare il punteggio, mai alzarlo.
        </p>
        <p className="indicators-guide-note">
          Esempi: titolo fermo <b>50</b> · solo direzione su <b>70</b> · tendenza piena <b>93</b> ·
          tendenza piena ma estremamente estesa <b>87</b> · ribasso pieno <b>7</b>.
        </p>
      </section>

      <section className="indicators-guide-block">
        <h3>3 · La fase di mercato</h3>
        <p className="indicators-guide-note">
          Quattro casi, decisi dalla sola combinazione di direzione, forza e momento.
        </p>
        <table className="indicators-guide-table">
          <thead>
            <tr><th>Fase</th><th>Quando</th><th>Significato</th></tr>
          </thead>
          <tbody>
            <tr><td><b>TENDENZA</b></td><td>direzione SU + forza FORTE + momento non calante</td><td>tre fattori allineati verso l'alto</td></tr>
            <tr><td><b>RIPRESA</b></td><td>direzione SU, ma senza ancora la forza (o con momento calante)</td><td>rialzo in formazione, da confermare</td></tr>
            <tr><td><b>LATERALE</b></td><td>direzione PIATTO</td><td>il prezzo non va da nessuna parte</td></tr>
            <tr><td><b>RIBASSO</b></td><td>direzione GIU</td><td>il prezzo è sotto la media</td></tr>
          </tbody>
        </table>
        <p className="indicators-guide-note">
          <b>Attento a non confondere fase e indicazione.</b> La fase descrive <i>dove</i> è il titolo,
          l'indicazione dice <i>cosa fare</i>. Un titolo può essere in TENDENZA e meritare comunque
          ATTENDI: succede quando è troppo esteso (rischio TESO o ESTREMO) o quando la liquidità non è OK.
          È il caso più importante da riconoscere: il trend c'è, l'ingresso no.
        </p>
      </section>

      <section className="indicators-guide-block">
        <h3>4 · L'indicazione operativa</h3>
        <table className="indicators-guide-table">
          <thead>
            <tr><th>Indicazione</th><th>Quando</th></tr>
          </thead>
          <tbody>
            <tr><td><b>ENTRA</b></td><td>fase TENDENZA, momento non calante, rischio NORMALE</td></tr>
            <tr><td><b>OSSERVA</b></td><td>fase RIPRESA, oppure direzione SU con momento CRESCENTE</td></tr>
            <tr><td><b>EVITA</b></td><td>fase RIBASSO con forza FORTE_GIU</td></tr>
            <tr><td><b>ATTENDI</b></td><td>tutti gli altri casi (laterale, o tendenza troppo tesa)</td></tr>
          </tbody>
        </table>
        <p className="indicators-guide-note">
          Nota: il solo momento crescente <b>non</b> basta per OSSERVA — serve anche una direzione
          rialzista. Senza questo vincolo, in laterale si promuoveva a OSSERVA oltre un terzo dei titoli.
        </p>
      </section>

      <section className="indicators-guide-block">
        <h3>5 · La liquidità e la riga "Manca: …"</h3>
        <ul className="indicators-guide-suffixes">
          <li><b>LIQ OK / LOW / AVOID</b> — con <b>AVOID</b> il titolo è escluso dalle indicazioni; con <b>LOW</b> resta in attesa. Il controllo della liquidità viene prima di ogni altro.</li>
          <li><b>Manca: …</b> — le condizioni del trigger di acquisto non ancora soddisfatte, con il valore attuale (per esempio <i>ADX ≥ 20, ora 18,9</i>), così si vede quanto manca.</li>
          <li>Se la fase è <b>LATERALE</b> la riga mostra <i>solo</i> quel blocco: nessuna condizione tecnica può sbloccare il segnale finché manca una direzione. Elencare le altre suggerirebbe un progresso che non esiste.</li>
          <li>Se la fase è <b>RIBASSO</b> la diagnosi è vuota: il motivo è già nel segnale EVITA, con la struttura fragile come spiegazione.</li>
        </ul>
      </section>
    </>
  );
}
