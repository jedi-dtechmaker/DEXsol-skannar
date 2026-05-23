from __future__ import annotations

from .http import HttpError
from .http import post_json
from .models import HolderSummary, PairData


class HolderProvider:
    def __init__(self, solana_rpc_url: str, timeout: int = 15):
        self.solana_rpc_url = solana_rpc_url
        self.timeout = timeout

    def summarize(self, pair: PairData) -> HolderSummary:
        if pair.chain_id.lower() == "solana":
            return self._solana_largest_accounts(pair.base_address)

        return HolderSummary(
            source="not_configured",
            note=f"{pair.chain_id} holder concentration needs an explorer/API key provider; market, flow, and EVM security checks still run.",
        )

    def _solana_largest_accounts(self, mint: str) -> HolderSummary:
        largest_payload = {
            "jsonrpc": "2.0",
            "id": "dexguard-largest-accounts",
            "method": "getTokenLargestAccounts",
            "params": [mint],
        }
        supply_payload = {
            "jsonrpc": "2.0",
            "id": "dexguard-supply",
            "method": "getTokenSupply",
            "params": [mint],
        }
        try:
            data = post_json(self.solana_rpc_url, largest_payload, timeout=self.timeout)
            supply_data = post_json(self.solana_rpc_url, supply_payload, timeout=self.timeout)
        except HttpError as exc:
            message = str(exc)
            if "HTTP 429" in message or "Too many requests" in message:
                return HolderSummary(
                    source="solana_rpc",
                    note="Solana public RPC rate-limited holder lookup. Use a private RPC URL in SOLANA_RPC_URL for reliable holder data.",
                )
            return HolderSummary(source="solana_rpc", note=f"Solana holder lookup unavailable: {_short_error(message)}")
        except Exception as exc:
            return HolderSummary(source="solana_rpc", note=f"Solana holder lookup unavailable: {_short_error(str(exc))}")

        result = data.get("result") or {}
        accounts = result.get("value") or []
        holders: list[tuple[str, float]] = []
        supply = _ui_amount((supply_data.get("result") or {}).get("value") or {})
        top10_percent = 0.0
        for account in accounts[:10]:
            address = str(account.get("address") or "")
            amount = _ui_amount(account)
            pct = (amount / supply * 100) if supply else 0.0
            top10_percent += pct
            holders.append((address, pct))

        return HolderSummary(
            source="solana_rpc",
            total_holders=None,
            top_holders=holders,
            top10_percent=top10_percent if top10_percent else None,
            note="Solana public RPC returns largest token accounts, not full unique holder count.",
        )


def _ui_amount(value: dict) -> float:
    try:
        if value.get("uiAmount") is not None:
            return float(value.get("uiAmount") or 0)
        if value.get("uiAmountString") is not None:
            return float(value.get("uiAmountString") or 0)
        amount = float(value.get("amount") or 0)
        decimals = int(value.get("decimals") or 0)
        return amount / (10**decimals)
    except (TypeError, ValueError):
        return 0.0


def _short_error(message: str, limit: int = 120) -> str:
    message = " ".join(message.split())
    if len(message) <= limit:
        return message
    return f"{message[:limit]}..."
