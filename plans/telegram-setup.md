# Telegram Bot Setup — @ProbBrain_bot

**Action required: human must complete BotFather steps.**
The bot token is already configured once created. These are the one-time setup steps.

---

## 1. Create the bot via BotFather

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Name: `ProbBrain`
4. Username: `ProbBrainBot` (or similar if taken — must end in `bot`)
5. BotFather will return a token like `123456789:ABC-...`
6. Copy the token into `.env`:
   ```
   TELEGRAM_BOT_TOKEN=<your token here>
   ```

> **Note:** A token is already set in `.env`. If you created the bot previously and have the token, no action needed — skip to step 3.

---

## 2. Create the channel

1. Create a new Telegram channel (public or private)
2. Set username to `@ProbBrain` (or `@ProbBrainSignals`)
3. Add `@ProbBrainBot` as an **admin** with permission to post messages
4. Get the channel ID:
   - Forward a message from the channel to `@userinfobot`
   - Or use `https://api.telegram.org/bot<TOKEN>/getUpdates` after sending a message
5. Set in `.env`:
   ```
   TELEGRAM_CHANNEL_ID=-100XXXXXXXXXX
   ```

> **Note:** Channel ID `-1003663233989` is already configured in `.env`.

---

## 3. Test the bot

```bash
cd /home/slova/ProbBrain
python -c "
import os, httpx
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('TELEGRAM_BOT_TOKEN')
resp = httpx.get(f'https://api.telegram.org/bot{token}/getMe')
print(resp.json())
"
```

A successful response will show `{'ok': True, 'result': {'username': 'ProbBrainBot', ...}}`.

---

## 4. Send a test message

```bash
python -c "
import os, httpx
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('TELEGRAM_BOT_TOKEN')
channel = os.getenv('TELEGRAM_CHANNEL_ID')
resp = httpx.post(f'https://api.telegram.org/bot{token}/sendMessage',
    json={'chat_id': channel, 'text': 'ProbBrain bot is live.'})
print(resp.json())
"
```

---

## 5. Running the bot

**Polling mode (dev/local):**
```bash
cd /home/slova/ProbBrain
python run_bot.py
```

**Webhook mode (production):**
Set `TELEGRAM_WEBHOOK_URL` in `.env` to your public HTTPS URL, then run `run_bot.py`. The server listens on `WEBHOOK_PORT` (default 8443).

---

## Current config in .env

| Variable | Status |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Set |
| `TELEGRAM_CHANNEL_ID` | Set (`-1003663233989`) |
| `TELEGRAM_WEBHOOK_URL` | Empty (polling mode) |
