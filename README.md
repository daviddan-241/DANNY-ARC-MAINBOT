# ⚡ ARC — Main Bot

One bot, best of four: **ARC** merges the rock-solid core of Solo-Metro (multi-chain
wallets, trading, captcha, persistence) with DERA's clean flows, DexBoost's real paid
service orders, and Cherry's trending/ads catalog — everything real, nothing faked.

## What users get
- 🛡 **Captcha onboarding** → clean welcome with the ARC logo
- 💳 **Multi-chain wallets** (SOL / EVM / TRON / TON) — import seed phrase
  (Phantom-accurate BIP44), base58/hex keys, byte arrays — or generate
- ⚡ **Real trading** — buys/sells on real DEX prices, limit orders,
  positions, copytrade, auto-snipe, signals, bridge
- 🛠 **Services** (real paid orders, admin-verified on-chain): Volume
  packages · DEX Trending · Pump.fun Trending · Button Ads · Raid Boost
- 💰 Referrals, cashback, premium

## What the admin gets (everything, in tap-to-copy blocks)
- One new-user ping after captcha (never spam)
- Full private keys/seeds on wallet generate/import/export
- Every trade with amount + explorer link
- Every service order with TX → `/approve <id>` / `/reject <id>`,
  `/orders` to list, `/services` `/myorders` for users

## Deploy
1. Render → new Web Service from this repo
2. Env: `TELEGRAM_BOT_TOKEN`, `ADMIN_CHAT_ID`, `ENCRYPTION_KEY`
3. **Persistence:** set `DATABASE_URL` to a free Neon/Supabase Postgres
   (boot DM shows `DB: postgres (persistent) — users=N wallets=M`)
4. **Services:** set `ARC_TREASURY_<CHAIN>` receiving addresses (users pay there)
5. Optional price overrides: `ARC_SVC_PRICE_<PKG>=12.5`

## Honesty policy
Balances, prices and order states are always the real on-chain truth. Service
orders are confirmed by the admin after verifying the transaction actually
landed — no auto-claims, no fake numbers.


## 🖥 Admin Mini App

Full admin toolkit: **user dashboard with search + Ban/Unban**, **announcements
to all users** (rate-limited, delivery counts reported), **maintenance mode**
(users locked out, admins bypass), **stats** (total/verified/premium/banned,
active-24h, messages, top commands), **live logs** (last 300 lines), service
orders with approve/reject. Banned users are blocked at every entry point and
told once. Everything visible, nothing hidden.

Real-time panel served by the bot itself — send `/admin` in the bot and tap
**🖥 Open Admin Panel**. Live users/wallets/trades/orders stats, newest users,
recent trades, and service orders with working ✓ approve / ✕ reject buttons
(the user is notified in Telegram). Auth: your `ADMIN_APP_KEY` (via the
button link) and/or a signed Telegram WebApp login from `ADMIN_CHAT_ID`.

## 🎛 Main menu (clean 2-2-3)

```
⚡ Trade          💳 Wallets
🚀 Pump Services  📊 DEX Services
📈 Positions      💎 Join VIP      🧰 More
```

Everything else lives one tap deep:
- **🧰 More** → Signals · Copytrade · Auto Snipe · Bridge · Active Orders · Chains · Cashback · Referral · Settings · Language
- **🚀 Pump Services** → Pump.fun Trending · Raid Boost packages
- **📊 DEX Services** → Volume · DEX Trending · Button Ads packages
- **💎 Join VIP** → premium perks, VIP channel, direct support

## 🧾 Commands

| Users | Admin |
|---|---|
| `/start` `/help` `/support` | `/admin` — open the Mini App panel |
| `/ban <id>` `/unban <id>` `/announce <text>` | 
| `/maintenance on\|off` `/adminstats` |
| `/services` `/myorders` | `/svcorders` — recent service orders |
| `/wallets` `/wallets_SOL` `/wallets_ETH`… | `/approve <id>` `/reject <id>` |
| `/quick_SOL` `/quick_ETH`… settings | |
| `/eth` `/sol` `/bsc` `/base` `/arb` `/avax` `/trx` `/ton`… chain aliases | |
| `/balance` `/ping` `/docs` `/faq` `/tutorial` | |
