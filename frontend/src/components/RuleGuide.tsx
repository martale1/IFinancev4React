export default function RuleGuide() {
  return (
    <section className="guide-card">
      <details>
        <summary>Guida regole: come leggere le card nei tab</summary>

        <div className="guide-grid compact">
          <div>
            <h3>Lettura veloce</h3>
            <p>
              Ogni card va letta in tre livelli: <b>Action</b> dice cosa suggerisce il sistema,
              <b> Market_Phase</b> dice dove siamo nel ciclo tecnico, <b>Trend_Phase_Detail</b>
              aggiunge la qualita' della fase quando serve.
            </p>
            <p>
              Esempio: <b>BUY + UPTREND + OVEREXTENDED</b> resta positivo, ma segnala che il
              movimento e' tirato. <b>REDUCE + REVERSAL_RISK</b> e' invece una card di cautela.
            </p>
          </div>

          <div>
            <h3>Action</h3>
            <p>
              <b>BUY</b>: trigger strict rialzista completo. <b>SELL</b>: trigger strict ribassista.
              <b>ADD</b>: contesto bullish buono, ma non abbastanza completo per BUY strict.
            </p>
            <p>
              <b>REDUCE</b>: alleggerire o non inseguire, per eccesso/rischio. <b>HOLD</b>:
              fase valida ma senza trigger operativo. <b>WAIT</b>: liquidita' non OK.
              <b> AVOID</b>: liquidita' da evitare. <b>EXIT</b>: rottura o fase ribassista.
            </p>
          </div>

          <div>
            <h3>Market_Phase</h3>
            <p>
              <b>BREAKOUT</b>: rottura rialzista. <b>UPTREND</b>: trend rialzista strutturale.
              <b> PULLBACK</b>: ritracciamento dentro una struttura ancora positiva.
            </p>
            <p>
              <b>RANGE</b>: fase laterale. <b>DOWNTREND</b>: struttura ribassista.
              <b> REVERSAL_RISK</b>: segnali contrastanti o rischio inversione.
            </p>
          </div>

          <div>
            <h3>Uptrend detail</h3>
            <p>
              <b>EARLY TREND</b>: trend appena partito, molto fresco. <b>EXPANSION</b>:
              trend in accelerazione ordinata. <b>MATURE TREND</b>: trend gia' avanzato.
            </p>
            <p>
              <b>OVEREXTENDED</b>: trend tirato. <b>UPTREDING COOLING</b>: trend ancora up,
              ma momentum che si raffredda. <b>UPTREND GENERIC</b>: uptrend senza dettaglio speciale.
            </p>
          </div>

          <div>
            <h3>Pullback / Breakout detail</h3>
            <p>
              <b>PULLBACK HEALTHY</b>: ritracciamento ordinato. <b>PULLBACK NORMAL</b>:
              pullback regolare, da monitorare. <b>PULLBACK RISKY</b>: pullback piu' fragile.
            </p>
            <p>
              <b>BREAKOUT FRESH</b>: rottura recente. <b>BREAKOUT EXTENDED</b>: breakout gia'
              partito, meno fresco.
            </p>
          </div>

          <div>
            <h3>Esempi pratici</h3>
            <p>
              <b>REDUCE + REVERSAL_RISK</b>: prudenza, possibile inversione o conflitto tecnico.
              <b>REDUCE + PULLBACK</b>: fase positiva ma non da inseguire ora.
            </p>
            <p>
              <b>HOLD + EARLY TREND</b>: setup interessante, ma manca almeno una conferma strict.
              <b>BUY + UPTREDING COOLING</b>: compra ancora secondo regole, ma con momentum meno brillante.
            </p>
          </div>
        </div>
      </details>
    </section>
  );
}
