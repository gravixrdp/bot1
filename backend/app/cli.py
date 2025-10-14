import asyncio
import os

from sqlalchemy.ext.asyncio import AsyncEngine

from .core.db import Base, engine, SessionLocal
from .models import Admin
from .security.auth import hash_password


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_admin(username: str, password: str):
    async with SessionLocal() as session:
        admin = Admin(username=username, password_hash=hash_password(password), is_owner=True)
        session.add(admin)
        await session.commit()
        print("Admin created:", username)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GRAVIX backend CLI")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("init-db")
    p = sub.add_parser("create-admin")
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)

    args = parser.parse_args()

    if args.cmd == "init-db":
        asyncio.run(init_db())
    elif args.cmd == "create-admin":
        asyncio.run(create_admin(args.username, args.password))
    else:
        parser.print_help()