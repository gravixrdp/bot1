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
    add_admin_reply,
)
from .utils import bold, code, human_dt, pre, escape


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

@router.message(F.text == "💬 Inbox")
async def admin_inbox(message: Message):
    if not is_admin(message.from_user.id):
        return
    from .storage import get_messages
    msgs = get_messages(limit=50)
    if not msgs:
        await message.answer(bold("💬 Inbox") + "\nNo messages yet.", reply_markup=admin_menu(), parse_mode=ParseMode.HTML)
        return
    # Build readable list
    lines = [bold("💬 Inbox (last 50)") + "\n" + code("Use: reply <user_id> <your message>")]
    for m in msgs:
        from_user = get_user(int(m["user_id"]))
        name = from_user.get("name") or "Unknown"
        prefix = "Admin →" if m.get("from_admin") else "User →"
        lines.append(f"• {m['time']} — {bold(name)} ({code(str(m['user_id']))}) — {prefix}")
        lines.append(f"  {escape(m['text'])}")
    await message.answer("\n".join(lines), reply_markup=admin_menu(), parse_mode=ParseMode.HTML)


@router.message(F.text == "📦 Apps")
async def admin_apps_msg(message: Message):
    if not is_admin(message.from_user.id):
        return
    text = [bold("📦 Apps")]
    db = _read_db()
    bots = list(db["bots"].values())
    for b in bots:
        text.append(
            f"• {bold(b.get('name') or 'Unknown')} — ID {code(b['id'])} — Owner {code(str(b['owner_id']))} — "
            f"Status: {bold(b['status'])}"
        )
    await message.answer("\n".join(text), reply_markup=admin_menu_apps(), parse_mode=ParseMode.HTML)

    # Send quick action buttons for one-tap control
    from .keyboards import bots_action_list
    if bots:
        await message.answer(bold("🛑 Stop a Bot") + "\nTap to stop:", reply_markup=bots_action_list(bots, "Stop", "admin_stop"), parse_mode=ParseMode.HTML)
        await message.answer(bold("♻️ Restart a Bot") + "\nTap to restart:", reply_markup=bots_action_list(bots, "Restart", "admin_restart"), parse_mode=ParseMode.HTML)
        await message.answer(bold("🗑️ Remove a Bot") + "\nTap to remove:", reply_markup=bots_action_list(bots, "Remove", "admin_remove"), parse_mode=ParseMode.HTML)
        await message.answer(bold("📜 Bot Logs") + "\nTap to view:", reply_markup=bots_action_list(bots, "Logs", "admin_logs"), parse_mode=ParseMode.HTML)
    else:
        await message.answer(bold("No bots yet."), reply_markup=admin_menu_apps(), parse_mode=ParseMode.HTML)


@router.message(F.text == "🧾 Logs")
async def admin_logs_msg(message: Message):
    if not is_admin(message.from_user.id):
        return
    db = _read_db()
    logs = db["logs"][-30:]
    header = bold("🧾 Logs (last 30)")
    body = pre("\n".join(["• {0} — {1}".format(l['time'], l['event']) for l in logs]))
    await message.answer(header + "\n" + body, reply_markup=admin_menu(), parse_mode=ParseMode.HTML)

@router.message(F.text == "🗑️ Clear Admin Logs")
async def admin_clear_logs(message: Message):
    if not is_admin(message.from_user.id):
        return
    from .storage import clear_admin_logs, log_event_admin
    clear_admin_logs()
    log_event_admin(f"Admin {message.from_user.id} cleared admin logs")
    await message.answer("✅ Admin logs cleared.", reply_markup=admin_menu(), parse_mode=ParseMode.HTML)


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
@router.message(F.text.in_(["stopbot", "restartbot", "removebot", "logsbot"]))
async def admin_action_help(message: Message):
    if not is_admin(message.from_user.id):
        return
    action = message.text.strip()
    usage_map = {
        "stopbot": "stopbot <id>",
        "restartbot": "restartbot <id>",
        "removebot": "removebot <id>",
        "logsbot": "logsbot <id>",
    }
    usage = usage_map[action]
    # Also list bots with IDs for convenience
    db = _read_db()
    lines = [bold("📦 Bots List")]
    for b in db["bots"].values():
        lines.append(f"• {bold(b.get('name') or 'Unknown')} — ID {code(b['id'])} — Owner {code(str(b['owner_id']))}")
    lines.append("\nSend: " + code(usage))
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=admin_menu_apps())


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
    from .storage import get_bot, mark_stopped, log_event_admin
    from .services.hoster import stop_runtime
    b = get_bot(bot_id)
    if not b:
        await message.answer("Bot not found.", reply_markup=admin_menu_apps())
        return
    rid = b.get("runtime_id")
    if rid:
        stop_runtime(rid)
    mark_stopped(bot_id)
    log_event_admin(f"Admin {message.from_user.id} stopped bot {bot_id}")
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


