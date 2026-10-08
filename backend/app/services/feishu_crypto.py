"""飞书事件订阅加解密（AES-256-CBC / PKCS7）。

官方格式：加密载荷为 ``base64(iv(16) + ciphertext)``，AES 密钥为 EncryptKey 的
SHA-256 摘要，IV 取自载荷前 16 字节（参见开放平台「事件解密」官方示例）。
"""

import base64
import hashlib
import os

from Crypto.Cipher import AES


class FeishuCryptoError(Exception):
    pass


def _aes_key(encrypt_key: str) -> bytes:
    return hashlib.sha256(encrypt_key.encode("utf-8")).digest()


def _unpad(data: bytes) -> bytes:
    pad = data[-1]
    if pad < 1 or pad > 16:
        raise FeishuCryptoError("invalid padding")
    return data[:-pad]


def decrypt(encrypt_key: str, encrypt_str: str) -> str:
    key = _aes_key(encrypt_key)
    raw = base64.b64decode(encrypt_str)
    if len(raw) < AES.block_size:
        raise FeishuCryptoError("cipher too short")
    iv = raw[: AES.block_size]
    data = AES.new(key, AES.MODE_CBC, iv).decrypt(raw[AES.block_size :])
    return _unpad(data).decode("utf-8")


def encrypt(encrypt_key: str, plaintext: str) -> str:
    key = _aes_key(encrypt_key)
    iv = os.urandom(AES.block_size)
    data = plaintext.encode("utf-8")
    pad = AES.block_size - (len(data) % AES.block_size)
    data += bytes([pad]) * pad
    ciphertext = AES.new(key, AES.MODE_CBC, iv).encrypt(data)
    return base64.b64encode(iv + ciphertext).decode()
