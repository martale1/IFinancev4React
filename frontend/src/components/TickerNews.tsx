import { useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { chartUrl } from "../api";
import type { WatchlistRow } from "../types";
import "./TickerNews.css";

type Report = { ticker: string; searched_at: string; text: string; price: number | null;
  price_date: string; sources: { title: string; url: string }[] };
type Result = { report: Report | null };
async function request(url: string, options?: RequestInit): Promise<Result> {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Errore nel caricamento News.");
  return data;
}

function linkedText(text: string) {
  return text.split(/(\[[^\]]+\]\(https?:\/\/[^\s)]+\))/g).map((part, i) => {
    const match = /^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/.exec(part);
    return match ? <a key={i} href={match[2]} target="_blank" rel="noopener noreferrer">{match[1]}</a> : part;
  });
}

type QuickSummary = { items: Array<{ label: string; value: string }>; reportText: string };
function quickSummary(text: string): QuickSummary | null {
  const match = /^\s*\[SINTESI_RAPIDA\]\s*\n([\s\S]*?)\n\[\/SINTESI_RAPIDA\]\s*/.exec(text);
  if (!match) return null;
  const items = match[1].split("\n").map((line) => {
    const separator = line.indexOf(":");
    return separator < 0 ? null : { label: line.slice(0, separator).trim(), value: line.slice(separator + 1).trim() };
  }).filter((item): item is { label: string; value: string } => Boolean(item?.label && item.value));
  return items.length ? { items, reportText: text.slice(match[0].length).trim() } : null;
}

export default function TickerNews({ row, market, onChart }: { row: WatchlistRow; market: string; onChart: (row: WatchlistRow) => void }) {
  const ticker = String(row.Ticker ?? "").trim().toUpperCase();
  const dialog = useRef<HTMLDialogElement>(null);
  const [showChart, setShowChart] = useState(false);
  const [chartRetry, setChartRetry] = useState(0);
  const client = useQueryClient();
  const key = ["ticker-news", ticker];
  const saved = useQuery({ queryKey: key,
    queryFn: () => request(`/api/news?ticker=${encodeURIComponent(ticker)}`),
    enabled: !!ticker, staleTime: Infinity, retry: false });
  const search = useMutation({
    mutationFn: () => request("/api/news/research", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker, market, name: String(row.Name ?? ""),
        price: row.Close == null ? null : Number(row.Close), price_date: String(row.Date ?? "") }),
    }),
    onSuccess: (result) => { client.setQueryData(key, result); },
  });
  const report = saved.data?.report;
  const date = report ? new Date(report.searched_at).toLocaleString("it-IT") : "";
  const summary = report ? quickSummary(report.text) : null;
  return <>
    <button className="btn ghost" disabled={!ticker} onClick={() => dialog.current?.showModal()}
      title={report ? `Ricerca salvata: ${date}` : "Notizie, sentiment e target analisti"}>
      {report ? "News ●" : "News"}
    </button>
    {createPortal(<dialog ref={dialog} className="ticker-news-dialog" aria-label={`News ${ticker}`}>
      <header className="ticker-news-header">
        <div><h2>{ticker} · News e sentiment</h2><p>{String(row.Name ?? "")}</p></div>
        <button className="btn ghost" onClick={() => dialog.current?.close()}>Chiudi</button>
      </header>
      <p>{report ? `Ricerca salvata il ${date}.` : "Nessuna ricerca salvata per questo titolo."}
        {" "}Il risultato resta disponibile fino alla prossima ricerca manuale.</p>
      <button className="btn" disabled={search.isPending || saved.isPending || saved.isError}
        onClick={() => search.mutate()}>{search.isPending ? "Ricerca in corso…" : report ? "Nuova ricerca" : "Cerca notizie"}</button>
      {search.isPending && <p role="status">Ricerca delle fonti e analisi in corso. Puoi chiudere questo pannello; il risultato sarà salvato dal server.</p>}
      {saved.isPending && <p role="status">Caricamento del risultato salvato…</p>}
      {saved.isError && <p role="alert">{saved.error.message} <button className="btn ghost" onClick={() => saved.refetch()}>Riprova caricamento</button></p>}
      {search.isError && <p role="alert">{search.error.message}</p>}
      {report && <>
        <p className="ticker-news-price">Prezzo della card al momento della ricerca: {report.price ?? "n/d"} · data {report.price_date || "non disponibile"}. Non è una quotazione live.</p>
        {summary ? <section className="ticker-news-summary" aria-label="Sintesi rapida">
          <h3>In breve</h3>
          <div className="ticker-news-summary-grid">{summary.items.map((item) => <div key={item.label}>
            <strong>{item.label}</strong><span>{linkedText(item.value)}</span>
          </div>)}</div>
        </section> : null}
        <article className="ticker-news-report">{linkedText(summary?.reportText ?? report.text)}</article>
        <h3>Fonti consultabili</h3>
        <ul>{report.sources.filter(s => /^https?:\/\//.test(s.url)).map(s => <li key={s.url}><a href={s.url} target="_blank" rel="noopener noreferrer">{s.title}</a></li>)}</ul>
      </>}
      {showChart && ticker ? <section className="ticker-news-chart" aria-label={`Grafico ${ticker}`}>
        <h3>Grafico {ticker}</h3>
        <img
          src={`${chartUrl(ticker, 70, "candlestick")}&retry=${chartRetry}`}
          alt={`Grafico ${ticker}`}
          onError={() => { if (chartRetry === 0) setChartRetry(1); }}
        />
      </section> : null}
      <footer className="ticker-news-footer">
        <button className="btn" disabled={!ticker} onClick={() => setShowChart((visible) => !visible)}>
          {showChart ? "Nascondi grafico" : "Apri grafico"}
        </button>
        <button className="btn ghost" disabled={!ticker} onClick={() => { dialog.current?.close(); onChart(row); }}>Grafico completo</button>
        <button className="btn ghost" onClick={() => dialog.current?.close()}>Chiudi</button>
      </footer>
    </dialog>, document.body)}
  </>;
}
