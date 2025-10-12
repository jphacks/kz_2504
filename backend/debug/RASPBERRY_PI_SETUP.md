# 4DX@HOME Raspberry Pi インストールガイド

## 概要

このドキュメントは、Raspberry Pi上で4DX@HOME通信システムをセットアップする手順を説明します。

## 必要環境

- **Raspberry Pi 4** (推奨: 4GB RAM以上)
- **Raspberry Pi OS** (Bullseye 64-bit 推奨)
- **Python 3.8+**
- **インターネット接続**

## インストール手順

### 1. システム更新

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. 必要パッケージインストール

```bash
# Python開発環境
sudo apt install -y python3-pip python3-venv python3-dev

# GPIO制御ライブラリ
sudo apt install -y python3-rpi.gpio python3-gpiozero

# システムツール
sudo apt install -y git curl wget htop
```

### 3. プロジェクトセットアップ

```bash
# ホームディレクトリに移動
cd /home/pi

# プロジェクトディレクトリ作成
mkdir -p 4dx-home
cd 4dx-home

# ファイルをコピー（以下のファイルをこのディレクトリに配置）
# - raspberry-pi-main.py
# - start-4dx-home.sh
# - 4dx-home.service
```

### 4. Python依存関係インストール

```bash
# 必要ライブラリインストール
pip3 install --user websockets aiohttp psutil

# RPi固有ライブラリ確認
python3 -c "import RPi.GPIO, gpiozero; print('GPIO libraries: OK')"
```

### 5. 実行権限設定

```bash
chmod +x /home/pi/4dx-home/start-4dx-home.sh
```

### 6. ログディレクトリ作成

```bash
sudo mkdir -p /var/log/4dx-home
sudo chown pi:pi /var/log/4dx-home
```

## 基本使用方法

### 手動実行

```bash
# デフォルトセッションで起動
./start-4dx-home.sh

# 特定セッションで起動
./start-4dx-home.sh session_demo123

# 停止
./start-4dx-home.sh stop

# 状態確認
./start-4dx-home.sh status

# ログ表示
./start-4dx-home.sh logs
```

### システムサービス登録（自動起動）

```bash
# サービスファイルコピー
sudo cp 4dx-home.service /etc/systemd/system/

# サービス有効化
sudo systemctl daemon-reload
sudo systemctl enable 4dx-home.service

# サービス開始
sudo systemctl start 4dx-home.service

# 状態確認
sudo systemctl status 4dx-home.service
```

### サービス管理コマンド

```bash
# 開始
sudo systemctl start 4dx-home

# 停止
sudo systemctl stop 4dx-home

# 再起動
sudo systemctl restart 4dx-home

# 状態確認
sudo systemctl status 4dx-home

# ログ表示
sudo journalctl -u 4dx-home -f

# 自動起動無効
sudo systemctl disable 4dx-home
```

## 設定変更

### アプリケーション設定

`raspberry-pi-main.py`内の`AppConfig`クラスで設定変更可能:

```python
@dataclass
class AppConfig:
    product_code: str = "RPI001"  # デバイス識別コード
    session_id: str = "session_demo123"  # デフォルトセッション
    api_base_url: str = "https://fourdk-backend-333203798555.asia-northeast1.run.app/api"
    ws_base_url: str = "wss://fourdk-backend-333203798555.asia-northeast1.run.app"
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
```

### サービス設定

`4dx-home.service`でサービス動作を調整:

```ini
# セッションID変更
ExecStart=/usr/bin/python3 /home/pi/4dx-home/raspberry-pi-main.py your_session_id

# リソース制限変更
MemoryMax=1G
CPUQuota=100%
```

## GPIO接続（ハードウェア制御用）

### 推奨GPIO配線

| 機能 | GPIO番号 | 物理ピン | 説明 |
|------|----------|----------|------|
| 振動モーター | GPIO 18 | 12 | PWM対応 |
| 水噴射 | GPIO 23 | 16 | リレー制御 |
| 風送風 | GPIO 24 | 18 | PWM対応 |
| フラッシュLED | GPIO 25 | 22 | リレー制御 |
| カラーLED | GPIO 12 | 32 | PWM対応 |

### Arduino連携（オプション）

USB Serial通信でArduino制御が可能:

