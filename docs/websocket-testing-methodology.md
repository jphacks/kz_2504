# WebSocket同期機能テスト手法

## 概要

Phase B-3 WebSocket同期機能の実装において採用した段階的テスト手法をまとめます。
「ひとつ実装するたびに、テストコードやシミュレーターでデバッグする」方針に基づいた体系的なテスト手法です。

## テスト手法の全体構成

### 1. 段階的テスト戦略

#### 1.1 基本方針
- **Bottom-Up Testing**: 基本機能から複雑な統合機能へ段階的に検証
- **Incremental Implementation**: 各実装フェーズごとに専用テストを作成
- **Simulation-Based Testing**: 実際のフロントエンド・デバイスを模擬したテストクライアント

#### 1.2 テストフェーズ
1. **Phase 1**: WebSocket基本接続テスト
2. **Phase 2**: デバイス接続・中継テスト  
3. **Phase 3**: 統合同期テスト

## テスト手法詳細

### 2. Phase 1: WebSocket基本接続テスト

#### 2.1 テストファイル
- **ファイル名**: `test_phase3_websocket_basic.py`
- **目的**: WebSocket接続の基本機能検証

#### 2.2 テスト手法

##### 2.2.1 PlaybackWebSocketTesterクラス
```python
class PlaybackWebSocketTester:
    def __init__(self, base_url: str = "ws://127.0.0.1:8004"):
        self.base_url = base_url
        self.session_id = None
        self.websocket = None
```

**特徴**:
- WebSocket接続の生成・管理を抽象化
- 再利用可能なテストコンポーネント
- 異なるセッションIDでの並列テスト対応

##### 2.2.2 接続テスト手法
```python
async def test_connection(self):
    """WebSocket接続の基本テスト"""
    try:
        # 接続確立
        await self.connect()
        # 接続確認メッセージの検証
        message = await self.websocket.recv()
        data = json.loads(message)
        assert data["type"] == "connection_established"
        # 正常切断
        await self.disconnect()
```

**検証項目**:
- WebSocket接続の確立
- 接続確認メッセージの受信
- 正常な切断処理

##### 2.2.3 同期メッセージテスト手法
```python
async def test_sync_messages(self):
    """動画同期メッセージの送受信テスト"""
    await self.connect()
    
    # 様々な同期状態をテスト
    test_cases = [
        {"state": "play", "time": 0.0},
        {"state": "pause", "time": 15.5},
        {"state": "seeking", "time": 30.0},
        {"state": "seeked", "time": 45.2}
    ]
    
    for case in test_cases:
        # メッセージ送信
        await self.send_sync_message(case["state"], case["time"])
        # 応答検証
        response = await self.websocket.recv()
        data = json.loads(response)
        assert data["type"] == "sync_ack"
```

**検証項目**:
- 各種同期状態メッセージの処理
- サーバーからの応答メッセージ検証
- メッセージフォーマットの互換性

### 3. Phase 2: デバイス接続・中継テスト

#### 3.1 テストファイル
- **ファイル名**: `test_phase3_device_relay.py`
- **目的**: ラズベリーパイデバイス接続の模擬・検証

#### 3.2 テスト手法

##### 3.2.1 DeviceSimulatorクラス
```python
class DeviceSimulator:
    def __init__(self, device_id: str, base_url: str = "ws://127.0.0.1:8004"):
        self.device_id = device_id
        self.base_url = base_url
        self.websocket = None
        self.json_loaded = False
```

**特徴**:
- ラズベリーパイデバイスの完全な模擬
- JSONファイル読み込み状態の管理
- エフェクト処理の疑似実行

##### 3.2.2 デバイス状態管理テスト
```python
async def send_device_status(self):
    """デバイス状態をサーバーに通知"""
    status_message = {
        "type": "device_status",
        "device_id": self.device_id,
        "status": "ready",
        "json_loaded": self.json_loaded
    }
    await self.websocket.send(json.dumps(status_message))
```

**検証項目**:
- デバイス接続の確立
- デバイス状態通知機能
- サーバーからのデバイス向けメッセージ受信

##### 3.2.3 エフェクト処理模擬
```python
async def simulate_effect_processing(self, sync_data):
    """受信した同期データからエフェクト処理を模擬"""
    state = sync_data.get("state", "unknown")
    time_pos = sync_data.get("time", 0.0)
    
    print(f"[DEVICE {self.device_id}] エフェクト処理: {state} at {time_pos}s")
    
    if state == "play":
        print(f"[DEVICE {self.device_id}] 再生エフェクト開始")
    elif state == "pause":
        print(f"[DEVICE {self.device_id}] エフェクト一時停止")
```

**検証項目**:
- 同期データの解析処理
- 状態別エフェクト処理の分岐
- デバイス側ログ出力の検証

### 4. Phase 3: 統合同期テスト

#### 4.1 テストファイル
- **ファイル名**: `test_phase3_integrated_sync.py`
- **目的**: フロントエンド→サーバー→デバイスの完全な統合テスト

#### 4.2 テスト手法

