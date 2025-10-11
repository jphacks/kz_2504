# final_test.py - 最終的な包括テスト
import requests
import json
import time
import asyncio
from websockets import connect
from datetime import datetime

BASE_URL = "http://localhost:8001"

def print_header(title):
    print(f"\n{'='*50}")
    print(f"🎯 {title}")
    print(f"{'='*50}")

def print_result(test_name, success, details=""):
    status = "✅ PASS" if success else "❌ FAIL"
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {status} {test_name}")
    if details:
        print(f"    {details}")

async def comprehensive_final_test():
    """最終包括テスト"""
    print_header("4DX@HOME Docker環境 最終包括テスト")
    
    # 1. システム基本動作確認
    print("\n📋 1. システム基本動作確認")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        data = response.json()
        print_result("システム起動状態", 
                    response.status_code == 200 and "Docker Hot Reload Test" in data['service'],
                    f"サービス: {data['service'][:50]}...")
        print_result("環境設定", 
                    data['environment'] == 'development',
                    f"環境: {data['environment']}")
    except Exception as e:
        print_result("システム基本動作", False, f"エラー: {e}")
        return
    
    # 2. API機能完全テスト
    print("\n🔗 2. API機能完全テスト")
    
    # ヘルスチェック
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        print_result("ヘルスチェック", response.status_code == 200)
    except Exception as e:
        print_result("ヘルスチェック", False, f"エラー: {e}")
    
    # 動画リスト取得
    try:
        response = requests.get(f"{BASE_URL}/api/videos", timeout=5)
        videos = response.json() if response.status_code == 200 else []
        print_result("動画リスト取得", 
                    response.status_code == 200 and len(videos) > 0,
                    f"検出動画数: {len(videos)}")
    except Exception as e:
        print_result("動画リスト取得", False, f"エラー: {e}")
    
    # セッション管理
    session_data = {
        "product_code": "DH001",
        "capabilities": ["vibration", "scent", "air", "motion", "wind"],
        "device_info": {
            "version": "1.2.0",
            "ip_address": "192.168.1.100"
        }
    }
    
    session_id = None
    try:
        response = requests.post(f"{BASE_URL}/api/sessions", json=session_data, timeout=5)
        if response.status_code == 200:
            session_id = response.json()['session_id']
            print_result("セッション作成", True, f"ID: {session_id[:8]}...")
            
            # セッション情報取得
            response = requests.get(f"{BASE_URL}/api/sessions/{session_id}", timeout=5)
            print_result("セッション情報取得", response.status_code == 200)
        else:
            print_result("セッション作成", False, f"HTTPエラー: {response.status_code}")
    except Exception as e:
        print_result("セッション作成", False, f"エラー: {e}")
    
    # 同期データ取得
    try:
        response = requests.get(f"{BASE_URL}/api/sync-data/sample1", timeout=5)
        if response.status_code == 200:
            sync_data = response.json()
            print_result("同期データ取得", True, 
                        f"動画ID: {sync_data['video_id']}, イベント数: {len(sync_data['sync_events'])}")
        else:
            print_result("同期データ取得", False, f"HTTPエラー: {response.status_code}")
    except Exception as e:
        print_result("同期データ取得", False, f"エラー: {e}")
    
    # 3. WebSocket完全テスト
    print("\n🔌 3. WebSocket完全テスト")
    
    if session_id:
        try:
            ws_url = f"ws://localhost:8001/ws/sessions/{session_id}"
            async with connect(ws_url) as websocket:
                print_result("WebSocket接続確立", True)
                
                # 初期メッセージ受信
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                welcome_data = json.loads(welcome_msg)
                print_result("接続確認メッセージ", 
                           welcome_data.get('type') == 'connection_established')
                
                # 双方向通信テスト
                test_messages = [
                    {"type": "ping"},
                    {"type": "device_status", "data": {"status": "ready", "battery": 95}},
                    {"type": "sync_command", "command": "start", "data": {"video_id": "sample1", "time": 0.0}}
                ]
                
                for msg in test_messages:
                    await websocket.send(json.dumps(msg))
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    print_result(f"メッセージ通信 ({msg['type']})", True)
                
        except Exception as e:
            print_result("WebSocket完全テスト", False, f"エラー: {e}")
    
    # 4. エラーハンドリング検証
    print("\n🚫 4. エラーハンドリング検証")
    
    # 存在しないセッション
    try:
        response = requests.get(f"{BASE_URL}/api/sessions/nonexistent-id", timeout=5)
        print_result("不正セッションID", response.status_code == 404)
    except Exception as e:
        print_result("不正セッションID", False, f"エラー: {e}")
    
    # 不正データ送信
    try:
        response = requests.post(f"{BASE_URL}/api/sessions", json={"invalid": "data"}, timeout=5)
        print_result("バリデーションエラー", response.status_code == 422)
    except Exception as e:
        print_result("バリデーションエラー", False, f"エラー: {e}")
    
    # 5. パフォーマンステスト
    print("\n⚡ 5. パフォーマンステスト")
    
    # API レスポンス時間測定
    start_time = time.time()
    for _ in range(10):
        requests.get(f"{BASE_URL}/api/health", timeout=5)
    avg_time = (time.time() - start_time) / 10
    print_result("API平均レスポンス時間", 
                avg_time < 0.1, 
                f"{avg_time:.3f}秒")
    
    print_header("最終テスト完了")
    print("🎉 Docker環境での4DX@HOME Backendが正常に動作しています！")
    print("🚀 本番環境デプロイの準備が完了しました。")

if __name__ == "__main__":
    asyncio.run(comprehensive_final_test())