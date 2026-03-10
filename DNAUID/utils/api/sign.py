import uuid
from typing import Any, Dict, Tuple

from .sign_120 import generate_headers_120
from .sign_122 import generate_headers_122

# 兜底列表，服务端动态下发时会被覆盖
SIGN_API_LIST = [
    "/user/sdkLogin",
    "/user/getSmsCode",
    "/role/defaultRoleForTool",
    "/media/av/cfg/getVideos",
    "/media/av/cfg/getAudios",
    "/media/av/cfg/getImages",
    "/encourage/signin/signin",
    "/user/refreshToken",
    "/user/signIn",
    "/user/refreshToken",
    "/role/defaultRole",
    "/role/list",
    "/role/getShortNoteInfo",
    "/forum/like",
    "/encourage/calendar/Activity/list",
]


def get_dev_code() -> str:
    return str(uuid.uuid4()).upper()


def get_signed_headers_and_body(
    url: str,
    header: Dict[str, str],
    data: Dict[str, Any],
    rsa_public_key: str,
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    if not any(url.endswith(api) for api in SIGN_API_LIST):
        return header, data

    token = header.get("token", "")
    dev_code = header.get("devCode", "")
    from .ws_manager import get_ws_manager, get_ws_wait_time

    get_ws_manager().get_connection(token, dev_code, wait_ready=True, timeout=get_ws_wait_time())

    version = header.get("version", "")
    # source = header.get("source", "")
    if version == "1.2.2":
        return generate_headers_122(header, data, rsa_public_key)
    return generate_headers_120(header, data, rsa_public_key)
