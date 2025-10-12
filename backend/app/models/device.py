"""
Device Models - Pydantic data models for device management

Defines the data structures for device registration, authentication,
and capability management in the 4DX@HOME system.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
import re

class DeviceRegistrationRequest(BaseModel):
    """デバイス登録リクエスト"""
    product_code: str = Field(
        ..., 
        min_length=5, 
        max_length=6,
        description="製品コード (例: DH001, DX123)"
    )
    
    @validator('product_code')
    def validate_product_code(cls, v):
        """製品コード形式バリデーション"""
        if not re.match(r'^[A-Z]{2,3}\d{3}$', v):
            raise ValueError('製品コードは英字2-3文字+数字3桁の形式である必要があります')
        return v.upper()

class DeviceCapability(BaseModel):
    """デバイス機能情報"""
    type: str = Field(..., description="機能タイプ")
    enabled: bool = Field(default=True, description="機能有効状態")
    parameters: Optional[dict] = Field(default=None, description="機能パラメータ")

class DeviceInfo(BaseModel):
    """デバイス基本情報"""
    product_code: str = Field(..., description="製品コード")
    device_name: str = Field(..., description="デバイス名")
    manufacturer: str = Field(..., description="製造元")
    model: str = Field(..., description="モデル名")
    capabilities: List[str] = Field(..., description="対応機能リスト")
    max_connections: int = Field(default=1, description="最大同時接続数")
    is_active: bool = Field(default=True, description="デバイス有効状態")
    description: str = Field(..., description="デバイス説明")
    price_tier: str = Field(..., description="価格帯")

class DeviceRegistrationResponse(BaseModel):
    """デバイス登録レスポンス"""
    device_id: str = Field(..., description="生成されたデバイスID")
    device_name: str = Field(..., description="デバイス名")
    capabilities: List[str] = Field(..., description="対応機能リスト")
    status: str = Field(default="registered", description="登録状態")
    registered_at: datetime = Field(default_factory=datetime.now, description="登録日時")
    session_timeout: int = Field(default=60, description="セッションタイムアウト（分）")

class DeviceError(BaseModel):
    """デバイス関連エラーレスポンス"""
    error: str = Field(..., description="エラーコード")
    message: str = Field(..., description="エラーメッセージ")
    details: Optional[dict] = Field(default=None, description="追加エラー詳細")
    timestamp: datetime = Field(default_factory=datetime.now, description="エラー発生時刻")

class DeviceSession(BaseModel):
    """デバイスセッション情報"""
    session_id: str = Field(..., description="セッションID")
    device_id: str = Field(..., description="デバイスID")
    product_code: str = Field(..., description="製品コード")
    created_at: datetime = Field(default_factory=datetime.now, description="セッション作成時刻")
    expires_at: datetime = Field(..., description="セッション有効期限")
    is_active: bool = Field(default=True, description="セッション有効状態")

# バリデーション定数
VALID_CAPABILITIES = [
    "VIBRATION",   # 振動クッション
    "WATER",       # 水しぶきスプレー
    "WIND",        # 風ファン
    "FLASH",       # フラッシュライト
    "COLOR"        # 色ライト
]

DEVICE_STATUS_CODES = {
    "registered": "登録完了",
    "invalid_code": "無効な製品コード",
    "device_inactive": "デバイス無効",
    "registration_failed": "登録失敗"
}