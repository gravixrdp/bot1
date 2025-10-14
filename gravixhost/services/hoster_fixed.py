import os
import shutil
import subprocess
import sys
import signal
import ast
import re
import tempfile
import time
from typing import Optional, Tuple, List

from docker import from_env as docker_from_env, errors as docker_errors

from ..config import UPLOADS_DIR, RUNTIME_NETWORK
from ..storage import log_event, get_settings

# Defaults aligned with requested hosting flow
DEFAULT_BASE_IMAGE = "python:3.11-slim"
AIOGRAM_V2_IMAGE = "python:3.9-slim"
DEFAULT_CPU_QUOTA = 100000           # 100% CPU
DEFAULT_MEM_LIMIT = "512m"
DEFAULT_PIDS_LIMIT = 100
BUILD_TIMEOUT_SECS = 300


_PYPI_MAP = {
    "telebot": "pyTelegramBotAPI",
    "telegram": "python-telegram-bot",
    "PIL": "pillow",
    "cv2": "opencv-python",
    "dotenv": "python-dotenv",
    "bs4": "beautifulsoup4",
    "yaml": "pyyaml",
    "Crypto": "pycryptodome",
    "OpenSSL": "pyOpenSSL",
    "configparser": "configparser",
    "ConfigParser": None,
    "HTMLParser": None,
    "Queue": None,
    "StringIO": None,
}

_BLACKLIST = {
    "__builtin__", "builtins", "__future__", "typing", "dataclasses", "asyncio",
    "sys", "os", "json", "re", "time", "datetime", "pathlib", "subprocess", "logging",
    "itertools", "functools", "collections", "math", "random", "hashlib", "hmac",
    "base64", "threading", "multiprocessing", "urllib", "http", "email", "sqlite3",
    "csv", "statistics", "enum", "types", "contextlib", "tempfile", "zipfile",
    "tarfile", "shutil", "glob", "fnmatch", "importlib", "inspect", "traceback",
    "argparse", "getopt", "site", "io", "pickle", "socket", "select",
    "ssl", "struct", "decimal", "fractions", "numbers",
    "abc", "array", "atexit", "binascii", "bisect", "bz2", "calendar", "cgi",
    "codecs", "colorsys", "compileall", "concurrent", "ctypes", "difflib",
    "distutils", "doctest", "errno", "faulthandler", "filecmp", "fileinput",
    "gc", "getpass", "gettext", "gzip", "heapq", "html", "html.parser",
    "http.client", "http.server", "imaplib", "ipaddress", "keyword", "linecache",
    "locale", "logging", "lzma", "mailbox", "mailcap", "marshal", "mimetypes",
    "mmap", "msvcrt", "netrc", "nis", "nntplib", "ntpath", "operator", "optparse",
    "os.path", "plistlib", "platform", "poplib", "posix", "pprint", "pty", "pwd",
    "py_compile", "queue", "quopri", "reprlib", "resource", "sched", "secrets",
    "selectors", "shelve", "shlex", "signal", "smtpd", "smtplib", "sndhdr",
    "socketserver", "sqlite3", "stat", "string", "stringprep",
    "sunau", "symtable", "sysconfig", "tabnanny", "telnetlib",
    "textwrap", "timeit", "tkinter", "token", "tokenize", "trace",
    "tracemalloc", "turtle", "types", "unicodedata", "unittest", "urllib",
    "uuid", "venv", "warnings", "wave", "weakref", "webbrowser", "xml", "xmlrpc",
    "zipapp", "zipfile", "zoneinfo",
}


def ensure_user_dir(user_id: int) -> str:
    path = os.path.join(UPLOADS_DIR, str(user_id))
    os.makedirs(path, exist_ok=True)
    return path


def new_bot_workspace(user_id: int, bot_id: str) -> str:
    base = ensure_user_dir(user_id)
    path = os.path.join(base, bot_id)
    os.makedirs(path, exist_ok=True)
    return path


def save_upload(user_id: int, bot_id: str, file_name: str, content: bytes) -> str:
    path = new_bot_workspace(user_id, bot_id)
    file_path = os.path.join(path, file_name)
    with open(file_path, "wb") as f:
        f.write(content)
    if file_name.lower().endswith(".zip"):
        import zipfile
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(path)
        os.remove(file_path)
    return path


def detect_framework(code: str) -> Tuple[str, str]:
    framework, token_var = "unknown", "TOKEN"
    try:
        tree = ast.parse(code)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        if "aiogram" in imports:
            framework = "aiogram_v2" if "executor.start_polling" in code else "aiogram_v3"
        elif "telebot" in imports:
            framework = "pytelegrambotapi"
        elif "telegram" in imports:
            framework = "python-telegram-bot"
        elif "pyrogram" in imports:
            framework = "pyrogram"
    except Exception:
        pass

    for pattern in [
        r'([a-zA-Z_]\w*)\s*=\s*["\']([0-9]+:[a-zA-Z0-9_-]+)["\']',
        r'([a-zA-Z_]\w*)\s*=\s*os\.getenv',
    ]:
        m = re.search(pattern, code)
        if m:
            token_var = m.group(1)
            break
    return framework, token_var


