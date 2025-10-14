import os
import shutil
import subprocess
import sys
import signal
from typing import Optional, Tuple, List

from docker import from_env as docker_from_env, errors as docker_errors

from ..config import UPLOADS_DIR, RUNTIME_CPU_LIMIT, RUNTIME_MEM_LIMIT, RUNTIME_NETWORK
from ..storage import log_event


# Map common import names to their PyPI package equivalents
# This helps when users write code like "import telebot" but the pip package is "pyTelegramBotAPI"
_PYPI_MAP = {
    "telebot": "pyTelegramBotAPI",
    "PIL": "pillow",
    "cv2": "opencv-python",
    "dotenv": "python-dotenv",
    "bs4": "beautifulsoup4",
    "yaml": "pyyaml",
    "Crypto": "pycryptodome",
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
    # If zip, extract
    if file_name.lower().endswith(".zip"):
        import zipfile
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(path)
        os.remove(file_path)
    return path


def _normalize_requirement(name: str) -> Optional[str]:
    """
    Normalize an import/module name or raw requirement line to a PyPI-installable requirement.
    - Maps common import names to their actual PyPI package
    - Filters obviously invalid placeholders (e.g., '%(module)s')
    """
    if not name:
        return None
    s = name.strip()
    if not s or s.startswith("#"):
        return None
    # Skip obvious placeholders from mis-templated requirements
    if "%(" in s and ")s" in s:
        return None
    # If the line looks like a valid pinned requirement (contains space is suspicious)
    if " " in s:
        # Spaces in requirement lines are usually invalid, skip them
        return None
    # If it's already a requirement spec (contains ==, >=, etc.) keep it
    for sep in ("==", ">=", "<=", "~=", ">", "<", "!="):
        if sep in s:
            return s
    # Otherwise treat as a module/import name and map if needed
    base = s.split(".")[0]
    return _PYPI_MAP.get(base, base)


def detect_requirements(workspace: str) -> List[str]:
    reqs = set()
    # If requirements.txt exists, use it
    req_path = os.path.join(workspace, "requirements.txt")
    if os.path.exists(req_path):
        try:
            with open(req_path, "r") as f:
                for line in f:
                    norm = _normalize_requirement(line)
                    if norm:
                        reqs.add(norm)
        except Exception:
            pass

    # Parse .py files for imports
    def parse_imports(py_path: str):
        try:
            with open(py_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("import ") or line.startswith("from "):
                        parts = line.replace("import ", " ").replace("from ", " ").split()
                        if parts:
                            mod = parts[0].split(".")[0]
                            # Skip stdlib/common
                            skip = {"os", "sys", "asyncio", "typing", "time", "json", "re", "dataclasses", "datetime"}
                            if mod and mod not in skip:
                                norm = _normalize_requirement(mod)
                                if norm:
                                    reqs.add(norm)
        except Exception:
            pass

    for root, _, files in os.walk(workspace):
        for f in files:
            if f.endswith(".py"):
                parse_imports(os.path.join(root, f))

    return sorted(reqs)


def write_runner_and_dockerfile(workspace: str, entry: Optional[str] = None, requirements: Optional[List[str]] = None):
    # Runner executes the detected entry file; token is passed via TELEGRAM_TOKEN env var
    entry_file = entry or "bot.py"
    runner = os.path.join(workspace, "gravix_runner.sh")
    with open(runner, "w") as f:
        f.write("#!/usr/bin/env bash\n")
        f.write("set -e\n")
        f.write("python " + entry_file + "\n")
    os.chmod(runner, 0o755)

    dockerfile = os.path.join(workspace, "Dockerfile")
    with open(dockerfile, "w") as f:
        f.write("FROM python:3.11-slim\n")
        f.write("WORKDIR /app\n")
        f.write("COPY . /app\n")
        f.write("RUN pip install --no-cache-dir --upgrade pip\n")
        # Always try to install user-provided requirements, but don't fail the build if they contain invalid lines
        f.write("RUN if [ -f requirements.txt ]; then pip install -r requirements.txt || true; fi\n")
        if requirements:
            # write normalized autodetected requirements
            req_path = os.path.join(workspace, "requirements.autodetected.txt")
            with open(req_path, "w") as rf:
                rf.write("\n".join(requirements))
            f.write("RUN pip install -r requirements.autodetected.txt || true\n")
        f.write("ENV PYTHONUNBUFFERED=1\n")
        f.write("CMD [\"/app/gravix_runner.sh\"]\n")


def _docker_available() -> bool:
    try:
        client = docker_from_env()
        # will raise if docker not reachable
        client.ping()
        return True
    except Exception:
        return False


def _run_locally(workspace: str, entry: Optional[str], token: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Fallback runner when Docker isn't available.
    Creates a venv inside the workspace, installs requirements, and starts the bot.
    Returns (ok, runtime_id, err). runtime_id is in form 'proc:<pid>'
    """
    entry_file = entry or "bot.py"
    venv_dir = os.path.join(workspace, ".venv")
    python_bin = os.path.join(venv_dir, "bin", "python")
    pip_bin = os.path.join(venv_dir, "bin", "pip")

    try:
        # Create virtual environment
        if not os.path.exists(python_bin):
            subprocess.check_call([sys.executable, "-m", "venv", venv_dir])

        # Install requirements if present (don't abort on errors)
        req_file = os.path.join(workspace, "requirements.txt")
        if os.path.exists(req_file):
            try:
                subprocess.check_call([pip_bin, "install", "-r", req_file])
            except Exception as e:
                log_event(f"Requirements installation failed: {e}. Continuing with autodetected packages.")

        # Best-effort: install autodetected requirements (normalized)
        autodetected = detect_requirements(workspace)
        if autodetected:
            try:
                subprocess.check_call([pip_bin, "install", *autodetected])
            except Exception as e:
                log_event(f"Autodetected requirements installation failed: {e}. Continuing without them.")

        env = os.environ.copy()
        env["TELEGRAM_TOKEN"] = token
        # Start the process detached
        proc = subprocess.Popen([python_bin, entry_file], cwd=workspace, env=env)
        log_event(f"Local runtime started pid={proc.pid}")
        return True, f"proc:{proc.pid}", None
    except Exception as e:
        return False, None, str(e)


def build_and_run(user_id: int, bot_id: str, token: str, workspace: str, entry: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
    image_tag = f"gravixhost_{user_id}_{bot_id}".lower()
    # Try Docker path first
    if _docker_available():
        client = docker_from_env()
        try:
            requirements = detect_requirements(workspace)
            write_runner_and_dockerfile(workspace, entry=entry, requirements=requirements)
            # Build
            log_event(f"Building runtime for {bot_id}")
            client.images.build(path=workspace, tag=image_tag, rm=True)
            # Run with resource limits
            env = {"TELEGRAM_TOKEN": token}
            host_cfg = client.api.create_host_config(
                nano_cpus=int(float(RUNTIME_CPU_LIMIT) * 1e9),
                mem_limit=RUNTIME_MEM_LIMIT,
                auto_remove=True,
                restart_policy={"Name": "unless-stopped"}
            )
            create_kwargs = {
                "image": image_tag,
                "name": image_tag,
                "environment": env,
                "host_config": host_cfg,
            }
            if RUNTIME_NETWORK:
                create_kwargs["network"] = RUNTIME_NETWORK
            container = client.api.create_container(**create_kwargs)
            client.api.start(container=container.get("Id"))
            runtime_id = container.get("Id")
            log_event(f"Runtime started {runtime_id} for {bot_id}")
            return True, runtime_id, None
        except docker_errors.BuildError:
            return False, None, "build_error"
        except Exception as e:
            # Fall back to local if the daemon becomes unavailable mid-way
            log_event(f"Docker path failed: {e}. Falling back to local runner.")
            return _run_locally(workspace, entry, token)
    else:
        # No Docker available
        log_event("Docker not available. Using local runner.")
        return _run_locally(workspace, entry, token)


def stop_runtime(runtime_id: str) -> bool:
    try:
        if runtime_id.startswith("proc:"):
            pid = int(runtime_id.split(":", 1)[1])
            os.kill(pid, signal.SIGTERM)
            return True
        # Docker container id
        client = docker_from_env()
        client.api.stop(runtime_id)
        return True
    except Exception:
        return False


def restart_runtime(runtime_id: str) -> bool:
    try:
        if runtime_id.startswith("proc:"):
            # Not supported for local process
            return False
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