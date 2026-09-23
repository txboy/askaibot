"""企业微信消息加解密（AES-256-CBC / PKCS7，区块按 32 补齐）。"""

import base64
import hashlib
import os
import struct

from Crypto.Cipher import AES


class WeComCryptoError(Exception):
    pass


def _aes_key(aes_key: str) -> bytes:
    return base64.b64decode(aes_key + "=")


def signature(token: str, timestamp: str, nonce: str, encrypt: str) -> str:
    arr = sorted([token, timestamp, nonce, encrypt])
    return hashlib.sha1("".join(arr).encode()).hexdigest()


def _pad(data: bytes, block: int = 32) -> bytes:
    pad = block - (len(data) % block)
    return data + bytes([pad]) * pad


def _unpad(data: bytes, block: int = 32) -> bytes:
    if not data:
        return data
    pad = data[-1]
    if pad < 1 or pad > block:
        raise WeComCryptoError("invalid padding")
    return data[:-pad]


def encrypt_msg(plaintext: str, aes_key: str, receive_id: str) -> bytes:
    key = _aes_key(aes_key)
    iv = key[:16]
    msg = plaintext.encode("utf-8")
    body = (
        os.urandom(16) + struct.pack(">I", len(msg)) + msg + receive_id.encode("utf-8")
    )
    padded = _pad(body)
    return AES.new(key, AES.MODE_CBC, iv).encrypt(padded)


def decrypt_msg(encrypted: bytes, aes_key: str, receive_id: str) -> str:
    key = _aes_key(aes_key)
    iv = key[:16]
    data = AES.new(key, AES.MODE_CBC, iv).decrypt(encrypted)
    data = _unpad(data)
    msg_len = struct.unpack(">I", data[16:20])[0]
    msg = data[20 : 20 + msg_len].decode("utf-8")
    rid = data[20 + msg_len :].decode("utf-8")
    if rid != receive_id:
        raise WeComCryptoError("receive_id mismatch")
    return msg
