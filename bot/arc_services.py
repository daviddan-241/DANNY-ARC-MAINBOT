"""ARC Services — the merged best-of from all four bots.

From DexBoost (My-boss): paid token-growth services with a REAL order
lifecycle (created -> tx submitted -> admin confirms on-chain -> approved).
From Cherry: trending / ads / boost / pump.fun-trending catalog + group add.
From DERA: join-channel & support URL buttons and clean menu structure.

Everything here is real: prices come from env config, payments go to the
admin's REAL treasury addresses, orders carry honest states, and the admin
approves only after verifying the transaction actually landed on-chain.
"""

from __future__ import annotations

import html
import logging
import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot import db
from bot.config import BOT_NAME
from bot.handlers import load_user, require_auth, send_panel

log = logging.getLogger("solo-metro.arc")

HTML = ParseMode.HTML

# ---------------------------------------------------------------- catalog
# Prices are in USD (float) — fully env-configurable. Services are delivered
# manually/semi-automatically by the admin after real payment confirmation.
SERVICES: dict[str, dict] = {
    "vol": {
        "short": "📦 Volume",
        "title": "📦 Volume Package",
        "desc": "Organic-style DEX volume spread over time — depth where scanners look.",
        "packages": [("vol1", "1k volume", 20), ("vol2", "5k volume", 60),
                     ("vol3", "10k volume", 110), ("vol4", "25k volume", 250)],
    },
    "trend": {
        "short": "🔥 DEX Trending",
        "title": "🔥 DEX Trending",
        "desc": "Trending slot on the trending hub — eyes on your chart.",
        "packages": [("tr1", "Top 10 · 6h", 45), ("tr2", "Top 10 · 24h", 120),
                     ("tr3", "Top 3 · 6h", 90), ("tr4", "Top 3 · 24h", 220)],
    },
    "ptrend": {
        "short": "🐸 Pump Trending",
        "title": "🐸 Pump.fun Trending",
        "desc": "Pump.fun launch trending slot — be the one everyone apes.",
        "packages": [("pt1", "Top 10 · 3h", 35), ("pt2", "Top 10 · 12h", 90),
                     ("pt3", "Top 3 · 3h", 70)],
    },
    "ads": {
        "short": "📢 Button Ads",
        "title": "📢 Button Ads",
        "desc": "Your button on the bot menu + trending channel posts.",
        "packages": [("ad1", "3 hours", 25), ("ad2", "12 hours", 70),
                     ("ad3", "24 hours", 120)],
    },
    "vip": {
        "short": "💎 VIP",
        "title": "💎 VIP Membership",
        "desc": "The serious trader's seat: premium slots, call channel access, "
                "priority delivery on every service order, VIP badge and direct support.",
        "packages": [("vip7", "7 days", 15), ("vip30", "30 days", 35),
                     ("vip90", "90 days", 80)],
    },
    "boost": {
        "short": "⚡ Raid Boost",
        "title": "⚡ Raid Boost",
        "desc": "Raid leaderboard boost points for your community.",
        "packages": [("bo1", "1k points", 10), ("bo2", "5k points", 40),
                     ("bo3", "10k points", 75)],
    },
}

PAY_CHAINS = ("SOL", "ETH", "BSC", "BASE", "TRX", "TON")


def _env_float(name: str, default: float) -> float:
    import os

    try:
        return float(os.getenv(name, "") or default)
    except ValueError:
        return default


def _apply_env_prices() -> None:
    """Allow ARC_SVC_PRICE_<id>=99.5 to override any single package price."""
    import os

    for svc in SERVICES.values():
        fixed = []
        for pid, label, price in svc["packages"]:
            fixed.append((pid, label, _env_float(f"ARC_SVC_PRICE_{pid.upper()}", price)))
        svc["packages"] = fixed


_apply_env_prices()


