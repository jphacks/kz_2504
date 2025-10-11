# test_video_playback_integration.py - 動画再生機能統合テスト
import asyncio
import websockets
import json
import requests
from datetime import datetime
import time

BASE_URL = "http://localhost:8001"

def create_test_session():
    """テスト用セッション作成"""
    response = requests.post(f"{BASE_URL}/api/sessions", json={
        "product_code": "DH001",
        "capabilities": ["motion", "vibration", "scent", "audio"],
        "device_info": {
            "version": "1.0.0",
            "ip_address": "192.168.1.100"
        }
    })
    if response.status_code == 200:
        return response.json()["session_id"]
    else:
        print(f"セッション作成失敗: {response.status_code} - {response.text}")
        return None

async def test_device_connection(session_id):
    """デバイス接続テスト"""
    uri = f"ws://localhost:8001/ws/device/{session_id}"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ デバイス接続成功")
            
            # 接続確認メッセージ受信
            welcome_msg = await websocket.recv()
            welcome_data = json.loads(welcome_msg)
            print(f"📨 デバイス接続確認: {welcome_data.get('message')}")
            
            # デバイス準備完了通知
            await websocket.send(json.dumps({
                "type": "device_ready",
                "device_info": {
                    "device_id": "test_device_4dx",
                    "capabilities": ["motion", "vibration", "scent"],
                    "version": "1.0.0"
                }
            }))
            print("📤 デバイス準備完了送信")
            
            return websocket
            
    except Exception as e:
        print(f"❌ デバイス接続エラー: {e}")
        return None

async def test_webapp_playback(session_id, device_ws):
    """Webアプリ再生制御テスト"""
    uri = f"ws://localhost:8001/ws/webapp/{session_id}"
    
    try:
        async with websockets.connect(uri) as webapp_ws:
            print("✅ Webアプリ接続成功")
            
            # 接続確認
            welcome_msg = await webapp_ws.recv()
            welcome_data = json.loads(welcome_msg)
            print(f"📨 Webアプリ接続確認: {welcome_data.get('message')}")
            
            # 再生開始
            await webapp_ws.send(json.dumps({
                "type": "start_playback",
                "video_id": "demo1",
                "user_settings": {
                    "vibration_intensity": 0.8,
                    "motion_intensity": 0.9,
                    "scent_intensity": 0.6,
                    "vibration_enabled": True,
                    "motion_enabled": True,
                    "scent_enabled": True
                }
            }))
            print("📤 再生開始コマンド送信")
            
            # 再生開始応答受信
            start_response = await webapp_ws.recv()
            start_data = json.loads(start_response)
            print(f"📨 再生開始応答: {start_data.get('type')} - {start_data.get('message')}")
            
            if start_data.get('type') == 'playback_started':
                print(f"🎬 同期イベント数: {start_data.get('sync_events_count')}")
                return webapp_ws, True
            else:
                print(f"❌ 再生開始失敗: {start_data}")
                return webapp_ws, False
                
    except Exception as e:
        print(f"❌ Webアプリテストエラー: {e}")
        return None, False

