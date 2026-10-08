from fastapi import HTTPException

import app.controllers.admin as admin_mod
import app.controllers.admin.system as system_mod
from app.controllers.admin import admin_access


def test_access_allowed_when_disabled(monkeypatch):
    setting = admin_mod.models.Setting(admin_secret_enabled=0, admin_secret="")
    monkeypatch.setattr(system_mod, "get_setting", lambda db: setting)
    assert admin_access(r="anything", db=None) == {"ok": True}


def test_access_allowed_with_correct_secret(monkeypatch):
    setting = admin_mod.models.Setting(admin_secret_enabled=1, admin_secret="abc123")
    monkeypatch.setattr(system_mod, "get_setting", lambda db: setting)
    assert admin_access(r="abc123", db=None) == {"ok": True}


def test_access_404_with_wrong_secret(monkeypatch):
    setting = admin_mod.models.Setting(admin_secret_enabled=1, admin_secret="abc123")
    monkeypatch.setattr(system_mod, "get_setting", lambda db: setting)
    try:
        admin_access(r="wrong", db=None)
        assert False, "should have raised"
    except HTTPException as e:
        assert e.status_code == 404


def test_access_404_without_secret(monkeypatch):
    setting = admin_mod.models.Setting(admin_secret_enabled=1, admin_secret="abc123")
    monkeypatch.setattr(system_mod, "get_setting", lambda db: setting)
    try:
        admin_access(r="", db=None)
        assert False, "should have raised"
    except HTTPException as e:
        assert e.status_code == 404
