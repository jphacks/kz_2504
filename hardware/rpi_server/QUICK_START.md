# 4DX@HOME Raspberry Pi Server - Quick Start Guide

このガイドに従えば、Raspberry Piに本サーバーをそのまま導入できます。

---

## 前提条件

- **Raspberry Pi 3 Model B** 以上（起動済み、SSH接続可能）
- **Raspberry Pi OS (Raspbian)** インストール済み
- **インターネット接続** 確立済み
- **ESP-12Eデバイス** 4台（Water/Wind, LED, Motor1, Motor2）
- **MQTTブローカー** がESP-12Eデバイスと同じネットワークにあること

---

## 導入手順（5ステップ）

### ステップ 1: プロジェクトをRaspberry Piに転送

**方法A: USBメモリを使う**
```bash
# Windows PCで hardware/rpi_server フォルダをUSBメモリにコピー
# Raspberry Piにマウントして転送
cp -r /media/usb/rpi_server ~/4dx-home
cd ~/4dx-home
```

**方法B: SCPで転送（推奨）**
```powershell
# Windows PC（PowerShell）から実行
scp -r C:\Users\kumes\Documents\kz_2504\hardware\rpi_server pi@<RaspberryPi_IP>:~/4dx-home
```

**方法C: Gitリポジトリ経由**
```bash
# Raspberry Piで実行
cd ~
git clone <your-repo-url>
mv kz_2504/hardware/rpi_server ~/4dx-home
cd ~/4dx-home
```

---

### ステップ 2: 依存関係をインストール

```bash
# スクリプトに実行権限を付与
chmod +x scripts/install_dependencies.sh

# インストール実行（10-15分程度）
bash scripts/install_dependencies.sh
```

**インストール内容**:
- システムパッケージ更新
- Python 3.9+, pip, venv
- Mosquitto MQTTブローカー（自動起動）
- Python仮想環境作成
- Pythonパッケージインストール

---

### ステップ 3: 環境変数を設定

```bash
# .envファイルを作成
cp .env.example .env
nano .env
```

**必須設定**:
```properties
# デバイスハブID（一意の値、例: DH001, DH002）
DEVICE_HUB_ID="DH001"

# Cloud Run API URL（本番環境のURLに置き換える）
# .env.exampleのXXXXXXXXXXを実際のURLに変更してください
CLOUD_RUN_API_URL="https://your-backend-api-XXXXXXXXXX.asia-northeast1.run.app"
CLOUD_RUN_WS_URL="wss://your-backend-api-XXXXXXXXXX.asia-northeast1.run.app"

# MQTTブローカー（Raspberry Pi上で起動するので localhost のまま）
MQTT_BROKER_HOST="localhost"
MQTT_BROKER_PORT=1883
```

保存して終了: `Ctrl+O` → `Enter` → `Ctrl+X`

---

### ステップ 4: サーバーを起動（テスト）

```bash
# 仮想環境を有効化
source venv/bin/activate

# サーバーを起動（セッションID: demo1）
python main.py demo1
```

**起動ログ例**:
```
============================================================
4DX@HOME Raspberry Pi Server 起動
============================================================
Device Hub ID: DH001
Session ID: demo1
Cloud Run API: https://your-backend-api-XXXXXXXXXX.asia-northeast1.run.app
============================================================
✓ MQTT接続完了
✓ Flaskサーバー起動完了
WebSocket接続開始...
WebSocket接続成功
WebSocket受信ループ開始
```

**動作確認**:
1. ブラウザで `http://<Raspberry_Pi_IP>:8000/` にアクセス
2. 「サーバー接続完了」と表示されればOK
3. デバイス制御ボタンをクリックしてMQTTコマンドが送信されるか確認

**停止**: `Ctrl+C`

---

### ステップ 5: systemdサービスとして自動起動（本番用）

```bash
# systemd設定スクリプトに実行権限を付与
chmod +x scripts/setup_systemd.sh

# サービス設定（セッションIDを入力）
sudo bash scripts/setup_systemd.sh
# 入力例: demo1
```

