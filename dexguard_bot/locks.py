from __future__ import annotations

from .models import LockSummary, PairData


class LockProvider:
    def summarize(self, pair: PairData) -> LockSummary:
        # Lock APIs differ by launchpad and often require keys or chain-specific contract reads.
        # Return an explicit unknown state instead of pretending liquidity is safe.
        if pair.liquidity_usd is None:
            return LockSummary(status="unknown", note="No liquidity data was returned for this pair.")
        return LockSummary(
            status="unknown",
            provider="not verified",
            note="Pool liquidity is visible, but verified LP-lock data is not available from the enabled free sources.",
        )
