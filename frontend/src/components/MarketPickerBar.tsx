import { MarketChips } from "./MarketChips";

/**
 * Barra con il solo selettore del mercato.
 *
 * Alcune tab mostrano dati di UN mercato (Heatmap, Highlights, Indicatori) ma
 * erano escluse dalla barra dei controlli della tab All: senza selettore
 * restavano ferme sull'ultimo mercato scelto altrove e non c'era modo di
 * cambiarlo. Questa barra risolve quei casi una volta sola, invece di ripetere
 * il selettore in ogni tab.
 *
 * IMPORTANTE: se l'elenco dei mercati non e' ancora arrivato dal server, la
 * barra NON sparisce — mostra un elenco di riserva. Prima dipendeva dalla
 * chiamata `/api/markets` per esistere: se quella falliva o tardava, il selettore
 * non compariva affatto, e sembrava che la funzione non esistesse.
 */
const MERCATI_DI_RISERVA = ["MIB30", "ETF", "ETC", "DAX", "US_Others", "Crypto"];

export default function MarketPickerBar({
  markets,
  market,
  onSelect,
  conVolume,
  minVolume,
  onVolume,
}: {
  markets: string[] | undefined;
  market: string;
  onSelect: (m: string) => void;
  /** Mostra anche il volume minimo, per le tab i cui dati dipendono da quello. */
  conVolume?: boolean;
  minVolume?: number;
  onVolume?: (v: number) => void;
}) {
  const elenco = markets && markets.length ? markets : MERCATI_DI_RISERVA;

  return (
    <div className="market-picker-bar">
      <MarketChips
        markets={elenco}
        market={market}
        onSelect={onSelect}
        // Le liste personali arrivano come "WL:<nome>": si mostra solo il nome.
        nomeProprio={(m) => (m.toUpperCase().startsWith("WL:") ? m.slice(3).trim() || null : null)}
        trailing={
          conVolume && onVolume ? (
            <label className="volume-filter market-chip-volume">
              Volume min
              <input
                type="number"
                min="0"
                value={minVolume ?? 0}
                onChange={(e) => onVolume(Math.max(0, Number(e.target.value) || 0))}
              />
            </label>
          ) : undefined
        }
      />
    </div>
  );
}