@router.message(F.text.regexp(r"^logsbot\s+\S+$"))
async def admin_logsbot(message: Message):
    if not is_admin(message.from_user.id):
        return
    bot_id = message.text.strip().split()[1]
    from .storage import get_bot
    from .services.hoster import get_runtime_logs

    db = _read_db()
    logs = []
    for entry in reversed(db.get("logs", [])):
        ev = entry.get("event", "")
        if bot_id in ev:
            logs.append(f"• {entry.get('time','')} — {ev}")
        if len(logs) >= 100:
            break

    # Try to fetch container logs too
    b = get_bot(bot_id)
    runtime_text = ""
    if b and b.get("runtime_id"):
        rid = b["runtime_id"]
        docker_logs = await asyncio.to_thread(get_runtime_logs, rid, 200)
        if docker_logs:
            runtime_text = docker_logs.strip()

    if not logs and not runtime_text:
        await message.answer(bold("No logs for this bot."), reply_markup=admin_menu_apps(), parse_mode=ParseMode.HTML)
        return

    # Chunked send of system logs
    if logs:
        header = bold("🧾 Bot Logs (system)")
        chunk = []
        current_len = 0
        for line in logs:
            if current_len + len(line) + 1 > 3500:
                await message.answer(header + "\n" + pre("\n".join(chunk)), reply_markup=admin_menu_apps(), parse_mode=ParseMode.HTML)
                chunk = []
                current_len = 0
            chunk.append(line)
            current_len += len(line) + 1
        if chunk:
            await message.answer(header + " (cont.)\n" + pre("\n".join(chunk)), reply_markup=admin_menu_apps(), parse_mode=ParseMode.HTML)

    # Send docker logs
    if runtime_text:
        await message.answer(bold("🧾 Bot Logs (container)") + "\n" + pre(runtime_text[-3500:]), reply_markup=admin_menu_apps(), parse_mode=ParseMode.HTML)


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
    bots = list(db["bots"].values())
    for b in bots:
        text.append(
            f"• {bold(b.get('name') or 'Unknown')} — ID {code(b['id'])} — Owner {code(str(b['owner_id']))} — "
            f"Status: {bold(b['status'])}"
        )
    await cb.message.answer("\n".join(text), reply_markup=admin_fixed_bar(), parse_mode=ParseMode.HTML)

    # Inline quick action lists
    from .keyboards import bots_action_list
    if bots:
        await cb.message.answer(bold("🛑 Stop a Bot") + "\nTap to stop:", reply_markup=bots_action_list(bots, "Stop", "admin_stop"), parse_mode=ParseMode.HTML)
        await cb.message.answer(bold("♻️ Restart a Bot") + "\nTap to restart:", reply_markup=bots_action_list(bots, "Restart", "admin_restart"), parse_mode=ParseMode.HTML)
        await cb.message.answer(bold("🗑️ Remove a Bot") + "\nTap to remove:", reply_markup=bots_action_list(bots, "Remove", "admin_remove"), parse_mode=ParseMode.HTML)
        await cb.message.answer(bold("📜 Bot Logs") + "\nTap to view:", reply_markup=bots_action_list(bots, "Logs", "admin_logs"), parse_mode=ParseMode.HTML)
    else:
        await cb.message.answer(bold("No bots yet."), reply_markup=admin_fixed_bar(), parse_mode=ParseMode.HTML)
    await cb.answer()


@router.callback_query(F.data.startswith("admin_stop:"))
async def admin_cb_stop(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    bot_id = cb.data.split(":", 1)[1]
    from .storage import get_bot, mark_stopped
    from .services.hoster import stop_runtime
    b = get_bot(bot_id)
    if not b:
        await cb.message.answer("Bot not found.", reply_markup=admin_fixed_bar(), parse_mode=ParseMode.HTML)
        await cb.answer()
        return
    rid = b.get("runtime_id")
    if rid:
        stop_runtime(rid)
    mark_stopped(bot_id)
    await cb.message.answer(f"🛑 Stopped {code(bot_id)}", reply_markup=admin_fixed_bar(), parse_mode=ParseMode.HTML)
    await cb.answer()


@router.callback_query(F.data.startswith("admin_restart:"))
async def admin_cb_restart(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    bot_id = cb.data.split(":", 1)[1]
    from .storage import get_bot
    from .services.hoster import restart_runtime
    b = get_bot(bot_id)
    if not b:
        await cb.message.answer("Bot not found.", reply_markup=admin_fixed_bar(), parse_mode=ParseMode.HTML)
        await cb.answer()
        return
    rid = b.get("runtime_id")
    if rid and restart_runtime(rid):
        await cb.message.answer(f"♻️ Restarted {code(bot_id)}", reply_markup=admin_fixed_bar(), parse_mode=ParseMode.HTML)
    else:
        await cb.message.answer("Failed to restart.", reply_markup=admin_fixed_bar(), parse_mode=ParseMode.HTML)
    await cb.answer()


@router.callback_query(F.data.startswith("admin_remove:"))
async def admin_cb_remove(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    bot_id = cb.data.split(":", 1)[1]
    from .storage import get_bot, delete_bot
    from .services.hoster import stop_runtime, remove_workspace, remove_image
    b = get_bot(bot_id)
    if not b:
        await cb.message.answer("Bot not found.", reply_markup=admin_fixed_bar(), parse_mode=ParseMode.HTML)
        await cb.answer()
        return
    rid = b.get("runtime_id")
    if rid:
        stop_runtime(rid)
    image_tag = f"gravixhost_{b['owner_id']}_{bot_id}".lower()
    remove_image(image_tag)
    if b.get("path"):
        remove_workspace(b["path"])
    delete_bot(bot_id)
    await cb.message.answer(f"🗑️ Removed {code(bot_id)}", reply_markup=admin_fixed_bar(), parse_mode=ParseMode.HTML)
    await cb.answer()


@router.callback_query(F.data == "admin_logs")
async def admin_logs(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        return
    db = _read_db()
    logs = db["logs"][-30:]
    header = bold("🧾 Logs (last 30)")
    body = pre("\n".join(["• {0} — {1}".format(l['time'], l['event']) for l in logs]))
    await cb.message.answer(header + "\n" + body, reply_markup=admin_fixed_bar(), parse_mode=ParseMode.HTML)
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