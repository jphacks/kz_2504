# 🔌 ラズベリーパイ接続・通信要件定義書

**最終更新**: 2025年10月12日 10:20 JST  
**対象**: Raspberry Pi + 4DX@HOME マイコンシステム統合  
**重要度**: ★★★ **マイコン統合必須要件**

## 🎯 **ラズベリーパイ統合要件概要**

### **システム構成**
```
[フロントエンド] ←→ [Cloud Run バックエンド] ←→ [Raspberry Pi + Arduino]
     ↑                      ↑                         ↑
   React/TS            FastAPI + WSS              Python + GPIO
   動画再生              中継・制御               ハードウェア制御
```

---

## 🔧 **ハードウェア要件**

### **1. ラズベリーパイ本体仕様**
- **推奨モデル**: Raspberry Pi 4 Model B (4GB以上)
- **OS**: Raspberry Pi OS (64-bit) 最新版
- **ネットワーク**: WiFi 802.11ac または Ethernet 100Mbps以上
- **ストレージ**: MicroSD 32GB以上 (Class 10)
- **電源**: USB-C 5V/3A 公式電源アダプター

### **2. Arduino/マイコン連携**
- **接続方式**: Serial通信 (UART) - /dev/ttyACM0
- **通信速度**: 115200 baud
- **プロトコル**: JSON形式コマンド送受信
- **タイムアウト**: 100ms以内の応答時間

### **3. アクチュエーター制御**
```python
# GPIO ピンアサイン例
ACTUATOR_PINS = {
    "VIBRATION": {"pin": 18, "pwm": True, "frequency": 1000},  # PWM制御
    "WATER": {"pin": 23, "relay": True},                      # リレー制御  
    "WIND": {"pin": 24, "pwm": True, "frequency": 25000},     # ファンPWM制御
    "FLASH": {"pin": 25, "pwm": True, "frequency": 5000},     # LED PWM制御
    "COLOR": {"pin": [12, 13, 19], "pwm": True, "rgb": True}, # RGB LED制御
}
```

---

## 📡 **ネットワーク通信要件**

### **1. WebSocket接続仕様**

#### **接続パラメーター**
- **URL**: `wss://fourdk-backend-333203798555.asia-northeast1.run.app/api/preparation/ws/{session_id}`
- **プロトコル**: WebSocket Secure (WSS)  
- **SSL/TLS**: TLS 1.2以上必須
- **接続タイムアウト**: 10秒
- **ハートビート**: 20秒間隔でping/pong

#### **帯域幅要件**
- **JSON同期データ受信**: 最大30KB/回 (demo1.json)
- **リアルタイム同期**: ~100bps (同期メッセージ)
- **状態フィードバック**: ~50bps (デバイス状態)
- **総帯域幅**: <1Mbps (十分な余裕)

#### **遅延要件**  
- **ネットワーク遅延**: <50ms (WiFi環境)
- **処理遅延**: <10ms (JSON→エフェクト変換)
- **エフェクト開始**: <30ms (GPIO制御)
- **総合遅延**: <100ms (動画同期許容範囲)

### **2. セキュリティ要件**

#### **SSL/TLS証明書**
```python
# SSL設定（本番環境）
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = True  # 必須
ssl_context.verify_mode = ssl.CERT_REQUIRED  # 必須

# Cloud Run証明書は自動的に信頼される（Let's Encrypt）
```

#### **認証・認可**
- **デバイス登録**: 6文字以内の製品コード認証
- **セッション管理**: session_id による接続制御
- **接続制限**: 1つのセッションに1台のマイコンまで

---

## 🐍 **Python実装要件**

### **1. 必須ライブラリ**
```bash
# WebSocket通信
pip install websockets==11.0.3
pip install aiohttp==3.9.1

# ハードウェア制御
pip install RPi.GPIO==0.7.1
pip install gpiozero==1.6.2

# Serial通信（Arduino連携）
pip install pyserial==3.5

# システム監視
pip install psutil==5.9.5

# SSL/TLS対応
# 標準ライブラリで十分（ssl, certifi）
```

### **2. ディレクトリ構造**
```
/home/pi/4dx-home/
├── main.py              # メインアプリケーション
├── config/
│   ├── settings.py      # 設定管理
│   └── hardware.py      # ハードウェア設定
├── communication/
│   ├── websocket_client.py  # WebSocket通信
│   ├── message_handler.py   # メッセージ処理
│   └── sync_processor.py    # 同期データ処理
├── hardware/
│   ├── actuator_controller.py  # アクチュエーター制御
│   ├── gpio_manager.py         # GPIO制御
│   └── arduino_bridge.py       # Arduino連携
├── monitoring/
│   ├── system_monitor.py   # システム監視
│   └── performance.py      # パフォーマンス測定
├── storage/
│   ├── sync_data/         # 同期データ保存
│   └── logs/              # ログファイル
└── tests/
    ├── test_hardware.py   # ハードウェアテスト
    └── test_communication.py  # 通信テスト
```

