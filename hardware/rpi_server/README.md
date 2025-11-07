# 4DX@HOME Raspberry Pi Server

Cloud Run APIと統合したRaspberry Pi向けデバイスハブサーバー

> **⚠️ セキュリティ注意**: `.env`ファイルには本番環境のCloud Run URLなどの機密情報が含まれます。このファイルは絶対にGitにコミットしないでください。`.env.example`をコピーして使用してください。

## 概要

このサーバーは、Cloud Run上のバックエンドAPIと連携し、WebSocket経由でタイムラインデータを受信し、MQTT経由でESP-12Eデバイス(水・風・LED・モーター)を制御します。

**主な機能**:
- Cloud Run APIへのWebSocket接続
- タイムラインデータの受信とキャッシュ
- リアルタイム同期（±100ms精度）
- MQTTブローカー経由のデバイス制御
- デバイスハートビート監視
- Flaskベースの制御UIとステータスAPI

---

## システム要件

### ハードウェア
- **Raspberry Pi 3 Model B** 以上
- **メモリ**: 1GB以上推奨
- **ストレージ**: 8GB以上（SDカード）
- **ネットワーク**: Wi-Fi または Ethernet

### ソフトウェア
- **OS**: Raspberry Pi OS (Raspbian) Bullseye 以降
- **Python**: 3.9以上
- **MQTT Broker**: Mosquitto 2.0以上

---

## ディレクトリ構造

```
rpi_server/
├── main.py                    # メインアプリケーション
├── config.py                  # 設定管理
├── requirements.txt           # Python依存関係
├── .env.example               # 環境変数テンプレート
├── .gitignore                 # Git除外設定
├── src/                       # ソースコード
│   ├── mqtt/                  # MQTT通信レイヤー
│   │   ├── broker.py          # MQTTブローカークライアント
│   │   ├── event_mapper.py    # イベント→MQTTマッピング
│   │   └── device_manager.py  # デバイス管理
│   ├── api/                   # Cloud Run API連携
│   │   ├── websocket_client.py  # WebSocketクライアント
│   │   └── message_handler.py   # メッセージハンドラー
│   ├── timeline/              # タイムライン処理
│   │   ├── processor.py       # タイムライン処理エンジン
│   │   └── cache_manager.py   # キャッシュ管理
│   ├── server/                # HTTPサーバー
│   │   └── app.py             # Flask アプリケーション
│   └── utils/                 # ユーティリティ
│       ├── logger.py          # ロガー設定
│       ├── communication_logger.py  # 通信ログ
│       └── timing.py          # タイミング処理
├── templates/                 # HTMLテンプレート
│   └── controller.html        # デバイス制御UI
├── static/                    # 静的ファイル
│   ├── css/
│   └── js/
├── data/                      # データ保存
│   ├── timeline_cache/        # タイムラインキャッシュ
│   ├── communication_logs/    # 通信ログ
│   └── rpi_server.log         # アプリケーションログ
├── scripts/                   # セットアップスクリプト
│   ├── install_dependencies.sh  # 依存関係インストール
│   └── setup_systemd.sh         # systemd設定
└── legacy/                    # 既存4DXHOMEコード（参考用)
```

---

## インストール手順

### 1. プロジェクトのダウンロード

```bash
# リポジトリをクローン
cd ~
git clone <your-repo-url>
cd kz_2504/hardware/rpi_server
```

または、このディレクトリをRaspberry Piに直接転送してください。

### 2. 依存関係のインストール

```bash
# インストールスクリプトに実行権限を付与
chmod +x scripts/install_dependencies.sh

# 依存関係をインストール
bash scripts/install_dependencies.sh
```

**インストールされる内容**:
- システムパッケージの更新
- Python 3, pip, venv
- Mosquitto MQTTブローカー
- Python仮想環境の作成
- Pythonパッケージのインストール

### 3. 環境変数の設定

```bash
# .envファイルを作成
cp .env.example .env
nano .env
```

**必須設定項目**:
```properties
DEVICE_HUB_ID="DH001"  # デバイスハブID（一意の値）
# 本番環境のCloud Run URLを設定（.env.exampleから実際のURLに置き換える）
CLOUD_RUN_API_URL="https://your-backend-api-XXXXXXXXXX.asia-northeast1.run.app"
CLOUD_RUN_WS_URL="wss://your-backend-api-XXXXXXXXXX.asia-northeast1.run.app"
```

**オプション設定**:
- `MQTT_BROKER_HOST`: MQTTブローカーホスト（デフォルト: localhost）
- `FLASK_PORT`: HTTPサーバーポート（デフォルト: 8000）
- `LOG_LEVEL`: ログレベル（DEBUG, INFO, WARNING, ERROR）

