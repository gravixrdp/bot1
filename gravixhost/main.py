import asyncio
import os
from dataclasses import dataclass
from typing import Optional, Dict

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, Document
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from .config import MASTER_BOT_TOKEN, APP_NAME
from .keyboards import main_menu, support_url_kb
from .utils import bold, code, human_dt, is_valid_token, italic, underline, strike, pre
from .storage import (
    get_user,
    update_user,
    add_bot,
    can_host_more,
    mark_started,
    mark_stopped,
    get_active_bots,
    get_user_bots,
)
from .services.hoster import save_upload, build_and_run, remove_workspace
from .services.scheduler import Scheduler
from .admin import router as admin_router


@dataclass
class PendingHost:
    workspace: Optional[str] = None
    entry_name: Optional[str] = None
    token: Optional[str] = None
    bot_record_id: Optional[str] = None
    bot_name: Optional[str] = None


class HostStates(StatesGroup):
    waiting_file = State()
    waiting_token = State()


router = Router(name="user")


@router.message(Command("start"))
async def cmd_start(message: Message):
    user = get_user(message.from_user.id)
    update_user(message.from_user.id, name=message.from_user.full_name)
    welcome = (
        f"✨ Welcome to {bold(APP_NAME)}\n"
        f"Host your Telegram bot in a secure, isolated environment.\n\n"
        f"Choose an option below:"
    )
    await message.answer(welcome, reply_markup=main_menu(user.get("is_premium")), parse_mode=ParseMode.HTML)


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "🆘 Help\n"
        "• Use '📦 Host My Bot' to upload your bot code.\n"
        "• Make sure your main file is named " + code("bot.py") + ".\n"
        "• After upload, send your bot token from " + bold("@BotFather") + ".\n"
        "• Free plan runs for 1 hour. Upgrade for unlimited uptime 💎.\n"
    )
    await message.answer(text, reply_markup=main_menu(get_user(message.from_user.id).get("is_premium")), parse_mode=ParseMode.HTML)


@router.message(Command("myinfo"))
async def cmd_myinfo(message: Message):
    user = get_user(message.from_user.id)
    text = (
        "👤 User Info\n"
        f"• Name: {bold(message.from_user.full_name)}\n"
        f"• ID: {code(str(message.from_user.id))}\n"
        f"• Status: {'Premium User' if user.get('is_premium') else 'Free User'}\n"
        f"• Hosted Bots: {len(get_user_bots(message.from_user.id))}\n"
        f"• Plan Expiry: {bold(human_dt(_safe_parse(user.get('premium_expiry'))))}\n"
    )
    await message.answer(text, reply_markup=main_menu(user.get("is_premium")), parse_mode=ParseMode.HTML)


def _safe_parse(s):
    if not s:
        return None
    from datetime import datetime
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


@router.message(Command("upgrade"))
async def cmd_upgrade(message: Message):
    text = (
        "💎 Upgrade to Premium\n"
        "• Unlimited uptime\n"
        "• Host multiple bots\n"
        "• Priority support\n\n"
        "Contact admin via the button (for premium users) or reply here with your request."
    )
    await message.answer(text, reply_markup=main_menu(get_user(message.from_user.id).get("is_premium")), parse_mode=ParseMode.HTML)


@router.message(Command("host"))
async def cmd_host(message: Message, state: FSMContext):
    await _start_host_flow(message, state)


