from bot.config import (
    BOT_NAME,
    BOT_HANDLE,
    DOCS_URL,
    HUB_URL,
    UPDATES_URL,
    TWITTER_URL,
    SUPPORT_URL,
    TOS_URL,
    MORE_LINKS_URL,
    FEE_PERCENT,
    CHAINS,
)


def t(lang: str, en: str, zh: str) -> str:
    return zh if lang == "zh" else en


def captcha_caption(lang: str) -> str:
    return t(
        lang,
        f"⭐ Welcome to {BOT_NAME}, the one-stop solution for all your trading needs!\n\n"
        "Before you can access the bot, type the text shown in the image (any message is fine — you do not need to tap Reply).",
        f"⭐ 欢迎使用 {BOT_NAME}，一站式交易解决方案！\n\n"
        "使用机器人前，请直接发送图片中显示的文字（不必点回复）。",
    )


def captcha_fail(lang: str) -> str:
    return t(
        lang,
        "Wrong code. Type the new text shown in the image (any message is fine).",
        "验证失败。请回复图片中显示的文字后重试。",
    )


def captcha_lock(lang: str, seconds: int) -> str:
    return t(
        lang,
        f"Too many failed attempts. The bot is idle for {seconds}s. Send /start after that to try again.",
        f"失败次数过多。机器人将空闲 {seconds} 秒。请稍后发送 /start 重试。",
    )


def authorized(lang: str) -> str:
    return t(
        lang,
        f"✅ You are now authorized to access the bot!\n\n"
        f"Tap <b>▶️ Continue</b> below to open the main menu.\n"
        f"You can also send /start anytime to summon it.\n\n"
        f"💵 Successful transactions through the {BOT_NAME} are charged a {FEE_PERCENT} tax on every successful buy and sell. Simple transfers are <u>NOT</u> taxed.\n\n"
        f"📚 You can find a thorough documentation for all the features we provide <a href=\"{DOCS_URL}\">here</a>.\n\n"
        f"📢 Join the <a href=\"{HUB_URL}\">Hub</a> and <a href=\"{UPDATES_URL}\">Updates</a> channels and follow us on <a href=\"{TWITTER_URL}\">X (Twitter)</a> to stay up to date with the latest {BOT_NAME} news.\n\n"
        f"🆘 Need help? Our <a href=\"{SUPPORT_URL}\">Support</a> is available to assist you 24/7.\n\n"
        f"By proceeding to use the bot, you <b>confirm</b> that you have read and agreed to our <a href=\"{TOS_URL}\">Terms of Service</a>.",
        f"✅ 你已获得机器人访问权限！\n\n"
        f"点下方 <b>▶️ Continue</b> 打开主菜单，也可随时发送 /start。\n\n"
        f"💵 通过 {BOT_NAME} 成功买入/卖出将收取 {FEE_PERCENT} 税费。普通转账<u>不</u>收费。\n\n"
        f"📚 完整功能文档见 <a href=\"{DOCS_URL}\">这里</a>。\n\n"
        f"📢 加入 <a href=\"{HUB_URL}\">Hub</a> 和 <a href=\"{UPDATES_URL}\">Updates</a>，并关注 <a href=\"{TWITTER_URL}\">X (Twitter)</a> 获取最新消息。\n\n"
        f"🆘 需要帮助？<a href=\"{SUPPORT_URL}\">客服</a> 全天 24/7 在线。\n\n"
        f"继续使用即表示你已阅读并同意 <a href=\"{TOS_URL}\">服务条款</a>。",
    )


def wallet_onboard(lang: str) -> str:
    return t(
        lang,
        "💳 <b>Import or generate a wallet before you trade.</b>\n\n"
        "Never import your main wallet. Generate a fresh W1, save the key offline, then fund it.\n"
        "Select a chain:",
        "💳 <b>交易前请先导入或生成钱包。</b>\n\n"
        "不要导入主钱包。生成新的 W1，离线保存私钥，然后充值。\n"
        "选择一条链：",
    )


def main_menu(lang: str) -> str:
    return t(
        lang,
        f"⚡ <b>{BOT_NAME}</b> — the desk serious traders keep open.\n\n"
        "🚀 <b>Pump Services</b> · 📊 <b>DEX Services</b> — growth packages, paid on-chain.\n"
        "💎 <b>Join VIP</b> — call channel, priority slots, direct line.\n"
        "⚡ <b>Trade</b> — paste any CA to trade in seconds. Multi-chain.\n\n"
        f"<a href=\"{UPDATES_URL}\">Updates</a> · <a href=\"{DOCS_URL}\">Docs</a> · "
        f"<a href=\"{SUPPORT_URL}\">Support</a> · <a href=\"{TWITTER_URL}\">X</a>\n\n"
        "<i>Serving degens since day one. Your keys, your coins.</i>",
        f"⚡ <b>{BOT_NAME}</b> — 认真交易者的工作台。\n\n"
        "🚀 <b>Pump 服务</b> · 📊 <b>DEX 服务</b> — 链上支付的推广套餐。\n"
        "💎 <b>加入 VIP</b> — 点位频道、优先额度、专属支持。\n"
        "⚡ <b>交易</b> — 粘贴 CA 秒级交易，多链支持。\n\n"
        f"<a href=\"{UPDATES_URL}\">更新</a> · <a href=\"{DOCS_URL}\">文档</a> · "
        f"<a href=\"{SUPPORT_URL}\">支持</a> · <a href=\"{TWITTER_URL}\">X</a>",
    )


