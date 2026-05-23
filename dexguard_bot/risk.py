from __future__ import annotations

from .models import HolderSummary, LockSummary, MarketInsight, PairData, RiskResult, SecuritySummary


def calculate_risk(
    pair: PairData,
    lock: LockSummary,
    holders: HolderSummary,
    security: SecuritySummary,
    market: MarketInsight,
) -> RiskResult:
    factors: dict[str, int] = {
        "liquidity_lock": 0,
        "holder_concentration": 0,
        "contract_security": 0,
        "tax_honeypot": 0,
        "buy_sell_pressure": 0,
        "volume_to_mcap": 0,
        "liquidity_depth": 0,
        "data_completeness": 0,
    }
    alerts: list[str] = []

    if lock.status == "unknown":
        factors["liquidity_lock"] = 18
        alerts.append("Liquidity lock is not verified yet.")
    elif lock.locked_percent is not None and lock.locked_percent < 80:
        factors["liquidity_lock"] = 30
        alerts.append("Less than 80% liquidity appears locked.")

    if holders.top10_percent is not None and holders.top10_percent > 40:
        factors["holder_concentration"] = 25
        alerts.append("Top 10 holders exceed 40% of supply.")
    elif holders.source == "not_configured":
        factors["holder_concentration"] = 8
        alerts.append("Holder distribution is not available for this chain yet.")

    if security.is_honeypot:
        factors["tax_honeypot"] = 25
        alerts.append("Honeypot/security provider reports this token as unsellable.")
    elif security.cannot_sell_all:
        factors["tax_honeypot"] = 18
        alerts.append("Security provider says holders may not be able to sell all tokens.")

    if security.sell_tax is not None:
        if security.sell_tax >= 20:
            factors["tax_honeypot"] = max(factors["tax_honeypot"], 20)
            alerts.append(f"Sell tax is high at {security.sell_tax:.2f}%.")
        elif security.sell_tax >= 10:
            factors["tax_honeypot"] = max(factors["tax_honeypot"], 10)
            alerts.append(f"Sell tax is elevated at {security.sell_tax:.2f}%.")

    hard_security_flags = [
        security.is_blacklisted,
        security.cannot_buy,
    ]
    soft_security_flags = [
        security.is_mintable,
        security.is_proxy,
        security.is_anti_whale,
        security.freeze_authority is not None,
        security.mint_authority is not None,
    ]
    if any(flag is True for flag in hard_security_flags):
        factors["contract_security"] = 20
        alerts.append("Critical contract control flags were detected.")
    elif any(flag is True for flag in soft_security_flags):
        factors["contract_security"] = 10
        alerts.append("Contract/admin control warnings were detected.")

    if security.risks:
        factors["contract_security"] = max(factors["contract_security"], 15)
        alerts.extend(security.risks[:2])

    h24 = pair.txns.get("h24") or {}
    buys = int(h24.get("buys") or 0)
    sells = int(h24.get("sells") or 0)
    if buys == 0 and sells > 0:
        factors["buy_sell_pressure"] = 15
        alerts.append("24h sells exist with no reported buys.")
    elif buys and sells / buys > 2.5:
        factors["buy_sell_pressure"] = 15
        alerts.append("24h sells are more than 2.5x buys.")

    market_cap = pair.market_cap or pair.fdv
    volume_24h = float(pair.volume.get("h24") or 0)
    if market_cap and volume_24h / market_cap > 3:
        factors["volume_to_mcap"] = 15
        alerts.append("24h volume is over 300% of market cap/FDV.")

    if pair.liquidity_usd is None:
        factors["liquidity_depth"] = 10
        alerts.append("Liquidity depth is unavailable.")
    elif pair.liquidity_usd < 10_000:
        factors["liquidity_depth"] = 10
        alerts.append("Liquidity is below $10k.")
    elif pair.liquidity_usd < 50_000:
        factors["liquidity_depth"] = 5
        alerts.append("Liquidity is thin, below $50k.")

    if pair.market_cap is None and pair.fdv is None:
        factors["data_completeness"] = 5
    if not pair.url:
        factors["data_completeness"] += 3
    if market.note and "unavailable" in market.note.lower():
        factors["data_completeness"] += 2

    score = min(100, sum(factors.values()))
    band = risk_band(score)
    if not alerts:
        alerts.append("No major DexScreener-based red flags detected.")
    return RiskResult(score=score, band=band, alerts=alerts, factors=factors)


def risk_band(score: int) -> str:
    if score <= 25:
        return "LOW"
    if score <= 50:
        return "MODERATE"
    if score <= 75:
        return "HIGH"
    return "CRITICAL"
