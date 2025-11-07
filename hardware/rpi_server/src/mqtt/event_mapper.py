"""
4DX@HOME Event to MQTT Mapper
タイムラインイベントをMQTTトピック・ペイロードにマッピング
4DXHOMEのevent_mapを継承
"""

import logging
from typing import List, Tuple, Dict, Optional

logger = logging.getLogger(__name__)


class EventToMQTTMapper:
    """イベント→MQTTコマンドマッピング"""
    
    # 4DXHOMEのevent_mapを継承
    # タプル(effect, mode)をキーとして、MQTT(topic, payload)のリストを返す
    EVENT_MAP: Dict[Tuple[str, str], List[Tuple[str, str]]] = {
        # === 水エフェクト ===
        ("water", "burst"): [
            ("/4dx/water", "trigger")
        ],
        ("water", "spray"): [
            ("/4dx/water", "trigger")
        ],
        
        # === 風エフェクト ===
        ("wind", "burst"): [
            ("/4dx/wind", "trigger")
        ],
        ("wind", "continuous"): [
            ("/4dx/wind", "trigger")
        ],
        
        # === 振動エフェクト（モーター制御） ===
        ("vibration", "strong"): [
            ("/4dx/motor1/control", "STRONG"),
            ("/4dx/motor2/control", "STRONG")
        ],
        ("vibration", "medium"): [
            ("/4dx/motor1/control", "MEDIUM"),
            ("/4dx/motor2/control", "MEDIUM")
        ],
        ("vibration", "weak"): [
            ("/4dx/motor1/control", "WEAK"),
            ("/4dx/motor2/control", "WEAK")
        ],
        ("vibration", "long"): [
            ("/4dx/motor1/control", "LONG"),
            ("/4dx/motor2/control", "LONG")
        ],
        ("vibration", "short"): [
            ("/4dx/motor1/control", "SHORT"),
            ("/4dx/motor2/control", "SHORT")
        ],
        
        # === フラッシュエフェクト（LED） ===
        ("flash", "burst"): [
            ("/4dx/light", "BLINK_FAST")
        ],
        ("flash", "strobe"): [
            ("/4dx/light", "BLINK_FAST")
        ],
        ("flash", "pulse"): [
            ("/4dx/light", "BLINK_SLOW")
        ],
        
        # === カラーエフェクト（LED色変更） ===
        ("color", "red"): [
            ("/4dx/color", "RED")
        ],
        ("color", "blue"): [
            ("/4dx/color", "BLUE")
        ],
        ("color", "green"): [
            ("/4dx/color", "GREEN")
        ],
        ("color", "yellow"): [
            ("/4dx/color", "YELLOW")
        ],
        ("color", "purple"): [
            ("/4dx/color", "PURPLE")
        ],
        ("color", "white"): [
            ("/4dx/color", "WHITE")
        ],
        
        # === 停止コマンド ===
        ("vibration", "stop"): [
            ("/4dx/motor1/control", "STOP"),
            ("/4dx/motor2/control", "STOP")
        ],
        ("flash", "stop"): [
            ("/4dx/light", "OFF")
        ],
        ("color", "stop"): [
            ("/4dx/color", "OFF")
        ],
    }
    
    @classmethod
    def map_event_to_mqtt(
        cls,
        effect: str,
        mode: str,
        action: str = "start"
    ) -> List[Tuple[str, str]]:
        """イベントをMQTTコマンドにマッピング
        
        Args:
            effect: エフェクト名 (water, wind, vibration, flash, color)
            mode: モード (burst, strong, red, etc.)
            action: アクション (start, stop)
            
        Returns:
            [(topic, payload), ...] のリスト
        """
        # actionがstopの場合は停止コマンドを使用
        if action == "stop":
            key = (effect, "stop")
        else:
            key = (effect, mode)
        
        mqtt_commands = cls.EVENT_MAP.get(key, [])
        
        if not mqtt_commands:
            logger.warning(
                f"未マップイベント: effect={effect}, mode={mode}, action={action}"
            )
        
        return mqtt_commands
    
    @classmethod
    def process_timeline_event(
        cls,
        event: Dict
    ) -> List[Tuple[str, str]]:
        """タイムラインイベントを処理してMQTTコマンドを生成
        
        Args:
            event: タイムラインイベント
                {
                    "t": 1.5,
                    "effect": "vibration",
                    "mode": "strong",
                    "action": "start"
                }
        
        Returns:
            [(topic, payload), ...] のリスト
        """
        effect = event.get("effect", "")
        mode = event.get("mode", "")
        action = event.get("action", "start")
        
        return cls.map_event_to_mqtt(effect, mode, action)
