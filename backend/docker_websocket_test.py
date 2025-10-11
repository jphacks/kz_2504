# docker_websocket_test.py - Docker環境WebSocketテスト
import json
import time
import threading
import requests
import websocket
from datetime import datetime

BASE_URL = "http://localhost:8001"
WS_BASE_URL = "ws://localhost:8001"

class WebSocketTester:
    def __init__(self):
        self.messages_received = []
        self.connection_established = False
        self.connection_error = None
        
    def test_websocket_connection(self):
        """WebSocket接続の包括テスト"""
        print("🔌 Docker環境 WebSocket接続テスト")
        print("=" * 40)
        
        # まずセッションを作成
        session_id = self._create_test_session()
        if not session_id:
            print("❌ セッション作成に失敗")
            return
            
        print(f"✅ テストセッション作成: {session_id[:8]}...")
        
        # WebSocket接続テスト
        self._test_websocket_communication(session_id)
        
        print("=" * 40)
        print("🎯 WebSocketテスト完了")
    
    def _create_test_session(self):
        """テスト用セッションを作成"""
        session_data = {
            "product_code": "DH001",
            "capabilities": ["vibration", "scent"],
            "device_info": {
                "version": "1.0.0",
                "ip_address": "192.168.1.100"
            }
        }
        
        try:
            response = requests.post(f"{BASE_URL}/api/sessions", json=session_data)
            if response.status_code == 200:
                return response.json()['session_id']
        except Exception as e:
            print(f"セッション作成エラー: {e}")
        return None
    
    def _test_websocket_communication(self, session_id):
        """WebSocket通信テスト"""
        ws_url = f"{WS_BASE_URL}/ws/sessions/{session_id}"
        print(f"接続URL: {ws_url}")
        
        # WebSocketイベントハンドラー
        def on_open(ws):
            self.connection_established = True
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] ✅ WebSocket接続確立")
            
            # テストメッセージ送信
            test_messages = [
                {"type": "ping", "timestamp": timestamp},
                {"type": "device_status", "data": {"status": "ready", "battery": 100}},
                {"type": "sync_command", "command": "start", "data": {"video_id": "sample1"}}
            ]
            
            for msg in test_messages:
                try:
                    ws.send(json.dumps(msg))
                    print(f"📤 送信: {msg['type']}")
                    time.sleep(0.2)  # 少し間隔を空ける
                except Exception as e:
                    print(f"❌ 送信エラー: {e}")
            
            # テスト完了後、接続を閉じる
            time.sleep(1)
            ws.close()
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                self.messages_received.append(data)
                timestamp = datetime.now().strftime("%H:%M:%S")
                message_preview = str(data).replace('{', '').replace('}', '')[:50]
                print(f"[{timestamp}] 📥 受信: {data.get('type', 'unknown')} - {message_preview}...")
            except Exception as e:
                print(f"❌ メッセージ解析エラー: {e}")
        
        def on_error(ws, error):
            self.connection_error = error
            print(f"❌ WebSocketエラー: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] 🔌 WebSocket接続終了 (コード: {close_status_code})")
        
        # WebSocket接続実行
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # 別スレッドで実行
        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        
        # 接続完了まで待機
        time.sleep(4)
        
        # 結果表示
        self._display_results()
    
    def _display_results(self):
        """テスト結果表示"""
        print("\n📊 WebSocketテスト結果:")
        print(f"  接続確立: {'✅ 成功' if self.connection_established else '❌ 失敗'}")
        if self.connection_error:
            print(f"  エラー: {self.connection_error}")
        print(f"  受信メッセージ数: {len(self.messages_received)}")
        
        if self.messages_received:
            print("\n📝 受信メッセージ詳細:")
            for i, msg in enumerate(self.messages_received[:5]):  # 最初の5件を表示
                msg_str = str(msg)[:80].replace('{', '').replace('}', '')
                print(f"    {i+1}. {msg.get('type', 'unknown')}: {msg_str}...")

def test_invalid_session_websocket():
    """不正セッションIDでのWebSocket接続テスト"""
    print("\n🚫 不正セッションWebSocketテスト")
    
    invalid_ws_url = f"{WS_BASE_URL}/ws/sessions/invalid-session-id"
    connection_failed = False
    error_received = None
    
    def on_open(ws):
        print("❌ 予期しない接続成功")
    
    def on_error(ws, error):
        nonlocal connection_failed, error_received
        connection_failed = True
        error_received = str(error)
    
    def on_close(ws, close_status_code, close_msg):
        if close_status_code == 4004:
            print("✅ 適切なエラーコードで接続拒否 (4004)")
        else:
            print(f"⚠️  予期しないクローズコード: {close_status_code}")
    
    try:
        ws = websocket.WebSocketApp(
            invalid_ws_url,
            on_open=on_open,
            on_error=on_error,
            on_close=on_close
        )
        
        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
        time.sleep(2)
        
    except Exception as e:
        print(f"✅ 接続エラーが適切に処理された: {e}")

if __name__ == "__main__":
    # 基本WebSocketテスト
    tester = WebSocketTester()
    tester.test_websocket_connection()
    
    # エラーケーステスト
    test_invalid_session_websocket()