### **3. システム起動要件**

#### **自動起動設定**
```bash
# systemd サービス設定
sudo nano /etc/systemd/system/4dx-home.service
```

```ini
[Unit]
Description=4DX@HOME Device Controller
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/4dx-home
ExecStart=/usr/bin/python3 /home/pi/4dx-home/main.py
Restart=always
RestartSec=5
Environment=PYTHONPATH=/home/pi/4dx-home

# ログ設定
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### **起動シーケンス**
1. **システム起動**: ラズベリーパイ電源ON
2. **ネットワーク接続**: WiFi自動接続
3. **4DX@HOMEサービス起動**: systemdによる自動起動
4. **デバイス登録**: 製品コード使用
5. **WebSocket接続待機**: セッション参加待ち
6. **準備完了通知**: フロントエンドに状態報告

---

## ⚡ **パフォーマンス要件**

### **1. リアルタイム処理**
```python
# 処理時間目標値
PERFORMANCE_TARGETS = {
    "websocket_message_processing": 5,    # ms
    "json_parsing": 2,                    # ms  
    "effect_lookup": 1,                   # ms
    "gpio_control_start": 10,             # ms
    "serial_arduino_command": 20,         # ms
    "total_sync_latency": 50,             # ms (動画同期要件)
}
```

### **2. システムリソース**
- **CPU使用率**: <30% (通常動作時)  
- **メモリ使用量**: <200MB (Python + キャッシュ)
- **ストレージ**: <100MB (同期データ + ログ)
- **GPIO応答性**: <1ms (割り込み処理)

### **3. 安定性要件**
- **連続稼働時間**: 24時間以上
- **自動復旧**: ネットワーク切断からの自動再接続
- **エラー許容**: 通信エラー時の適切なフォールバック
- **リソース管理**: メモリリーク防止、ファイルハンドル管理

---

## 🛠️ **開発・テスト環境**

### **1. 開発環境構築**
```bash
# Python仮想環境作成
python3 -m venv /home/pi/4dx-venv
source /home/pi/4dx-venv/bin/activate

# 依存関係インストール  
pip install -r requirements.txt

# GPIO権限設定
sudo usermod -a -G gpio pi
sudo usermod -a -G dialout pi  # Serial通信用
```

### **2. ハードウェアテスト**
```python
# GPIO動作確認
python3 tests/test_hardware.py --test-all

# アクチュエーター動作確認  
python3 tests/test_hardware.py --actuator VIBRATION --intensity 0.5 --duration 2.0

# Arduino通信テスト
python3 tests/test_hardware.py --arduino-ping
```

### **3. 通信テスト**
```bash
# WebSocket接続テスト
python3 tests/test_communication.py --connect

# 同期データ受信テスト
python3 tests/test_communication.py --sync-test

# エンドツーエンドテスト（フロントエンド連携）
python3 tests/test_communication.py --e2e-test --session-id session_test123
```

---

## 🔧 **運用・メンテナンス要件**

### **1. 監視・ログ**
- **システムログ**: `/var/log/4dx-home/`
- **エラーログ**: 自動ローテーション (7日保持)
- **パフォーマンスメトリクス**: CPU・メモリ・温度監視
- **通信ログ**: WebSocket接続・切断・エラー記録

### **2. 自動更新**
- **アプリケーション更新**: git pull + サービス再起動
- **システム更新**: 自動セキュリティパッチ適用
- **設定管理**: 設定ファイルのバックアップ・復旧

### **3. トラブルシューティング**
- **ヘルスチェック**: 定期的なシステム状態確認
- **自動復旧**: 異常検出時の自動再起動
- **リモート診断**: SSH経由での遠隔メンテナンス
- **ハードウェア診断**: GPIO・Serial・センサー動作確認

---

## 📋 **実装チェックリスト**

### **Phase 1: 基盤構築** ✅
- [ ] ラズベリーパイ セットアップ完了
- [ ] 必要ライブラリ インストール完了  
- [ ] GPIO配線・テスト完了
- [ ] Arduino連携確認完了

### **Phase 2: 通信実装** 🔄
- [ ] WebSocket接続実装完了
- [ ] SSL/TLS設定完了
- [ ] JSON同期データ受信実装完了
- [ ] エフェクト処理実装完了

### **Phase 3: 統合テスト** ⏳
- [ ] フロントエンド連携テスト完了
- [ ] エンドツーエンド動作確認完了
- [ ] パフォーマンステスト完了
- [ ] 長時間稼働テスト完了

---

**推定実装期間**: 3-4日 (ハードウェア準備込み)  
**担当者**: マイコンエンジニア  
**サポート**: バックエンドエンジニア（WebSocket通信サポート）  
**完成目標**: フル機能統合システム 🎯