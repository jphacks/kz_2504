# app/models/device.py - デバイス管理モデル
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class DeviceCapability(str, Enum):
    """デバイス機能定義"""
    VIBRATION = "VIBRATION"
    MOTION = "MOTION" 
    SCENT = "SCENT"
    AUDIO = "AUDIO"
    LIGHTING = "LIGHTING"
    WIND = "WIND"

class DeviceStatus(str, Enum):
    """デバイス状態"""
    REGISTERED = "registered"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"

class ProductCodeInfo(BaseModel):
    """製品コード情報"""
    product_code: str = Field(..., description="製品コード (例: DH001)")
    device_name: str = Field(..., description="デバイス名")
    manufacturer: str = Field(..., description="製造元")
    model: str = Field(..., description="モデル名")
    capabilities: List[DeviceCapability] = Field(..., description="サポート機能一覧")
    max_connections: int = Field(default=1, description="最大同時接続数")
    is_active: bool = Field(default=True, description="製品コードが有効かどうか")

class DeviceRegistration(BaseModel):
    """デバイス登録情報"""
    device_id: str = Field(..., description="生成されたデバイスID")
    product_code: str = Field(..., description="製品コード")
    device_name: str = Field(..., description="デバイス名")
    capabilities: List[DeviceCapability] = Field(..., description="サポート機能")
    status: DeviceStatus = Field(default=DeviceStatus.REGISTERED, description="デバイス状態")
    registered_at: datetime = Field(default_factory=datetime.now, description="登録日時")
    last_active: Optional[datetime] = Field(default=None, description="最終アクティブ日時")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="追加メタデータ")

class DeviceRegistrationRequest(BaseModel):
    """デバイス登録リクエスト"""
    product_code: str = Field(..., 
        min_length=5, 
        max_length=10,
        pattern=r'^[A-Z]{2,3}\d{3}$',
        description="製品コード (例: DH001, DX123)",
        example="DH001"
    )
    client_info: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="クライアント情報（IP、ユーザーエージェントなど）"
    )

class DeviceRegistrationResponse(BaseModel):
    """デバイス登録レスポンス"""
    device_id: str = Field(..., description="生成されたデバイスID")
    device_name: str = Field(..., description="デバイス名")
    capabilities: List[DeviceCapability] = Field(..., description="サポート機能")
    status: DeviceStatus = Field(..., description="デバイス状態")
    session_token: str = Field(..., description="セッション認証トークン")
    expires_in: int = Field(default=3600, description="トークン有効期限（秒）")
    websocket_endpoints: Dict[str, str] = Field(..., description="WebSocketエンドポイント情報")

class DeviceValidationError(BaseModel):
    """デバイス認証エラー"""
    error_code: str = Field(..., description="エラーコード")
    error_message: str = Field(..., description="エラーメッセージ")
    details: Optional[Dict[str, Any]] = Field(default=None, description="エラー詳細")

# デバイス管理用の内部クラス
class RegisteredDevice:
    """登録済みデバイス管理クラス"""
    
    def __init__(self, registration: DeviceRegistration):
        self.registration = registration
        self.current_session_id: Optional[str] = None
        self.connection_count: int = 0
        
    def update_activity(self):
        """最終アクティブ時刻を更新"""
        self.registration.last_active = datetime.now()
        
    def set_session(self, session_id: str):
        """セッションを設定"""
        self.current_session_id = session_id
        self.update_activity()
        
    def clear_session(self):
        """セッションをクリア"""
        self.current_session_id = None
        
    def increment_connection(self):
        """接続数を増加"""
        self.connection_count += 1
        
    def decrement_connection(self):
        """接続数を減少"""
        self.connection_count = max(0, self.connection_count - 1)
        
    def is_available(self) -> bool:
        """セッション参加可能かどうか"""
        return (
            self.registration.status == DeviceStatus.REGISTERED and
            self.current_session_id is None
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            **self.registration.dict(),
            "current_session_id": self.current_session_id,
            "connection_count": self.connection_count,
            "is_available": self.is_available()
        }