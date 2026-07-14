from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel

from app.ai.prompts import FINANCE_AGENT_INSTRUCTIONS
from app.ai.tools import (
    get_price_sequence_data,
    get_screening_fields_data,
    screen_tickers_data,
    get_ticker_snapshot_data,
    get_top_tickers_data,
    list_available_markets_data,
)

try:
    from agents import Agent, Runner, function_tool, WebSearchTool
except Exception:  # pragma: no cover - depends on optional local package
    Agent = None
    Runner = None
    function_tool = None
    WebSearchTool = None


class ScreenFilter(BaseModel):
    field: str
    op: str = "=="
    value: str | int | float | bool | list[str] | list[int] | list[float] | None = None


if function_tool is not None:

    @function_tool
    def list_available_markets() -> dict[str, Any]:
        return list_available_markets_data()

    @function_tool
    def get_screening_fields() -> dict[str, Any]:
        return get_screening_fields_data()

    @function_tool
    def screen_tickers(
        market: str = "MIB30",
        filters: list[ScreenFilter] | None = None,
        sort_by: str = "TECH_SCORE",
        sort_dir: str = "desc",
        limit: int = 20,
        columns: list[str] | None = None,
    ) -> dict[str, Any]:
        filter_dicts = [f.model_dump() for f in filters or []]
        return screen_tickers_data(
            market=market,
            filters=filter_dicts,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            columns=columns,
        )

    @function_tool
    def get_top_tickers(market: str = "MIB30", tab: str = "BUY", limit: int = 8, min_volume: int = 2000) -> dict[str, Any]:
        return get_top_tickers_data(market=market, tab=tab, limit=limit, min_volume=min_volume)

    @function_tool
    def get_ticker_snapshot(market: str, ticker: str) -> dict[str, Any]:
        return get_ticker_snapshot_data(market=market, ticker=ticker)

    @function_tool
    def get_price_sequence(ticker: str, period: str = "6mo", bars: int = 30) -> dict[str, Any]:
        return get_price_sequence_data(ticker=ticker, period=period, bars=bars)

else:
    list_available_markets = None
    get_screening_fields = None
    screen_tickers = None
    get_top_tickers = None
    get_ticker_snapshot = None
    get_price_sequence = None


def _build_agent(model_name: str | None = None):
    if Agent is None:
        return None
    model = model_name or os.getenv("OPENAI_AGENT_MODEL", "gpt-4o-mini")
    
    agent_tools = [
        list_available_markets,
        get_screening_fields,
        screen_tickers,
        get_top_tickers,
        get_ticker_snapshot,
        get_price_sequence,
    ]
    if WebSearchTool is not None:
        agent_tools.append(WebSearchTool())
        
    return Agent(
        name="IFinance Analyst",
        instructions=FINANCE_AGENT_INSTRUCTIONS,
        model=model,
        tools=agent_tools,
    )


def _fallback_reply(message: str) -> dict[str, Any]:
    text = message.lower()
    try:
        if "mercat" in text:
            data = list_available_markets_data()
            return {"answer": "Mercati disponibili: " + ", ".join(data["markets"]), "tool_results": [data], "mode": "fallback"}

        if any(word in text for word in ["migliori", "top", "buy"]):
            market = "MIB30"
            for candidate in list_available_markets_data()["markets"]:
                if candidate.lower() in text:
                    market = candidate
                    break
            data = get_top_tickers_data(market=market, tab="BUY", limit=8, min_volume=2000)
            lines = [f"Top BUY su {data['market']} ({data['source_file']}):"]
            for i, row in enumerate(data["items"], start=1):
                lines.append(
                    f"{i}. {row.get('Ticker')} - {row.get('Name')} | TECH {row.get('TECH_SCORE')} | "
                    f"{row.get('Market_Phase')} | Close {row.get('Close')}"
                )
            return {"answer": "\n".join(lines), "tool_results": [data], "mode": "fallback"}

        return {
            "answer": (
                "AI non ancora attiva o OPENAI_API_KEY mancante. Posso gia' rispondere in fallback a domande "
                "tipo: 'migliori titoli su MIB30' oppure 'mercati disponibili'."
            ),
            "tool_results": [],
            "mode": "fallback",
        }
    except Exception as exc:
        return {"answer": f"Errore fallback: {type(exc).__name__}: {exc}", "tool_results": [], "mode": "fallback"}


async def run_finance_chat(message: str, history: list[dict[str, str]] | None = None, model: str | None = None) -> dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY") or Agent is None or Runner is None:
        return _fallback_reply(message)

    recent_history = history[-8:] if history else []
    context_lines = []
    for item in recent_history:
        role = item.get("role", "user")
        content = item.get("content", "")
        if content:
            context_lines.append(f"{role}: {content}")
    context = "\n".join(context_lines)
    prompt = f"Contesto recente:\n{context}\n\nDomanda utente:\n{message}" if context else message

    agent = _build_agent(model_name=model)
    result = await Runner.run(agent, prompt, max_turns=6)
    return {
        "answer": str(getattr(result, "final_output", "")),
        "tool_results": [],
        "mode": "agent",
    }