def must_verify(lang: str) -> str:
    return t(
        lang,
        "Please complete the captcha first. Send /start to receive a new image.",
        "请先完成验证码。发送 /start 获取新图片。",
    )


def chains_text(lang: str) -> str:
    return t(
        lang,
        "🔗 <b>Chains</b>\n\n"
        "Enable or disable chains based on your preference. Disabled chains are hidden from wallets, copytrade, snipes and token reports.\n\n"
        "Tap a chain to toggle it. Tap 💳 to set up wallets for that chain.",
        "🔗 <b>链</b>\n\n启用或禁用你要交易的链。禁用后将从钱包、跟单、狙击和代币面板中隐藏。\n\n点击链名称切换开关，点击 💳 设置该链钱包。",
    )


def wallets_pick_chain(lang: str) -> str:
    return t(
        lang,
        "💳 <b>Wallets</b>\n\nSelect a chain to import or generate wallets.",
        "💳 <b>钱包</b>\n\n选择一条链以导入或生成钱包。",
    )


def wallets_chain(lang: str, chain: str, wallets: list) -> str:
    meta = CHAINS[chain]
    if not wallets:
        return t(
            lang,
            f"💳 <b>{meta['name']} Wallets</b>\n\n"
            "No wallets yet. It is recommended to <b>generate a new wallet</b> instead of importing your main wallet.\n\n"
            "You can connect up to 8 wallets per chain, or 10 if you are ⭐ Premium.",
            f"💳 <b>{meta['name']} 钱包</b>\n\n还没有钱包。建议<b>生成新钱包</b>，不要导入主钱包。\n\n每条链最多 8 个钱包，⭐ Premium 用户最多 10 个。",
        )
    lines = [f"💳 <b>{meta['name']} Wallets</b>\n"]
    for w in wallets:
        flags = []
        if w["is_default"]:
            flags.append("Default")
        if w["is_manual"]:
            flags.append("Manual")
        tag = f" ({', '.join(flags)})" if flags else ""
        lines.append(f"• <b>{w['name']}</b>{tag}\n<code>{w['address']}</code>")
    lines.append(
        t(
            lang,
            "\n🟢 <b>Manual</b> wallets participate in manual multi-buys.\n"
            "💳 <b>Default Wallet</b> is used for Signals, Copytrade and Auto Snipe.",
            "\n🟢 <b>Manual</b> 钱包参与手动买入。\n💳 <b>默认钱包</b> 用于信号、跟单和自动狙击。",
        )
    )
    return "\n".join(lines)


def global_settings(lang: str, chain: str, s: dict) -> str:
    meta = CHAINS[chain]
    on = lambda k: "🟢" if s.get(k) in ("1", "true", "on") else "🔴"
    return t(
        lang,
        f"⚙️ <b>Global Settings — {meta['name']}</b>\n\n"
        f"{on('anti_mev')} Anti-MEV\n"
        f"{on('degen')} Degen Mode\n"
        f"{on('anti_rug')} Anti-Rug\n"
        f"{on('smart_slip')} Smart Slippage\n"
        f"{on('auto_buy')} Auto Buy on paste\n"
        f"{on('auto_approve')} Auto-Approve\n\n"
        f"💧 Buy slippage: <b>{s.get('buy_slip', '20')}%</b>\n"
        f"💧 Sell slippage: <b>{s.get('sell_slip', '20')}%</b>\n"
        f"⛽ Gas delta: <b>{s.get('gas_delta', '0.5')} gwei</b>\n"
        f"💰 Buy amount: <b>{s.get('buy_amount', '0.1')} {meta['native']}</b>\n"
        f"⛽ Max gas price: <b>{s.get('max_gas', '100')} gwei</b>",
        f"⚙️ <b>全局设置 — {meta['name']}</b>\n\n"
        f"{on('anti_mev')} 反 MEV\n"
        f"{on('degen')} Degen 模式\n"
        f"{on('anti_rug')} 反 Rug\n"
        f"{on('smart_slip')} 智能滑点\n"
        f"{on('auto_buy')} 粘贴自动买入\n"
        f"{on('auto_approve')} 自动授权\n\n"
        f"💧 买入滑点: <b>{s.get('buy_slip', '20')}%</b>\n"
        f"💧 卖出滑点: <b>{s.get('sell_slip', '20')}%</b>\n"
        f"⛽ Gas 增量: <b>{s.get('gas_delta', '0.5')} gwei</b>\n"
        f"💰 买入金额: <b>{s.get('buy_amount', '0.1')} {meta['native']}</b>\n"
        f"⛽ 最高 Gas: <b>{s.get('max_gas', '100')} gwei</b>",
    )


