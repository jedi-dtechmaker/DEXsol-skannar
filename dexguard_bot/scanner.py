from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .dexscreener import DexScreenerClient
from .holders import HolderProvider
from .locks import LockProvider
from .models import (
    ScanResult,
    empty_holder_summary,
    empty_lock_summary,
    empty_market_insight,
    empty_security_summary,
)
from .providers import GeckoTerminalClient, SecurityAggregator
from .risk import calculate_risk
from .storage import Storage


class Scanner:
    def __init__(
        self,
        dexscreener: DexScreenerClient,
        holders: HolderProvider,
        locks: LockProvider,
        security: SecurityAggregator,
        market: GeckoTerminalClient,
        storage: Storage,
        deep_enrichment: bool = False,
    ):
        self.dexscreener = dexscreener
        self.holders = holders
        self.locks = locks
        self.security = security
        self.market = market
        self.storage = storage
        self.deep_enrichment = deep_enrichment

    def scan(self, query: str) -> ScanResult:
        return self.deep_scan(query)

    def quick_scan(self, query: str) -> ScanResult:
        pair = self.dexscreener.find_best_pair(query)
        holder_summary = empty_holder_summary()
        lock_summary = empty_lock_summary()
        security_summary = empty_security_summary()
        market_insight = empty_market_insight()
        risk = calculate_risk(pair, lock_summary, holder_summary, security_summary, market_insight)
        scan_count = self.storage.record_scan(pair.chain_id, pair.base_address, pair.base_symbol)
        return ScanResult(
            pair=pair,
            holders=holder_summary,
            lock=lock_summary,
            security=security_summary,
            market=market_insight,
            risk=risk,
            scan_count=scan_count,
        )

    def deep_scan(self, query: str) -> ScanResult:
        if not self.deep_enrichment:
            return self.quick_scan(query)

        pair = self.dexscreener.find_best_pair(query)
        with ThreadPoolExecutor(max_workers=4) as executor:
            holder_future = executor.submit(self.holders.summarize, pair)
            lock_future = executor.submit(self.locks.summarize, pair)
            security_future = executor.submit(self.security.summarize, pair)
            market_future = executor.submit(self.market.summarize, pair)
            holder_summary = holder_future.result()
            lock_summary = lock_future.result()
            security_summary = security_future.result()
            market_insight = market_future.result()
        risk = calculate_risk(pair, lock_summary, holder_summary, security_summary, market_insight)
        scan_count = self.storage.record_scan(pair.chain_id, pair.base_address, pair.base_symbol)
        return ScanResult(
            pair=pair,
            holders=holder_summary,
            lock=lock_summary,
            security=security_summary,
            market=market_insight,
            risk=risk,
            scan_count=scan_count,
        )

    def holder_scan(self, query: str) -> ScanResult:
        if not self.deep_enrichment:
            result = self.quick_scan(query)
            result.holders.note = "Holder enrichment is disabled for speed. Enable DEXGUARD_DEEP_ENRICHMENT=true to use Solana RPC/explorer calls."
            return result

        pair = self.dexscreener.find_best_pair(query)
        holder_summary = self.holders.summarize(pair)
        lock_summary = empty_lock_summary()
        security_summary = empty_security_summary()
        market_insight = empty_market_insight()
        risk = calculate_risk(pair, lock_summary, holder_summary, security_summary, market_insight)
        scan_count = self.storage.record_scan(pair.chain_id, pair.base_address, pair.base_symbol)
        return ScanResult(
            pair=pair,
            holders=holder_summary,
            lock=lock_summary,
            security=security_summary,
            market=market_insight,
            risk=risk,
            scan_count=scan_count,
        )

    def risk_scan(self, query: str) -> ScanResult:
        pair = self.dexscreener.find_best_pair(query)
        if not self.deep_enrichment and pair.chain_id.lower() == "solana":
            holder_summary = empty_holder_summary()
            lock_summary = empty_lock_summary("Verified lock APIs are disabled in fast mode.")
            security_summary = empty_security_summary("Solana RugCheck is disabled in fast mode to avoid slow/time-out responses.")
            market_insight = empty_market_insight()
            risk = calculate_risk(pair, lock_summary, holder_summary, security_summary, market_insight)
            scan_count = self.storage.record_scan(pair.chain_id, pair.base_address, pair.base_symbol)
            return ScanResult(
                pair=pair,
                holders=holder_summary,
                lock=lock_summary,
                security=security_summary,
                market=market_insight,
                risk=risk,
                scan_count=scan_count,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            security_future = executor.submit(self.security.summarize, pair)
            lock_future = executor.submit(self.locks.summarize, pair)
            security_summary = security_future.result()
            lock_summary = lock_future.result()
        holder_summary = empty_holder_summary()
        market_insight = empty_market_insight()
        risk = calculate_risk(pair, lock_summary, holder_summary, security_summary, market_insight)
        scan_count = self.storage.record_scan(pair.chain_id, pair.base_address, pair.base_symbol)
        return ScanResult(
            pair=pair,
            holders=holder_summary,
            lock=lock_summary,
            security=security_summary,
            market=market_insight,
            risk=risk,
            scan_count=scan_count,
        )