---

## 起動方法

### 手動起動

```bash
# 仮想環境を有効化
source venv/bin/activate

# サーバーを起動（セッションIDを指定）
python main.py <session_id>

# 例: セッション "demo1" に接続
python main.py demo1
```

**セッションID**: Cloud Run APIで準備されたセッションIDを指定してください。

### systemdサービスとして自動起動

```bash
# systemd設定スクリプトに実行権限を付与
chmod +x scripts/setup_systemd.sh

# systemdサービスを設定
sudo bash scripts/setup_systemd.sh
```

**サービスの操作**:
```bash
# 起動
sudo systemctl start 4dx-home

# 停止
sudo systemctl stop 4dx-home

# 再起動
sudo systemctl restart 4dx-home

# ステータス確認
sudo systemctl status 4dx-home

# ログ確認
sudo journalctl -u 4dx-home -f
```

**自動起動の有効化**:
```bash
# Raspberry Pi起動時に自動起動
sudo systemctl enable 4dx-home

# 自動起動を無効化
sudo systemctl disable 4dx-home
```

---

## デバッグ機能

### デバッグコントローラー（Web UI）v2.0

Raspberry Piと同じWiFiネットワーク上のデバイス（スマホ、タブレット、PC）から、簡単にアクチュエータを操作できるWebベースのデバッグツールが利用可能です。

**アクセス方法**:
```
http://<Raspberry_Pi_IP>:8000/
```

**主な機能**:

#### タブ1: 手動制御
- 🛑 **ALL STOP（緊急停止）**: 全アクチュエータを即座に停止
- ESP1 (Water/Wind)制御
- ESP2 (LED/RGB)制御
- ESP3/4 (Motor1/Motor2)制御
- デバイスステータス表示
- リアルタイムなMQTT接続状態表示

#### タブ2: 自動テスト 🆕
- **クイックテスト（30秒）**: 全デバイスの基本動作確認
- **完全テスト（2分）**: 全パターン網羅的にテスト
- **プログレスバー**: 視覚的な進行状況表示
- **クイックプリセット**: アクション/ホラー/レーシング/デモシーン

#### タブ3: デバイス状態 🆕
- 接続デバイスの詳細情報表示
- オンライン/オフライン状態（🟢/🔴）
- 最終ハートビート時刻
- リアルタイム更新

#### タブ4: ログ 🆕
- MQTT通信履歴をリアルタイム表示
- 最新20件を保持
- 色分けされた視覚的フィードバック
- タイムスタンプ付き

**スマホ対応**: レスポンシブデザイン、タップしやすいUI

**使用例**:
1. スマホをRaspberry Piと同じWiFiに接続
2. ブラウザで `http://192.168.1.100:8000/` にアクセス（IPは実際のアドレスに置き換え）
3. 「自動テスト」タブでクイックテストを実行
4. 「ログ」タブで通信履歴を確認
5. 問題が発生したら「🛑 ALL STOP」で即座に全停止

> **基本ガイド**: [DEBUG_CONTROLLER.md](./DEBUG_CONTROLLER.md)  
> **拡張機能**: [DEBUG_CONTROLLER_ADVANCED.md](./DEBUG_CONTROLLER_ADVANCED.md)

### 2. ステータスAPI

**ヘルスチェック**:
```bash
curl http://localhost:8000/health
```

**デバイスステータス**:
```bash
curl http://localhost:8000/api/status
```

**接続デバイス一覧**:
```bash
curl http://localhost:8000/api/devices
```

**タイムライン統計**:
```bash
curl http://localhost:8000/api/timeline/stats
```

### 3. 手動MQTT配信（テスト用）

```bash
curl -X POST http://localhost:8000/api/mqtt/publish \
  -H "Content-Type: application/json" \
  -d '{"topic": "/4dx/water", "payload": "trigger"}'
```

---

## トラブルシューティング

### ポート8000が既に使用されている

**エラーメッセージ**:
```
Port 8000 is in use by another program
```

**解決方法1: 既存プロセスを停止**
```bash
# 停止スクリプトを実行
bash scripts/stop_server.sh

# または手動でポートを使用しているプロセスを停止
sudo lsof -ti:8000 | xargs kill -9
```

**解決方法2: 別のポートを使用**
```bash
# .envファイルを編集
nano .env

# FLASK_PORTを変更（例: 8001）
FLASK_PORT=8001
```

**解決方法3: 再起動スクリプトを使用**
```bash
# 自動的に既存プロセスを停止して再起動
bash scripts/restart_server.sh demo1
```

### デバイスIDが"unknown"と表示される

