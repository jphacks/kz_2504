# 4DX@HOME セットアップガイド

## 1. 必要機材・環境

### 1.1 ハードウェア要件

| カテゴリ | 項目 | 仕様 | 必須/推奨 |
|----------|------|------|-----------|
| **デバイスハブ** | Raspberry Pi 4 Model B | 4GB RAM以上 | 必須 |
| | microSD カード | 32GB Class10以上 | 必須 |
| | USB-C 電源アダプター | 5V/3A以上 | 必須 |
| **制御基板** | Arduino Uno R3 | 正規品推奨 | 必須 |
| | USB A-B ケーブル | 0.5m | 必須 |
| **アクチュエーター** | 振動モーター | 10mmコイン型 3-5V | 必須 |
| | モータードライバー | L293D IC | 必須 |
| | 外部電源 | 6V/1A 安定化電源 | 必須 |
| **回路部品** | ブレッドボード | 半固定タイプ | 必須 |
| | ジャンパーワイヤー | オス-オス 20本セット | 必須 |

### 1.2 ソフトウェア要件

| カテゴリ | 項目 | バージョン | 用途 |
|----------|------|------------|------|
| **ラズパイOS** | Raspberry Pi OS | Lite 64-bit (最新) | ベースOS |
| **開発環境** | Python | 3.9以上 | サーバー・ハブ開発 |
| | Node.js | 18以上 | フロントエンド開発 |
| | Arduino IDE | 2.0以上 | Arduino開発 |
| **Webブラウザ** | Chrome/Firefox | 最新版 | Webアプリ動作 |

### 1.3 ネットワーク要件

- **インターネット接続**: 下り10Mbps以上推奨
- **WiFi**: 2.4GHz/5GHz対応ルーター
- **ファイアウォール**: WSS (443ポート) 通信許可
- **遅延**: RTT 100ms以下推奨

## 2. ハードウェアセットアップ

### 2.1 回路組み立て手順

#### ステップ1: 部品確認
```
チェックリスト:
□ Arduino Uno R3 × 1
□ L293D モータードライバー IC × 1
□ 振動モーター (10mm) × 1
□ ブレッドボード × 1
□ ジャンパーワイヤー (オス-オス) × 10本
□ 6V外部電源 × 1
```

#### ステップ2: ブレッドボード配線
```
配線図:
Arduino Uno     →  L293D IC      →  振動モーター
─────────────     ──────────     ──────────────
5V              →  VCC (Pin 16)  
GND             →  GND (Pin 4,5,12,13)
Digital Pin 9   →  Input 1 (Pin 2)
Digital Pin 8   →  Enable 1 (Pin 1)
                   Output 1 (Pin 3) → Motor (+)
外部6V電源      →  VS (Pin 8)
外部GND         →  GND           → Motor (-)
```

#### ステップ3: 接続確認
1. 各配線が正しく接続されているか目視確認
2. マルチメーターで導通チェック
3. 電源極性の確認（特に外部電源）

### 2.2 Arduino セットアップ

#### ステップ1: Arduino IDE インストール
```bash
# Windows
1. https://www.arduino.cc/en/software からダウンロード
2. インストーラーを実行
3. Arduino Uno ドライバーを自動インストール

# macOS
brew install --cask arduino

# Linux (Ubuntu/Debian)
sudo apt update
sudo apt install arduino
```

#### ステップ2: ファームウェア書き込み
1. Arduino IDE を起動
2. `hardware/actuators/vibration-motor/actuator.ino` を開く
3. **ツール** → **ボード** → **Arduino Uno** を選択
4. **ツール** → **ポート** → 適切なCOMポートを選択
5. **アップロード** ボタンをクリック
6. 「アップロード完了」メッセージを確認

#### ステップ3: 動作確認
```cpp
// シリアルモニターでテスト
1. Arduino IDE でシリアルモニター開く (Ctrl+Shift+M)
2. ボーレート 9600 に設定
3. 以下のコマンドを入力してテスト:

v,50,1000    // 50%強度で1秒間振動
v,100,500    // 100%強度で0.5秒間振動
stop         // 振動停止
status       // 現在の状態確認
```

### 2.3 Raspberry Pi セットアップ

#### ステップ1: OS インストール
```bash
# Raspberry Pi Imager を使用
1. https://www.raspberrypi.com/software/ からダウンロード
2. microSD カードを挿入
3. "Raspberry Pi OS Lite (64-bit)" を選択
4. 歯車アイコンで詳細設定:
   - SSH有効化
   - WiFi設定
   - ユーザー: pi, パスワード設定
5. 書き込み実行
```

