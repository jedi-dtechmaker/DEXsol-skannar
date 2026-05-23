from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .http import get_json
from .models import MarketInsight, PairData, SecuritySummary


EVM_CHAIN_IDS = {
    "ethereum": "1",
    "eth": "1",
    "bsc": "56",
    "polygon": "137",
    "polygon_pos": "137",
    "arbitrum": "42161",
    "base": "8453",
    "optimism": "10",
    "avalanche": "43114",
    "fantom": "250",
    "cronos": "25",
    "linea": "59144",
}

GECKO_NETWORKS = {
    "ethereum": "eth",
    "eth": "eth",
    "bsc": "bsc",
    "polygon": "polygon_pos",
    "polygon_pos": "polygon_pos",
    "arbitrum": "arbitrum",
    "base": "base",
    "optimism": "optimism",
    "avalanche": "avax",
    "fantom": "ftm",
    "cronos": "cro",
    "solana": "solana",
}


def as_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def bool_from_flag(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes"}


class GeckoTerminalClient:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def summarize(self, pair: PairData) -> MarketInsight:
        network = GECKO_NETWORKS.get(pair.chain_id.lower())
        if not network:
            return MarketInsight(source="geckoterminal", note=f"Unsupported GeckoTerminal network: {pair.chain_id}")

        try:
            data = get_json(
                f"https://api.geckoterminal.com/api/v2/networks/{network}/tokens/{pair.base_address}/pools",
                timeout=self.timeout,
                params={"include": "dex"},
            )
        except Exception as exc:
            return MarketInsight(source="geckoterminal", note=f"GeckoTerminal unavailable: {exc}")

        pools = data.get("data") or []
        if not pools:
            return MarketInsight(source="geckoterminal", note="No GeckoTerminal pools found.")

        best = max(pools, key=lambda item: as_float((item.get("attributes") or {}).get("reserve_in_usd")) or 0)
        attrs = best.get("attributes") or {}
        volume = attrs.get("volume_usd") or {}
        price_change = attrs.get("price_change_percentage") or {}
        return MarketInsight(
            source="geckoterminal",
            pool_count=len(pools),
            reserve_usd=as_float(attrs.get("reserve_in_usd")),
            volume_24h_usd=as_float(volume.get("h24")),
            price_change_24h=as_float(price_change.get("h24")),
        )


class GoPlusClient:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def summarize(self, pair: PairData) -> SecuritySummary:
        chain_id = EVM_CHAIN_IDS.get(pair.chain_id.lower())
        if not chain_id:
            return SecuritySummary(source="goplus", note=f"GoPlus token security is EVM-only; chain={pair.chain_id}.")

        try:
            data = get_json(
                f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}",
                timeout=self.timeout,
                params={"contract_addresses": pair.base_address},
            )
        except Exception as exc:
            return SecuritySummary(source="goplus", note=f"GoPlus unavailable: {exc}")

        result = data.get("result") or {}
        token = result.get(pair.base_address.lower()) or result.get(pair.base_address) or {}
        if not token:
            return SecuritySummary(source="goplus", note="GoPlus returned no token-security record.")

        risks: list[str] = []
        warnings: list[str] = []
        flag_labels = {
            "is_honeypot": "GoPlus marks token as honeypot",
            "is_mintable": "Contract appears mintable",
            "is_blacklisted": "Blacklist controls detected",
            "is_proxy": "Proxy contract detected",
            "cannot_sell_all": "Cannot sell all tokens",
            "trading_cooldown": "Trading cooldown detected",
            "is_anti_whale": "Anti-whale controls detected",
        }
        for key, label in flag_labels.items():
            flag = bool_from_flag(token.get(key))
            if flag:
                if key in {"is_honeypot", "cannot_sell_all", "is_blacklisted"}:
                    risks.append(label)
                else:
                    warnings.append(label)

        return SecuritySummary(
            source="goplus",
            is_honeypot=bool_from_flag(token.get("is_honeypot")),
            buy_tax=as_float(token.get("buy_tax")),
            sell_tax=as_float(token.get("sell_tax")),
            owner_address=token.get("owner_address"),
            owner_percent=as_float(token.get("owner_percent")),
            creator_address=token.get("creator_address"),
            creator_percent=as_float(token.get("creator_percent")),
            is_open_source=bool_from_flag(token.get("is_open_source")),
            is_proxy=bool_from_flag(token.get("is_proxy")),
            is_mintable=bool_from_flag(token.get("is_mintable")),
            is_blacklisted=bool_from_flag(token.get("is_blacklisted")),
            is_whitelisted=bool_from_flag(token.get("is_whitelisted")),
            is_anti_whale=bool_from_flag(token.get("is_anti_whale")),
            cannot_buy=bool_from_flag(token.get("cannot_buy")),
            cannot_sell_all=bool_from_flag(token.get("cannot_sell_all")),
            risks=risks,
            warnings=warnings,
        )


