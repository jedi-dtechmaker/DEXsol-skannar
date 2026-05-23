from __future__ import annotations

import html
from datetime import datetime, timezone
from urllib.parse import quote_plus
from typing import Any

from .models import OutgoingResponse, PairData, ScanResult


def esc(value: Any) -> str:
    return html.escape(str(value), quote=False)


def money(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"${value / 1_000:.2f}K"
    return f"${value:,.2f}"


def pct(value: float | None, signed: bool = True) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.2f}%" if signed else f"{value:.2f}%"


def num(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:,}"


def compact_address(value: str) -> str:
    if len(value) <= 14:
        return value
    return f"{value[:6]}...{value[-6:]}"


def pair_age(pair: PairData) -> str:
    if not pair.pair_created_at_ms:
        return "n/a"
    created = datetime.fromtimestamp(pair.pair_created_at_ms / 1000, tz=timezone.utc)
    delta = datetime.now(timezone.utc) - created
    days = delta.days
    if days:
        return f"{days}d"
    hours = delta.seconds // 3600
    if hours:
        return f"{hours}h"
    return f"{max(1, delta.seconds // 60)}m"


def risk_icon(band: str) -> str:
    return {
        "LOW": "🟢",
        "MODERATE": "🟡",
        "HIGH": "🟠",
        "CRITICAL": "🔴",
    }.get(band, "⚪")


def scan_message(result: ScanResult) -> str:
    pair = result.pair
    h24 = pair.txns.get("h24") or {}
    h1 = pair.txns.get("h1") or {}
    m5 = pair.txns.get("m5") or {}
    links = social_links(pair)
    alerts = "\n".join(f"- {esc(alert)}" for alert in result.risk.alerts[:5])

    lines = [
        f"🛡️ <b>DexGuard Scan: {esc(pair.base_symbol)} / {esc(pair.quote_symbol)}</b>",
        f"{esc(pair.base_name)}",
        f"<code>{esc(pair.base_address)}</code>",
        "",
        f"⚠️ <b>Risk:</b> {risk_icon(result.risk.band)} {result.risk.score}/100 ({esc(result.risk.band)})",
        alerts,
        "",
        "🪙 <b>Coin Information</b>",
        f"⛓️ Chain: <b>{esc(pair.chain_id)}</b> | DEX: <b>{esc(pair.dex_id)}</b> | Age: <b>{pair_age(pair)}</b>",
        f"💵 Price: <b>{money(pair.price_usd)}</b>",
        f"💰 Market Cap: <b>{money(pair.market_cap)}</b> | FDV: <b>{money(pair.fdv)}</b>",
        f"💧 Liquidity: <b>{money(pair.liquidity_usd)}</b>",
        f"📊 Volume 24h: <b>{money(float(pair.volume.get('h24') or 0))}</b>",
        f"📈 Price Change: 5m {pct(pair.price_change.get('m5'))} | 1h {pct(pair.price_change.get('h1'))} | 24h {pct(pair.price_change.get('h24'))}",
        f"🔁 Txns 5m: 🟢 {num(m5.get('buys'))} / 🔴 {num(m5.get('sells'))}",
        f"🔁 Txns 1h: 🟢 {num(h1.get('buys'))} / 🔴 {num(h1.get('sells'))}",
        f"🔁 Txns 24h: 🟢 {num(h24.get('buys'))} / 🔴 {num(h24.get('sells'))}",
        f"👁️ Scan Count: <b>{result.scan_count}</b>",
    ]
    append_section(lines, "🌐 <b>External Market Cross-Check</b>", market_text(result))
    append_section(lines, "🧪 <b>Contract & Trade Security</b>", security_text(result))
    append_section(lines, "🔐 <b>Liquidity Lock</b>", lock_text(result))
    append_section(lines, "🐋 <b>Holder Information</b>", holder_text(result))
    append_section(lines, "🔗 <b>Links</b>", links)
    lines.extend(["", "<i>Informational only. Always do your own due diligence.</i>"])
    return "\n".join(lines)


def append_section(lines: list[str], title: str, body: str) -> None:
    if not body or is_unavailable_text(body):
        return
    lines.extend(["", title, body])


def is_unavailable_text(text: str) -> bool:
    lowered = text.lower()
    unavailable_markers = (
        "timed out",
        "unavailable",
        "disabled for speed",
        "deferred",
        "not available",
    )
    return any(marker in lowered for marker in unavailable_markers)


def scan_card(result: ScanResult) -> OutgoingResponse:
    return OutgoingResponse(
        text=scan_card_caption(result),
        photo_url=token_image_url(result.pair),
        reply_markup=token_keyboard(result),
    )


