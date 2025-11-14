#!/usr/bin/env python3
"""
Event Mapper テストスクリプト

最新のタイムラインJSON仕様（09_json_specification.md）のイベントが
正しくMQTTコマンドにマッピングされるかをテストします。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.mqtt.event_mapper import EventToMQTTMapper


def test_water():
    """水しぶきのテスト"""
    print("\n=== Water（水しぶき）テスト ===")
    
    # shot アクション
    commands = EventToMQTTMapper.map_event_to_mqtt("water", "burst", "shot")
    assert commands == [("/4dx/water", "trigger")], f"期待: [('/4dx/water', 'trigger')], 実際: {commands}"
    print("✅ water + burst + shot → /4dx/water:trigger")


def test_wind():
    """風のテスト"""
    print("\n=== Wind（風）テスト ===")
    
    # start
    commands = EventToMQTTMapper.map_event_to_mqtt("wind", "burst", "start")
    assert commands == [("/4dx/wind", "ON")], f"期待: [('/4dx/wind', 'ON')], 実際: {commands}"
    print("✅ wind + burst + start → /4dx/wind:ON")
    
    # stop
    commands = EventToMQTTMapper.map_event_to_mqtt("wind", "burst", "stop")
    assert commands == [("/4dx/wind", "OFF")], f"期待: [('/4dx/wind', 'OFF')], 実際: {commands}"
    print("✅ wind + burst + stop → /4dx/wind:OFF")


def test_flash():
    """光のテスト"""
    print("\n=== Flash（光）テスト ===")
    
    # steady
    commands = EventToMQTTMapper.map_event_to_mqtt("flash", "steady", "start")
    assert commands == [("/4dx/light", "ON")]
    print("✅ flash + steady + start → /4dx/light:ON")
    
    # slow_blink
    commands = EventToMQTTMapper.map_event_to_mqtt("flash", "slow_blink", "start")
    assert commands == [("/4dx/light", "BLINK_SLOW")]
    print("✅ flash + slow_blink + start → /4dx/light:BLINK_SLOW")
    
    # fast_blink
    commands = EventToMQTTMapper.map_event_to_mqtt("flash", "fast_blink", "start")
    assert commands == [("/4dx/light", "BLINK_FAST")]
    print("✅ flash + fast_blink + start → /4dx/light:BLINK_FAST")
    
    # stop
    commands = EventToMQTTMapper.map_event_to_mqtt("flash", "fast_blink", "stop")
    assert commands == [("/4dx/light", "OFF")]
    print("✅ flash + fast_blink + stop → /4dx/light:OFF")


def test_color():
    """色のテスト"""
    print("\n=== Color（色）テスト ===")
    
    colors = ["red", "green", "blue", "yellow", "cyan", "purple"]
    payloads = ["RED", "GREEN", "BLUE", "YELLOW", "CYAN", "PURPLE"]
    
    for color, payload in zip(colors, payloads):
        commands = EventToMQTTMapper.map_event_to_mqtt("color", color, "start")
        assert commands == [("/4dx/color", payload)]
        print(f"✅ color + {color} + start → /4dx/color:{payload}")
    
    # stop（すべて赤に戻る）
    for color in colors:
        commands = EventToMQTTMapper.map_event_to_mqtt("color", color, "stop")
        assert commands == [("/4dx/color", "RED")]
    print("✅ color + (any) + stop → /4dx/color:RED")


def test_vibration_down():
    """振動（下: おしり）のテスト"""
    print("\n=== Vibration - 下（おしり）のみ（Motor1/ESP3）テスト ===")
    
    modes = ["down_weak", "down_mid_weak", "down_mid_strong", "down_strong"]
    payloads = ["WEAK", "MEDIUM_WEAK", "MEDIUM_STRONG", "STRONG"]
    
    for mode, payload in zip(modes, payloads):
        # start
        commands = EventToMQTTMapper.map_event_to_mqtt("vibration", mode, "start")
        assert commands == [("/4dx/motor1/control", payload)]
        print(f"✅ vibration + {mode} + start → /4dx/motor1/control:{payload}")
        
        # stop
        commands = EventToMQTTMapper.map_event_to_mqtt("vibration", mode, "stop")
        assert commands == [("/4dx/motor1/control", "OFF")]
        print(f"✅ vibration + {mode} + stop → /4dx/motor1/control:OFF")


def test_vibration_up():
    """振動（上: 背中）のテスト"""
    print("\n=== Vibration - 上（背中）のみ（Motor2/ESP4）テスト ===")
    
    modes = ["up_weak", "up_mid_weak", "up_mid_strong", "up_strong"]
    payloads = ["WEAK", "MEDIUM_WEAK", "MEDIUM_STRONG", "STRONG"]
    
    for mode, payload in zip(modes, payloads):
        # start
        commands = EventToMQTTMapper.map_event_to_mqtt("vibration", mode, "start")
        assert commands == [("/4dx/motor2/control", payload)]
        print(f"✅ vibration + {mode} + start → /4dx/motor2/control:{payload}")
        
        # stop
        commands = EventToMQTTMapper.map_event_to_mqtt("vibration", mode, "stop")
        assert commands == [("/4dx/motor2/control", "OFF")]
        print(f"✅ vibration + {mode} + stop → /4dx/motor2/control:OFF")


def test_vibration_up_down():
    """振動（上下同時）のテスト"""
    print("\n=== Vibration - 上下同時（Motor1+Motor2）テスト ===")
    
    modes = ["up_down_weak", "up_down_mid_weak", "up_down_mid_strong", "up_down_strong"]
    payloads = ["WEAK", "MEDIUM_WEAK", "MEDIUM_STRONG", "STRONG"]
    
    for mode, payload in zip(modes, payloads):
        # start
        commands = EventToMQTTMapper.map_event_to_mqtt("vibration", mode, "start")
        expected = [
            ("/4dx/motor1/control", payload),
            ("/4dx/motor2/control", payload)
        ]
        assert commands == expected
        print(f"✅ vibration + {mode} + start → Motor1:{payload}, Motor2:{payload}")
        
        # stop
        commands = EventToMQTTMapper.map_event_to_mqtt("vibration", mode, "stop")
        expected = [
            ("/4dx/motor1/control", "OFF"),
            ("/4dx/motor2/control", "OFF")
        ]
        assert commands == expected
        print(f"✅ vibration + {mode} + stop → Motor1:OFF, Motor2:OFF")


def test_vibration_special():
    """振動（特殊パターン）のテスト"""
    print("\n=== Vibration - 特殊パターン（旧仕様互換）テスト ===")
    
    # heartbeat
    commands = EventToMQTTMapper.map_event_to_mqtt("vibration", "heartbeat", "start")
    expected = [
        ("/4dx/motor1/control", "HEARTBEAT"),
        ("/4dx/motor2/control", "HEARTBEAT")
    ]
    assert commands == expected
    print("✅ vibration + heartbeat + start → Motor1:HEARTBEAT, Motor2:HEARTBEAT")
    
    # long (Rumble Slow)
    commands = EventToMQTTMapper.map_event_to_mqtt("vibration", "long", "start")
    expected = [
        ("/4dx/motor1/control", "RUMBLE_SLOW"),
        ("/4dx/motor2/control", "RUMBLE_SLOW")
    ]
    assert commands == expected
    print("✅ vibration + long + start → Motor1:RUMBLE_SLOW, Motor2:RUMBLE_SLOW")
    
    # strong
    commands = EventToMQTTMapper.map_event_to_mqtt("vibration", "strong", "start")
    expected = [
        ("/4dx/motor1/control", "STRONG"),
        ("/4dx/motor2/control", "STRONG")
    ]
    assert commands == expected
    print("✅ vibration + strong + start → Motor1:STRONG, Motor2:STRONG")


def test_all_stop():
    """全停止のテスト"""
    print("\n=== 全停止コマンドテスト ===")
    
    commands = EventToMQTTMapper.get_stop_all_commands()
    expected = [
        ("/4dx/wind", "OFF"),
        ("/4dx/light", "OFF"),
        ("/4dx/color", "RED"),
        ("/4dx/motor1/control", "OFF"),
        ("/4dx/motor2/control", "OFF"),
    ]
    
    assert commands == expected, f"期待: {expected}, 実際: {commands}"
    print(f"✅ 全停止コマンド生成成功（{len(commands)}件）")
    for topic, payload in commands:
        print(f"   - {topic} → {payload}")


def test_timeline_event():
    """タイムラインイベント処理のテスト"""
    print("\n=== タイムラインイベント処理テスト ===")
    
    # 振動イベント
    event = {
        "t": 1.5,
        "effect": "vibration",
        "mode": "down_weak",
        "action": "start"
    }
    commands = EventToMQTTMapper.process_timeline_event(event)
    assert commands == [("/4dx/motor1/control", "WEAK")]
    print("✅ タイムラインイベント処理成功（振動）")
    
    # 水しぶきイベント
    event = {
        "t": 2.0,
        "effect": "water",
        "mode": "burst",
        "action": "shot"
    }
    commands = EventToMQTTMapper.process_timeline_event(event)
    assert commands == [("/4dx/water", "trigger")]
    print("✅ タイムラインイベント処理成功（水しぶき）")


def main():
    """全テストを実行"""
    print("=" * 60)
    print("Event Mapper テスト開始")
    print("=" * 60)
    
    try:
        test_water()
        test_wind()
        test_flash()
        test_color()
        test_vibration_down()
        test_vibration_up()
        test_vibration_up_down()
        test_vibration_special()
        test_all_stop()
        test_timeline_event()
        
        print("\n" + "=" * 60)
        print("✅ 全テスト合格！")
        print("=" * 60)
        print("\n最新のタイムラインJSON仕様（09_json_specification.md）に完全対応しています。")
        print("詳細なマッピング表: TIMELINE_JSON_MAPPING.md")
        
        return 0
    
    except AssertionError as e:
        print(f"\n❌ テスト失敗: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ エラー発生: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
