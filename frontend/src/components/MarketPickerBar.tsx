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
 * Non include ordinamento, ricerca ne' le tessere dell'indicazione: quelle
 * servono solo dove c'e' un elenco da ordinare. Il volume minimo invece e' un
 * filtro sui dati, quindi si puo' mostrare.
 */
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
  if (!markets) return null;

  return (
    <div className="market-picker-bar">
      <MarketChips
        markets={markets}
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
