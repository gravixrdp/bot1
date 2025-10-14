import asyncio
import json
from typing import Any, Dict

from redis.asyncio import Redis
from .bus import REDIS_URL, set_key
from .hoster import stop_runtime, restart_runtime, get_runtime_logs  # integrate with your helpers


async def handle_message(msg: Dict[str, Any]):
    t = msg.get("type")
    if t == "container_action":
        action = msg.get("action")
        cid = msg.get("container_id")
        if not cid:
            return
        try:
            if action == "stop":
                stop_runtime(cid)
            elif action == "restart":
                restart_runtime(cid)
            elif action == "delete":
                # Stop + remove is handled in dashboard or storage; implement as needed
                stop_runtime(cid)
        except Exception:
            pass

    elif t == "logs_request":
        cid = msg.get("container_id")
        tail = int(msg.get("tail") or 100)
        if not cid:
            return
        key = f"gravix:container:{cid}:logs:tail:{tail}"
        logs = ""
        try:
            logs = await asyncio.to_thread(get_runtime_logs, cid, tail) or ""
        except Exception:
            logs = ""
        await set_key(key, logs, ttl=20)

    elif t == "broadcast":
        # Implement: master bot should deliver messages to users (aiogram send_message)
        # Scope could be all|premium|user_ids; integrate with storage.py as desired.
        pass

    elif t == "support_reply":
        # Implement: reply to user from ticket; integrate with your storage for mapping ticket->user
        pass


async def command_consumer():
    r = Redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("gravix:commands")
    try:
        async for m in pubsub.listen():
            if m and m.get("type") == "message":
                raw = m.get("data")
                try:
                    payload = json.loads(raw)
                except Exception:
                    payload = {}
                await handle_message(payload)
    finally:
        await pubsub.close()