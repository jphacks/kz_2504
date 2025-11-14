# 4DX@HOME Raspberry Pi Server - 実装状況まとめ

最終更新日: 2025年11月8日

---

## 📋 実装状況サマリー

### ✅ 完了済み機能

| 機能カテゴリ | 実装状況 | 備考 |
|------------|---------|------|
| **WebSocket通信** | ✅ 完了 | Cloud Run APIとの双方向通信 |
| **MQTT通信** | ✅ 完了 | Mosquitto経由でESP-12E制御 |
| **タイムライン処理** | ✅ 完了 | ±100ms精度で同期 |
| **イベントマッピング** | ✅ 完了 | 4DXHOMEイベント→MQTTコマンド変換 |
| **デバイス管理** | ✅ 完了 | ハートビート監視、オンライン状態管理 |
| **キャッシュ管理** | ✅ 完了 | タイムラインデータのローカル保存 |
| **通信ログ** | ✅ 完了 | 送受信メッセージの記録 |
| **Flask HTTPサーバー** | ✅ 完了 | ステータスAPI、制御UI |
| **デバッグコントローラー** | ✅ **NEW!** | スマホ対応Web UI、ALL STOP機能 |
| **systemd対応** | ✅ 完了 | 自動起動、サービス管理 |
| **再接続ロジック** | ✅ 完了 | WebSocket切断時の自動再接続 |
| **エラーハンドリング** | ✅ 完了 | 適切なログ出力とリカバリー |

---

## 🎮 デバッグコントローラーの新機能

### 概要

Raspberry Piと同じWiFiネットワーク上のデバイス（スマホ、タブレット、PC）から、簡単にアクチュエータを操作できるWebベースのデバッグツールです。

### アクセス方法

```
http://<Raspberry_Pi_IP>:8000/
```

### 主な機能

#### 1. 🛑 ALL STOP（緊急停止）

**説明**: すべてのアクチュエータを即座に停止する緊急停止ボタン

**停止されるデバイス**:
- Wind（風モーター）→ OFF
- Light（単体LED）→ OFF
- RGB LED → 赤色に戻る
- Motor1（振動モーター1）→ OFF
- Motor2（振動モーター2）→ OFF

**実装詳細**:
```javascript
// frontend/templates/controller.html
async function emergencyStopAll() {
    const stopCommands = [
        { topic: '/4dx/wind', payload: 'OFF' },
        { topic: '/4dx/light', payload: 'OFF' },
        { topic: '/4dx/color', payload: 'RED' },
        { topic: '/4dx/motor1/control', payload: 'OFF' },
        { topic: '/4dx/motor2/control', payload: 'OFF' }
    ];
    
    // 並列送信で即座に停止
    await Promise.all(
        stopCommands.map(cmd => fetch(publishUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cmd)
        }))
    );
}
```

#### 2. デバイス個別制御

**ESP1 (Water/Wind)**:
- Water単発トリガー
- Water Loop ON/OFF
- Wind ON/OFF

**ESP2 (LED)**:
- 単体LED: ON/Blink Slow/Blink Fast/OFF
- RGB LED: 6色切り替え (Red, Green, Blue, Yellow, Cyan, Purple)

**ESP3/4 (Motor)**:
- 8種類の振動パターン
  - 強度: 強/中強/中弱/弱
  - パターン: ハートビート/Rumble Fast/Rumble Slow
  - OFF

#### 3. リアルタイムステータス表示

- **サーバー接続状態**: ✅/❌ で表示
- **デバイス数**: オンライン/総数を5秒ごと更新
- **MQTT接続状態**: 🟢接続中/🔴切断

#### 4. スマホ対応UI

- レスポンシブデザイン
- タップしやすいボタンサイズ
- 視覚的なフィードバック（色変化、アニメーション）

---

## 📂 関連ファイル

### デバッグコントローラー関連

| ファイル | 説明 |
|---------|------|
| `templates/controller.html` | デバッグコントローラーのHTML/CSS/JS |
| `src/server/app.py` | Flask HTTPサーバー（`/api/mqtt/publish`エンドポイント提供） |
| `DEBUG_CONTROLLER.md` | デバッグコントローラーの使い方ドキュメント |

### コア機能