#### ステップ2: 初期設定
```bash
# SSH接続
ssh pi@<ラズパイのIPアドレス>

# システム更新
sudo apt update && sudo apt upgrade -y

# 必要パッケージインストール
sudo apt install -y python3-pip git vim

# Python仮想環境作成
python3 -m venv ~/4dx-env
source ~/4dx-env/bin/activate

# 必要ライブラリインストール
pip install websockets pyserial asyncio
```

#### ステップ3: 4DX@HOME ソフトウェア配置
```bash
# プロジェクトクローン
cd ~
git clone https://github.com/your-org/4dx-home.git
cd 4dx-home

# ハブソフトウェア配置
cp hardware/device-hub/src/* ~/4dx-home/
cp hardware/device-hub/config/* ~/4dx-home/

# 実行権限付与
chmod +x hub.py

# 設定ファイル編集
vim config.json
```

#### ステップ4: 自動起動設定
```bash
# systemdサービスファイル作成
sudo cp hardware/device-hub/systemd/4dx-hub.service /etc/systemd/system/

# サービス有効化
sudo systemctl daemon-reload
sudo systemctl enable 4dx-hub.service
sudo systemctl start 4dx-hub.service

# 動作確認
sudo systemctl status 4dx-hub.service
```

## 3. ソフトウェア開発環境構築

### 3.1 バックエンド開発環境

#### Python/FastAPI 環境
```bash
# 仮想環境作成
cd backend/
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
vim .env  # 必要な設定を編集

# 開発サーバー起動
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 設定例 (.env)
```env
# サーバー設定
DEBUG=true
HOST=0.0.0.0
PORT=8000

# セキュリティ設定
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com

# ログ設定
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 3.2 フロントエンド開発環境

#### React/TypeScript 環境
```bash
# Node.js プロジェクト初期化
cd frontend/
npm install

# 環境変数設定
cp .env.example .env.local
vim .env.local

# 開発サーバー起動
npm run dev
```

#### 設定例 (.env.local)
```env
# API エンドポイント
VITE_WS_URL=ws://localhost:8000/ws
VITE_API_BASE_URL=http://localhost:8000/api

# 開発設定
VITE_DEV_MODE=true
VITE_DEBUG_WEBSOCKET=true
```

### 3.3 開発ツール設定

#### VSCode 推奨拡張機能
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.flake8",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-typescript-next",
    "arduino.arduino-ide"
  ]
}
```

## 4. 動作テスト手順

### 4.1 単体テスト

#### Arduino 単体テスト
```bash
# Arduino シリアルテスト
1. Arduino IDE のシリアルモニターを開く
2. 以下のテストシーケンスを実行:

Test 1: 基本振動テスト
> v,25,500
Expected: 25%強度で500ms振動

Test 2: 最大強度テスト  
> v,100,1000
Expected: 100%強度で1000ms振動

Test 3: 停止テスト
> v,50,5000
> stop  (振動中に実行)
Expected: 即座に振動停止

Test 4: ステータステスト
> status
Expected: "STATUS: idle,0" または "STATUS: active,XX"
```

#### ラズパイ単体テスト
```bash
# Python環境でテスト
cd ~/4dx-home
python3 test_hardware.py

Expected Output:
✅ Arduino connection: OK
✅ Serial communication: OK  
✅ WiFi connection: OK
✅ WebSocket client: OK
```

### 4.2 統合テスト

#### システム全体テスト
```bash
# 1. バックエンド起動
cd backend/
uvicorn app.main:app --reload

# 2. フロントエンド起動  
cd frontend/
npm run dev

# 3. デバイスハブ起動
ssh pi@<raspberry-pi-ip>
sudo systemctl start 4dx-hub.service

# 4. 動作確認
1. Webブラウザで http://localhost:3000 を開く
2. ラズパイのコンソールでセッションコードを確認
3. Webアプリでコードを入力
4. 体験設定で「振動」を有効化
5. テスト動画を再生して振動同期を確認
```

### 4.3 パフォーマンステスト

#### 同期精度テスト
```python
# sync_test.py
import time
import websockets
import json
import asyncio

async def sync_precision_test():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        
        # テスト用同期メッセージ送信
        test_times = [10.0, 10.5, 11.0, 11.5, 12.0]
        
        for test_time in test_times:
            start = time.time()
            
            message = {
                "event": "playback_sync",
                "data": {"current_time": test_time}
            }
            
            await websocket.send(json.dumps(message))
            response = await websocket.recv()
            
            end = time.time()
            latency = (end - start) * 1000  # ms
            
            print(f"Time: {test_time}s, Latency: {latency:.1f}ms")

