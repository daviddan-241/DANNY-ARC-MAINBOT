"""ARC Admin Mini App — a real Telegram Web App served by the bot itself.

- URL:  <public-url>/admin/app   (opened via the /admin command button)
- Auth: EITHER a Telegram WebApp initData signature (validated HMAC-SHA256
        against the bot token, user must be in ADMIN_CHAT_ID)
        OR the ADMIN_APP_KEY env secret passed as ?key=...
- Data: 100% real — live counts, service orders with working approve/reject
        (the user gets a Telegram message), recent trades and users.
- Zero external assets: the page is one inline HTML file (dark fintech style).
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import html as _html
import json
import logging
import os
import time

from aiohttp import web

from bot import db

log = logging.getLogger("solo-metro.adminweb")

_STARTED = time.time()

# ---- in-memory log ring for the admin panel (last 300 lines) ----
import collections
import logging as _logging

_RING = collections.deque(maxlen=300)


class _RingHandler(_logging.Handler):
    def emit(self, record):
        try:
            _RING.append(f"{time.strftime('%H:%M:%S')} {record.levelname[:1]} {record.name}: {record.getMessage()[:300]}")
        except Exception:
            pass


_RING_ATTACHED = False


def _attach_ring() -> None:
    global _RING_ATTACHED
    if _RING_ATTACHED:
        return
    try:
        h = _RingHandler(level=_logging.INFO)
        _logging.getLogger().addHandler(h)
        _RING_ATTACHED = True
    except Exception:
        pass


def _app_key() -> str:
    return (os.getenv("ADMIN_APP_KEY") or "").strip()


def _bot_token() -> str:
    from bot.config import BOT_TOKEN

    return BOT_TOKEN


def _admin_ids() -> set[int]:
    from bot.admin import admin_ids

    try:
        return set(admin_ids())
    except Exception:
        return set()


# ---------------------------------------------------------------- auth
def verify_init_data(init_data: str, bot_token: str) -> int | None:
    """Validate Telegram WebApp initData (HMAC-SHA256, official algorithm).
    Returns the user id when the signature is valid, else None."""
    try:
        from urllib.parse import unquote

        pairs = {}
        hash_ = ""
        for part in init_data.split("&"):
            k, _, v = part.partition("=")
            if k == "hash":
                hash_ = unquote(v)
            else:
                # official algorithm hashes the DECODED values
                pairs[k] = unquote(v)
        if not hash_:
            return None
        data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        calc = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc, hash_):
            return None
        user = json.loads(pairs.get("user", "{}"))
        return int(user.get("id") or 0) or None
    except Exception:
        return None


def _authorized(request: web.Request) -> bool:
    key = request.headers.get("X-Admin-Key", "") or request.query.get("key", "")
    env_key = _app_key()
    if env_key and hmac.compare_digest(key, env_key):
        return True
    init_data = request.headers.get("X-Init-Data", "") or request.query.get("init_data", "")
    if init_data:
        uid = verify_init_data(init_data, _bot_token())
        if uid and uid in _admin_ids():
            return True
    return False


def _deny() -> web.Response:
    return web.json_response({"ok": False, "error": "unauthorized"}, status=401)


# ---------------------------------------------------------------- data
async def api_stats(_request: web.Request) -> web.Response:
    if not _authorized(_request):
        return _deny()
    from bot.config import BOT_NAME
    from bot.db import ENGINE

    def one(con, sql):
        return con.execute(sql).fetchone()

    with db.connect() as con:
        users = one(con, "SELECT COUNT(*) AS n FROM users")["n"]
        verified = one(con, "SELECT COUNT(*) AS n FROM users WHERE verified=1")["n"]
        premium = one(con, "SELECT COUNT(*) AS n FROM users WHERE premium=1")["n"]
        banned = one(con, "SELECT COUNT(*) AS n FROM users WHERE banned=1")["n"]
        wallets = one(con, "SELECT COUNT(*) AS n FROM wallets")["n"]
        trades = one(con, "SELECT COUNT(*) AS n FROM trades")["n"]
        orders = one(con, "SELECT COUNT(*) AS n FROM services_orders")["n"]
        pending = one(con, "SELECT COUNT(*) AS n FROM services_orders WHERE status IN ('pending','paid_check')")["n"]
    from bot.admintools import maintenance_on

    try:
        active24 = db.count_active_since(time.time() - 86400)
        messages = db.stat_total("msg")
        top = db.stat_counts(8)
    except Exception:
        active24, messages, top = 0, 0, []
    return web.json_response({
        "ok": True,
        "bot": BOT_NAME,
        "engine": ENGINE,
        "users": users,
        "verified": verified,
        "premium": premium,
        "banned": banned,
        "active_24h": active24,
        "messages": messages,
        "top_usage": top,
        "maintenance": maintenance_on(),
        "wallets": wallets,
        "trades": trades,
        "orders": orders,
        "orders_pending": pending,
        "uptime_seconds": int(time.time() - _STARTED),
    })


async def api_orders(_request: web.Request) -> web.Response:
    if not _authorized(_request):
        return _deny()
    with db.connect() as con:
        rows = con.execute(
            "SELECT o.*, u.username, u.first_name FROM services_orders o "
            "LEFT JOIN users u ON u.user_id = o.user_id "
            "ORDER BY o.id DESC LIMIT 50"
        ).fetchall()
    out = []
    for r in rows:
        out.append({
            "id": r["id"], "user": f"@{r['username']}" if r["username"] else (r["first_name"] or str(r["user_id"])),
            "user_id": r["user_id"], "service": r["service"], "label": r["label"],
            "chain": r["chain"], "price_usd": r["price_usd"], "status": r["status"],
            "tx": r["tx"] or "", "created": int(r["created_at"] or 0),
        })
    return web.json_response({"ok": True, "orders": out})


async def api_trades(_request: web.Request) -> web.Response:
    if not _authorized(_request):
        return _deny()
    with db.connect() as con:
        rows = con.execute(
            "SELECT t.*, u.username, u.first_name FROM trades t "
            "LEFT JOIN users u ON u.user_id = t.user_id "
            "ORDER BY t.id DESC LIMIT 50"
        ).fetchall()
    out = [{
        "id": r["id"], "user": f"@{r['username']}" if r["username"] else (r["first_name"] or str(r["user_id"])),
        "chain": r["chain"], "token": r["token"], "side": r["side"],
        "amount": r["amount"], "txid": r["txid"], "created": int(r["created_at"] or 0),
    } for r in rows]
    return web.json_response({"ok": True, "trades": out})


async def api_order_action(request: web.Request) -> web.Response:
    """POST {id, action: 'approve'|'reject'} — the SAME logic as the bot
    commands: status update + user notification."""
    if not _authorized(request):
        return _deny()
    try:
        body = await request.json()
        order_id = int(body.get("id") or 0)
        action = str(body.get("action") or "")
    except Exception:
        return web.json_response({"ok": False, "error": "bad body"}, status=400)
    if action not in ("approve", "reject") or not order_id:
        return web.json_response({"ok": False, "error": "bad action"}, status=400)
    order = db.get_service_order(order_id)
    if not order:
        return web.json_response({"ok": False, "error": "not found"}, status=404)
    status = "approved" if action == "approve" else "rejected"
    db.set_service_order_status(order_id, status)
    notified = False
    try:
        from bot import admin as _adm

        if _adm._bot:
            emoji = "\u2705" if action == "approve" else "\u274c"
            await _adm._bot.send_message(
                order["user_id"],
                f"{emoji} Your service order <b>#{order_id}</b> "
                f"({_html.escape(order['service'])} \u00b7 {_html.escape(order['label'])}) was "
                f"<b>{status}</b>" + (" \u2014 delivery starting. \U0001F680" if action == "approve" else "."),
                parse_mode="HTML",
            )
            notified = True
    except Exception as exc:
        log.warning("mini-app notify failed: %s", exc)
    return web.json_response({"ok": True, "id": order_id, "status": status, "notified": notified})


async def api_users_list(request: web.Request) -> web.Response:
    """GET /admin/api/users?q=search — full user list for the dashboard."""
    if not _authorized(request):
        return _deny()
    q = request.query.get("q", "").strip()
    rows = db.list_users_admin(q, 100)
    out = [{
        "id": r["user_id"], "name": f"@{r['username']}" if r["username"] else (r["first_name"] or "?"),
        "verified": bool(r["verified"]), "premium": bool(r["premium"]), "banned": bool(r["banned"]),
        "created": int(r["created_at"] or 0), "last_active": int(r["last_active"] or 0),
    } for r in rows]
    return web.json_response({"ok": True, "users": out})


async def api_ban(request: web.Request) -> web.Response:
    if not _authorized(request):
        return _deny()
    try:
        body = await request.json()
        uid = int(body.get("id") or 0)
    except Exception:
        return web.json_response({"ok": False, "error": "bad body"}, status=400)
    if not uid:
        return web.json_response({"ok": False, "error": "bad id"}, status=400)
    if uid in _admin_ids():
        return web.json_response({"ok": False, "error": "cannot ban an admin"}, status=400)
    db.ban_user(uid, True)
    log.warning("admin mini-app: banned user %s", uid)
    return web.json_response({"ok": True, "id": uid, "banned": True})


async def api_unban(request: web.Request) -> web.Response:
    if not _authorized(request):
        return _deny()
    try:
        body = await request.json()
        uid = int(body.get("id") or 0)
    except Exception:
        return web.json_response({"ok": False, "error": "bad body"}, status=400)
    if not uid:
        return web.json_response({"ok": False, "error": "bad id"}, status=400)
    db.ban_user(uid, False)
    log.warning("admin mini-app: unbanned user %s", uid)
    return web.json_response({"ok": True, "id": uid, "banned": False})


async def api_announce(request: web.Request) -> web.Response:
    """POST {text} — queued broadcast; result is visible via /logs + admin DM."""
    if not _authorized(request):
        return _deny()
    try:
        body = await request.json()
        text = str(body.get("text") or "").strip()
    except Exception:
        return web.json_response({"ok": False, "error": "bad body"}, status=400)
    if not text:
        return web.json_response({"ok": False, "error": "empty text"}, status=400)
    targets = db.broadcast_targets()

    async def _job():
        from bot.admintools import run_broadcast
        from bot.admin import alert

        res = await run_broadcast(text)
        await alert(
            f"📣 Announcement finished: {res.get('sent')}/{res.get('targets')} delivered "
            f"({res.get('failed')} failed)."
        )

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_job())
    except Exception:
        return web.json_response({"ok": False, "error": "no loop"}, status=500)
    return web.json_response({"ok": True, "queued": True, "targets": len(targets)})


async def api_maintenance(request: web.Request) -> web.Response:
    if not _authorized(request):
        return _deny()
    try:
        body = await request.json()
        on = bool(body.get("on"))
    except Exception:
        return web.json_response({"ok": False, "error": "bad body"}, status=400)
    from bot.admintools import set_maintenance

    set_maintenance(on)
    log.warning("admin mini-app: maintenance %s", "ON" if on else "OFF")
    return web.json_response({"ok": True, "maintenance": on})


async def api_logs(request: web.Request) -> web.Response:
    if not _authorized(request):
        return _deny()
    return web.json_response({"ok": True, "logs": list(_RING)[-120:]})


# ---------------------------------------------------------------- page
_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ARC Admin</title>
<style>
:root{--bg:#0b1220;--card:#121b2e;--line:#1f2b45;--txt:#e8eefc;--mut:#8fa3c8;--gold:#f5c451;--ok:#3ddc84;--bad:#ff5d5d}
*{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,'Segoe UI',Roboto,sans-serif}
body{background:var(--bg);color:var(--txt);padding:16px 14px 60px}
h1{font-size:20px;letter-spacing:.5px;margin-bottom:2px}h1 b{color:var(--gold)}
.sub{color:var(--mut);font-size:12px;margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px}
.card .v{font-size:20px;font-weight:700}.card .k{font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:.6px;margin-top:2px}
h2{font-size:13px;color:var(--mut);text-transform:uppercase;letter-spacing:.8px;margin:16px 0 8px}
table{width:100%;border-collapse:collapse;font-size:12px}
td,th{padding:7px 6px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:110px}
th{color:var(--mut);font-weight:500;font-size:10px;text-transform:uppercase}
.pill{display:inline-block;padding:2px 8px;border-radius:99px;font-size:10px;font-weight:600}
.p-approved{background:rgba(61,220,132,.15);color:var(--ok)}.p-paid_check{background:rgba(245,196,81,.15);color:var(--gold)}
.p-pending{background:rgba(143,163,200,.15);color:var(--mut)}.p-rejected{background:rgba(255,93,93,.15);color:var(--bad)}
button{border:0;border-radius:8px;padding:5px 10px;font-size:11px;font-weight:600;cursor:pointer;margin-right:4px}
.b-ok{background:var(--ok);color:#04150b}.b-no{background:var(--bad);color:#fff}.b-mut{background:#22304e;color:var(--txt)}
input,textarea{width:100%;background:#0d1626;border:1px solid var(--line);border-radius:8px;color:var(--txt);padding:8px 10px;font-size:13px;margin-bottom:8px}
.row{display:flex;gap:8px;align-items:center}
.err{color:var(--bad);text-align:center;padding:40px 10px}
#refresh{position:fixed;right:14px;top:14px;background:var(--card);border:1px solid var(--line);color:var(--mut);border-radius:99px;padding:6px 12px}
#maint{position:fixed;left:14px;top:14px;border-radius:99px;padding:6px 12px;font-size:11px}
pre{background:#0a101d;border:1px solid var(--line);border-radius:10px;padding:10px;font-size:10px;color:#9fb4d8;max-height:180px;overflow:auto;white-space:pre-wrap}
.ok-msg{color:var(--ok);font-size:12px;min-height:16px;margin-bottom:6px}
</style></head><body>
<div id="maint"><button class="b-mut" id="maintBtn" onclick="toggleMaint()">🛠 MAINTENANCE: ?</button></div>
<h1>⚡ <b>ARC</b> Admin</h1>
<div class="sub">Live · real data only</div>
<button id="refresh" onclick="loadAll()">↻</button>
<div class="grid" id="stats"></div>
<h2>📣 Announcement</h2>
<textarea id="annText" rows="2" placeholder="Message to all verified users (HTML allowed)"></textarea>
<div class="row"><button class="b-ok" onclick="announce()">Send to everyone</button><span class="ok-msg" id="annMsg"></span></div>
<h2>Service orders</h2><div id="orders"></div>
<h2>Users <input id="q" placeholder="search id/name" style="width:130px;display:inline-block;margin-left:8px;padding:4px 8px" oninput="loadUsers()"></h2><div id="users"></div>
<h2>Recent trades</h2><div id="trades"></div>
<h2>Top usage</h2><div id="usage"></div>
<h2>Logs (last 120)</h2><pre id="logs">—</pre>
<script>
const KEY=new URLSearchParams(location.search).get('key')||'';
const H={'X-Admin-Key':KEY};
try{if(window.Telegram&&Telegram.WebApp&&Telegram.WebApp.initData){H['X-Init-Data']=Telegram.WebApp.initData;Telegram.WebApp.expand();}}catch(e){}
async function j(url,opts){const r=await fetch(url,{...opts,headers:{...H,...(opts&&opts.headers||{})}});if(r.status===401){document.body.innerHTML='<div class="err">401 — unauthorized. Open the panel via the /admin button in the bot.</div>';throw new Error('unauthorized');}return r.json();}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function fmtT(s){return s?new Date(s*1000).toLocaleString():'—'}
async function loadAll(){
 try{
  const s=await j('/admin/api/stats');
  document.getElementById('maintBtn').textContent='🛠 MAINTENANCE: '+(s.maintenance?'ON':'OFF');
  document.getElementById('stats').innerHTML=
   [['Users',s.users],['Active 24h',s.active_24h],['Verified',s.verified],['Premium',s.premium],['Banned',s.banned],['Wallets',s.wallets],['Trades',s.trades],['Messages',s.messages],['Orders',s.orders+(s.orders_pending?' ('+s.orders_pending+' open)':'')]]
   .map(x=>`<div class="card"><div class="v">${x[1]}</div><div class="k">${x[0]}</div></div>`).join('');
  document.getElementById('usage').innerHTML='<table>'+s.top_usage.map(u=>`<tr><td><code>${esc(u.key)}</code></td><td>${u.count}</td></tr>`).join('')+'</table>'||'—';
  await Promise.all([loadOrders(),loadUsers(),loadTrades(),loadLogs()]);
 }catch(e){}}
async function loadOrders(){
  const o=await j('/admin/api/orders');
  document.getElementById('orders').innerHTML=o.orders.length?'<table><tr><th>#</th><th>User</th><th>Service</th><th>$</th><th>Chain</th><th>Status</th><th>TX</th><th></th></tr>'+
   o.orders.map(r=>`<tr><td>${r.id}</td><td>${esc(r.user)}</td><td>${esc(r.service)} ${esc(r.label)}</td><td>${r.price_usd}</td><td>${r.chain}</td><td><span class="p-${r.status}">${r.status}</span></td><td title="${esc(r.tx)}">${r.tx?r.tx.slice(0,8)+'…':'—'}</td>
   <td>${(r.status==='pending'||r.status==='paid_check')?`<button class="b-ok" onclick="act(${r.id},'approve')">✓</button><button class="b-no" onclick="act(${r.id},'reject')">✕</button>`:''}</td></tr>`).join('')+'</table>':'<div class="sub">No orders yet.</div>';}
async function loadUsers(){
  const q=document.getElementById('q').value.trim();
  const u=await j('/admin/api/users'+(q?('?q='+encodeURIComponent(q)):''));
  document.getElementById('users').innerHTML=u.users.length?'<table><tr><th>ID</th><th>Name</th><th>OK</th><th>⭐</th><th>Joined</th><th>Last active</th><th></th></tr>'+
   u.users.map(r=>`<tr><td>${r.id}</td><td>${esc(r.name)}</td><td>${r.verified?'✓':'—'}</td><td>${r.premium?'⭐':''}</td><td>${fmtT(r.created)}</td><td>${fmtT(r.last_active)}</td>
   <td>${r.banned?`<button class="b-ok" onclick="unban(${r.id})">Unban</button><span class="pill p-rejected">banned</span>`:`<button class="b-no" onclick="ban(${r.id})">Ban</button>`}</td></tr>`).join('')+'</table>':'<div class="sub">No users match.</div>';}
async function loadTrades(){
  const t=await j('/admin/api/trades');
  document.getElementById('trades').innerHTML=t.trades.length?'<table><tr><th>User</th><th>Chain</th><th>Side</th><th>Amount</th><th>Token</th><th>When</th></tr>'+
   t.trades.map(r=>`<tr><td>${esc(r.user)}</td><td>${r.chain}</td><td>${r.side}</td><td>${esc(String(r.amount))}</td><td title="${esc(r.token)}">${esc(String(r.token).slice(0,10))}…</td><td>${fmtT(r.created)}</td></tr>`).join('')+'</table>':'<div class="sub">No trades yet.</div>';}
async function loadLogs(){
  const l=await j('/admin/api/logs');
  document.getElementById('logs').textContent=l.logs.join('\n')||'—';}
async function act(id,a){if(!confirm(a+' order #'+id+'?'))return;await j('/admin/api/order',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id,action:a})});loadAll();}
async function ban(id){if(!confirm('Ban user '+id+'?'))return;await j('/admin/api/ban',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})});loadUsers();}
async function unban(id){await j('/admin/api/unban',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})});loadUsers();}
async function announce(){const t=document.getElementById('annText').value.trim();if(!t)return;document.getElementById('annMsg').textContent='Sending…';const r=await j('/admin/api/announce',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});document.getElementById('annMsg').textContent='Queued to '+r.targets+' users ✓';document.getElementById('annText').value='';}
async function toggleMaint(){const s=await j('/admin/api/stats');const on=!s.maintenance;if(on&&!confirm('Turn maintenance ON? Users will be locked out.'))return;await j('/admin/api/maintenance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({on:on})});loadAll();}
loadAll();setInterval(loadAll,30000);
</script></body></html>"""


