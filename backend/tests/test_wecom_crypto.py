import base64
import hashlib

import pytest

import app.wecom_crypto as wc


AES_KEY = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG"  # 43 chars -> 32 byte key


def test_signature_uses_sorted_concat():
    sig = wc.signature("token", "123", "nonce", "encrypt")
    expected = hashlib.sha1(
        "".join(sorted(["token", "123", "nonce", "encrypt"])).encode()
    ).hexdigest()
    assert sig == expected


def test_encrypt_decrypt_roundtrip():
    plain = "<xml><ToUserName>corp</ToUserName><Content>你好</Content></xml>"
    enc = wc.encrypt_msg(plain, AES_KEY, "corp123")
    assert isinstance(enc, bytes)
    dec = wc.decrypt_msg(enc, AES_KEY, "corp123")
    assert dec == plain


def test_decrypt_extracts_corp_id_and_rejects_mismatch():
    plain = "<xml>abc</xml>"
    enc = wc.encrypt_msg(plain, AES_KEY, "corp123")
    assert wc.decrypt_msg(enc, AES_KEY, "corp123") == plain
    with pytest.raises(wc.WeComCryptoError):
        wc.decrypt_msg(enc, AES_KEY, "other")
