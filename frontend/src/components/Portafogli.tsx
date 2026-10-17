/**
 * Portafoglio virtuale — fase 1.
 *
 * Cosa si puo' fare qui: creare piu' portafogli indipendenti, comprare e vendere
 * a mano, vedere valore, P/L, costi e distanza dallo stop.
 *
 * Cosa NON c'e' ancora (fasi successive): uscite automatiche, ingressi da
 * segnale, motore ogni 15 minuti. La schermata lo dice, perche' un numero senza
 * la sua avvertenza e' una bugia.
 *
 * Tutti gli importi mostrati sono in EURO, tranne il prezzo dello strumento che
 * resta nella sua valuta (indicata accanto).
 */
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  anteprimaAcquisto,
  aggiornaPortafoglio,
  archiviaPortafoglio,
  compraTitolo,
  creaPortafoglio,
  eseguiGiro,
  fetchCandidati,
  fetchOperazioniPortafoglio,
  fetchPortafogli,
  fetchPortafoglio,
  vendiTitolo,
} from "../portafoglioApi";
import type { EsitoGiro } from "../portafoglioApi";
import type { AnteprimaAcquisto, OperazioneChiusa } from "../portafoglioTipi";
import { toNum } from "../format";

/** Importo con la virgola italiana; i centesimi servono sempre. */
function euro(valore: unknown): string {
  const n = toNum(valore);
  if (n === null) return "—";
  return `${n.toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`;
}