class HoneypotClient:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def summarize(self, pair: PairData) -> SecuritySummary:
        chain_id = EVM_CHAIN_IDS.get(pair.chain_id.lower())
        if not chain_id:
            return SecuritySummary(source="honeypot.is", note=f"Honeypot.is is EVM-focused; chain={pair.chain_id}.")

        try:
            data = get_json(
                "https://api.honeypot.is/v2/IsHoneypot",
                timeout=self.timeout,
                params={"address": pair.base_address, "chainID": chain_id},
            )
        except Exception as exc:
            return SecuritySummary(source="honeypot.is", note=f"Honeypot.is unavailable: {exc}")

        hp = data.get("honeypotResult") or {}
        sim = data.get("simulationResult") or {}
        summary = SecuritySummary(
            source="honeypot.is",
            is_honeypot=hp.get("isHoneypot"),
            buy_tax=as_float(sim.get("buyTax")),
            sell_tax=as_float(sim.get("sellTax")),
            can_sell=not hp.get("isHoneypot") if hp.get("isHoneypot") is not None else None,
        )
        reason = hp.get("honeypotReason") or hp.get("reason")
        if summary.is_honeypot:
            summary.risks.append(f"Honeypot simulation failed: {reason or 'unknown reason'}")
        if summary.sell_tax is not None and summary.sell_tax >= 20:
            summary.risks.append(f"High sell tax: {summary.sell_tax:.2f}%")
        elif summary.sell_tax is not None and summary.sell_tax >= 10:
            summary.warnings.append(f"Elevated sell tax: {summary.sell_tax:.2f}%")
        return summary


class RugCheckClient:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def summarize(self, pair: PairData) -> SecuritySummary:
        if pair.chain_id.lower() != "solana":
            return SecuritySummary(source="rugcheck", note=f"RugCheck is Solana-only; chain={pair.chain_id}.")

        try:
            data = get_json(
                f"https://api.rugcheck.xyz/v1/tokens/{pair.base_address}/report/summary",
                timeout=self.timeout,
            )
        except Exception as exc:
            return SecuritySummary(source="rugcheck", note=f"RugCheck unavailable: {exc}")

        risks: list[str] = []
        warnings: list[str] = []
        for item in data.get("risks") or []:
            name = item.get("name") or item.get("description") or "RugCheck risk"
            level = str(item.get("level") or item.get("severity") or "").lower()
            if level in {"danger", "critical", "high"}:
                risks.append(name)
            else:
                warnings.append(name)

        token_meta = data.get("tokenMeta") or {}
        return SecuritySummary(
            source="rugcheck",
            mint_authority=token_meta.get("mintAuthority"),
            freeze_authority=token_meta.get("freezeAuthority"),
            risks=risks[:8],
            warnings=warnings[:8],
            note=f"RugCheck score: {data.get('score', 'n/a')}",
        )


class SecurityAggregator:
    def __init__(self, timeout: int = 15):
        self.goplus = GoPlusClient(timeout)
        self.honeypot = HoneypotClient(timeout)
        self.rugcheck = RugCheckClient(timeout)

    def summarize(self, pair: PairData) -> SecuritySummary:
        if pair.chain_id.lower() == "solana":
            return self.rugcheck.summarize(pair)

        with ThreadPoolExecutor(max_workers=2) as executor:
            goplus_future = executor.submit(self.goplus.summarize, pair)
            honeypot_future = executor.submit(self.honeypot.summarize, pair)
            goplus = goplus_future.result()
            honeypot = honeypot_future.result()
        return merge_security([goplus, honeypot])


def merge_security(items: list[SecuritySummary]) -> SecuritySummary:
    merged = SecuritySummary(source="+".join(item.source for item in items))
    merged.risks = []
    merged.warnings = []
    notes = []
    for item in items:
        for field in (
            "is_honeypot",
            "buy_tax",
            "sell_tax",
            "can_sell",
            "owner_address",
            "owner_percent",
            "creator_address",
            "creator_percent",
            "is_open_source",
            "is_proxy",
            "is_mintable",
            "is_blacklisted",
            "is_whitelisted",
            "is_anti_whale",
            "cannot_buy",
            "cannot_sell_all",
        ):
            if getattr(merged, field) is None and getattr(item, field) is not None:
                setattr(merged, field, getattr(item, field))
        merged.risks.extend(item.risks)
        merged.warnings.extend(item.warnings)
        if item.note:
            notes.append(f"{item.source}: {item.note}")
    merged.note = " | ".join(notes) if notes else None
    return merged
