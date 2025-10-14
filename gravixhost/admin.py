from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode

from .config import ADMIN_TELEGRAM_ID, ADMIN_TELEGRAM_IDS
from .keyboards import admin_fixed_bar, main_menu, admin_menu, admin_menu_apps
from .storage import (
    _read_db,
    get_user,
    set_premium,
    remove_premium,
    get_user_bots,
    update_user,
)
from .utils import bold, code, human_dt


router = Router(name="admin")


def is_admin(user_id: int) -> bool:
    return bool(ADMIN_TELEGRAM_IDS) and user_id in ADMIN_TELEGRAM_IDS


@router.message(Command("admin"))
async def admin_entry(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        bold("🛡️ Admin Panel"),
        reply_markup=admin_menu(),
        parse_mode=ParseMode.HTML,
    )


# Reply-keyboard based admin navigation
@router.message(F.text == "👥 Users")
async def admin_users_msg(message: Message):
    if not is_admin(message.from_user.id):
        return
    db = _read_db()
    users = db["users"].values()
    text = [bold("👥 Users")]
    for u in users:
        text.append(
            f"• {bold(u.get('name') or 'Unknown')} — ID {code(str(u['id']))} — "
            f"Status: {'Premium' if u.get('is_premium') else 'Free'} — "
            f"Expiry: {human_dt(_safe_parse(u.get('premium_expiry')))}"
        )
    await message.answer("\n".join(text), reply_markup=admin_menu(), parse_mode=ParseMode.HTML)


def _safe_parse(s):
    if not s:
        return None
    from datetime import datetime
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


@router.message(F.text == "💎 Premium")
async def admin_premium_msg(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        bold("💎 Premium Controls") + "\nSend: " + code("premium <user_id> <days>") + " or " + code("unpremium <user_id>"),
        reply_markup=admin_menu(),
        parse_mode=ParseMode.HTML,
    )


@router.message(F.text == "📦 Apps")
async def admin_apps_msg(message: Message):
    if not is_admin(message.from_user.id):
        return
    text = [bold("📦 Apps")]
    db = _read_db()
    for b in db["bots"].values():
        text.append(
            f"• {bold(b.get('name') or 'Unknown')} — ID {code(b['id'])} — Owner {code(str(b['owner_id']))} — "
            f"Status: {bold(b['status'])}"
        )
    text.append("\n" + bold("Admin commands:") + "\n<code>stopbot &lt;id&gt;</code>  <code>restartbot &lt;id&gt;</code>  <code>removebot &lt;id&gt;</code>")
    await message.answer("\n".join(text), reply_markup=admin_menu_apps(), parse_mode=ParseMode.HTML)


@router.message(F.text == "🧾 Logs")
async def admin_logs_msg(message: Message):
    if not is_admin(message.from_user.id):
        return
    db = _read_db()
    logs = db["logs"][-30:]
    text = [bold("🧾 Logs (last 30)"), *["• {0} — {1}".format(l['time'], l['event']) for l in logs]]
    await message.answer("\n".join(text), reply_markup=admin_menu(), parse_mode=ParseMode.HTML)


@router.message(F.text == "⚙️ Settings")
async def admin_settings_msg(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        bold("⚙️ Settings") + "\nFree hosting time: 1 Hour\nRestart policy: Enabled\nUse commands to adjust.",
        reply_markup=admin_menu(),
        parse_mode=ParseMode.HTML,
    )


@router.message(F.text == "🏠 Main Menu")
async def admin_main_menu_msg(message: Message):
    if not is_admin(message.from_user.id):
        return
    await admin_entry(message)


# Quick-action helper buttons (send usage if no id provided)
@router.message(F.text.in_(["stopbot", "restartbot", "removebot"]))
async def admin_action_help(message: Message):
    if not is_admin(message.from_user.id):
        return
    action = message.text.strip()
    usage = {
        "stopbot": "stopbot <id>",
        "restartbot": "restartbot <id>",
        "removebot": "removebot <id>",
    }[action]
    await message.answer(f"Usage: {code(usage)}", parse_mode=ParseMode.HTML, reply_markup=admin_menu_apps())


