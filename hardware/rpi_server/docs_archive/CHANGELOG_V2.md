# デバッグコントローラー v2.0 - 変更履歴

## バージョン 2.0.0 (2025年11月8日)

### 🎉 新機能

#### 1. タブ式インターフェース

**手動制御タブ**:
- 既存の全コントロールを統合
- ESP1-4の個別操作
- 視覚的に整理されたレイアウト

**自動テストタブ**:
- クイックテスト（30秒）
  - 全デバイスの基本動作確認
  - 各デバイス1-3秒間隔でテスト
  - プログレスバー表示
- 完全テスト（2分）
  - 全パターン網羅的にテスト
  - RGB 6色、Motor振動パターン全種類
  - 詳細な動作確認

**デバイス状態タブ**:
- 接続デバイスの詳細情報表示
- デバイスID、タイプ、オンライン状態
- 最終ハートビート時刻
- リアルタイム更新

**ログタブ**:
- MQTT通信履歴表示
- 最新20件を保持
- 色分けされた視覚的フィードバック
- タイムスタンプ付き

#### 2. クイックプリセット機能

4種類のシーンプリセットを追加:

**アクションシーン**:
```javascript
Motor1/2: 強振動
Wind: ON
Light: 高速点滅
実行時間: 約3秒
```

**ホラーシーン**:
```javascript
RGB: 赤色
Light: ゆっくり点滅
Motor1/2: ハートビート
実行時間: 約6秒
```

**レーシング**:
```javascript
Motor1/2: 高速Rumble
Wind: ON
RGB: シアン色
実行時間: 約4秒
```

**デモ演出**:
```javascript
RGB: 赤→緑→青（順次変化）
Light: 高速点滅
Wind: ON
Motor1: 強振動
Water: 単発トリガー
実行時間: 約10秒
```

#### 3. 通信ログビューワー

**機能**:
- リアルタイムでMQTT通信を記録
- ブラウザ内で最新20件を表示
- 成功/失敗/エラーを色分け
- ターミナル風のデザイン

**ログフォーマット**:
```
[HH:MM:SS] 📤 送信: /4dx/water = trigger
[HH:MM:SS] ✅ 成功: /4dx/water
[HH:MM:SS] ❌ 失敗: /4dx/wind - Connection timeout
```

#### 4. プログレスバー機能

自動テスト実行中に以下を表示:
- 現在のステップ名（例: "5/14: LED 点滅"）
- 進行状況のバー（0-100%）
- 視覚的なフィードバック

### 🔧 API拡張

#### 新規エンドポイント

**GET /api/debug/logs**:
```json
{
  "logs": [
    {
      "timestamp": "2025-11-08T15:30:45",
      "type": "sent",
      "topic": "/4dx/water",
      "payload": "trigger"
    }
  ]
}
```

**GET /api/debug/system-info**:
```json
{
  "platform": "Linux",
  "python_version": "3.9.2",
  "cpu_percent": 15.2,
  "memory": {
    "total_gb": 1.0,
    "used_gb": 0.4,
    "percent": 40.0
  },
  "config": {
    "device_hub_id": "DH001",
    "mqtt_broker": "localhost:1883"
  }
}
```

**POST /api/debug/mqtt-test**:
```json
{
  "success": true,
  "connected": true,
  "test_sent": true
}
```

### 🎨 UI/UX改善

#### スタイル追加

**新しいボタンスタイル**:
- `.btn-test`: 紫色（自動テスト用）
- `.btn-preset`: 緑色（プリセット用）

**デバイスステータスカード**:
```css
.device-status-item {
    display: flex;
    justify-content: space-between;
    background-color: #f8f9fa;
    border-radius: 6px;
    padding: 8px 12px;
}
```

**ログビューワー**:
```css
.log-viewer {
    max-height: 200px;
    overflow-y: auto;
    background-color: #212529;
    color: #0f0;
    font-family: 'Courier New', monospace;
}
```

**プログレスバー**:
```css
.progress-bar {
    width: 100%;
    height: 8px;
    background-color: #e9ecef;
    border-radius: 4px;
}
.progress-bar-fill {
    height: 100%;
    background-color: #007bff;
    transition: width 0.3s ease;
}
```

**タブボタン**:
```css
.tab-button.active {
    color: #007bff;
    border-bottom: 3px solid #007bff;
}
```

### 📊 JavaScript関数追加

#### タブ管理

```javascript
switchTab(tabName)  // タブ切り替え
updateDeviceDetails()  // デバイス詳細更新
```

#### ログ管理

```javascript
addLog(message, type)  // ログエントリ追加
updateLogViewer()  // ログビューワー更新
refreshLogs()  // ログ手動更新
```

#### 自動テスト

