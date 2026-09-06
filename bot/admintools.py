"""ARC admin toolkit: bans, maintenance mode, announcements, usage stats.

Every action here is visible and logged — nothing hidden:
- banned users are told they're banned, once per message
- maintenance mode is announced to the admin chat when toggled
- broadcasts report delivered/failed counts
- usage stats count commands/messages (no content stored)
"""

from __future__ import annotations

import asyncio
import html
import logging
import time

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot import db

log = logging.getLogger("solo-metro.admintools")
HTML = ParseMode.HTML

_MAINT_KEY = "maintenance_mode"


def maintenance_on() -> bool:
    return db.worker_get(_MAINT_KEY, "0") == "1"


def set_maintenance(on: bool) -> None:
    db.worker_set(_MAINT_KEY, "1" if on else "0")


def _is_admin_uid(uid: int) -> bool:
    from bot.admin import admin_ids

    try:
        return uid in admin_ids()
    except Exception:
        return False


async def gate(update: Update, user: dict | None) -> str | None:
    """Entry gate for every handler. Returns 'banned' or 'maintenance' after
    replying to the user, or None when the update may proceed. Admins bypass
    maintenance. Also records activity + message stats (no content)."""
    uid = user.get("user_id") if user else (update.effective_user.id if update.effective_user else 0)
    if not uid:
        return None
    try:
        db.touch_active(uid)
        db.bump_stat("msg")
    except Exception:
        pass
    if user and user.get("banned"):
        try:
            await update.effective_message.reply_text(
                "🚫 You are banned from this bot."
            )
        except Exception:
            pass
        return "banned"
    if maintenance_on() and not _is_admin_uid(uid):
        try:
            await update.effective_message.reply_text(
                "🛠 ARC is under maintenance — back shortly. Follow the updates channel."
            )
        except Exception:
            pass
        return "maintenance"
    return None


# ---------------------------------------------------------------- broadcast
async def run_broadcast(text: str, bot=None) -> dict:
    """Send an announcement to all verified, non-banned users. Rate-limited
    (~15 msg/s, well under Telegram limits). Returns real counts."""
    from bot.admin import _bot

    bot = bot or _bot
    if not bot:
        return {"error": "bot not ready"}
    targets = db.broadcast_targets()
    sent = failed = 0
    for uid in targets:
        try:
            await bot.send_message(uid, text, parse_mode=HTML, disable_web_page_preview=True)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.07)
    db.bump_stat("announcements")
    return {"targets": len(targets), "sent": sent, "failed": failed}


# ---------------------------------------------------------------- commands
async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin_uid(update.effective_user.id):
        return
    args = context.args or []
    if not args or not args[0].lstrip("-").isdigit():
        await update.effective_message.reply_text("Usage: /ban <user_id>")
        return
    uid = int(args[0])
    if _is_admin_uid(uid):
        await update.effective_message.reply_text("Refusing to ban an admin.")
        return
    db.ban_user(uid, True)
    from bot.admin import alert

    await alert(f"🚫 User <code>{uid}</code> banned by admin.")


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin_uid(update.effective_user.id):
        return
    args = context.args or []
    if not args or not args[0].lstrip("-").isdigit():
        await update.effective_message.reply_text("Usage: /unban <user_id>")
        return
    db.ban_user(int(args[0]), False)
    from bot.admin import alert

    await alert(f"✅ User <code>{args[0]}</code> unbanned by admin.")


async def cmd_announce(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin_uid(update.effective_user.id):
        return
    text = " ".join(context.args or []).strip()
    if not text:
        await update.effective_message.reply_text(
            "Usage: /announce <message — HTML allowed>"
        )
        return
    await update.effective_message.reply_text("📣 Broadcasting…")
    res = await run_broadcast(text)
    await update.effective_message.reply_text(
        f"📣 Done: {res.get('sent', 0)}/{res.get('targets', 0)} delivered "
        f"({res.get('failed', 0)} failed)."
    )


async def cmd_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin_uid(update.effective_user.id):
        return
    arg = (context.args or [""])[0].lower()
    if arg in ("on", "1", "true"):
        set_maintenance(True)
        state = "ON"
    elif arg in ("off", "0", "false"):
        set_maintenance(False)
        state = "OFF"
    else:
        state = "ON" if maintenance_on() else "OFF"
        await update.effective_message.reply_text(f"Maintenance is currently {state}.")
        return
    from bot.admin import alert

    await alert(f"🛠 Maintenance mode {state}.")
    await update.effective_message.reply_text(f"🛠 Maintenance mode {state}.")


async def cmd_adminstats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin_uid(update.effective_user.id):
        return
    day_ago = time.time() - 86400
    with db.connect() as con:
        total = con.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        verified = con.execute("SELECT COUNT(*) AS n FROM users WHERE verified=1").fetchone()["n"]
        banned = con.execute("SELECT COUNT(*) AS n FROM users WHERE banned=1").fetchone()["n"]
    active = db.count_active_since(day_ago)
    msgs = db.stat_total("msg")
    top = db.stat_counts(10)
    top_lines = "\n".join(f"• <code>{html.escape(t['key'])}</code> — {t['count']}" for t in top) or "—"
    await update.effective_message.reply_text(
        f"📊 <b>ARC stats</b>\n"
        f"Users: <b>{total}</b> (verified {verified}, banned {banned})\n"
        f"Active 24h: <b>{active}</b>\n"
        f"Messages tracked: <b>{msgs}</b>\n\n"
        f"Top usage:\n{top_lines}",
        parse_mode=HTML,
    )
