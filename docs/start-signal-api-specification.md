# スタート信号送信API仕様書

## 概要

4DX@HOME システムにおいて、ラズベリーパイデバイスに対してシンプルなスタート信号を送信するためのAPI仕様です。  
従来の複雑な同期処理とは異なり、単純な「スタート」コマンドをそのままデバイスに転送する機能を提供します。

**作成日**: 2025年10月12日  
**バージョン**: 1.0.0  
**対象システム**: 4DX@HOME Backend API  

---

## 1. API エンドポイント

### 1.1 REST API エンドポイント

#### `POST /api/playback/start/{session_id}`

シンプルなスタート信号をセッション内の全デバイスに送信します。

**URL**: `POST /api/playback/start/{session_id}`

**パラメータ**:
- `session_id` (Path Parameter, Required): セッションID

**リクエスト例**:
```bash
curl -X POST http://localhost:8080/api/playback/start/test_session \
  -H "Content-Type: application/json"
```

**レスポンス形式**:

**成功時（デバイス接続あり）**:
```json
{
  "success": true,
  "message": "スタート信号を2台のデバイスに送信しました",
  "session_id": "test_session",
  "sent_to_devices": 2,
  "signal_data": {
    "type": "start_signal",
    "session_id": "test_session", 
    "timestamp": 1697097883.245,
    "message": "start"
  }
}
```

**成功時（デバイス未接続）**:
```json
{
  "success": false,
  "message": "接続されたデバイスがありません",
  "session_id": "test_session",
  "sent_to_devices": 0
}
```

**エラー時**:
```json
{
  "detail": "スタート信号送信失敗: [エラー詳細]"
}
```

---

### 1.2 WebSocket メッセージ

#### WebSocket エンドポイント
`ws://localhost:8080/api/playback/ws/sync/{session_id}`

#### 送信メッセージ形式

**リクエストメッセージ**:
```json
{
  "type": "start_signal",
  "message": "start"
}
```

**フィールド説明**:
- `type`: 必須。値は `"start_signal"` 固定
- `message`: オプション。カスタムメッセージ（デフォルト: `"start"`）

**応答メッセージ**:
```json
{
  "type": "start_signal_ack",
  "session_id": "test_session",
  "success": true,
  "sent_to_devices": 2,
  "message": "スタート信号を2台のデバイスに送信しました"
}
```

---

## 2. デバイスへの送信データ形式

ラズベリーパイデバイスに送信されるスタート信号の形式：

### 2.1 REST API経由での送信データ
```json
{
  "type": "start_signal",
  "session_id": "test_session",
  "timestamp": 1697097883.245,
  "message": "start"
}
```

### 2.2 WebSocket経由での送信データ
```json
{
  "type": "start_signal", 
  "session_id": "test_session",
  "timestamp": 1697097883.245,
  "message": "start",
  "source": "websocket"
}
```

**フィールド説明**:
- `type`: メッセージタイプ（`"start_signal"` 固定）
- `session_id`: 送信元セッションID
- `timestamp`: Unix タイムスタンプ（送信時刻）
- `message`: スタートメッセージ内容
- `source`: 送信元（`"websocket"` または未設定）

---

## 3. 技術仕様

### 3.1 送信方式
- **並列送信**: セッション内の全デバイスに対して並列でスタート信号を送信
- **タイムアウト**: 2秒でタイムアウト（個別デバイスへの送信）
- **エラーハンドリング**: 個別デバイスの送信失敗は他のデバイスに影響しない

### 3.2 デバイス識別
- デバイス接続は `connection_id` が `"device_"` で始まるWebSocket接続として識別
- セッション内のデバイス接続のみが対象

### 3.3 ログ出力
```
[START_SIGNAL] スタート信号送信要求: session=test_session
[START_SIGNAL_RELAY] セッション test_session のデバイスにスタート信号並列送信
[START_SIGNAL_RELAY] 2/2 デバイスにスタート信号送信完了
[START_SIGNAL] スタート信号送信完了: session=test_session, devices=2
```