async def test_realtime_sync(webapp_ws, device_ws, video_duration=120.0):
    """リアルタイム同期テスト"""
    print("\n🎯 リアルタイム同期テスト開始")
    
    # 同期タイムスタンプリスト（demo1の重要な同期ポイント）
    sync_points = [5.0, 12.5, 18.2, 25.8, 32.1, 41.5, 48.3, 55.7, 62.4, 69.9, 77.2, 84.6, 91.3, 98.8, 105.5, 112.1]
    
    device_commands_received = 0
    webapp_acks_received = 0
    
    try:
        for i, sync_time in enumerate(sync_points[:8]):  # 最初の8個をテスト
            print(f"\n⏰ 同期テスト {i+1}/8: 時刻 {sync_time}秒")
            
            # Webアプリから同期メッセージ送信
            await webapp_ws.send(json.dumps({
                "type": "playback_sync",
                "current_time": sync_time,
                "video_id": "demo1"
            }))
            
            # Webアプリからの同期確認応答を受信
            try:
                webapp_response = await asyncio.wait_for(webapp_ws.recv(), timeout=2.0)
                webapp_data = json.loads(webapp_response)
                if webapp_data.get('type') == 'sync_acknowledged':
                    webapp_acks_received += 1
                    events_sent = webapp_data.get('events_sent', 0)
                    print(f"✅ Webapp同期確認: {events_sent}個のイベント送信")
                else:
                    print(f"⚠️ Webapp応答: {webapp_data.get('type')}")
            except asyncio.TimeoutError:
                print("⚠️ Webapp応答タイムアウト")
            
            # デバイスからのコマンド受信を試行
            try:
                device_response = await asyncio.wait_for(device_ws.recv(), timeout=1.0)
                device_data = json.loads(device_response)
                if device_data.get('type') == 'effect_command':
                    device_commands_received += 1
                    action = device_data.get('action')
                    intensity = device_data.get('intensity')
                    print(f"🎮 デバイスコマンド受信: {action} (強度: {intensity})")
                    
                    # デバイスからコマンド実行確認を返送
                    await device_ws.send(json.dumps({
                        "type": "effect_status",
                        "effect_id": device_data.get('effect_id'),
                        "status": "completed"
                    }))
                else:
                    print(f"📨 デバイス他メッセージ: {device_data.get('type')}")
            except asyncio.TimeoutError:
                print("⚠️ デバイスコマンドタイムアウト")
            
            # 少し待機
            await asyncio.sleep(0.5)
            
        print(f"\n📊 同期テスト結果:")
        print(f"  - Webapp同期確認: {webapp_acks_received}/{len(sync_points[:8])}")
        print(f"  - デバイスコマンド受信: {device_commands_received}")
        
        return webapp_acks_received, device_commands_received
        
    except Exception as e:
        print(f"❌ 同期テストエラー: {e}")
        return 0, 0

async def test_playback_end(webapp_ws, device_ws):
    """再生終了テスト"""
    print("\n🛑 再生終了テスト")
    
    try:
        # 再生終了コマンド
        await webapp_ws.send(json.dumps({
            "type": "end_playback",
            "video_id": "demo1"
        }))
        print("📤 再生終了コマンド送信")
        
        # 終了応答受信
        end_response = await asyncio.wait_for(webapp_ws.recv(), timeout=3.0)
        end_data = json.loads(end_response)
        
        if end_data.get('type') == 'playback_ended':
            print("✅ 再生終了確認")
            return True
        else:
            print(f"❌ 再生終了失敗: {end_data}")
            return False
            
    except Exception as e:
        print(f"❌ 再生終了テストエラー: {e}")
        return False

async def main():
    """メイン統合テスト実行"""
    print("🎬 動画再生機能 統合テスト開始")
    print("=" * 50)
    
    # 1. セッション作成
    session_id = create_test_session()
    if not session_id:
        print("❌ テスト失敗: セッション作成できません")
        return
        
    print(f"✅ テストセッション作成: {session_id}")
    
    # 2. デバイス接続
    device_ws = await test_device_connection(session_id)
    if not device_ws:
        print("❌ テスト失敗: デバイス接続できません")
        return
    
    try:
        # 3. Webアプリ再生開始
        webapp_ws, playback_started = await test_webapp_playback(session_id, device_ws)
        if not playback_started:
            print("❌ テスト失敗: 再生開始できません")
            return
            
        try:
            # 4. リアルタイム同期テスト
            webapp_acks, device_commands = await test_realtime_sync(webapp_ws, device_ws)
            
            # 5. 再生終了テスト
            playback_ended = await test_playback_end(webapp_ws, device_ws)
            
            # 結果サマリー
            print("\n" + "=" * 50)
            print("📊 統合テスト結果サマリー:")
            print(f"  ✅ セッション作成: 成功")
            print(f"  ✅ デバイス接続: 成功")
            print(f"  ✅ 再生開始: 成功") 
            print(f"  📡 Webapp同期応答: {webapp_acks}/8")
            print(f"  🎮 デバイスコマンド: {device_commands}")
            print(f"  🛑 再生終了: {'成功' if playback_ended else '失敗'}")
            
            # 成功基準
            success_criteria = [
                webapp_acks >= 6,  # 8回中6回以上同期成功
                device_commands >= 4,  # 4回以上デバイスコマンド受信
                playback_ended  # 再生終了成功
            ]
            
            if all(success_criteria):
                print("\n🎉 動画再生機能統合テスト: 全体的に成功！")
            else:
                print("\n⚠️ 動画再生機能統合テスト: 一部課題あり")
                
        finally:
            if webapp_ws:
                await webapp_ws.close()
                
    finally:
        if device_ws:
            await device_ws.close()

if __name__ == "__main__":
    asyncio.run(main())