**サービス起動**:
```bash
sudo systemctl start 4dx-home
```

**ステータス確認**:
```bash
sudo systemctl status 4dx-home
```

**ログ確認**:
```bash
sudo journalctl -u 4dx-home -f
```

**自動起動を有効化** (Raspberry Pi起動時に自動でサーバー起動):
```bash
sudo systemctl enable 4dx-home
```

これで **Raspberry Pi再起動後も自動的にサーバーが起動** します。

---

## 動作確認チェックリスト

### ✅ MQTT接続確認

```bash
# Mosquittoの状態確認
sudo systemctl status mosquitto

# MQTTハートビート受信テスト（別ターミナル）
mosquitto_sub -h localhost -t "/4dx/heartbeat"
```

ESP-12Eデバイスが正常に動作していれば、5秒間隔でハートビートが表示されます。

### ✅ WebSocket接続確認

```bash
# ログでWebSocket接続成功を確認
sudo journalctl -u 4dx-home -n 20 | grep "WebSocket"
```

出力例:
```
WebSocket接続開始: wss://...
WebSocket接続成功
```

### ✅ デバイス制御確認

1. ブラウザで `http://<Raspberry_Pi_IP>:8000/` にアクセス
2. 「Water (単発)」ボタンをクリック
3. 実際にWaterデバイスが動作するか確認

### ✅ タイムライン同期確認

1. Cloud Run APIのフロントエンドからセッション「demo1」を開始
2. タイムラインデータをアップロード
3. 動画再生と同期してデバイスが動作するか確認

---

## トラブルシューティング

### エラー: "MQTT接続失敗"

```bash
# Mosquittoを再起動
sudo systemctl restart mosquitto

# ステータス確認
sudo systemctl status mosquitto
```

### エラー: "WebSocket接続失敗"

**確認事項**:
- インターネット接続が正常か確認: `ping google.com`
- Cloud Run APIのURLが正しいか確認: `.env`ファイル
- セッションIDがCloud Run側で準備されているか確認

### デバイスが反応しない

```bash
# ESP-12Eデバイスがハートビートを送信しているか確認
mosquitto_sub -h localhost -t "/4dx/heartbeat"

# MQTTコマンドを手動で送信
mosquitto_pub -h localhost -t "/4dx/water" -m "trigger"
```

### ログ確認

```bash
# サービスログ
sudo journalctl -u 4dx-home -f

# アプリケーションログ
cat ~/4dx-home/data/rpi_server.log

# 通信ログ
ls -lh ~/4dx-home/data/communication_logs/
```

---

## サーバーの操作コマンド

```bash
# サービス起動
sudo systemctl start 4dx-home

# サービス停止
sudo systemctl stop 4dx-home

# サービス再起動
sudo systemctl restart 4dx-home

# ステータス確認
sudo systemctl status 4dx-home

# リアルタイムログ表示
sudo journalctl -u 4dx-home -f

# 自動起動を有効化
sudo systemctl enable 4dx-home

# 自動起動を無効化
sudo systemctl disable 4dx-home
```

---

## 次のステップ

### API連携テスト

1. **フロントエンド**（debug_frontend）でセッション開始
2. **タイムラインアップロード**（準備フェーズ）
3. **動画再生開始**（Raspberry PiがWebSocket経由で同期データ受信）
4. **デバイス制御**（タイムラインに基づいてESP-12Eが動作）

### カスタマイズ

- **イベントマッピング変更**: `src/mqtt/event_mapper.py`
- **同期精度調整**: `.env` ファイル（SYNC_TOLERANCE_MS）
- **ログレベル変更**: `.env` ファイル（LOG_LEVEL）

### ドキュメント参照

詳細は `README.md` を参照してください。

---

## サポート

問題が発生した場合は、以下の情報を添えて開発チームに連絡してください:

1. エラーメッセージ
2. ログファイル (`data/rpi_server.log`)
3. システム情報 (`uname -a`)
4. Raspberry Piモデル

---

**これで導入完了です!** 🎉
