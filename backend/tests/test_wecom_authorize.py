from urllib.parse import parse_qs, urlparse

from app import models
from app.controllers.frontend.auth import _wecom_authorize_url, _wecom_callback_url


def _setting():
    return models.Setting(
        wecom_corp_id="wwa7f31908d0ab46a2",
        wecom_agent_id="1000191",
        wecom_redirect="https://oabot.gxqggsglyxgs.cn:18899",
    )


def test_authorize_redirect_uri_points_to_callback():
    url = _wecom_authorize_url(_setting(), state="abc123")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    redirect = query["redirect_uri"][0]
    assert redirect == "https://oabot.gxqggsglyxgs.cn:18899/api/auth/wecom/callback"


def test_authorize_query_params():
    url = _wecom_authorize_url(_setting(), state="abc123")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert query["appid"] == ["wwa7f31908d0ab46a2"]
    assert query["agentid"] == ["1000191"]
    assert query["state"] == ["abc123"]
    assert query["response_type"] == ["code"]


def test_callback_url_appends_when_missing():
    assert (
        _wecom_callback_url(_setting())
        == "https://oabot.gxqggsglyxgs.cn:18899/api/auth/wecom/callback"
    )


def test_callback_url_does_not_duplicate_path():
    setting = models.Setting()
    setting.wecom_redirect = (
        "https://oabot.gxqggsglyxgs.cn:18899/api/auth/wecom/callback"
    )
    assert (
        _wecom_callback_url(setting)
        == "https://oabot.gxqggsglyxgs.cn:18899/api/auth/wecom/callback"
    )
