from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TokenRef:
    chain_id: str
    token_address: str
    query: str


@dataclass
class PairData:
    raw: dict[str, Any]
    chain_id: str
    dex_id: str
    pair_address: str
    url: str
    base_address: str
    base_name: str
    base_symbol: str
    quote_symbol: str
    price_usd: float | None
    fdv: float | None
    market_cap: float | None
    liquidity_usd: float | None
    pair_created_at_ms: int | None
    txns: dict[str, dict[str, int]] = field(default_factory=dict)
    volume: dict[str, float] = field(default_factory=dict)
    price_change: dict[str, float] = field(default_factory=dict)
    info: dict[str, Any] = field(default_factory=dict)


@dataclass
class HolderSummary:
    source: str
    total_holders: int | None = None
    top_holders: list[tuple[str, float]] = field(default_factory=list)
    top10_percent: float | None = None
    note: str | None = None


@dataclass
class LockSummary:
    status: str
    locked_percent: float | None = None
    unlock_date: str | None = None
    provider: str | None = None
    note: str | None = None


@dataclass
class MarketInsight:
    source: str
    token_score: float | None = None
    pool_count: int | None = None
    reserve_usd: float | None = None
    volume_24h_usd: float | None = None
    price_change_24h: float | None = None
    note: str | None = None


@dataclass
class SecuritySummary:
    source: str
    is_honeypot: bool | None = None
    buy_tax: float | None = None
    sell_tax: float | None = None
    can_sell: bool | None = None
    owner_address: str | None = None
    owner_percent: float | None = None
    creator_address: str | None = None
    creator_percent: float | None = None
    mint_authority: str | None = None
    freeze_authority: str | None = None
    is_open_source: bool | None = None
    is_proxy: bool | None = None
    is_mintable: bool | None = None
    is_blacklisted: bool | None = None
    is_whitelisted: bool | None = None
    is_anti_whale: bool | None = None
    cannot_buy: bool | None = None
    cannot_sell_all: bool | None = None
    risks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    note: str | None = None


@dataclass
class RiskResult:
    score: int
    band: str
    alerts: list[str]
    factors: dict[str, int]


@dataclass
class ScanResult:
    pair: PairData
    holders: HolderSummary
    lock: LockSummary
    security: SecuritySummary
    market: MarketInsight
    risk: RiskResult
    scan_count: int


@dataclass
class OutgoingResponse:
    text: str
    photo_url: str | None = None
    reply_markup: dict[str, Any] | None = None
    disable_preview: bool = True
