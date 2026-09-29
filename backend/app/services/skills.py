"""技能包集成：上传/解压技能包、解析 SKILL.md 声明（含 CLI 工具），并在沙箱中执行。

技能包为 zip/tar.gz，内含 SKILL.md（YAML frontmatter 声明 name/description/tools，
正文作为系统提示词注入）与脚本资源。每个声明的工具以 ``skill__{name}__{tool}``
命名空间化，供请求内路由回对应技能与命令；命令以技能包目录为工作目录、读取
stdin JSON 参数执行（Docker 优先 + 软沙箱回退）。
"""

import asyncio
import json
import os
import shlex
import socket
import subprocess
import tarfile
import zipfile

import yaml

from app import models
from app.config import config

PREFIX = "skill__"


def _slug(name: str) -> str:
    out = []
    for ch in name or "":
        out.append(ch if (ch.isascii() and (ch.isalnum() or ch == "-")) else "_")
    return "".join(out).strip("_") or "skill"


def function_name(skill_name: str, tool_name: str) -> str:
    return f"{PREFIX}{_slug(skill_name)}__{_slug(tool_name)}"


def _safe_join(base: str, name: str) -> str:
    base = os.path.abspath(base)
    target = os.path.normpath(os.path.join(base, name))
    if not (target == base or target.startswith(base + os.sep)):
        raise ValueError(f"非法的压缩包路径：{name}")
    return target


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            try:
                data = yaml.safe_load(text[3:end].strip()) or {}
            except Exception:
                data = {}
            body = text[end + 4 :].strip()
            return (data if isinstance(data, dict) else {}), body
    return {}, text.strip()


def extract_upload(archive_path: str, target_dir: str) -> str:
    """解压 zip / tar.gz 到 target_dir，返回该目录；拒绝路径穿越。"""
    os.makedirs(target_dir, exist_ok=True)
    lower = archive_path.lower()
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as zf:
            for member in zf.infolist():
                if member.filename.startswith("/") or ".." in member.filename:
                    raise ValueError("非法的压缩包路径")
                target = _safe_join(target_dir, member.filename)
                if member.is_dir():
                    os.makedirs(target, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zf.open(member) as src, open(target, "wb") as dst:
                        dst.write(src.read())
    elif lower.endswith((".tar.gz", ".tgz")) or tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path, "r:*") as tf:
            for member in tf.getmembers():
                if member.name.startswith("/") or ".." in member.name:
                    raise ValueError("非法的压缩包路径")
                target = _safe_join(target_dir, member.name)
                if member.isfile():
                    f = tf.extractfile(member)
                    if f is None:
                        continue
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with open(target, "wb") as dst:
                        dst.write(f.read())
                elif member.isdir():
                    os.makedirs(target, exist_ok=True)
    elif lower.endswith(".zip"):
        raise ValueError("压缩包解压失败")
    else:
        raise ValueError("仅支持 zip / tar.gz 技能包")
    return target_dir


def _validate_command(cmd: str) -> None:
    if ".." in cmd:
        raise ValueError("工具命令不得包含 ..")
    for tok in shlex.split(cmd):
        if tok.startswith("/") or tok.startswith("\\"):
            raise ValueError("工具命令不得使用绝对路径")


def parse_skill(dir_path: str) -> dict:
    """解析技能包 SKILL.md，返回 {name, description, content, tools}。"""
    skill_md = os.path.join(dir_path, "SKILL.md")
    if not os.path.exists(skill_md):
        raise ValueError("技能包缺少 SKILL.md")
    with open(skill_md, "r", encoding="utf-8") as f:
        text = f.read()
    meta, body = _parse_frontmatter(text)
    name = (meta.get("name") or "").strip()
    if not name:
        raise ValueError("SKILL.md 缺少 name")
    tools: list[dict] = []
    for t in meta.get("tools") or []:
        if not isinstance(t, dict):
            continue
        tname = (t.get("name") or "").strip()
        cmd = (t.get("command") or "").strip()
        if not tname or not cmd:
            continue
        _validate_command(cmd)
        tools.append(
            {
                "name": tname,
                "description": (t.get("description") or "").strip(),
                "command": cmd,
                "input_schema": t.get("input_schema")
                or {"type": "object", "properties": {}},
            }
        )
    return {
        "name": name,
        "description": (meta.get("description") or "").strip(),
        "content": body,
        "tools": tools,
    }


def build_openai_tools(
    skills: list[models.Skill],
) -> tuple[list[dict], dict[str, tuple[models.Skill, dict]]]:
    openai_tools: list[dict] = []
    mapping: dict[str, tuple[models.Skill, dict]] = {}
    for skill in skills:
        try:
            tools = json.loads(skill.tools or "[]")
        except Exception:
            tools = []
        if not isinstance(tools, list):
            tools = []
        for t in tools:
            name = function_name(skill.name, t.get("name", ""))
            mapping[name] = (skill, t)
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": t.get("description") or "",
                        "parameters": t.get("input_schema")
                        or {"type": "object", "properties": {}},
                    },
                }
            )
    return openai_tools, mapping


