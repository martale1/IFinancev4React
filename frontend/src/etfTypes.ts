/**
 * Tipologia di un ETF, dedotta dal nome.
 *
 * PERCHE' DEDURLA: il file `ETF_TA_Analyses.xlsx` ha 149 colonne ma NESSUNA di
 * categoria: niente asset class, niente area, niente provider. Gli unici campi
 * leggibili sono `Ticker` e `Name`. Quindi l'unico modo per raggruppare 1684 ETF
 * e' leggere il nome, che segue convenzioni abbastanza regolari.
 *
 * QUANTO E' AFFIDABILE: misurato sui 1684 ETF, questa classificazione riconosce
 * il 79% dei titoli. Il restante 21% sono nomi TRONCATI dai fornitori ("JPM EUR
 * CRP BD RES ENH", "HSBC ASIA PACIF EX JP SUST EQU", "SPDR REFIN GL CONVERT BD"):
 * `CRP BD` = corporate bond, `EQU` = equity. Sono abbreviazioni AMBIGUE —
 * `TEC` puo' essere tecnologia o tecnologia pulita — e indovinarle
 * significherebbe classificare male. Una categoria sbagliata e' peggio di
 * nessuna categoria, quindi quei titoli finiscono in "Non riconosciuto" e la
 * scheda lo dichiara, invece di fingere una precisione che non c'e'.
 *
 * Per arrivare al 100% servirebbe una tabella di riferimento compilata a mano,
 * come `mib30_sectors.json` fa per i settori del MIB30.
 *
 * L'ORDINE CONTA: la prima regola che corrisponde vince. La leva e' per prima
 * perche' cambia la natura del prodotto (un "MSCI USA 3X SHORT" non e' un
 * azionario come gli altri), e le materie prime prima delle obbligazioni perche'
 * "WISDOMTREE WTI CRUDE OIL" non deve finire fra i bond.
 */

export type TipoEtf =
  | "Leva e inversi"
  | "Materie prime"
  | "Obbligazionari"
  | "Cripto"
  | "Immobiliare"
  | "Azionari"
  | "Non riconosciuto";

const REGOLE: Array<{ tipo: TipoEtf; pattern: RegExp }> = [
  { tipo: "Leva e inversi", pattern: /(\d+X\b|\bLEVERAG|\bSHORT\b|\bINVERSE\b|\bDAILY\b)/ },
  {
    tipo: "Materie prime",
    pattern: /\b(ETC|ETP|GOLD|SILVER|CRUDE|OIL|BRENT|WTI|NATURAL GAS|COMMODIT|COPPER|PLATINUM|PALLADIUM|AGRICULT|WHEAT|CORN|SOYBEAN|COFFEE|LITHIUM|URANIUM|LEAD|ZINC|NICKEL|ALUMINIUM|HYDROGEN|CARBON)\b/,
  },
  {
    tipo: "Obbligazionari",
    pattern: /\b(BOND|BONDS|TREAS|TREASURY|GILT|GILTS|CORP|CORPORATE|GOVT|GOVERNMENT|GOVIES|SOVEREIGN|EMBI|CREDIT|YIELD|BUND|BTP|SUKUK|MBS|ABS|FLOATING RATE|TIPS|INF-?LINK|AGGRE|AGG|IG |HIGH YIELD|MONEY MARKET|OVERNIGHT|CASH|SHORT DURATION|DURATION)\b/,
  },
  { tipo: "Cripto", pattern: /\b(BITCOIN|ETHEREUM|CRYPTO|BLOCKCHAIN|SOLANA|CARDANO|POLKADOT)\b/ },
  { tipo: "Immobiliare", pattern: /\b(REAL ESTATE|REIT|PROPERT)\b/ },
  {
    tipo: "Azionari",
    pattern: /\b(MSCI|FTSE|S&P|STOXX|NASDAQ|RUSSELL|DOW JONES|EQUITY|EQUITIES|DIVIDEND|WORLD|GLOBAL|EMERGING|EM |SECTOR|BANK|TECH|HEALTH|ENERGY|UTILIT|DAX|CAC|IBEX|AEX|SMI|OMX|NIKKEI|TOPIX|HANG SENG|ALL CAP|ALLCAP|SMALL CAP|MID CAP|LARGE CAP|VALUE|GROWTH|MOMENTUM|QUALITY|INCOME)\b/,
  },
];

/** Ordine di visualizzazione: prima i gruppi piu' grandi e utili. */
export const ORDINE_TIPI: TipoEtf[] = [
  "Azionari",
  "Obbligazionari",
  "Leva e inversi",
  "Materie prime",
  "Cripto",
  "Immobiliare",
  "Non riconosciuto",
];

