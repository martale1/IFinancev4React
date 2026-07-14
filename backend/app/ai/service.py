from __future__ import annotations

from app.ai.finance_agent import run_finance_chat

_HISTORY: dict[str, list[dict[str, str]]] = {}


async def chat(session_id: str, message: str, model: str | None = None) -> dict:
    sid = (session_id or "default").strip() or "default"
    msg = (message or "").strip()
    if not msg:
        return {"session_id": sid, "answer": "Scrivi una domanda.", "mode": "empty", "messages": _HISTORY.get(sid, [])}

    history = _HISTORY.setdefault(sid, [])
    result = await run_finance_chat(msg, history=history, model=model)
    history.append({"role": "user", "content": msg})
    history.append({"role": "assistant", "content": result["answer"]})
    del history[:-20]
    return {
        "session_id": sid,
        "answer": result["answer"],
        "mode": result.get("mode", "agent"),
        "messages": history,
        "tool_results": result.get("tool_results", []),
    }