/** Percentuale con segno. */
function perc(valore: unknown): string {
  const n = toNum(valore);
  if (n === null) return "—";
  return `${n > 0 ? "+" : ""}${n.toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

/** Prezzo dello strumento: tre decimali sotto i 5, due sopra. */
function prezzo(valore: unknown): string {
  const n = toNum(valore);
  if (n === null) return "—";
  const dec = Math.abs(n) < 5 ? 3 : 2;
  return n.toLocaleString("it-IT", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

function classeDaSegno(valore: unknown): string {
  const n = toNum(valore);
  if (n === null || n === 0) return "neutral";
  return n > 0 ? "positive" : "negative";
}

const PRESET = [
  { chiave: "conservativo", etichetta: "Conservativo", nota: "rischio 0,5% · max 5% per titolo · stop 1,5 ATR" },
  { chiave: "bilanciato", etichetta: "Bilanciato", nota: "rischio 1% · max 10% per titolo · stop 2 ATR" },
  { chiave: "aggressivo", etichetta: "Aggressivo", nota: "rischio 2% · max 20% per titolo · stop 2,5 ATR" },
];
/** I mercati su cui un portafoglio puo' operare. Devono combaciare con le analisi. */
const MERCATI = [
  { chiave: "MIB30", etichetta: "MIB30" },
  { chiave: "DAX", etichetta: "DAX" },
  { chiave: "ETF", etichetta: "ETF" },
  { chiave: "ETC", etichetta: "ETC" },
  { chiave: "Crypto", etichetta: "Crypto" },
  { chiave: "US_Others", etichetta: "US / altri" },
  { chiave: "Preferite", etichetta: "Preferite" },
];



export default function Portafogli() {
  const qc = useQueryClient();
  const [scelto, setScelto] = useState<string | null>(null);
  const [creando, setCreando] = useState(false);
  const [errore, setErrore] = useState("");

  // ── creazione ───────────────────────────────────────────────────────
  const [nome, setNome] = useState("");
  const [capitale, setCapitale] = useState("10000");
  const [preset, setPreset] = useState("bilanciato");
  const [mercatiNuovi, setMercatiNuovi] = useState<string[]>(["MIB30", "DAX"]);

  // ── acquisto ────────────────────────────────────────────────────────
  const [ticker, setTicker] = useState("");
  const [importo, setImporto] = useState("");
  const [anteprima, setAnteprima] = useState<AnteprimaAcquisto | null>(null);
  /** Titoli proposti mentre si scrive nel campo di ricerca. */
  const [suggerimenti, setSuggerimenti] = useState<
    Array<{ ticker: string; nome: string; mercato: string; indicazione?: string | null; tech_score?: number | null }>
  >([]);

  // ── vendita: due passaggi, perche' e' denaro (anche se finto) ───────
  const [uscita, setUscita] = useState<string | null>(null);
  /** Risultato dell'ultimo giro automatico: chi ha comprato e chi no. */
  const [esitoGiro, setEsitoGiro] = useState<EsitoGiro | null>(null);

  // ── comandi della tabella (come nel conto titoli del broker) ────────
  const [filtroStrumento, setFiltroStrumento] = useState("Tutti");
  const [filtroValuta, setFiltroValuta] = useState("Tutte");
  /** Colonna di ordinamento e verso. Default: valore, dal piu' grande. */
  const [ordine, setOrdine] = useState<{ chiave: string; verso: "asc" | "desc" }>({
    chiave: "valore_eur",
    verso: "desc",
  });
  /** Maschera gli importi: serve quando si guarda lo schermo insieme ad altri. */
  const [nascondi, setNascondi] = useState(false);

  const elencoQuery = useQuery({ queryKey: ["portafogli"], queryFn: fetchPortafogli });
  const dettaglioQuery = useQuery({
    queryKey: ["portafoglio", scelto],
    queryFn: () => fetchPortafoglio(String(scelto)),
    enabled: Boolean(scelto),
  });
  const operazioniQuery = useQuery({
    queryKey: ["portafoglio-operazioni", scelto],
    queryFn: () => fetchOperazioniPortafoglio(String(scelto)),
    enabled: Boolean(scelto),
  });

  const ricarica = async (id?: string | null) => {
    await qc.invalidateQueries({ queryKey: ["portafogli"] });
    if (id) {
      await qc.invalidateQueries({ queryKey: ["portafoglio", id] });
      await qc.invalidateQueries({ queryKey: ["portafoglio-operazioni", id] });
    }
  };

  const creaMut = useMutation({
    mutationFn: () =>
      creaPortafoglio({
        nome,
        capitale: Number(capitale.replace(",", ".")),
        preset,
        parametri: { mercati: mercatiNuovi },
      }),
    onSuccess: async (pf) => {
      setCreando(false);
      setNome("");
      setScelto(pf.id);
      setErrore("");
      await ricarica(pf.id);
    },
    onError: (e: unknown) => setErrore(e instanceof Error ? e.message : "Creazione non riuscita"),
  });

  const giroMut = useMutation({
    mutationFn: () => eseguiGiro(String(scelto)),
    onSuccess: async (esito) => {
      setEsitoGiro(esito);
      setErrore("");
      await ricarica(scelto);
    },
    onError: (e: unknown) => {
      setEsitoGiro(null);
      setErrore(e instanceof Error ? e.message : "Giro non riuscito");
    },
  });

  const compraMut = useMutation({
    mutationFn: () =>
      compraTitolo(String(scelto), {
        ticker,
        importo_eur: importo.trim() ? Number(importo.replace(",", ".")) : undefined,
        motivo: "acquisto manuale",
      }),
    onSuccess: async () => {
      setAnteprima(null);
      setTicker("");
      setImporto("");
      setErrore("");
      await ricarica(scelto);
    },
    onError: (e: unknown) => setErrore(e instanceof Error ? e.message : "Acquisto non riuscito"),
  });

  const vendiMut = useMutation({
    mutationFn: (tk: string) => vendiTitolo(String(scelto), { ticker: tk, motivo: "manuale" }),
    onSuccess: async () => {
      setUscita(null);
      setErrore("");
      await ricarica(scelto);
    },
    onError: (e: unknown) => setErrore(e instanceof Error ? e.message : "Vendita non riuscita"),
  });

  const mercatiMut = useMutation({
    mutationFn: (mercati: string[]) =>
      aggiornaPortafoglio(String(scelto), { parametri: { mercati } }),
    onSuccess: async () => {
      setErrore("");
      await ricarica(scelto);
    },
    onError: (e: unknown) => setErrore(e instanceof Error ? e.message : "Modifica non riuscita"),
  });

  const archiviaMut = useMutation({
    mutationFn: (id: string) => archiviaPortafoglio(id),
    onSuccess: async () => {
      setScelto(null);
      await ricarica();
    },
    onError: (e: unknown) => setErrore(e instanceof Error ? e.message : "Archiviazione non riuscita"),
  });

  // Suggerimenti: si chiede al server dopo una breve pausa dalla digitazione,
  // cosi' scrivere "campari" non produce sette richieste.
  useEffect(() => {
    const testo = ticker.trim();
    if (!scelto || testo.length < 2) {
      setSuggerimenti([]);
      return;
    }
    let annullato = false;
    const timer = window.setTimeout(async () => {
      try {
        const trovati = await fetchCandidati(scelto, testo);
        if (!annullato) setSuggerimenti(trovati);
      } catch {
        if (!annullato) setSuggerimenti([]);
      }
    }, 250);
    return () => {
      annullato = true;
      window.clearTimeout(timer);
    };
  }, [ticker, scelto]);

  const caricaAnteprima = async () => {
    if (!scelto || !ticker.trim()) return;
    setErrore("");
    try {
      const risultato = await anteprimaAcquisto(
        scelto,
        ticker.trim().toUpperCase(),
        importo.trim() ? Number(importo.replace(",", ".")) : undefined,
      );
      setAnteprima(risultato);
    } catch (e) {
      setAnteprima(null);
      setErrore(e instanceof Error ? e.message : "Anteprima non disponibile");
    }
  };

  const dettaglio = dettaglioQuery.data;
  const operazioni = operazioniQuery.data ?? [];

  /** Valori distinti per i due menu a tendina. */
  const strumentiDisponibili = useMemo(() => {
    const insieme = new Set<string>();
    for (const pos of dettaglio?.posizioni ?? []) {
      if (pos.strumento) insieme.add(pos.strumento);
    }
    return ["Tutti", ...Array.from(insieme).sort()];
  }, [dettaglio]);

  const valuteDisponibili = useMemo(() => {
    const insieme = new Set<string>();
    for (const pos of dettaglio?.posizioni ?? []) {
      if (pos.valuta) insieme.add(pos.valuta);
    }
    return ["Tutte", ...Array.from(insieme).sort()];
  }, [dettaglio]);

  /** Posizioni da mostrare: filtrate e ordinate. */
  const posizioniVisibili = useMemo(() => {
    const tutte = dettaglio?.posizioni ?? [];
    const filtrate = tutte.filter(
      (pos) =>
        (filtroStrumento === "Tutti" || pos.strumento === filtroStrumento) &&
        (filtroValuta === "Tutte" || pos.valuta === filtroValuta),
    );
    const valore = (pos: (typeof filtrate)[number], chiave: string): number | string => {
      switch (chiave) {
        case "ticker":
          return pos.ticker;
        case "strumento":
          return pos.strumento ?? "";
        case "valuta":
          return pos.valuta ?? "";
        case "quantita":
          return Number(pos.quantita) || 0;
        case "prezzo_ingresso":
          return Number(pos.prezzo_ingresso) || 0;
        case "prezzo_corrente":
          return Number(pos.prezzo_corrente) || 0;
        case "valore_eur":
          return Number(pos.valore_eur) || 0;
        case "pnl":
          return Number(pos.pnl_eur) || 0;
        case "netto":
          return Number(pos.pnl_netto_eur) || 0;
        default:
          return 0;
      }
    };
    return [...filtrate].sort((a, b) => {
      const va = valore(a, ordine.chiave);
      const vb = valore(b, ordine.chiave);
      const confronto =
        typeof va === "string" || typeof vb === "string"
          ? String(va).localeCompare(String(vb))
          : Number(va) - Number(vb);
      return ordine.verso === "asc" ? confronto : -confronto;
    });
  }, [dettaglio, filtroStrumento, filtroValuta, ordine]);

  /** Clic su un'intestazione: ordina, e al secondo clic inverte. */
  const ordinaPer = (chiave: string) => {
    setOrdine((prima) =>
      prima.chiave === chiave
        ? { chiave, verso: prima.verso === "asc" ? "desc" : "asc" }
        : { chiave, verso: chiave === "ticker" || chiave === "strumento" || chiave === "valuta" ? "asc" : "desc" },
    );
  };
  const freccia = (chiave: string) => (ordine.chiave === chiave ? (ordine.verso === "asc" ? " ▲" : " ▼") : "");
  /** Maschera un importo quando "Nascondi" e' attivo. */
  const soldi = (valore: string) => (nascondi ? "•••••" : valore);

  const totaleGenerale = useMemo(() => {
    const portafogli = elencoQuery.data ?? [];
    return portafogli.reduce((somma, p) => somma + (toNum(p.capitale_iniziale) ?? 0), 0);
  }, [elencoQuery.data]);

  return (
    <div className="pf">
      <header className="pf-testata">
        <div>
          <h2>Portafogli virtuali</h2>
          <p className="pf-sottotitolo">
            Capitale simulato, prezzi reali. Prima fase: compravendita manuale con costi veri
            (0,19% minimo 2,95 €, Tobin 0,10%, cambio 0,25%).
          </p>
        </div>
        <button type="button" className="btn primary" onClick={() => setCreando((v) => !v)}>
          {creando ? "Chiudi" : "+ Nuovo portafoglio"}
        </button>
      </header>

      {errore ? <div className="error-banner">{errore}</div> : null}

      {creando ? (
        <section className="pf-crea">
          <label>
            Nome
            <input value={nome} onChange={(e) => setNome(e.target.value)} placeholder="es. Bilanciato 2026" />
          </label>
          <label>
            Capitale iniziale (€)
            <input value={capitale} onChange={(e) => setCapitale(e.target.value)} inputMode="decimal" />
          </label>
          <label>
            Profilo di partenza
            <select value={preset} onChange={(e) => setPreset(e.target.value)}>
              {PRESET.map((p) => (
                <option key={p.chiave} value={p.chiave}>{p.etichetta} — {p.nota}</option>
              ))}
            </select>
          </label>
          <div className="pf-mercati">
            <span className="pf-mercati-titolo">Mercati su cui operare</span>
            <div className="pf-mercati-scelta">
              {MERCATI.map((m) => (
                <label key={m.chiave} className={mercatiNuovi.includes(m.chiave) ? "attivo" : ""}>
                  <input
                    type="checkbox"
                    checked={mercatiNuovi.includes(m.chiave)}
                    onChange={(e) =>
                      setMercatiNuovi((prima) =>
                        e.target.checked ? [...prima, m.chiave] : prima.filter((x) => x !== m.chiave),
                      )
                    }
                  />
                  {m.etichetta}
                </label>
              ))}
            </div>
            {mercatiNuovi.length === 0 ? (
              <small className="pf-avvertenza">Senza mercati il portafoglio non potra' comprare nulla.</small>
            ) : null}
          </div>

          <button
            type="button"
            className="btn primary"
            disabled={!nome.trim() || creaMut.isPending}
            onClick={() => creaMut.mutate()}
          >
            {creaMut.isPending ? "Creo..." : "Crea portafoglio"}
          </button>
        </section>
      ) : null}

      {/* ── elenco ─────────────────────────────────────────────────── */}
      <section className="pf-elenco">
        {elencoQuery.isLoading ? <p className="muted">Carico i portafogli...</p> : null}
        {elencoQuery.data?.length === 0 ? (
          <p className="pf-vuoto">
            Nessun portafoglio. Creane uno: il capitale e' finto, i prezzi e i costi sono quelli veri.
          </p>
        ) : null}
        {(elencoQuery.data ?? []).map((p) => (
          <button
            key={p.id}
            type="button"
            className={`pf-riga ${scelto === p.id ? "scelto" : ""} ${p.stato !== "attivo" ? "archiviato" : ""}`}
            onClick={() => setScelto(p.id === scelto ? null : p.id)}
          >
            <span className="pf-riga-nome">
              <b>{p.nome}</b>
              <small>{p.stato}</small>
            </span>
            {/* Il riepilogo utile: quanto vale, se stai guadagnando e di quanto. */}
            <span className="pf-riga-riepilogo">
              <span className="pf-riga-valore">
                <b>{euro(p.valore_totale)}</b>
                <small>valore attuale</small>
              </span>
              <span className={`pf-riga-var ${classeDaSegno(p.pnl_eur)}`}>
                <b>
                  {(toNum(p.pnl_eur) ?? 0) > 0 ? "+" : ""}
                  {euro(p.pnl_eur)}
                </b>
                <small>{perc(p.pnl_pct)}</small>
              </span>
              <span className="pf-riga-dettagli">
                <small>
                  liquidi {euro(p.liquidita)} · {p.num_posizioni} posizioni · esposizione{" "}
                  {(toNum(p.esposizione_pct) ?? 0).toFixed(0)}%
                </small>
                <small>{p.num_operazioni} operazioni chiuse</small>
              </span>
            </span>
            <span className="pf-riga-azione">{scelto === p.id ? "▴" : "▾"}</span>
          </button>
        ))}
        {totaleGenerale > 0 ? (
          <p className="pf-nota">Capitale iniziale complessivo: {euro(totaleGenerale)}</p>
        ) : null}
      </section>

      {/* ── dettaglio ──────────────────────────────────────────────── */}
      {scelto && dettaglio ? (
        <section className="pf-dettaglio">
          <header className="pf-dettaglio-testata">
            <h3>{dettaglio.nome}</h3>
            <button
              type="button"
              className="btn ghost"
              onClick={() => archiviaMut.mutate(dettaglio.id)}
              title="Archivia il portafoglio: lo storico delle operazioni resta"
            >
              Archivia
            </button>
          </header>

          {/* I tre numeri in grande, come nel conto titoli del broker. */}
          <div className="pf-quadro">
            <div className="pf-quadro-voce">
              <small>Valorizzazione EUR</small>
              <b>{euro(dettaglio.valore_totale)}</b>
            </div>
            <div className="pf-quadro-voce">
              <small>Variazione EUR</small>
              <b className={classeDaSegno(dettaglio.pnl_totale_eur)}>
                {dettaglio.pnl_totale_eur > 0 ? "+" : ""}
                {euro(dettaglio.pnl_totale_eur)}
              </b>
            </div>
            <div className="pf-quadro-voce">
              <small>Variazione %</small>
              <b className={classeDaSegno(dettaglio.pnl_totale_pct)}>{perc(dettaglio.pnl_totale_pct)}</b>
            </div>
          </div>
          <p className="pf-quadro-nota">
            Liquidi {euro(dettaglio.liquidita)} · esposizione{" "}
            {(toNum(dettaglio.esposizione_pct) ?? 0).toLocaleString("it-IT", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
            % · {dettaglio.num_posizioni} posizioni · capitale iniziale {euro(dettaglio.capitale_iniziale)}
          </p>

          {/* Mercati su cui questo portafoglio puo' operare: si cambiano qui,
              e il backend rifiuta comunque gli acquisti fuori elenco. */}
          <div className="pf-mercati">
            <span className="pf-mercati-titolo">Mercati abilitati</span>
            <div className="pf-mercati-scelta">
              {MERCATI.map((m) => {
                const abilitati = dettaglio.parametri.mercati ?? [];
                const attivo = abilitati.includes(m.chiave);
                return (
                  <button
                    key={m.chiave}
                    type="button"
                    className={attivo ? "attivo" : ""}
                    disabled={mercatiMut.isPending}
                    onClick={() => {
                      const nuovi = attivo
                        ? abilitati.filter((x) => x !== m.chiave)
                        : [...abilitati, m.chiave];
                      mercatiMut.mutate(nuovi);
                    }}
                  >
                    {m.etichetta}
                  </button>
                );
              })}
            </div>
            {(dettaglio.parametri.mercati ?? []).length === 0 ? (
              <small className="pf-avvertenza">Nessun mercato abilitato: non si puo' comprare nulla.</small>
            ) : null}
          </div>

          {/* ── il giro automatico: i titoli li sceglie il sistema ─── */}
          <div className="pf-giro">
            <button
              type="button"
              className="btn primary pf-giro-bottone"
              disabled={giroMut.isPending || dettaglio.stato !== "attivo"}
              onClick={() => giroMut.mutate()}
              title="Il sistema sceglie i titoli migliori dei mercati abilitati e compra entro i limiti del profilo"
            >
              {giroMut.isPending ? "Giro in corso..." : "🤖 Esegui il giro"}
            </button>
                      </div>

          {esitoGiro ? (
            <div className="pf-esito">
              <p className="pf-esito-titolo">
                {esitoGiro.eseguiti.length > 0
                  ? `Comprati ${esitoGiro.eseguiti.length} titoli su ${esitoGiro.candidati_valutati} candidati`
                  : `Nessun acquisto su ${esitoGiro.candidati_valutati} candidati`}
              </p>
              {esitoGiro.eseguiti.map((e) => (
                <div className="pf-esito-riga buono" key={e.ticker}>
                  <b>{e.ticker}</b>
                  <span>{e.nome}</span>
                  <small>
                    {e.quantita} × {prezzo(e.prezzo)} = {euro(e.importo_eur)} · TECH {e.tech_score} · stop {prezzo(e.stop)}
                  </small>
                </div>
              ))}
              {esitoGiro.scarti.map((sc) => (
                <div className="pf-esito-riga scarto" key={`${sc.ticker}-${sc.motivo}`}>
                  <b>{sc.ticker}</b>
                  <span>{sc.motivo.replace(/_/g, " ")}</span>
                  <small>{sc.dettaglio}</small>
                </div>
              ))}
            </div>
          ) : null}

          {/* ── acquisto manuale, per chi vuole intervenire ────────── */}
          <details className="pf-manuale">
            <summary>Aggiungi un titolo a mano</summary>
            <div className="pf-acquisto">
              <div className="pf-acquisto-riga">
                <input
                  value={ticker}
                  onChange={(e) => {
                    setTicker(e.target.value);
                    setAnteprima(null);
                  }}
                  placeholder="Cerca un titolo (es. Eni, o ENI.MI)"
                  aria-label="Ticker da comprare"
                />
                <input
                  value={importo}
                  onChange={(e) => {
                    setImporto(e.target.value);
                    setAnteprima(null);
                  }}
                  placeholder="Importo € (vuoto = automatico)"
                  inputMode="decimal"
                  aria-label="Importo in euro"
                />
                <button type="button" className="btn" onClick={() => void caricaAnteprima()} disabled={!ticker.trim()}>
                  Anteprima
                </button>
              </div>

              {suggerimenti.length > 0 && !anteprima ? (
                <div className="pf-suggerimenti">
                  {suggerimenti.map((c2) => (
                    <button
                      key={`${c2.mercato}-${c2.ticker}`}
                      type="button"
                      onClick={() => {
                        setTicker(c2.ticker);
                        setSuggerimenti([]);
                        void (async () => {
                          try {
                            const risultato = await anteprimaAcquisto(String(scelto), c2.ticker);
                            setAnteprima(risultato);
                            setErrore("");
                          } catch (e) {
                            setAnteprima(null);
                            setErrore(e instanceof Error ? e.message : "Anteprima non disponibile");
                          }
                        })();
                      }}
                    >
                      <b>{c2.ticker}</b>
                      <span>{c2.nome}</span>
                      <small>
                        {c2.mercato}
                        {c2.indicazione ? ` · ${c2.indicazione}` : ""}
                      </small>
                    </button>
                  ))}
                </div>
              ) : null}

              {anteprima ? (
                <div className="pf-anteprima">
                  <p className="pf-anteprima-titolo">
                    {anteprima.nome} · {anteprima.ticker} · {prezzo(anteprima.prezzo)} {anteprima.valuta}
                    {anteprima.indicazione ? ` · ${anteprima.indicazione}` : ""}
                    {anteprima.tech_score !== null && anteprima.tech_score !== undefined
                      ? ` · TECH ${Math.round(Number(anteprima.tech_score))}`
                      : ""}
                  </p>
                  <div className="pf-anteprima-numeri">
                    <span>Quantità <b>{anteprima.quantita}</b></span>
                    <span>Importo <b>{euro(anteprima.importo_eur)}</b></span>
                    <span>
                      Costi{" "}
                      <b>
                        {euro(
                          (toNum(anteprima.commissione_eur) ?? 0) +
                            (toNum(anteprima.imposta_tobin_eur) ?? 0) +
                            (toNum(anteprima.costo_cambio_eur) ?? 0),
                        )}
                      </b>
                    </span>
                    <span>Totale <b>{euro(anteprima.totale_eur)}</b></span>
                    <span>Stop <b>{prezzo(anteprima.stop)}</b></span>
                    <span>Obiettivo <b>{prezzo(anteprima.obiettivo)}</b></span>
                    <span>
                      Perdita massima <b className="negative">{euro(anteprima.perdita_massima_eur)}</b>
                    </span>
                  </div>
                  <div className="pf-anteprima-azioni">
                    <button
                      type="button"
                      className="btn primary"
                      disabled={compraMut.isPending || anteprima.quantita <= 0}
                      onClick={() => compraMut.mutate()}
                    >
                      {compraMut.isPending ? "Compro..." : `Compra ${anteprima.quantita} × ${prezzo(anteprima.prezzo)}`}
                    </button>
                    <button type="button" className="btn ghost" onClick={() => setAnteprima(null)}>
                      Annulla
                    </button>
                  </div>
                  <p className="pf-avvertenza">
                    Prezzo di esecuzione: quello visto dall&apos;app adesso. Può avere un ritardo fino a 15 minuti.
                  </p>
                </div>
              ) : null}
            </div>
          </details>

          {/* ── posizioni ──────────────────────────────────────────── */}
          {/* Comandi sopra la tabella: strumenti, valuta, nascondi. */}
          <div className="pf-comandi">
            <label className="pf-comando">
              <span>Strumenti</span>
              <select value={filtroStrumento} onChange={(e) => setFiltroStrumento(e.target.value)}>
                {strumentiDisponibili.map((x) => (
                  <option key={x} value={x}>{x}</option>
                ))}
              </select>
            </label>
            <label className="pf-comando">
              <span>Valuta</span>
              <select value={filtroValuta} onChange={(e) => setFiltroValuta(e.target.value)}>
                {valuteDisponibili.map((x) => (
                  <option key={x} value={x}>{x}</option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className={nascondi ? "btn active" : "btn ghost"}
              onClick={() => setNascondi((v) => !v)}
              title={nascondi ? "Mostra di nuovo gli importi" : "Nascondi gli importi"}
            >
              {nascondi ? "👁 Mostra" : "👁‍🗨 Nascondi"}
            </button>
            <span className="pf-conteggio pf-comandi-conteggio">
              {posizioniVisibili.length} di {dettaglio.posizioni.length}
            </span>
          </div>

          <h4 className="pf-sezione">
            Posizioni <span className="pf-conteggio">{dettaglio.posizioni.length}</span>
          </h4>
          {dettaglio.posizioni.length === 0 ? (
            <p className="pf-vuoto">Nessuna posizione aperta.</p>
          ) : posizioniVisibili.length === 0 ? (
            <p className="pf-vuoto">Nessuna posizione con questi filtri.</p>
          ) : (
            <div className="pf-tabella">
              <div className="pf-tabella-testa">
                <button type="button" className="pf-th" onClick={() => ordinaPer("ticker")}>
                  Titolo{freccia("ticker")}
                </button>
                <button type="button" className="pf-th" onClick={() => ordinaPer("strumento")}>
                  Strumento{freccia("strumento")}
                </button>
                <button type="button" className="pf-th" onClick={() => ordinaPer("valuta")}>
                  Valuta{freccia("valuta")}
                </button>
                <button type="button" className="pf-th num" onClick={() => ordinaPer("quantita")}>
                  Quantità{freccia("quantita")}
                </button>
                <button type="button" className="pf-th num" onClick={() => ordinaPer("prezzo_ingresso")}>
                  Pzo di carico{freccia("prezzo_ingresso")}
                </button>
                <button type="button" className="pf-th num" onClick={() => ordinaPer("prezzo_corrente")}>
                  Pzo di mercato{freccia("prezzo_corrente")}
                </button>
                <button type="button" className="pf-th num" onClick={() => ordinaPer("valore_eur")}>
                  Valore €{freccia("valore_eur")}
                </button>
                <button type="button" className="pf-th num" onClick={() => ordinaPer("pnl")}>
                  Var € / %{freccia("pnl")}
                </button>
                <button type="button" className="pf-th num" onClick={() => ordinaPer("netto")}>
                  Netto se vendi{freccia("netto")}
                </button>
                <span />
              </div>

              {posizioniVisibili.map((pos) => {
                const costi = (toNum(pos.costi_ingresso_eur) ?? 0) + (toNum(pos.costo_vendita_eur) ?? 0);
                const base = Number(pos.importo_investito_eur ?? pos.valore_eur ?? 1) || 1;
                const pari = (costi / base) * 100;
                return (
                  <div className="pf-riga-pos" key={pos.id}>
                    <span className="pf-cella titolo" data-label="Titolo">
                      <b>{pos.ticker}</b>
                      <small>{pos.nome}</small>
                    </span>
                    <span className="pf-cella" data-label="Strumento">{pos.strumento || "—"}</span>
                    <span className="pf-cella" data-label="Valuta">{pos.valuta}</span>
                    <span className="pf-cella num" data-label="Quantità">{pos.quantita}</span>
                    <span className="pf-cella num" data-label="Pzo di carico">{prezzo(pos.prezzo_ingresso)}</span>
                    <span className="pf-cella num" data-label="Pzo di mercato">
                      {prezzo(pos.prezzo_corrente)}
                      {!pos.prezzo_valido ? <small className="pf-piccolo">stimato</small> : null}
                    </span>
                    <span className="pf-cella num" data-label="Valore €">{soldi(euro(pos.valore_eur))}</span>
                    <span className={`pf-cella num ${classeDaSegno(pos.pnl_eur)}`} data-label="Var € / %">
                      <b>
                        {pos.pnl_eur > 0 ? "+" : ""}
                        {soldi(euro(pos.pnl_eur))}
                      </b>
                      <small>{nascondi ? "•••" : perc(pos.pnl_pct)}</small>
                    </span>
                    <span
                      className={`pf-cella num netto ${classeDaSegno(pos.pnl_netto_eur)}`}
                      data-label="Netto se vendi"
                      title={`Costi: ${euro(costi)} (commissioni, Tobin, slippage). Per andare in pari serve ${pari.toFixed(2)}%`}
                    >
                      <b>
                        {pos.pnl_netto_eur > 0 ? "+" : ""}
                        {soldi(euro(pos.pnl_netto_eur))}
                      </b>
                      <small>{nascondi ? "•••" : perc(pos.pnl_netto_pct)}</small>
                    </span>
                    <span className="pf-cella azioni" data-label="">
                      {uscita === pos.ticker ? (
                        <>
                          <button
                            type="button"
                            className="btn danger"
                            disabled={vendiMut.isPending}
                            onClick={() => vendiMut.mutate(pos.ticker)}
                          >
                            {vendiMut.isPending ? "Vendo..." : "Confermo"}
                          </button>
                          <button type="button" className="btn ghost" onClick={() => setUscita(null)}>
                            No
                          </button>
                        </>
                      ) : (
                        <button type="button" className="btn ghost" onClick={() => setUscita(pos.ticker)}>
                          Vendi
                        </button>
                      )}
                    </span>
                    <span className="pf-cella nota" data-label="">
                      Stop {prezzo(pos.stop_attuale)} · distanza{" "}
                      {pos.distanza_stop_pct === null ? "—" : `${pos.distanza_stop_pct.toFixed(2)}%`} · costi{" "}
                      {soldi(euro(costi))} · per andare in pari serve <b>{pari.toFixed(2)}%</b>
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {/* ── operazioni chiuse ─────────────────────────────────── */}
          <h4 className="pf-sezione">
            Operazioni chiuse <span className="pf-conteggio">{operazioni.length}</span>
          </h4>
          {operazioni.length === 0 ? (
            <p className="pf-vuoto">Ancora nessuna operazione chiusa.</p>
          ) : (
            <div className="pf-operazioni">
              {operazioni.map((op: OperazioneChiusa, indice) => (
                <div className="pf-operazione" key={`${op.ticker}-${op.data_uscita}-${indice}`}>
                  <span className="pf-operazione-ticker">
                    <b>{op.ticker}</b>
                    <small>{op.motivo_uscita}</small>
                  </span>
                  <span className="pf-operazione-date">
                    <small>{op.data_ingresso} → {op.data_uscita}</small>
                    <small>{op.quantita} × {prezzo(op.prezzo_ingresso)} → {prezzo(op.prezzo_uscita)}</small>
                  </span>
                  <span className={`pf-operazione-esito ${classeDaSegno(op.pnl_netto_eur)}`}>
                    <b>{euro(op.pnl_netto_eur)}</b>
                    <small>
                      {perc(op.pnl_pct)}
                      {op.r_multiplo !== null && op.r_multiplo !== undefined
                        ? ` · ${Number(op.r_multiplo) > 0 ? "+" : ""}${Number(op.r_multiplo).toFixed(2)} R`
                        : ""}
                    </small>
                  </span>
                </div>
              ))}
            </div>
          )}

          <p className="pf-nota">
            Fase 1: le uscite automatiche (stop, obiettivo, trailing) e gli ingressi da segnale
            arriveranno nelle fasi successive. Gli stop sono calcolati e mostrati, ma non agiscono da soli.
          </p>
        </section>
      ) : null}
    </div>
  );
}