def scan_card_caption(result: ScanResult) -> str:
    pair = result.pair
    h24 = pair.txns.get("h24") or {}
    alerts = "\n".join(f"- {esc(alert)}" for alert in result.risk.alerts[:3])
    socials = compact_socials(pair)
    lines = [
        f"🛡️ <b>{esc(pair.base_name)} • ${esc(pair.base_symbol)}</b>",
        f"<code>{esc(pair.base_address)}</code>",
        f"⚠️ <b>Risk:</b> {risk_icon(result.risk.band)} {result.risk.score}/100 ({esc(result.risk.band)})",
        alerts,
        "",
        f"⛓️ <b>{esc(pair.chain_id)}</b> | 🧬 <b>{esc(pair.dex_id)}</b> | ⏱️ <b>{pair_age(pair)}</b>",
        f"💵 <b>{money(pair.price_usd)}</b> | 💧 <b>{money(pair.liquidity_usd)}</b>",
        f"💰 MC <b>{money(pair.market_cap)}</b> | FDV <b>{money(pair.fdv)}</b>",
        f"📊 24h Vol <b>{money(float(pair.volume.get('h24') or 0))}</b> | 📈 <b>{pct(pair.price_change.get('h24'))}</b>",
        f"🔁 24h Txns: 🟢 <b>{num(h24.get('buys'))}</b> / 🔴 <b>{num(h24.get('sells'))}</b>",
    ]
    if socials:
        lines.append(f"👻 Socials: {socials}")
    lines.append("👇 <i>Tap Risk Scan or Details for the full breakdown.</i>")
    return "\n".join(lines)


def token_image_url(pair: PairData) -> str | None:
    info = pair.info or {}
    return info.get("header") or info.get("imageUrl") or info.get("openGraph")


def token_keyboard(result: ScanResult) -> dict[str, Any]:
    pair = result.pair
    chart_url = pair.url or dexscreener_search_url(pair)
    share_text = quote_plus(f"DexGuard scan for ${pair.base_symbol}: {chart_url}")
    share_url = f"https://t.me/share/url?url={quote_plus(chart_url)}&text={share_text}"
    keyboard = [
        [
            {"text": f"⚡ Buy ${pair.base_symbol}", "url": chart_url},
            {"text": "👁️ Track", "url": chart_url},
            {"text": "🔁 Share", "url": share_url},
        ],
        [
            {"text": "🕊️ Alpha", "url": gecko_token_url(pair)},
            {"text": "🔥 Trending", "callback_data": "trending"},
        ],
        [
            {"text": "🛡️ Risk Scan", "callback_data": f"risk:{pair.chain_id}:{pair.base_address}"},
        ],
        [
            {"text": "📋 Details", "callback_data": f"details:{pair.chain_id}:{pair.base_address}"},
        ],
    ]
    return {"inline_keyboard": keyboard}


def dexscreener_search_url(pair: PairData) -> str:
    return f"https://dexscreener.com/search?q={quote_plus(pair.base_address)}"


def gecko_token_url(pair: PairData) -> str:
    network = {
        "ethereum": "eth",
        "eth": "eth",
        "bsc": "bsc",
        "polygon": "polygon_pos",
        "arbitrum": "arbitrum",
        "base": "base",
        "optimism": "optimism",
        "avalanche": "avax",
        "solana": "solana",
    }.get(pair.chain_id.lower(), pair.chain_id.lower())
    return f"https://www.geckoterminal.com/{quote_plus(network)}/tokens/{quote_plus(pair.base_address)}"


def compact_socials(pair: PairData) -> str:
    labels = []
    if pair.info.get("websites"):
        labels.append("Web")
    for link in pair.info.get("socials") or []:
        label = str(link.get("type") or "Social").title()
        if label not in labels:
            labels.append(label)
    return " | ".join(labels[:5])


def risk_scan_message(result: ScanResult) -> str:
    pair = result.pair
    status, note = buy_status(result)
    factors = sorted(result.risk.factors.items(), key=lambda item: item[1], reverse=True)
    active_factors = [f"{name.replace('_', ' ').title()}: <b>{score}</b>" for name, score in factors if score]
    alerts = "\n".join(f"- {esc(alert)}" for alert in result.risk.alerts[:6])
    lines = [
        f"🛡️ <b>Risk Scan: {esc(pair.base_symbol)}</b>",
        f"{esc(pair.base_name)}",
        f"<code>{esc(pair.base_address)}</code>",
        "",
        f"⚠️ <b>Risk Score:</b> {risk_icon(result.risk.band)} {result.risk.score}/100 ({esc(result.risk.band)})",
        f"📉 <b>Risk Percent:</b> {result.risk.score}%",
        f"🛒 <b>Buy Status:</b> {buy_status_icon(status)} {esc(status)}",
        f"🧠 <b>Read:</b> {esc(note)}",
        "",
        "🚨 <b>Main Signals</b>",
        alerts or "- No major red flags detected by enabled providers.",
    ]
    if active_factors:
        lines.extend(["", "🧮 <b>Score Breakdown</b>", "\n".join(active_factors[:6])])
    lines.extend(
        [
            "",
            f"✅ Can sell: <b>{yes_no(result.security.can_sell) if result.security.can_sell is not None else 'UNKNOWN'}</b>",
            f"🍯 Honeypot: <b>{yes_no(result.security.is_honeypot) if result.security.is_honeypot is not None else 'UNKNOWN'}</b>",
            f"💸 Tax: buy <b>{tax(result.security.buy_tax)}</b> | sell <b>{tax(result.security.sell_tax)}</b>",
            "",
            "<i>This is a risk screen, not financial advice. Confirm with your own research before buying.</i>",
        ]
    )
    return "\n".join(lines)


