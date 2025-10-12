"""
Preparation Models - 準備処理データモデル

動画とデバイスの準備処理状況を管理するPydanticモデル
新しいアクチュエータ定義（振動クッション、水しぶきスプレー、風ファン、フラッシュライト、色ライト）に対応
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ActuatorType(str, Enum):
    """アクチュエータタイプ（統一版）"""
    VIBRATION = "VIBRATION"  # 振動クッション
    WATER = "WATER"          # 水しぶきスプレー
    WIND = "WIND"            # 風ファン
    FLASH = "FLASH"          # フラッシュライト
    COLOR = "COLOR"          # 色ライト

class PreparationStatus(str, Enum):
    """準備処理状況"""
    NOT_STARTED = "not_started"    # 未開始
    INITIALIZING = "initializing"  # 初期化中
    IN_PROGRESS = "in_progress"    # 進行中
    TESTING = "testing"            # テスト中
    COMPLETED = "completed"        # 完了
    FAILED = "failed"              # 失敗
    TIMEOUT = "timeout"            # タイムアウト

class ActuatorTestStatus(str, Enum):
    """アクチュエーターテスト状況"""
    PENDING = "pending"        # 待機中
    TESTING = "testing"        # テスト中
    READY = "ready"           # 準備完了
    FAILED = "failed"         # テスト失敗
    TIMEOUT = "timeout"       # タイムアウト
    UNAVAILABLE = "unavailable"  # 利用不可

class ActuatorTestResult(BaseModel):
    """アクチュエーターテスト結果"""
    actuator_type: ActuatorType = Field(..., description="アクチュエータタイプ")
    status: ActuatorTestStatus = Field(..., description="テスト状況")
    response_time_ms: Optional[int] = Field(default=None, description="応答時間（ミリ秒）")
    test_intensity: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="テスト強度")
    error_message: Optional[str] = Field(default=None, description="エラーメッセージ")
    tested_at: Optional[datetime] = Field(default=None, description="テスト実行時刻")
    
    # アクチュエータ固有情報
    vibration_frequency: Optional[float] = Field(default=None, description="振動周波数（Hz）")
    water_pressure: Optional[float] = Field(default=None, description="水圧レベル")
    wind_speed: Optional[float] = Field(default=None, description="風速レベル")
    flash_brightness: Optional[float] = Field(default=None, description="フラッシュ明度")
    color_accuracy: Optional[float] = Field(default=None, description="色再現精度")

class VideoPreparationInfo(BaseModel):
    """動画準備情報"""
    video_id: str = Field(..., description="動画ID")
    video_url: str = Field(..., description="動画URL")
    file_size_mb: float = Field(..., description="ファイルサイズ（MB）")
    duration_seconds: float = Field(..., description="動画時間（秒）")
    preload_progress: int = Field(default=0, ge=0, le=100, description="プリロード進捗（%）")
    preload_status: PreparationStatus = Field(default=PreparationStatus.NOT_STARTED, description="プリロード状況")

class SyncDataTransmissionResult(BaseModel):
    """同期データ送信結果"""
    transmitted: bool = Field(default=False, description="送信成功フラグ")
    device_hub_url: Optional[str] = Field(default=None, description="送信先デバイスハブURL")
    transmission_size_kb: Optional[float] = Field(default=None, description="送信データサイズ（KB）")
    supported_events: Optional[int] = Field(default=None, description="対応済みエフェクト数")
    unsupported_events: Optional[int] = Field(default=None, description="非対応エフェクト数")
    transmission_timestamp: Optional[datetime] = Field(default=None, description="送信完了時刻")
    checksum: Optional[str] = Field(default=None, description="送信データチェックサム")
    error_message: Optional[str] = Field(default=None, description="送信エラーメッセージ")

class SyncDataPreparationInfo(BaseModel):
    """同期データ準備情報"""
    sync_data_url: str = Field(..., description="同期データURL")
    file_size_kb: float = Field(..., description="ファイルサイズ（KB）")
    effects_count: int = Field(..., description="エフェクト総数")
    required_actuators: List[ActuatorType] = Field(..., description="必要なアクチュエータ")
    download_progress: int = Field(default=0, ge=0, le=100, description="ダウンロード進捗（%）")
    parsing_progress: int = Field(default=0, ge=0, le=100, description="解析進捗（%）")
    preparation_status: PreparationStatus = Field(default=PreparationStatus.NOT_STARTED, description="準備状況")
    transmission_result: Optional[SyncDataTransmissionResult] = Field(default=None, description="デバイスハブ送信結果")

class DeviceCommunicationInfo(BaseModel):
    """デバイス通信情報"""
    device_id: str = Field(..., description="デバイスID")
    device_name: str = Field(..., description="デバイス名")
    connection_status: PreparationStatus = Field(default=PreparationStatus.NOT_STARTED, description="接続状況")
    websocket_connected: bool = Field(default=False, description="WebSocket接続状況")
    last_ping_ms: Optional[int] = Field(default=None, description="最新ping応答時間（ms）")
    supported_actuators: List[ActuatorType] = Field(..., description="対応アクチュエータ")
    actuator_tests: Dict[str, ActuatorTestResult] = Field(default_factory=dict, description="アクチュエーターテスト結果")

class PreparationState(BaseModel):
    """準備処理統合状態"""
    session_id: str = Field(..., description="セッションID")
    overall_status: PreparationStatus = Field(default=PreparationStatus.NOT_STARTED, description="全体状況")
    overall_progress: int = Field(default=0, ge=0, le=100, description="全体進捗（%）")
    
    # 各コンポーネントの準備情報
    video_preparation: VideoPreparationInfo = Field(..., description="動画準備情報")
    sync_data_preparation: SyncDataPreparationInfo = Field(..., description="同期データ準備情報")
    device_communication: DeviceCommunicationInfo = Field(..., description="デバイス通信情報")
    
    # タイムスタンプ
    started_at: datetime = Field(default_factory=datetime.now, description="準備開始時刻")
    completed_at: Optional[datetime] = Field(default=None, description="準備完了時刻")
    estimated_completion_time: Optional[datetime] = Field(default=None, description="完了予定時刻")
    
    # 準備完了条件
    ready_for_playback: bool = Field(default=False, description="再生準備完了フラグ")
    min_required_actuators_ready: bool = Field(default=False, description="最小要件アクチュエータ準備完了")
    all_actuators_ready: bool = Field(default=False, description="全アクチュエータ準備完了")

class PreparationProgress(BaseModel):
    """準備進捗通知"""
    session_id: str = Field(..., description="セッションID")
    component: str = Field(..., description="進捗コンポーネント")  # video, sync_data, device, actuator_{type}
    progress: int = Field(..., ge=0, le=100, description="進捗（%）")
    status: PreparationStatus = Field(..., description="状況")
    message: Optional[str] = Field(default=None, description="進捗メッセージ")
    timestamp: datetime = Field(default_factory=datetime.now, description="通知時刻")

class PreparationRequest(BaseModel):
    """準備処理開始リクエスト"""
    session_id: str = Field(..., description="セッションID")
    video_id: str = Field(..., description="動画ID")
    device_id: str = Field(..., description="デバイスID")
    force_restart: bool = Field(default=False, description="強制再開始")
    test_all_actuators: bool = Field(default=True, description="全アクチュエータテスト実行")

class ActuatorTestRequest(BaseModel):
    """アクチュエーターテストリクエスト"""
    session_id: str = Field(..., description="セッションID")
    actuator_types: List[ActuatorType] = Field(..., description="テスト対象アクチュエータ")
    test_intensity: float = Field(default=0.8, ge=0.1, le=1.0, description="テスト強度")
    test_duration_ms: int = Field(default=2000, ge=500, le=5000, description="テスト時間（ms）")
    timeout_ms: int = Field(default=3000, ge=1000, le=10000, description="タイムアウト（ms）")

class PreparationResponse(BaseModel):
    """準備処理レスポンス"""
    session_id: str = Field(..., description="セッションID")
    preparation_started: bool = Field(..., description="準備開始成功")
    estimated_completion_seconds: int = Field(..., description="完了予定時間（秒）")
    websocket_url: str = Field(..., description="進捗通知WebSocketURL")
    components_to_prepare: List[str] = Field(..., description="準備対象コンポーネント")

class PreparationError(BaseModel):
    """準備処理エラー"""
    error_code: str = Field(..., description="エラーコード")
    error_message: str = Field(..., description="エラーメッセージ")
    component: Optional[str] = Field(default=None, description="エラー発生コンポーネント")
    actuator_type: Optional[ActuatorType] = Field(default=None, description="エラー発生アクチュエータ")
    retry_possible: bool = Field(default=True, description="リトライ可能フラグ")
    timestamp: datetime = Field(default_factory=datetime.now, description="エラー発生時刻")

# 定数定義
ACTUATOR_TEST_DEFAULTS = {
    ActuatorType.VIBRATION: {
        "test_duration": 2000,
        "test_intensity": 0.8,
        "timeout": 1000,
        "expected_response_time": 500
    },
    ActuatorType.WATER: {
        "test_duration": 1000,
        "test_intensity": 0.6,
        "timeout": 1500,
        "expected_response_time": 800
    },
    ActuatorType.WIND: {
        "test_duration": 3000,
        "test_intensity": 0.7,
        "timeout": 800,
        "expected_response_time": 600
    },
    ActuatorType.FLASH: {
        "test_duration": 500,
        "test_intensity": 1.0,
        "timeout": 500,
        "expected_response_time": 200
    },
    ActuatorType.COLOR: {
        "test_duration": 2000,
        "test_intensity": 0.9,
        "timeout": 600,
        "expected_response_time": 300
    }
}

PREPARATION_PHASES = [
    "video_preload",       # 動画プリロード
    "sync_data_download",  # 同期データダウンロード
    "device_connection",   # デバイス接続確認
    "actuator_detection",  # アクチュエータ検出
    "actuator_testing",    # アクチュエータテスト
    "final_validation"     # 最終検証
]