"""
4DX@HOME Cloud Run WebSocket Client
Cloud Run APIとのWebSocket接続を管理し、タイムラインデータを受信
"""

import asyncio
import logging
import json
import websockets
from typing import Optional, Callable, Dict, Any
from config import Config

logger = logging.getLogger(__name__)


class CloudRunWebSocketClient:
    """Cloud Run APIへのWebSocketクライアント"""
    
    def __init__(
        self,
        session_id: str,
        on_message_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.session_id = session_id
        self.on_message_callback = on_message_callback
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected: bool = False
        self.reconnect_task: Optional[asyncio.Task] = None
        self.ping_task: Optional[asyncio.Task] = None
        self._stop_requested: bool = False
    
    async def connect(self) -> None:
        """WebSocketサーバーに接続"""
        ws_url = Config.get_websocket_url(self.session_id)
        
        logger.info(f"WebSocket接続開始: {ws_url}")
        
        try:
            self.websocket = await websockets.connect(
                ws_url,
                ping_interval=Config.WS_PING_INTERVAL,
                ping_timeout=10,
                close_timeout=5
            )
            
            self.is_connected = True
            logger.info("WebSocket接続成功")
            
            # Ping送信タスクを開始
            self.ping_task = asyncio.create_task(self._ping_loop())
            
        except Exception as e:
            logger.error(f"WebSocket接続エラー: {e}", exc_info=True)
            self.is_connected = False
            raise
    
    async def disconnect(self) -> None:
        """WebSocket接続を切断"""
        self._stop_requested = True
        
        # Pingタスクをキャンセル
        if self.ping_task and not self.ping_task.done():
            self.ping_task.cancel()
            try:
                await self.ping_task
            except asyncio.CancelledError:
                pass
        
        # WebSocket切断
        if self.websocket and not self.websocket.closed:
            logger.info("WebSocket切断開始")
            await self.websocket.close()
            self.is_connected = False
            logger.info("WebSocket切断完了")
    
    async def send_message(self, message: Dict[str, Any]) -> None:
        """メッセージを送信
        
        Args:
            message: 送信するメッセージ（dict形式）
        """
        if not self.is_connected or not self.websocket:
            logger.warning("WebSocket未接続のため送信スキップ")
            return
        
        try:
            message_json = json.dumps(message)
            await self.websocket.send(message_json)
            logger.debug(f"WebSocket送信: {message.get('type', 'unknown')}")
        
        except Exception as e:
            logger.error(f"WebSocket送信エラー: {e}", exc_info=True)
    
    async def receive_loop(self) -> None:
        """メッセージ受信ループ"""
        if not self.websocket:
            logger.error("WebSocketが初期化されていません")
            return
        
        logger.info("WebSocket受信ループ開始")
        
        try:
            async for message in self.websocket:
                if self._stop_requested:
                    break
                
                try:
                    data = json.loads(message)
                    message_type = data.get("type", "unknown")
                    
                    logger.debug(f"WebSocket受信: type={message_type}")
                    
                    # コールバック実行
                    if self.on_message_callback:
                        self.on_message_callback(data)
                
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析エラー: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"メッセージ処理エラー: {e}", exc_info=True)
        
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"WebSocket接続切断: code={e.code}, reason={e.reason}")
            self.is_connected = False
        
        except Exception as e:
            logger.error(f"WebSocket受信ループエラー: {e}", exc_info=True)
            self.is_connected = False
        
        finally:
            logger.info("WebSocket受信ループ終了")
    
    async def start_with_reconnect(self) -> None:
        """自動再接続機能付きで接続・受信ループを開始"""
        attempt = 0
        max_attempts = Config.WS_MAX_RECONNECT_ATTEMPTS
        
        while not self._stop_requested:
            try:
                # 接続
                await self.connect()
                
                # 受信ループ
                await self.receive_loop()
                
                # 正常終了の場合はループを抜ける
                if self._stop_requested:
                    break
            
            except Exception as e:
                logger.error(f"WebSocketエラー: {e}", exc_info=True)
            
            # 再接続判定
            attempt += 1
            
            if max_attempts > 0 and attempt >= max_attempts:
                logger.error(f"最大再接続回数に到達: {max_attempts}")
                break
            
            if not self._stop_requested:
                logger.info(
                    f"WebSocket再接続待機: {Config.WS_RECONNECT_DELAY}秒後 "
                    f"(試行回数: {attempt})"
                )
                await asyncio.sleep(Config.WS_RECONNECT_DELAY)
    
    async def _ping_loop(self) -> None:
        """定期的にpingメッセージを送信"""
        try:
            while not self._stop_requested and self.is_connected:
                await asyncio.sleep(Config.WS_PING_INTERVAL)
                
                if self.is_connected:
                    await self.send_message({
                        "type": "ping",
                        "device_id": Config.DEVICE_HUB_ID,
                        "timestamp": asyncio.get_event_loop().time()
                    })
        
        except asyncio.CancelledError:
            logger.debug("Pingループがキャンセルされました")
        except Exception as e:
            logger.error(f"Pingループエラー: {e}", exc_info=True)
