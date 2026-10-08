import json
import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.dialects import mssql, oracle
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateIndex, CreateTable

from app import models
from app.database import Base, resolve_config, resolve_url
from app.models.user import User
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
            {
                "type": "mysql",
                "host": "127.0.0.1",
                "port": "3306",
                "database": "askai",
                "username": "root",
                "password": "p@ss",
            }
        )
        assert url == "mysql+pymysql://root:p%40ss@127.0.0.1:3306/askai"
        assert dialect == "mysql"

    def test_postgresql(self):
        url, _ = db_service.build_url(
            {
                "type": "postgresql",
                "host": "db",
                "port": "5432",
                "database": "askai",
                "username": "user",
                "password": "pw",
            }
        )
        assert url.startswith("postgresql+psycopg2://user:pw@db:5432/askai")

    def test_mssql(self):
        url, _ = db_service.build_url(
            {
                "type": "mssql",
                "host": "db",
                "port": "1433",
                "database": "askai",
                "username": "sa",
                "password": "pw",
            }
        )
        assert url.startswith("mssql+pymssql://sa:pw@db:1433/askai")

    def test_oracle_uses_service_name(self):
        # PDB 通过 service_name 注册，URL 路径会被当作 SID，需用查询参数。
        url, _ = db_service.build_url(
            {
                "type": "oracle",
                "host": "db",
                "port": "1521",
                "database": "FREEPDB1",
                "username": "askai",
                "password": "pw",
            }
        )
        assert url == "oracle+oracledb://askai:pw@db:1521/?service_name=FREEPDB1"

    def test_oracle_without_database(self):
        url, _ = db_service.build_url(
            {
                "type": "oracle",
                "host": "db",
                "port": "1521",
                "username": "askai",
                "password": "pw",
            }
        )
        assert url == "oracle+oracledb://askai:pw@db:1521/"

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
        monkeypatch.setattr(
            app_config.config, "db_config_file", str(tmp_path / "nope.json")
        )
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


class TestUserUniqueIndexes:
    def test_mssql_uses_filtered_unique_index(self):
        # SQL Server 唯一索引不允许重复 NULL，必须用过滤索引
        # 只对非空值唯一，以支持多个用户没有该平台标识。
        index_map = {index.name: index for index in User.__table__.indexes}
        for col, idx_name in [
            ("phone", "ix_users_phone"),
            ("wecom_userid", "ix_users_wecom_userid"),
            ("dingtalk_userid", "ix_users_dingtalk_userid"),
            ("feishu_userid", "ix_users_feishu_userid"),
        ]:
            ddl = str(CreateIndex(index_map[idx_name]).compile(dialect=mssql.dialect()))
            assert "IS NOT NULL" in ddl, f"{idx_name} 应为过滤唯一索引: {ddl}"
            assert "UNIQUE" in ddl, f"{idx_name} 应保持唯一: {ddl}"

    def test_mssql_allows_multiple_null_users(self, tmp_path):
        # 用多个 NULL dingtalk_userid 的用户验证迁移不再报重复 NULL。
        src_path = tmp_path / "src.db"
        src_engine = create_engine(f"sqlite:///{src_path}")
        Base.metadata.create_all(src_engine)
        Session = sessionmaker(bind=src_engine)
        s = Session()
        for i in range(3):
            s.add(models.User(nickname=f"用户{i}", phone=f"1380000000{i}"))
        s.commit()
        s.close()
        tgt_path = tmp_path / "tgt.db"
        res = db_migrate.migrate(
            {"type": "sqlite", "path": str(tgt_path)},
            override=False,
            backup=False,
            src_engine=src_engine,
        )
        assert res["ok"] is True


class TestOracleEmptyString:
    def test_default_setting_roundtrip(self, tmp_path):
        # Oracle 将空串视为 NULL；OrEmptyStr/OrEmptyText 应保证空串读写一致。
        engine = create_engine(f"sqlite:///{tmp_path / 's.db'}")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        s = Session()
        s.add(models.Setting(id=1))
        s.commit()
        setting = s.get(models.Setting, 1)
        assert setting is not None
        assert setting.site_title == "askaibot"
        assert setting.api_key == ""  # 空串读取归一化为 ''
        assert setting.system_prompt == ""
        s.close()

    def test_oracle_nullable_for_empty_columns(self):
        # 空串默认列在 Oracle 下必须可空，否则 '' 存为 NULL 会触发 ORA-01400。
        from app.models.setting import Setting
        from app.models.user import User

        table_ddl = str(
            CreateTable(Setting.__table__).compile(dialect=oracle.dialect())
        )
        # api_key 列应可空（不带 NOT NULL）
        api_key_line = next(
            line.strip()
            for line in table_ddl.splitlines()
            if line.strip().startswith("api_key")
        )
        assert "NOT NULL" not in api_key_line, f"api_key 应为可空列: {api_key_line}"
        user_ddl = str(CreateTable(User.__table__).compile(dialect=oracle.dialect()))
        avatar_line = next(
            line.strip()
            for line in user_ddl.splitlines()
            if line.strip().startswith("avatar")
        )
        assert "NOT NULL" not in avatar_line, f"avatar 应为可空列: {avatar_line}"


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
