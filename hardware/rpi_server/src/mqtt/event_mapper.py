"""
4DX@HOME Event to MQTT Mapper
タイムラインイベントをMQTTトピック・ペイロードにマッピング
4DXHOMEのevent_mapを継承
"""

import logging
from typing import List, Tuple, Dict, Optional

logger = logging.getLogger(__name__)


class EventToMQTTMapper:
    """イベント→MQTTコマンドマッピング
    
    重要: このマッピングは 4DXHOME/mqtt_server.py の event_map に準拠しています。
    ESP-12Eデバイスのファームウェアと互換性を保つため、勝手に変更しないでください。
    """
    
    # 4DXHOME/mqtt_server.py の event_map を完全継承
    # タプル(effect, mode)をキーとして、MQTT(topic, payload)のリストを返す
    EVENT_MAP: Dict[Tuple[str, str], List[Tuple[str, str]]] = {
        # === (1) ESP1 (Water/Wind) ===
        ("water", "burst"): [
            ("/4dx/water", "trigger")
        ],
        
        ("wind", "burst"): [
            ("/4dx/wind", "ON")
        ],
        ("wind", "long"): [
            ("/4dx/wind", "ON")
        ],
        
        # === (2) ESP2 (LED) ===
        # 色変更
        ("color", "red"): [
            ("/4dx/color", "RED")
        ],
        ("color", "green"): [
            ("/4dx/color", "GREEN")
        ],
        ("color", "blue"): [
            ("/4dx/color", "BLUE")
        ],
        ("color", "yellow"): [
            ("/4dx/color", "YELLOW")
        ],
        ("color", "cyan"): [
            ("/4dx/color", "CYAN")
        ],
        ("color", "purple"): [
            ("/4dx/color", "PURPLE")
        ],
        
        # フラッシュ
        ("flash", "steady"): [
            ("/4dx/light", "ON")
        ],
        ("flash", "burst"): [
            ("/4dx/light", "BLINK_FAST")
        ],
        ("flash", "strobe"): [
            ("/4dx/light", "BLINK_FAST")
        ],
        
        # === (3) ESP3 / ESP4 (Motor) ===
        ("vibration", "heartbeat"): [
            ("/4dx/motor1/control", "HEARTBEAT"),
            ("/4dx/motor2/control", "HEARTBEAT")
        ],
        ("vibration", "long"): [
            ("/4dx/motor1/control", "RUMBLE_SLOW"),
            ("/4dx/motor2/control", "RUMBLE_SLOW")
        ],
        ("vibration", "strong"): [
            ("/4dx/motor1/control", "STRONG"),
            ("/4dx/motor2/control", "STRONG")
        ],
    }
    
    # 停止 (stop) アクションのマッピング（mqtt_server.py の stop_event_map）
    STOP_EVENT_MAP: Dict[str, List[Tuple[str, str]]] = {
        "wind": [
            ("/4dx/wind", "OFF")
        ],
        "color": [
            ("/4dx/color", "RED")  # LEDはOFFにせず「赤」に戻す
        ],
        "flash": [
            ("/4dx/light", "OFF")
        ],
        "vibration": [
            ("/4dx/motor1/control", "OFF"),
            ("/4dx/motor2/control", "OFF")
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
            action: アクション (start, stop, shot)
            
        Returns:
            [(topic, payload), ...] のリスト
        """
        # actionがstopの場合は停止コマンドを使用（mqtt_server.pyに準拠）
        if action == "stop":
            mqtt_commands = cls.STOP_EVENT_MAP.get(effect, [])
        else:
            # action == "start" or "shot"
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
    
    @classmethod
    def get_stop_all_commands(cls) -> List[Tuple[str, str]]:
        """全アクチュエータを停止するMQTTコマンドを生成
        
        再生一時停止や動画終了時に呼び出される。
        全てのエフェクトを安全な状態（OFF）に戻す。
        
        Returns:
            [(topic, payload), ...] のリスト
        """
        stop_commands = [
            # Wind OFF
            ("/4dx/wind", "OFF"),
            
            # Flash/Light OFF
            ("/4dx/light", "OFF"),
            
            # Color を RED に戻す（LEDを完全OFFにはしない）
            ("/4dx/color", "RED"),
            
            # Motor1 OFF
            ("/4dx/motor1/control", "OFF"),
            
            # Motor2 OFF
            ("/4dx/motor2/control", "OFF"),
        ]
        
        logger.info(f"🛑 全停止MQTTコマンド生成: {len(stop_commands)}件")
        
        return stop_commands

