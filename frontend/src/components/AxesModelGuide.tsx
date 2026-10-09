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
      <p className="indicators-guide-intro">
        <b>Lettura veloce:</b> la prima etichetta risponde a una sola domanda —
        <b>conviene valutare un nuovo ingresso?</b> Fase e dettaglio tecnico spiegano il
        contesto, ma non sono comandi operativi.
      </p>

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

      <section className="indicators-guide-block">
        <h3>6 · Tutte le diciture delle card</h3>
        <p className="indicators-guide-note">
          Ogni card è divisa in quattro gruppi. Qui c'è cosa significa ogni voce,
          con la scala dei valori.
        </p>

        <h4 className="indicators-guide-sub">Gruppo TREND — direzione e forza</h4>
        <table className="indicators-guide-table">
          <thead><tr><th>Voce</th><th>Cosa significa</th></tr></thead>
          <tbody>
            <tr><td><b>Direzione</b></td><td><b>SU</b> prezzo sopra la media · <b>PIATTO</b> intorno alla media · <b>GIU</b> sotto</td></tr>
            <tr><td><b>Forza</b></td><td><b>FORTE SU / FORTE GIU</b> movimento convinto (ADX ≥ 22) · <b>DEBOLE</b> poco convincente</td></tr>
            <tr><td><b>ADX</b></td><td>Quanta tendenza c'è, da 0 a 100, <i>senza direzione</i>. Sotto 20 mercato piatto, sopra 25 tendenza definita.</td></tr>
            <tr><td><b>DI+ / DI−</b></td><td>Spinta dei compratori (DI+) e dei venditori (DI−). Se DI+ supera DI− comanda la parte rialzista.</td></tr>
            <tr><td><b>SARMA</b></td><td>Da quante sedute il Parabolic SAR sta dalla stessa parte del prezzo. <b>0</b> = SAR sopra il prezzo (segnale ribassista); <b>1, 2, 3…</b> = SAR sotto, da altrettante sedute (rialzista).</td></tr>
          </tbody>
        </table>

        <h4 className="indicators-guide-sub">Gruppo MOMENTUM — sta accelerando o frenando</h4>
        <table className="indicators-guide-table">
          <thead><tr><th>Voce</th><th>Cosa significa</th></tr></thead>
          <tbody>
            <tr><td><b>Momento</b></td><td><b>CRESCENTE</b> · <b>STABILE</b> · <b>CALANTE</b>, misurato <i>solo</i> sul MACD</td></tr>
            <tr><td><b>RSI</b></td><td>Forza relativa, da 0 a 100. Sopra 70 il titolo è comprato in eccesso, sotto 30 venduto in eccesso. Il valore 50 è equilibrio.</td></tr>
            <tr><td><b>Stoch K/D</b></td><td>Posizione del prezzo nel range recente, da 0 a 100. La K è la linea veloce, la D quella lenta: K sopra D indica spinta rialzista. Sopra 80 eccesso di acquisti, sotto 20 di vendite.</td></tr>
            <tr><td><b>willR</b></td><td>Williams %R, da −100 a 0. Vicino a 0 il prezzo è in alto nel range, vicino a −100 in basso. È l'opposto dell'RSI per come si legge.</td></tr>
            <tr><td><b>MACD−Signal</b></td><td>Da quante sedute il MACD è sopra (positivo) o sotto (negativo) la sua linea di segnale. Piccolo e positivo = incrocio recente; grande = movimento maturo.</td></tr>
            <tr><td><b>Alligator</b></td><td>Stato delle tre medie di Bill Williams: <b>sleep1/sleep2</b> = mercato addormentato, <b>wakeup1/wakeup2</b> = si sta svegliando, <b>Uptrend / Downtrend</b> = bocca aperta in trend. Gli asterischi e i trattini indicano la variante, <b>_revS3Sig</b> che è comparsa una divergenza.</td></tr>
          </tbody>
        </table>

        <h4 className="indicators-guide-sub">Gruppo PERFORMANCE — come si è mosso</h4>
        <table className="indicators-guide-table">
          <thead><tr><th>Voce</th><th>Cosa significa</th></tr></thead>
          <tbody>
            <tr><td><b>1D · 5D · 10D · 30D · 180D</b></td><td>Variazione percentuale del prezzo su 1, 5, 10, 30 e 180 sedute.</td></tr>
            <tr><td><b>TECH</b></td><td>Il punteggio 0-100 spiegato al punto 2. <b>50 = né convinzione né rischio</b>; sopra 65 sostegno rialzista, sotto 35 debolezza.</td></tr>
            <tr><td><b>VOL</b></td><td>Volume scambiato nell'ultima seduta (M = milioni, K = migliaia).</td></tr>
          </tbody>
        </table>

        <h4 className="indicators-guide-sub">Gruppo CONTESTO — tensioni e pattern</h4>
        <table className="indicators-guide-table">
          <thead><tr><th>Voce</th><th>Cosa significa</th></tr></thead>
          <tbody>
            <tr><td><b>Rischio</b></td><td><b>NORMALE</b> · <b>TESO</b> · <b>ESTREMO</b>: quanto è teso il titolo per volatilità e distanza dalla media (soglie al punto 1).</td></tr>
            <tr><td><b>TENDENZA / RIPRESA / LATERALE / RIBASSO</b></td><td>La fase di mercato (punto 3).</td></tr>
            <tr><td><b>S2 · S3 · S4 · S8</b></td><td>Anzianità dell'ultimo pattern di quel tipo, in sedute: <b>0g</b> = scattato oggi. Per esempio <b>S3 5g fa</b> significa che il pattern S3 è comparso cinque sedute fa. Sono pattern sperimentali, spiegati nella scheda *Multi-Pattern Lab*.</td></tr>
          </tbody>
        </table>

        <h4 className="indicators-guide-sub">Le tre righe di stato in alto</h4>
        <table className="indicators-guide-table">
          <thead><tr><th>Voce</th><th>Cosa significa</th></tr></thead>
          <tbody>
            <tr><td><b>ENTRA / OSSERVA / ATTENDI / EVITA</b></td><td>L'indicazione operativa (punto 4): è la sola che dice <i>cosa fare</i>.</td></tr>
            <tr><td><b>Fase · Dettaglio</b></td><td>Dove si trova il titolo. Il dettaglio compare solo quando aggiunge informazione rispetto alla fase.</td></tr>
            <tr><td><b>LIQ OK / LOW / AVOID</b></td><td>Liquidità: <b>OK</b> si opera · <b>LOW</b> volume insufficiente, si resta in attesa · <b>AVOID</b> titolo escluso dalle indicazioni.</td></tr>
          </tbody>
        </table>

        <p className="indicators-guide-note">
          Nel <b>Monitor</b> e nella vista <b>Tabella</b> compaiono anche le colonne degli assi
          (<i>Direzione, Forza, Momento, Rischio</i>) e <b>AZIONE</b>, che è il comando interno
          da cui deriva l'indicazione: <b>BUY</b> = comprare, <b>ADD</b> = aggiungere su debolezza,
          <b>HOLD</b> = mantenere, <b>REDUCE</b> = alleggerire, <b>EXIT</b> = uscire,
          <b>AVOID</b> = stare fuori, <b>WAIT</b> = attendere per liquidità insufficiente.
        </p>
      </section>
      <p className="indicators-guide-intro">
        <b>UPTREND</b>, <b>PULLBACK</b>, <b>RANGE</b> e gli altri dettagli del contesto restano
        visibili per spiegare perché il titolo è stato classificato. Le decisioni sulle posizioni
        già possedute saranno gestite nella futura schermata Portafoglio.
      </p>

    </>
  );
}
