import base64
import random
import hashlib
from typing import Any, Dict


def rand_str(length: int) -> str:
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(random.choice(chars) for _ in range(length))


def rsa_encrypt(data: str, public_key_base64: str) -> str:
    try:
        from Crypto.Cipher import PKCS1_v1_5
        from Crypto.PublicKey import RSA
    except Exception:
        raise RuntimeError("[DNA] 缺少依赖: 需要 pycryptodome 执行 RSA 加密。请安装: uv add pycryptodome")
    try:
        key = RSA.importKey(base64.b64decode(public_key_base64))
        cipher = PKCS1_v1_5.new(key)
        return base64.b64encode(cipher.encrypt(data.encode("utf-8"))).decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"RSA Encrypt Error: {e}")


def xor_encode(text: str, key: str) -> str:
    """自定义 XOR 编码（字节值相加，非异或）"""
    tb = text.encode("utf-8")
    kb = key.encode("utf-8")
    return "".join(f"@{(tb[i] & 255) + (kb[i % len(kb)] & 255)}" for i in range(len(tb)))


def shuffle_md5(md5_hex: str) -> str:
    """MD5 结果位置混淆: 1↔13, 5↔17, 7↔23"""
    if len(md5_hex) <= 23:
        return md5_hex
    chars = list(md5_hex)
    for i, j in [(1, 13), (5, 17), (7, 23)]:
        chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)


def sign_shuffled(params: Dict[str, Any], app_key: str) -> str:
    """按 key 排序拼接参数 → MD5 → shuffle"""
    pairs = [f"{k}={params[k]}" for k in sorted(params) if params[k] is not None and str(params[k]) != ""]
    pairs.append(app_key)
    md5_hash = hashlib.md5("&".join(pairs).encode("utf-8")).hexdigest().upper()
    return shuffle_md5(md5_hash)
