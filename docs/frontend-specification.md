# 4DX@HOME フロントエンド仕様書

## 概要

4DX@HOMEのWebアプリケーションフロントエンドは、React + TypeScriptで構築されたSPA（Single Page Application）です。動画再生とデバイス制御の同期を管理し、直感的なユーザーインターフェースを提供します。

## 技術スタック

### 主要フレームワーク・ライブラリ
- **React** 18.3.1 - UIライブラリ
- **TypeScript** 5.9.3 - 型安全なJavaScript
- **React Router DOM** 6.30.1 - SPA ルーティング

### 開発・ビルドツール
- **Vite** 7.1.9 - 高速ビルドツール
- **PostCSS** 8.5.6 - CSS処理
- **Tailwind CSS** 4.1.14 - ユーティリティファーストCSS

### 開発環境
- **@vitejs/plugin-react** 4.7.0 - Vite React プラグイン
- **@types/react** & **@types/react-dom** - React型定義

## アーキテクチャ

### ディレクトリ構造
```
frontend/4dathome-app/src/
├── App.tsx              # メインアプリケーションコンポーネント
├── main.tsx             # エントリーポイント
├── components/          # 再利用可能なUIコンポーネント
│   └── AppHeader.tsx    # アプリケーションヘッダー
├── pages/               # ページコンポーネント
│   ├── HomePage.tsx     # ホームページ
│   ├── PairingPage.tsx  # デバイスペアリング
│   ├── SelectPage.tsx   # 動画選択
│   └── PlayerPage.tsx   # 動画再生・制御
├── hooks/               # カスタムReactフック
├── types/               # TypeScript型定義
├── utils/               # ユーティリティ関数
└── assets/              # 静的アセット
```

### ルーティング構成
| パス | コンポーネント | 用途 |
|------|---------------|------|
| `/` | HomePage | メインランディングページ |
| `/session` | PairingPage | セッションコード入力・デバイスペアリング |
| `/selectpage` | SelectPage | 動画選択・カテゴリ閲覧 |
| `/player` | PlayerPage | 動画再生・リアルタイム制御 |

## 主要機能

### 1. セッション管理
- **セッションコード生成・入力**: 4桁のセッションコードによるデバイスペアリング
- **状態管理**: デバイス接続状態の監視とUI反映
- **自動接続**: WebSocket接続の確立と維持

### 2. 動画管理
- **動画一覧表示**: 利用可能な動画コンテンツの表示
- **カテゴリ分類**: ジャンル別動画表示
- **動画詳細**: メタデータ、サムネイル表示
- **動画選択**: 再生する動画の選択機能

### 3. 動画再生制御
- **HTML5 Video Player**: ブラウザネイティブ動画再生
- **再生制御**: 再生/一時停止、シーク、音量調整
- **タイムスタンプ同期**: リアルタイムでのタイムスタンプ送信
- **フルスクリーン対応**: モバイル・デスクトップ両対応

### 4. WebSocket通信
- **リアルタイム通信**: バックエンドとの双方向通信
- **自動再接続**: 接続断絶時の自動復旧
- **同期制御**: 動画再生とデバイス制御の同期

## API連携

### REST API エンドポイント
```typescript
// デバイス登録
POST /api/device/register
{
  "product_code": string,
  "session_id": string
}

// 動画一覧取得
GET /api/videos/available

// 動画選択
POST /api/videos/select
{
  "video_id": string,
  "session_id": string
}

// 準備開始
POST /api/preparation/start/{session_id}

// 準備状態確認
GET /api/preparation/status/{session_id}
```

### WebSocket接続
```typescript
// 接続エンドポイント
ws://localhost:8000/api/preparation/ws/{session_id}

// 送信メッセージ
{
  "type": "video_time_update",
  "current_time": number,
  "session_id": string
}

// 受信メッセージ
{
  "type": "sync_ready",
  "message": string
}
```

## 状態管理

### アプリケーション状態
```typescript
interface AppState {
  sessionId: string | null;
  deviceConnected: boolean;
  selectedVideo: VideoInfo | null;
  playbackState: PlaybackState;
  websocketConnection: WebSocket | null;
}

interface PlaybackState {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
}
```

### データフロー
1. **セッション作成** → セッションコード生成 → デバイス待機
2. **動画選択** → メタデータ取得 → 4DX効果データ準備
3. **再生開始** → WebSocket接続 → リアルタイム同期開始
4. **再生制御** → タイムスタンプ送信 → デバイス効果発動

## レスポンシブ対応

### ブレークポイント
- **Mobile**: < 768px
- **Tablet**: 768px - 1024px  
- **Desktop**: > 1024px

### デバイス最適化
- **スマートフォン**: タッチ操作最適化、縦画面対応
- **タブレット**: 中間サイズでの操作性向上
- **デスクトップ**: マウス操作、大画面対応

## パフォーマンス要件

### 同期精度
- **WebSocket レイテンシ**: < 50ms
- **動画同期精度**: ±50ms以内
- **UI応答速度**: < 100ms

### リソース管理
- **メモリ使用量**: < 100MB (動画再生時)
- **CPU使用率**: < 30% (通常時)
- **ネットワーク**: 最小限のデータ転送

## セキュリティ

### データ保護
- **HTTPS通信**: 本番環境での暗号化通信
- **CSP適用**: Content Security Policy設定
- **XSS対策**: React標準のエスケープ処理

### セッション管理
- **セッション有効期限**: 24時間
- **セッションコード**: 4桁ランダム生成
- **重複防止**: セッションコードの一意性保証

## 開発・デプロイ

### 開発コマンド
```bash
# 開発サーバー起動
npm run dev

# ビルド
npm run build

# プレビュー
npm run preview
```

### ビルド設定
- **出力ディレクトリ**: `dist/`
- **アセット最適化**: 自動圧縮・最適化
- **Tree Shaking**: 未使用コードの除去
- **Code Splitting**: 動的インポートによる分割

### 対応ブラウザ
- **Chrome**: 90+
- **Firefox**: 88+
- **Safari**: 14+
- **Edge**: 90+
- **Mobile Safari**: 14+
- **Chrome Mobile**: 90+

## 今後の拡張予定

### 機能拡張
- **多言語対応**: i18n実装
- **ユーザー設定**: カスタマイズ可能な設定
- **再生履歴**: 視聴履歴の保存・表示
- **お気に入り**: 動画ブックマーク機能

### 技術的改善
- **PWA対応**: オフライン機能、プッシュ通知
- **パフォーマンス監視**: リアルタイム監視ダッシュボード
- **A/Bテスト**: ユーザーエクスペリエンス最適化
- **アナリティクス**: ユーザー行動分析

## トラブルシューティング

### よくある問題
1. **WebSocket接続失敗**
   - ネットワーク環境確認
   - ファイアウォール設定確認
   - バックエンドサーバー状態確認

2. **動画再生できない**
   - ブラウザ対応フォーマット確認
   - ネットワーク帯域確認
   - コーデック対応状況確認

3. **同期ずれ**
   - ネットワークレイテンシ測定
   - デバイス時刻同期確認
   - WebSocket接続品質確認

### デバッグ情報
- **Console Logs**: 詳細なログ出力
- **Network Tab**: API通信状況確認
- **WebSocket Inspector**: リアルタイム通信監視