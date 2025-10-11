# app/services/device_service.py - デバイス管理サービス
import json
import os
import uuid
import re
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging

from app.models.device import (
    ProductCodeInfo, DeviceRegistration, DeviceRegistrationRequest,
    DeviceRegistrationResponse, DeviceValidationError, RegisteredDevice,
    DeviceCapability, DeviceStatus
)
from app.config.settings import Settings

logger = logging.getLogger(__name__)

class DeviceService:
    """デバイス管理サービス"""
    
    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
        self.devices_data_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "devices.json"
        )
        
        # 登録済みデバイス管理（メモリ内）
        self.registered_devices: Dict[str, RegisteredDevice] = {}
        
        # 製品コードマスタ読み込み
        self._load_product_codes()
        
    def _load_product_codes(self) -> None:
        """製品コードマスタデータを読み込み"""
        try:
            if os.path.exists(self.devices_data_file):
                with open(self.devices_data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.product_codes: Dict[str, ProductCodeInfo] = {}
                    
                    for code, info in data.get("devices", {}).items():
                        self.product_codes[code] = ProductCodeInfo(**info)
                    
                    self.validation_rules = data.get("validation_rules", {})
                    logger.info(f"製品コードマスタ読み込み完了: {len(self.product_codes)}件")
            else:
                logger.warning(f"製品コードマスタファイルが見つかりません: {self.devices_data_file}")
                self.product_codes = {}
                self.validation_rules = {}
                
        except Exception as e:
            logger.error(f"製品コードマスタ読み込みエラー: {e}")
            self.product_codes = {}
            self.validation_rules = {}
    
    def validate_product_code(self, product_code: str) -> Optional[DeviceValidationError]:
        """製品コードの妥当性検証"""
        
        # 基本形式チェック
        pattern = self.validation_rules.get("product_code_pattern", r"^[A-Z]{2,3}\d{3}$")
        if not re.match(pattern, product_code):
            return DeviceValidationError(
                error_code="invalid_format",
                error_message=f"製品コードの形式が無効です。形式: {pattern}",
                details={"pattern": pattern, "provided": product_code}
            )
        
        # 製品コード存在チェック
        if product_code not in self.product_codes:
            return DeviceValidationError(
                error_code="product_not_found",
                error_message="製品コードが見つかりません",
                details={"product_code": product_code}
            )
        
        # アクティブ状態チェック
        product_info = self.product_codes[product_code]
        if not product_info.is_active:
            return DeviceValidationError(
                error_code="product_inactive",
                error_message="この製品コードは無効化されています",
                details={"product_code": product_code, "device_name": product_info.device_name}
            )
        
        return None
    
    def generate_device_id(self, product_code: str) -> str:
        """デバイスIDを生成"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_part = str(uuid.uuid4()).split('-')[0]
        return f"{product_code}_{timestamp}_{unique_part}"
    
    def generate_session_token(self, device_id: str) -> str:
        """セッション認証トークンを生成"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_part = str(uuid.uuid4()).replace('-', '')
        return f"4DX_{device_id}_{timestamp}_{unique_part}"
    
    def register_device(self, request: DeviceRegistrationRequest) -> DeviceRegistrationResponse:
        """デバイスを登録"""
        
        # 製品コード検証
        validation_error = self.validate_product_code(request.product_code)
        if validation_error:
            raise ValueError(f"{validation_error.error_code}: {validation_error.error_message}")
        
        # 製品情報取得
        product_info = self.product_codes[request.product_code]
        
        # デバイスID・トークン生成
        device_id = self.generate_device_id(request.product_code)
        session_token = self.generate_session_token(device_id)
        
        # デバイス登録情報作成
        registration = DeviceRegistration(
            device_id=device_id,
            product_code=request.product_code,
            device_name=product_info.device_name,
            capabilities=product_info.capabilities,
            status=DeviceStatus.REGISTERED,
            metadata={
                "manufacturer": product_info.manufacturer,
                "model": product_info.model,
                "max_connections": product_info.max_connections,
                "client_info": request.client_info,
                "session_token": session_token
            }
        )
        
        # 登録済みデバイス管理に追加
        registered_device = RegisteredDevice(registration)
        self.registered_devices[device_id] = registered_device
        
        logger.info(f"デバイス登録完了: {device_id} ({product_info.device_name})")
        
        # WebSocketエンドポイント情報
        websocket_endpoints = {
            "device_endpoint": f"/ws/device/{{session_id}}",
            "webapp_endpoint": f"/ws/webapp/{{session_id}}",
            "legacy_endpoint": f"/ws/sessions/{{session_id}}"
        }
        
        # レスポンス作成
        return DeviceRegistrationResponse(
            device_id=device_id,
            device_name=product_info.device_name,
            capabilities=product_info.capabilities,
            status=DeviceStatus.REGISTERED,
            session_token=session_token,
            expires_in=self.validation_rules.get("session_timeout_minutes", 60) * 60,
            websocket_endpoints=websocket_endpoints
        )
    
    def get_device(self, device_id: str) -> Optional[RegisteredDevice]:
        """登録済みデバイス取得"""
        return self.registered_devices.get(device_id)
    
    def verify_device_token(self, device_id: str, token: str) -> bool:
        """デバイストークンの検証"""
        device = self.get_device(device_id)
        if not device:
            return False
            
        stored_token = device.registration.metadata.get("session_token")
        return stored_token == token
    
    def get_available_devices(self) -> List[Dict]:
        """利用可能なデバイス一覧取得"""
        available = []
        for device in self.registered_devices.values():
            if device.is_available():
                available.append(device.to_dict())
        return available
    
    def cleanup_expired_devices(self, expiry_hours: int = 24) -> int:
        """期限切れデバイスのクリーンアップ"""
        cutoff_time = datetime.now() - timedelta(hours=expiry_hours)
        expired_ids = []
        
        for device_id, device in self.registered_devices.items():
            if (device.registration.last_active and 
                device.registration.last_active < cutoff_time):
                expired_ids.append(device_id)
        
        for device_id in expired_ids:
            del self.registered_devices[device_id]
            
        if expired_ids:
            logger.info(f"期限切れデバイスクリーンアップ: {len(expired_ids)}件削除")
            
        return len(expired_ids)
    
    def get_device_statistics(self) -> Dict:
        """デバイス統計情報取得"""
        total_registered = len(self.registered_devices)
        active_devices = len([d for d in self.registered_devices.values() 
                             if d.registration.status == DeviceStatus.ACTIVE])
        available_devices = len([d for d in self.registered_devices.values() 
                               if d.is_available()])
        
        return {
            "total_registered": total_registered,
            "active_devices": active_devices,
            "available_devices": available_devices,
            "product_codes_available": len([p for p in self.product_codes.values() if p.is_active]),
            "last_cleanup": datetime.now().isoformat()
        }
    
    def get_supported_capabilities(self, product_code: str) -> List[DeviceCapability]:
        """製品コードのサポート機能取得"""
        if product_code in self.product_codes:
            return self.product_codes[product_code].capabilities
        return []
    
    def is_capability_supported(self, device_id: str, capability: DeviceCapability) -> bool:
        """デバイスが特定機能をサポートしているかチェック"""
        device = self.get_device(device_id)
        if device:
            return capability in device.registration.capabilities
        return False