@router.message(Command("bold"))
async def cmd_bold(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: " + code("/bold Your text here"), parse_mode=ParseMode.HTML)
        return
    await message.answer(bold(parts[1]), parse_mode=ParseMode.HTML)


@router.message(Command("italic"))
async def cmd_italic(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: " + code("/italic Your text here"), parse_mode=ParseMode.HTML)
        return
    await message.answer(italic(parts[1]), parse_mode=ParseMode.HTML)


@router.message(Command("underline"))
async def cmd_underline(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: " + code("/underline Your text here"), parse_mode=ParseMode.HTML)
        return
    await message.answer(underline(parts[1]), parse_mode=ParseMode.HTML)


@router.message(Command("strike"))
async def cmd_strike(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: " + code("/strike Your text here"), parse_mode=ParseMode.HTML)
        return
    await message.answer(strike(parts[1]), parse_mode=ParseMode.HTML)


@router.message(Command("mono"))
async def cmd_mono(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: " + code("/mono Your text here"), parse_mode=ParseMode.HTML)
        return
    await message.answer(code(parts[1]), parse_mode=ParseMode.HTML)


@router.message(Command("pre"))
async def cmd_pre(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: " + code("/pre Your text here"), parse_mode=ParseMode.HTML)
        return
    await message.answer(pre(parts[1]), parse_mode=ParseMode.HTML)


# Map reply keyboard button texts to actions
@router.message(F.text == "📦 Host My Bot")
async def on_host_btn(message: Message, state: FSMContext):
    await _start_host_flow(message, state)


@router.message(F.text.in_(["📘 How it Works", "ℹ️ How it Works"]))
async def on_how_it_works(message: Message):
    text = (
        "📘 How it Works\n"
        "• Upload your bot code (prefer " + code("bot.py") + " or a .zip).\n"
        "• Send your bot token.\n"
        "• We prepare a secure runtime and get your bot online.\n"
        "• Free plan: 1 hour uptime; Premium: unlimited.\n"
    )
    await message.answer(text, reply_markup=main_menu(get_user(message.from_user.id).get("is_premium")), parse_mode=ParseMode.HTML)


@router.message(F.text == "💰 Upgrade to Premium")
async def on_upgrade_btn(message: Message):
    await cmd_upgrade(message)


@router.message(F.text == "👤 My Info")
async def on_my_info_btn(message: Message):
    await cmd_myinfo(message)


@router.message(F.text == "🆘 Support")
async def on_support(message: Message):
    await message.answer(
        "Support ke liye niche button par click karein:",
        reply_markup=support_url_kb(),
        parse_mode=ParseMode.HTML,
    )


@router.message(F.text == "⚙️ Manage My Bots")
async def on_manage_bots(message: Message):
    user = get_user(message.from_user.id)
    bots = get_user_bots(message.from_user.id)
    lines = ["⚙️ Manage My Bots"]
    for b in bots:
        lines.append(f"• {bold(b.get('name') or 'MyBot')} — ID {code(b['id'])} — Status: {bold(b['status'])}")
    await message.answer("\n".join(lines), reply_markup=main_menu(user.get("is_premium")), parse_mode=ParseMode.HTML)


@router.message(F.text == "🏠 Main Menu")
async def on_main_menu(message: Message):
    user = get_user(message.from_user.id)
    await message.answer("🏠 Main Menu", reply_markup=main_menu(user.get("is_premium")), parse_mode=ParseMode.HTML)


@router.message(F.text == "💬 Contact Admin")
async def on_contact_admin(message: Message):
    user = get_user(message.from_user.id)
    if not user.get("is_premium"):
        await message.answer("This feature is available for premium users only.", parse_mode=ParseMode.HTML)
        return
    await message.answer(
        "💬 Contact Admin\nSend a message starting with " + code("admin:") + " and we'll forward it to the admin.",
        reply_markup=main_menu(True),
        parse_mode=ParseMode.HTML,
    )


@router.message(F.text == "🖋️ Style Text")
async def on_style_text(message: Message):
    demo = (
        "Text styling options (Telegram-supported):\n"
        f"• Bold: {bold('Bold sample')}\n"
        f"• Italic: {italic('Italic sample')}\n"
        f"• Underline: {underline('Underline sample')}\n"
        f"• Strikethrough: {strike('Strikethrough sample')}\n"
        f"• Monospace (inline): {code('inline code')}\n"
        f"• Monospace (block):\n{pre('line 1\\nline 2')}\n\n"
        "Use commands:\n"
        + code("/bold Your text here") + "\n"
        + code("/italic Your text here") + "\n"
        + code("/underline Your text here") + "\n"
        + code("/strike Your text here") + "\n"
        + code("/mono Your text here") + "  (inline monospace)\n"
        + code("/pre Your text here") + "   (block monospace)"
    )
    await message.answer(demo, parse_mode=ParseMode.HTML)


async def _start_host_flow(message: Message, state: FSMContext):
    await state.set_state(HostStates.waiting_file)
    await state.update_data(pending=PendingHost().__dict__)
    await message.answer(
        "🚀 Let's get your bot online!\nPlease upload your bot file (like " + code("bot.py") + " or a .zip containing your bot code).",
        reply_markup=main_menu(get_user(message.from_user.id).get("is_premium")),
        parse_mode=ParseMode.HTML,
    )


@router.message(HostStates.waiting_file, F.document)
async def handle_upload(message: Message, state: FSMContext):
    doc: Document = message.document
    filename = doc.file_name or "upload"
    # Validate extension
    if not (filename.endswith(".py") or filename.endswith(".zip")):
        await message.answer(
            "⚠️ File type not supported.\nPlease upload a .py file or .zip archive.",
            reply_markup=main_menu(get_user(message.from_user.id).get("is_premium")),
            parse_mode=ParseMode.HTML,
        )
        return
    user_id = message.from_user.id
    # Create a bot record (temporary)
    bot_rec = add_bot(user_id, name=os.path.splitext(filename)[0], token="", path="")
    # Download file
    file = await message.bot.get_file(doc.file_id)
    content = await message.bot.download_file(file.file_path)
    data_bytes = content.read()
    workspace = save_upload(user_id, bot_rec["id"], filename, data_bytes)
    from .storage import update_bot
    update_bot(bot_rec["id"], path=workspace)
    await state.update_data(pending=PendingHost(workspace=workspace, entry_name="bot.py", bot_record_id=bot_rec["id"], bot_name=bot_rec["name"]).__dict__)

    await message.answer(
        "🔐 Please send your bot token (e.g. " + code("123456:ABC-DEF...") + ")",
        reply_markup=main_menu(get_user(message.from_user.id).get("is_premium")),
        parse_mode=ParseMode.HTML,
    )
    await state.set_state(HostStates.waiting_token)


@router.message(HostStates.waiting_file)
async def upload_error(message: Message):
    await message.answer(
        "⚠️ File type not supported.\nPlease upload a .py file or .zip archive.",
        reply_markup=main_menu(get_user(message.from_user.id).get("is_premium")),
        parse_mode=ParseMode.HTML,
    )


@router.message(HostStates.waiting_token)
async def handle_token(message: Message, state: FSMContext):
    token = message.text.strip()
    if not await is_valid_token(token):
        await message.answer(
            "❌ That doesn't look like a valid bot token.\nPlease check again from @BotFather.",
            reply_markup=main_menu(get_user(message.from_user.id).get("is_premium")),
            parse_mode=ParseMode.HTML,
        )
        return

    user = get_user(message.from_user.id)
    data = await state.get_data()
    pending = PendingHost(**data.get("pending"))
    # Enforce plan constraints
    if not can_host_more(message.from_user.id):
        await message.answer(
            "⚠️ You already have one active hosted bot.\nFree users can only host 1 bot for 1 hour.\nStop or wait for it to expire, or upgrade to premium 💎.",
            reply_markup=main_menu(get_user(message.from_user.id).get("is_premium")),
            parse_mode=ParseMode.HTML,
        )
        # Cleanup workspace
        if pending.workspace:
            remove_workspace(pending.workspace)
        await state.clear()
        return

    # Build and deploy
    await message.answer("🔧 Setting up your hosting environment...", reply_markup=main_menu(get_user(message.from_user.id).get("is_premium")), parse_mode=ParseMode.HTML)
    ok, runtime_id, err = build_and_run(message.from_user.id, pending.bot_record_id, token, pending.workspace)
    if not ok:
        await message.answer(
            "⚠️ Oops! Something went wrong while setting up your bot.\nPlease double-check your code or try again later.\nTip: Make sure your main file is named bot.py and uses valid Python imports.",
            reply_markup=main_menu(get_user(message.from_user.id).get("is_premium")),
            parse_mode=ParseMode.HTML,
        )
        await state.clear()
        return

    # Success
    plan = "premium" if user.get("is_premium") else "free"
    mark_started(pending.bot_record_id, plan, runtime_id or "")
    await message.answer(
        "✅ Your bot is live!\n"
        f"• Name: {bold(pending.bot_name or 'MyBot')}\n"
        f"• ID: {code(pending.bot_record_id)}\n"
        f"• Host Time: {'Unlimited (Premium Plan)' if plan == 'premium' else '1 Hour (Free Plan)'}\n"
        "Use /stop to end early.",
        reply_markup=main_menu(get_user(message.from_user.id).get("is_premium")),
        parse_mode=ParseMode.HTML,
    )
    await state.clear()


@router.message(Command("stop"))
async def cmd_stop(message: Message):
    # Stop user's active bot(s)
    active = get_active_bots(message.from_user.id)
    if not active:
        await message.answer("ℹ️ No active hosted bots.", reply_markup=main_menu(get_user(message.from_user.id).get("is_premium")), parse_mode=ParseMode.HTML)
        return
    from .services.hoster import stop_runtime
    stopped_any = False
    for b in active:
        rid = b.get("runtime_id")
        if rid:
            stop_runtime(rid)
        mark_stopped(b["id"])
        stopped_any = True
    if stopped_any:
        await message.answer("🛑 Your hosted bot has been stopped.", reply_markup=main_menu(get_user(message.from_user.id).get("is_premium")), parse_mode=ParseMode.HTML)
    else:
        await message.answer("⚙️ Internal error occurred while processing your request.\nDon't worry — our system automatically handles this.\nPlease retry in a few minutes.", reply_markup=main_menu(get_user(message.from_user.id).get("is_premium")), parse_mode=ParseMode.HTML)


# Keep callback-based handlers for backward compatibility with any existing inline keyboards
@router.callback_query(F.data == "my_info")
async def cb_myinfo(cb: CallbackQuery):
    await cmd_myinfo(cb.message)
    await cb.answer()


@router.callback_query(F.data == "upgrade")
async def cb_upgrade(cb: CallbackQuery):
    await cmd_upgrade(cb.message)
    await cb.answer()


@router.callback_query(F.data == "contact_admin")
async def cb_contact_admin(cb: CallbackQuery):
    user = get_user(cb.from_user.id)
    if not user.get("is_premium"):
        await cb.message.answer("This feature is available for premium users only.", parse_mode=ParseMode.HTML)
        await cb.answer()
        return
    await cb.message.answer(
        "💬 Contact Admin\nSend a message starting with " + code("admin:") + " and we'll forward it to the admin.",
        reply_markup=main_menu(True),
        parse_mode=ParseMode.HTML,
    )
    await cb.answer()


@router.message(F.text.startswith("admin:"))
async def forward_to_admin(message: Message):
    user = get_user(message.from_user.id)
    if not user.get("is_premium"):
        return
    from .config import ADMIN_TELEGRAM_ID
    if not ADMIN_TELEGRAM_ID:
        await message.answer("Admin is not configured.", parse_mode=ParseMode.HTML)
        return
    await message.bot.send_message(
        chat_id=ADMIN_TELEGRAM_ID,
        text=f"📨 Message from {bold(message.from_user.full_name)} ({code(str(message.from_user.id))}):\n{message.text[6:]}",
        parse_mode=ParseMode.HTML,
    )
    await message.answer("✅ Sent to admin.", parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "how_it_works")
async def cb_how(cb: CallbackQuery):
    text = (
        "📘 How it Works\n"
        "• Upload your bot code (prefer " + code("bot.py") + " or a .zip).\n"
        "• Send your bot token.\n"
        "• We prepare a secure runtime and get your bot online.\n"
        "• Free plan: 1 hour uptime; Premium: unlimited.\n"
    )
    await cb.message.answer(text, reply_markup=main_menu(get_user(cb.from_user.id).get("is_premium")), parse_mode=ParseMode.HTML)
    await cb.answer()


@router.callback_query(F.data == "manage_bots")
async def cb_manage(cb: CallbackQuery):
    user = get_user(cb.from_user.id)
    bots = get_user_bots(cb.from_user.id)
    lines = ["⚙️ Manage My Bots"]
    for b in bots:
        lines.append(f"• {bold(b.get('name') or 'MyBot')} — ID {code(b['id'])} — Status: {bold(b['status'])}")
    await cb.message.answer("\n".join(lines), reply_markup=main_menu(user.get("is_premium")), parse_mode=ParseMode.HTML)
    await cb.answer()


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(cb: CallbackQuery):
    user = get_user(cb.from_user.id)
    await cb.message.answer("🏠 Main Menu", reply_markup=main_menu(user.get("is_premium")), parse_mode=ParseMode.HTML)
    await cb.answer()


async def on_timeout_notify(bot: Bot, user_id: int, bot_id: str):
    await bot.send_message(
        chat_id=user_id,
        text="⏱️ Hosting time expired!\nYour hosted bot has been stopped automatically.\nUpgrade to premium for unlimited uptime 💎.",
        parse_mode=ParseMode.HTML,
    )


def create_app():
    if not MASTER_BOT_TOKEN:
        raise RuntimeError("MASTER_BOT_TOKEN not set")
    bot = Bot(MASTER_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    dp.include_router(admin_router)

    scheduler = Scheduler(on_timeout_notify=lambda uid, bid: asyncio.create_task(on_timeout_notify(bot, uid, bid)))

    async def run():
        await scheduler.start()
        await dp.start_polling(bot)

    return run


if __name__ == "__main__":
    asyncio.run(create_app()())