def deliver_order(order: dict) -> str:
    """Real delivery on approve. VIP orders activate the user's premium for
    the purchased days. Returns a short delivery note for the admin."""
    if order.get("service", "").startswith("💎 VIP"):
        import re as _re
        import time as _time

        m = _re.search(r"(\d+)", order.get("label") or "")
        days = int(m.group(1)) if m else 30
        uid = order["user_id"]
        row = db.get_user(uid) or {}
        until = max(float(row.get("premium_until") or 0), _time.time()) + days * 86400
        db.update_user(uid, premium=1, premium_until=until)
        return f"VIP activated for {days}d (user {uid})"
    return ""


def _hub_of(svc_key: str) -> str:
    return "pump" if svc_key in HUBS["pump"] else "dex"


def _pkg(pid: str):
    for svc in SERVICES.values():
        for p in svc["packages"]:
            if p[0] == pid:
                return svc, p
    return None, None


# ---------------------------------------------------------------- treasury
def treasury_for(chain: str) -> str:
    """REAL receiving address per chain from env (set these on Render!)."""
    import os

    return (os.getenv(f"ARC_TREASURY_{chain}") or os.getenv("ARC_TREASURY") or "").strip()


# ---------------------------------------------------------------- keyboards
def _b(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text, callback_data=data)


HUBS = {
    "pump": ("ptrend", "boost"),     # 🚀 Pump Services (Cherry-style)
    "dex": ("vol", "trend", "ads"),  # 📊 DEX Services (DexBoost-style)
}


def fmt_sol(v: float) -> str:
    return f"{v:g} SOL"


def fmt_usd(v: float) -> str:
    return f"${v:g}"


def hub_kb(hub: str) -> InlineKeyboardMarkup:
    """Hub screen: one button per SERVICE (2 per row) — packages live one
    level deeper so nothing is jammed."""
    keys = HUBS.get(hub, ())
    svc_btns = [_b(SERVICES[k]["short"], f"arc:svc:{k}") for k in keys if k in SERVICES]
    rows = [svc_btns[i:i + 2] for i in range(0, len(svc_btns), 2)]
    rows.append([_b("🧾 My orders", "arc:mine"), _b("🛠 All Services", "arc:root")])
    rows.append([_b("🔙 Menu", "nav:main")])
    return InlineKeyboardMarkup(rows)


def vip_links_kb() -> InlineKeyboardMarkup:
    """VIP screen: package buttons 2-per-row + optional channel/support links."""
    from bot.config import CALL_CHANNEL_URL, SUPPORT_URL
    from telegram import InlineKeyboardButton as _IB

    svc = SERVICES["vip"]
    btns = [_b(f"{label} · {fmt_usd(price)}", f"arc:pkg:{pid}")
            for pid, label, price in svc["packages"]]
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)]
    links = []
    if (CALL_CHANNEL_URL or "").strip():
        links.append(_IB("💎 VIP Channel", url=CALL_CHANNEL_URL.strip()))
    if (SUPPORT_URL or "").strip():
        links.append(_IB("💬 Support", url=SUPPORT_URL.strip()))
    if links:
        rows.append(links[:2])
    rows.append([_b("🏠 Menu", "nav:main")])
    return InlineKeyboardMarkup(rows)


def services_root_kb() -> InlineKeyboardMarkup:
    btns = [_b(s["short"], f"arc:svc:{key}") for key, s in SERVICES.items()]
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)]
    rows.append([_b("🧾 My orders", "arc:mine"), _b("🔙 Menu", "nav:main")])
    return InlineKeyboardMarkup(rows)


def packages_kb(svc_key: str, hub: str = "") -> InlineKeyboardMarkup:
    """Service screen: packages 2 per row with SOL prices."""
    svc = SERVICES[svc_key]
    btns = [_b(f"{label} · {fmt_usd(price)}", f"arc:pkg:{pid}")
            for pid, label, price in svc["packages"]]
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)]
    back = f"arc:{hub}" if hub in ("pump", "dex") else "arc:root"
    rows.append([_b("🔙 Back", back), _b("🏠 Menu", "nav:main")])
    return InlineKeyboardMarkup(rows)


