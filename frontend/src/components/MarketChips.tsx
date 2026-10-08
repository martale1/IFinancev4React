import type { ReactNode } from "react";

/**
 * Scelta del mercato (e delle liste personali), con pulsanti piccoli.
 *
 * Prima stava in alto, sotto l'intestazione: occupava molto spazio in ogni
 * schermata ed era poco pratica da raggiungere. Ora sta accanto al selettore
 * Schede/Tabella/Lista, che e' il posto dove si guarda quando si cambia vista.
 *
 * Componente condiviso fra la tab All e il Monitor: prima era scritto una volta
 * sola dentro App, e il Monitor non aveva alcuna scelta del mercato.
 */
export function MarketChips({
  markets,
  market,
  onSelect,
  nomeProprio,
  trailing,
}: {
  markets: string[];
  market: string;
  onSelect: (m: string) => void;
  /** Nome proprio di una lista personale, altrimenti null. */
  nomeProprio: (m: string) => string | null;
  /** Contenuto dopo i mercati (di solito il filtro del volume). */
  trailing?: ReactNode;
}) {
  // Una lista personale si riconosce dal nome proprio oppure dal prefisso "WL:"
  // che usa il backend. "Preferite" e' anch'essa una lista, non un mercato.
  const eLista = (m: string) => m === "Preferite" || m.startsWith("WL:") || Boolean(nomeProprio(m));
  const etichetta = (m: string) => nomeProprio(m) ?? m.replace(/^WL:/, "").replace(/_/g, " ");
  const mercatiVeri = markets.filter((m) => m !== "Tutti" && !eLista(m));
  const listePersonali = markets.filter((m) => m !== "Tutti" && eLista(m));
  const speciali = markets.filter((m) => m === "Tutti");

  const gruppo = (etichettaGruppo: string, opzioni: string[]) => {
    if (!opzioni.length) return null;
    return (
      <div className="market-chip-group" key={etichettaGruppo}>
        <span className="market-chip-label">{etichettaGruppo}</span>
        {opzioni.map((m) => (
          <button
            key={m}
            type="button"
            className={`market-chip${market === m ? " selected" : ""}`}
            aria-pressed={market === m}
            onClick={() => onSelect(m)}
            title={`Mostra ${etichetta(m)}`}
          >
            {etichetta(m)}
          </button>
        ))}
      </div>
    );
  };

  return (
    <div className="market-chips" aria-label="Selezione mercato e liste">
      {speciali.map((m) => (
        <button
          key={m}
          type="button"
          className={`market-chip${market === m ? " selected" : ""}`}
          aria-pressed={market === m}
          onClick={() => onSelect(m)}
          title="Mostra tutti i mercati"
        >
          {m}
        </button>
      ))}
      {gruppo("Mercati", mercatiVeri)}
      {gruppo("Le mie liste", listePersonali)}
      {trailing}
    </div>
  );
}
