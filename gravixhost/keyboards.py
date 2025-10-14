from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


# Reply keyboard that stays above the input field and sends button text as a message
def main_menu(is_premium: bool) -> ReplyKeyboardMarkup:
    if is_premium:
        # Single horizontal row
        rows = [[
            KeyboardButton(text="📦 Host My Bot"),
            KeyboardButton(text="⚙️ Manage My Bots"),
            KeyboardButton(text="📘 How it Works"),
            KeyboardButton(text="💬 Contact Admin"),
            KeyboardButton(text="🆘 Support"),
            KeyboardButton(text="👤 My Info"),
            KeyboardButton(text="⏳ Premium Time Left"),
            KeyboardButton(text="🏠 Main Menu"),
        ]]
    else:
        # Single horizontal row
        rows = [[
            KeyboardButton(text="📦 Host My Bot"),
            KeyboardButton(text="⚙️ Manage My Bots"),
            KeyboardButton(text="ℹ️ How it Works"),
            KeyboardButton(text="💰 Upgrade to Premium"),
            KeyboardButton(text="🆘 Support"),
            KeyboardButton(text="👤 My Info"),
            KeyboardButton(text="⏳ Premium Time Left"),
            KeyboardButton(text="🏠 Main Menu"),
        ]]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=False, is_persistent=True)


# User "Manage My Bots" persistent menu
def user_manage_menu() -> ReplyKeyboardMarkup:
    # Single horizontal row with all actions
    rows = [[
        KeyboardButton(text="🔍 My Running Bots"),
        KeyboardButton(text="🛑 Stop My Bot"),
        KeyboardButton(text="♻️ Restart My Bot"),
        KeyboardButton(text="🗑️ Remove My Bot"),
        KeyboardButton(text="📜 Bot Logs"),
        KeyboardButton(text="🧾 My Logs"),
        KeyboardButton(text="🏠 Main Menu"),
    ]]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=False, is_persistent=True)


# Admin menus as persistent reply keyboards
def admin_menu() -> ReplyKeyboardMarkup:
    # Single horizontal row
    rows = [[
        KeyboardButton(text="👥 Users"),
        KeyboardButton(text="💎 Premium"),
        KeyboardButton(text="📦 Apps"),
        KeyboardButton(text="🧾 Logs"),
        KeyboardButton(text="🗑️ Clear Admin Logs"),
        KeyboardButton(text="⚙️ Settings"),
        KeyboardButton(text="🏠 Main Menu"),
    ]]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=False, is_persistent=True)


def admin_menu_apps() -> ReplyKeyboardMarkup:
    # Single horizontal row including quick actions
    rows = [[
        KeyboardButton(text="👥 Users"),
        KeyboardButton(text="💎 Premium"),
        KeyboardButton(text="📦 Apps"),
        KeyboardButton(text="🧾 Logs"),
        KeyboardButton(text="⚙️ Settings"),
        KeyboardButton(text="🏠 Main Menu"),
        KeyboardButton(text="stopbot"),
        KeyboardButton(text="restartbot"),
        KeyboardButton(text="removebot"),
    ]]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=False, is_persistent=True)


def admin_fixed_bar() -> InlineKeyboardMarkup:
    # Kept for backward compatibility (unused now)
    buttons = [
        [
            InlineKeyboardButton(text="👥 Users", callback_data="admin_users"),
        ],
        [
            InlineKeyboardButton(text="💎 Premium", callback_data="admin_premium"),
        ],
        [
            InlineKeyboardButton(text="📦 Apps", callback_data="admin_apps"),
        ],
        [
            InlineKeyboardButton(text="🧾 Logs", callback_data="admin_logs"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Settings", callback_data="admin_settings"),
        ],
        [
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def support_url_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Open Support Chat", url="https://t.me/Dravonnbot")]
        ]
    )


def bots_action_list(bots, action_text: str, prefix: str) -> InlineKeyboardMarkup:
    """
    Build an inline keyboard with one button per bot.
    action_text: label prefix e.g., "Delete", "Stop", "Restart", "Logs"
    prefix: callback prefix e.g., "user_remove", "user_stop"
    """
    rows = []
    for b in bots:
        name = b.get("name") or "MyBot"
        bid = b.get("id")
        rows.append([InlineKeyboardButton(text=f"{action_text}: {name} — {bid}", callback_data=f"{prefix}:{bid}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)