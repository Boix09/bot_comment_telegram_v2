import time
import asyncio
import json
import urllib.request
from email.utils import parsedate_to_datetime

from telethon import TelegramClient, events, functions
from telethon.errors import ChatAdminRequiredError, ChatWriteForbiddenError, FloodWaitError
try:
    from telethon.network.connection import ConnectionTcpAbridged as ConnType
except Exception:
    ConnType = None

from logger import get_logger
import config as cfg

log = get_logger('bot')

# Runtime state
ENTITIES = {'channel': None, 'group': None}
pending_comments = {}   # channel_msg_id -> {'ts': ..., 'tries': int}
seen_ids = set()

# ------------------ Time helpers ------------------
def fetch_remote_time():
    # try worldtimeapi
    try:
        with urllib.request.urlopen('https://worldtimeapi.org/api/ip', timeout=5) as r:
            j = json.load(r)
            if 'unixtime' in j:
                return float(j['unixtime'])
    except Exception:
        pass
    # fallback: google date header
    try:
        req = urllib.request.Request('https://www.google.com', headers={'User-Agent': 'curl/7.64.1'})
        with urllib.request.urlopen(req, timeout=5) as r:
            dh = r.headers.get('Date')
            if dh:
                return parsedate_to_datetime(dh).timestamp()
    except Exception:
        pass
    return None

def check_system_clock(threshold: float = None):
    if threshold is None:
        threshold = cfg.CLOCK_DELTA_THRESHOLD
    remote = fetch_remote_time()
    if remote is None:
        log.warning('Impossible de récupérer l heure distante — activation du poller par sécurité')
        return False, 0.0
    local = time.time()
    delta = remote - local
    ok = abs(delta) <= threshold
    if not ok:
        log.warning(f'Horloge décalée: delta={delta:.1f}s (> {threshold}s). Poller fallback conseillé.')
    else:
        log.info(f'Horloge OK (delta={delta:.2f}s).')
    return ok, delta

# ------------------ Client factory & preload ------------------
def create_client():
    conn = ConnType if ConnType else None
    client = TelegramClient(cfg.SESSION_NAME, cfg.API_ID, cfg.API_HASH, connection=conn)
    return client

async def preload_entities(client):
    try:
        ENTITIES['channel'] = await client.get_entity(cfg.CHANNEL_USERNAME)
        log.info(f'Channel entity loaded: {cfg.CHANNEL_USERNAME}')
    except Exception as e:
        log.error(f'Impossible de charger channel entity: {e}')
        ENTITIES['channel'] = None
    try:
        ENTITIES['group'] = await client.get_entity(cfg.GROUP_USERNAME)
        log.info(f'Group entity loaded: {cfg.GROUP_USERNAME}')
    except Exception:
        ENTITIES['group'] = None

# ------------------ Comment functions ------------------
async def try_comment_fast(client, channel_msg_id: int) -> bool:
    if ENTITIES['channel'] is None:
        raise RuntimeError('Channel entity missing')
    await client.send_message(entity=ENTITIES['channel'], message=cfg.COMMENT_TEXT, comment_to=channel_msg_id)
    return True

async def get_discussion_msg_id(client, channel_msg_id: int):
    if ENTITIES['channel'] is None:
        return None
    try:
        r = await client(functions.messages.GetDiscussionMessageRequest(peer=ENTITIES['channel'], msg_id=channel_msg_id))
        if r and getattr(r, 'messages', None):
            return r.messages[0].id
    except Exception as e:
        log.debug(f'GetDiscussionMessageRequest failed: {e}')
    return None

async def try_comment_via_group(client, group_msg_id: int) -> bool:
    if ENTITIES['group'] is None:
        raise RuntimeError('Group entity missing')
    await client.send_message(entity=ENTITIES['group'], message=cfg.COMMENT_TEXT, reply_to=group_msg_id)
    return True

async def safe_comment(client, channel_msg_id: int) -> bool:
    t0 = time.perf_counter()
    try:
        await try_comment_fast(client, channel_msg_id)
        dt = (time.perf_counter() - t0) * 1000
        log.info(f'✅ Fast comment sent for {channel_msg_id} in {dt:.1f} ms')
        return True
    except (ChatAdminRequiredError, ChatWriteForbiddenError) as e:
        log.debug(f'Fast refused: {e} -> fallback')
    except FloodWaitError as e:
        log.warning(f'FloodWait (fast) {getattr(e, "seconds", "?")}s')
        raise
    except Exception as e:
        log.debug(f'Fast error: {e} -> fallback')

    try:
        disc_id = await get_discussion_msg_id(client, channel_msg_id)
        if disc_id and ENTITIES['group']:
            await try_comment_via_group(client, disc_id)
            dt = (time.perf_counter() - t0) * 1000
            log.info(f'✅ Fallback group comment for {channel_msg_id} in {dt:.1f} ms (disc_id={disc_id})')
            return True
        else:
            log.debug('No discussion mirror ready')
    except (ChatAdminRequiredError, ChatWriteForbiddenError) as e:
        log.debug(f'Fallback refused: {e}')
    except FloodWaitError as e:
        log.warning(f'FloodWait (fallback) {getattr(e, "seconds", "?")}s')
        raise
    except Exception as e:
        log.debug(f'Fallback error: {e}')

    return False

