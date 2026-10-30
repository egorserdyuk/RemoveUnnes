"""Random deletion-notice phrases: mild insult + username + message type."""

import random

from i18n import _, get_lang

INSULTS: list[str] = [
    "jerk",
    "rascal",
    "sneaky fox",
    "rebel",
    "wise guy",
    "troublemaker",
    "smarty-pants",
    "menace",
    "asshole",
    "fuckboy",
    "scumbag",
    "SCUMBAG",
    "dickhead",
    "faggot",
    "gay",
    "gayboy",
    "fuck",
    "bitch",
]

NOTICE_TEMPLATES: list[str] = [
    "That {insult} {user} tried to send a {type}! Denied.",
    "{user} thought a {type} would sneak past me. Adorable. Deleted.",
    "Nice try, {user} — no {type} allowed here.",
    "The {insult} {user} strikes again with a forbidden {type}!",
    "{user} tested the {type} filter. The filter won.",
    "A wild {type} from {user} appeared! I swept it away.",
    "{user}, sweetie, {type} are banned here. Gone.",
    "Breaking news: {user}'s {type} didn't survive. What a {insult}.",
]

# Optional per-scenario pools. Empty (default) falls back to NOTICE_TEMPLATES,
# so adding replies is opt-in per scenario. Same placeholders as above.
NOTICE_TEMPLATES_DURATION: list[str] = []
NOTICE_TEMPLATES_COOLDOWN: list[str] = []

CONTENT_LABELS: dict[str, str] = {
    "story_forward": "forwarded story",
    "photo": "photo",
    "video": "video",
    "video_note": "video message",
    "voice": "voice message",
    "audio": "audio file",
    "document": "file",
    "animation": "GIF",
    "sticker": "sticker",
    "poll": "poll",
    "contact": "contact",
    "location": "location",
    "venue": "venue",
    "dice": "dice roll",
    "game": "game",
    "invoice": "invoice",
    "successful_payment": "payment",
    "checklist": "checklist",
    "text": "text message",
}



RUSSIAN_REPLIES: list[str] = [
    "{user} Че ты, хуй во рту? Хотел голосовое записать?",
    "Ты че {user}, плохо слышишь меня, толстый блять!? Здесь нельзя голосовые!",
    "Еще одно голосовое и я дам цветами леща {user}",
    "{user} попробуй ЕЩЁ!",
    "Еще одно голосовое от {user} и я наложу себе в руки!",
    "Да мне похуй что ты вообще говоришь {user}",
    "{user}, я прочитал твоё голосовое. Не слушал, просто по лицу видно, что хуйню сказал.",
    "{user}, ты бы ещё письмо голубем отправил. Пиши текстом, долбоёб",
    "Голосовое от {user} удалено. Грустно. Хотя нет, вообще похуй.",
    "{user}, голосовое не удалось отправить: у бота сегодня плохое настроение. И он твою мать ебал.",
    "{user}, у меня на тебя заведена папка «Дебилы, которые не умеют писать текстом». Ты там уже на первом месте.",
    "Голосовое от {user} отправлено в архив «Хуйня, которую никто не просил».",
    "{user}, запиши голосовое своей маме. Она, может, и послушает. Мы нет.",
    "Это не баг, {user}, это фича. Фича называется «пошёл нахуй со своими голосовыми».",
    "Жиза: {user} отправил голосовое, а бот его удалил. Пиздец, как предсказуемо.",
    "{user}, голосовое удалено, как и твои шансы на уважение в этом чате. Ты тут вообще для мебели, пиздабол.",
    "{user}, я послушал всё, что ты говорил за год. Вывод: лучше бы ты молчал, конченый.",
    "Голосовое от {user} удалено. Совет старейшин чата собрался и решил: ты хуй с горы, а гора давно жалуется.",
    "{user}, говорят, у человека есть право хранить молчание. Но у тебя есть обязанность его хранить, мудила.",
    "{user} дрочи мой хуй себе в рот, я знаю ты любишь отсасывать",
    "{user}, тебе для чего рот нужен?",
    "{user}, какое нахуй голосовое? Если продолжишь в том же духе, то скоро будешь разговаривать как Марси, только свистом, чудовище",
    "{user}, где твоя кружка, сынок?",
    "{user}, я ошибся в жизни всего два раза, второй раз когда прослушал это голосовое, а первый когда зачал тебя. Голосовое я удалил, жаль что тебя не могу. Лох.",
    "Здесь было голосовое от {user}. Судя по звукам, его ебут толпой. Видимо случайно записалось, я удалил.",
    "{user}, твой рот создан для двух вещей: жрать и сосать. Голосовые в сделку не входили.",
    "{user}, у меня два вопроса: нахуя ты это записал и почему твои родители не остановились на брате?",
    "{user}, у меня два вопроса: нахуя ты это записал и почему твои родители не остановились на сестре?",
    "{user}, Вам направлена повестка в военкомат. Ознакомиться: реестрповесток.рф",
    "{user}, ты ебало закрой, а пальцы из очка вытащи. Да, ими можно ещё и печатать.",
    """1000-7, 1000-7, 1000-7...

    Да блять, опять перепутал, надо было удалить, а не озвучивать хуйню от {user}""",
    "{user}, я так понимаю Мом насадку на вейп в виде члена быстрее получит, чем ты поймёшь что голосовые запрещены?",
    "{user}, твоя мать родила тебя случайно, а я удаляю твои голосовые специально. Чувствуешь разницу, чмом?",
    "{user}, у тебя рот работает быстрее, чем мозг. Ещё и голосовые записываешь. Дела...",
    "{user}, дико извиняюсь, а зачем всему чату слушать как ты напеваешь Егора Крида?",
    "Бот проанализировал голосовое от {user} и выдал ошибку: «Обнаружено слишком много хуйни, обработка невозможна». Удалено.",
    "{user}, тебе рот для чего нужен? По назначению используй",
]

