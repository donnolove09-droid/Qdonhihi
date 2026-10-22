import asyncio
import json
import logging
import os
import re
import threading
from typing import Any, Optional

import aiohttp
from flask import Flask, jsonify
from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configure these in Render > Environment. Never hardcode API credentials.
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
API_UID = os.getenv("API_UID", "").strip()
API_PASSWORD = os.getenv("API_PASSWORD", "").strip()
API_BASE_URL = os.getenv(
    "API_BASE_URL", "https://flash-player-info-v1.vercel.app"
).rstrip("/")
PORT = int(os.getenv("PORT", "10000"))
BOT_DISPLAY_NAME = os.getenv("BOT_DISPLAY_NAME", "QDONENLITE").strip()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO"),
)
logger = logging.getLogger("qdonenlite")

web_app = Flask(__name__)


@web_app.get("/")
def home():
    return f"{BOT_DISPLAY_NAME} Telegram Bot is running", 200


@web_app.get("/health")
def health():
    return jsonify(status="ok", bot=BOT_DISPLAY_NAME), 200


def start_web_server():
    web_app.run(host="0.0.0.0", port=PORT, use_reloader=False, threaded=True)


def format_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    if value is None:
        return "—"
    return str(value)


def format_response(data: Any) -> str:
    """Format API JSON without assuming one fixed schema."""
    if isinstance(data, dict):
        # Unwrap common API response containers when possible.
        for key in ("data", "player", "result", "info", "response"):
            if key in data and isinstance(data[key], dict):
                data = data[key]
                break
        lines = []
        for key, value in data.items():
            label = re.sub(r"[_\-]+", " ", str(key)).strip().title()
            rendered = format_value(value)
            if len(rendered) > 700:
                rendered = rendered[:697] + "..."
            lines.append(f"• {label}: {rendered}")
        result = "\n".join(lines) if lines else json.dumps(data, ensure_ascii=False)
    elif isinstance(data, (list, tuple)):
        result = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        result = str(data)
    return result[:3900]


async def call_api(endpoint: str, *, uid: Optional[str] = None,
                   name: Optional[str] = None,
                   extra_params: Optional[dict] = None) -> Any:
    if not API_UID or not API_PASSWORD:
        raise RuntimeError(
            "Thiếu API_UID hoặc API_PASSWORD. Hãy thêm hai biến này trong Render > Environment."
        )

    # API format provided by user: /{Uid}/{Password}/{endpoint}?uid=... or ?name=...
    url = f"{API_BASE_URL}/{API_UID}/{API_PASSWORD}/{endpoint.lstrip('/')}"
    params = dict(extra_params or {})
    if uid:
        params["uid"] = uid
    if name:
        params["name"] = name

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, params=params) as response:
            body = await response.text()
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = {"response": body[:2500]}
            if response.status >= 400:
                detail = format_response(payload)
                raise RuntimeError(f"API HTTP {response.status}: {detail[:500]}")
            return payload


async def reply_api(update: Update, context: ContextTypes.DEFAULT_TYPE,
                    endpoint: str, title: str, *, needs_target: bool = True,
                    extra_params: Optional[dict] = None) -> None:
    if not update.message:
        return
    args = context.args or []
    uid = None
    name = None
    if needs_target:
        if not args:
            await update.message.reply_text(
                f"Thiếu UID hoặc tên người chơi.\nCách dùng: /{endpoint.replace('/', '_')} <UID|name>"
            )
            return
        target = args[0].strip()
        if target.isdigit():
            uid = target
        else:
            name = target
    status = await update.message.reply_text(f"⏳ {title}: đang truy vấn API...")
    try:
        result = await call_api(endpoint, uid=uid, name=name, extra_params=extra_params)
        target_text = uid or name or "—"
        output = f"🎮 QDONENLITE · {title}\nĐối tượng: {target_text}\n\n{format_response(result)}"
        await status.edit_text(output[:4090])
    except asyncio.TimeoutError:
        await status.edit_text("API quá thời gian chờ. Vui lòng thử lại sau.")
    except aiohttp.ClientError as exc:
        logger.warning("API network error: %s", exc)
        await status.edit_text("Không kết nối được API Free Fire. Hãy thử lại sau.")
    except Exception as exc:
        logger.exception("API command failed (%s)", endpoint)
        await status.edit_text(f"❌ Truy vấn thất bại:\n{str(exc)[:700]}")


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "🔥 QDONENLITE · FREE FIRE API BOT\n\n"
            "Tra cứu bằng UID hoặc tên người chơi:\n"
            "/player <UID|name> — thông tin người chơi\n"
            "/bancheck <UID|name> — kiểm tra ban\n"
            "/stats <UID|name> — thống kê\n"
            "/careerbr <UID|name> — Career BR stats\n"
            "/career cs <UID|name> — Career CS stats\n"
            "/rankedbr <UID|name> — Ranked BR stats\n"
            "/rankedcs <UID|name> — Ranked CS stats\n"
            "/normalbr <UID|name> — Normal BR stats\n"
            "/normalcs <UID|name> — Normal CS stats\n"
            "/level <UID|name> — cấp độ\n"
            "/region <UID|name> — khu vực\n"
            "/wishlist <UID|name> — wishlist\n"
            "/workshop <UID|name> — workshop info\n"
            "/duo <UID|name> — duo info\n"
            "/help — danh sách lệnh\n\n"
            "Ví dụ: /player 123456789"
        )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_cmd(update, context)


