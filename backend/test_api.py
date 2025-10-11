# test_api.py - APIテストスクリプト
import sys
import os
sys.path.append('.')

from app.main import app
from fastapi.testclient import TestClient
import json

def test_api():
    """基本的なAPIテスト"""
    client = TestClient(app)
    
    print("=== 4DX@HOME Backend API テスト ===")
    
    # 1. ルートエンドポイント
    print("\n1. ルートエンドポイントテスト")
    response = client.get("/")
    print(f"ステータス: {response.status_code}")
    print(f"レスポンス: {response.json()}")
    
    # 2. ヘルスチェック
    print("\n2. ヘルスチェックテスト")
    response = client.get("/api/health")
    print(f"ステータス: {response.status_code}")
    print(f"レスポンス: {response.json()}")
    
    # 3. セッション作成テスト
    print("\n3. セッション作成テスト")
    session_data = {
        "product_code": "DH001",
        "capabilities": ["vibration", "scent"],
        "device_info": {
            "version": "1.0.0",
            "ip_address": "192.168.1.100"
        }
    }
    
    response = client.post("/api/sessions", json=session_data)
    print(f"ステータス: {response.status_code}")
    if response.status_code == 200:
        session_response = response.json()
        print(f"セッションID: {session_response['session_id']}")
        session_id = session_response['session_id']
        
        # 4. セッション情報取得テスト
        print("\n4. セッション情報取得テスト")
        response = client.get(f"/api/sessions/{session_id}")
        print(f"ステータス: {response.status_code}")
        print(f"レスポンス: {response.json()}")
        
    else:
        print(f"エラー: {response.json()}")
    
    # 5. 動画リスト取得テスト
    print("\n5. 動画リスト取得テスト")
    response = client.get("/api/videos")
    print(f"ステータス: {response.status_code}")
    print(f"レスポンス: {response.json()}")
    
    # 6. 同期データ取得テスト
    print("\n6. 同期データ取得テスト")
    response = client.get("/api/sync-data/sample1")
    print(f"ステータス: {response.status_code}")
    if response.status_code == 200:
        sync_data = response.json()
        print(f"動画ID: {sync_data['video_id']}")
        print(f"イベント数: {len(sync_data['sync_events'])}")
    else:
        print(f"エラー: {response.json()}")

if __name__ == "__main__":
    test_api()