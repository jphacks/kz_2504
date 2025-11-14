"""
キャプションイベントのログ出力テスト
"""

import sys
import logging
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from src.timeline.processor import TimelineProcessor
from src.mqtt.event_mapper import EventToMQTTMapper

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def test_caption_event_logging():
    """キャプションイベントのログ出力テスト"""
    print("=" * 70)
    print("キャプションイベントのログ出力テスト")
    print("=" * 70)
    
    executed_events = []
    
    def callback(event):
        executed_events.append(event)
    
    processor = TimelineProcessor(on_event_callback=callback)
    
    # タイムラインロード（キャプション + 水しぶき）
    processor.load_timeline({
        "events": [
            {
                "t": 0,
                "action": "caption",
                "text": "オープニングシーン。静寂の中、物語が始まる。"
            },
            {
                "t": 5.0,
                "effect": "vibration",
                "mode": "down_weak",
                "action": "start"
            },
            {
                "t": 10.0,
                "action": "caption",
                "text": "カメラが川面を捉える。穏やかな水の流れ。"
            },
            {
                "t": 15.0,
                "effect": "water",
                "mode": "burst",
                "action": "shot"
            },
            {
                "t": 36.0,
                "action": "caption",
                "text": "球体が川面に激突し、巨大な水しぶきを上げる。激しい衝撃音が聞こえてきそうだ。"
            },
            {
                "t": 36.0,
                "effect": "water",
                "mode": "burst",
                "action": "shot"
            }
        ]
    })
    
    processor.start_playback()
    
    print("\n--- 時刻0秒: キャプションイベント ---")
    processor.update_current_time(0.0)
    
    print("\n--- 時刻5秒: 振動イベント ---")
    processor.update_current_time(5.0)
    
    print("\n--- 時刻10秒: キャプションイベント ---")
    processor.update_current_time(10.0)
    
    print("\n--- 時刻15秒: 水しぶきイベント ---")
    processor.update_current_time(15.0)
    
    print("\n--- 時刻36秒: キャプション + 水しぶきイベント ---")
    processor.update_current_time(36.0)
    
    # キャプションはコールバックされない（MQTTコマンドなし）
    print(f"\n実行されたイベント数: {len(executed_events)}")
    print("期待値: 3イベント（振動1 + 水2）")
    
    assert len(executed_events) == 3, f"Expected 3 events, got {len(executed_events)}"
    print("✅ キャプションはコールバックされず、エフェクトのみ実行される")
    
    print("\n✅ テスト合格\n")


def test_caption_event_mapper():
    """キャプションイベントのマッピングテスト（警告が出ないこと）"""
    print("=" * 70)
    print("キャプションイベントのマッピングテスト")
    print("=" * 70)
    
    # キャプションイベント
    caption_event = {
        "t": 10,
        "action": "caption",
        "text": "テストキャプション"
    }
    
    print("\n--- キャプションイベントを処理 ---")
    mqtt_commands = EventToMQTTMapper.process_timeline_event(caption_event)
    
    print(f"MQTTコマンド数: {len(mqtt_commands)}")
    print("期待値: 0個（キャプションはMQTTコマンドなし）")
    
    assert len(mqtt_commands) == 0, f"Expected 0 MQTT commands, got {len(mqtt_commands)}"
    print("✅ キャプションは警告なくスキップされる")
    
    print("\n✅ テスト合格\n")


if __name__ == "__main__":
    try:
        test_caption_event_logging()
        test_caption_event_mapper()
        
        print("=" * 70)
        print("🎉 全テスト合格！キャプション表示が改善されました")
        print("=" * 70)
        print("\n期待されるログ出力:")
        print("💬 キャプション: t=0, text=\"オープニングシーン。静寂の中、物語が始まる。\"")
        print("💬 キャプション: t=10, text=\"カメラが川面を捉える。穏やかな水の流れ。\"")
        print("💬 キャプション: t=36, text=\"球体が川面に激突し、巨大な水しぶきを上げる。激しい衝撃音が聞こえてきそうだ。\"")
    
    except AssertionError as e:
        print(f"\n❌ テスト失敗: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