def guess_requirements(framework: str) -> List[str]:
    fmap = {
        "aiogram_v2": "aiogram<3.0",
        "aiogram_v3": "aiogram>=3.0",
        "pytelegrambotapi": "pyTelegramBotAPI",
        "python-telegram-bot": "python-telegram-bot",
        "pyrogram": "pyrogram",
    }
    return [fmap[framework]] if framework in fmap else []


def _docker_available() -> bool:
    try:
        client = docker_from_env()
        client.ping()
        return True
    except Exception:
        return False


def build_and_run(user_id: int, bot_id: str, token: str, workspace: str, entry: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
    if not _docker_available():
        log_event("Docker not available. Aborting deployment.")
        return False, None, "docker_unavailable"

    # Read bot code
    code = None
    entry_file = entry
    try:
        if not entry_file:
            candidate = os.path.join(workspace, "bot.py")
            if os.path.exists(candidate):
                entry_file = "bot.py"
            else:
                for f in os.listdir(workspace):
                    if f.endswith(".py"):
                        entry_file = f
                        break
        if entry_file:
            with open(os.path.join(workspace, entry_file), "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
    except Exception:
        code = None

    if not code:
        return False, None, "no_entry_py"

    framework, token_var = detect_framework(code)
    reqs = guess_requirements(framework)

    temp_dir = None
    client = docker_from_env()
    try:
        temp_dir = tempfile.mkdtemp()
        # Write code
        with open(os.path.join(temp_dir, "bot.py"), "w", encoding="utf-8") as f:
            f.write(code)
        # Write requirements
        with open(os.path.join(temp_dir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(reqs) if reqs else "")

        # Smart runner that injects env token and patches frameworks
        runner_code = """import os, runpy, sys, subprocess, threading, time, re

def _get_env_token():
    t = os.getenv('TELEGRAM_TOKEN') or os.getenv('BOT_TOKEN') or os.getenv('TOKEN') or ''
    t = str(t).strip().strip("'\\\"").strip()
    return t

def _is_valid_token(t):
    return bool(re.match(r'^\\d+:[A-Za-z0-9_-]+$', (t or '').strip()))

token = _get_env_token()
os.environ['BOT_TOKEN'] = token
os.environ['TELEGRAM_TOKEN'] = token
os.environ['TOKEN'] = token
os.environ['TELEGRAM_BOT_TOKEN'] = token
init_globals = {'BOT_TOKEN': token, 'TOKEN': token, 'TELEGRAM_TOKEN': token}
os.chdir(os.path.dirname(__file__))

def _patch_telebot():
    try:
        import telebot, re as _re
        class _PatchedTeleBot(telebot.TeleBot):
            def __init__(self, tok, *args, **kwargs):
                t = tok or ''
                if ':' not in t or not _re.match(r'^\\d+:[A-Za-z0-9_-]+$', t):
                    env_t = _get_env_token()
                    if env_t:
                        t = env_t
                super().__init__(t, *args, **kwargs)
        telebot.TeleBot = _PatchedTeleBot
    except Exception:
        pass

def _patch_aiogram():
    try:
        import aiogram
        if hasattr(aiogram, 'Bot'):
            class _PatchedAioBot(aiogram.Bot):
                def __init__(self, tok, *args, **kwargs):
                    t = tok or ''
                    if not _is_valid_token(t):
                        env_t = _get_env_token()
                        if env_t:
                            t = env_t
                    super().__init__(t, *args, **kwargs)
            aiogram.Bot = _PatchedAioBot
    except Exception:
        pass
    try:
        from aiogram import Bot as _BotV2
        class _PatchedAioBot2(_BotV2):
            def __init__(self, tok, *args, **kwargs):
                t = tok or ''
                if not _is_valid_token(t):
                    env_t = _get_env_token()
                    if env_t:
                        t = env_t
                super().__init__(t, *args, **kwargs)
    except Exception:
        pass

def _patch_ptb():
    try:
        import telegram
        class _PatchedPTBBot(telegram.Bot):
            def __init__(self, tok, *args, **kwargs):
                t = tok or ''
                if not _is_valid_token(t):
                    env_t = _get_env_token()
                    if env_t:
                        t = env_t
                super().__init__(t, *args, **kwargs)
        telegram.Bot = _PatchedPTBBot
    except Exception:
        pass

def _patch_pyrogram():
    try:
        import pyrogram
        class _PatchedClient(pyrogram.Client):
            def __init__(self, name, *args, **kwargs):
                bt = kwargs.get('bot_token') or ''
                if not _is_valid_token(bt):
                    env_t = _get_env_token()
                    if env_t:
                        kwargs['bot_token'] = env_t
                super().__init__(name, *args, **kwargs)
        pyrogram.Client = _PatchedClient
    except Exception:
        pass

_patch_telebot()
_patch_aiogram()
_patch_ptb()
_patch_pyrogram()

def _heartbeat():
    while True:
        try:
            print('gravix_runner: heartbeat alive')
        except Exception:
            pass
        time.sleep(30)
threading.Thread(target=_heartbeat, daemon=True).start()

print('gravix_runner: entry=bot.py token_len=%d' % (len(token)))
def _try_run():
    runpy.run_path('bot.py', init_globals=init_globals)

try:
    _try_run()
except ModuleNotFoundError as e:
    missing = getattr(e, 'name', None)
    if not missing and 'No module named' in str(e):
        m = re.search(r"No module named ['\\\"]([^'\\\"]+)['\\\"]", str(e))
        if m:
            missing = m.group(1)
    _MAP = {
        'telebot': 'pyTelegramBotAPI',
        'telegram': 'python-telegram-bot',
        'PIL': 'pillow',
        'cv2': 'opencv-python',
        'bs4': 'beautifulsoup4',
        'yaml': 'pyyaml',
        'Crypto': 'pycryptodome',
        'OpenSSL': 'pyOpenSSL',
    }
    pkg = _MAP.get(missing)
    if pkg:
        print('gravix_runner: auto-installing %s for missing module %s' % (pkg, missing))
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg])
            _try_run()
        except Exception:
            import traceback; traceback.print_exc(); sys.exit(1)
    else:
        raise
except SystemExit:
    raise
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""
        with open(os.path.join(temp_dir, "gravix_runner.py"), "w", encoding="utf-8") as f:
            f.write(runner_code)

        base_img = AIOGRAM_V2_IMAGE if framework == "aiogram_v2" else DEFAULT_BASE_IMAGE
        dockerfile = (
            f"FROM {base_img}\n"
            "WORKDIR /app\n"
            "COPY requirements.txt .\n"
            "RUN pip install --no-cache-dir -r requirements.txt\n"
            "COPY bot.py .\n"
            "COPY gravix_runner.py .\n"
            f"ENV TELEGRAM_TOKEN={token}\n"
            f"ENV TOKEN={token}\n"
            f"ENV BOT_TOKEN={token}\n"
            f"ENV {token_var}={token}\n"
            'CMD ["python","/app/gravix_runner.py"]\n'
        )
        with open(os.path.join(temp_dir, "Dockerfile"), "w", encoding="utf-8") as f:
            f.write(dockerfile)

        image_tag = f"hostbot_{user_id}_{bot_id}_{int(time.time())}".lower().replace(" ", "_").replace("-", "_")
        container_name = f"hostbot_{user_id}_{bot_id}_{int(time.time())}".lower().replace(" ", "_").replace("-", "_")

        log_event(f"Building image {image_tag} for {bot_id}")
        client.images.build(path=temp_dir, tag=image_tag, rm=True, timeout=BUILD_TIMEOUT_SECS)

        network = RUNTIME_NETWORK
        if network:
            try:
                nets = client.networks.list(names=[network])
                if not nets:
                    client.networks.create(name=network)
                    log_event(f"Created missing Docker network: {network}")
            except Exception:
                log_event(f"Could not verify/create network '{network}', proceeding with defaults.")
                network = None

        container = client.containers.run(
            image_tag,
            name=container_name,
            detach=True,
            cpu_quota=DEFAULT_CPU_QUOTA,
            mem_limit=DEFAULT_MEM_LIMIT,
            pids_limit=DEFAULT_PIDS_LIMIT,
            network=network if network else None,
            restart_policy={"Name": "unless-stopped"},
        )

        runtime_id = container.id
        log_event(f"Runtime started {runtime_id} for {bot_id} (framework={framework})")
        return True, runtime_id, None
    except docker_errors.BuildError:
        return False, None, "build_error"
    except Exception as e:
        log_event(f"Build/run failed for {bot_id}: {e}")
        return False, None, str(e)
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


def stop_runtime(runtime_id: str) -> bool:
    try:
        client = docker_from_env()
        try:
            client.api.stop(runtime_id, timeout=10)
        except Exception:
            pass
        try:
            client.api.remove_container(runtime_id, force=True)
        except Exception:
            pass
        return True
    except Exception:
        return False


def restart_runtime(runtime_id: str) -> bool:
    try:
        client = docker_from_env()
        client.api.restart(runtime_id)
        return True
    except Exception:
        return False


def remove_image(image_tag: str) -> bool:
    try:
        client = docker_from_env()
        client.images.remove(image=image_tag, force=True)
        return True
    except Exception:
        return False


def remove_workspace(workspace: str):
    try:
        shutil.rmtree(workspace, ignore_errors=True)
    except Exception:
        pass


def get_runtime_logs(runtime_id: str, tail: int = 200) -> Optional[str]:
    try:
        client = docker_from_env()
        logs = client.api.logs(runtime_id, tail=tail, stdout=True, stderr=True)
        if isinstance(logs, (bytes, bytearray)):
            try:
                return logs.decode("utf-8", errors="replace")
            except Exception:
                return logs.decode("latin1", errors="replace")
        return str(logs)
    except Exception:
        return None