def pay_kb(order_id: int, chain: str) -> InlineKeyboardMarkup:
    rows = [
        [_b(f"✅ Paid — sent TX ({chain})", f"arc:paid:{order_id}:{chain}")],
        [_b("🔙 Services", "arc:root")],
    ]
    return InlineKeyboardMarkup(rows)


def order_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[_b("🧾 My orders", "arc:mine"), _b("🔙 Menu", "nav:main")]])


# ---------------------------------------------------------------- flow
async def show_services(update: Update, query=None) -> None:
    await send_panel(
        update,
        f"🛠 <b>{BOT_NAME} Services</b>\n\n"
        "Everything a launch needs, in one place — volume, trending, ads and "
        "raid boosts. Prices in <b>SOL</b>, paid on-chain.\n\n"
        "<b>How it works:</b>\n"
        "1️⃣ Pick a service and package\n"
        "2️⃣ Send payment to the address shown (any major chain)\n"
        "3️⃣ Paste your transaction signature\n"
        "4️⃣ The team verifies it on-chain and delivery starts — you get a "
        "message the moment it's approved.\n\n"
        "No auto-claims. No fake numbers. Every order is real and trackable "
        "in 🧾 My orders.",
        services_root_kb(),
    )


async def _show_packages(update: Update, svc_key: str) -> None:
    svc = SERVICES.get(svc_key)
    if not svc:
        await send_panel(update, "Unknown service.")
        return
    await send_panel(
        update,
        f"{svc['title']}\n\n<i>{svc['desc']}</i>\n\n"
        + "\n".join(f"• <b>{label}</b> — {fmt_usd(price)}"
                    for _, label, price in svc["packages"])
        + "\n\nPrices in USD — auto-converted to your paying chain at checkout. Tap a package:",
        packages_kb(svc_key, _hub_of(svc_key)),
    )


def _is_vip(pid: str) -> bool:
    return pid.startswith("vip")


async def _chain_picker(update: Update, uid: int, pid: str, token: str = "", tsym: str = "") -> None:
    svc, pkg = _pkg(pid)
    _, label, price = pkg
    chain_btns = [_b(ch, f"arc:pick:{pid}:{ch}") for ch in PAY_CHAINS]
    rows = [chain_btns[i:i + 2] for i in range(0, len(chain_btns), 2)]
    rows.append([_b("🔙 Back", "arc:root")])
    tok_line = (f"🎯 Token: <code>{html.escape(token)}</code>" + (f" ({html.escape(tsym)})" if tsym else "") + "\n") if token else ""
    db.set_state(uid, "arc_chain", {"pid": pid, "token": token, "tsym": tsym})
    await send_panel(
        update,
        f"🧾 <b>{svc['title']} — {label}</b>\n"
        f"Price: <b>{fmt_usd(price)}</b>\n"
        f"{tok_line}\n"
        "Pick the chain you'll pay in — the price auto-converts to that "
        "chain's token at the live rate, and the bot shows the REAL "
        "receiving address:",
        InlineKeyboardMarkup(rows),
    )


async def _start_order(update: Update, user: dict, pid: str) -> None:
    uid = user["user_id"]
    svc, pkg = _pkg(pid)
    if not pkg:
        await send_panel(update, "Unknown package.")
        return
    _, label, price = pkg
    if _is_vip(pid):
        await _chain_picker(update, uid, pid)
        return
    db.set_state(uid, "arc_ca", {"pid": pid})
    await send_panel(
        update,
        f"🧾 <b>{svc['title']} — {label}</b> · {fmt_usd(price)}\n\n"
        "🎯 Send the <b>token address (CA) or link</b> this order is for.\n"
        "Any format works: bare CA, DexScreener / pump.fun / GeckoTerminal "
        "link — the bot resolves it on-chain, even for old or dead tokens.\n\n"
        "(Example: <code>https://pump.fun/AbC…</code> or just the CA)",
    )


