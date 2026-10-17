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
            <span className="pf-riga-numeri">
              <b>{euro(p.liquidita)}</b>
              <small>liquidi · {p.num_posizioni} posizioni · {p.num_operazioni} operazioni</small>
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

          <div className="pf-numeri">
            <div className="pf-numero">
              <small>Valore totale</small>
              <b>{euro(dettaglio.valore_totale)}</b>
            </div>
            <div className="pf-numero">
              <small>Risultato</small>
              <b className={classeDaSegno(dettaglio.pnl_totale_eur)}>
                {euro(dettaglio.pnl_totale_eur)} <span>({perc(dettaglio.pnl_totale_pct)})</span>
              </b>
            </div>
            <div className="pf-numero">
              <small>Liquidi</small>
              <b>{euro(dettaglio.liquidita)}</b>
            </div>
            <div className="pf-numero">
              <small>Esposizione</small>
              {/* Non e' una variazione: niente segno + davanti. */}
              <b>
                {(toNum(dettaglio.esposizione_pct) ?? 0).toLocaleString("it-IT", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
                %
              </b>
            </div>
          </div>

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
            <p className="pf-giro-spiega">
              Il sistema legge l&apos;analisi più recente dei mercati abilitati
              ({(dettaglio.parametri.mercati ?? []).join(", ") || "nessuno"}), sceglie i titoli che
              rispettano il profilo — indicazione {dettaglio.parametri.ingressi_da.join(" o ")},
              TECH ≥ {dettaglio.parametri.tech_score_min}, rischio{" "}
              {dettaglio.parametri.rischio_ammesso.join(" o ")} — e compra fino al limite di cassa,
              posizioni e tetto per titolo. Non vende: gli stop sono calcolati ma non agiscono ancora.
            </p>
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
          <h4 className="pf-sezione">
            Posizioni <span className="pf-conteggio">{dettaglio.posizioni.length}</span>
          </h4>
          {dettaglio.posizioni.length === 0 ? (
            <p className="pf-vuoto">Nessuna posizione aperta.</p>
          ) : (
            <div className="pf-posizioni">
              {dettaglio.posizioni.map((pos) => (
                <div className="pf-posizione" key={pos.id}>
                  <div className="pf-posizione-testa">
                    <span className="pf-posizione-ticker">
                      <b>{pos.ticker}</b>
                      <small>{pos.nome}</small>
                    </span>
                    <span className="pf-posizione-prezzo">
                      <b>{prezzo(pos.prezzo_corrente)}</b>
                      <small className={classeDaSegno(pos.pnl_pct)}>{perc(pos.pnl_pct)}</small>
                    </span>
                  </div>
                  <div className="pf-posizione-numeri">
                    <span>Quantità <b>{pos.quantita}</b></span>
                    <span>Ingresso <b>{prezzo(pos.prezzo_ingresso)}</b></span>
                    <span>Valore <b>{euro(pos.valore_eur)}</b></span>
                    <span title="Solo movimento di prezzo: non comprende le commissioni">
                      Prezzo{" "}
                      <b className={classeDaSegno(pos.pnl_eur)}>{euro(pos.pnl_eur)}</b>
                      <small className="pf-piccolo">{perc(pos.pnl_pct)}</small>
                    </span>
                    <span title="Se vendessi adesso: dopo commissioni di acquisto e vendita, Tobin e slippage">
                      Netto{" "}
                      <b className={classeDaSegno(pos.pnl_netto_eur)}>{euro(pos.pnl_netto_eur)}</b>
                      <small className="pf-piccolo">{perc(pos.pnl_netto_pct)}</small>
                    </span>
                    <span>Stop <b>{prezzo(pos.stop_attuale)}</b></span>
                    <span>
                      Distanza stop{" "}
                      <b className={classeDaSegno(-(pos.distanza_stop_pct ?? 0))}>
                        {pos.distanza_stop_pct === null ? "—" : `${pos.distanza_stop_pct.toFixed(2)}%`}
                      </b>
                    </span>
                  </div>
                  <p className="pf-costi-posizione">
                    Costi d&apos;ingresso {euro(pos.costi_ingresso_eur)} · costo di vendita{" "}
                    {euro(pos.costo_vendita_eur)} · per andare in pari serve{" "}
                    <b>
                      {(
                        ((toNum(pos.costi_ingresso_eur) ?? 0) + (toNum(pos.costo_vendita_eur) ?? 0)) /
                        Math.max(Number(pos.importo_investito_eur ?? pos.valore_eur ?? 1), 1) *
                        100
                      ).toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      %
                    </b>
                  </p>
                  {!pos.prezzo_valido ? (
                    <p className="pf-avvertenza">Prezzo non disponibile: il valore usa il prezzo d&apos;ingresso.</p>
                  ) : null}
                  <div className="pf-posizione-azioni">
                    {uscita === pos.ticker ? (
                      <>
                        <button
                          type="button"
                          className="btn danger"
                          disabled={vendiMut.isPending}
                          onClick={() => vendiMut.mutate(pos.ticker)}
                        >
                          {vendiMut.isPending ? "Vendo..." : "Confermo la vendita"}
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
                  </div>
                </div>
              ))}
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
