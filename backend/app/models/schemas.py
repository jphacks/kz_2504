# app/models/schemas.py - 4DX@HOME データモデル定義
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

class DeviceInfo(BaseModel):
    """デバイス情報モデル"""
    version: str = Field(..., description="デバイスソフトウェアバージョン")
    ip_address: str = Field(..., description="デバイスIPアドレス")

class SessionCreateRequest(BaseModel):
    """セッション作成リクエスト"""
    product_code: str = Field(..., pattern=r"^DH\d{3}$", description="デバイス製品コード (DH001-DH999)")
    capabilities: List[str] = Field(..., description="デバイス機能リスト")
    device_info: DeviceInfo = Field(..., description="デバイス詳細情報")

class SessionResponse(BaseModel):
    """セッション作成レスポンス"""
    session_id: str = Field(..., description="生成されたセッションID")
    product_code: str = Field(..., description="デバイス製品コード")
    status: str = Field(..., description="セッション状態")
    websocket_url: str = Field(..., description="WebSocket接続URL")

class SessionInfo(BaseModel):
    """セッション情報"""
    session_id: str = Field(..., description="セッションID")
    product_code: str = Field(..., description="製品コード") 
    device_connected: bool = Field(..., description="デバイス接続状態")
    status: str = Field(..., description="セッション状態")
    websocket_url: Optional[str] = Field(None, description="WebSocket URL")

class Video(BaseModel):
    """動画情報モデル"""
    video_id: str = Field(..., description="動画ID")
    title: str = Field(..., description="動画タイトル")
    duration: float = Field(..., description="動画長(秒)")
    video_size: int = Field(..., description="ファイルサイズ(バイト)")
    video_url: Optional[str] = Field(None, description="動画URL")
    thumbnail: str = Field(..., description="サムネイル画像パス")

class SyncEvent(BaseModel):
    """同期イベントモデル"""
    time: float = Field(..., description="動画時刻(秒)")
    action: str = Field(..., description="アクション種別")
    intensity: int = Field(..., ge=0, le=100, description="強度(0-100)")
    duration: int = Field(..., description="継続時間(ms)")

class SyncData(BaseModel):
    """同期データモデル"""
    video_id: str = Field(..., description="動画ID")
    duration: float = Field(..., description="動画長(秒)")
    video_url: str = Field(..., description="動画URL")
    video_size: int = Field(..., description="ファイルサイズ")
    sync_events: List[SyncEvent] = Field(..., description="同期イベントリスト")

class WebSocketMessage(BaseModel):
    """WebSocketメッセージモデル"""
    type: str = Field(..., description="メッセージタイプ")
    data: Optional[Dict[str, Any]] = Field(None, description="メッセージデータ")
    timestamp: Optional[datetime] = Field(None, description="タイムスタンプ")

# 旧モデル（互換性のため残存）
class SessionCreate(BaseModel):
    # 旧形式 - 非推奨
    pass

class SyncMessage(BaseModel):
    # 旧形式 - 非推奨
    current_time: float
    playback_rate: float = 1.0

# セッション状態定数
class SessionStatus:
    REGISTERED = "registered"
    CONNECTED = "connected" 
    PLAYING = "playing"
    ENDED = "ended"