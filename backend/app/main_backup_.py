# 4DX@HOME FastAPI Server - Main Application
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import logging
import random
import string
import os

# セットアップ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="4DX@HOME Backend",
    description="WebSocketを使用したリアルタイム同期システム",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発環境用、本番では具体的なドメインを指定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 接続管理クラス
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.sessions: Dict[str, Dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")
    
    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)
    
    async def broadcast_to_session(self, message: str, session_code: str):
        if session_code in self.sessions:
            for client_id in self.sessions[session_code].get("clients", []):
                if client_id in self.active_connections:
                    await self.active_connections[client_id].send_text(message)
    
    def create_session(self) -> str:
        """セッションコードを生成"""
        session_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.sessions[session_code] = {
            "created_at": datetime.now().isoformat(),
            "clients": [],
            "status": "waiting"
        }
        return session_code
    
    def join_session(self, session_code: str, client_id: str) -> bool:
        """セッションに参加"""
        if session_code in self.sessions:
            if client_id not in self.sessions[session_code]["clients"]:
                self.sessions[session_code]["clients"].append(client_id)
            return True
        return False

manager = ConnectionManager()

@app.get("/")
async def root():
    return {
        "message": "4DX@HOME API Server",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "active_connections": len(manager.active_connections),
        "active_sessions": len(manager.sessions)
    }

@app.post("/api/session/create")
async def create_session():
    """新しいセッションを作成"""
    session_code = manager.create_session()
    return {
        "session_code": session_code,
        "message": f"Session {session_code} created successfully"
    }

@app.get("/api/session/{session_code}")
async def get_session_info(session_code: str):
    """セッション情報を取得"""
    if session_code in manager.sessions:
        return {
            "session_code": session_code,
            "session_data": manager.sessions[session_code]
        }
    raise HTTPException(status_code=404, detail="Session not found")

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket接続エンドポイント"""
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # クライアントからのメッセージを受信
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # メッセージタイプに応じて処理
            if message_data.get("type") == "join_session":
                session_code = message_data.get("session_code")
                if manager.join_session(session_code, client_id):
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "session_joined",
                            "session_code": session_code,
                            "message": "Successfully joined session"
                        }),
                        client_id
                    )
                    # セッション内の他のクライアントに通知
                    await manager.broadcast_to_session(
                        json.dumps({
                            "type": "client_joined",
                            "client_id": client_id,
                            "message": f"Client {client_id} joined the session"
                        }),
                        session_code
                    )
                else:
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "error",
                            "message": "Session not found"
                        }),
                        client_id
                    )
            
            elif message_data.get("type") == "sync_data":
                # 同期データの処理とブロードキャスト
                session_code = message_data.get("session_code")
                if session_code:
                    await manager.broadcast_to_session(
                        json.dumps({
                            "type": "sync_data",
                            "data": message_data.get("data"),
                            "timestamp": datetime.now().isoformat(),
                            "from_client": client_id
                        }),
                        session_code
                    )
            
            else:
                # エコーバック（テスト用）
                await manager.send_personal_message(
                    json.dumps({
                        "type": "echo",
                        "message": f"Received: {data}",
                        "timestamp": datetime.now().isoformat()
                    }),
                    client_id
                )
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected")

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat()
    }

@app.get("/test")
async def websocket_test_page():
    """WebSocketテストページ"""
    test_file = os.path.join(os.path.dirname(__file__), "..", "websocket_test.html")
    if os.path.exists(test_file):
        return FileResponse(test_file)
    else:
        raise HTTPException(status_code=404, detail="Test page not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)