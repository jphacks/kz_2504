import asyncio
from typing import Dict
from starlette.websockets import WebSocket

class SessionHub:
    """
    セッションIDごとに接続中のWebSocketを管理。
    自分以外へブロードキャストするメソッドを提供。
    """
    def __init__(self) -> None:
        # sessions[session_id] = { conn_key: websocket }
        self.sessions: Dict[str, Dict[int, WebSocket]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, session_id: str, ws: WebSocket) -> str:
        await ws.accept()
        key = id(ws)
        async with self.lock:
            self.sessions.setdefault(session_id, {})[key] = ws
        return str(key)

    async def disconnect(self, session_id: str, ws: WebSocket) -> None:
        key = id(ws)
        async with self.lock:
            bucket = self.sessions.get(session_id)
            if not bucket:
                return
            bucket.pop(key, None)
            if not bucket:
                self.sessions.pop(session_id, None)

    async def broadcast(self, session_id: str, text: str, *, sender: WebSocket | None) -> None:
        """
        同じsession_idに属する“自分以外”へ送信。
        """
        async with self.lock:
            bucket = list(self.sessions.get(session_id, {}).values())

        for conn in bucket:
            if sender is not None and conn is sender:
                continue
            try:
                await conn.send_text(text)
            except Exception:
                # 送れないコネクションは閉じて掃除
                try:
                    await conn.close()
                finally:
                    await self.disconnect(session_id, conn)