# ------------------ Pending worker ------------------
async def process_pending(client):
    while True:
        if pending_comments:
            items = sorted(pending_comments.items(), key=lambda kv: kv[1]['ts'])
            for channel_msg_id, payload in items:
                try:
                    ok = await safe_comment(client, channel_msg_id)
                    if ok:
                        pending_comments.pop(channel_msg_id, None)
                        log.info(f'📤 Sent from queue -> {channel_msg_id}')
                except FloodWaitError as e:
                    wait = max(1, min(getattr(e, 'seconds', 10), 60))
                    log.warning(f'⏳ FloodWait in pending: sleeping {wait}s')
                    await asyncio.sleep(wait)
                except Exception as e:
                    log.debug(f'Pending retry failed for {channel_msg_id}: {e}')
        await asyncio.sleep(cfg.RETRY_INTERVAL)

# ------------------ Poller fallback ------------------
last_seen = None
async def poller_loop(client):
    global last_seen
    if ENTITIES['channel'] is None:
        log.error('Poller: channel entity missing')
        return
    while True:
        try:
            msgs = await client.get_messages(ENTITIES['channel'], limit=1)
            if msgs:
                m = msgs[0]
                if last_seen is None:
                    last_seen = m.id
                    log.debug(f'Poller init last_seen={last_seen}')
                elif m.id != last_seen:
                    # process missed posts
                    for uid in range(last_seen+1, m.id+1) if m.id > last_seen else [m.id]:
                        if uid in seen_ids:
                            continue
                        seen_ids.add(uid)
                        log.info(f'🔔 Poller detected new message {uid}')
                        try:
                            sent = await safe_comment(client, uid)
                            if not sent:
                                pending_comments[uid] = {'ts': time.time(), 'tries': 0}
                        except FloodWaitError as e:
                            pending_comments[uid] = {'ts': time.time(), 'tries': 0}
                            wait = max(1, min(getattr(e, 'seconds', 10), 60))
                            logger.warning(f'⏳ FloodWait (poller): sleeping {wait}s')
                            await asyncio.sleep(wait)
                        except Exception as e:
                            pending_comments[uid] = {'ts': time.time(), 'tries': 0}
                            log.exception(f'Poller handling error for {uid}: {e}')
                    last_seen = m.id
            await asyncio.sleep(cfg.POLL_INTERVAL)
        except Exception as e:
            log.exception(f'Poller exception: {e}')
            await asyncio.sleep(1.0)

# ------------------ Keep-alive ------------------
async def keep_alive(client):
    while True:
        try:
            await client.get_me()
            log.debug('Keep-alive OK')
        except FloodWaitError as e:
            wait = max(1, min(getattr(e, 'seconds', 10), 60))
            log.warning(f'Keep-alive FloodWait: sleeping {wait}s')
            await asyncio.sleep(wait)
        except Exception as e:
            log.debug(f'Keep-alive error: {e}')
        await asyncio.sleep(cfg.KEEP_ALIVE_INTERVAL)

# ------------------ Event handler ------------------
@events.register(events.NewMessage(chats=cfg.CHANNEL_USERNAME, incoming=True))
async def handler(event):
    msg = event.message
    channel_msg_id = msg.id
    if channel_msg_id in seen_ids:
        return
    seen_ids.add(channel_msg_id)
    try:
        sent = await safe_comment(client, channel_msg_id)
        if not sent:
            pending_comments[channel_msg_id] = {'ts': time.time(), 'tries': 0}
            log.info(f'⏳ Queued (event) for {channel_msg_id}')
    except FloodWaitError as e:
        pending_comments[channel_msg_id] = {'ts': time.time(), 'tries': 0}
        wait = max(1, min(getattr(e, 'seconds', 10), 60))
        log.warning(f'⏳ FloodWait (event): {wait}s -> queued')
        await asyncio.sleep(wait)
    except Exception as e:
        pending_comments[channel_msg_id] = {'ts': time.time(), 'tries': 0}
        log.exception(f'Event handler error for {channel_msg_id}: {e}')

# ------------------ Run ------------------
async def start_loop():
    global client
    client = create_client()
    await client.start(cfg.PHONE_NUMBER)
    log.info('Client started')
    await preload_entities(client)
    ok_clock, delta = check_system_clock()
    if not ok_clock:
        log.info('Clock check failed or delta large — poller fallback will run (safe).')
    # start background tasks
    asyncio.create_task(process_pending(client))
    asyncio.create_task(keep_alive(client))
    # Always start poller as redundancy
    asyncio.create_task(poller_loop(client))
    log.info('Bot is running and listening for new posts...')
    await client.run_until_disconnected()

def run():
    try:
        asyncio.run(start_loop())
    except KeyboardInterrupt:
        log.info('Stopped by user')
    except Exception as e:
        log.exception(f'Fatal error in run: {e}')
