from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WatchlistResponse(BaseModel):
    market: str
    tab: str
    source_file: str | None = None
    source_path: str | None = None
    source_updated_at: str | None = None
    page: int
    page_size: int
    total_rows: int
    total_pages: int
    items: list[dict[str, Any]]


class AlertUpsertRequest(BaseModel):
    payload: dict[str, Any]


class AiAlertCreateRequest(BaseModel):
    ticker: str
    conditions: list[dict[str, Any]]
    title: str | None = None


class AiLevelAlertCreateRequest(BaseModel):
    ticker: str
    level: dict[str, Any]


class AlertToggleRequest(BaseModel):
    enabled: bool


class RunEngineRequest(BaseModel):
    market: str | None = None
    markets: list[str] | None = None
    run_only_this_market: bool = True
    telegram_channel: int = Field(default=5, ge=1, le=50)


class ExportPdfRequest(BaseModel):
    market: str
    bars: int = Field(default=70, ge=30, le=400)
    chart_type: str = Field(default="candlestick")


class CustomWatchlistCreateRequest(BaseModel):
    name: str


class CustomWatchlistAddItemRequest(BaseModel):
    name: str
    ticker: str
    source_market: str


class CustomWatchlistRemoveItemRequest(BaseModel):
    name: str
    ticker: str
    source_market: str | None = None


class AiChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    model: str | None = None
    history: list[dict[str, str]] = []


class AiChatResponse(BaseModel):
    session_id: str
    answer: str
    mode: str = "agent"
    messages: list[dict[str, str]] = []
    tool_results: list[dict[str, Any]] = []
