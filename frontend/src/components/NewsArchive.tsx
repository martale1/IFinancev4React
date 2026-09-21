import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchNewsHistory, type NewsReport } from "../api";

function linkedText(text: string) {
  return text.split(/(\[[^\]]+\]\(https?:\/\/[^\s)]+\))/g).map((part, index) => {
    const match = /^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/.exec(part);
    return match ? <a key={index} href={match[2]} target="_blank" rel="noopener noreferrer">{match[1]}</a> : part;
  });
}

export default function NewsArchive() {
  const [tickerFilter, setTickerFilter] = useState("");
  const [selected, setSelected] = useState<NewsReport | null>(null);
  const history = useQuery({ queryKey: ["news-history"], queryFn: () => fetchNewsHistory({ limit: 500 }), staleTime: 30_000 });
  const reports = useMemo(() => {
    const filter = tickerFilter.trim().toUpperCase();
    return (history.data?.reports ?? []).filter((report) => !filter || report.ticker.toUpperCase().includes(filter));
  }, [history.data?.reports, tickerFilter]);

  return <section className="news-archive" aria-label="Archivio News">
    <div className="news-archive-head">
      <div><h2>📰 Archivio News</h2><p className="muted">Tutte le ricerche riuscite, incluse quelle avviate dal grafico.</p></div>
      <input value={tickerFilter} onChange={(event) => setTickerFilter(event.target.value)} placeholder="Filtra ticker…" aria-label="Filtra archivio news" />
    </div>
    {history.isLoading ? <p>Caricamento archivio…</p> : null}
    {history.isError ? <p className="err">{String(history.error)}</p> : null}
    {!history.isLoading && !reports.length ? <p className="muted">Nessuna ricerca archiviata.</p> : null}
    <div className="news-archive-list">{reports.map((report) => <article className="news-archive-item" key={`${report.history_id ?? report.searched_at}-${report.ticker}`}>
      <div><strong>{report.ticker}</strong><span>{report.name || ""}</span><small>{new Date(report.searched_at).toLocaleString("it-IT")}</small></div>
      <p>{report.text.slice(0, 260)}{report.text.length > 260 ? "…" : ""}</p>
      <button className="btn ghost" onClick={() => setSelected(report)}>Apri report</button>
    </article>)}</div>
    {selected ? <div className="news-archive-detail">
      <header><div><h3>{selected.ticker} · Report News</h3><small>{new Date(selected.searched_at).toLocaleString("it-IT")}</small></div><button className="btn ghost" onClick={() => setSelected(null)}>Chiudi</button></header>
      <article>{linkedText(selected.text)}</article>
      <h4>Fonti</h4><ul>{selected.sources.map((source) => <li key={source.url}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.title}</a></li>)}</ul>
    </div> : null}
  </section>;
}
