"""飞书事件订阅加解密（AES-256-CBC / PKCS7，密钥为 EncryptKey 的 SHA-256）。"""

import base64
import hashlib

from Crypto.Cipher import AES


class FeishuCryptoError(Exception):
    pass


def _aes_key(encrypt_key: str) -> bytes:
    return hashlib.sha256(encrypt_key.encode("utf-8")).digest()


def decrypt(encrypt_key: str, encrypt_str: str) -> str:
    key = _aes_key(encrypt_key)
    iv = key[:16]
    data = AES.new(key, AES.MODE_CBC, iv).decrypt(base64.b64decode(encrypt_str))
    pad = data[-1]
    if pad < 1 or pad > 16:
        raise FeishuCryptoError("invalid padding")
    return data[:-pad].decode("utf-8")


def encrypt(encrypt_key: str, plaintext: str) -> str:
    key = _aes_key(encrypt_key)
    iv = key[:16]
    data = plaintext.encode("utf-8")
    pad = 16 - (len(data) % 16)
    data += bytes([pad]) * pad
    return base64.b64encode(AES.new(key, AES.MODE_CBC, iv).encrypt(data)).decode()