def buy_status_icon(status: str) -> str:
    return {
        "LOWER RISK": "🟢",
        "CAUTION": "🟡",
        "HIGH RISK": "🟠",
        "DO NOT BUY": "🔴",
    }.get(status, "⚪")


def buy_status(result: ScanResult) -> tuple[str, str]:
    score = result.risk.score
    security = result.security
    if security.is_honeypot or security.cannot_buy or security.cannot_sell_all:
        return "DO NOT BUY", "Critical trading restriction detected by an enabled provider."
    if security.sell_tax is not None and security.sell_tax >= 20:
        return "DO NOT BUY", "Sell tax is extremely high."
    if score >= 76:
        return "DO NOT BUY", "Critical overall risk score."
    if score >= 51:
        return "HIGH RISK", "Only consider if you understand the risks and position size carefully."
    if score >= 26:
        return "CAUTION", "Moderate risk. Check liquidity, holders, and contract controls before buying."
    return "LOWER RISK", "No major enabled-provider red flags, but still verify manually."


def lock_message(result: ScanResult) -> str:
    pair = result.pair
    return "\n".join(
        [
            f"<b>DexGuard Lock Check: {esc(pair.base_symbol)}</b>",
            f"<code>{esc(pair.base_address)}</code>",
            f"Liquidity: <b>{money(pair.liquidity_usd)}</b>",
            f"Lock Status: <b>{esc(result.lock.status.upper())}</b>",
            f"Locked: <b>{pct(result.lock.locked_percent, signed=False)}</b>",
            f"Unlock Date: <b>{esc(result.lock.unlock_date or 'n/a')}</b>",
            f"Provider: {esc(result.lock.provider or 'n/a')}",
            f"Note: {esc(result.lock.note or 'n/a')}",
        ]
    )


def flow_message(result: ScanResult) -> str:
    pair = result.pair
    lines = [
        f"<b>DexGuard Flow: {esc(pair.base_symbol)}</b>",
        f"<code>{esc(pair.base_address)}</code>",
    ]
    for window in ("m5", "h1", "h6", "h24"):
        tx = pair.txns.get(window) or {}
        vol = float(pair.volume.get(window) or 0)
        lines.append(
            f"{esc(window)}: B <b>{num(tx.get('buys'))}</b> / S <b>{num(tx.get('sells'))}</b> | Vol <b>{money(vol)}</b>"
        )
    return "\n".join(lines)


def market_text(result: ScanResult) -> str:
    market = result.market
    if market.source == "deferred" or is_bad_note(market.note):
        return ""
    lines = [f"Source: {esc(market.source)}"]
    if market.pool_count is not None:
        lines.append(f"Pools found: <b>{num(market.pool_count)}</b>")
    if market.reserve_usd is not None:
        lines.append(f"Best pool reserve: <b>{money(market.reserve_usd)}</b>")
    if market.volume_24h_usd is not None:
        lines.append(f"24h volume: <b>{money(market.volume_24h_usd)}</b>")
    if market.price_change_24h is not None:
        lines.append(f"24h change: <b>{pct(market.price_change_24h)}</b>")
    if market.note:
        lines.append(f"Note: {esc(market.note)}")
    return "\n".join(lines)


def security_text(result: ScanResult) -> str:
    security = result.security
    if security.source == "deferred" or is_bad_note(security.note):
        return ""
    lines = [f"Source: {esc(security.source)}"]
    if security.is_honeypot is not None:
        lines.append(f"Honeypot: <b>{yes_no(security.is_honeypot)}</b>")
    if security.can_sell is not None:
        lines.append(f"Can sell: <b>{yes_no(security.can_sell)}</b>")
    if security.buy_tax is not None or security.sell_tax is not None:
        lines.append(f"Tax: buy <b>{tax(security.buy_tax)}</b> | sell <b>{tax(security.sell_tax)}</b>")
    if security.is_open_source is not None:
        lines.append(f"Open source: <b>{yes_no(security.is_open_source)}</b>")
    controls = security_controls(result)
    if controls:
        lines.append(f"Controls: {controls}")
    if security.owner_percent is not None:
        lines.append(f"Owner holds: <b>{pct(security.owner_percent * 100 if security.owner_percent <= 1 else security.owner_percent, signed=False)}</b>")
    if security.creator_percent is not None:
        lines.append(f"Creator holds: <b>{pct(security.creator_percent * 100 if security.creator_percent <= 1 else security.creator_percent, signed=False)}</b>")
    if security.risks:
        lines.append("Risks:")
        lines.extend(f"- {esc(item)}" for item in security.risks[:4])
    if security.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {esc(item)}" for item in security.warnings[:4])
    if security.note:
        lines.append(f"Note: {esc(security.note)}")
    return "\n".join(lines)


