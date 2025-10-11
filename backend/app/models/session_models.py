# app/models/session_models.py - セッション管理データモデル
from typing import Dict, Set, Optional
from datetime import datetime
import asyncio

class SessionData:
    """セッションデータクラス"""
    
    def __init__(self, session_id: str, product_code: str, capabilities: list, device_info: dict):
        self.session_id = session_id
        self.product_code = product_code
        self.capabilities = capabilities
        self.device_capabilities = capabilities  # エイリアス追加
        self.device_info = device_info
        self.status = "registered"
        self.websocket = None
        self.created_at = datetime.now()
        self.connected_at: Optional[datetime] = None
        
    def set_websocket(self, websocket):
        """WebSocket接続設定"""
        self.websocket = websocket
        self.status = "connected"
        self.connected_at = datetime.now()
        
    def is_connected(self) -> bool:
        """接続状態チェック"""
        return self.websocket is not None and self.status == "connected"
        
    def disconnect(self):
        """切断処理"""
        self.websocket = None
        self.status = "ended"
        
    def to_dict(self) -> dict:
        """辞書形式で返却"""
        return {
            "session_id": self.session_id,
            "product_code": self.product_code,
            "device_connected": self.is_connected(),
            "status": self.status,
            "websocket_url": f"/ws/sessions/{self.session_id}" if self.status == "connected" else None
        }

class SessionManager:
    """セッション管理クラス"""
    
    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}
        self._websockets: Dict[str, Set] = {}
        
    def create_session(self, session_id: str, product_code: str, capabilities: list, device_info: dict) -> SessionData:
        """セッション作成"""
        session = SessionData(session_id, product_code, capabilities, device_info)
        self._sessions[session_id] = session
        return session
        
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """セッション取得"""
        return self._sessions.get(session_id)
        
    def remove_session(self, session_id: str):
        """セッション削除"""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.disconnect()
            del self._sessions[session_id]
            
    def add_websocket(self, session_id: str, websocket):
        """WebSocket追加"""
        if session_id not in self._websockets:
            self._websockets[session_id] = set()
        self._websockets[session_id].add(websocket)
        
        # セッションにWebSocket設定
        session = self.get_session(session_id)
        if session:
            session.set_websocket(websocket)
            
    def remove_websocket(self, session_id: str, websocket):
        """WebSocket削除"""
        if session_id in self._websockets:
            self._websockets[session_id].discard(websocket)
            if not self._websockets[session_id]:
                del self._websockets[session_id]
                
        # セッション切断
        session = self.get_session(session_id)
        if session:
            session.disconnect()
            
    async def broadcast_to_session(self, session_id: str, message: dict):
        """セッションへメッセージ送信"""
        if session_id in self._websockets:
            disconnected = []
            for websocket in self._websockets[session_id].copy():
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(websocket)
                    
            # 切断されたWebSocketを削除
            for websocket in disconnected:
                self.remove_websocket(session_id, websocket)
                
    def get_all_sessions(self) -> Dict[str, dict]:
        """全セッション取得"""
        return {sid: session.to_dict() for sid, session in self._sessions.items()}
        
    def cleanup_expired_sessions(self, expiry_hours: int = 24):
        """期限切れセッション削除"""
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session in self._sessions.items():
            hours_since_created = (now - session.created_at).total_seconds() / 3600
            if hours_since_created > expiry_hours:
                expired_sessions.append(session_id)
                
        for session_id in expired_sessions:
            self.remove_session(session_id)
            
        return len(expired_sessions)

# グローバルセッションマネージャー
session_manager = SessionManager()