**原因**: ESP-12Eデバイスから送信されるデバイスIDが`DEVICE_TYPE_MAP`に登録されていない

**確認方法**:
```bash
# MQTTハートビートを監視
mosquitto_sub -h localhost -t "/4dx/heartbeat"
```

**修正方法**: `src/mqtt/device_manager.py`の`DEVICE_TYPE_MAP`に実際のデバイスIDを追加
```python
DEVICE_TYPE_MAP = {
    "alive_esp1_water": "water_wind",
    "alive_esp2_led": "led",
    "alive_esp3_motor1": "motor1",
    "alive_esp4_motor2": "motor2",
    "your_device_id": "device_type",  # 追加
}
```

### "未知のメッセージタイプ"警告が表示される

**警告例**:
```
WARNING - 未知のメッセージタイプ: device_connected
```

**対応**: 通常は無害な警告です。バックエンドから新しいメッセージタイプが送信されている場合、必要に応じて`src/api/message_handler.py`にハンドラーを追加してください。

### MQTTブローカー接続エラー

```bash
# Mosquittoのステータス確認
sudo systemctl status mosquitto

# Mosquittoの再起動
sudo systemctl restart mosquitto

# MQTTポート確認
sudo netstat -tuln | grep 1883
```

### WebSocket接続エラー

**エラーログを確認**:
```bash
sudo journalctl -u 4dx-home -n 50
```

**確認事項**:
- Cloud Run APIのURLが正しいか（.envファイル）
- インターネット接続が正常か
- セッションIDがCloud Run側で準備されているか

### デバイスが接続されない

**MQTTハートビート確認**:
```bash
mosquitto_sub -h localhost -t "/4dx/heartbeat"
```

**デバイスのログ確認**:
- ESP-12Eデバイスのシリアルログを確認
- MQTTブローカーのIPアドレスが正しいか確認

### ログファイルの確認

```bash
# アプリケーションログ
cat data/rpi_server.log

# 通信ログ（JSON形式）
ls -lh data/communication_logs/

# 最新の通信ログを表示
cat data/communication_logs/*.json | tail -n 20
```

---

## 開発・カスタマイズ

### イベントマッピングの変更

`src/mqtt/event_mapper.py` の `EVENT_MAP` を編集:

```python
EVENT_MAP: Dict[Tuple[str, str], List[Tuple[str, str]]] = {
    ("water", "burst"): [
        ("/4dx/water", "trigger")
    ],
    # 新しいマッピングを追加
    ("custom_effect", "mode1"): [
        ("/4dx/custom", "CUSTOM_PAYLOAD")
    ],
}
```

### 同期精度の調整

`.env` ファイルで設定:

```properties
# 同期許容誤差（ミリ秒）
# イベント実行の時間範囲を指定します
# 例: 100ms の場合、1.0秒のイベントは 0.9~1.1秒の範囲で実行されます
SYNC_TOLERANCE_MS=100  # デフォルト: ±100ms (0.1秒)

# WebSocket Ping間隔（秒）
WS_PING_INTERVAL=30  # デフォルト: 30秒
```

**同期精度の説明**:
- `SYNC_TOLERANCE_MS=100` の場合、イベント時刻から±0.1秒の範囲内で実行
- タイムライン上で `t=1.0` のイベントは、現在時刻が `0.9~1.1秒` の時に発火
- ネットワーク遅延を考慮した設定値です
- より厳密な同期が必要な場合は `50` (±0.05秒) に設定可能

### ログレベルの変更

```properties
# ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=DEBUG

# 通信ログの有効化/無効化
ENABLE_COMMUNICATION_LOG=True
```

---

## アーキテクチャ

```
[Cloud Run API] ←WebSocket→ [Raspberry Pi Server] ←MQTT→ [ESP-12E Devices]
                                    ↓
                            [Timeline Processor]
                                    ↓
                            [Event Mapper]
                                    ↓
                            [MQTT Publisher]
```

**処理フロー**:
1. Cloud Run APIから`sync_data_bulk_transmission`メッセージでタイムラインJSON受信
2. タイムラインをキャッシュに保存
3. Cloud Run APIから`sync`メッセージで現在時刻受信（500ms間隔）
4. TimelineProcessorが現在時刻±100msのイベントを検出
5. EventMapperがイベントをMQTTコマンドに変換
6. MQTTBrokerClientがESP-12Eデバイスに配信

---

## ライセンス

このプロジェクトは個人利用・研究用途です。

---

## サポート

質問やバグ報告は開発チームまでお問い合わせください。

---

## 更新履歴

- **2025-01-06**: 初回リリース
  - Cloud Run API統合
  - WebSocket通信実装
  - MQTT制御実装
  - systemdサービス対応