def resolve_skills_by_ids(db, ids: list[int]) -> list[models.Skill]:
    if not ids:
        return []
    return (
        db.query(models.Skill)
        .filter(models.Skill.id.in_(ids), models.Skill.enabled == 1)
        .all()
    )


def user_skills(db, user_id: int) -> list[models.Skill]:
    """当前用户可用的技能：global 开启的 + 分配给该用户的（scope=user） + 所在组被授权的（scope=group）。"""
    access_ids = (
        db.query(models.SkillAccess.skill_id)
        .filter(models.SkillAccess.user_id == user_id)
        .scalar_subquery()
    )
    from app.services import groups as groups_core

    granted_ids = groups_core.accessible_ids(db, user_id, "skill")
    return (
        db.query(models.Skill)
        .filter(
            models.Skill.enabled == 1,
            (models.Skill.scope == "global")
            | (models.Skill.id.in_(access_ids))
            | (
                (models.Skill.scope == "group")
                & (models.Skill.id.in_([g for g in granted_ids]))
            ),
        )
        .all()
    )


def parse_ids(ids: str) -> list[int]:
    return [int(x) for x in (ids or "").split(",") if x.strip().isdigit()]


def _clean_env() -> dict:
    return {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
    }


def _format_result(rc: int, out: str, err: str) -> str:
    out = out or ""
    err = err or ""
    if rc == 0:
        return out.strip() or "（无输出）"
    return f"技能执行失败（退出码 {rc}）：\n{err or out}"


def _finish(proc: subprocess.CompletedProcess) -> str:
    return _format_result(proc.returncode, proc.stdout, proc.stderr)


def _run_docker(skill: models.Skill, command: str, args_json: str) -> str:
    """通过 Docker SDK（挂载 /var/run/docker.sock）执行技能工具。"""
    try:
        import docker
    except ImportError as e:
        raise RuntimeError(f"docker SDK 不可用：{e}")
    try:
        client = docker.from_env()
    except Exception as e:
        raise RuntimeError(f"docker 守护进程不可达：{e}")
    upload_dir = os.path.abspath(config.upload_dir)
    rel = os.path.relpath(os.path.abspath(skill.dir_path), upload_dir)
    workdir = f"{config.skill_data_mount.rstrip('/')}/{rel.replace(os.sep, '/')}"
    try:
        container = client.containers.create(
            config.skill_runner_image,
            command=["sh", "-c", command],
            working_dir=workdir,
            volumes={
                config.skill_data_volume: {
                    "bind": config.skill_data_mount,
                    "mode": "ro",
                }
            },
            nano_cpus=int(float(config.skill_cpus) * 1_000_000_000),
            mem_limit=config.skill_memory,
            pids_limit=config.skill_pids_limit,
            stdin_open=True,
            detach=True,
        )
    except Exception as e:
        raise RuntimeError(f"docker 容器创建失败：{e}")
    try:
        container.start()
        try:
            sock = client.api.attach_socket(
                container.id,
                params={"stdin": 1, "stdout": 0, "stderr": 0, "stream": 1},
            )
            sock.sendall(args_json.encode("utf-8"))
            sock.shutdown(socket.SHUT_WR)
            sock.close()
        except Exception:
            pass
        try:
            res = container.wait(timeout=config.skill_timeout)
            rc = int(res.get("StatusCode") or 0)
        except Exception:
            container.remove(force=True)
            return f"技能执行超时（>{config.skill_timeout}s）"
        out = (container.logs(stdout=True, stderr=False) or b"").decode(
            "utf-8", "replace"
        )
        err = (container.logs(stdout=False, stderr=True) or b"").decode(
            "utf-8", "replace"
        )
    finally:
        try:
            container.remove(force=True)
        except Exception:
            pass
    return _format_result(rc, out, err)


def _run_local(skill: models.Skill, command: str, args_json: str) -> str:
    def _limits() -> None:
        try:
            import resource

            resource.setrlimit(
                resource.RLIMIT_CPU, (config.skill_timeout, config.skill_timeout)
            )
        except Exception:
            pass

    try:
        kwargs: dict = {
            "shell": True,
            "cwd": skill.dir_path,
            "input": args_json,
            "capture_output": True,
            "text": True,
            "timeout": config.skill_timeout,
            "env": _clean_env(),
        }
        if os.name != "nt":
            kwargs["preexec_fn"] = _limits
        proc = subprocess.run(command, **kwargs)
    except subprocess.TimeoutExpired:
        return f"技能执行超时（>{config.skill_timeout}s）"
    return _finish(proc)


async def call_tool(skill: models.Skill, tool: dict, args: dict) -> str:
    """调用技能工具，stdout 为结果；Docker 优先 + 软沙箱回退。"""
    command = tool.get("command") or ""
    if not command:
        return "技能未配置命令。"
    args_json = json.dumps(args, ensure_ascii=False)
    sandbox = (config.skill_sandbox or "auto").lower()
    if sandbox == "local":
        return await asyncio.to_thread(_run_local, skill, command, args_json)
    try:
        return await asyncio.to_thread(_run_docker, skill, command, args_json)
    except Exception:
        if sandbox == "docker":
            raise
        return await asyncio.to_thread(_run_local, skill, command, args_json)