async def player_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply_api(update, context, "player-info", "Thông tin người chơi")


async def bancheck_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply_api(update, context, "bancheck", "Kiểm tra ban")


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply_api(update, context, "stats-info", "Thống kê người chơi")


async def level_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply_api(update, context, "level", "Cấp độ")


async def region_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply_api(update, context, "region", "Khu vực")


async def wishlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply_api(update, context, "wishlist", "Wishlist")


async def workshop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply_api(update, context, "workshop-info", "Workshop")


async def duo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply_api(update, context, "duo-info", "Duo info")


async def stats_mode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE,
                         matchmode: str, gamemode: str, label: str) -> None:
    await reply_api(
        update, context, f"STATS/{matchmode}/{gamemode}", label
    )


async def careerbr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await stats_mode_cmd(update, context, "CAREER", "BR", "Career BR")


async def careercs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await stats_mode_cmd(update, context, "CAREER", "CS", "Career CS")


async def rankedbr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await stats_mode_cmd(update, context, "RANKED", "BR", "Ranked BR")


async def rankedcs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await stats_mode_cmd(update, context, "RANKED", "CS", "Ranked CS")


async def normalbr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await stats_mode_cmd(update, context, "NORMAL", "BR", "Normal BR")


async def normalcs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await stats_mode_cmd(update, context, "NORMAL", "CS", "Normal CS")


COMMANDS = [
    ("start", "Mở menu QDONENLITE"),
    ("help", "Danh sách lệnh"),
    ("player", "Thông tin người chơi theo UID/tên"),
    ("bancheck", "Kiểm tra trạng thái ban"),
    ("stats", "Thống kê tổng quát"),
    ("careerbr", "Thống kê Career BR"),
    ("careercs", "Thống kê Career CS"),
    ("rankedbr", "Thống kê Ranked BR"),
    ("rankedcs", "Thống kê Ranked CS"),
    ("normalbr", "Thống kê Normal BR"),
    ("normalcs", "Thống kê Normal CS"),
    ("level", "Tra cứu cấp độ"),
    ("region", "Tra cứu khu vực"),
    ("wishlist", "Tra cứu wishlist"),
    ("workshop", "Tra cứu workshop"),
    ("duo", "Tra cứu duo info"),
]


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [BotCommand(command, description) for command, description in COMMANDS]
    )
    logger.info("Telegram command menu configured for QDONENLITE")


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Thiếu biến môi trường BOT_TOKEN trong Render.")
    threading.Thread(target=start_web_server, daemon=True, name="http-health-server").start()

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    handlers = [
        ("start", start_cmd), ("help", help_cmd),
        ("player", player_cmd), ("bancheck", bancheck_cmd),
        ("stats", stats_cmd), ("level", level_cmd), ("region", region_cmd),
        ("wishlist", wishlist_cmd), ("workshop", workshop_cmd), ("duo", duo_cmd),
        ("careerbr", careerbr_cmd), ("careercs", careercs_cmd),
        ("rankedbr", rankedbr_cmd), ("rankedcs", rankedcs_cmd),
        ("normalbr", normalbr_cmd), ("normalcs", normalcs_cmd),
    ]
    for command, handler in handlers:
        app.add_handler(CommandHandler(command, handler))

    logger.info("Starting QDONENLITE Telegram polling")
    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
