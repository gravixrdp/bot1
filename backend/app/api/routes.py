from fastapi import APIRouter, Depends, HTTPException, Response, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from slowapi.util import get_remote_address
from slowapi import Limiter

from ..core.db import get_db
from ..core.redis_conn import redis
from ..core.config import settings
from ..models import Admin, User, Container, Build, Ticket, Message, AuditLog
from ..schemas import LoginRequest, AdminInfo, Stats, UserOut, ContainerOut, ActionRequest, BroadcastRequest, GrantRequest
from ..security.auth import verify_password, create_session, set_session_cookies, get_current_admin, require_csrf

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    # Only owner is supported
    res = await db.execute(select(Admin).where(Admin.username == payload.username))
    admin = res.scalar_one_or_none()
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    sid, csrf = await create_session(admin.username)
    set_session_cookies(response, sid, csrf)
    return {"ok": True}


@router.get("/auth/me", response_model=AdminInfo)
async def me(admin: Admin = Depends(get_current_admin)):
    return AdminInfo(username=admin.username, is_owner=admin.is_owner)


@router.post("/auth/logout")
async def logout(request: Request, response: Response):
    sid = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if sid:
        await redis.delete(f"sess:{sid}")
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/stats", response_model=Stats)
async def stats(_: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    premium_users = (await db.execute(select(func.count()).select_from(User).where(User.is_premium == True))).scalar() or 0
    active_containers = (await db.execute(select(func.count()).select_from(Container).where(Container.status == "running"))).scalar() or 0
    running_builds = (await db.execute(select(func.count()).select_from(Build).where(Build.status == "running"))).scalar() or 0

    # System metrics should arrive via Redis; provide placeholders
    sys = await redis.hgetall("gravix:metrics:host") or {}
    cpu = float(sys.get("cpu", 0.0))
    mem = float(sys.get("mem", 0.0))
    disk = float(sys.get("disk", 0.0))

    return Stats(
        total_users=total_users,
        premium_users=premium_users,
        active_containers=active_containers,
        running_builds=running_builds,
        cpu_percent=cpu,
        mem_percent=mem,
        disk_percent=disk,
    )


@router.get("/users")
async def list_users(_: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User))
    rows = res.scalars().all()
    # For MVP, compute active containers as 0; could subquery
    return [
        UserOut(
            id=u.id,
            username=u.username,
            email=u.email,
            is_premium=u.is_premium,
            premium_expires=u.premium_expires,
            created_at=u.created_at,
            active_containers=0,
        ).model_dump()
        for u in rows
    ]


@router.post("/users/{user_id}/grant")
async def grant_premium(user_id: int, body: GrantRequest, admin: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    from datetime import datetime, timedelta

    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    now = datetime.utcnow()
    if u.premium_expires and u.premium_expires > now:
        u.premium_expires = u.premium_expires + timedelta(days=body.days)
    else:
        u.premium_expires = now + timedelta(days=body.days)
    u.is_premium = True
    db.add(AuditLog(actor=admin.username, action="grant_premium", target_type="user", target_id=str(user_id)))
    await db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/revoke")
async def revoke_premium(user_id: int, admin: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.is_premium = False
    u.premium_expires = None
    db.add(AuditLog(actor=admin.username, action="revoke_premium", target_type="user", target_id=str(user_id)))
    await db.commit()
    return {"ok": True}


@router.get("/containers")
async def list_containers(_: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Container))
    rows = res.scalars().all()
    return [
        ContainerOut(
            id=c.id,
            user_id=c.user_id,
            name=c.name,
            status=c.status,
            host_port=c.host_port,
            image_tag=c.image_tag,
        ).model_dump()
        for c in rows
    ]


@router.post("/containers/{cid}/action")
async def container_action(cid: str, body: ActionRequest, admin: Admin = Depends(get_current_admin)):
    if body.action not in {"start", "stop", "restart", "delete"}:
        raise HTTPException(status_code=400, detail="Invalid action")
    await redis.publish(
        settings.MASTER_COMMANDS_CHANNEL,
        {
            "type": "container_action",
            "action": body.action,
            "container_id": cid,
            "actor": admin.username,
        },
    )
    return {"ok": True}


@router.get("/containers/{cid}/logs")
async def container_logs(cid: str, tail: int = 100, admin: Admin = Depends(get_current_admin)):
    # For MVP: ask master via Redis to dump last logs to a Redis key, then read it
    key = f"gravix:container:{cid}:logs:tail:{tail}"
    await redis.publish(
        settings.MASTER_COMMANDS_CHANNEL,
        {"type": "logs_request", "container_id": cid, "tail": tail},
    )
    # poll a few times
    for _ in range(10):
        data = await redis.get(key)
        if data:
            return {"logs": data}
    return {"logs": ""}


@router.get("/builds")
async def list_builds(_: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Build))
    rows = res.scalars().all()
    return [{"id": b.id, "app_id": b.app_id, "status": b.status, "created_at": b.created_at, "finished_at": b.finished_at} for b in rows]


@router.post("/broadcast")
async def broadcast(body: BroadcastRequest, admin: Admin = Depends(get_current_admin)):
    await redis.publish(
        settings.MASTER_COMMANDS_CHANNEL,
        {"type": "broadcast", "scope": body.scope, "message": body.message, "user_ids": body.user_ids or [], "actor": admin.username},
    )
    return {"ok": True}


@router.get("/support/tickets")
async def tickets(_: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Ticket))
    rows = res.scalars().all()
    return [{"id": t.id, "user_id": t.user_id, "status": t.status, "created_at": t.created_at} for t in rows]


@router.post("/support/tickets/{tid}/reply")
async def ticket_reply(tid: int, message: str, admin: Admin = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    t = await db.get(Ticket, tid)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    db.add(Message(ticket_id=tid, sender="admin", content=message))
    await db.commit()
    await redis.publish(settings.MASTER_COMMANDS_CHANNEL, {"type": "support_reply", "ticket_id": tid, "message": message})
    return {"ok": True}