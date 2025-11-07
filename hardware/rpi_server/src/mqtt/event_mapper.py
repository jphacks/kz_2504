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
    
    # 4DXHOME/mqtt_server.py の event_map を完全継承 + 最新JSON仕様対応
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
        
        # フラッシュ（最新JSON仕様対応）
        ("flash", "steady"): [
            ("/4dx/light", "ON")
        ],
        ("flash", "slow_blink"): [
            ("/4dx/light", "BLINK_SLOW")
        ],
        ("flash", "fast_blink"): [
            ("/4dx/light", "BLINK_FAST")
        ],
        # 旧仕様との互換性維持
        ("flash", "burst"): [
            ("/4dx/light", "BLINK_FAST")
        ],
        ("flash", "strobe"): [
            ("/4dx/light", "BLINK_FAST")
        ],
        
        # === (3) ESP3 / ESP4 (Motor) ===
        # 振動: 下（おしり）のみ - Motor1 (ESP3)
        ("vibration", "down_weak"): [
            ("/4dx/motor1/control", "WEAK")
        ],
        ("vibration", "down_mid_weak"): [
            ("/4dx/motor1/control", "MEDIUM_WEAK")
        ],
        ("vibration", "down_mid_strong"): [
            ("/4dx/motor1/control", "MEDIUM_STRONG")
        ],
        ("vibration", "down_strong"): [
            ("/4dx/motor1/control", "STRONG")
        ],
        
        # 振動: 上（背中）のみ - Motor2 (ESP4)
        ("vibration", "up_weak"): [
            ("/4dx/motor2/control", "WEAK")
        ],
        ("vibration", "up_mid_weak"): [
            ("/4dx/motor2/control", "MEDIUM_WEAK")
        ],
        ("vibration", "up_mid_strong"): [
            ("/4dx/motor2/control", "MEDIUM_STRONG")
        ],
        ("vibration", "up_strong"): [
            ("/4dx/motor2/control", "STRONG")
        ],
        
        # 振動: 上下同時 - Motor1 + Motor2
        ("vibration", "up_down_weak"): [
            ("/4dx/motor1/control", "WEAK"),
            ("/4dx/motor2/control", "WEAK")
        ],
        ("vibration", "up_down_mid_weak"): [
            ("/4dx/motor1/control", "MEDIUM_WEAK"),
            ("/4dx/motor2/control", "MEDIUM_WEAK")
        ],
        ("vibration", "up_down_mid_strong"): [
            ("/4dx/motor1/control", "MEDIUM_STRONG"),
            ("/4dx/motor2/control", "MEDIUM_STRONG")
        ],
        ("vibration", "up_down_strong"): [
            ("/4dx/motor1/control", "STRONG"),
            ("/4dx/motor2/control", "STRONG")
        ],
        
        # 振動: 特殊パターン（旧仕様との互換性維持）
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
    
    # 停止 (stop) アクションのマッピング（mqtt_server.py の stop_event_map + 最新JSON仕様対応）
    STOP_EVENT_MAP: Dict[Tuple[str, str], List[Tuple[str, str]]] = {
        # Wind
        ("wind", "burst"): [
            ("/4dx/wind", "OFF")
        ],
        ("wind", "long"): [
            ("/4dx/wind", "OFF")
        ],
        
        # Color（すべての色モードで同じ停止処理）
        ("color", "red"): [
            ("/4dx/color", "RED")  # LEDはOFFにせず「赤」に戻す
        ],
        ("color", "green"): [
            ("/4dx/color", "RED")
        ],
        ("color", "blue"): [
            ("/4dx/color", "RED")
        ],
        ("color", "yellow"): [
            ("/4dx/color", "RED")
        ],
        ("color", "cyan"): [
            ("/4dx/color", "RED")
        ],
        ("color", "purple"): [
            ("/4dx/color", "RED")
        ],
        
        # Flash（すべての点滅モードで同じ停止処理）
        ("flash", "steady"): [
            ("/4dx/light", "OFF")
        ],
        ("flash", "slow_blink"): [
            ("/4dx/light", "OFF")
        ],
        ("flash", "fast_blink"): [
            ("/4dx/light", "OFF")
        ],
        ("flash", "burst"): [
            ("/4dx/light", "OFF")
        ],
        ("flash", "strobe"): [
            ("/4dx/light", "OFF")
        ],
        
        # Vibration - 下（おしり）のみ: Motor1停止
        ("vibration", "down_weak"): [
            ("/4dx/motor1/control", "OFF")
        ],
        ("vibration", "down_mid_weak"): [
            ("/4dx/motor1/control", "OFF")
        ],
        ("vibration", "down_mid_strong"): [
            ("/4dx/motor1/control", "OFF")
        ],
        ("vibration", "down_strong"): [
            ("/4dx/motor1/control", "OFF")
        ],
        
        # Vibration - 上（背中）のみ: Motor2停止
        ("vibration", "up_weak"): [
            ("/4dx/motor2/control", "OFF")
        ],
        ("vibration", "up_mid_weak"): [
            ("/4dx/motor2/control", "OFF")
        ],
        ("vibration", "up_mid_strong"): [
            ("/4dx/motor2/control", "OFF")
        ],
        ("vibration", "up_strong"): [
            ("/4dx/motor2/control", "OFF")
        ],
        
        # Vibration - 上下同時: Motor1+Motor2停止
        ("vibration", "up_down_weak"): [
            ("/4dx/motor1/control", "OFF"),
            ("/4dx/motor2/control", "OFF")
        ],
        ("vibration", "up_down_mid_weak"): [
            ("/4dx/motor1/control", "OFF"),
            ("/4dx/motor2/control", "OFF")
        ],
        ("vibration", "up_down_mid_strong"): [
            ("/4dx/motor1/control", "OFF"),
            ("/4dx/motor2/control", "OFF")
        ],
        ("vibration", "up_down_strong"): [
            ("/4dx/motor1/control", "OFF"),
            ("/4dx/motor2/control", "OFF")
        ],
        
        # Vibration - 特殊パターン（旧仕様との互換性維持）
        ("vibration", "heartbeat"): [
            ("/4dx/motor1/control", "OFF"),
            ("/4dx/motor2/control", "OFF")
        ],
        ("vibration", "long"): [
            ("/4dx/motor1/control", "OFF"),
            ("/4dx/motor2/control", "OFF")
        ],
        ("vibration", "strong"): [
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
            mode: モード (burst, strong, red, down_weak, up_strong, etc.)
            action: アクション (start, stop, shot)
            
        Returns:
            [(topic, payload), ...] のリスト
        """
        key = (effect, mode)
        
        # actionがstopの場合は停止コマンドを使用
        if action == "stop":
            mqtt_commands = cls.STOP_EVENT_MAP.get(key, [])
        else:
            # action == "start" or "shot"
            mqtt_commands = cls.EVENT_MAP.get(key, [])
        
        # キャプションイベントの場合は警告を出さない（MQTTコマンドなし）
        if not mqtt_commands and action != "caption":
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

