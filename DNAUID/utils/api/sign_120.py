import time
from typing import Any, Dict, Tuple

from .sign_utils import rand_str, xor_encode, rsa_encrypt, sign_shuffled


def _generate_sa() -> Tuple[str, str]:
    """
    生成 1.2.0 sa 参数 (30 位)
    返回 (raw_sa, header_sa)
    - 时间戳嵌入位置: 8-12, 16-20, 22-24
    - header 交换: 2↔23, 9↔17, 13↔25
    """
    random_str = rand_str(17)
    timestamp = str(int(time.time() * 1000))

    sb = []
    time_idx = rand_idx = 0
    for i in range(30):
        if (8 <= i <= 12) or (16 <= i <= 20) or (22 <= i <= 24):
            sb.append(timestamp[time_idx])
            time_idx += 1
        else:
            sb.append(random_str[rand_idx])
            rand_idx += 1

    raw_sa = "".join(sb)

    chars = list(raw_sa)
    for i, j in [(2, 23), (9, 17), (13, 25)]:
        chars[i], chars[j] = chars[j], chars[i]

    return raw_sa, "".join(chars)


def generate_headers_120(
    headers: Dict[str, str],
    payload: Dict[str, Any],
    rsa_public_key: str,
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """为 1.2.0 版本生成签名 headers (tn + sa + rk)"""
    rk: str = rand_str(16)
    raw_sa, sa_header = _generate_sa()

    sign_params = dict(payload)
    if headers.get("token"):
        sign_params["token"] = headers["token"]
    sign_params["sa"] = raw_sa

    sign_encoded = xor_encode(sign_shuffled(sign_params, rk), rk)
    tn = f"{rsa_encrypt(rk, rsa_public_key)},{sign_encoded}"

    headers.update({"rk": rk, "sa": sa_header, "tn": tn})
    return headers, payload