def security_controls(result: ScanResult) -> str:
    security = result.security
    flags = []
    if security.is_mintable:
        flags.append("mintable")
    if security.is_proxy:
        flags.append("proxy")
    if security.is_blacklisted:
        flags.append("blacklist")
    if security.is_whitelisted:
        flags.append("whitelist")
    if security.is_anti_whale:
        flags.append("anti-whale")
    if security.cannot_buy:
        flags.append("cannot buy")
    if security.cannot_sell_all:
        flags.append("cannot sell all")
    if security.mint_authority:
        flags.append("mint authority")
    if security.freeze_authority:
        flags.append("freeze authority")
    return ", ".join(esc(item) for item in flags)


def holder_text(result: ScanResult) -> str:
    holders = result.holders
    if holders.source == "deferred" or is_bad_note(holders.note):
        return ""
    lines = [f"Source: {esc(holders.source)}"]
    if holders.total_holders is not None:
        lines.append(f"Total holders: <b>{num(holders.total_holders)}</b>")
    if holders.top10_percent is not None:
        lines.append(f"Top 10: <b>{pct(holders.top10_percent, signed=False)}</b>")
    if holders.top_holders:
        lines.append("Largest accounts:")
        for address, holder_pct in holders.top_holders[:5]:
            lines.append(f"- <code>{esc(compact_address(address))}</code> {pct(holder_pct, signed=False)}")
    if holders.note:
        lines.append(f"Note: {esc(holders.note)}")
    return "\n".join(lines)


def lock_text(result: ScanResult) -> str:
    lock = result.lock
    if lock.provider == "deferred" or is_bad_note(lock.note):
        return ""
    lines = [
        f"Status: <b>{esc(lock.status.upper())}</b>",
        f"Provider: {esc(lock.provider or 'n/a')}",
    ]
    if lock.locked_percent is not None:
        lines.append(f"Locked: <b>{pct(lock.locked_percent, signed=False)}</b>")
    if lock.unlock_date:
        lines.append(f"Unlock Date: <b>{esc(lock.unlock_date)}</b>")
    if lock.note:
        lines.append(f"Note: {esc(lock.note)}")
    return "\n".join(lines)


def is_bad_note(note: str | None) -> bool:
    if not note:
        return False
    return is_unavailable_text(note)


def yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def tax(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}%"


def social_links(pair: PairData) -> str:
    lines = []
    if pair.url:
        lines.append(f'<a href="{esc(pair.url)}">DexScreener chart</a>')
    for link in (pair.info.get("websites") or [])[:2]:
        url = link.get("url")
        label = link.get("label") or "Website"
        if url:
            lines.append(f'<a href="{esc(url)}">{esc(label)}</a>')
    for link in (pair.info.get("socials") or [])[:4]:
        url = link.get("url")
        label = link.get("type") or "Social"
        if url:
            lines.append(f'<a href="{esc(url)}">{esc(label.title())}</a>')
    return "\n".join(lines) if lines else "n/a"


def help_message() -> str:
    return "\n".join(
        [
            "🛡️ <b>DexGuard Bot Commands</b>",
            '<a href="tg://msg?text=/scan%20">/scan</a> &lt;contract | chain:contract | symbol&gt; - full token report',
            '<a href="tg://msg?text=/lock%20">/lock</a> &lt;contract&gt; - liquidity lock view',
            '<a href="tg://msg?text=/flow%20">/flow</a> &lt;contract&gt; - buy/sell activity',
            '<a href="tg://msg?text=/trending">/trending</a> - most scanned tokens here',
            '<a href="tg://msg?text=/help">/help</a> - this guide',
            "",
            "💡 Tap a command to place it in your message box, then paste the token address.",
            "Example: <code>/scan base:0x...</code>",
        ]
    )


def help_keyboard() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "🛡️ Scan", "switch_inline_query_current_chat": "/scan "},
                {"text": "🔐 Lock", "switch_inline_query_current_chat": "/lock "},
            ],
            [
                {"text": "🔁 Flow", "switch_inline_query_current_chat": "/flow "},
                {"text": "🔥 Trending", "callback_data": "trending"},
            ],
        ]
    }
