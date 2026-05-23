from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .dexscreener import DexScreenerClient
from .holders import HolderProvider
from .locks import LockProvider
from .models import ScanResult
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
    ):
        self.dexscreener = dexscreener
        self.holders = holders
        self.locks = locks
        self.security = security
        self.market = market
        self.storage = storage

    def scan(self, query: str) -> ScanResult:
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