async def _show_pay_address(update: Update, user: dict, pid: str, chain: str) -> None:
    uid = user["user_id"]
    svc, pkg = _pkg(pid)
    if not pkg:
        await send_panel(update, "Unknown package.")
        return
    _, label, price_usd = pkg
    state, payload = db.get_state(uid)
    payload = payload or {}
    token = payload.get("token", "")
    tsym = payload.get("tsym", "")
    if not token and not _is_vip(pid):
        db.set_state(uid, "arc_ca", {"pid": pid})
        await send_panel(update, "Send the <b>token CA or link</b> for this order first:")
        return
    addr = treasury_for(chain)
    if not addr:
        await send_panel(
            update,
            f"⚠️ {chain} payments are temporarily unavailable — pick another chain "
            "or contact support.")
        return
    native = None
    approx = ""
    try:
        from bot.market import fmt_native, native_usd_price

        px = await native_usd_price(chain)
        if px and px > 0:
            native = price_usd / px
            approx = f"≈ <b>{fmt_native(native, chain)} {chain}</b> at the live rate"
    except Exception:
        approx = ""
    howmuch = (f"Amount: <b>{fmt_usd(price_usd)}</b>" + (f" ({approx})" if approx else "")) if approx else (
        f"Amount: <b>{fmt_usd(price_usd)}</b> — send the equivalent in <b>{chain}</b> at the current rate.")
    order = db.add_service_order(uid, svc["title"], label, chain, price_usd, token=token)
    db.set_state(uid, "arc_tx", {"order": order["id"]})
    try:
        from bot.admin import alert, user_tag

        await alert(
            f"🧾 <b>ORDER #{order['id']} CREATED</b> — {user_tag(user, uid)}\n"
            f"📦 {html.escape(svc['title'])} · {html.escape(label)} — {fmt_usd(price_usd)}"
            + (f"\n🎯 Token: <code>{html.escape(token)}</code>" if token else "")
            + f"\n⛓ {html.escape(chain)} — awaiting payment + TX"
        )
    except Exception:
        pass
    tok_line = (f"🎯 Token: <code>{html.escape(token)}</code>" + (f" ({html.escape(tsym)})" if tsym else "") + "\n") if token else ""
    await send_panel(
        update,
        f"🧾 Order <b>#{order['id']}</b> — {svc['title']} · {label}\n"
        f"{tok_line}"
        f"{howmuch}\n\n"
        f"💰 Receiving address (<b>{chain}</b>):\n<code>{html.escape(addr)}</code>\n\n"
        "After sending, tap the button below and paste your "
        "<b>transaction signature / hash</b>. The team verifies it on-chain "
        "before your order starts.",
        pay_kb(order["id"], chain),
    )


async def _handle_arc_inputs(update: Update, user: dict, text: str) -> bool:
    """States: arc_ca (token for the order) and arc_chain (fallback pick)."""
    uid = user["user_id"]
    state, payload = db.get_state(uid)
    if state not in ("arc_ca", "arc_chain"):
        return False
    if state == "arc_chain":
        # user typed instead of tapping — show the picker again
        pid = payload.get("pid", "")
        await _chain_picker(update, uid, pid, payload.get("token", ""), payload.get("tsym", ""))
        return True
    pid = payload.get("pid", "")
    from bot.handlers import extract_ca

    ca = extract_ca(text)
    if not ca:
        await send_panel(
            update,
            "❌ That doesn't look like a token address or link. Send the CA "
            "(or a DexScreener / pump.fun link) for this order:",
        )
        return True
    sym = ""
    try:
        from bot.market import resolve_token

        info = await resolve_token(ca)
        sym = str(info.get("symbol") or "")[:16]
    except Exception:
        sym = ""
    await _chain_picker(update, uid, pid, ca, sym)
    return True