def token_report(lang: str, chain: str, ca: str, mode: str = "buy") -> str:
    meta = CHAINS[chain]
    native = meta["native"]
    return t(
        lang,
        f"📊 <b>Token Report</b> — {meta['name']}\n\n"
        f"<code>{ca}</code>\n\n"
        f"💵 Price: —\n"
        f"🧢 MC: —\n"
        f"💧 Liquidity: —\n"
        f"🧾 Tax: Buy — / Sell —\n"
        f"🔗 Chart • Scan • Socials\n\n"
        f"{'🟢 Buy menu' if mode == 'buy' else '🔴 Sell menu'}  •  Wallet: Default\n"
        f"Slippage inherits your Global {mode.title()} Settings.",
        f"📊 <b>代币报告</b> — {meta['name']}\n\n<code>{ca}</code>\n\n"
        f"{'🟢 买入菜单' if mode == 'buy' else '🔴 卖出菜单'}",
    )


def help_text(lang: str) -> str:
    return t(
        lang,
        f"📖 <b>{BOT_NAME} — useful commands</b>\n\n"
        "/start /metro /sniper /menu — Main menu\n"
        "/chains /eth /sol /bsc /base /arb /avax — Chains & wallets\n"
        "/wallets /balance /export /import /collect /disperse\n"
        "/quick /settings — Gas, slippage, Anti-MEV\n"
        "/copytrade /signals /scraper — Copy & call channels\n"
        "/autosnipe /godmode /presale /snipe — Snipes\n"
        "/orders /dca /limits — Limits & DCA\n"
        "/pos /pnl /monitor /summary /cleartrades\n"
        "/buy /sell /buysell /scan /chart /approve — Paste a CA\n"
        "/bridge /relay /debridge /private /arc\n"
        "/premium /cashback /claim /rewards /campaigns /competition /mvp /referral\n"
        "/trending /pumpfun /language /cancel /ping /tutorial /faq /docs\n"
        "/support /help\n\n"
        f"Paste a token CA anytime to open the Token Report.\n"
        f"Docs: {DOCS_URL}\nSupport: {SUPPORT_URL}",
        f"📖 <b>{BOT_NAME} 常用命令</b>\n\n发送 /start /metro /sniper 打开主菜单，粘贴合约地址即可交易。/help 查看全部命令。",
    )


def support_text(lang: str) -> str:
    return t(
        lang,
        f"🆘 <b>Support</b>\n\n"
        f"{BOT_NAME} support is available 24/7.\n\n"
        f"📚 Manual: {DOCS_URL}\n"
        f"💬 Live support: {SUPPORT_URL}\n"
        f"📢 Hub: {HUB_URL}\n"
        f"📣 Updates: {UPDATES_URL}\n"
        f"🐦 X: {TWITTER_URL}",
        f"🆘 <b>客服</b>\n\n{BOT_NAME} 全天 24/7 在线。\n文档: {DOCS_URL}\n客服: {SUPPORT_URL}",
    )


def bot_description() -> str:
    return (
        f"{BOT_NAME} — the multi-chain trading desk on Telegram.\n\n"
        "⚡ Trade any CA in seconds · snipe launches · copy wallets · bridge\n"
        "🚀 Pump & DEX growth services — real orders, paid on-chain, verified by hand\n"
        "💎 VIP — call channel, priority slots, direct line\n\n"
        "Non-custodial: import your own wallet, keys stay yours. Every balance "
        "and order state is the real on-chain truth. Support 24/7 via /support."
    )


def main_caption(lang: str = "en") -> str:
    """Main screen text — sent TOGETHER with the ARC logo as the photo caption."""
    return t(
        lang,
        f"⚡ <b>{BOT_NAME}</b> — the desk serious traders keep open.\n\n"
        "Trade any token in seconds: paste a CA, set your size, fire. Snipe "
        "pumps, copy wallets, run limit orders and bridge — from one bot, with "
        "your own wallets. Keys stay yours.\n\n"
        "🚀 <b>Pump Services</b> — trending slots + raid boosts for launches\n"
        "📊 <b>DEX Services</b> — volume, trending hub, button ads\n"
        "💎 <b>VIP</b> — call channel, priority slots, direct line\n\n"
        "Paid in SOL on-chain, verified by hand — every order real, every "
        "state honest.\n\n"
        "New here? Tap ⚡ Trade and paste any contract address. Need a hand? /support",
        f"⚡ <b>{BOT_NAME}</b> — 认真交易者的工作台。\n\n"
        "粘贴 CA 秒级交易 · 抢跑打新 · 跟单 · 跨链桥 — 一个机器人全搞定，钱包你自己掌管。\n\n"
        "🚀 <b>Pump 服务</b> · 📊 <b>DEX 服务</b> · 💎 <b>VIP</b>\n\n"
        "SOL 链上支付，人工核验 — 每一单都真实。\n\n"
        "开始：点 ⚡ Trade 粘结合约地址。需要帮助？/support",
    )



