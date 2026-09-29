import asyncio
import io
import json
import zipfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.controllers.admin as admin_mod
import app.controllers.frontend.chat as chat_mod
import app.controllers.frontend.conversations as conversations_mod
import app.services.skills as skill_core
from app import models, schemas
from app.database import Base
from app.config import config


def _db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


SKILL_MD = """---
name: 代码检查
description: 对代码做静态检查
tools:
  - name: run_lint
    description: 运行 lint
    command: python tools/lint.py
---
请对代码做静态检查，发现有问题的行给出建议。
"""


# ---------- 解析 ----------


def test_parse_skill(tmp_path):
    d = tmp_path / "pkg"
    d.mkdir()
    (d / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
    (d / "tools").mkdir()
    (d / "tools" / "lint.py").write_text("print('x')", encoding="utf-8")
    info = skill_core.parse_skill(str(d))
    assert info["name"] == "代码检查"
    assert "静态检查" in info["description"]
    assert len(info["tools"]) == 1
    assert info["tools"][0]["name"] == "run_lint"
    assert info["tools"][0]["command"] == "python tools/lint.py"
    assert "请对代码做静态检查" in info["content"]


def test_parse_skill_missing_name(tmp_path):
    d = tmp_path / "pkg"
    d.mkdir()
    (d / "SKILL.md").write_text("---\ndescription: x\n---\nbody", encoding="utf-8")
    with pytest.raises(ValueError):
        skill_core.parse_skill(str(d))


# ---------- 解压 ----------


def test_extract_upload_zip(tmp_path):
    z = tmp_path / "pkg.zip"
    z.write_bytes(_make_zip({"SKILL.md": "x", "tools/lint.py": "print(1)"}))
    out = tmp_path / "out"
    skill_core.extract_upload(str(z), str(out))
    assert (out / "SKILL.md").exists()
    assert (out / "tools" / "lint.py").exists()


def test_extract_upload_rejects_zip_slip(tmp_path):
    z = tmp_path / "evil.zip"
    z.write_bytes(_make_zip({"../evil.txt": "bad"}))
    out = tmp_path / "out"
    with pytest.raises(ValueError):
        skill_core.extract_upload(str(z), str(out))


# ---------- 工具 schema 转换 ----------


def test_build_openai_tools_namespacing():
    skill = models.Skill(
        id=1,
        name="lint",
        description="desc",
        tools=json.dumps(
            [{"name": "run", "description": "lint", "command": "python x.py"}]
        ),
    )
    tools, mapping = skill_core.build_openai_tools([skill])
    assert tools[0]["type"] == "function"
    assert tools[0]["function"]["name"] == "skill__lint__run"
    assert "skill__lint__run" in mapping
    assert mapping["skill__lint__run"][0] is skill


def test_parse_ids():
    assert skill_core.parse_ids("1,2,3") == [1, 2, 3]
    assert skill_core.parse_ids("") == []
    assert skill_core.parse_ids("a,4") == [4]


# ---------- 调用（软沙箱路径）----------


class _FakeProc:
    def __init__(self, rc, out, err=""):
        self.returncode = rc
        self.stdout = out
        self.stderr = err


def test_call_tool_local_stdin(monkeypatch, tmp_path):
    monkeypatch.setattr(skill_core.config, "skill_sandbox", "local")
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["input"] = kwargs.get("input")
        captured["cwd"] = kwargs.get("cwd")
        return _FakeProc(0, "lint:3\n")

    monkeypatch.setattr(skill_core.subprocess, "run", fake_run)
    skill = models.Skill(id=1, name="s", dir_path=str(tmp_path))
    out = asyncio.run(
        skill_core.call_tool(
            skill, {"command": "python tools/lint.py"}, {"file": "a.py"}
        )
    )
    assert out == "lint:3"
    assert json.loads(captured["input"]) == {"file": "a.py"}
    assert captured["cwd"] == str(tmp_path)


def test_call_tool_local_error(monkeypatch, tmp_path):
    monkeypatch.setattr(skill_core.config, "skill_sandbox", "local")

    def fake_run(cmd, **kwargs):
        return _FakeProc(2, "", "boom")

    monkeypatch.setattr(skill_core.subprocess, "run", fake_run)
    skill = models.Skill(id=1, name="s", dir_path=str(tmp_path))
    out = asyncio.run(skill_core.call_tool(skill, {"command": "python x"}, {}))
    assert "退出码 2" in out
    assert "boom" in out


# ---------- 调用（Docker SDK 路径）----------


def _install_fake_docker(
    monkeypatch, *, rc=0, out=b"", err=b"", wait_error=False, sent=None, created=None
):
    import sys
    import types

    if sent is None:
        sent = []
    if created is None:
        created = {}

    class FakeSocket:
        def __init__(self):
            self.shutdown_called = False

        def sendall(self, data):
            sent.append(data)

        def shutdown(self, how):
            self.shutdown_called = True

        def close(self):
            pass

    class FakeContainer:
        id = "cid123"

        def __init__(self):
            self.removed = False
            self.started = False

        def start(self):
            self.started = True

        def wait(self, timeout=None, condition=None):
            if wait_error:
                raise TimeoutError("read timeout")
            return {"StatusCode": rc}

        def logs(self, stdout=True, stderr=False):
            return out if stdout else err

        def remove(self, force=False):
            self.removed = True

    class FakeContainers:
        def __init__(self):
            self.container = FakeContainer()

        def create(self, image, command=None, **kwargs):
            created["image"] = image
            created["command"] = command
            created.update(kwargs)
            return self.container

    class FakeApi:
        def attach_socket(self, cid, params=None):
            return FakeSocket()

    class FakeClient:
        def __init__(self):
            self.containers = FakeContainers()
            self.api = FakeApi()

    fake = types.ModuleType("docker")
    setattr(fake, "from_env", lambda: FakeClient())
    monkeypatch.setitem(sys.modules, "docker", fake)
    return fake


def test_call_tool_docker_sdk(monkeypatch, tmp_path):
    sent, created = [], {}
    _install_fake_docker(monkeypatch, out=b"lint:3\n", sent=sent, created=created)
    monkeypatch.setattr(skill_core.config, "skill_sandbox", "docker")
    monkeypatch.setattr(skill_core.config, "upload_dir", str(tmp_path.parent))
    skill = models.Skill(id=1, name="s", dir_path=str(tmp_path))
    out = asyncio.run(
        skill_core.call_tool(
            skill, {"command": "python tools/lint.py"}, {"file": "a.py"}
        )
    )
    assert out == "lint:3"
    assert created["image"] == config.skill_runner_image
    assert created["command"] == ["sh", "-c", "python tools/lint.py"]
    assert created["working_dir"].startswith(config.skill_data_mount.rstrip("/"))
    assert created["volumes"][config.skill_data_volume]["mode"] == "ro"
    assert created["stdin_open"] is True
    assert json.loads(sent[0]) == {"file": "a.py"}


def test_call_tool_docker_timeout(monkeypatch, tmp_path):
    sent, created = [], {}
    _install_fake_docker(monkeypatch, wait_error=True, sent=sent, created=created)
    monkeypatch.setattr(skill_core.config, "skill_sandbox", "docker")
    monkeypatch.setattr(skill_core.config, "upload_dir", str(tmp_path.parent))
    skill = models.Skill(id=1, name="s", dir_path=str(tmp_path))
    out = asyncio.run(skill_core.call_tool(skill, {"command": "python x"}, {}))
    assert "超时" in out


def test_call_tool_docker_error(monkeypatch, tmp_path):
    sent, created = [], {}
    _install_fake_docker(monkeypatch, rc=2, err=b"boom", sent=sent, created=created)
    monkeypatch.setattr(skill_core.config, "skill_sandbox", "docker")
    monkeypatch.setattr(skill_core.config, "upload_dir", str(tmp_path.parent))
    skill = models.Skill(id=1, name="s", dir_path=str(tmp_path))
    out = asyncio.run(skill_core.call_tool(skill, {"command": "python x"}, {}))
    assert "退出码 2" in out
    assert "boom" in out


def test_call_tool_docker_unavailable_falls_back(monkeypatch, tmp_path):
    sent, created = [], {}
    _install_fake_docker(monkeypatch, sent=sent, created=created)

    def raise_from_env():
        raise RuntimeError("daemon unreachable")

    import sys

    setattr(sys.modules["docker"], "from_env", raise_from_env)
    monkeypatch.setattr(skill_core.config, "skill_sandbox", "auto")
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["input"] = kwargs.get("input")
        return _FakeProc(0, "local:ok")

    monkeypatch.setattr(skill_core.subprocess, "run", fake_run)
    skill = models.Skill(id=1, name="s", dir_path=str(tmp_path))
    out = asyncio.run(skill_core.call_tool(skill, {"command": "python x"}, {"k": 1}))
    assert out == "local:ok"


# ---------- 可见性/权限 ----------


def test_user_skills_global_and_assigned():
    db = _db()
    global_skill = models.Skill(id=1, name="g", scope="global", enabled=1)
    user_skill = models.Skill(id=2, name="u", scope="user", enabled=1)
    disabled = models.Skill(id=3, name="d", scope="user", enabled=0)
    db.add_all([global_skill, user_skill, disabled])
    db.add(models.SkillAccess(skill_id=2, user_id=10))
    db.add(models.SkillAccess(skill_id=3, user_id=10))
    db.commit()
    got = {s.id for s in skill_core.user_skills(db, 10)}
    assert got == {1, 2}
    db.close()


def test_resolve_skills_by_ids_only_enabled():
    db = _db()
    on = models.Skill(id=1, name="a", enabled=1)
    off = models.Skill(id=2, name="b", enabled=0)
    db.add_all([on, off])
    db.commit()
    ids = [s.id for s in skill_core.resolve_skills_by_ids(db, [1, 2])]
    assert ids == [1]
    assert skill_core.resolve_skills_by_ids(db, []) == []
    db.close()


# ---------- 管理后台 ----------


def test_admin_update_skill_assigns_users():
    db = _db()
    db.add(models.Skill(id=1, name="A", scope="global", enabled=1, tools="[]"))
    db.add(models.User(id=1, nickname="张三"))
    db.add(models.User(id=2, nickname="李四"))
    db.commit()
    out = admin_mod.update_skill(
        skill_id=1,
        payload=schemas.SkillUpdate(scope="user", enabled=1, user_ids=[1, 2]),
        admin=None,
        db=db,
    )
    assert out.scope == "user"
    assert sorted(out.user_ids) == [1, 2]
    db.close()


def test_admin_delete_skill():
    db = _db()
    db.add(models.Skill(id=1, name="A", enabled=1, tools="[]"))
    db.add(models.SkillAccess(skill_id=1, user_id=5))
    db.commit()
    assert admin_mod.delete_skill(skill_id=1, admin=None, db=db) == {"ok": True}
    assert db.get(models.Skill, 1) is None
    assert db.query(models.SkillAccess).count() == 0
    db.close()


# ---------- 会话技能接口 ----------


def test_update_conversation_skills():
    db = _db()
    db.add(models.User(id=1, nickname="张三"))
    db.add(models.Conversation(id=1, user_id=1, title="c", skill_ids=""))
    db.commit()
    out = conversations_mod.update_conversation_skills(
        conversation_id=1,
        payload=schemas.ConversationSkillUpdate(skill_ids="3,5"),
        user=db.get(models.User, 1),
        db=db,
    )
    assert out.skill_ids == "3,5"
    db.close()


# ---------- 聊天集成 ----------


class _FakeStreamResp:
    def __init__(self, lines, status=200):
        self._lines = lines
        self.status_code = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def aread(self):
        return b"mock error"

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeHttpClient:
    def __init__(self, tool_name):
        self.jsons = []
        self._first = tool_name

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def stream(self, method, url, headers=None, json=None):
        self.jsons.append(json)
        if len(self.jsons) == 1:
            lines = [
                'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","function":{"name":"'
                + self._first
                + '","arguments":"{}"}}]}}]}',
                "data: [DONE]",
            ]
        else:
            lines = [
                'data: {"choices":[{"delta":{"content":"ok"}}]}',
                'data: {"choices":[{"delta":{}}],"usage":{"total_tokens":7}}',
                "data: [DONE]",
            ]
        return _FakeStreamResp(lines)


def test_chat_injects_skill_and_routes(monkeypatch):
    db = _db()
    user = models.User(id=1, nickname="张三")
    endpoint = models.ApiEndpoint(
        id=1,
        name="ep",
        base_url="https://api.example/v1",
        api_key="k",
        models="gpt-test",
        enabled=1,
    )
    conversation = models.Conversation(id=1, user_id=1, title="c", skill_ids="3")
    setting = models.Setting(id=1)
    skill = models.Skill(id=3, name="代码检查", scope="global", enabled=1, tools="[]")
    db.add_all([user, endpoint, conversation, setting, skill])
    db.commit()

    calls = []

    def fake_build(skills):
        return (
            [
                {
                    "type": "function",
                    "function": {
                        "name": "skill__lint__run",
                        "description": "lint",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            {"skill__lint__run": (skill, {"name": "run", "command": "python x"})},
        )

    async def fake_call(sk, tool, arguments):
        calls.append((sk, tool, arguments))
        return "lint:3"

    monkeypatch.setattr(chat_mod.skill_core, "build_openai_tools", fake_build)
    monkeypatch.setattr(chat_mod.skill_core, "call_tool", fake_call)
    fake = _FakeHttpClient("skill__lint__run")
    monkeypatch.setattr(chat_mod.httpx, "AsyncClient", lambda *a, **k: fake)

    payload = schemas.ChatRequest(
        conversation_id=1, content="hi", endpoint_id=1, model="gpt-test"
    )
    resp = chat_mod.chat(payload=payload, user=user, db=db)

    async def collect():
        chunks = []
        async for c in resp.body_iterator:
            chunks.append(c)
        return "".join(chunks)

    output = asyncio.run(collect())

    assert "skill__lint__run" in str(fake.jsons[0].get("tools"))
    assert "tools" not in (fake.jsons[1] or {})
    assert calls and calls[0][1]["name"] == "run"
    assert "ok" in output
    db.close()
