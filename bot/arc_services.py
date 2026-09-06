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
        "title": "📦 Volume Package",
        "desc": "Organic-style DEX volume spread over time.",
        "packages": [("vol1", "1k volume", 15.0), ("vol2", "5k volume", 60.0),
                     ("vol3", "10k volume", 110.0), ("vol4", "25k volume", 250.0)],
    },
    "trend": {
        "title": "🔥 DEX Trending",
        "desc": "Trending slot on the trending hub.",
        "packages": [("tr1", "Top 10 · 6h", 45.0), ("tr2", "Top 10 · 24h", 120.0),
                     ("tr3", "Top 3 · 6h", 90.0), ("tr4", "Top 3 · 24h", 220.0)],
    },
    "ptrend": {
        "title": "🐸 Pump.fun Trending",
        "desc": "Pump.fun launch trending slot.",
        "packages": [("pt1", "Top 10 · 3h", 35.0), ("pt2", "Top 10 · 12h", 90.0),
                     ("pt3", "Top 3 · 3h", 70.0)],
    },
    "ads": {
        "title": "📢 Button Ads",
        "desc": "Your button on the bot menu + trending channel posts.",
        "packages": [("ad1", "3 hours", 25.0), ("ad2", "12 hours", 70.0),
                     ("ad3", "24 hours", 120.0)],
    },
    "boost": {
        "title": "⚡ Raid Boost",
        "desc": "Raid leaderboard boost points for your community.",
        "packages": [("bo1", "1k points", 10.0), ("bo2", "5k points", 40.0),
                     ("bo3", "10k points", 75.0)],
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
    "pump": ("ptrend", "boost"),   # 🚀 Pump Services (Cherry-style)
    "dex": ("vol", "trend", "ads"),  # 📊 DEX Services (DexBoost-style)
}


def hub_kb(hub: str) -> InlineKeyboardMarkup:
    rows = []
    seen = set()
    for svc_key in HUBS.get(hub, ()):
        if svc_key in seen:
            continue
        seen.add(svc_key)
        svc = SERVICES[svc_key]
        for pid, label, price in svc["packages"]:
            rows.append([_b(f"{svc['title']} · {label} — ${price:g}", f"arc:pkg:{pid}")])
    rows.append([_b("🧾 My orders", "arc:mine"), _b("🔙 Menu", "nav:main")])
    return InlineKeyboardMarkup(rows)


def services_root_kb() -> InlineKeyboardMarkup:
    rows = [[_b(s["title"], f"arc:svc:{key}")] for key, s in SERVICES.items()]
    rows.append([_b("🧾 My orders", "arc:mine"), _b("🔙 Menu", "nav:main")])
    return InlineKeyboardMarkup(rows)


def packages_kb(svc_key: str) -> InlineKeyboardMarkup:
    svc = SERVICES[svc_key]
    rows = [[_b(f"{label} — ${price:g}", f"arc:pkg:{pid}")] for pid, label, price in svc["packages"]]
    rows.append([_b("🔙 Services", "arc:root")])
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
        "Real promotion packages, paid on-chain and confirmed by hand — "
        "nothing is auto-claimed, nothing is fake.\n\n"
        "Pick a service to see packages and prices:",
        services_root_kb(),
    )


async def _show_packages(update: Update, svc_key: str) -> None:
    svc = SERVICES.get(svc_key)
    if not svc:
        await send_panel(update, "Unknown service.")
        return
    await send_panel(
        update,
        f"{svc['title']}\n<i>{svc['desc']}</i>\n\nPick a package:",
        packages_kb(svc_key),
    )


async def _start_order(update: Update, user: dict, pid: str) -> None:
    uid = user["user_id"]
    svc, pkg = _pkg(pid)
    if not pkg:
        await send_panel(update, "Unknown package.")
        return
    _, label, price = pkg
    rows = [[_b(ch, f"arc:pick:{pid}:{ch}")] for ch in PAY_CHAINS]
    rows.append([_b("🔙 Services", "arc:root")])
    db.set_state(uid, None)
    await send_panel(
        update,
        f"🧾 <b>{svc['title']} — {label}</b>\n"
        f"Price: <b>${price:g}</b>\n\n"
        "Pick the chain you'll pay in (the bot shows the REAL receiving "
        "address for that chain):",
        InlineKeyboardMarkup(rows),
    )


async def _show_pay_address(update: Update, user: dict, pid: str, chain: str) -> None:
    uid = user["user_id"]
    svc, pkg = _pkg(pid)
    if not pkg:
        await send_panel(update, "Unknown package.")
        return
    _, label, price = pkg
    addr = treasury_for(chain)
    if not addr:
        await send_panel(
            update,
            f"⚠️ {chain} payments are temporarily unavailable — pick another chain "
            "or contact support.",
            packages_kb(svc and next(k for k, v in SERVICES.items() if v is svc) or "vol"),
        )
        return
    order = db.add_service_order(uid, svc["title"], label, chain, price)
    db.set_state(uid, "arc_tx", {"order": order["id"]})
    await send_panel(
        update,
        f"🧾 Order <b>#{order['id']}</b> — {svc['title']} · {label}\n"
        f"Price: <b>${price:g}</b> paid in <b>{chain}</b> (equivalent at "
        "current rate).\n\n"
        f"Send the payment to this <b>{chain}</b> address:\n<code>{html.escape(addr)}</code>\n\n"
        "After sending, tap the button below and paste your "
        "<b>transaction signature / hash</b>. The team verifies it on-chain "
        "before your order starts.",
        pay_kb(order["id"], chain),
    )


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
        f"${order['price_usd']:g}\n"
        f"⛓ {html.escape(order['chain'])}\n"
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
        name = "🚀 Pump.fun Services" if hub == "pump" else "📊 DEX Services"
        blurb = (
            "Everything pump.fun: trending slots and raid boosts for your launch."
            if hub == "pump" else
            "DexBoost-grade growth: volume, DEX trending and button ads — paid on-chain."
        )
        await send_panel(update, f"{name}\n<i>{blurb}</i>\n\nPick a package:", hub_kb(hub))
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
            f"{html.escape(o['label'])} — ${o['price_usd']:g} [{o['status']}]"
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
    try:
        await context.bot.send_message(
            order["user_id"],
            f"✅ Your service order <b>#{order_id}</b> ({html.escape(order['service'])} · "
            f"{html.escape(order['label'])}) was <b>approved</b> — delivery is starting. 🚀",
            parse_mode=HTML,
        )
    except Exception:
        pass
    await update.effective_message.reply_text(f"✅ Order #{order_id} approved.")


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
            f"{html.escape(o['service'])} {html.escape(o['label'])} ${o['price_usd']:g} "
            f"{o['chain']}" + (f" tx:<code>{html.escape((o['tx'] or '')[:24])}…</code>" if o["tx"] else "")
        )
    await update.effective_message.reply_text("\n".join(lines), parse_mode=HTML)
