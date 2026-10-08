import hashlib
import hmac

from app import models, schemas
import app.services.captcha as captcha_mod


def test_geetest_sign_token_and_success(monkeypatch):
    captured = {}

    def fake_post(url, params=None, data=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["data"] = data

        class R:
            def json(self):
                return {"result": "success"}

        return R()

    monkeypatch.setattr(captcha_mod.httpx, "post", fake_post)
    setting = models.Setting(
        id=1,
        sms_captcha_provider="geetest",
        geetest_captcha_id="gid",
        geetest_captcha_key="gkey",
    )
    payload = schemas.SMSRequest(
        phone="13800000000",
        lot_number="lot123",
        captcha_output="out",
        pass_token="pass",
        gen_time="123",
    )
    assert captcha_mod.verify(setting, payload) is True
    assert captured["url"].endswith("/validate")
    assert captured["params"] == {"captcha_id": "gid"}
    expected = hmac.new(b"gkey", b"lot123", hashlib.sha256).hexdigest()
    assert captured["data"]["sign_token"] == expected
    assert captured["data"]["lot_number"] == "lot123"
    assert captured["data"]["captcha_output"] == "out"
    assert captured["data"]["pass_token"] == "pass"


def test_geetest_fail(monkeypatch):
    def fake_post(*args, **kwargs):
        class R:
            def json(self):
                return {"result": "fail"}

        return R()

    monkeypatch.setattr(captcha_mod.httpx, "post", fake_post)
    setting = models.Setting(
        id=1,
        sms_captcha_provider="geetest",
        geetest_captcha_id="gid",
        geetest_captcha_key="gkey",
    )
    payload = schemas.SMSRequest(phone="13800000000", lot_number="lot123")
    assert captcha_mod.verify(setting, payload) is False


def test_geetest_network_error_returns_false(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(captcha_mod.httpx, "post", boom)
    setting = models.Setting(
        id=1,
        sms_captcha_provider="geetest",
        geetest_captcha_id="gid",
        geetest_captcha_key="gkey",
    )
    payload = schemas.SMSRequest(phone="13800000000", lot_number="lot123")
    assert captcha_mod.verify(setting, payload) is False


def test_geetest_missing_config_returns_false():
    setting = models.Setting(id=1, sms_captcha_provider="geetest")
    payload = schemas.SMSRequest(phone="13800000000", lot_number="lot123")
    assert captcha_mod.verify(setting, payload) is False
