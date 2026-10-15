# RemoveUnnes — Telegram Media Remover Bot

Silently deletes blocked message types in your groups, even from admins.
Only whitelisted users bypass the blocks. Stats stay private to the owner.

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather), copy the token.
2. In BotFather, turn **Group Privacy OFF** (`/setprivacy` → Disable),
   otherwise the bot never sees normal group messages.
3. Start Postgres:
   ```bash
   docker compose up -d db
   ```
4. Install deps and run:
   ```bash
   python -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt
   export BOT_TOKEN=... POSTGRES_DSN=postgresql://remover:remover@localhost:5432/remover
   python bot.py
   ```
5. Open the bot in Telegram (`/start`), add it to a group **as admin with
   Delete Messages right**, then configure blocked types / whitelist in the
   private chat.

## Tests

```bash
python -m pytest tests/ -m "not integration"
```

Integration tests need a live DB:

```bash
POSTGRES_DSN_TEST=postgresql://remover:remover@localhost:5432/remover python -m pytest tests/ -m integration
```

## Languages (i18n)

UI copy is English-first with a built-in Russian dictionary — no Babel,
no `.po`/`.mo` files, no compile step.

- English strings are the msgids, used inline throughout the code.
- Russian translations live in `i18n_ru.py` (`RU_STRINGS` for plain strings,
  `RU_PLURALS` for singular/plural pairs with full 3-form Russian plurals).
- Missing keys fall back to English at runtime, so a partial translation
  never breaks the bot.
- Each owner picks a language with the 🌐 button in the private chat
  (auto-detected from their Telegram `language_code` on first `/start`).

To add or fix Russian copy, edit `i18n_ru.py` directly and restart.
To add a third language, add its dict plus locale plumbing in `i18n.py`.