# 実行
asyncio.run(sync_precision_test())
```

## 5. トラブルシューティング

### 5.1 よくある問題と解決方法

| 問題 | 症状 | 原因候補 | 解決方法 |
|------|------|----------|----------|
| **Arduino接続失敗** | "Serial port not found" | ドライバー未インストール | Arduino IDE再インストール |
| **振動しない** | コマンド送信しても無反応 | 配線間違い・電源不足 | 配線確認・外部電源確認 |
| **WiFi接続不安定** | 頻繁な切断 | 電波干渉・距離 | ルーター位置調整 |
| **同期ずれ** | 映像と振動のタイミング不一致 | ネットワーク遅延 | QoS設定・有線接続 |
| **Webアプリエラー** | ページが表示されない | CORS・ファイアウォール | 設定確認・ポート開放 |

### 5.2 診断コマンド

#### システム診断スクリプト
```python
# diagnosis.py - システム診断ツール
import subprocess
import serial
import socket
import requests

def diagnose_system():
    results = {}
    
    # ネットワーク接続チェック
    try:
        response = requests.get("http://google.com", timeout=5)
        results["internet"] = "OK"
    except:
        results["internet"] = "NG"
    
    # Arduino接続チェック
    try:
        ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
        ser.write(b'status\n')
        response = ser.readline()
        results["arduino"] = "OK" if response else "NG"
        ser.close()
    except:
        results["arduino"] = "NG"
    
    # CPU温度チェック (ラズパイ)
    try:
        temp_output = subprocess.check_output(['vcgencmd', 'measure_temp'])
        temperature = temp_output.decode().strip().split('=')[1]
        results["temperature"] = temperature
    except:
        results["temperature"] = "Unknown"
    
    # メモリ使用量チェック
    try:
        mem_output = subprocess.check_output(['free', '-h'])
        results["memory"] = "OK"
    except:
        results["memory"] = "NG"
    
    return results

if __name__ == "__main__":
    results = diagnose_system()
    for key, value in results.items():
        print(f"{key}: {value}")
```

### 5.3 ログ確認方法

#### システムログ確認
```bash
# ラズパイ システムログ
sudo journalctl -u 4dx-hub.service -f

# Arduino シリアルログ (screen使用)
sudo apt install screen
sudo screen /dev/ttyUSB0 9600

# Webサーバーログ
tail -f backend/logs/app.log

# ブラウザ開発者ツール
F12 → Console タブで JavaScript エラー確認
F12 → Network タブで WebSocket 通信確認
```

## 6. 運用・保守

### 6.1 定期メンテナンス

#### 週次チェック項目
```bash
# システム更新確認
sudo apt update && sudo apt list --upgradable

# ディスク使用量確認
df -h

# システム温度確認
vcgencmd measure_temp

# ログサイズ確認
sudo journalctl --disk-usage

# 接続テスト
python3 diagnosis.py
```

#### 月次メンテナンス
```bash
# システム更新適用
sudo apt upgrade -y

# ログローテーション
sudo journalctl --vacuum-time=30d

# バックアップ作成
sudo dd if=/dev/mmcblk0 of=/backup/raspios-$(date +%Y%m%d).img bs=4M status=progress

# 設定ファイルバックアップ
tar -czf ~/config-backup-$(date +%Y%m%d).tar.gz ~/4dx-home/config/
```

### 6.2 監視・アラート設定

#### システム監視スクリプト
```python
# monitor.py - システム監視
import psutil
import smtplib
from email.mime.text import MIMEText

class SystemMonitor:
    def __init__(self):
        self.thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'temperature': 70,
            'disk_usage': 90
        }
    
    def check_system_health(self):
        alerts = []
        
        # CPU使用率チェック
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > self.thresholds['cpu_percent']:
            alerts.append(f"High CPU usage: {cpu_percent}%")
        
        # メモリ使用率チェック
        memory = psutil.virtual_memory()
        if memory.percent > self.thresholds['memory_percent']:
            alerts.append(f"High memory usage: {memory.percent}%")
        
        # ディスク使用率チェック
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        if disk_percent > self.thresholds['disk_usage']:
            alerts.append(f"High disk usage: {disk_percent:.1f}%")
        
        return alerts
    
    def send_alert(self, alerts):
        if not alerts:
            return
            
        # メール通知 (オプション)
        # 実際の運用では適切なSMTP設定が必要
        print(f"ALERT: {', '.join(alerts)}")

# crontabに登録して定期実行
# */5 * * * * /usr/bin/python3 /home/pi/4dx-home/monitor.py
```

---

**更新日**: 2025年10月11日  
**バージョン**: 1.0  
**セットアップガイド作成者**: 4DX@HOME開発チーム