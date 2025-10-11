# app/websocket/manager.py - WebSocket接続管理クラス
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Optional, Any
import json
import logging
import asyncio
from datetime import datetime
from enum import Enum

class ClientType(str, Enum):
    """WebSocketクライアントタイプ"""
    DEVICE = "device"
    WEBAPP = "webapp"

class ConnectionInfo:
    """接続情報クラス"""
    
    def __init__(self, websocket: WebSocket, client_type: ClientType, session_id: str):
        self.websocket = websocket
        self.client_type = client_type
        self.session_id = session_id
        self.connected_at = datetime.now()
        self.last_ping = datetime.now()
        self.is_active = True
        
    async def send_message(self, message: dict) -> bool:
        """メッセージ送信（エラーハンドリング付き）"""
        try:
            await self.websocket.send_json(message)
            return True
        except Exception as e:
            self.is_active = False
            return False
            
    def update_ping(self):
        """最終ping時刻更新"""
        self.last_ping = datetime.now()

class WebSocketManager:
    """WebSocket接続管理クラス"""
    
    def __init__(self):
        # session_id -> {client_type -> Set[ConnectionInfo]}
        self.sessions: Dict[str, Dict[ClientType, Set[ConnectionInfo]]] = {}
        # connection_id -> ConnectionInfo のマッピング
        self.connections: Dict[str, ConnectionInfo] = {}
        self.logger = logging.getLogger(__name__)
        
    def _get_connection_id(self, websocket: WebSocket) -> str:
        """WebSocketインスタンスから一意IDを生成"""
        return f"{id(websocket)}"
        
    async def connect(self, websocket: WebSocket, session_id: str, client_type: ClientType) -> str:
        """WebSocket接続処理"""
        await websocket.accept()
        
        # 接続情報作成
        connection_info = ConnectionInfo(websocket, client_type, session_id)
        connection_id = self._get_connection_id(websocket)
        
        # セッション構造初期化
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        if client_type not in self.sessions[session_id]:
            self.sessions[session_id][client_type] = set()
            
        # 接続情報登録
        self.sessions[session_id][client_type].add(connection_info)
        self.connections[connection_id] = connection_info
        
        self.logger.info(f"WebSocket接続: {client_type} -> セッション {session_id}")
        
        return connection_id
        
    def disconnect(self, websocket: WebSocket):
        """WebSocket切断処理"""
        connection_id = self._get_connection_id(websocket)
        
        if connection_id in self.connections:
            connection_info = self.connections[connection_id]
            session_id = connection_info.session_id
            client_type = connection_info.client_type
            
            # セッションから削除
            if (session_id in self.sessions and 
                client_type in self.sessions[session_id]):
                self.sessions[session_id][client_type].discard(connection_info)
                
                # 空になったらクリーンアップ
                if not self.sessions[session_id][client_type]:
                    del self.sessions[session_id][client_type]
                if not self.sessions[session_id]:
                    del self.sessions[session_id]
                    
            # 接続マップから削除
            del self.connections[connection_id]
            
            self.logger.info(f"WebSocket切断: {client_type} <- セッション {session_id}")
            
    async def send_to_session_client(self, session_id: str, client_type: ClientType, message: dict) -> int:
        """指定セッションの指定クライアントタイプに送信"""
        if (session_id not in self.sessions or 
            client_type not in self.sessions[session_id]):
            return 0
            
        sent_count = 0
        disconnected_connections = []
        
        for connection in self.sessions[session_id][client_type].copy():
            if await connection.send_message(message):
                sent_count += 1
            else:
                disconnected_connections.append(connection)
                
        # 切断されたコネクションをクリーンアップ
        for connection in disconnected_connections:
            self.disconnect(connection.websocket)
            
        return sent_count
        
    async def send_to_device(self, session_id: str, message: dict) -> int:
        """セッションのデバイスにメッセージ送信"""
        return await self.send_to_session_client(session_id, ClientType.DEVICE, message)
        
    async def send_to_webapp(self, session_id: str, message: dict) -> int:
        """セッションのWebアプリにメッセージ送信"""
        return await self.send_to_session_client(session_id, ClientType.WEBAPP, message)
        
    async def broadcast_to_session(self, session_id: str, message: dict) -> int:
        """セッション内全クライアントにブロードキャスト"""
        device_count = await self.send_to_device(session_id, message)
        webapp_count = await self.send_to_webapp(session_id, message)
        return device_count + webapp_count
        
    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """セッション接続情報取得"""
        if session_id not in self.sessions:
            return {"device_count": 0, "webapp_count": 0, "total": 0}
            
        device_count = len(self.sessions[session_id].get(ClientType.DEVICE, set()))
        webapp_count = len(self.sessions[session_id].get(ClientType.WEBAPP, set()))
        
        return {
            "device_count": device_count,
            "webapp_count": webapp_count,
            "total": device_count + webapp_count
        }
        
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """全セッション接続情報取得"""
        result = {}
        for session_id in self.sessions.keys():
            result[session_id] = self.get_session_info(session_id)
        return result
        
    async def cleanup_inactive_connections(self, timeout_minutes: int = 30):
        """非アクティブ接続のクリーンアップ"""
        current_time = datetime.now()
        disconnected_count = 0
        
        for connection_id, connection in list(self.connections.items()):
            # タイムアウトチェック
            idle_time = (current_time - connection.last_ping).total_seconds() / 60
            
            if idle_time > timeout_minutes or not connection.is_active:
                self.disconnect(connection.websocket)
                disconnected_count += 1
                
        if disconnected_count > 0:
            self.logger.info(f"非アクティブ接続削除: {disconnected_count}件")
            
        return disconnected_count
        
    async def ping_all_connections(self) -> int:
        """全接続にpingメッセージ送信"""
        ping_message = {
            "type": "ping",
            "timestamp": datetime.now().isoformat()
        }
        
        ping_count = 0
        for connection in self.connections.values():
            if await connection.send_message(ping_message):
                ping_count += 1
                
        return ping_count

# グローバルWebSocketマネージャー
websocket_manager = WebSocketManager()