- **ボーレート**: 115200
- **デバイス**: `/dev/ttyUSB0` または `/dev/ttyACM0`
- **プロトコル**: JSON形式コマンド

## トラブルシューティング

### よくある問題

#### 1. GPIO権限エラー

```bash
# ユーザーをgpioグループに追加
sudo usermod -a -G gpio pi
# ログアウト・ログインが必要
```

#### 2. WebSocket接続失敗

```bash
# ネットワーク確認
ping fourdk-backend-333203798555.asia-northeast1.run.app

# 時刻同期確認
sudo timedatectl set-ntp true
```

#### 3. パッケージインストール失敗

```bash
# pip更新
python3 -m pip install --upgrade pip

# 権限付きインストール
sudo pip3 install websockets aiohttp
```

#### 4. メモリ不足

```bash
# GPU分割メモリ削減
sudo raspi-config
# Advanced Options -> Memory Split -> 16
```

### ログ確認

```bash
# アプリケーションログ
tail -f /var/log/4dx-home/4dx-app.log

# システムログ
sudo journalctl -u 4dx-home -f

# システム全体ログ
dmesg | tail
```

### デバッグモード実行

```bash
# 詳細ログで実行
LOG_LEVEL=DEBUG python3 raspberry-pi-main.py session_debug

# 接続テスト
python3 -c "
import asyncio
import websockets

async def test():
    uri = 'wss://fourdk-backend-333203798555.asia-northeast1.run.app/api/preparation/ws/test'
    try:
        async with websockets.connect(uri) as ws:
            print('WebSocket接続成功')
    except Exception as e:
        print(f'WebSocket接続失敗: {e}')

asyncio.run(test())
"
```

## パフォーマンス監視

### システムリソース確認

```bash
# CPU・メモリ使用率
htop

# 温度監視
vcgencmd measure_temp

# ネットワーク状態
iftop
```

### ログローテーション設定

```bash
# logrotateファイル作成
sudo tee /etc/logrotate.d/4dx-home << EOF
/var/log/4dx-home/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    create 0644 pi pi
    postrotate
        systemctl reload 4dx-home || true
    endscript
}
EOF
```

## セキュリティ考慮事項

### ファイアウォール設定

```bash
# ufw有効化
sudo ufw enable

# 必要ポートのみ許可
sudo ufw allow ssh
sudo ufw allow out 443  # HTTPS
sudo ufw allow out 53   # DNS
```

### 自動更新設定

```bash
# unattended-upgrades設定
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## 本番環境運用

### 定期メンテナンス

```bash
# 週次メンテナンススクリプト
cat > /home/pi/weekly_maintenance.sh << 'EOF'
#!/bin/bash
# ログクリーンアップ
find /var/log/4dx-home -name "*.log" -mtime +30 -delete

# 一時ファイルクリーンアップ
find /tmp/4dx_sync_data -name "*.json" -mtime +7 -delete

# システム更新チェック
apt list --upgradable

# サービス状態確認
systemctl status 4dx-home
EOF

chmod +x /home/pi/weekly_maintenance.sh

# cron設定
crontab -e
# 毎週日曜日の午前3時に実行
0 3 * * 0 /home/pi/weekly_maintenance.sh
```

### 監視とアラート

```bash
# システム監視スクリプト例
cat > /home/pi/monitor_4dx.sh << 'EOF'
#!/bin/bash
# CPU温度チェック
temp=$(vcgencmd measure_temp | cut -d= -f2 | cut -d\' -f1)
if (( $(echo "$temp > 70" | bc -l) )); then
    echo "高温警告: ${temp}°C" | logger -t 4dx-monitor
fi

# サービス状態チェック
if ! systemctl is-active --quiet 4dx-home; then
    echo "サービス停止検出" | logger -t 4dx-monitor
    systemctl restart 4dx-home
fi
EOF

chmod +x /home/pi/monitor_4dx.sh

# 5分間隔で監視
crontab -e
*/5 * * * * /home/pi/monitor_4dx.sh
```

## 関連ファイル

- `raspberry-pi-main.py`: メインアプリケーション
- `start-4dx-home.sh`: 起動スクリプト  
- `4dx-home.service`: systemdサービス設定
- `/var/log/4dx-home/4dx-app.log`: アプリケーションログ
- `/tmp/4dx_sync_data/`: 同期データ保存ディレクトリ