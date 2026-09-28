from app import models, schemas
import app.services.captcha as captcha_mod


# ---------------- tencent ----------------


def test_tencent_dispatch(monkeypatch):
    calls = {}

    def fake_tencent(app_id, secret, ticket, randstr):
        calls["app_id"] = app_id
        calls["ticket"] = ticket
        return True

    monkeypatch.setattr(captcha_mod, "_tencent_request", fake_tencent)
    setting = models.Setting(
        id=1,
        sms_captcha_provider="tencent",
        tencent_captcha_app_id="aid",
        tencent_captcha_app_secret_key="skey",
    )
    payload = schemas.SMSRequest(phone="13800000000", ticket="tick", randstr="rand")
    assert captcha_mod.verify(setting, payload) is True
    assert calls["app_id"] == "aid"
    assert calls["ticket"] == "tick"


def test_tencent_missing_ticket_returns_false(monkeypatch):
    called = []

    def fake_tencent(*args, **kwargs):
        called.append(True)
        return True

    monkeypatch.setattr(captcha_mod, "_tencent_request", fake_tencent)
    setting = models.Setting(
        id=1,
        sms_captcha_provider="tencent",
        tencent_captcha_app_id="aid",
        tencent_captcha_app_secret_key="skey",
    )
    assert captcha_mod.verify(setting, schemas.SMSRequest(phone="13800000000")) is False
    assert called == []


def test_tencent_request_success(monkeypatch):
    captured = {}

    def fake_post(url, params=None, data=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["data"] = data

        class R:
            text = '"0"'

        return R()

    monkeypatch.setattr(captcha_mod.httpx, "post", fake_post)
    assert captcha_mod._tencent_request("aid", "skey", "tick", "rand") is True
    assert "ssl.captcha.qq.com" in captured["url"]
    assert captured["params"] == {"aid": "aid"}
    assert captured["data"]["Ticket"] == "tick"
    assert captured["data"]["Randstr"] == "rand"


def test_tencent_request_fail(monkeypatch):
    def fake_post(*args, **kwargs):
        class R:
            text = '"1"'

        return R()

    monkeypatch.setattr(captcha_mod.httpx, "post", fake_post)
    assert captcha_mod._tencent_request("aid", "skey", "tick", "rand") is False


# ---------------- aliyun ----------------


def test_aliyun_dispatch(monkeypatch):
    calls = {}

    def fake_aliyun(ak, sk, scene, param):
        calls["scene"] = scene
        calls["param"] = param
        return True

    monkeypatch.setattr(captcha_mod, "_aliyun_request", fake_aliyun)
    setting = models.Setting(
        id=1,
        sms_captcha_provider="aliyun",
        aliyun_captcha_access_key_id="AK",
        aliyun_captcha_access_key_secret="SK",
        aliyun_captcha_scene_id="sc",
    )
    payload = schemas.SMSRequest(phone="13800000000", captcha_verify_param="param")
    assert captcha_mod.verify(setting, payload) is True
    assert calls["scene"] == "sc"
    assert calls["param"] == "param"


def test_aliyun_missing_param_returns_false():
    assert captcha_mod._aliyun_request("AK", "SK", "sc", "") is False
