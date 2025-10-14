import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Master bot token and admin ID are expected as environment variables for security.
MASTER_BOT_TOKEN = os.getenv("MASTER_BOT_TOKEN", "").strip()


def _parse_admin_ids(raw: str):
    ids = set()
    for part in (raw or "").replace(";", ",").split(","):
        p = part.strip().strip("'\"")
        if not p:
            continue
        try:
            # Support negative IDs too
            ids.add(int(p))
        except Exception:
            # Try to extract leading sign and digits
            import re
            m = re.match(r"^(-?\\d+)", p)
            if m:
                try:
                    ids.add(int(m.group(1)))
                except Exception:
                    pass
    return ids


ADMIN_TELEGRAM_IDS = _parse_admin_ids(os.getenv("ADMIN_TELEGRAM_ID", "0"))
# Backward-compat single admin id
ADMIN_TELEGRAM_ID = next(iter(ADMIN_TELEGRAM_IDS), 0)

# Free plan hosting duration
FREE_PLAN_DURATION = timedelta(hours=1)

# Filesystem paths
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
DB_PATH = os.path.join(DATA_DIR, "db.json")
LOGS_PATH = os.path.join(DATA_DIR, "logs.txt")

# Runtime controls (internal)
RUNTIME_CPU_LIMIT = os.getenv("RUNTIME_CPU_LIMIT", "0.5")  # CPU shares
RUNTIME_MEM_LIMIT = os.getenv("RUNTIME_MEM_LIMIT", "256m")  # Memory limit
RUNTIME_NETWORK = os.getenv("RUNTIME_NETWORK", None)  # Optional network name

# Misc
APP_NAME = "GRAVIXHOST"