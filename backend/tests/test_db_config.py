import json
import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import models
from app.database import Base, resolve_config, resolve_url
from app.services import db as db_service
from app.services import db_migrate
from app import config as app_config


def _make_source(path):
    """构造一个带示例数据的 SQLite 源库，返回 engine。"""
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    u = models.User(nickname="测试用户", phone="13800000000")
    s.add(u)
    s.flush()
    s.add(models.Conversation(user_id=u.id, title="会话1", model="gpt-4o-mini"))
    s.add(models.Setting(id=1, site_title="askai"))
    s.commit()
    s.close()
    return engine


class TestBuildUrl:
    def test_sqlite(self):
        url, dialect = db_service.build_url({"type": "sqlite", "path": "./x.db"})
        assert url == "sqlite:///./x.db"
        assert dialect == "sqlite"

    def test_mysql(self):
        url, dialect = db_service.build_url(
            {"type": "mysql", "host": "127.0.0.1", "port": "3306",
             "database": "askai", "username": "root", "password": "p@ss"}
        )
        assert url == "mysql+pymysql://root:p%40ss@127.0.0.1:3306/askai"
        assert dialect == "mysql"

    def test_postgresql(self):
        url, _ = db_service.build_url(
            {"type": "postgresql", "host": "db", "port": "5432",
             "database": "askai", "username": "user", "password": "pw"}
        )
        assert url.startswith("postgresql+psycopg2://user:pw@db:5432/askai")

    def test_mssql(self):
        url, _ = db_service.build_url(
            {"type": "mssql", "host": "db", "port": "1433",
             "database": "askai", "username": "sa", "password": "pw"}
        )
        assert url.startswith("mssql+pymssql://sa:pw@db:1433/askai")

    def test_oracle(self):
        url, _ = db_service.build_url(
            {"type": "oracle", "host": "db", "port": "1521",
             "database": "XEPDB1", "username": "askai", "password": "pw"}
        )
        assert url.startswith("oracle+oracledb://askai:pw@db:1521/XEPDB1")

    def test_unsupported(self):
        with pytest.raises(ValueError):
            db_service.build_url({"type": "db2"})


class TestResolveUrl:
    def test_priority_config_file(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "db_config.json"
        cfg_file.write_text(
            json.dumps({"type": "sqlite", "path": str(tmp_path / "cfg.db")}),
            encoding="utf-8",
        )
        monkeypatch.setattr(app_config.config, "db_config_file", str(cfg_file))
        url, dialect = resolve_url()
        assert dialect == "sqlite"
        assert str(tmp_path / "cfg.db") in url

    def test_fallback_default(self, monkeypatch, tmp_path):
        # 无配置文件 + 无环境变量 -> 默认 sqlite
        monkeypatch.setattr(app_config.config, "db_config_file", str(tmp_path / "nope.json"))
        monkeypatch.delenv("DATABASE_URL", raising=False)
        url, dialect = resolve_url()
        assert dialect == "sqlite"
        assert "app.db" in url

    def test_invalid_config_returns_none(self, tmp_path):
        cfg_file = tmp_path / "bad.json"
        cfg_file.write_text("not json", encoding="utf-8")
        old = app_config.config.db_config_file
        app_config.config.db_config_file = str(cfg_file)
        try:
            assert resolve_config() is None
        finally:
            app_config.config.db_config_file = old


class TestConnection:
    def test_sqlite_ok(self, tmp_path):
        path = str(tmp_path / "t.db")
        res = db_service.test_connection({"type": "sqlite", "path": path})
        assert res["ok"] is True
        assert os.path.exists(path)

    def test_driver_status(self):
        status = db_service.driver_status()
        assert status["sqlite"] is True
        assert "mysql" in status


class TestMigrate:
    def test_sqlite_to_sqlite(self, tmp_path):
        src_path = tmp_path / "src.db"
        tgt_path = tmp_path / "tgt.db"
        src_engine = _make_source(str(src_path))
        res = db_migrate.migrate(
            {"type": "sqlite", "path": str(tgt_path)},
            override=False,
            backup=False,
            src_engine=src_engine,
        )
        assert res["ok"] is True
        tgt = create_engine(f"sqlite:///{tgt_path}")
        Session = sessionmaker(bind=tgt)
        s = Session()
        users = s.execute(select(models.User)).scalars().all()
        assert len(users) == 1
        assert users[0].nickname == "测试用户"
        convs = s.execute(select(models.Conversation)).scalars().all()
        assert len(convs) == 1
        assert convs[0].user_id == users[0].id
        s.close()
        src_engine.dispose()

    def test_refuses_nonempty_target_without_override(self, tmp_path):
        src_path = tmp_path / "src.db"
        tgt_path = tmp_path / "tgt.db"
        src_engine = _make_source(str(src_path))
        # 先在目标库放一条数据
        tgt = create_engine(f"sqlite:///{tgt_path}")
        Base.metadata.create_all(tgt)
        Session = sessionmaker(bind=tgt)
        s = Session()
        s.add(models.ApiEndpoint(name="existing", base_url="http://x"))
        s.commit()
        s.close()
        res = db_migrate.migrate(
            {"type": "sqlite", "path": str(tgt_path)},
            override=False,
            backup=False,
            src_engine=src_engine,
        )
        assert res["ok"] is False
        src_engine.dispose()


class TestEnsureColumnsIdempotent:
    def test_create_all_twice(self, tmp_path):
        # create_all 幂等（已齐全的列不会被再次 ALTER）
        path = str(tmp_path / "a.db")
        engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(engine)
        Base.metadata.create_all(engine)
        from app.main import _ensure_columns

        _ensure_columns(engine)
        _ensure_columns(engine)
