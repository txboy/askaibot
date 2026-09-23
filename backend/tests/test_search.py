import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.routers.admin as admin_mod
import app.search as search_mod
from app import models, schemas
from app.database import Base


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        return None


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.post_data = {}
        self.get_params = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, **kwargs):
        self.post_data = kwargs
        return FakeResponse({"results": [{"title": "T", "url": "U", "content": "C"}]})

    async def get(self, url, **kwargs):
        self.get_params = kwargs
        return FakeResponse(
            {
                "webPages": {"value": [{"name": "T", "url": "U", "snippet": "C"}]},
                "results": [{"title": "T", "url": "U", "content": "C"}],
                "AbstractText": "abs",
                "RelatedTopics": [{"Text": "top", "FirstURL": "U"}],
            }
        )


def test_format_results_empty():
    assert "未找到" in search_mod.format_results([])


def test_format_results_has_results():
    text = search_mod.format_results([{"title": "T", "url": "U", "content": "C"}])
    assert "T" in text and "U" in text and "C" in text


def test_search_web_unknown_provider():
    with pytest.raises(ValueError):
        import asyncio

        asyncio.run(search_mod.search_web("unknown", "", "", "q"))


def test_tavily(monkeypatch):
    monkeypatch.setattr(search_mod.httpx, "AsyncClient", FakeClient)
    import asyncio

    results = asyncio.run(
        search_mod.search_web("tavily", "key", "", "hello")
    )
    assert results and results[0]["title"] == "T"


def test_bing(monkeypatch):
    monkeypatch.setattr(search_mod.httpx, "AsyncClient", FakeClient)
    import asyncio

    results = asyncio.run(search_mod.search_web("bing", "key", "", "hello"))
    assert results and results[0]["title"] == "T"


def test_searxng(monkeypatch):
    monkeypatch.setattr(search_mod.httpx, "AsyncClient", FakeClient)
    import asyncio

    results = asyncio.run(
        search_mod.search_web("searxng", "", "https://searx.example", "hello")
    )
    assert results and results[0]["title"] == "T"


def test_duckduckgo(monkeypatch):
    monkeypatch.setattr(search_mod.httpx, "AsyncClient", FakeClient)
    import asyncio

    results = asyncio.run(search_mod.search_web("duckduckgo", "", "", "hello"))
    assert results


def test_admin_search_get(monkeypatch):
    setting = models.Setting(id=1)
    setting.search_provider = "tavily"
    setting.search_base_url = ""
    setting.search_auto = 1
    setting.search_api_key = "secret"
    monkeypatch.setattr(admin_mod, "get_setting", lambda db: setting)
    out = admin_mod.get_search(admin=None, db=None)
    assert out.provider == "tavily"
    assert out.auto is True
    assert out.api_key_set is True


def test_admin_search_put(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    setting = models.Setting(id=1)
    db.add(setting)
    db.commit()
    monkeypatch.setattr(admin_mod, "get_setting", lambda db: setting)
    out = admin_mod.update_search(
        payload=schemas.SearchUpdate(
            provider="bing", api_key="newkey", base_url="https://x", auto=True
        ),
        admin=None,
        db=db,
    )
    assert out.provider == "bing"
    assert out.api_key_set is True
    assert out.auto is True
    db.close()
