/**
 * Chiamate al portafoglio virtuale (fase 1).
 *
 * Le funzioni stanno qui e non sparse nei componenti: quando cambiera' la forma
 * delle risposte (fase 2, uscite automatiche) ci sara' un solo posto da toccare.
 */
import { API_BASE, parseJson } from "./api";
import type {
  AnteprimaAcquisto,
  OperazioneChiusa,
  Portafoglio,
  PortafoglioElenco,
} from "./portafoglioTipi";

export async function fetchPortafogli(): Promise<PortafoglioElenco[]> {
  const resp = await fetch(`${API_BASE}/portafogli`);
  const dati = await parseJson<{ portafogli: PortafoglioElenco[] }>(resp);
  return dati.portafogli ?? [];
}

export async function fetchPortafoglio(id: string): Promise<Portafoglio> {
  const resp = await fetch(`${API_BASE}/portafogli/${encodeURIComponent(id)}`);
  const dati = await parseJson<{ portafoglio: Portafoglio }>(resp);
  return dati.portafoglio;
}

export async function creaPortafoglio(corpo: {
  nome: string;
  capitale: number;
  preset?: string;
  note?: string;
  /** Parametri che sovrascrivono il preset, per esempio `mercati`. */
  parametri?: Record<string, unknown>;
}): Promise<Portafoglio> {
  const resp = await fetch(`${API_BASE}/portafogli`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
  const dati = await parseJson<{ portafoglio: Portafoglio }>(resp);
  return dati.portafoglio;
}

export async function aggiornaPortafoglio(
  id: string,
  corpo: { nome?: string; stato?: string; parametri?: Record<string, unknown>; note?: string },
): Promise<Portafoglio> {
  const resp = await fetch(`${API_BASE}/portafogli/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
  const dati = await parseJson<{ portafoglio: Portafoglio }>(resp);
  return dati.portafoglio;
}

export async function archiviaPortafoglio(id: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/portafogli/${encodeURIComponent(id)}`, { method: "DELETE" });
  await parseJson<{ stato: string }>(resp);
}

export async function anteprimaAcquisto(
  id: string,
  ticker: string,
  importoEur?: number,
): Promise<AnteprimaAcquisto> {
  const parametri = new URLSearchParams({ ticker });
  if (importoEur && importoEur > 0) parametri.set("importo_eur", String(importoEur));
  const resp = await fetch(
    `${API_BASE}/portafogli/${encodeURIComponent(id)}/anteprima?${parametri.toString()}`,
  );
  return parseJson<AnteprimaAcquisto>(resp);
}

export async function compraTitolo(
  id: string,
  corpo: { ticker: string; importo_eur?: number; quantita?: number; motivo?: string },
): Promise<Portafoglio> {
  const resp = await fetch(`${API_BASE}/portafogli/${encodeURIComponent(id)}/compra`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
  const dati = await parseJson<{ portafoglio: Portafoglio }>(resp);
  return dati.portafoglio;
}

export async function vendiTitolo(
  id: string,
  corpo: { ticker: string; motivo?: string; quantita?: number },
): Promise<Portafoglio> {
  const resp = await fetch(`${API_BASE}/portafogli/${encodeURIComponent(id)}/vendi`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
  });
  const dati = await parseJson<{ portafoglio: Portafoglio }>(resp);
  return dati.portafoglio;
}

export async function fetchOperazioniPortafoglio(id: string): Promise<OperazioneChiusa[]> {
  const resp = await fetch(`${API_BASE}/portafogli/${encodeURIComponent(id)}/operazioni`);
  const dati = await parseJson<{ operazioni: OperazioneChiusa[] }>(resp);
  return dati.operazioni ?? [];
}

/** Titoli dei mercati abilitati che corrispondono al testo cercato. */
export async function fetchCandidati(
  id: string,
  testo: string,
): Promise<Array<{ ticker: string; nome: string; mercato: string; indicazione?: string | null; tech_score?: number | null }>> {
  const parametri = new URLSearchParams({ q: testo });
  const resp = await fetch(`${API_BASE}/portafogli/${encodeURIComponent(id)}/candidati?${parametri.toString()}`);
  const dati = await parseJson<{ candidati: Array<{ ticker: string; nome: string; mercato: string }> }>(resp);
  return dati.candidati ?? [];
}

export type EsitoGiro = {
  portafoglio: Portafoglio;
  eseguiti: Array<{
    ticker: string;
    nome: string;
    mercato: string;
    quantita: number;
    prezzo: number;
    importo_eur: number;
    tech_score: number;
    indicazione: string;
    stop: number;
  }>;
  scarti: Array<{ ticker: string; motivo: string; dettaglio?: string }>;
  candidati_valutati: number;
  analisi_usate: Record<string, string>;
  liquidita_dopo: number;
};

/** Un giro di ingressi decisi dal sistema, secondo il profilo del portafoglio. */
export async function eseguiGiro(id: string): Promise<EsitoGiro> {
  const resp = await fetch(`${API_BASE}/portafogli/${encodeURIComponent(id)}/esegui`, {
    method: "POST",
  });
  return parseJson<EsitoGiro>(resp);
}
