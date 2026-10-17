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
