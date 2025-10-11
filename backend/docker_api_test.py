# docker_api_test.py - Docker環境での包括的APIテスト
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8001"

def log_result(test_name, success, details=""):
    """テスト結果をログ出力"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"[{timestamp}] {status} {test_name}")
    if details:
        print(f"    {details}")
    print()

def test_docker_api():
    """Docker環境でのAPIテスト"""
    print("🐳 Docker環境 4DX@HOME API 包括テスト")
    print("=" * 50)
    
    # 1. サーバー基本動作確認
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        data = response.json()
        log_result("サーバー基本動作", 
                  response.status_code == 200,
                  f"環境: {data.get('environment')}, 活動セッション: {data.get('active_sessions')}")
    except Exception as e:
        log_result("サーバー基本動作", False, f"接続エラー: {e}")
        return
    
    # 2. ヘルスチェック
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        log_result("ヘルスチェック", 
                  response.status_code == 200 and response.json().get('status') == 'healthy')
    except Exception as e:
        log_result("ヘルスチェック", False, f"エラー: {e}")
    
    # 3. セッション作成・管理テスト
    session_data = {
        "product_code": "DH001",
        "capabilities": ["vibration", "scent", "air", "motion"],
        "device_info": {
            "version": "1.2.0", 
            "ip_address": "192.168.1.100"
        }
    }
    
    session_id = None
    try:
        response = requests.post(f"{BASE_URL}/api/sessions", json=session_data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            session_id = result['session_id']
            log_result("セッション作成", True,
                      f"ID: {session_id[:8]}..., WebSocket: {result['websocket_url']}")
        else:
            log_result("セッション作成", False, f"HTTPエラー: {response.status_code}")
    except Exception as e:
        log_result("セッション作成", False, f"エラー: {e}")
    
    # 4. セッション情報取得
    if session_id:
        try:
            response = requests.get(f"{BASE_URL}/api/sessions/{session_id}", timeout=5)
            if response.status_code == 200:
                session_info = response.json()
                log_result("セッション情報取得", True,
                          f"状態: {session_info['status']}, 接続: {session_info['device_connected']}")
            else:
                log_result("セッション情報取得", False, f"HTTPエラー: {response.status_code}")
        except Exception as e:
            log_result("セッション情報取得", False, f"エラー: {e}")
    
    # 5. 動画リスト取得
    try:
        response = requests.get(f"{BASE_URL}/api/videos", timeout=5)
        if response.status_code == 200:
            videos = response.json()
            log_result("動画リスト取得", True, f"検出動画数: {len(videos)}")
            for video in videos[:2]:  # 最初の2つを表示
                print(f"    - {video['title']} ({video['duration']}秒)")
        else:
            log_result("動画リスト取得", False, f"HTTPエラー: {response.status_code}")
    except Exception as e:
        log_result("動画リスト取得", False, f"エラー: {e}")
    
    # 6. 同期データ取得
    try:
        response = requests.get(f"{BASE_URL}/api/sync-data/sample1", timeout=5)
        if response.status_code == 200:
            sync_data = response.json()
            log_result("同期データ取得", True,
                      f"動画ID: {sync_data['video_id']}, イベント数: {len(sync_data['sync_events'])}")
        else:
            log_result("同期データ取得", False, f"HTTPエラー: {response.status_code}")
    except Exception as e:
        log_result("同期データ取得", False, f"エラー: {e}")
    
    # 7. エラーハンドリングテスト
    try:
        response = requests.get(f"{BASE_URL}/api/sessions/invalid-id", timeout=5)
        log_result("エラーハンドリング（不正ID）", 
                  response.status_code == 404,
                  f"期待される404レスポンス: {response.status_code == 404}")
    except Exception as e:
        log_result("エラーハンドリング", False, f"エラー: {e}")
    
    # 8. 不正データ送信テスト
    try:
        invalid_session = {"invalid": "data"}
        response = requests.post(f"{BASE_URL}/api/sessions", json=invalid_session, timeout=5)
        log_result("バリデーションエラー処理", 
                  response.status_code == 422,
                  f"期待される422レスポンス: {response.status_code == 422}")
    except Exception as e:
        log_result("バリデーションエラー処理", False, f"エラー: {e}")
    
    print("=" * 50)
    print("🎯 Docker環境APIテスト完了")

if __name__ == "__main__":
    test_docker_api()