##### 4.2.1 IntegratedSyncTestクラス
```python
class IntegratedSyncTest:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.frontend_tester = PlaybackWebSocketTester()
        self.device_simulator = DeviceSimulator("integrated_test_device")
```

**特徴**:
- フロントエンドとデバイスの同時接続
- リアルタイム同期フローの検証
- セッションベースの統合テスト

##### 4.2.2 並列接続テスト手法
```python
async def setup_connections(self):
    """フロントエンドとデバイスを並列接続"""
    # 同時接続タスク作成
    frontend_task = asyncio.create_task(
        self.frontend_tester.connect_to_session(self.session_id)
    )
    device_task = asyncio.create_task(
        self.device_simulator.connect_to_session(self.session_id)
    )
    
    # 並列実行
    await asyncio.gather(frontend_task, device_task)
```

**検証項目**:
- 複数クライアントの同時接続処理
- セッション管理の正確性
- 接続順序に依存しない動作

##### 4.2.3 同期フローテスト手法
```python
async def test_sync_flow(self):
    """完全な同期フローをテスト"""
    sync_scenarios = [
        {"state": "play", "time": 0.0, "duration": 30.0},
        {"state": "play", "time": 5.5, "duration": 30.0},
        {"state": "pause", "time": 10.2, "duration": 30.0},
        {"state": "seeking", "time": 15.0, "duration": 30.0},
        {"state": "seeked", "time": 20.0, "duration": 30.0}
    ]
    
    for scenario in sync_scenarios:
        # フロントエンドから同期メッセージ送信
        await self.frontend_tester.send_sync_message(
            scenario["state"], scenario["time"], scenario["duration"]
        )
        
        # デバイスでの受信確認（タイムアウト付き）
        device_message = await asyncio.wait_for(
            self.device_simulator.websocket.recv(), timeout=2.0
        )
```

**検証項目**:
- メッセージ中継の完全性
- タイミング同期の正確性
- エラー状況での堅牢性

### 5. エラーハンドリングテスト手法

#### 5.1 WebSocket切断テスト
```python
async def test_graceful_disconnect(self):
    """正常切断のテスト"""
    await self.connect()
    await self.websocket.close(1000, "正常終了")
    # サーバーログで正常切断の確認
```

#### 5.2 異常切断テスト
```python
async def test_abnormal_disconnect(self):
    """異常切断のテスト"""
    await self.connect()
    await self.websocket.close(1001, "異常終了")
    # エラーハンドリングの確認
```

#### 5.3 送信エラーテスト
- 切断済み接続への送信試行
- 不正なメッセージフォーマット
- タイムアウト処理

### 6. テスト実行手法

#### 6.1 個別テスト実行
```bash
# Phase 1: 基本機能テスト
python test_phase3_websocket_basic.py

# Phase 2: デバイス中継テスト  
python test_phase3_device_relay.py

# Phase 3: 統合テスト
python test_phase3_integrated_sync.py
```

#### 6.2 サーバー並列実行
```bash
# Terminal 1: サーバー起動
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload

# Terminal 2: テスト実行
python test_*.py
```

#### 6.3 ログ解析手法
- **接続管理ログ**: `[WS] 接続受け入れ`, `[WS] 接続切断`
- **メッセージフローログ**: `[SYNC]`, `[RELAY]`, `[DEVICE]`
- **エラーログ**: `WebSocketDisconnect`, 送信エラー

### 7. テスト品質保証手法

#### 7.1 テストカバレッジ
- **機能カバレッジ**: 全WebSocketエンドポイント
- **状態カバレッジ**: play/pause/seeking/seeked
- **エラーカバレッジ**: 正常/異常切断、送信エラー

#### 7.2 非同期テスト安定化
```python
# タイムアウト設定
async def safe_recv(websocket, timeout=5.0):
    try:
        return await asyncio.wait_for(websocket.recv(), timeout)
    except asyncio.TimeoutError:
        raise AssertionError("メッセージ受信がタイムアウトしました")

# リソースクリーンアップ
async def cleanup_test(self):
    try:
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
    except Exception as e:
        print(f"クリーンアップエラー: {e}")
```

#### 7.3 テスト独立性
- 各テストで独立したセッションID生成
- テスト間でのWebSocket接続の完全クリーンアップ
- 状態共有の排除

### 8. 継続的改善手法

#### 8.1 テスト結果の分析
- 成功/失敗パターンの記録
- パフォーマンス測定（接続時間、メッセージ遅延）
- エラー頻度の監視

#### 8.2 テストケースの拡張
- 新機能追加時の対応テスト作成
- エッジケースの段階的追加
- 負荷テストの準備

#### 8.3 自動化の促進
- CI/CD パイプラインへの統合
- 回帰テストの自動実行
- テスト結果レポートの自動生成

## まとめ

この段階的テスト手法により、WebSocket同期機能の信頼性と安定性を段階的に検証し、実装品質を確保しています。各フェーズで適切なテストクライアントを作成し、実際の使用パターンを模擬することで、本格的な統合前に問題を発見・解決できる体系的なテスト戦略を実現しています。