"""
4DX@HOME Backend Main Application

FastAPI-based backend server for 4DX@HOME system.
Provides REST API endpoints and WebSocket communication for device management.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime
import os

# 設定管理
from app.config.settings import settings

# API ルーター  
from app.api import device_registration

# ログ設定（環境変数から）
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format
)
logger = logging.getLogger(__name__)

# FastAPIアプリケーション作成（環境変数から）
app = FastAPI(
    title=settings.app_name,
    description="4DX@HOME システムのバックエンドAPI",
    version=settings.app_version,
    docs_url="/docs" if settings.is_development() else None,  # 本番環境では無効化
    redoc_url="/redoc" if settings.is_development() else None,  # 本番環境では無効化
    debug=settings.debug
)

# CORS設定 - 環境変数から設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ヘルスチェックエンドポイント
@app.get("/", response_model=dict)
async def root():
    """
    ルートエンドポイント - システム状態確認
    """
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

# ヘルスチェック（詳細）
@app.get("/health", response_model=dict)
async def health_check():
    """
    詳細なヘルスチェック
    """
    return {
        "service": settings.app_name,
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment": settings.environment,
        "debug": settings.debug,
        "components": {
            "api": "ready",
            "websocket": "ready",
            "cors": f"{len(settings.get_cors_origins())} origins configured"
        }
    }

# APIルーター登録
app.include_router(device_registration.router)

# 動画管理APIルーター
from app.api import video_management
app.include_router(video_management.router)

# 準備処理APIルーター
from app.api import preparation
app.include_router(preparation.router)

# Phase B-3: 再生制御APIルーター
from app.api import playback_control
app.include_router(playback_control.router)

# APIバージョン情報
@app.get("/api/version", response_model=dict)
async def api_version():
    """
    API バージョン情報
    """
    return {
        "api_version": settings.app_version,
        "environment": settings.environment,
        "supported_endpoints": [
            "/",
            "/health",
            "/api/version",
            "/api/device/register",
            "/api/device/info/{product_code}",
            "/api/device/capabilities",
            "/api/videos/available",
            "/api/videos/{video_id}",
            "/api/videos/select",
            "/api/videos/categories/list",
            "/api/preparation/start/{session_id}",
            "/api/preparation/status/{session_id}",
            "/api/preparation/stop/{session_id}",
            "/api/preparation/ws/{session_id}",
            "/api/preparation/health"
        ],
        "documentation": "/docs" if settings.is_development() else "disabled"
    }

# アプリケーション起動時の処理
@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 {settings.app_name} starting up...")
    logger.info(f"🌍 Environment: {settings.environment}")
    logger.info(f"🔧 Debug mode: {settings.debug}")
    logger.info(f"🌐 CORS origins: {len(settings.get_cors_origins())} configured")
    if settings.is_development():
        logger.info("📋 API Documentation available at /docs")
    logger.info("✅ Backend initialization complete")

# アプリケーション終了時の処理
@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"🔴 {settings.app_name} shutting down...")

# 例外ハンドラー
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "予期しないエラーが発生しました"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )