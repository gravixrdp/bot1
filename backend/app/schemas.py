from datetime import datetime
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class AdminInfo(BaseModel):
    username: str
    is_owner: bool = True


class Stats(BaseModel):
    total_users: int
    premium_users: int
    active_containers: int
    running_builds: int
    cpu_percent: float
    mem_percent: float
    disk_percent: float


class UserOut(BaseModel):
    id: int
    username: str | None = None
    email: str | None = None
    is_premium: bool
    premium_expires: datetime | None = None
    created_at: datetime
    active_containers: int = 0


class ContainerOut(BaseModel):
    id: str
    user_id: int
    name: str
    status: str
    host_port: int | None = None
    image_tag: str | None = None


class ActionRequest(BaseModel):
    action: str  # start|stop|restart|delete


class BroadcastRequest(BaseModel):
    scope: str  # all|premium|user_ids
    message: str
    user_ids: list[int] | None = None


class GrantRequest(BaseModel):
    days: int = 30