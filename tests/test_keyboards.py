from keyboards import groups_kb, group_menu_kb, types_kb, whitelist_kb, picker_kb


def test_types_kb_marks_blocked():
    kb = types_kb(-1001, {"photo"})
    flat = " ".join(b.text for row in kb.inline_keyboard for b in row)
    assert "✅ photo" in flat and "❌ video" in flat


def test_groups_kb_callback_data():
    kb = groups_kb([(-1001, "Family")])
    btn = kb.inline_keyboard[0][0]
    assert btn.text == "Family" and btn.callback_data == "group:-1001"


def test_group_menu_counts():
    kb = group_menu_kb(-1001, n_blocked=2, n_white=3)
    flat = " ".join(b.text for row in kb.inline_keyboard for b in row)
    assert "Blocked types: 2" in flat and "Whitelist: 3 users" in flat


def test_whitelist_kb_remove_buttons():
    kb = whitelist_kb(-1001, [(7, "bob")])
    datas = [b.callback_data for row in kb.inline_keyboard for b in row]
    assert "unwhite:-1001:7" in datas


def test_picker_kb_requests_users():
    kb = picker_kb(42)
    btn = kb.keyboard[0][0]
    assert btn.text == "Pick users"
    assert btn.request_users is not None
    assert btn.request_users.request_id == 42
    assert btn.request_users.max_quantity == 10
