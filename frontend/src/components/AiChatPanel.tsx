import { useEffect, useRef, useState } from "react";
import { sendAiChat } from "../api";
import type { AiChatMessage } from "../types";

type Props = {
  market: string;
};

const SUGGESTIONS = [
  "Quali sono i migliori titoli su MIB30?",
  "Mostrami i BUY con volume sopra 2000",
  "Analizza TEN.MI su MIB30",
  "Scarica una sequenza prezzi recente per NEXI.MI"
];

const STORAGE_KEY = "ifinance-ai-chat-state";
const SESSION_KEY = "ifinance-ai-session";

function makeSessionId(forceNew = false): string {
  const existing = forceNew ? null : window.localStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const next = `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  window.localStorage.setItem(SESSION_KEY, next);
  return next;
}

function formatInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|\b[A-Z0-9]{2,8}\.MI\b|\b(?:TECH_SCORE|TECH|RSI|ADX|MACD_vs_Signal|MACD|Close|Volume|Liquidity|Action|Market_Phase|UPTREND|PULLBACK|BREAKOUT|BUY|SELL|WAIT|OK)\b|-?\d+(?:[.,]\d+)?%?)/g).filter(Boolean);
  return parts.map((part, idx) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={idx}>{part.slice(2, -2)}</strong>;
    }
    if (/^[A-Z0-9]{2,8}\.MI$/.test(part)) {
      return <span key={idx} className="ai-token ticker">{part}</span>;
    }
    if (/^-?\d+(?:[.,]\d+)?%?$/.test(part)) {
      return <span key={idx} className="ai-token number">{part}</span>;
    }
    if (/^(TECH_SCORE|TECH|RSI|ADX|MACD_vs_Signal|MACD|Close|Volume|Liquidity|Action|Market_Phase)$/.test(part)) {
      return <span key={idx} className="ai-token field">{part}</span>;
    }
    if (/^(UPTREND|PULLBACK|BREAKOUT|BUY|SELL|WAIT|OK)$/.test(part)) {
      return <span key={idx} className="ai-token signal">{part}</span>;
    }
    return <span key={idx}>{part}</span>;
  });
}

function formatMessage(content: string) {
  const lines = String(content || "").split("\n");
  const out: JSX.Element[] = [];
  let list: { type: "ul" | "ol"; items: string[] } | null = null;

  function flushList() {
    if (!list) return;
    const Tag = list.type;
    out.push(
      <Tag key={`list-${out.length}`}>
        {list.items.map((item, idx) => (
          <li key={idx}>{formatInline(item)}</li>
        ))}
      </Tag>
    );
    list = null;
  }

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      flushList();
      continue;
    }

    const heading = line.match(/^#{1,3}\s+(.+)$/);
    if (heading) {
      flushList();
      out.push(
        <h4 key={`h-${out.length}`}>
          {formatInline(heading[1])}
        </h4>
      );
      continue;
    }

    const bullet = line.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      if (!list || list.type !== "ul") {
        flushList();
        list = { type: "ul", items: [] };
      }
      list.items.push(bullet[1]);
      continue;
    }

    const numbered = line.match(/^\d+[.)]\s+(.+)$/);
    if (numbered) {
      if (!list || list.type !== "ol") {
        flushList();
        list = { type: "ol", items: [] };
      }
      list.items.push(numbered[1]);
      continue;
    }

    flushList();
    out.push(<p key={`p-${out.length}`}>{formatInline(line)}</p>);
  }

  flushList();
  return out.length ? out : null;
}

export default function AiChatPanel({ market }: Props) {
  const [sessionId, setSessionId] = useState(() => makeSessionId());
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<AiChatMessage[]>(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw) as { messages?: AiChatMessage[] };
      return Array.isArray(parsed.messages) ? parsed.messages : [];
    } catch {
      return [];
    }
  });
  const [mode, setMode] = useState(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return "";
      const parsed = JSON.parse(raw) as { mode?: string };
      return parsed.mode ?? "";
    } catch {
      return "";
    }
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [model, setModel] = useState(() => window.localStorage.getItem("ifinance-openai-model") || "gpt-4o-mini");

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ messages, mode }));
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, mode]);

  function clearChat() {
    setMessages([]);
    setMode("");
    setError("");
    setInput("");
    window.localStorage.removeItem(STORAGE_KEY);
    window.localStorage.removeItem(SESSION_KEY);
    setSessionId(makeSessionId(true));
  }

  async function submit(text?: string) {
    const message = (text ?? input).trim();
    if (!message || busy) return;
    setBusy(true);
    setError("");
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setInput("");
    try {
      const resp = await sendAiChat({ session_id: sessionId, message, model });
      setMessages(resp.messages);
      setMode(resp.mode);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="ai-panel">
      <div className="ai-head">
        <div>
          <h2>IFinance AI</h2>
          <p>Chat con gli Excel, ranking e serie prezzi.</p>
        </div>
        <div className="ai-head-actions">
          {mode ? <span className="ai-mode">{mode}</span> : null}
          <select
            value={model}
            onChange={(e) => {
              const val = e.target.value;
              setModel(val);
              window.localStorage.setItem("ifinance-openai-model", val);
            }}
            className="model-select"
            style={{
              marginRight: "10px",
              padding: "4px 8px",
              borderRadius: "4px",
              border: "1px solid #ccc",
              background: "#fff",
              color: "#333",
              fontSize: "0.85rem",
              cursor: "pointer",
            }}
          >
            <option value="gpt-4o-mini">GPT-4o Mini (Default)</option>
            <option value="gpt-4o">GPT-4o (Completo)</option>
            <option value="o1-mini">o1 Mini (Ragionamento)</option>
            <option value="o3-mini">o3 Mini (Nuovo Ragionamento)</option>
            <option value="o1">o1 (Ragionamento Completo)</option>
            <option value="gpt-5.5">GPT-5.5</option>
            <option value="gpt-5.5-pro">GPT-5.5 Pro</option>
            <option value="gpt-5.4">GPT-5.4</option>
            <option value="gpt-5.4-pro">GPT-5.4 Pro</option>
            <option value="gpt-5.4-mini">GPT-5.4 Mini</option>
            <option value="gpt-5.4-nano">GPT-5.4 Nano</option>
          </select>
          <button className="btn ghost" onClick={clearChat} disabled={busy || messages.length === 0}>
            Nuova chat
          </button>
        </div>
      </div>

      <div className="ai-messages">
        {messages.length === 0 ? (
          <div className="ai-welcome">
            <h3>Come posso aiutarti sui mercati?</h3>
            <p>Puoi chiedere ranking, analisi ticker, segnali tecnici o sequenze prezzi.</p>
            <div className="ai-suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="ai-suggestion" disabled={busy} onClick={() => submit(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, idx) => (
            <div key={`${m.role}-${idx}`} className={m.role === "user" ? "ai-msg user" : "ai-msg assistant"}>
              <div className="ai-avatar">{m.role === "user" ? "Tu" : "AI"}</div>
              <div className="ai-bubble">
                <div className="ai-role">{m.role === "user" ? "Tu" : "IFinance AI"}</div>
                <div className="ai-content">{formatMessage(m.content)}</div>
              </div>
            </div>
          ))
        )}
        {busy ? (
          <div className="ai-msg assistant">
            <div className="ai-avatar">AI</div>
            <div className="ai-bubble">
              <div className="ai-role">IFinance AI</div>
              <div className="ai-typing">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>

      {error ? <p className="err">{error}</p> : null}

      <form
        className="ai-compose"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <textarea
          value={input}
          rows={3}
          placeholder={`Chiedi qualcosa su ${market}, per esempio: analizza STMMI.MI usando anche la serie prezzi`}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <button className="btn" disabled={busy || !input.trim()}>
          {busy ? "Invio..." : "Invia"}
        </button>
      </form>
    </section>
  );
}
