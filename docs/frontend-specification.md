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
| `/` | HomePage | メインページ |
| `/session` | PairingPage | セッションコード入力・デバイスペアリング |
| `/selectpage` | SelectPage | 動画選択・ランキング閲覧 |
| `/player` | PlayerPage | 動画再生・デバイス同期 |

## 主要機能

### 1. セッション管理
- **セッションコード生成・入力**: 6桁のセッションコードによるデバイスペアリング
- **状態管理**: デバイス接続状態の監視とUI反映
- **自動接続**: WebSocket接続の確立と維持

### 2. 動画管理
- **動画一覧表示**: 利用可能な動画コンテンツの表示
- **カテゴリ分類**: ジャンル別動画表示
- **ランキング**: ランキング表示
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
- **同期制御**: 動画再生とデバイスの同期


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


## 今後の拡張予定


### 機能拡張
- **多言語対応**: i18n実装
- **ユーザー設定**: カスタマイズ可能な設定
- **再生履歴**: 視聴履歴の保存・表示
- **レスポンシブ対応**: スマートフォンやタブレットに対応する
- **お気に入り**: 動画ブックマーク機能
