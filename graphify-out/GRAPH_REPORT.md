# Graph Report - RemoveUnnes  (2026-11-02)

## Corpus Check
- 38 files · ~20,971 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 3, .example 1, .ini 1)

## Summary
- 550 nodes · 1418 edges · 26 communities (18 shown, 8 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 103 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4e464ec4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- db.py
- handlers_private.py
- Design specification and plan
- config.py
- Persistence schema and docker
- set_lang
- handlers_group.py
- test_private.py
- Keyboard builders
- classify
- test_group.py
- texts.py
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
- FakeConn
- db
- Group config share via base64 line — short design (2026-10-30)

## God Nodes (most connected - your core abstractions)
1. `activate_owner_lang()` - 27 edges
2. `handle_group_message()` - 25 edges
3. `GMsg` - 24 edges
4. `route_private()` - 23 edges
5. `route_cb()` - 23 edges
6. `make_app()` - 23 edges
7. `set_lang()` - 22 edges
8. `make_app()` - 22 edges
9. `make_msg()` - 21 edges
10. `sender()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `Constraints` --references--> `activate_owner_lang()`  [INFERRED]
  docs/superpowers/specs/2026-10-30-group-config-share-design.md → i18n.py
- `Constraints` --references--> `message_fields()`  [INFERRED]
  docs/superpowers/specs/2026-10-30-timing-rate-limits-design.md → adapters.py
- `Left to builder` --references--> `get_notify()`  [INFERRED]
  docs/superpowers/specs/2026-10-30-timing-rate-limits-design.md → db.py
- `Goals` --references--> `incr_stat()`  [INFERRED]
  docs/superpowers/specs/2026-10-30-timing-rate-limits-design.md → db.py
- `Task 5: Wiring + full verification` --references--> `reset_group_data()`  [INFERRED]
  docs/superpowers/plans/2026-10-30-timing-rate-limits.md → db.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Bypass Telegram permissions** — docs_superpowers_specs_2026_10_13_telegram_cleaner_design_telegram_media_remover_bot, spec_intent_above_telegram_permissions, spec_admin_delete_rights, spec_silent_removal_no_group_noise [INFERRED 0.90]
- **Content-type moderation pipeline** — plan_classify_function, plan_db_should_delete, plan_group_router, plan_db_format_stats, spec_service_messages_exempt [INFERRED 0.90]
- **Owner-controlled group configuration** — plan_private_router, plan_keyboards, plan_callback_protocol, spec_owner_only_control, spec_flows_group_config_screen [INFERRED 0.90]

## Communities (26 total, 8 thin omitted)

### Community 0 - "db.py"
Cohesion: 0.08
Nodes (41): main(), add_pending_greeting(), clear_limit(), delete_pending_greeting(), get_limit(), get_limits(), get_stats(), init_pool() (+33 more)

### Community 1 - "handlers_private.py"
Cohesion: 0.14
Nodes (41): add_whitelist(), get_whitelist(), remove_whitelist(), _deny(), _group_title(), _limit_detail_text(), on_back_groups(), on_group_selected() (+33 more)

### Community 2 - "Design specification and plan"
Cohesion: 0.07
Nodes (20): Implementation plan, Telegram Media Remover Bot design, bot.py entrypoint, Callback data protocol, classify(message), classify module, CONTENT_TYPES priority list, reset_group_data helper (+12 more)

### Community 3 - "config.py"
Cohesion: 0.25
Nodes (7): load(), Settings, test_load_api_base_optional(), test_load_missing_env_raises(), make_app(), test_main_awaits_run_and_registers_handlers(), test_main_without_custom_api_base()

### Community 4 - "Persistence schema and docker"
Cohesion: 0.09
Nodes (19): docker-compose PostgreSQL db service, pgdata volume, config.Settings and load, init_pool(dsn), init_schema(pool), db module, register_group and ownership transfer, flush_pending helper (+11 more)

### Community 5 - "set_lang"
Cohesion: 0.06
Nodes (39): format_stats(), should_delete(), detect_language(), get_lang(), n(), _ru_plural_index(), set_lang(), format_mention() (+31 more)

### Community 6 - "handlers_group.py"
Cohesion: 0.06
Nodes (43): get_blocked(), get_notify(), get_owner(), get_owner_lang(), incr_stat(), is_whitelisted(), Global Constraints, Review Focus (+35 more)

### Community 7 - "test_private.py"
Cohesion: 0.15
Nodes (30): on_language(), on_start(), route_private(), _clean_pending_limits(), GCb, GMsg, make_app(), make_msg() (+22 more)

### Community 8 - "Keyboard builders"
Cohesion: 0.19
Nodes (24): back_to_group_kb(), _btn(), confirm_reset_kb(), group_menu_kb(), groups_kb(), _inline(), limits_list_kb(), picker_kb() (+16 more)

### Community 9 - "classify"
Cohesion: 0.10
Nodes (20): _get(), is_start_command(), message_fields(), shared_users(), classify(), is_command_exempt(), _is_service(), FakeMsg (+12 more)

### Community 10 - "test_group.py"
Cohesion: 0.15
Nodes (35): handle_group_message(), GMsg, _base_patches(), _cross_type_patches(), _notify_on_patches(), _stack(), _stack_notify(), test_cooldown_buckets_are_per_user() (+27 more)

### Community 11 - "texts.py"
Cohesion: 0.10
Nodes (28): Task 4: Private-chat Limits UI + copy, _consume_pending_limit(), _lang_toggle(), _start_screen(), GCb, GMsg, make_app(), make_shared() (+20 more)

### Community 12 - "Whitelist request picker"
Cohesion: 1.00
Nodes (3): request_users picker, handlers_whitelist router, Unlimited per-group whitelist

### Community 13 - "Babel translation catalogs"
Cohesion: 0.67
Nodes (3): Babel message catalogs, Compiled .mo files, Babel dependency

### Community 14 - "Private start flow"
Cohesion: 0.67
Nodes (3): Private group config screen, Private start and group list flow, Design goals

### Community 23 - "FakeConn"
Cohesion: 0.14
Nodes (3): _FakeAcquire, FakeConn, _FakeTransaction

### Community 24 - "db"
Cohesion: 0.15
Nodes (12): environment, image, ports, restart, volumes, POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER (+4 more)

### Community 25 - "Group config share via base64 line — short design (2026-10-30)"
Cohesion: 0.20
Nodes (9): Anti-goals, Approaches, Constraints, Goals, Group config share via base64 line — short design (2026-10-30), How (approach A, decided parts), Intent / why, Left to builder (+1 more)

## Knowledge Gaps
- **27 isolated node(s):** `Compiled .mo files`, `Babel dependency`, `Private group config screen`, `Private start and group list flow`, `Plan architecture` (+22 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 150 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `set_lang()` connect `set_lang` to `db.py`, `handlers_private.py`, `handlers_group.py`, `test_private.py`, `texts.py`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `route_private()` (e.g. with `Task 4: Private-chat Limits UI + copy` and `Task 5: Wiring + full verification`) actually correct?**
  _`route_private()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Compiled .mo files`, `Babel dependency`, `Private group config screen` to the rest of the system?**
  _27 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `db.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07667900581702802 - nodes in this community are weakly interconnected._
- **Why does `route_private()` connect `test_private.py` to `handlers_private.py`, `handlers_group.py`, `classify`, `texts.py`, `Group config share via base64 line — short design (2026-10-30)`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Should `handlers_private.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13725490196078433 - nodes in this community are weakly interconnected._
- **Why does `get_limit()` connect `db.py` to `handlers_private.py`, `texts.py`, `handlers_group.py`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._