/**
 * Tipologie di un ETC: la materia prima sottostante.
 *
 * Il file degli ETC non ha piu' colonne di categoria di quello degli ETF, ma i
 * nomi sono molto piu' regolari perche' il prodotto E' la materia ("ETFS SILVER",
 * "ETFS LEVERAGED NICKEL", "ETFS EUR DAILY HEDGED SOYBEANS"). Misurato sui 93
 * ETC, questa classificazione riconosce il 96% dei titoli.
 */
export type TipoEtc =
  | "Leva e short"
  | "Metalli preziosi"
  | "Metalli industriali"
  | "Energia"
  | "Agricoli"
  | "Valute"
  | "Panieri"
  | "Non riconosciuto";

const REGOLE_ETC: Array<{ tipo: TipoEtc; pattern: RegExp }> = [
  // La leva per prima: "ETFS 3X SHORT GBP LONG EUR" e' un prodotto a leva, non
  // una valuta, e "LEVERAGED NICKEL" non e' nichel fisico.
  { tipo: "Leva e short", pattern: /(\d+X\b|\bLEVERAG|\bSHORT\b|\bBULL\b|\bBEAR\b)/ },
  { tipo: "Metalli preziosi", pattern: /\b(GOLD|SILVER|PLATINUM|PALLADIUM|RHODIUM)\b/ },
  { tipo: "Metalli industriali", pattern: /\b(COPPER|NICKEL|ZINC|ALUMINIUM|ALUMINUM|LEAD|TIN|STEEL|IRON)\b/ },
  { tipo: "Energia", pattern: /\b(CRUDE|OIL|BRENT|WTI|GAS|GASOLINE|HEATING|COAL|CARBON|ELECTRIC)\b/ },
  // "SOYBEANS" e "Coffee" hanno forme irregolari nei nomi ("ETFS SOYBEANS",
  // "ETFCoffee" senza spazio): il confine di parola non li prende, quindi qui
  // si cerca la radice.
  { tipo: "Agricoli", pattern: /(WHEAT|CORN|SOY|SUGAR|COFFEE|COCOA|COTTON|HOGS|LIVESTOCK|CATTLE|AGRICULT|GRAIN|RICE)/ },
  { tipo: "Valute", pattern: /\b(EUR|USD|GBP|JPY|CHF|CURRENC|FOREX)\b/ },
  { tipo: "Panieri", pattern: /(COMMODIT|DJ-UBSCI|BOOSTER|BROAD|BASKET)/ },
];

export const ORDINE_ETC: TipoEtc[] = [
  "Leva e short",
  "Metalli preziosi",
  "Metalli industriali",
  "Energia",
  "Agricoli",
  "Panieri",
  "Valute",
  "Non riconosciuto",
];

/** La tipologia di un ETC, dedotta dal nome. */
export function tipoEtc(row: Record<string, unknown>): TipoEtc {
  const nome = nomeEtf(row.Ticker, row.Name).toUpperCase();
  if (!nome) return "Non riconosciuto";
  for (const regola of REGOLE_ETC) {
    if (regola.pattern.test(nome)) return regola.tipo;
  }
  return "Non riconosciuto";
}

const NON_RICONOSCIUTO: TipoEtf = "Non riconosciuto";

/**
 * Il nome senza il suffisso di mercato attaccato in coda.
 *
 * Negli Excel alcuni nomi arrivano come "... UCITS ETF Acc.MI": il suffisso
 * viene tolto solo quando coincide con quello del ticker, cosi' non si taglia
 * altro.
 */
export function nomeEtf(ticker: unknown, name: unknown): string {
  const grezzo = String(name ?? "").replace(/\s+/g, " ").trim();
  if (!grezzo) return "";
  const tk = String(ticker ?? "").trim();
  const suffisso = tk.includes(".") ? tk.slice(tk.indexOf(".")) : "";
  if (suffisso && grezzo.endsWith(suffisso)) {
    return grezzo.slice(0, -suffisso.length).trim();
  }
  return grezzo;
}

/** La tipologia dedotta dal nome del titolo. */
export function tipoEtf(row: Record<string, unknown>): TipoEtf {
  const nome = nomeEtf(row.Ticker, row.Name).toUpperCase();
  if (!nome) return NON_RICONOSCIUTO;
  for (const regola of REGOLE) {
    if (regola.pattern.test(nome)) return regola.tipo;
  }
  return NON_RICONOSCIUTO;
}

/**
 * Se un titolo e' negoziabile.
 *
 * La liquidita' e' calcolata dal sistema (OK / LOW / AVOID) ed e' l'unico dato
 * affidabile per separare i prodotti reali da quelli morti: sugli ETF, 718
 * titoli su 1684 sono AVOID e 118 hanno volume zero.
 */
export function isLiquido(row: Record<string, unknown>): boolean {
  return String(row.Liquidity ?? "").trim().toUpperCase() === "OK";
}
