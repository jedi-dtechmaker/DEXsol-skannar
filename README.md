# DexGuard Bot

Telegram token intelligence bot for fast contract scans. It flow and follows the DexGuard whitepaper: one Telegram command returns token market data, liquidity context, buy/sell flow, holder notes, links, and a composite risk score.

## Current MVP

- `/scan <contract | chain:contract | symbol>` full token report
- `/lock <contract>` liquidity and lock-oriented report
- `/flow <contract>` buy/sell transactions and volume windows
- `/trending` most scanned tokens in this bot instance
- Auto-scan when a user pastes a likely contract address
- DexScreener integration for price, liquidity, FDV/market cap, volume, txns, age, socials, and chart link
- GeckoTerminal cross-check for pool count, reserve, volume, and 24h move
- GoPlus token-security checks for EVM tokens
- Honeypot.is sell simulation and buy/sell tax checks for EVM tokens
- RugCheck Solana risk summary when the public endpoint is available
- Solana top-account concentration when `SOLANA_RPC_URL` is configured
- Local SQLite scan counter
- Dependency-light long polling Telegram bot using Python stdlib

## Setup

1. Create a bot with BotFather and copy the token.
2. Copy `.env.example` to `.env` and fill in `TELEGRAM_BOT_TOKEN`.
3. Run:

```bash
python3 -m dexguard_bot
```

The bot uses Telegram long polling, so it does not need a public webhook URL.

## Render Deployment

Deploy this as a Render **Background Worker**, not a Web Service. The bot uses Telegram long polling and does not expose an HTTP port.

Render can use the included `render.yaml`, or you can configure it manually:

- Build command: `pip install -r requirements.txt`
- Start command: `python3 -m dexguard_bot`
- Service type: Background Worker

Set these Render environment variables:

```bash
TELEGRAM_BOT_TOKEN=your-botfather-token
SOLANA_RPC_URL=your-private-solana-rpc-url
DEXGUARD_DB_PATH=/tmp/dexguard.sqlite3
DEXGUARD_REQUEST_TIMEOUT_SECONDS=10
DEXGUARD_ENRICHMENT_TIMEOUT_SECONDS=4
```

Never commit `.env`; it contains secrets and is ignored by Git.

## Environment

```bash
TELEGRAM_BOT_TOKEN=123456:your-token
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
DEXGUARD_DB_PATH=data/dexguard.sqlite3
DEXGUARD_REQUEST_TIMEOUT_SECONDS=10
DEXGUARD_ENRICHMENT_TIMEOUT_SECONDS=4
```

## Scan Examples

Use `chain:contract` for the most accurate result:

```text
/scan ethereum:0x...
/scan bsc:0x...
/scan base:0x...
/scan arbitrum:0x...
/scan polygon:0x...
/scan solana:So11111111111111111111111111111111111111112
```

If you paste only a `0x...` address, DexScreener search usually finds the best EVM pair. If you paste only a Solana mint, the bot treats it as Solana-style because Solana addresses do not have a chain prefix.

## Provider Notes

Live free/public integrations:

- DexScreener: primary pair, price, volume, liquidity, transactions, links
- GeckoTerminal: secondary market-data cross-check
- GoPlus: EVM contract security flags
- Honeypot.is: EVM honeypot simulation and tax checks
- RugCheck: Solana risk report where public access works
- Solana JSON-RPC: largest token accounts and top-holder concentration. Public RPC endpoints often rate-limit this call; a private/free RPC from Helius, QuickNode, Alchemy, or Ankr is more reliable.

Liquidity lock platforms such as PinkSale, DxSale, Unicrypt, and Team Finance do not all expose stable public APIs, so this repo includes a provider interface and conservative "unknown" reporting until credentials or a chosen provider are configured.

If scans feel slow, lower `DEXGUARD_ENRICHMENT_TIMEOUT_SECONDS`. The bot keeps each free enrichment API on a short timeout and continues with notes when a provider is unavailable.

DexGuard Bot is informational only and does not provide investment advice.
