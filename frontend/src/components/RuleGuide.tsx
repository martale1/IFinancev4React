export default function RuleGuide() {
  return (
    <section className="guide-card">
      <details>
        <summary>Guida regole: come leggere le card nei tab</summary>

        <div className="guide-grid compact">
          <div>
            <h3>Lettura veloce</h3>
            <p>
              La prima etichetta risponde a una sola domanda: <b>conviene valutare un nuovo ingresso?</b>
              Fase e dettaglio tecnico spiegano il contesto, ma non sono comandi operativi.
            </p>
          </div>

          <div>
            <h3>ENTRA</h3>
            <p>
              Trigger rialzista completo, liquidita' idonea e nessuna condizione di rischio prevalente.
              È il gruppo delle opportunita' operative, non un ordine automatico.
            </p>
          </div>

          <div>
            <h3>OSSERVA</h3>
            <p>
              Setup promettente ma incompleto: trend iniziale, espansione, breakout fresco oppure
              pullback sano/normale. Serve ancora una conferma prima dell'ingresso.
            </p>
          </div>

          <div>
            <h3>ATTENDI</h3>
            <p>
              Non ci sono ancora condizioni sufficienti. Include situazioni laterali, trend maturo,
              movimento troppo esteso, momentum in raffreddamento o liquidita' non ottimale.
            </p>
          </div>

          <div>
            <h3>EVITA</h3>
            <p>
              Struttura ribassista, rischio inversione, pullback rischioso o invalidato oppure
              liquidita' da evitare. Ha priorita' sugli eventuali segnali positivi.
            </p>
          </div>

          <div>
            <h3>Contesto tecnico</h3>
            <p>
              <b>UPTREND, PULLBACK, RANGE</b> e gli altri dettagli restano visibili per spiegare
              perché il titolo è stato classificato. Le decisioni sulle posizioni già possedute
              saranno gestite nella futura schermata Portafoglio.
            </p>
          </div>
        </div>
      </details>
    </section>
  );
}
