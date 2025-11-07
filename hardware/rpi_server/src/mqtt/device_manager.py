"""
4DX@HOME Device Manager
ESP-12Eデバイスのステータス管理とハートビート監視
"""

import logging
import time
from typing import Dict, Optional, List
from dataclasses import dataclass
from config import Config

logger = logging.getLogger(__name__)


@dataclass
class DeviceStatus:
    """デバイスステータス情報"""
    device_id: str
    device_type: str  # water_wind, led, motor1, motor2
    is_online: bool
    last_heartbeat: float
    first_seen: float


class DeviceManager:
    """デバイス管理マネージャー"""
    
    # デバイスIDとタイプのマッピング
    DEVICE_TYPE_MAP = {
        # 旧形式（後方互換性のため維持）
        "ESP_WATER_WIND": "water_wind",
        "ESP_LED": "led",
        "ESP_MOTOR1": "motor1",
        "ESP_MOTOR2": "motor2",
        # 新形式（実際のハードウェアで使用）
        "alive_esp1_water": "water_wind",
        "alive_esp2_led": "led",
        "alive_esp3_motor1": "motor1",
        "alive_esp4_motor2": "motor2",
        "alive": "heartbeat",  # ハートビート専用メッセージ
    }
    
    def __init__(self):
        self.devices: Dict[str, DeviceStatus] = {}
        self.heartbeat_timeout = Config.HEARTBEAT_TIMEOUT
    
    def register_device(self, device_id: str) -> None:
        """デバイスをハートビートから登録
        
        Args:
            device_id: デバイスID (例: ESP_WATER_WIND)
        """
        current_time = time.time()
        
        if device_id in self.devices:
            # 既存デバイスのハートビート更新
            device = self.devices[device_id]
            device.last_heartbeat = current_time
            
            if not device.is_online:
                logger.info(f"デバイス復帰: {device_id}")
                device.is_online = True
        
        else:
            # 新規デバイス登録
            device_type = self.DEVICE_TYPE_MAP.get(device_id, "unknown")
            
            self.devices[device_id] = DeviceStatus(
                device_id=device_id,
                device_type=device_type,
                is_online=True,
                last_heartbeat=current_time,
                first_seen=current_time
            )
            
            logger.info(f"新規デバイス登録: {device_id} ({device_type})")
    
    def check_device_health(self) -> None:
        """全デバイスのヘルスチェック（タイムアウト検出）"""
        current_time = time.time()
        
        for device_id, device in self.devices.items():
            if device.is_online:
                elapsed = current_time - device.last_heartbeat
                
                if elapsed > self.heartbeat_timeout:
                    logger.warning(
                        f"デバイスタイムアウト: {device_id} "
                        f"(最終ハートビート: {elapsed:.1f}秒前)"
                    )
                    device.is_online = False
    
    def get_online_devices(self) -> List[DeviceStatus]:
        """オンラインデバイスのリストを取得"""
        return [
            device for device in self.devices.values()
            if device.is_online
        ]
    
    def get_device_status(self, device_id: str) -> Optional[DeviceStatus]:
        """特定デバイスのステータスを取得"""
        return self.devices.get(device_id)
    
    def get_all_devices(self) -> List[DeviceStatus]:
        """全デバイスのリストを取得"""
        return list(self.devices.values())
    
    def get_status_summary(self) -> Dict:
        """デバイスステータスのサマリーを取得"""
        online_count = len(self.get_online_devices())
        total_count = len(self.devices)
        
        devices_by_type = {
            "water_wind": 0,
            "led": 0,
            "motor1": 0,
            "motor2": 0,
            "unknown": 0
        }
        
        for device in self.devices.values():
            if device.is_online:
                devices_by_type[device.device_type] += 1
        
        return {
            "total_devices": total_count,
            "online_devices": online_count,
            "offline_devices": total_count - online_count,
            "devices_by_type": devices_by_type
        }
