import ssl
import json
import time
import base64
import threading
from typing import Any, Dict, Tuple, Optional
from collections import OrderedDict

import websocket

from gsuid_core.logger import logger

from .request_util import ios_base_header


class WebSocketManager:
    """WebSocket 连接池管理器

    心跳：业务层心跳（每10秒发送 {"event": "ping", "data": {"userId": ...}}）
    """

    WS_URL = "wss://dnabbs-api.yingxiong.com:8180/ws-community-websocket"
    MAX_POOL_SIZE = 20
    HEARTBEAT_INTERVAL = 10

    def __init__(self):
        self._pool: OrderedDict[Tuple[str, str], Any] = OrderedDict()
        self._connected: Dict[Tuple[str, str], bool] = {}
        self._lock = threading.Lock()

    def _extract_user_id(self, token: str) -> str:
        try:
            parts = token.split(".")
            if len(parts) >= 2:
                payload = parts[1]
                padding = len(payload) % 4
                if padding:
                    payload += "=" * (4 - padding)
                decoded = base64.urlsafe_b64decode(payload)
                return str(json.loads(decoded).get("userId", ""))
        except Exception:
            pass
        return ""

    def _start_heartbeat(self, ws: Any, user_id: str):
        def heartbeat_loop():
            while True:
                time.sleep(self.HEARTBEAT_INTERVAL)
                try:
                    if ws.sock and ws.sock.connected:
                        ws.send(json.dumps({"event": "ping", "data": {"userId": user_id}}))
                    else:
                        break
                except Exception:
                    break

        threading.Thread(target=heartbeat_loop, daemon=True).start()

    def _create_connection(self, token: str, dev_code: str) -> Optional[Any]:
        try:
            key = (token, dev_code)
            user_id = self._extract_user_id(token)

            def on_message(ws, message):
                pass

            def on_error(ws, error):
                with self._lock:
                    self._connected[key] = False

            def on_close(ws, close_status_code, close_msg):
                with self._lock:
                    self._connected[key] = False

            def on_open(ws):
                with self._lock:
                    self._connected[key] = True
                self._start_heartbeat(ws, user_id)

            ws = websocket.WebSocketApp(
                self.WS_URL,
                header=[
                    f"{k}:{v}"
                    for k, v in {
                        "sourse": "ios",
                        "appVersion": ios_base_header.get("version", "1.2.0"),
                        "token": token,
                        "devCode": dev_code,
                    }.items()
                ],
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
            )

            threading.Thread(target=lambda: ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}), daemon=True).start()
            return ws
        except Exception as e:
            logger.warning(f"[WebSocket] 连接失败: {e}")
            return None

    def get_connection(self, token: str, dev_code: str) -> Optional[Any]:
        key = (token, dev_code)

        with self._lock:
            if key in self._pool and self._connected.get(key, False):
                self._pool.move_to_end(key)
                return self._pool[key]

            if key in self._pool:
                try:
                    self._pool[key].close()
                except Exception:
                    pass
                del self._pool[key]
                del self._connected[key]

            while len(self._pool) >= self.MAX_POOL_SIZE:
                oldest_key, oldest_ws = self._pool.popitem(last=False)
                del self._connected[oldest_key]
                try:
                    oldest_ws.close()
                except Exception:
                    pass

            self._connected[key] = False
            ws = self._create_connection(token, dev_code)
            if ws:
                self._pool[key] = ws
                return ws

        return None

    def close_all(self):
        with self._lock:
            for ws in self._pool.values():
                try:
                    ws.close()
                except Exception:
                    pass
            self._pool.clear()
            self._connected.clear()


# 全局单例
_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
