import time
import uuid
import base64
import random
import hashlib
from typing import Any, Dict, Tuple


def get_dev_code() -> str:
    return str(uuid.uuid4()).upper()


def generate_random_string(length):
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(random.choice(chars) for _ in range(length))


def swap_chars(char_list, *indices):
    for i in range(1, len(indices), 2):
        idx1 = indices[i - 1]
        idx2 = indices[i]
        if idx1 < len(char_list) and idx2 < len(char_list):
            char_list[idx1], char_list[idx2] = char_list[idx2], char_list[idx1]


class SignUtils:
    @staticmethod
    def generate_sa():
        random_str = generate_random_string(17)
        timestamp = str(int(time.time() * 1000))

        sb = []
        time_idx = 0
        rand_idx = 0

        for i in range(30):
            if 8 <= i <= 12:
                sb.append(timestamp[time_idx])
                time_idx += 1
            elif 16 <= i <= 20:
                sb.append(timestamp[time_idx])
                time_idx += 1
            elif i < 22 or i > 24:
                sb.append(random_str[rand_idx])
                rand_idx += 1
            else:
                sb.append(timestamp[time_idx])
                time_idx += 1

        sa_raw = "".join(sb)

        char_list = list(sa_raw)
        swap_chars(char_list, 2, 23, 9, 17, 13, 25)
        sa_header = "".join(char_list)

        return sa_raw, sa_header

    @staticmethod
    def rsa_encrypt(data, public_key_base64):
        try:
            from Crypto.Cipher import PKCS1_v1_5
            from Crypto.PublicKey import RSA
        except Exception:
            raise RuntimeError("[DNA] 缺少依赖: 需要 pycryptodome 执行 RSA 加密。请安装: uv add pycryptodome")
        try:
            key_data = base64.b64decode(public_key_base64)
            key = RSA.importKey(key_data)
            cipher = PKCS1_v1_5.new(key)
            encrypted_bytes = cipher.encrypt(data.encode("utf-8"))
            return base64.b64encode(encrypted_bytes).decode("utf-8")
        except Exception as e:
            raise RuntimeError(f"RSA Encrypt Error: {e}")

    @staticmethod
    def custom_encrypt(src, key):
        src_bytes = src.encode("utf-8")
        key_bytes = key.encode("utf-8")
        sb = []

        for i in range(len(src_bytes)):
            b1 = src_bytes[i]
            b2 = key_bytes[i % len(key_bytes)]
            val = b1 + b2
            sb.append(f"@{val}")

        return "".join(sb)

    @staticmethod
    def sign_and_encrypt_params(params_map, app_key):
        sorted_keys = sorted(params_map.keys())
        sb_list = []
        for key in sorted_keys:
            val = params_map[key]
            if val is not None and str(val) != "":
                sb_list.append(f"{key}={val}&")

        sb = "".join(sb_list) + app_key

        md5_hash = hashlib.md5(sb.encode("utf-8")).hexdigest().upper()
        md5_chars = list(md5_hash)

        if len(md5_chars) > 23:
            swap_chars(md5_chars, 1, 13, 5, 17, 7, 23)

        sign_str = "".join(md5_chars)

        return SignUtils.custom_encrypt(sign_str, app_key)

    @staticmethod
    def generate_tn(params_map, request_key, public_key_base64):
        encrypted_key = SignUtils.rsa_encrypt(request_key, public_key_base64)
        signed_params = SignUtils.sign_and_encrypt_params(params_map, request_key)

        return f"{encrypted_key},{signed_params}"


def generate_headers(headers: Dict[str, str], payload: Dict[str, Any], rsa_public_key: str):
    request_key = generate_random_string(16)
    sa_raw, sa_header = SignUtils.generate_sa()
    sign_map = payload.copy()
    if headers.get("token"):
        sign_map["token"] = headers["token"]
    sign_map["sa"] = sa_raw
    tn_header = SignUtils.generate_tn(sign_map, request_key, rsa_public_key)
    headers.update({"sa": sa_header, "tn": tn_header})
    return headers, payload


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

    return generate_headers(header, data, rsa_public_key)
