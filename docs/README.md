# 4DX@HOME システム仕様書

## はじめに

4DX@HOMEは、AI動画解析とリアルタイム同期技術により、スマートフォンでの動画視聴に物理フィードバックを追加する革新的なシステムです。本仕様書では、システムを構成する3つの主要コンポーネントの技術仕様を詳細に説明します。

## システム概要

### アーキテクチャ図
```
[フロントエンド] ←→ [バックエンド] ←→ [ハードウェア]
    React           FastAPI         Raspberry Pi
   WebSocket        WebSocket         Arduino
   TypeScript         Python           C++
```

### 主要機能
- **AI動画解析**: GPT-4o-mini Visionによる自動4DX効果生成
- **リアルタイム同期**: ±50ms以内の高精度同期
- **多様な物理効果**: 振動・光・風・水・色の5種類
- **セッション管理**: 4桁コードによる簡単ペアリング

## 仕様書構成

### 📱 [フロントエンド仕様書](./frontend-specification.md)
**React + TypeScript Webアプリケーション**

- **技術スタック**: React 18.3.1, TypeScript 5.9.3, Vite 7.1.9
- **主要機能**: 
  - セッション管理・デバイスペアリング
  - 動画選択・再生制御
  - WebSocketリアルタイム通信
  - レスポンシブUI (モバイル・デスクトップ対応)
- **アーキテクチャ**: SPA, Component-based, Hook-based状態管理
- **パフォーマンス**: 同期精度±50ms, レスポンシブ設計

### 🔧 [バックエンド仕様書](./backend-specification.md)  
**FastAPI WebサーバーとAPI**

- **技術スタック**: FastAPI 0.104.1, Uvicorn, WebSockets 11.0.3
- **主要機能**:
  - RESTful API (デバイス管理・動画管理)
  - WebSocketリアルタイム通信
  - セッション管理・同期制御
  - 動画メタデータ管理
- **アーキテクチャ**: 非同期処理, Pydanticデータ検証, CORS対応
- **スケーラビリティ**: 100同時セッション, 1000 req/sec

### ⚙️ [ハードウェア仕様書](./hardware-specification.md)
**Raspberry Pi + Arduino 物理制御システム**

- **技術スタック**: Python 3.9+, Arduino C++, MQTT, Serial通信
- **主要機能**:
  - 5種類物理効果制御 (振動・光・風・水・色)
  - TCP/WebSocketリアルタイム通信
  - 並列処理・タイムライン管理
  - 安全機能・エラー回復
- **アーキテクチャ**: デバイスハブ(RPi) + アクチュエーター制御(Arduino)
- **物理仕様**: 手のひらサイズ筐体, 5V/12V電源系統

## 技術的特徴

### 🎯 リアルタイム同期
- **WebSocket双方向通信**による継続的時刻同期
- **マルチスレッド処理**によるノンブロッキング制御
- **予測補正**によるネットワーク遅延対応

### 🔄 データフロー
1. **フロントエンド**: 動画再生・タイムスタンプ送信
2. **バックエンド**: セッション管理・同期データ転送
3. **ハードウェア**: タイムライン処理・物理効果制御

### 🛡️ 安全・信頼性
- **入力検証**: Pydanticによる厳密な型チェック
- **エラー回復**: 自動再接続・フォールバック機能
- **物理安全**: 過熱保護・動作時間制限・緊急停止

## 開発・デプロイ

### 開発環境セットアップ
```bash
# フロントエンド
cd frontend/4dathome-app
npm install
npm run dev

# バックエンド  
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# ハードウェア
cd hardware
pip install -r device-hub/requirements.txt
python3 hardware_server.py
```

### システム要件
- **フロントエンド**: Node.js 18+, モダンブラウザ
- **バックエンド**: Python 3.9+, 512MB RAM
- **ハードウェア**: Raspberry Pi 3 Model B, Arduino Uno, 12V/5A電源

## API一覧

### RESTful API
- `POST /api/device/register` - デバイス登録
- `GET /api/videos/available` - 動画一覧取得
- `POST /api/videos/select` - 動画選択
- `POST /api/preparation/start/{session_id}` - 準備開始

### WebSocket
- `ws://server/api/preparation/ws/{session_id}` - リアルタイム通信

### デバイス制御プロトコル
- **振動**: MQTT `/vibration/{mode}`
- **光**: Serial `"COLOR R G B"`  
- **風**: Serial `"ON"/"OFF"`
- **水**: Serial `"SPLASH"`

## パフォーマンス指標

| メトリクス | 目標値 | 用途 |
|-----------|--------|------|
| API応答時間 | < 100ms | ユーザビリティ |
| WebSocket遅延 | < 50ms | 同期精度 |
| 同期精度 | ±50ms | 体験品質 |
| 同時セッション | 100+ | スケーラビリティ |
| メモリ使用量 | < 512MB | リソース効率 |

## トラブルシューティング

### よくある問題
1. **同期ずれ**: ネットワーク環境・処理負荷確認
2. **WebSocket接続失敗**: ファイアウォール・CORS設定確認  
3. **デバイス無応答**: シリアル接続・Arduino状態確認
4. **動画再生できない**: ブラウザ対応・コーデック確認

### ログ確認
```bash
# バックエンドログ
tail -f backend/logs/app.log

# ハードウェアログ  
journalctl -u 4dx-home.service -f

# フロントエンド
# ブラウザ開発者ツール Console
```

## 今後の拡張計画

### Phase 1: 機能拡張
- **AI動画解析**: GPT-4o-mini Vision API統合
- **多動画対応**: ユーザーアップロード機能
- **カスタマイズ**: ユーザー設定・プロファイル

### Phase 2: 技術向上
- **クラウド化**: スケーラブルクラウドデプロイ
- **リアルタイムOS**: 確定的レスポンス
- **機械学習**: 個人最適化・予測制御

### Phase 3: 新体験
- **多感覚拡張**: 温度・香り・触覚の追加
- **ソーシャル**: 複数人同時体験
- **VR/AR**: 仮想現実との融合

## まとめ

4DX@HOMEは、最新のWeb技術、リアルタイム通信、組み込みシステムを統合し、従来の動画視聴体験を革新する包括的なシステムです。各コンポーネントが独立して動作しながら、高精度な同期により統一された体験を提供します。

詳細な技術仕様については、各コンポーネントの専用仕様書をご参照ください。

---

**更新日**: 2025年10月12日  
**バージョン**: 1.0.0  
**対象**: 開発チーム・技術仕様確認