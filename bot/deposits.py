"""Real deposit detection for ARC.

The worker sweeps every wallet's native balance and alerts the admin on any
INCREASE (funds arriving). Baselines live in worker_state (survives
restarts — old deposits never re-alert). One DM per deposit, no false
positives on spends or unchanged balances.
"""

from __future__ import annotations

import asyncio
import html
import logging
from decimal import Decimal

log = logging.getLogger("solo-metro.deposits")

MAX_PER_SWEEP = 300
RPC_PACE_EVERY = 10
RPC_PACE_SLEEP = 0.4


def _fmt(d: Decimal) -> str:
    try:
        return f"{d.normalize():f}"
    except Exception:
        return str(d)


async def sweep_deposits(bot) -> None:
    from bot import db
    from bot.engine import native_balance

    try:
        wallets = db.all_wallets()
    except Exception:
        return
    for i, w in enumerate(wallets[:MAX_PER_SWEEP]):
        try:
            bal = await native_balance(w["chain"], w["address"])
        except Exception:
            continue  # one RPC hiccup must not stop the sweep
        key = f"dep_bal:{w['id']}"
        prev_raw = db.worker_get(key, "")
        try:
            prev = Decimal(prev_raw) if prev_raw not in ("", None) else None
        except Exception:
            prev = None
        try:
            db.worker_set(key, str(bal))
        except Exception:
            pass
        if prev is None:
            continue  # first sighting — baseline only
        delta = bal - prev
        if delta <= 0:
            continue  # spend or unchanged
        try:
            from bot.admin import alert, tag_uid
            from bot.chainmeta import CHAIN_META

            meta = CHAIN_META.get(w["chain"], {})
            native = meta.get("native") or w["chain"]
            explorer = (meta.get("explorer") or "").rstrip("/")
            url = f"{explorer}/address/{w['address']}" if explorer else ""
            lines = [
                f"💰 <b>DEPOSIT RECEIVED</b> — {tag_uid(w['user_id'])}",
                f"Chain: <b>{html.escape(str(w['chain']))}</b> · Wallet: <b>{html.escape(str(w.get('name') or 'wallet'))}</b>",
                f"🏦 <code>{html.escape(str(w['address']))}</code>",
                f"🟢 Amount: <b>+{_fmt(delta)} {html.escape(native)}</b>",
                f"💼 Balance now: <b>{_fmt(bal)} {html.escape(native)}</b>",
            ]
            if url:
                lines.append(f"🔗 {url}")
            await alert("\n".join(lines))
        except Exception:
            log.exception("deposit alert")
        if i % RPC_PACE_EVERY == RPC_PACE_EVERY - 1:
            await asyncio.sleep(RPC_PACE_SLEEP)
