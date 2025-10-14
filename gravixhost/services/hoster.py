import os
import shutil
from typing import Optional, Tuple, List

from docker import from_env as docker_from_env, errors as docker_errors

from ..config import UPLOADS_DIR, RUNTIME_CPU_LIMIT, RUNTIME_MEM_LIMIT, RUNTIME_NETWORK
from ..storage import log_event


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


def detect_requirements(workspace: str) -> List[str]:
    reqs = set()
    # If requirements.txt exists, use it
    req_path = os.path.join(workspace, "requirements.txt")
    if os.path.exists(req_path):
        try:
            with open(req_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        reqs.add(line)
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
                                reqs.add(mod)
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
        if requirements:
            # write requirements.txt
            req_path = os.path.join(workspace, "requirements.autodetected.txt")
            with open(req_path, "w") as rf:
                rf.write("\n".join(requirements))
            f.write("RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi\n")
            f.write("RUN pip install -r requirements.autodetected.txt || true\n")
        else:
            f.write("RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi\n")
        f.write("ENV PYTHONUNBUFFERED=1\n")
        f.write("CMD [\"/app/gravix_runner.sh\"]\n")


def build_and_run(user_id: int, bot_id: str, token: str, workspace: str, entry: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
    client = docker_from_env()
    image_tag = f"gravixhost_{user_id}_{bot_id}".lower()
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
        return False, None, str(e)


def stop_runtime(runtime_id: str) -> bool:
    try:
        client = docker_from_env()
        client.api.stop(runtime_id)
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