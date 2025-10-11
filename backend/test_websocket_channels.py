# test_websocket_channels.py - WebSocketチャネル分離テスト
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
        "capabilities": ["motion", "audio", "haptic", "scent"],
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

async def test_device_channel(session_id):
    """デバイスチャネルテスト"""
    uri = f"ws://localhost:8001/ws/device/{session_id}"
    
    print(f"🔧 デバイスチャネル接続テスト: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ デバイスチャネル接続成功")
            
            # 接続確認メッセージ受信
            welcome_msg = await websocket.recv()
            welcome_data = json.loads(welcome_msg)
            print(f"📨 接続確認: {welcome_data.get('message')}")
            
            # デバイス準備完了メッセージ送信
            device_ready_msg = {
                "type": "device_ready",
                "device_info": {
                    "device_id": "test_device_001",
                    "capabilities": ["motion", "audio", "haptic"],
                    "version": "1.0.0"
                }
            }
            await websocket.send(json.dumps(device_ready_msg))
            print("📤 デバイス準備完了メッセージ送信")
            
            # Ping送信
            ping_msg = {"type": "ping", "timestamp": datetime.now().isoformat()}
            await websocket.send(json.dumps(ping_msg))
            print("📤 Ping送信")
            
            # 応答受信（最大3秒）
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                response_data = json.loads(response)
                print(f"📨 デバイス応答: {response_data.get('type')}")
            except asyncio.TimeoutError:
                print("⚠️  デバイス応答タイムアウト")
            
            return True
            
    except Exception as e:
        print(f"❌ デバイスチャネルエラー: {e}")
        return False

async def test_webapp_channel(session_id):
    """Webアプリチャネルテスト"""
    uri = f"ws://localhost:8001/ws/webapp/{session_id}"
    
    print(f"🌐 Webアプリチャネル接続テスト: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Webアプリチャネル接続成功")
            
            # 接続確認メッセージ受信
            welcome_msg = await websocket.recv()
            welcome_data = json.loads(welcome_msg)
            print(f"📨 接続確認: {welcome_data.get('message')}")
            
            # 再生開始メッセージ送信
            start_playback_msg = {
                "type": "start_playback",
                "video_id": "sample_video_001",
                "user_preferences": {
                    "motion_intensity": 0.8,
                    "audio_enabled": True
                }
            }
            await websocket.send(json.dumps(start_playback_msg))
            print("📤 再生開始メッセージ送信")
            
            # Ping送信
            ping_msg = {"type": "ping", "timestamp": datetime.now().isoformat()}
            await websocket.send(json.dumps(ping_msg))
            print("📤 Ping送信")
            
            # 応答受信（最大3秒）
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                response_data = json.loads(response)
                print(f"📨 Webアプリ応答: {response_data.get('type')}")
            except asyncio.TimeoutError:
                print("⚠️  Webアプリ応答タイムアウト")
            
            return True
            
    except Exception as e:
        print(f"❌ Webアプリチャネルエラー: {e}")
        return False

async def test_legacy_channel(session_id):
    """レガシーチャネルテスト（後方互換性確認）"""
    uri = f"ws://localhost:8001/ws/sessions/{session_id}"
    
    print(f"🔄 レガシーチャネル接続テスト: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ レガシーチャネル接続成功")
            
            # 接続確認メッセージ受信
            welcome_msg = await websocket.recv()
            welcome_data = json.loads(welcome_msg)
            print(f"📨 接続確認: {welcome_data.get('message')}")
            print(f"🏷️  クライアントタイプ: {welcome_data.get('client_type', 'N/A')}")
            
            # テストメッセージ送信
            test_msg = {
                "type": "ping",
                "message": "レガシーエンドポイントテスト",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(test_msg))
            print("📤 テストメッセージ送信")
            
            # 応答受信
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                response_data = json.loads(response)
                print(f"📨 レガシー応答: {response_data.get('type')}")
            except asyncio.TimeoutError:
                print("⚠️  レガシー応答タイムアウト")
                
            return True
            
    except Exception as e:
        print(f"❌ レガシーチャネルエラー: {e}")
        return False

async def test_concurrent_connections(session_id):
    """同時接続テスト"""
    print(f"🔗 同時接続テスト開始: セッション {session_id}")
    
    # 複数チャネル同時接続
    tasks = [
        test_device_channel(session_id),
        test_webapp_channel(session_id),
        test_legacy_channel(session_id)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for result in results if result is True)
    print(f"📊 同時接続テスト結果: {success_count}/3 成功")
    
    return success_count == 3

def main():
    """メインテスト実行"""
    print("🚀 WebSocketチャネル分離テスト開始")
    print("=" * 50)
    
    # 1. セッション作成
    session_id = create_test_session()
    if not session_id:
        print("❌ テスト失敗: セッション作成できません")
        return
        
    print(f"✅ テストセッション作成: {session_id}")
    print()
    
    # 2. 個別チャネルテスト
    async def run_tests():
        tests = [
            ("デバイスチャネル", test_device_channel(session_id)),
            ("Webアプリチャネル", test_webapp_channel(session_id)),
            ("レガシーチャネル", test_legacy_channel(session_id)),
            ("同時接続", test_concurrent_connections(session_id))
        ]
        
        results = []
        for test_name, test_coro in tests:
            print(f"\n--- {test_name}テスト ---")
            try:
                result = await test_coro
                results.append((test_name, result))
                print(f"✅ {test_name}: {'成功' if result else '失敗'}")
            except Exception as e:
                results.append((test_name, False))
                print(f"❌ {test_name}: エラー - {e}")
            
            print()
        
        return results
    
    # テスト実行
    results = asyncio.run(run_tests())
    
    # 結果サマリー
    print("=" * 50)
    print("📊 テスト結果サマリー:")
    success_count = 0
    for test_name, result in results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"  {test_name}: {status}")
        if result:
            success_count += 1
    
    print(f"\n🏆 総合結果: {success_count}/{len(results)} テスト成功")
    
    if success_count == len(results):
        print("🎉 すべてのWebSocketチャネル分離テストが成功しました！")
    else:
        print("⚠️  一部のテストが失敗しました。ログを確認してください。")

if __name__ == "__main__":
    main()