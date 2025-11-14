"""
クールダウン処理のバグ修正テスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from src.timeline.processor import TimelineProcessor


def test_cooldown_normal():
    """正常なクールダウン動作テスト"""
    print("=" * 60)
    print("テスト1: 正常なクールダウン動作")
    print("=" * 60)
    
    executed_events = []
    
    def callback(event):
        executed_events.append(event)
    
    processor = TimelineProcessor(on_event_callback=callback)
    processor.cooldown_durations["water"] = 3.0
    
    # タイムラインロード（水イベント3つ、1秒間隔）
    processor.load_timeline({
        "events": [
            {"t": 1.0, "effect": "water", "mode": "burst", "action": "shot"},
            {"t": 2.0, "effect": "water", "mode": "burst", "action": "shot"},
            {"t": 5.0, "effect": "water", "mode": "burst", "action": "shot"},
        ]
    })
    
    processor.start_playback()
    
    # 時刻1.0: 実行される
    processor.update_current_time(1.0)
    assert len(executed_events) == 1, f"Expected 1 event, got {len(executed_events)}"
    print("✅ 時刻1.0: イベント実行 (1/1)")
    
    # 時刻2.0: クールダウン中でスキップされる
    processor.update_current_time(2.0)
    assert len(executed_events) == 1, f"Expected 1 event (cooldown), got {len(executed_events)}"
    print("✅ 時刻2.0: クールダウン中でスキップ (1/2)")
    
    # 時刻5.0: クールダウン解除、実行される
    processor.update_current_time(5.0)
    assert len(executed_events) == 2, f"Expected 2 events, got {len(executed_events)}"
    print("✅ 時刻5.0: クールダウン解除、イベント実行 (2/2)")
    
    print("✅ テスト1 合格\n")


def test_cooldown_seek_backward():
    """シーク（巻き戻し）時のクールダウンリセットテスト"""
    print("=" * 60)
    print("テスト2: シーク（巻き戻し）時のクールダウンリセット")
    print("=" * 60)
    
    executed_events = []
    
    def callback(event):
        executed_events.append(event)
        print(f"  → イベント実行: t={event['t']}")
    
    processor = TimelineProcessor(on_event_callback=callback)
    processor.cooldown_durations["water"] = 3.0
    
    # タイムラインロード
    processor.load_timeline({
        "events": [
            {"t": 10.0, "effect": "water", "mode": "burst", "action": "shot"},
            {"t": 36.0, "effect": "water", "mode": "burst", "action": "shot"},
        ]
    })
    
    processor.start_playback()
    
    # 時刻10.0: 実行される
    print("📍 時刻10.0に移動")
    processor.update_current_time(10.0)
    assert len(executed_events) == 1, f"Expected 1 event, got {len(executed_events)}"
    print("✅ 時刻10.0: イベント実行 (1/2)")
    
    # 時刻36.0: 本来なら実行されるべき（クールダウン3秒は過ぎている）
    print("\n📍 時刻36.0に移動（26秒経過、クールダウン解除されているはず）")
    processor.update_current_time(36.0)
    assert len(executed_events) == 2, f"Expected 2 events, got {len(executed_events)}"
    print("✅ 時刻36.0: イベント実行 (2/2)")
    
    # ここで巻き戻し（120秒 → 36秒）
    print("\n📍 時刻120.0に移動してから36.0に巻き戻し（シーク）")
    processor.update_current_time(120.0)
    executed_events.clear()  # カウントリセット
    
    # 36秒に戻る（シーク）
    processor.update_current_time(36.0)
    
    # クールダウンがリセットされているので、再度実行される
    assert len(executed_events) == 1, f"Expected 1 event after seek, got {len(executed_events)}"
    print("✅ シーク後、時刻36.0: クールダウンリセットされ、イベント再実行")
    
    print("✅ テスト2 合格\n")


def test_cooldown_negative_time_diff():
    """時刻差が負の値になる場合のテスト（バグ再現）"""
    print("=" * 60)
    print("テスト3: 時刻差が負の値になるケース（バグ再現）")
    print("=" * 60)
    
    executed_events = []
    
    def callback(event):
        executed_events.append(event)
    
    processor = TimelineProcessor(on_event_callback=callback)
    processor.cooldown_durations["water"] = 3.0
    
    # バグ再現: 時刻120秒でイベント実行 → 時刻36秒に巻き戻り
    processor.load_timeline({
        "events": [
            {"t": 120.0, "effect": "water", "mode": "burst", "action": "shot"},
            {"t": 36.0, "effect": "water", "mode": "burst", "action": "shot"},
        ]
    })
    
    processor.start_playback()
    
    # 時刻120.0でイベント実行
    print("📍 時刻120.0に移動してイベント実行")
    processor.update_current_time(120.0)
    assert len(executed_events) == 1
    print(f"✅ 時刻120.0: イベント実行、last_executed={processor.effect_cooldowns.get('water', 'None')}")
    
    # 時刻36.0に巻き戻り（時刻差 = 36 - 120 = -84秒）
    print("\n📍 時刻36.0に巻き戻り（時刻差 = -84秒）")
    print("  旧バグ: 残り=3.0-(-84)=87秒 と誤計算される")
    print("  修正後: クールダウンが自動リセットされる")
    
    processor.update_current_time(36.0)
    
    # 修正後は実行される（クールダウンがリセットされる）
    assert len(executed_events) == 2, f"Expected 2 events (cooldown reset), got {len(executed_events)}"
    print("✅ 時刻36.0: クールダウンリセット後、イベント実行")
    
    print("✅ テスト3 合格（バグ修正確認）\n")


if __name__ == "__main__":
    try:
        test_cooldown_normal()
        test_cooldown_seek_backward()
        test_cooldown_negative_time_diff()
        
        print("=" * 60)
        print("🎉 全テスト合格！クールダウンバグが修正されました")
        print("=" * 60)
    
    except AssertionError as e:
        print(f"\n❌ テスト失敗: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
