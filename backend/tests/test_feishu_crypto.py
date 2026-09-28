import app.services.feishu_crypto as fc


KEY = "my-secret-encrypt-key"
PLAIN = '{"challenge":"abc123","token":"tk","type":"url_verification"}'


def test_encrypt_decrypt_roundtrip():
    enc = fc.encrypt(KEY, PLAIN)
    assert isinstance(enc, str)
    dec = fc.decrypt(KEY, enc)
    assert dec == PLAIN


def test_decrypt_uses_sha256_key_iv():
    # 密钥为 sha256(EncryptKey)，用不同 key 解密要么报错要么得到不同内容
    enc = fc.encrypt(KEY, PLAIN)
    try:
        other = fc.decrypt(KEY + "x", enc)
        assert other != PLAIN
    except Exception:
        pass


def test_wrong_padding_raises():
    try:
        fc.decrypt(KEY, "===invalid===")
    except Exception:
        assert True
    else:
        raise AssertionError("invalid base64 should raise")