| ファイル | 説明 |
|---------|------|
| `main.py` | メインアプリケーション |
| `config.py` | 環境変数と設定管理 |
| `src/mqtt/broker.py` | MQTTブローカークライアント |
| `src/mqtt/event_mapper.py` | イベント→MQTTコマンドマッピング |
| `src/mqtt/device_manager.py` | デバイス管理とハートビート監視 |
| `src/api/websocket_client.py` | Cloud Run APIへのWebSocket接続 |
| `src/api/message_handler.py` | WebSocketメッセージハンドラー |
| `src/timeline/processor.py` | タイムライン処理エンジン |
| `src/timeline/cache_manager.py` | タイムラインキャッシュ管理 |

### ドキュメント

| ファイル | 説明 |
|---------|------|
| `README.md` | プロジェクト概要 |
| `QUICK_START.md` | クイックスタートガイド |
| `DEBUG_CONTROLLER.md` | デバッグコントローラーの詳細 |
| `IMPLEMENTATION_PLAN.md` | 実装計画 |
| `TIME_TOLERANCE_SPEC.md` | 時間同期仕様 |
| `IMPLEMENTATION_STATUS.md` | このファイル（実装状況まとめ） |

---

## 🔧 動作環境

### ハードウェア

- **Raspberry Pi 3 Model B** 以上
- **メモリ**: 1GB以上
- **ストレージ**: 8GB以上（SDカード）
- **WiFi**: 2.4GHz対応（ESP-12Eと同じネットワーク）

### ソフトウェア

- **OS**: Raspberry Pi OS (Raspbian) Bullseye 以降
- **Python**: 3.9以上
- **MQTT Broker**: Mosquitto 2.0以上

### ネットワーク

- **ラズパイとESP-12E**: 同じローカルネットワーク（MQTT通信用）
- **ラズパイとCloud Run API**: インターネット接続（WebSocket通信用）
- **スマホ/PCとラズパイ**: 同じローカルネットワーク（デバッグUI用）

---

## 📡 通信フロー

### 通常動作時

```
[Cloud Run API]
    ↓ WebSocket (sync_data_bulk_transmission)
[Raspberry Pi Server]
    ↓ タイムライン処理
[Timeline Processor]
    ↓ イベント検出
[Event Mapper]
    ↓ MQTT変換
[MQTT Broker]
    ↓ MQTT配信
[ESP-12E Devices]
```

### デバッグコントローラー使用時

```
[スマホ/PC ブラウザ]
    ↓ HTTP POST (/api/mqtt/publish)
[Flask Server]
    ↓ MQTT配信
[MQTT Broker]
    ↓ MQTT配信
[ESP-12E Devices]
```

---

## 🧪 テスト手順

### 1. サーバー起動テスト

```bash
cd hardware/rpi_server
source venv/bin/activate
python main.py demo1
```

**期待される出力**:
```
============================================================
4DX@HOME Raspberry Pi Server 起動
============================================================
Device Hub ID: DH001
Session ID: demo1
Cloud Run API: https://...
============================================================
✓ MQTT接続完了
✓ Flaskサーバー起動完了
WebSocket接続開始...
WebSocket接続成功
```

### 2. デバッグコントローラーアクセステスト

1. ラズパイのIPアドレスを確認: `hostname -I`
2. スマホをラズパイと同じWiFiに接続
3. ブラウザで `http://<IP>:8000/` にアクセス
4. 「✅ サーバー接続完了」と表示されることを確認

### 3. デバイス制御テスト

1. 「Water (単発)」ボタンをタップ
2. ESP1デバイスのサーボモーターが動作することを確認
3. 「Wind ON」→「Wind OFF」で風モーターの動作確認
4. RGB LED色変更ボタンで色が変わることを確認

### 4. 緊急停止テスト

1. 複数のエフェクトを起動（Wind ON, モーター起動など）
2. 「🛑 ALL STOP」ボタンをタップ
3. 全デバイスが即座に停止することを確認

### 5. WebSocket統合テスト

1. Cloud Run APIのフロントエンド（debug_frontend）を起動
2. セッション「demo1」で動画準備開始
3. タイムラインデータをアップロード
4. ラズパイサーバーのログでタイムライン受信を確認:
   ```
   タイムラインデータ処理開始: video_id=...
   タイムラインデータ処理完了
   ```

