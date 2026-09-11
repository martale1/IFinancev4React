import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createCustomWatchlist, fetchCustomWatchlists } from "../api";

type Item = { Ticker: string; Name: string; Source_Market?: string };
async function request(url: string, method = "GET", body?: unknown) {
  const response = await fetch(url, { method, headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Operazione non riuscita");
  return data;
}
export default function WatchlistsPanel({ markets, initialMarket, onDeleted, onOpen }: { markets: string[]; initialMarket: string; onDeleted: (m: string) => void; onOpen: (m: string) => void }) {
  const qc = useQueryClient();
  const [selected, setSelected] = useState(initialMarket);
  const [name, setName] = useState("");
  const [ticker, setTicker] = useState("");
  const [company, setCompany] = useState("");
  const [source, setSource] = useState("MIB30");
  const [filter, setFilter] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const custom = selected.startsWith("WL:");
  const lists = useQuery({ queryKey: ["custom-watchlists"], queryFn: fetchCustomWatchlists });
  const items = useQuery<{ items: Item[] }>({ queryKey: ["list-items", selected], queryFn: () => request(`/api/ticker-lists/${encodeURIComponent(selected)}`) });
  async function act(action: () => Promise<unknown>) {
    setBusy(true); setError("");
    try {
      await action();
      await Promise.all(["custom-watchlists", "markets", "list-items", "watchlist", "heatmap"].map(key => qc.invalidateQueries({ queryKey: [key] })));
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  function choose(value: string) { setSelected(value); setFilter(""); setConfirmDelete(false); setError(""); }
  const visible = (items.data?.items ?? []).filter(i => `${i.Ticker} ${i.Name}`.toLowerCase().includes(filter.toLowerCase()));
  return <section className="watchlists-manager">
    <header><h2>Gestisci liste</h2><p className="muted">Crea le tue watchlist e scegli quali titoli seguire. Le liste dei mercati restano disponibili per l’analisi.</p></header>
    <form className="watchlists-actions" onSubmit={e => { e.preventDefault(); if (name.trim()) void act(async () => { const result = await createCustomWatchlist(name.trim()); choose(`WL:${result.name}`); setName(""); }); }}>
      <label>Nuova watchlist<input value={name} onChange={e => setName(e.target.value)} placeholder="Es. Titoli da seguire" /></label>
      <button className="btn" disabled={busy || !name.trim()}>Crea lista</button>
    </form>
    <div className="watchlists-layout">
      <aside aria-label="Liste disponibili">
        <strong>Le mie watchlist</strong>
        {(lists.data?.watchlists ?? []).map(l => <button disabled={busy} className={`market-option ${selected === `WL:${l.name}` ? "selected" : ""}`} key={l.name} onClick={() => choose(`WL:${l.name}`)}>{l.name} · {l.size}</button>)}
        {!lists.data?.watchlists.length && <p className="muted">Crea la tua prima watchlist.</p>}
        {lists.isError && <p className="err">{String(lists.error)}</p>}
        <strong>Liste dei mercati</strong>
        {markets.filter(m => !m.startsWith("WL:")).map(m => <button disabled={busy} key={m} className={`market-option ${selected === m ? "selected" : ""}`} onClick={() => choose(m)}>{m}</button>)}
      </aside>
      <div className="watchlists-detail">
        <div className="watchlists-actions"><h3>{custom ? selected.slice(3) : selected} <small>· {items.data?.items.length ?? 0} titoli</small></h3><button className="btn ghost" disabled={busy} onClick={() => onOpen(selected)}>Apri schede</button>{custom && <button className="btn ghost" disabled={busy} onClick={() => setConfirmDelete(true)}>Elimina lista</button>}</div>
        {confirmDelete && <div className="watchlists-confirm" role="alert"><p>Eliminare “{selected.slice(3)}” e i suoi collegamenti ai titoli? I titoli nei mercati originali restano disponibili.</p><button className="btn" disabled={busy} onClick={() => void act(async () => { const removed = selected; await request(`/api/custom-watchlists/${encodeURIComponent(selected.slice(3))}`, "DELETE"); choose("Preferite"); onDeleted(removed); })}>Conferma eliminazione</button> <button className="btn ghost" disabled={busy} onClick={() => setConfirmDelete(false)}>Annulla</button></div>}
        <form className="watchlists-actions" onSubmit={e => { e.preventDefault(); void act(async () => { await request(`/api/ticker-lists/${encodeURIComponent(selected)}/add`, "POST", { ticker: ticker.trim(), name: company.trim() || ticker.trim(), source_market: source }); setTicker(""); setCompany(""); }); }}>
          <label>Ticker completo<input required value={ticker} placeholder="Es. FCT.MI" onChange={e => setTicker(e.target.value)} /></label>
          {!custom && <label>Nome<input required value={company} onChange={e => setCompany(e.target.value)} /></label>}
          {custom && <label>Mercato di origine<select value={source} onChange={e => setSource(e.target.value)}>{markets.filter(m => !m.startsWith("WL:")).map(m => <option key={m}>{m}</option>)}</select></label>}
          <button className="btn" disabled={busy || !ticker.trim()}>Aggiungi titolo</button>
        </form>
        {!custom && <p className="muted">Le modifiche a questa lista saranno recepite dalle schede alla prossima analisi.</p>}
        <label>Filtra titoli<input value={filter} onChange={e => setFilter(e.target.value)} placeholder="Ticker o nome" /></label>
        {error && <p className="err" role="alert">{error}</p>}
        {items.isLoading ? <p>Caricamento…</p> : items.isError ? <p className="err">{String(items.error)}</p> : <ul className="watchlists-items">{visible.map(i => <li key={`${i.Ticker}:${i.Source_Market}`}><div><strong>{i.Ticker}</strong><span>{i.Name !== i.Ticker ? i.Name : i.Source_Market}</span></div><button className="btn ghost" disabled={busy} onClick={() => void act(() => request(`/api/ticker-lists/${encodeURIComponent(selected)}/remove`, "POST", { ticker: i.Ticker, source_market: i.Source_Market }))}>Rimuovi</button></li>)}{!visible.length && <li>Nessun titolo{filter ? " corrispondente" : " nella lista"}.</li>}</ul>}
      </div>
    </div>
  </section>;
}
