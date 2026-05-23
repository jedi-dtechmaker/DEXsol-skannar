import unittest

from dexguard_bot.models import HolderSummary, LockSummary, MarketInsight, PairData, SecuritySummary
from dexguard_bot.risk import calculate_risk


class RiskTests(unittest.TestCase):
    def test_unknown_lock_adds_moderate_risk(self):
        pair = PairData(
            raw={},
            chain_id="bsc",
            dex_id="pancakeswap",
            pair_address="pair",
            url="https://example.com",
            base_address="0xabc",
            base_name="Token",
            base_symbol="TOK",
            quote_symbol="WBNB",
            price_usd=1,
            fdv=100_000,
            market_cap=100_000,
            liquidity_usd=20_000,
            pair_created_at_ms=None,
            txns={"h24": {"buys": 10, "sells": 5}},
            volume={"h24": 30_000},
            price_change={},
            info={},
        )
        result = calculate_risk(
            pair,
            LockSummary(status="unknown"),
            HolderSummary(source="not_configured"),
            SecuritySummary(source="test"),
            MarketInsight(source="test"),
        )
        self.assertEqual(result.band, "MODERATE")
        self.assertGreaterEqual(result.score, 26)


if __name__ == "__main__":
    unittest.main()
