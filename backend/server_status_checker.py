#!/usr/bin/env python3
"""
4DX@HOME バックエンド サーバー状態確認ツール
==============================================

このスクリプトは、バックエンドサーバーの現在の状態を包括的に確認します。
- ヘルスチェック
- 現在のセッション一覧
- WebSocket接続状況
- システム情報
"""

import asyncio
import requests
import json
import websockets
from datetime import datetime
import sys
import time

class ServerStatusChecker:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.ws_base_url = base_url.replace("http", "ws")
    
    def print_header(self, title):
        """セクションヘッダーを表示"""
        print("\n" + "="*50)
        print(f"🔍 {title}")
        print("="*50)
    
    def check_health(self):
        """ヘルスチェック"""
        self.print_header("サーバーヘルスチェック")
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print("✅ サーバー正常動作中")
                print(f"📊 ステータス: {health_data.get('status', 'unknown')}")
                print(f"🔧 サービス: {health_data.get('service', 'unknown')}")
                print(f"🏷️ バージョン: {health_data.get('version', 'unknown')}")
                return True
            else:
                print(f"❌ ヘルスチェック失敗 - Status: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ サーバー接続エラー: {e}")
            return False
    
    def get_sessions(self):
        """現在のセッション一覧を取得"""
        self.print_header("アクティブセッション一覧")
        try:
            # セッション管理APIの確認
            response = requests.get(f"{self.base_url}/api/sessions", timeout=5)
            if response.status_code == 200:
                sessions = response.json()
                # レスポンス構造を確認
                session_data = sessions.get('sessions', sessions)
                if isinstance(session_data, list) and session_data:
                    print(f"📱 アクティブセッション数: {len(session_data)}")
                    for i, session in enumerate(session_data, 1):
                        print(f"\n{i}. セッションID: {session.get('session_id', 'unknown')}")
                        print(f"   製品コード: {session.get('product_code', 'unknown')}")
                        print(f"   ステータス: {session.get('status', 'unknown')}")
                        print(f"   作成時刻: {session.get('created_at', 'unknown')}")
                        if session.get('capabilities'):
                            print(f"   機能: {', '.join(session['capabilities'])}")
                elif sessions.get('count', 0) == 0:
                    print("📭 アクティブセッションなし")
                else:
                    print(f"📊 セッション数: {sessions.get('count', 0)}")
                return sessions
            else:
                print(f"❌ セッション取得失敗 - Status: {response.status_code}")
                print(f"📝 レスポンス: {response.text}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"❌ セッション取得エラー: {e}")
            return []
    
    def check_api_endpoints(self):
        """主要APIエンドポイントの確認"""
        self.print_header("APIエンドポイント確認")
        
        endpoints = [
            ("/", "ルート"),
            ("/api/health", "ヘルスチェック"),
            ("/api/sessions", "セッション一覧"),
            ("/api/videos", "動画一覧"),
            ("/docs", "API仕様書"),
        ]
        
        for endpoint, description in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                status_emoji = "✅" if response.status_code < 400 else "❌"
                print(f"{status_emoji} {description}: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"❌ {description}: 接続エラー ({e})")
    
    async def test_websocket_connection(self, session_id=None):
        """WebSocket接続テスト"""
        self.print_header("WebSocket接続テスト")
        
        test_urls = [
            f"{self.ws_base_url}/ws/sessions",
        ]
        
        if session_id:
            test_urls.extend([
                f"{self.ws_base_url}/ws/device/{session_id}",
                f"{self.ws_base_url}/ws/webapp/{session_id}",
            ])
        
        for url in test_urls:
            try:
                print(f"🔌 テスト中: {url}")
                async with websockets.connect(url, timeout=5) as websocket:
                    print(f"✅ 接続成功: {url}")
                    # ping-pongテスト
                    await websocket.ping()
                    print("📡 Ping-Pong テスト成功")
            except Exception as e:
                print(f"❌ 接続失敗: {url} - {e}")
    
    def get_system_info(self):
        """システム情報の確認"""
        self.print_header("システム情報")
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code == 200:
                info = response.json()
                print("📋 システム情報:")
                for key, value in info.items():
                    print(f"   {key}: {value}")
            else:
                print(f"❌ システム情報取得失敗 - Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ システム情報取得エラー: {e}")
    
    def create_test_session(self):
        """テスト用セッション作成"""
        self.print_header("テストセッション作成")
        try:
            device_data = {
                "product_code": "DH001",
                "capabilities": ["vibration", "motion", "scent", "audio"],
                "device_info": {
                    "version": "1.0.0",
                    "ip_address": "127.0.0.1"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/sessions",
                json=device_data,
                timeout=10
            )
            
            if response.status_code == 200:
                session_data = response.json()
                print("✅ テストセッション作成成功")
                print(f"📱 セッションID: {session_data.get('session_id')}")
                print(f"🔗 製品コード: {session_data.get('product_code')}")
                return session_data.get('session_id')
            else:
                print(f"❌ テストセッション作成失敗 - Status: {response.status_code}")
                print(f"📝 レスポンス: {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ テストセッション作成エラー: {e}")
            return None
    
    async def run_full_check(self):
        """フル状態チェック実行"""
        print("🚀 4DX@HOME バックエンド状態チェック開始")
        print(f"🎯 対象サーバー: {self.base_url}")
        print(f"⏰ 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. ヘルスチェック
        is_healthy = self.check_health()
        
        if not is_healthy:
            print("\n❌ サーバーが応答しません。Dockerコンテナが起動しているか確認してください。")
            return
        
        # 2. システム情報
        self.get_system_info()
        
        # 3. APIエンドポイント確認
        self.check_api_endpoints()
        
        # 4. セッション一覧
        sessions = self.get_sessions()
        
        # 5. テストセッション作成
        test_session_id = self.create_test_session()
        
        # 6. WebSocket接続テスト
        await self.test_websocket_connection(test_session_id)
        
        # 7. 最終結果
        self.print_header("状態チェック完了")
        if is_healthy:
            print("✅ サーバーは正常に動作しています")
            if sessions:
                print(f"📱 {len(sessions)}個のアクティブセッションがあります")
            if test_session_id:
                print(f"🧪 テストセッション: {test_session_id}")
        
        print(f"\n🔗 管理画面URL: {self.base_url}/docs")
        print(f"🌐 フロントエンド接続URL: {self.base_url}")

async def main():
    """メイン実行関数"""
    checker = ServerStatusChecker()
    await checker.run_full_check()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 状態チェック中断")
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")