async def _await_tx(update: Update, user: dict, text: str) -> bool:
    """State: user pastes the tx signature for their service order."""
    uid = user["user_id"]
    state, payload = db.get_state(uid)
    if state != "arc_tx":
        return False
    order_id = int(payload.get("order") or 0)
    order = db.get_service_order(order_id)
    if not order or order["user_id"] != uid:
        db.set_state(uid, None)
        await send_panel(update, "Order not found — open 🛠 Services to start again.")
        return True
    sig = text.strip().split()[0][:120]
    db.set_service_order_status(order_id, "paid_check", tx=sig)
    db.set_state(uid, None)
    from bot.admin import alert, user_tag

    await alert(
        f"🧾 <b>SERVICE ORDER #{order_id} — TX submitted</b>\n"
        f"👤 {user_tag(user, uid)}\n"
        f"📦 {html.escape(order['service'])} · {html.escape(order['label'])} — "
        f"{fmt_usd(order['price_usd'])}\n"
        + (f"🎯 Token: <code>{html.escape(order.get('token') or '')}</code>\n" if order.get("token") else "")
        + f"⛓ {html.escape(order['chain'])}\n"
        f"🔗 TX: <code>{html.escape(sig)}</code>\n\n"
        f"Verify on-chain, then /approve {order_id} or /reject {order_id}"
    )
    await send_panel(
        update,
        f"✅ TX received for order <b>#{order_id}</b>.\n"
        "The team verifies the payment on-chain and your order starts right "
        "after. Track it any time in 🧾 My orders.",
        order_kb(order_id),
    )
    return True


async def maybe_handle_text(update: Update, user: dict, text: str) -> bool:
    """Hook for _on_text: returns True when the message was an ARC flow input."""
    try:
        if await _handle_arc_inputs(update, user, text):
            return True
        return await _await_tx(update, user, text)
    except Exception:
        log.exception("arc text flow")
        return False


# ---------------------------------------------------------------- callbacks
async def handle_callback(update: Update, context, query, user) -> None:
    """Routed from _dispatch_callback for every 'arc:' callback."""
    data = query.data or ""
    uid = user["user_id"]
    parts = data.split(":")
    if data == "arc:root":
        await show_services(update)
    elif data in ("arc:pump", "arc:dex"):
        hub = data.split(":")[1]
        if hub == "pump":
            name = "🚀 <b>Pump Services</b>"
            blurb = (
                "Built for pump.fun launches.\n\n"
                "🐸 <b>Pump Trending</b> — Top 10 / Top 3 slots while your coin "
                "is live. More eyes, more apes, faster curve.\n"
                "⚡ <b>Raid Boost</b> — push your community up the raid "
                "leaderboard and keep it trending.\n\n"
                "Pick a service to see packages and SOL prices:"
            )
        else:
            name = "📊 <b>DEX Services</b>"
            blurb = (
                "Growth for tokens past the launch.\n\n"
                "📦 <b>Volume</b> — organic-style DEX volume spread over time, "
                "so scanners and rankers pick you up.\n"
                "🔥 <b>DEX Trending</b> — trending hub slots, 6h to 24h.\n"
                "📢 <b>Button Ads</b> — your button inside this bot and the "
                "trending channel.\n\n"
                "Pick a service to see packages and SOL prices:"
            )
        await send_panel(update, f"{name}\n\n{blurb}", hub_kb(hub))
    elif data.startswith("arc:svc:"):
        await _show_packages(update, parts[2])
    elif data.startswith("arc:pkg:"):
        await _start_order(update, user, parts[2])
    elif data.startswith("arc:pick:"):
        await _show_pay_address(update, user, parts[2], parts[3].upper())
    elif data.startswith("arc:paid:"):
        order_id = int(parts[2])
        chain = parts[3]
        order = db.get_service_order(order_id)
        if order and order["user_id"] == uid:
            db.set_state(uid, "arc_tx", {"order": order_id})
            await send_panel(
                update,
                f"Paste the <b>{chain} transaction signature / hash</b> for "
                f"order <b>#{order_id}</b> now:",
            )
        else:
            await send_panel(update, "Order not found.")
    elif data == "arc:mine":
        await _my_orders(update, user)


