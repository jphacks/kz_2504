#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
debug_client.py  (WSトリガ統合・自動開始版)
- サーバーのWebSocketからの合図で、元のTCP送信ロジックを開始/停止。
- Enter待ちを廃止し、開始合図受信後に自動で送信開始。
- 送信仕様は元のまま（4バイトbig-endian長 + JSON）。

合図:
  start系: {"type":"continuous_sync_started", ...} or {"type":"start_signal"}
  stop系 : {"type":"continuous_sync_stopped", ...} or {"type":"stop_signal"}

依存:
  pip install websocket-client
"""

import os
import sys
import json
import time
import socket
import threading
import websocket  # pip install websocket-client

# --- WS接続先（固定） ---
SESSION_ID = "demo_session"
WEBSOCKET_URI = f"wss://fourdk-backend-333203798555.asia-northeast1.run.app/api/playback/ws/device/{SESSION_ID}"

# --- 元コードの設定を維持 ---
HOST = '127.0.0.1'
PORT = 65432
TIMELINE_FILE = 'demo2.json'

# ====== 共有状態 ======
runner_lock = threading.Lock()
runner_thread = None
runner_stop = threading.Event()
runner_running = threading.Event()  # 多重起動ガード

def send_data(sock: socket.socket, data: dict) -> bool:
    """元コードそのまま：4バイトbig-endianヘッダ + JSON本体 を送信"""
    try:
        payload = json.dumps(data).encode('utf-8')
        header = len(payload).to_bytes(4, 'big')
        sock.sendall(header + payload)
        return True
    except (BrokenPipeError, ConnectionResetError):
        print("❌ サーバーとの接続が切れました。")
        return False
    except Exception as e:
        print(f"❌ データの送信中にエラーが発生しました: {e}")
        return False

def load_timeline():
    """タイムライン読み込み（元の動作）"""
    try:
        with open(TIMELINE_FILE, 'r', encoding='utf-8') as f:
            timeline_data = json.load(f)
        print(f"✅ タイムラインファイル '{TIMELINE_FILE}' を読み込みました。")

        total_duration = 0.0
        if timeline_data.get('events'):
            total_duration = max(event.get('t', 0.0) for event in timeline_data['events'])

        return timeline_data, total_duration
    except FileNotFoundError:
        print(f"❌ エラー: タイムラインファイル '{TIMELINE_FILE}' が見つかりません。")
    except json.JSONDecodeError:
        print(f"❌ エラー: '{TIMELINE_FILE}' は有効なJSONファイルではありません。")
    except Exception as e:
        print(f"💥 タイムライン読み込み時の予期せぬエラー: {e}")
    return None, 0.0

def tcp_send_loop():
    """元の main() 相当の処理（合図後に動く／Enter待ちなしの自動開始）"""
    print("--- デバッグクライアント (連続送信モード / 自動開始) ---")

    timeline_data, total_duration = load_timeline()
    if timeline_data is None:
        runner_running.clear()
        return

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((HOST, PORT))
        print(f"✅ サーバー ({HOST}:{PORT}) に接続しました。")

        # 最初にタイムライン全体を送信（元仕様）
        if not send_data(s, timeline_data):
            s.close()
            runner_running.clear()
            return

        # ★ Enter待ちをスキップして即時開始
        print("▶️ 自動開始：currentTime の連続送信を開始します。")

        current_time = 0.0
        start_time = time.time()

        while not runner_stop.is_set():
            current_time = time.time() - start_time

            # タイムラインの終点に到達したらリセット（元仕様）
            if current_time > total_duration:
                print("🏁 タイムラインの終点に到達しました。最初から再生します。")
                current_time = 0.0
                start_time = time.time()

            time_update_data = {'currentTime': current_time}
            print(f"  -> 送信中: currentTime = {current_time:.2f}s")

            if not send_data(s, time_update_data):
                break

            # 0.5秒ごと（元仕様）
            for _ in range(5):
                if runner_stop.is_set():
                    break
                time.sleep(0.1)

    except ConnectionRefusedError:
        print("❌ サーバーへの接続が拒否されました。hardware_manager.pyが起動しているか確認してください。")
    except KeyboardInterrupt:
        print("\n⏹️ ユーザーによって停止されました。")
    except Exception as e:
        print(f"💥 予期せぬエラー: {e}")
    finally:
        print("🔌 サーバーとの接続を閉じます。")
        try:
            s.close()
        except Exception:
            pass
        runner_running.clear()

def start_runner_if_needed():
    """多重起動を避けつつ、送信ループを開始"""
    global runner_thread
    with runner_lock:
        if runner_running.is_set():
            print("ℹ️ 送信ループはすでに起動済みです。")
            return
        runner_stop.clear()
        runner_running.set()
        runner_thread = threading.Thread(target=tcp_send_loop, daemon=True)
        runner_thread.start()
        print("▶️ 送信ループを起動しました。")

def stop_runner_if_running():
    """送信ループを停止"""
    with runner_lock:
        if not runner_running.is_set():
            print("ℹ️ 停止対象の送信ループはありません。")
            return
        print("⏹️ 送信ループの停止を指示します。")
        runner_stop.set()

# ====== WebSocketハンドラ ======
def on_open(ws):
    print(f"✅ [WS] Connected: {WEBSOCKET_URI}")

def on_message(ws, message):
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        print(f"📥 [WS] Non-JSON ignored: {message!r}")
        return

    t = data.get("type")

    # ---- 開始系トリガ ----
    if t == "continuous_sync_started" or t == "start_signal":
        print(f"🏁 [WS] start trigger received: {data}")
        start_runner_if_needed()
        return

    # ---- 停止系トリガ ----
    if t == "continuous_sync_stopped" or t == "stop_signal":
        print(f"🛑 [WS] stop trigger received: {data}")
        stop_runner_if_running()
        return

    # それ以外はログだけ
    print(f"📥 [WS] Ignored: {data}")

def on_error(ws, error):
    print(f"❌ [WS] Error: {error}")

def on_close(ws, code, reason):
    print(f"🔌 [WS] Closed: code={code}, reason={reason}")
    # WS切断時も安全側で停止
    stop_runner_if_running()

def main():
    print(f"▶️ Connecting to: {WEBSOCKET_URI}")
    while True:
        ws = websocket.WebSocketApp(
            WEBSOCKET_URI,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        try:
            ws.run_forever(ping_interval=30, ping_timeout=10)
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user.")
            break
        except Exception as e:
            print(f"⚠️ [WS] run_forever exception: {e}")

        # 切断後の再接続待機
        time.sleep(3)

    # 終了処理
    stop_runner_if_running()
    with runner_lock:
        if runner_thread and runner_thread.is_alive():
            runner_thread.join(timeout=2)

if __name__ == '__main__':
    try:
        import websocket  # noqa
    except ImportError:
        print("websocket-client が未インストールです。以下を実行してください:\n  pip install websocket-client")
        sys.exit(1)

    main()
