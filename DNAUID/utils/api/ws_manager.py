import ssl
import json
import time
import base64
import threading
from typing import Any, Optional
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
    CONNECTION_TIMEOUT = 300

    def __init__(self):
        # _pool 存储 (ws, timestamp) 元组
        self._pool: OrderedDict[tuple[str, str], tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()

    def _extract_user_id(self, token: str) -> str:
        try:
            if len(parts := token.split(".")) >= 2:
                payload = parts[1]
                if padding := len(payload) % 4:
                    payload += "=" * (4 - padding)
                if data := json.loads(base64.urlsafe_b64decode(payload)):
                    return str(data.get("userId", ""))
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

            def _remove_from_pool():
                with self._lock:
                    self._pool.pop(key, None)

            def on_message(ws, message):
                # 快速过期检查
                logger.debug(f"[DNA WebSocket] 收到消息: {message}")
                with self._lock:
                    if (item := self._pool.get(key)) and time.time() - item[1] > self.CONNECTION_TIMEOUT:
                        try:
                            ws.close()
                        except Exception:
                            pass

            def on_error(ws, error):
                _remove_from_pool()

            def on_close(ws, close_status_code, close_msg):
                _remove_from_pool()

            def on_open(ws):
                with self._lock:
                    self._pool[key] = (ws, time.time())
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
            logger.warning(f"[DNA WebSocket] 连接失败: {e}")
            return None

    def _is_expired(self, key: tuple[str, str]) -> bool:
        if not (item := self._pool.get(key)):
            return True
        return time.time() - item[1] > self.CONNECTION_TIMEOUT

    def _cleanup_connection(self, key: tuple[str, str]):
        if item := self._pool.pop(key, None):
            try:
                item[0].close()
            except Exception:
                pass

    def get_connection(self, token: str, dev_code: str) -> Optional[Any]:
        key = (token, dev_code)

        with self._lock:
            # 检查连接是否存在且有效（未过期）
            if (item := self._pool.get(key)) and time.time() - item[1] <= self.CONNECTION_TIMEOUT:
                self._pool.move_to_end(key)
                return item[0]

            # 清理当前请求的无效连接
            if key in self._pool:
                self._cleanup_connection(key)

            # 批量清理其他过期连接
            for expired_key in [k for k in self._pool if self._is_expired(k)]:
                self._cleanup_connection(expired_key)

            # LRU 淘汰：超过上限则移除最老的
            while len(self._pool) >= self.MAX_POOL_SIZE:
                self._cleanup_connection(self._pool.popitem(last=False)[0])

            # 创建新连接
            if ws := self._create_connection(token, dev_code):
                self._pool[key] = (ws, time.time())  # on_open 会更新为实际建立时间
                return ws

        return None

    def close_all(self):
        with self._lock:
            while self._pool:
                key, item = self._pool.popitem()
                try:
                    item[0].close()
                except Exception:
                    pass


# 全局单例
_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    global _ws_manager
    return _ws_manager or (_ws_manager := WebSocketManager())
