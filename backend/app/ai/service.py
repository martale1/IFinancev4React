from __future__ import annotations

from app.ai.finance_agent import run_finance_chat

_HISTORY: dict[str, list[dict[str, str]]] = {}


async def chat(
    session_id: str,
    message: str,
    model: str | None = None,
    client_history: list[dict[str, str]] | None = None,
) -> dict:
    sid = (session_id or "default").strip() or "default"
    msg = (message or "").strip()
    if not msg:
        return {"session_id": sid, "answer": "Scrivi una domanda.", "mode": "empty", "messages": _HISTORY.get(sid, [])}

    history = _HISTORY.setdefault(sid, [])
    if client_history is not None:
        history[:] = [
            {"role": str(item.get("role", "user")), "content": str(item.get("content", ""))}
            for item in client_history[-20:]
            if item.get("content") and item.get("role") in {"user", "assistant"}
        ]
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
