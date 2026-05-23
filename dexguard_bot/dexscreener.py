from __future__ import annotations

import time
from typing import Any

from .http import get_json
from .models import PairData, TokenRef


API_BASE = "https://api.dexscreener.com"


def _as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_pair(raw: dict[str, Any]) -> PairData:
    base = raw.get("baseToken") or {}
    quote = raw.get("quoteToken") or {}
    liquidity = raw.get("liquidity") or {}
    return PairData(
        raw=raw,
        chain_id=str(raw.get("chainId") or "unknown"),
        dex_id=str(raw.get("dexId") or "unknown"),
        pair_address=str(raw.get("pairAddress") or ""),
        url=str(raw.get("url") or ""),
        base_address=str(base.get("address") or ""),
        base_name=str(base.get("name") or "Unknown Token"),
        base_symbol=str(base.get("symbol") or "UNKNOWN"),
        quote_symbol=str(quote.get("symbol") or "?"),
        price_usd=_as_float(raw.get("priceUsd")),
        fdv=_as_float(raw.get("fdv")),
        market_cap=_as_float(raw.get("marketCap")),
        liquidity_usd=_as_float(liquidity.get("usd")),
        pair_created_at_ms=_as_int(raw.get("pairCreatedAt")),
        txns=raw.get("txns") or {},
        volume=raw.get("volume") or {},
        price_change=raw.get("priceChange") or {},
        info=raw.get("info") or {},
    )


def _score_pair(pair: dict[str, Any], token_address: str | None = None) -> tuple[float, float]:
    liquidity = _as_float((pair.get("liquidity") or {}).get("usd")) or 0
    volume = _as_float((pair.get("volume") or {}).get("h24")) or 0
    created = _as_int(pair.get("pairCreatedAt")) or 0
    score = liquidity + (volume * 0.15) + (created / 1_000_000_000)
    exact = 0.0
    if token_address:
        token_address = token_address.lower()
        base_address = str((pair.get("baseToken") or {}).get("address") or "").lower()
        if base_address == token_address:
            exact = 1_000_000_000_000
    return exact, score


class DexScreenerClient:
    def __init__(self, timeout: int = 15, cache_ttl_seconds: int = 60):
        self.timeout = timeout
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[float, PairData]] = {}

    def find_best_pair(self, query: str) -> PairData:
        cache_key = query.strip().lower()
        cached = self._cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < self.cache_ttl_seconds:
            return cached[1]

        pair = self._find_best_pair_uncached(query)
        self._cache[cache_key] = (time.monotonic(), pair)
        self._cache[f"{pair.chain_id}:{pair.base_address}".lower()] = (time.monotonic(), pair)
        return pair

    def _find_best_pair_uncached(self, query: str) -> PairData:
        token_ref = parse_token_ref(query)

        if token_ref.chain_id:
            pairs = get_json(
                f"{API_BASE}/tokens/v1/{token_ref.chain_id}/{token_ref.token_address}",
                timeout=self.timeout,
            )
            if pairs:
                best = max(pairs, key=lambda item: _score_pair(item, token_ref.token_address))
                return parse_pair(best)

        search = get_json(
            f"{API_BASE}/latest/dex/search",
            timeout=self.timeout,
            params={"q": token_ref.query},
        )
        pairs = search.get("pairs") or []
        if not pairs:
            raise LookupError(f"No DexScreener pairs found for {query!r}.")
        best = max(pairs, key=lambda item: _score_pair(item, token_ref.token_address or None))
        return parse_pair(best)


def parse_token_ref(query: str) -> TokenRef:
    value = query.strip()
    if ":" in value:
        chain_id, token_address = value.split(":", 1)
        return TokenRef(chain_id=chain_id.strip().lower(), token_address=token_address.strip(), query=value)

    return TokenRef(chain_id="", token_address=value, query=value)