async def serve_page(_request: web.Request) -> web.Response:
    return web.Response(text=_PAGE, content_type="text/html", charset="utf-8",
                        headers={"Cache-Control": "no-store"})


def mount_admin(app: web.Application, bot=None) -> None:
    """Attach the admin mini app to the bot's existing HTTP server."""
    _attach_ring()
    if bot is not None:
        try:
            from bot import admin as _adm

            if _adm._bot is None:
                _adm.set_bot(bot)
        except Exception:
            pass
    app.router.add_get("/admin/app", serve_page)
    app.router.add_get("/admin/api/stats", api_stats)
    app.router.add_get("/admin/api/orders", api_orders)
    app.router.add_get("/admin/api/trades", api_trades)
    app.router.add_post("/admin/api/order", api_order_action)
    app.router.add_get("/admin/api/users", api_users_list)
    app.router.add_post("/admin/api/ban", api_ban)
    app.router.add_post("/admin/api/unban", api_unban)
    app.router.add_post("/admin/api/announce", api_announce)
    app.router.add_post("/admin/api/maintenance", api_maintenance)
    app.router.add_get("/admin/api/logs", api_logs)
    log.info("admin mini app mounted at /admin/app")


def public_app_url() -> str:
    """The bot's public URL (Render provides RENDER_EXTERNAL_URL)."""
    from bot.config import WEBHOOK_URL

    return WEBHOOK_URL  # config already folds RENDER_EXTERNAL_URL into it


def admin_button_url() -> str:
    base = public_app_url()
    key = _app_key()
    if not base:
        return ""
    return f"{base}/admin/app" + (f"?key={key}" if key else "")
