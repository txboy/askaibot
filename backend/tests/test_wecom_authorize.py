from urllib.parse import parse_qs, urlparse

from app import models
from app.controllers.frontend.auth import _wecom_authorize_url, _wecom_callback_url


class _Req:
    base_url = "http://testserver"


def _setting():
    return models.Setting(
        wecom_corp_id="wwtestcorp12345678",
        wecom_agent_id="1000001",
        wecom_redirect="https://example.com",
    )


def test_authorize_redirect_uri_points_to_callback():
    url = _wecom_authorize_url(_Req(), _setting(), state="abc123")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    redirect = query["redirect_uri"][0]
    assert redirect == "https://example.com/api/auth/wecom/callback"


def test_authorize_query_params():
    url = _wecom_authorize_url(_Req(), _setting(), state="abc123")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert query["appid"] == ["wwtestcorp12345678"]
    assert query["agentid"] == ["1000001"]
    assert query["state"] == ["abc123"]
    assert query["response_type"] == ["code"]


def test_callback_url_appends_when_missing():
    assert (
        _wecom_callback_url(_Req(), _setting())
        == "https://example.com/api/auth/wecom/callback"
    )


def test_callback_url_does_not_duplicate_path():
    setting = models.Setting()
    setting.wecom_redirect = "https://example.com/api/auth/wecom/callback"
    assert (
        _wecom_callback_url(_Req(), setting)
        == "https://example.com/api/auth/wecom/callback"
    )
