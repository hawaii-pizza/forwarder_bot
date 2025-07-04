from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Add source", callback_data="add_src")
    kb.button(text="📚 Manage sources", callback_data="mgr_src")
    kb.button(text="🎯 Set target", callback_data="set_tgt")
    kb.button(text="👤 Add filtered user", callback_data="add_filter")
    kb.button(text="👥 Manage filtered users", callback_data="mgr_filter")
    kb.button(text="🛠️ Toggle filter", callback_data="toggle_mode")
    kb.button(text="📄 View config", callback_data="view_cfg")
    kb.button(text="❤️ Donate", callback_data="donate")
    kb.button(text="🔒 Log out", callback_data="logout")
    kb.adjust(2)
    return kb