5. 動画を再生
6. タイムラインに従ってデバイスが動作することを確認

---

## 🐛 既知の問題と対処法

### 問題1: ポート8000が既に使用中

**症状**:
```
OSError: [Errno 98] Address already in use
```

**対処法**:
```bash
# 停止スクリプトを実行
bash scripts/stop_server.sh

# または手動でプロセスを停止
sudo lsof -ti:8000 | xargs kill -9
```

### 問題2: WebSocket接続が頻繁に切断される

**原因**: ネットワーク不安定、Cloud Run APIのタイムアウト

**対処法**:
- `.env`ファイルの`WS_PING_INTERVAL`を短くする（例: 15秒）
- 自動再接続機能が動作していることを確認

### 問題3: デバイスが反応しない

**原因**: MQTTブローカー未起動、ESPデバイスオフライン

**確認方法**:
```bash
# Mosquitto状態確認
sudo systemctl status mosquitto

# ハートビート確認
mosquitto_sub -h localhost -t "/4dx/heartbeat"
```

**対処法**:
```bash
# Mosquitto再起動
sudo systemctl restart mosquitto

# ESPデバイス再起動（電源OFF→ON）
```

---

## 🚀 今後の拡張予定

### 短期（1-2週間）

- [ ] デバッグコントローラーに再生コントロール追加（Start/Stop/Reset）
- [ ] タイムラインプレビュー機能（現在の再生時刻表示）
- [ ] デバイスごとの詳細ステータス表示

### 中期（1ヶ月）

- [ ] ログビューワー機能（Web UIでログ確認）
- [ ] 通信遅延測定ツール
- [ ] 複数セッション対応

### 長期（3ヶ月）

- [ ] デバイス認証機能
- [ ] HTTPS対応
- [ ] カスタムタイムライン作成ツール

---

## 📚 参考資料

### プロジェクト内ドキュメント

- [README.md](./README.md) - プロジェクト概要
- [QUICK_START.md](./QUICK_START.md) - クイックスタートガイド
- [DEBUG_CONTROLLER.md](./DEBUG_CONTROLLER.md) - デバッグコントローラー詳細
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - 実装計画
- [TIME_TOLERANCE_SPEC.md](./TIME_TOLERANCE_SPEC.md) - 時間同期仕様

### バックエンドAPI

- Cloud Run API仕様: `backend/debug/CONFIG.md`
- WebSocketプロトコル: `backend/app/api/playback_control.py`
- ストップ信号仕様: `debug_frontend/STOP_SIGNAL_SPEC.md`

### MQTT

- 4DXHOME MQTTサーバー: `4DXHOME/mqtt_server.py`
- イベントマッピング: `src/mqtt/event_mapper.py`

---

## 👥 開発者向けメモ

### コード修正時の注意点

1. **イベントマッピング変更時**
   - `src/mqtt/event_mapper.py` の `EVENT_MAP` を修正
   - `4DXHOME/mqtt_server.py` の `event_map` と互換性を保つこと

2. **WebSocketメッセージ追加時**
   - `src/api/message_handler.py` にハンドラーを追加
   - バックエンドAPIとメッセージ形式を統一

3. **環境変数追加時**
   - `config.py` に設定追加
   - `.env.example` を更新
   - `README.md` の設定説明を更新

4. **デバッグUI変更時**
   - `templates/controller.html` を編集
   - レスポンシブデザインを維持
   - スマホでの動作確認必須

### デプロイ前チェックリスト

- [ ] `.env` ファイルの機密情報確認
- [ ] Cloud Run API URLが本番環境になっているか
- [ ] MQTTブローカーが起動しているか
- [ ] デバイスハートビートが受信できるか
- [ ] systemdサービスが正常起動するか
- [ ] デバッグコントローラーがスマホからアクセス可能か

---

## 📞 サポート

問題が発生した場合は、以下の情報を添えて開発チームに連絡してください:

1. **エラーメッセージ**
2. **ログファイル**: `data/rpi_server.log`
3. **システム情報**: `uname -a`
4. **Raspberry Piモデル**
5. **発生時の操作内容**

---

**最終更新**: 2025年11月8日  
**バージョン**: 1.1.0  
**主な変更**: デバッグコントローラーのALL STOP機能追加
