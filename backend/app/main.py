import asyncio
import json
from typing import Any

import orjson
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .core.config import settings
from .core.redis_conn import redis
from .security.auth import get_current_admin
from .api.routes import router as api_router

limiter = Limiter(key_func=lambda request: request.client.host if request.client else "unknown")


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting on login
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # API
    app.include_router(api_router, prefix=settings.API_PREFIX)

    @app.websocket("/ws/admin")
    async def admin_ws(ws: WebSocket):
        # Cookie-based auth: ensure session exists
        await ws.accept()
        cookies = {k.strip(): v for k, v in [c.split("=") for c in (ws.headers.get("cookie") or "").split(";") if "=" in c]}
        sid = cookies.get(settings.SESSION_COOKIE_NAME)
        if not sid:
            await ws.close(code=4401)
            return
        data = await redis.hgetall(f"sess:{sid}")
        if not data:
            await ws.close(code=4401)
            return

        # Subscribe to Redis pubsub
        pubsub = redis.pubsub()
        await pubsub.subscribe(*settings.REDIS_EVENTS_CHANNELS)

        try:
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=10.0)
                if msg and msg["type"] == "message":
                    payload = msg["data"]
                    # If data is dict-like string, pass as-is
                    if isinstance(payload, (bytes, bytearray)):
                        try:
                            payload = payload.decode("utf-8")
                        except Exception:
                            payload = ""
                    await ws.send_text(payload)
                else:
                    # keepalive ping
                    if ws.client_state == WebSocketState.CONNECTED:
                        await ws.send_text(json.dumps({"type": "ping"}))
                await asyncio.sleep(0.5)
        except WebSocketDisconnect:
            pass
        finally:
            try:
                await pubsub.unsubscribe(*settings.REDIS_EVENTS_CHANNELS)
                await pubsub.close()
            except Exception:
                pass

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    return app


app = create_app()