```javascript
runAutoTest(mode)  // 'quick' | 'full'
```

**テストシーケンス**:
- クイックテスト: 14ステップ、約30秒
- 完全テスト: 24ステップ、約2分

#### プリセット

```javascript
runPreset(presetName)  // 'action' | 'horror' | 'racing' | 'demo'
```

### 🐛 バグ修正

- publish関数のログ記録機能を追加（オーバーライド）
- タブ切り替え時の自動更新機能
- 自動テスト重複実行防止機能
- デバイス詳細取得エラーハンドリング

### 📈 パフォーマンス改善

- ログは最新20件のみ保持（メモリ節約）
- デバイス情報は5秒間隔で自動更新
- タブアクティブ時のみデータ取得

### 🔒 セキュリティ

- ログに機密情報を含まない設計
- システム情報取得時のエラーハンドリング
- MQTT テストメッセージの一意性（タイムスタンプ使用）

---

## バージョン 1.1.0 (2025年11月8日 - 初回リリース)

### 初期機能

- 基本的な手動制御UI
- ALL STOP（緊急停止）機能
- ESP1-4の個別操作
- リアルタイムステータス表示
- スマホ対応レスポンシブデザイン

---

## ファイル変更サマリー

### 更新ファイル

| ファイル | 変更内容 | 追加行数 |
|---------|---------|----------|
| `templates/controller.html` | タブUI、自動テスト、ログビューワー追加 | +400行 |
| `src/server/app.py` | デバッグAPI追加 | +150行 |
| `DEBUG_CONTROLLER_ADVANCED.md` | 新規ドキュメント | +500行 |

### 新規ファイル

| ファイル | 説明 |
|---------|------|
| `DEBUG_CONTROLLER_ADVANCED.md` | 拡張機能ガイド |
| `CHANGELOG_V2.md` | このファイル（変更履歴）|

---

## 破壊的変更

**なし** - 既存機能は全て互換性を維持

---

## アップグレード手順

### 既存ユーザー向け

1. **ファイルを更新**:
   ```bash
   cd hardware/rpi_server
   git pull origin main
   ```

2. **サーバーを再起動**:
   ```bash
   sudo systemctl restart 4dx-home
   ```

3. **ブラウザでアクセス**:
   ```
   http://<Raspberry_Pi_IP>:8000/
   ```

4. **新機能を確認**:
   - 画面上部のタブが表示されているか
   - 「自動テスト」タブで「クイックテスト」を実行
   - 「デバイス状態」タブでデバイス情報を確認

### 新規ユーザー向け

通常のセットアップ手順に従ってください:
- [QUICK_START.md](./QUICK_START.md)

---

## 既知の問題

### 軽微な問題

1. **ログビューワーのスクロール**
   - 20件以上のログが蓄積するとスクロールが必要
   - 影響: なし（仕様通り）

2. **自動テスト中のボタン無効化**
   - 自動テスト実行中は全ボタンが無効化される
   - 影響: なし（意図的な設計）

### 回避策あり

1. **タブ切り替え時のちらつき**
   - 原因: CSS transitionの遅延
   - 回避策: 現時点で問題なし

---

## 依存関係

### Python パッケージ

既存の依存関係のみ（追加なし）:
```
Flask==2.3.0
flask-cors==4.0.0
paho-mqtt==1.6.1
websockets==11.0.3
python-dotenv==1.0.0
```

### オプション

システム情報取得のため（推奨）:
```bash
pip install psutil
```

---

## テスト結果

### 動作確認環境

- **ハードウェア**: Raspberry Pi 3 Model B+
- **OS**: Raspberry Pi OS (Bullseye)
- **Python**: 3.9.2
- **ブラウザ**: Chrome 119, Safari 17, Firefox 120

### テストケース

✅ タブ切り替え動作  
✅ 自動テスト（クイック）実行  
✅ 自動テスト（完全）実行  
✅ プリセット4種類実行  
✅ デバイス詳細表示  
✅ ログビューワー表示  
✅ スマホレスポンシブデザイン  
✅ ALL STOP機能  

---

## コントリビューター

- GitHub Copilot

---

## 次回バージョン予定

### v2.1.0（予定: 2025年12月）

- [ ] カスタムプリセット作成機能
- [ ] テスト結果のエクスポート（JSON）
- [ ] システムメトリクスのグラフ表示
- [ ] WebSocketリアルタイム更新

### v2.2.0（予定: 2026年1月）

- [ ] 複数デバイスハブの統合管理
- [ ] タイムライン再生コントロール
- [ ] 認証機能の追加

---

**リリース日**: 2025年11月8日  
**メジャーバージョン**: 2.0.0  
**主な変更**: タブUI、自動テスト、プリセット、ログビューワー
