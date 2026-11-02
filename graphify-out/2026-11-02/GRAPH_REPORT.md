# Graph Report - RemoveUnnes  (2026-10-15)

## Corpus Check
- Corpus is ~10,116 words - fits in a single context window. You may not need a graph.

## Summary
- 303 nodes · 695 edges · 23 communities (15 shown, 8 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 50 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- PostgreSQL membership store
- Private chat handler UI
- Design specification and plan
- Entrypoint and configuration
- Persistence schema and docker
- Group moderation and notices
- Whitelist picker flow
- Internationalization and catalogs
- Keyboard builders
- Content classification
- Group message handling
- User-facing text constants
- Whitelist request picker
- Babel translation catalogs
- Private start flow
- Plan architecture
- Stats formatting
- Command exemption logic
- aiogram dependency stack
- Graphify knowledge graph
- Bot setup workflow
- Test async runtime

## God Nodes (most connected - your core abstractions)
1. `activate_owner_lang()` - 20 edges
2. `_handle()` - 16 edges
3. `_deny()` - 15 edges
4. `on_group_selected()` - 15 edges
5. `on_my_chat_member()` - 14 edges
6. `_start_screen()` - 14 edges
7. `on_stats()` - 14 edges
8. `set_lang()` - 14 edges
9. `get_owner_lang()` - 12 edges
10. `on_toggle()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `RemoveUnnes Telegram Media Remover Bot` --semantically_similar_to--> `Telegram Media Remover Bot design`  [INFERRED] [semantically similar]
  README.md → docs/superpowers/specs/2026-10-13-telegram-cleaner-design.md
- `BotFather group privacy off` --semantically_similar_to--> `Group privacy requirement`  [INFERRED] [semantically similar]
  README.md → docs/superpowers/specs/2026-10-13-telegram-cleaner-design.md
- `Admin delete rights requirement` --semantically_similar_to--> `Delete rights requirement`  [INFERRED] [semantically similar]
  README.md → docs/superpowers/specs/2026-10-13-telegram-cleaner-design.md
- `test_load_api_base_optional()` --calls--> `load()`  [EXTRACTED]
  tests/test_config.py → config.py
- `test_should_delete_anonymous_by_type()` --calls--> `should_delete()`  [EXTRACTED]
  tests/test_db.py → db.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Bypass Telegram permissions** — docs_superpowers_specs_2026_10_13_telegram_cleaner_design_telegram_media_remover_bot, spec_intent_above_telegram_permissions, spec_admin_delete_rights, spec_silent_removal_no_group_noise [INFERRED 0.90]
- **Content-type moderation pipeline** — plan_classify_function, plan_db_should_delete, plan_group_router, plan_db_format_stats, spec_service_messages_exempt [INFERRED 0.90]
- **Owner-controlled group configuration** — plan_private_router, plan_keyboards, plan_callback_protocol, spec_owner_only_control, spec_flows_group_config_screen [INFERRED 0.90]

## Communities (23 total, 8 thin omitted)

### Community 0 - "PostgreSQL membership store"
Cohesion: 0.12
Nodes (24): add_pending_greeting(), add_whitelist(), delete_pending_greeting(), get_owner_lang(), get_stats(), init_pool(), init_schema(), list_pending_greetings() (+16 more)

### Community 1 - "Private chat handler UI"
Cohesion: 0.18
Nodes (27): get_blocked(), get_notify(), toggle_blocked(), whitelist_count(), _deny(), _group_title(), on_back_groups(), on_group_selected() (+19 more)

### Community 2 - "Design specification and plan"
Cohesion: 0.07
Nodes (20): Implementation plan, Telegram Media Remover Bot design, bot.py entrypoint, Callback data protocol, classify(message), classify module, CONTENT_TYPES priority list, reset_group_data helper (+12 more)

### Community 3 - "Entrypoint and configuration"
Cohesion: 0.11
Nodes (12): main(), load(), Settings, format_stats(), should_delete(), test_load_api_base_optional(), test_load_missing_env_raises(), test_format_stats_order_and_empty() (+4 more)

### Community 4 - "Persistence schema and docker"
Cohesion: 0.09
Nodes (19): docker-compose PostgreSQL db service, pgdata volume, config.Settings and load, init_pool(dsn), init_schema(pool), db module, register_group and ownership transfer, flush_pending helper (+11 more)

### Community 5 - "Group moderation and notices"
Cohesion: 0.14
Nodes (12): get_owner(), incr_stat(), is_whitelisted(), _handle(), _notify_no_rights(), _now(), format_mention(), render_notice() (+4 more)

### Community 6 - "Whitelist picker flow"
Cohesion: 0.16
Nodes (15): get_whitelist(), remove_whitelist(), _next_request_id(), on_back_group(), on_pick_users(), on_unwhite(), on_users_shared(), on_white_list() (+7 more)

### Community 7 - "Internationalization and catalogs"
Cohesion: 0.13
Nodes (11): detect_language(), get_lang(), msgid(), msgid_plural(), set_lang(), teardown_function(), test_detect_language(), test_english_returns_msgid() (+3 more)

### Community 8 - "Keyboard builders"
Cohesion: 0.21
Nodes (12): n(), back_to_group_kb(), group_menu_kb(), groups_kb(), picker_kb(), types_kb(), whitelist_kb(), test_group_menu_counts() (+4 more)

### Community 9 - "Content classification"
Cohesion: 0.26
Nodes (10): classify(), is_command_exempt(), _is_service(), photo_msg(), test_anonymous_channel_photo_classifies(), test_captioned_photo_counts_as_photo(), test_command_exempt_when_text_blocked(), test_non_command_text_not_exempt() (+2 more)

### Community 10 - "Group message handling"
Cohesion: 0.40
Nodes (10): handle_edited_message(), handle_group_message(), make_bot(), make_msg(), test_allowed_type_passes(), test_blocked_photo_deleted_and_counted(), test_edited_message_rechecked(), test_no_rights_dms_owner_once() (+2 more)

### Community 11 - "User-facing text constants"
Cohesion: 0.21
Nodes (10): _lang_toggle(), on_start(), _start_screen(), GROUPS_EMPTY(), LANG_BUTTON_EN(), LANG_BUTTON_RU(), MY_GROUPS(), NEED_ADMIN() (+2 more)

### Community 12 - "Whitelist request picker"
Cohesion: 1.00
Nodes (3): request_users picker, handlers_whitelist router, Unlimited per-group whitelist

### Community 13 - "Babel translation catalogs"
Cohesion: 0.67
Nodes (3): Babel message catalogs, Compiled .mo files, Babel dependency

### Community 14 - "Private start flow"
Cohesion: 0.67
Nodes (3): Private group config screen, Private start and group list flow, Design goals

## Knowledge Gaps
- **27 isolated node(s):** `graphify knowledge graph`, `Bot setup workflow`, `Integration test marker`, `Compiled .mo files`, `docker-compose PostgreSQL db service` (+22 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 81 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `set_lang()` connect `Internationalization and catalogs` to `PostgreSQL membership store`, `Private chat handler UI`, `User-facing text constants`, `Group moderation and notices`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **What connects `graphify knowledge graph`, `Bot setup workflow`, `Integration test marker` to the rest of the system?**
  _27 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `PostgreSQL membership store` be split into smaller, more focused modules?**
  _Cohesion score 0.12222222222222222 - nodes in this community are weakly interconnected._
- **Why does `classify()` connect `Content classification` to `Group moderation and notices`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Should `Design specification and plan` be split into smaller, more focused modules?**
  _Cohesion score 0.07126436781609195 - nodes in this community are weakly interconnected._
- **Why does `activate_owner_lang()` connect `Private chat handler UI` to `PostgreSQL membership store`, `Whitelist picker flow`, `Internationalization and catalogs`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Should `Entrypoint and configuration` be split into smaller, more focused modules?**
  _Cohesion score 0.11384615384615385 - nodes in this community are weakly interconnected._