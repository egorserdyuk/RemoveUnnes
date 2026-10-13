FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py config.py texts.py classify.py keyboards.py db.py \
    handlers_private.py handlers_group.py \
    handlers_membership.py handlers_whitelist.py ./

CMD ["python", "bot.py"]
