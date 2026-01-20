import time
import uuid
import base64
import hashlib
import secrets
from typing import Any, Dict, Tuple, Optional


def rsa_encrypt(text: str, public_key_b64: str) -> str:
    try:
        from Crypto.Cipher import PKCS1_v1_5
        from Crypto.PublicKey import RSA
    except Exception:
        raise RuntimeError("[DNA] 缺少依赖: 需要 pycryptodome 执行 RSA 加密。请安装: uv add pycryptodome")

    try:
        # 将一行 base64 公钥转 PEM（PKCS#8 公钥）
        lines = [public_key_b64[i : i + 64] for i in range(0, len(public_key_b64), 64)]
        pem = "-----BEGIN PUBLIC KEY-----\n" + "\n".join(lines) + "\n-----END PUBLIC KEY-----"
        rsa_key = RSA.import_key(pem)
        cipher = PKCS1_v1_5.new(rsa_key)

        max_block_size = 117
        input_bytes = text.encode("utf-8")
        result = []
        offset = 0
        while offset < len(input_bytes):
            remaining = len(input_bytes) - offset
            block_size = min(max_block_size, remaining)
            block = input_bytes[offset : offset + block_size]
            encrypted = cipher.encrypt(block)
            result.append(encrypted)
            offset += block_size

        encrypted_bytes = b"".join(result)
        return base64.b64encode(encrypted_bytes).decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"[DNA] RSA 加密失败: {e}")


def get_timestamp() -> int:
    return int(time.time() * 1000)


def get_dev_code() -> str:
    return str(uuid.uuid4()).upper()


def rand_str(length: int = 16) -> str:
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(chars) for _ in range(length))


def md5_upper(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest().upper()


def shuffle_md5(md5_hex: str) -> str:
    """MD5 结果位置混淆: 1↔13, 5↔17, 7↔23"""
    if len(md5_hex) <= 23:
        return md5_hex
    chars = list(md5_hex)
    for i, j in [(1, 13), (5, 17), (7, 23)]:
        chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)


def generate_sa() -> Tuple[str, str]:
    """生成 sa 参数 (30位字符串)
    Returns:
        (raw_sa, shuffled_sa)
    """
    random_part = rand_str(17)
    timestamp = str(int(time.time() * 1000))

    result = []
    rand_idx = 0
    time_idx = 0

    for i in range(30):
        if 8 <= i <= 12:
            result.append(timestamp[time_idx])
            time_idx += 1
        elif 16 <= i <= 20:
            result.append(timestamp[time_idx])
            time_idx += 1
        elif 22 <= i <= 24:
            result.append(timestamp[time_idx])
            time_idx += 1
        else:
            result.append(random_part[rand_idx])
            rand_idx += 1

    raw_sa = "".join(result)

    chars = list(raw_sa)
    for i, j in [(2, 23), (9, 17), (13, 25)]:
        chars[i], chars[j] = chars[j], chars[i]
    shuffled_sa = "".join(chars)

    return raw_sa, shuffled_sa


def build_sign_string(params: Dict[str, Any], app_key: str) -> str:
    sorted_keys = sorted(params.keys())
    pairs = []
    for key in sorted_keys:
        value = params.get(key, "")
        if value is not None and value != "":
            pairs.append(f"{key}={value}")
    pairs.append(app_key)
    return "&".join(pairs)


def sign_shuffled(params: Dict[str, Any], app_key: str) -> str:
    sign_str = build_sign_string(params, app_key)
    md5_res = md5_upper(sign_str)
    return shuffle_md5(md5_res)


def xor_encode(text: str, key: str) -> str:
    tb = list(text.encode("utf-8"))
    kb = list(key.encode("utf-8"))
    out = []
    for i, b in enumerate(tb):
        e = (b & 255) + (kb[i % len(kb)] & 255)
        out.append(f"@{e}")
    return "".join(out)


def build_signature_headers(
    params: Dict[str, Any], token: Optional[str], dev_code: str, rsa_public_key: str
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    rk = rand_str(16)
    raw_sa, shuffled_sa = generate_sa()
    str_params = {k: str(v) for k, v in params.items()}
    sign_params = str_params.copy()
    if token:
        sign_params["token"] = token
    sign_params["sa"] = raw_sa

    sign_val = sign_shuffled(sign_params, rk)
    rk_encrypted = rsa_encrypt(rk, rsa_public_key)
    sign_encoded = xor_encode(sign_val, rk)
    tn_value = f"{rk_encrypted},{sign_encoded}"

    headers_update = {
        "rk": rk,
        "tn": tn_value,
        "sa": shuffled_sa,
        "devcode": dev_code,
    }

    return headers_update, str_params


def get_signed_headers_and_body(
    url: str,
    header: Dict[str, str],
    data: Dict[str, Any],
    rsa_public_key: str,
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    SIGN_API_LIST = [
        "/user/sdkLogin",
        "/user/getSmsCode",
        "/role/defaultRoleForTool",
        "/encourage/signin/signin",
        "/user/signIn",
        "/user/refreshToken",
        "/role/defaultRole",
        "/role/list",
        "/role/getShortNoteInfo",
        "/forum/like",
        "/encourage/calendar/Activity/list",
    ]

    need_sign = False
    for api in SIGN_API_LIST:
        if url.endswith(api):
            need_sign = True
            break

    if not need_sign:
        return header, data

    current_header = header or {}
    dev_code = current_header.get("devcode") or get_dev_code()
    token = current_header.get("token")

    current_data = data or {}

    headers_update, body_update = build_signature_headers(
        params=current_data, token=token, dev_code=dev_code, rsa_public_key=rsa_public_key
    )

    new_header = dict(current_header)
    new_header.update(headers_update)

    return new_header, body_update