# Optional per-scenario RU pools. Empty (default) falls back to RUSSIAN_REPLIES.
# Only {user} is substituted here.
RUSSIAN_REPLIES_DURATION: list[str] = []
RUSSIAN_REPLIES_COOLDOWN: list[str] = []

# Common aliases for language-specific Russian replies.
RUSSIAN_TEMPLATES = RUSSIAN_REPLIES
RU_REPLIES = RUSSIAN_REPLIES
RUSSIAN_PHRASES = RUSSIAN_REPLIES
RUSSIAN_ROASTS = RUSSIAN_REPLIES
RUSSIAN_NOTICES = RUSSIAN_REPLIES



MAX_UNIQUE_ATTEMPTS = 10


def _scenario_templates(reason: str | None) -> list[str]:
    """Scenario pool if the owner filled it, else the generic pool."""
    if reason == "duration" and NOTICE_TEMPLATES_DURATION:
        return NOTICE_TEMPLATES_DURATION
    if reason == "cooldown" and NOTICE_TEMPLATES_COOLDOWN:
        return NOTICE_TEMPLATES_COOLDOWN
    return NOTICE_TEMPLATES


def _scenario_ru_replies(reason: str | None) -> list[str]:
    if reason == "duration" and RUSSIAN_REPLIES_DURATION:
        return RUSSIAN_REPLIES_DURATION
    if reason == "cooldown" and RUSSIAN_REPLIES_COOLDOWN:
        return RUSSIAN_REPLIES_COOLDOWN
    return RUSSIAN_REPLIES


def render_notice(
    user: str, ctype: str, reason: str | None = None, rng=random.choice
) -> str:
    """Pick a random template + insult and fill in user and type label.

    `reason` is one of "blocked" (default), "duration", "cooldown".
    A scenario pool is used only when the owner filled it; otherwise the
    generic pool applies, so per-scenario replies are opt-in.
    """
    if get_lang() == "ru":
        return rng(_scenario_ru_replies(reason)).format(user=user)
    templates = _scenario_templates(reason)
    return _(rng(templates)).format(
        user=user, insult=_(rng(INSULTS)), type=_(CONTENT_LABELS[ctype])
    )


def render_unique_notice(
    user: str, ctype: str, previous: list[str], reason: str | None = None, rng=random.choice
) -> str:
    """Render a notice that doesn't repeat any of the previous bot replies.

    Re-rolls the random pick while the text matches a recent one; after
    MAX_UNIQUE_ATTEMPTS draws the last one is sent as-is (never hangs).
    """
    text = render_notice(user, ctype, reason=reason, rng=rng)
    for _ in range(MAX_UNIQUE_ATTEMPTS - 1):
        if text not in previous:
            return text
        text = render_notice(user, ctype, reason=reason, rng=rng)
    return text


def format_mention(sender) -> str:
    """@username, first name, or 'someone' for anonymous senders."""
    if sender is None:
        return _("someone")
    username = getattr(sender, "username", None)
    if username:
        return f"@{username}"
    return getattr(sender, "first_name", None) or _("someone")