# Existing command regex handlers (with IDs)
@router.message(F.text.regexp(r"^premium\s+\d+\s+\d+$"))
async def premium_set(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    user_id = int(parts[1])
    days = int(parts[2])

    # Capture previous state
    prev = get_user(user_id)
    was_premium = bool(prev.get("is_premium"))

    set_premium(user_id, days)

    # Notify admin
    await message.answer(
        f"✅ Premium set for {code(str(user_id))} for {days} days.",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_menu(),
    )

    # Notify the target user
    try:
        from datetime import datetime
        updated = get_user(user_id)
        expiry_str = updated.get("premium_expiry")
        expiry_text = human_dt(datetime.fromisoformat(expiry_str)) if expiry_str else "Not set"
        await message.bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 " + str(bold("Premium Activated")) + "\n"
                f"• Duration: {bold(str(days))} days\n"
                f"• Expires on: {bold(expiry_text)}\n"
                "Enjoy unlimited uptime and premium features!"
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        # Silent fail if bot can't message the user (e.g., user never started the bot)
        pass


@router.message(F.text.regexp(r"^unpremium\s+\d+$"))
async def premium_remove(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    user_id = int(parts[1])
    remove_premium(user_id)
    await message.answer(f"✅ Premium removed for {code(str(user_id))}.", parse_mode=ParseMode.HTML, reply_markup=admin_menu())


@router.message(F.text.regexp(r"^stopbot\s+\S+$"))
async def admin_stopbot(message: Message):
    if not is_admin(message.from_user.id):
        return
    bot_id = message.text.strip().split()[1]
    from .storage import get_bot, mark_stopped
    from .services.hoster import stop_runtime
    b = get_bot(bot_id)
    if not b:
        await message.answer("Bot not found.", reply_markup=admin_menu_apps())
        return
    rid = b.get("runtime_id")
    if rid:
        stop_runtime(rid)
    mark_stopped(bot_id)
    await message.answer(f"🛑 Stopped {code(bot_id)}", parse_mode=ParseMode.HTML, reply_markup=admin_menu_apps())


@router.message(F.text.regexp(r"^restartbot\s+\S+$"))
async def admin_restartbot(message: Message):
    if not is_admin(message.from_user.id):
        return
    bot_id = message.text.strip().split()[1]
    from .storage import get_bot
    from .services.hoster import restart_runtime
    b = get_bot(bot_id)
    if not b:
        await message.answer("Bot not found.", reply_markup=admin_menu_apps())
        return
    rid = b.get("runtime_id")
    if rid and restart_runtime(rid):
        await message.answer(f"♻️ Restarted {code(bot_id)}", parse_mode=ParseMode.HTML, reply_markup=admin_menu_apps())
    else:
        await message.answer("Failed to restart.", reply_markup=admin_menu_apps())


@router.message(F.text.regexp(r"^removebot\s+\S+$"))
async def admin_removebot(message: Message):
    if not is_admin(message.from_user.id):
        return
    bot_id = message.text.strip().split()[1]
    from .storage import get_bot, delete_bot
    from .services.hoster import stop_runtime, remove_workspace, remove_image
    b = get_bot(bot_id)
    if not b:
        await message.answer("Bot not found.", reply_markup=admin_menu_apps())
        return
    rid = b.get("runtime_id")
    if rid:
        stop_runtime(rid)
    # remove workspace and image
    image_tag = f"gravixhost_{b['owner_id']}_{bot_id}".lower()
    remove_image(image_tag)
    if b.get("path"):
        remove_workspace(b["path"])
    delete_bot(bot_id)
    await message.answer(f"🗑️ Removed {code(bot_id)}", parse_mode=ParseMode.HTML, reply_markup=admin_menu_apps())


# Keep callback-based handlers for backward compatibility (not used by the new UI)
@router.callback_query(F.data == "admin_users")
async def admin_users(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    db = _read_db()
    users = db["users"].values()
    text = [bold("👥 Users")]
    for u in users:
        text.append(
            f"• {bold(u.get('name') or 'Unknown')} — ID {code(str(u['id']))} — "
            f"Status: {'Premium' if u.get('is_premium') else 'Free'} — "
            f"Expiry: {human_dt(_safe_parse(u.get('premium_expiry')))}"
        )
    await cb.message.answer("\n".join(text), reply_markup=admin_fixed_bar(), parse_mode=ParseMode.HTML)
    await cb.answer()


@router.callback_query(F.data == "admin_premium")
async def admin_premium(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    await cb.message.answer(
        bold("💎 Premium Controls") + "\nSend: " + code("premium <user_id> <days>") + " or " + code("unpremium <user_id>"),
        reply_markup=admin_fixed_bar(),
        parse_mode=ParseMode.HTML,
    )
    await cb.answer()


@router.callback_query(F.data == "admin_apps")
async def admin_apps(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    text = [bold("📦 Apps")]
    db = _read_db()
    for b in db["bots"].values():
        text.append(
            f"• {bold(b.get('name') or 'Unknown')} — ID {code(b['id'])} — Owner {code(str(b['owner_id']))} — "
            f"Status: {bold(b['status'])}"
        )
    text.append("\n" + bold("Admin commands:") + "\n<code>stopbot &lt;id&gt;</code> <code>restartbot &lt;id&gt;</code> <code>removebot &lt;id&gt;</code>")
    await cb.message.answer("\n".join(text), reply_markup=admin_fixed_bar(), parse_mode=ParseMode.HTML)
    await cb.answer()


@router.callback_query(F.data == "admin_logs")
async def admin_logs(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    db = _read_db()
    logs = db["logs"][-30:]
    text = [bold("🧾 Logs (last 30)"), *["• {0} — {1}".format(l['time'], l['event']) for l in logs]]
    await cb.message.answer("\n".join(text), reply_markup=admin_fixed_bar(), parse_mode=ParseMode.HTML)
    await cb.answer()


@router.callback_query(F.data == "admin_settings")
async def admin_settings(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    await cb.message.answer(
        bold("⚙️ Settings") + "\nFree hosting time: 1 Hour\nRestart policy: Enabled\nUse commands to adjust.",
        reply_markup=admin_fixed_bar(),
        parse_mode=ParseMode.HTML,
    )
    await cb.answer()