async def _my_orders(update: Update, user: dict) -> None:
    uid = user["user_id"]
    orders = db.list_service_orders(uid)
    if not orders:
        await send_panel(update, "🧾 No service orders yet — pick one in 🛠 Services.", services_root_kb())
        return
    icons = {"pending": "🕐", "paid_check": "🔍", "approved": "✅", "rejected": "❌", "expired": "⌛"}
    lines = ["🧾 <b>Your service orders</b>:"]
    for o in orders[:10]:
        lines.append(
            f"{icons.get(o['status'], '•')} #{o['id']} {html.escape(o['service'])} · "
            f"{html.escape(o['label'])} — {fmt_usd(o['price_usd'])}"
                + (f" · <code>{html.escape((o.get('token') or '')[:10])}…</code>" if o.get("token") else "")
                + f" [{o['status']}]"
        )
    await send_panel(update, "\n".join(lines), services_root_kb())


# ---------------------------------------------------------------- admin cmds
async def cmd_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = load_user(update)
    if not await require_auth(update, user):
        return
    await show_services(update)


async def cmd_myorders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = load_user(update)
    if not await require_auth(update, user):
        return
    await _my_orders(update, user)


def _is_admin(update: Update) -> bool:
    from bot.admin import admin_ids

    try:
        return update.effective_user.id in admin_ids()
    except Exception:
        return False


async def cmd_approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return
    try:
        order_id = int((context.args or ["0"])[0])
    except ValueError:
        order_id = 0
    order = db.get_service_order(order_id)
    if not order:
        await update.effective_message.reply_text("Order not found.")
        return
    db.set_service_order_status(order_id, "approved")
    note = deliver_order(order)
    try:
        await context.bot.send_message(
            order["user_id"],
            f"✅ Your service order <b>#{order_id}</b> ({html.escape(order['service'])} · "
            f"{html.escape(order['label'])}) was <b>approved</b> — delivery is starting. 🚀",
            parse_mode=HTML,
        )
    except Exception:
        pass
    await update.effective_message.reply_text(
        f"✅ Order #{order_id} approved." + (f" | {note}" if note else ""))


async def cmd_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        return
    try:
        order_id = int((context.args or ["0"])[0])
    except ValueError:
        order_id = 0
    order = db.get_service_order(order_id)
    if not order:
        await update.effective_message.reply_text("Order not found.")
        return
    db.set_service_order_status(order_id, "rejected")
    try:
        await context.bot.send_message(
            order["user_id"],
            f"❌ Order <b>#{order_id}</b> could not be verified on-chain and was "
            "rejected. If you believe this is a mistake, contact support with your TX.",
            parse_mode=HTML,
        )
    except Exception:
        pass
    await update.effective_message.reply_text(f"❌ Order #{order_id} rejected.")


async def cmd_orders_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin: all recent service orders."""
    if not _is_admin(update):
        return
    rows = db.all_service_orders(20)
    if not rows:
        await update.effective_message.reply_text("No service orders yet.")
        return
    lines = ["🧾 <b>Recent service orders</b>:"]
    from bot.admin import tag_uid

    for o in rows:
        lines.append(
            f"#{o['id']} [{o['status']}] {tag_uid(o['user_id'])} · "
            f"{html.escape(o['service'])} {html.escape(o['label'])} {fmt_usd(o['price_usd'])} "
            f"{o['chain']}" + (f" tok:<code>{html.escape((o.get('token') or '')[:10])}…</code>" if o.get("token") else "") + (f" tx:<code>{html.escape((o['tx'] or '')[:24])}…</code>" if o["tx"] else "")
        )
    await update.effective_message.reply_text("\n".join(lines), parse_mode=HTML)