---

## 4. 使用例

### 4.1 基本的な使用フロー

1. **デバイス接続確認**
```bash
curl http://localhost:8080/api/playback/connections
```

2. **スタート信号送信**
```bash
curl -X POST http://localhost:8080/api/playback/start/my_session
```

3. **結果確認**
レスポンスの `sent_to_devices` で送信成功数を確認

### 4.2 WebSocket使用例

```javascript
// WebSocket接続
const ws = new WebSocket('ws://localhost:8080/api/playback/ws/sync/my_session');

// スタート信号送信
ws.send(JSON.stringify({
  type: "start_signal",
  message: "start"
}));

// 応答受信
ws.onmessage = function(event) {
  const response = JSON.parse(event.data);
  if (response.type === "start_signal_ack") {
    console.log(`${response.sent_to_devices}台のデバイスに送信完了`);
  }
};
```

---

## 5. エラーハンドリング

### 5.1 よくあるエラー

| エラー状況 | HTTPステータス | メッセージ | 対処方法 |
|------------|---------------|-----------|----------|
| セッション不存在 | 200 | `"接続されたデバイスがありません"` | デバイスの接続を確認 |
| 内部エラー | 500 | `"スタート信号送信失敗: [詳細]"` | サーバーログを確認 |
| 送信タイムアウト | 200 | 部分的成功（一部デバイスのみ送信） | 個別デバイスの接続状態を確認 |

### 5.2 デバッグ方法

1. **接続状態確認**
```bash
curl http://localhost:8080/api/playbook/connections
```

2. **サーバーログ確認**
```bash
# ログレベルを INFO に設定してサーバー起動
python -m uvicorn app.main:app --log-level info
```

---

## 6. システム要件

### 6.1 依存関係
- FastAPI
- WebSocket サポート
- asyncio (非同期処理)

### 6.2 対応デバイス
- Raspberry Pi ベースの 4DX デバイス
- WebSocket クライアント機能を持つデバイス
- `device_` プレフィックスを持つ接続ID

---

## 7. セキュリティ考慮事項

### 7.1 認証・認可
- 現在は認証なし（開発環境用）
- 本番環境では適切な認証機能の追加が必要

### 7.2 入力検証
- セッションIDの形式チェック
- メッセージ内容のサニタイズ

---

## 8. パフォーマンス

### 8.1 送信性能
- **並列送信**: 複数デバイスへの同時送信
- **タイムアウト制御**: 2秒以内での送信完了
- **非ブロッキング**: 他のAPI操作への影響なし

### 8.2 スケーラビリティ
- セッションあたりのデバイス数: 制限なし（実装上）
- 同時セッション数: サーバースペック依存

---

## 9. 今後の拡張予定

### 9.1 追加予定機能
- カスタムメッセージペイロード対応
- デバイス別個別送信機能
- 送信履歴・ログ機能
- 認証・認可機能

### 9.2 互換性保証
- 既存の同期APIとの互換性維持
- 新機能追加時の後方互換性保証

---

## 10. 付録

### 10.1 関連API
- `POST /api/playback/debug/sync/{session_id}/start`: 連続同期開始
- `POST /api/playback/debug/sync/{session_id}/stop`: 連続同期停止
- `GET /api/playbook/connections`: 接続状態確認

### 10.2 参考実装ファイル
- `backend/app/api/playback_control.py`: メイン実装
- `backend/debug/raspberry-pi-pc-debug.py`: デバイス側実装例

### 10.3 テスト方法
```bash
# 1. サーバー起動
cd backend && python -m uvicorn app.main:app --reload --port 8080

# 2. デバイス接続シミュレーション
cd backend/debug && python raspberry-pi-pc-debug.py test_session

# 3. スタート信号送信テスト
curl -X POST http://localhost:8080/api/playback/start/test_session
```

---

**文書更新履歴**:
- v1.0.0 (2025-10-12): 初版作成