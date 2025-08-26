# COPY THIS FILE to config.py and fill your own values.
# Do NOT commit config.py with real keys into GitHub.

API_ID = 123456                # from https://my.telegram.org
API_HASH = "your_api_hash"     # from https://my.telegram.org
PHONE_NUMBER = "+1234567890"   # your phone number with country code

CHANNEL_USERNAME = "@your_channel"   # channel to monitor (e.g. @master_NF)
GROUP_USERNAME = "@your_group"       # the linked discussion group (optional)
COMMENT_TEXT = "."                   # short comment to post (keep short)

# Session file name used by Telethon (do not commit .session files)
SESSION_NAME = "bot_session"

# Tuning (keep default unless you know what you do)
RETRY_INTERVAL = 0.05        # seconds between retry attempts (50 ms)
POLL_INTERVAL = 0.25         # channel poller interval (250 ms)
KEEP_ALIVE_INTERVAL = 20     # seconds between keep-alive pings
CLOCK_DELTA_THRESHOLD = 10   # seconds; if system clock > this vs remote, poller used
