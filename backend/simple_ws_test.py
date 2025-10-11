# simple_ws_test.py - シンプルなWebSocketテスト
import asyncio
import json
import requests
from websockets import connect

async def test_websocket():
    print("🔌 シンプルWebSocketテスト")
    
    # セッション作成
    session_data = {
        "product_code": "DH001",
        "capabilities": ["vibration", "scent"],
        "device_info": {"version": "1.0.0", "ip_address": "192.168.1.100"}
    }
    
    response = requests.post("http://localhost:8001/api/sessions", json=session_data)
    if response.status_code != 200:
        print("❌ セッション作成失敗")
        return
    
    session_id = response.json()['session_id']
    print(f"✅ セッション作成: {session_id[:8]}...")
    
    # WebSocket接続
    ws_url = f"ws://localhost:8001/ws/sessions/{session_id}"
    print(f"接続URL: {ws_url}")
    
    try:
        async with connect(ws_url) as websocket:
            print("✅ WebSocket接続成功")
            
            # 接続確認メッセージ受信
            try:
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"📥 初期メッセージ: {welcome_msg}")
            except asyncio.TimeoutError:
                print("⚠️  初期メッセージなし")
            
            # テストメッセージ送信
            test_msg = {"type": "ping", "message": "hello"}
            await websocket.send(json.dumps(test_msg))
            print("📤 ping メッセージ送信")
            
            # レスポンス受信
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                print(f"📥 レスポンス: {response}")
            except asyncio.TimeoutError:
                print("⚠️  レスポンスなし")
            
    except Exception as e:
        print(f"❌ WebSocket接続エラー: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())