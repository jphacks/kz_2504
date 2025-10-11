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
import os

# アプリケーション設定とロギング
from app.config.settings import Settings
from app.config.logging import setup_logging
from app.api.phase1 import router as phase1_router
from app.api.device_registration import router as device_router
from app.models.session_models import session_manager
from app.websocket.manager import websocket_manager, ClientType
from app.websocket.device_handler import handle_device_message
from app.websocket.webapp_handler import handle_webapp_message

# 設定読み込み
settings = Settings()

# ロギング設定
setup_logging(
    log_level=settings.log_level,
    log_file=settings.log_file if settings.environment != "production" else None
)
logger = logging.getLogger(__name__)

# FastAPIアプリケーション作成
app = FastAPI(
    title="4DX@HOME Backend API",
    description="WebSocketベースリアルタイム体験同期システム",
    version="1.0.0",
    docs_url="/docs",  # 本番環境でもAPIドキュメント有効化
    redoc_url="/redoc"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーター登録
app.include_router(phase1_router)
app.include_router(device_router)

# Phase 2: ビデオ管理APIルーター追加
from app.api.video_management import router as video_router
app.include_router(video_router)

# 静的ファイル設定（開発環境のみ）
if settings.environment == "development":
    # アセット用静的ファイル
    if os.path.exists(settings.assets_directory):
        app.mount("/assets", StaticFiles(directory=settings.assets_directory), name="assets")

# ルートエンドポイント
@app.get("/")
async def root():
    """APIルート - 基本情報返却"""
    sessions = session_manager.get_all_sessions()
    return {
        "service": "4DX@HOME Backend API (Docker Hot Reload Test)",
        "status": "running",
        "version": "1.0.0", 
        "environment": settings.environment,
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(sessions),
        "endpoints": {
            "api_docs": "/docs",
            "sessions": "/api/sessions",
            "videos": "/api/videos",
            "health": "/api/health"
        }
    }

@app.websocket("/ws/sessions/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket接続エンドポイント（レガシー互換性維持）
    セッション別WebSocket通信を管理
    """
    # セッション存在確認
    session = session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    # WebSocket接続
    await websocket.accept()
    session_manager.add_websocket(session_id, websocket)
    
    logger.info(f"WebSocket接続: セッション {session_id} (レガシーエンドポイント)")
    
    try:
        # 接続確認メッセージ送信
        await websocket.send_json({
            "type": "connection_established",
            "session_id": session_id,
            "message": "WebSocket接続が確立されました (レガシーエンドポイント)",
            "timestamp": datetime.now().isoformat(),
            "client_type": "legacy"
        })
        
        # メッセージ受信ループ
        while True:
            # メッセージ受信
            data = await websocket.receive_text()
            message = json.loads(data)
            
            logger.info(f"WebSocketメッセージ受信: セッション {session_id}, タイプ: {message.get('type')}")
            
            # メッセージタイプ別処理
            message_type = message.get("type")
            
            if message_type == "ping":
                # ヘルスチェック
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
                
            elif message_type == "device_status":
                # デバイス状態更新
                await session_manager.broadcast_to_session(session_id, {
                    "type": "device_status_update",
                    "data": message.get("data"),
                    "timestamp": datetime.now().isoformat()
                })
                
            elif message_type == "sync_command":
                # 同期コマンド配信
                await session_manager.broadcast_to_session(session_id, {
                    "type": "sync_command",
                    "command": message.get("command"),
                    "data": message.get("data"),
                    "timestamp": datetime.now().isoformat()
                })
                
            else:
                # 未知のメッセージタイプ
                await websocket.send_json({
                    "type": "error",
                    "message": f"未対応のメッセージタイプ: {message_type}",
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket切断: セッション {session_id}")
        
    except Exception as e:
        logger.error(f"WebSocketエラー: セッション {session_id}, エラー: {e}")
        
    finally:
        # WebSocket削除
        session_manager.remove_websocket(session_id, websocket)

@app.websocket("/ws/device/{session_id}")
async def device_websocket_endpoint(websocket: WebSocket, session_id: str):
    """デバイス専用WebSocket接続エンドポイント"""
    
    # セッション存在確認
    session = session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    connection_id = await websocket_manager.connect(
        websocket, session_id, ClientType.DEVICE
    )
    
    logger.info(f"デバイスWebSocket接続: セッション {session_id}")
    
    try:
        # 接続確認メッセージ送信
        await websocket.send_json({
            "type": "connection_established",
            "client_type": "device",
            "session_id": session_id,
            "message": "デバイス制御チャネル接続確立",
            "timestamp": datetime.now().isoformat()
        })
        
        while True:
            # メッセージ受信
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # デバイス専用メッセージ処理
            await handle_device_message(session_id, message, websocket_manager)
            
    except WebSocketDisconnect:
        logger.info(f"デバイスWebSocket切断: セッション {session_id}")
        websocket_manager.disconnect(websocket)

@app.websocket("/ws/webapp/{session_id}")
async def webapp_websocket_endpoint(websocket: WebSocket, session_id: str):
    """Webアプリ専用WebSocket接続エンドポイント"""
    
    # セッション存在確認
    session = session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    connection_id = await websocket_manager.connect(
        websocket, session_id, ClientType.WEBAPP
    )
    
    logger.info(f"WebアプリWebSocket接続: セッション {session_id}")
    
    try:
        # 接続確認メッセージ送信
        await websocket.send_json({
            "type": "connection_established",
            "client_type": "webapp",
            "session_id": session_id,
            "message": "Webアプリ同期チャネル接続確立",
            "timestamp": datetime.now().isoformat()
        })
        
        while True:
            # メッセージ受信
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Webアプリ専用メッセージ処理
            await handle_webapp_message(session_id, message, websocket_manager)
            
    except WebSocketDisconnect:
        logger.info(f"WebアプリWebSocket切断: セッション {session_id}")
        websocket_manager.disconnect(websocket)

# 開発用テストページ（開発環境のみ）
if settings.environment == "development":
    @app.get("/test")
    async def websocket_test_page():
        """WebSocketテストページ（開発環境のみ）"""
        return JSONResponse({
            "message": "WebSocketテストページは削除されました",
            "alternatives": [
                "API Documentation: /docs",
                "Session WebSocket: /ws/sessions/{session_id}",
                "Device WebSocket: /ws/device/{session_id}",
                "WebApp WebSocket: /ws/webapp/{session_id}"
            ]
        })

# アプリケーション起動時処理
@app.on_event("startup")
async def startup_event():
    """アプリケーション起動処理"""
    logger.info("4DX@HOME Backend API サーバー起動")
    logger.info(f"環境: {settings.environment}")
    logger.info(f"ログレベル: {settings.log_level}")
    
    # 期限切れセッション削除（起動時クリーンアップ）
    cleaned = session_manager.cleanup_expired_sessions()
    if cleaned > 0:
        logger.info(f"期限切れセッション削除: {cleaned}件")

@app.on_event("shutdown") 
async def shutdown_event():
    """アプリケーション終了処理"""
    logger.info("4DX@HOME Backend API サーバー終了")

# アプリケーション実行
if __name__ == "__main__":
    import uvicorn
    
    # 設定に基づいて起動
    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        log_level=settings.log_level.lower(),
        reload=settings.environment == "development"
    )