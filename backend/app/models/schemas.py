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

# 新しい動画同期仕様対応のデータモデル

class PlaybackTimeSync(BaseModel):
    """リアルタイム再生時刻同期データ"""
    current_time: float = Field(..., description="現在の再生時刻(秒)")
    is_playing: bool = Field(..., description="再生状態(true=再生中, false=停止/一時停止)")
    playback_rate: float = Field(default=1.0, description="再生速度倍率")
    video_id: str = Field(..., description="動画ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="送信タイムスタンプ")

class SyncDataFile(BaseModel):
    """同期データファイル（待機画面時の事前送信用）"""
    video_id: str = Field(..., description="動画ID")
    video_duration: float = Field(..., description="動画長(秒)")
    sync_events: List[SyncEvent] = Field(..., description="同期イベントリスト")
    file_checksum: Optional[str] = Field(None, description="ファイルチェックサム")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")

class SyncCommand(BaseModel):
    """即座に実行する同期コマンド"""
    command_type: str = Field(..., description="コマンド種別(vibration, scent, heat, etc.)")
    intensity: int = Field(..., ge=0, le=100, description="強度(0-100)")
    duration: int = Field(..., description="継続時間(ms)")
    video_time: float = Field(..., description="動画時刻(秒)")
    timestamp: datetime = Field(default_factory=datetime.now, description="送信タイムスタンプ")

class ActuatorCommand(BaseModel):
    """アクチュエーター制御コマンド（デバイス内部処理用）"""
    command_type: str = Field(..., description="コマンド種別")
    intensity: int = Field(..., ge=0, le=100, description="強度(0-100)")
    duration: int = Field(..., description="継続時間(ms)")
    timestamp: datetime = Field(default_factory=datetime.now, description="実行タイムスタンプ")

class DeviceStatus(BaseModel):
    """デバイス状態情報"""
    device_id: str = Field(..., description="デバイスID")
    is_ready: bool = Field(..., description="準備完了状態")
    actuator_status: Dict[str, str] = Field(..., description="各アクチュエーターの状態")
    last_command_time: Optional[datetime] = Field(None, description="最後のコマンド実行時刻")
    error_message: Optional[str] = Field(None, description="エラーメッセージ")

class VideoSyncRequest(BaseModel):
    """動画同期開始リクエスト"""
    video_id: str = Field(..., description="動画ID")
    sync_data_file: SyncDataFile = Field(..., description="同期データファイル")
    user_settings: Dict[str, Any] = Field(default_factory=dict, description="ユーザー設定")

class PlaybackStatusUpdate(BaseModel):
    """再生状態更新通知"""
    session_id: str = Field(..., description="セッションID")
    status: str = Field(..., description="再生状態(waiting, playing, paused, stopped)")
    current_time: Optional[float] = Field(None, description="現在時刻(秒)")
    video_id: Optional[str] = Field(None, description="動画ID")

# セッション状態定数
class SessionStatus:
    REGISTERED = "registered"
    CONNECTED = "connected" 
    PLAYING = "playing"
    ENDED = "ended"