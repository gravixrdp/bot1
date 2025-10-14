from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu(is_premium: bool) -> InlineKeyboardMarkup:
    if is_premium:
        buttons = [
            [InlineKeyboardButton(text="📦 Host My Bot", callback_data="host_start")],
            [InlineKeyboardButton(text="⚙️ Manage My Bots", callback_data="manage_bots")],
            [InlineKeyboardButton(text="🧩 Extra Support", callback_data="extra_support")],
            [InlineKeyboardButton(text="📘 How it Works", callback_data="how_it_works")],
            [InlineKeyboardButton(text="💬 Contact Admin", callback_data="contact_admin")],
            [InlineKeyboardButton(text="👤 My Info", callback_data="my_info")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton(text="📦 Host My Bot", callback_data="host_start")],
            [InlineKeyboardButton(text="ℹ️ How it Works", callback_data="how_it_works")],
            [InlineKeyboardButton(text="💰 Upgrade to Premium", callback_data="upgrade")],
            [InlineKeyboardButton(text="👤 My Info", callback_data="my_info")],
        ]
    buttons.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_fixed_bar() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="👥 Users", callback_data="admin_users"),
            InlineKeyboardButton(text="💎 Premium", callback_data="admin_premium"),
            InlineKeyboardButton(text="📦 Apps", callback_data="admin_apps"),
        ],
        [
            InlineKeyboardButton(text="🧾 Logs", callback_data="admin_logs"),
            InlineKeyboardButton(text="⚙️ Settings", callback_data="admin_settings"),
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)