import pytest
from fastapi import HTTPException

import app.controllers.frontend.uploads as upload_mod
from app import models
from app.controllers.frontend.uploads import get_default_assistant_avatar, get_site


@pytest.fixture
def setting():
    return models.Setting(id=1)


def test_get_site_assistant_avatar_url_empty(monkeypatch, setting):
    monkeypatch.setattr(upload_mod, "get_setting", lambda db: setting)
    result = get_site(db=None)
    assert result["assistant_avatar_url"] == ""


def test_get_site_assistant_avatar_url_set(monkeypatch, setting):
    setting.assistant_avatar = "assistant_avatar_abc.png"
    monkeypatch.setattr(upload_mod, "get_setting", lambda db: setting)
    result = get_site(db=None)
    assert "assistant-avatar?v=" in result["assistant_avatar_url"]


def test_default_avatar_404_when_unset(monkeypatch, setting):
    monkeypatch.setattr(upload_mod, "get_setting", lambda db: setting)
    with pytest.raises(HTTPException) as exc:
        get_default_assistant_avatar(db=None)
    assert exc.value.status_code == 404
