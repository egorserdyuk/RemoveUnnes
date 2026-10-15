from keyboards import (
    back_to_group_kb,
    confirm_reset_kb,
    group_menu_kb,
    groups_kb,
    picker_kb,
    types_kb,
    whitelist_kb,
)


def flat_text(kb):
    return " ".join(b["text"] for row in kb["inline_keyboard"] for b in row)


def flat_data(kb):
    return [b["callback_data"] for row in kb["inline_keyboard"] for b in row]


def test_types_kb_marks_blocked():
    kb = types_kb(-1001, {"photo"})
    text = flat_text(kb)
    assert "✅ photo" in text and "❌ video" in text


def test_groups_kb_callback_data():
    kb = groups_kb([(-1001, "Family")])
    btn = kb["inline_keyboard"][0][0]
    assert btn["text"] == "Family" and btn["callback_data"] == "group:-1001"


def test_groups_kb_lang_toggle():
    kb = groups_kb([], lang_toggle=("🌐 Русский", "lang:ru"))
    btn = kb["inline_keyboard"][0][0]
    assert btn["callback_data"] == "lang:ru"


def test_group_menu_counts():
    kb = group_menu_kb(-1001, n_blocked=2, n_white=3)
    text = flat_text(kb)
    assert "Blocked types: 2" in text and "Whitelist: 3 users" in text
    assert "Notifications: OFF" in text


def test_whitelist_kb_remove_buttons():
    kb = whitelist_kb(-1001, [(7, "bob")])
    assert "unwhite:-1001:7" in flat_data(kb)


def test_picker_kb_requests_users():
    kb = picker_kb(42)
    btn = kb["keyboard"][0][0]
    assert btn["text"] == "Pick users"
    assert btn["request_users"]["request_id"] == 42
    assert btn["request_users"]["max_quantity"] == 10
    assert kb["resize_keyboard"] is True


def test_back_and_confirm_buttons():
    assert flat_data(back_to_group_kb(-1001)) == ["group:-1001"]
    datas = flat_data(confirm_reset_kb(-1001))
    assert datas == ["reset_group:-1001:confirm", "group:-1001"]
