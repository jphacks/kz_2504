# 🔒 機密情報管理ガイド

## 概要

このプロジェクトでは、実際のCloud Run URLやその他の機密情報をGitHubリポジトリから除外するため、以下のセキュリティ対策を実施しています。

## 📋 除外されているファイル

### 環境変数ファイル（`.env`）

以下のディレクトリの `.env` ファイルには実際のCloud Run URLが含まれますが、`.gitignore` により除外されています：

```
backend/.env
debug_frontend/.env
debug_hardware/.env
hardware/rpi_server/.env
```

**使用方法**:
```bash
# .env.example をコピーして .env を作成
cp .env.example .env

# 実際のCloud Run URLを設定
# CLOUD_RUN_API_URL=https://your-actual-url.run.app
```

### ドキュメント・スクリプトファイル

実際のURLを含むため、以下のファイルもGit追跡から除外されています：

- `TESTING_GUIDE.md` - テストガイド（実際のURL含む）
- `QUICK_START.md` - クイックスタートガイド（実際のURL含む）
- `quick_start_test.ps1` - テストスクリプト（実際のURL含む）
- `backend/DEPLOYMENT_GUIDE.md` - デプロイガイド（デプロイ履歴含む）
- `.github/copilot-instructions.md` - Copilot指示書（デプロイ例含む）
- `communication_test_dashboard.html` - テストダッシュボード（実際のURL含む）

### デバッグディレクトリ

以下のディレクトリ全体が除外されています：

```
backend/debug/           # デバッグツール・スクリプト
debug_frontend/          # フロントエンドデバッグツール
debug_hardware/          # ハードウェアシミュレータ
4DXHOME/                # レガシーコード
docs/backend-report/     # バックエンドレポート
```

## 📝 Exampleファイル（公開用テンプレート）

実際のURLの代わりに、プレースホルダーを含むexampleファイルを用意しています：

| 実ファイル（Git除外） | Exampleファイル（Git追跡） |
|----------------------|---------------------------|
| `TESTING_GUIDE.md` | `TESTING_GUIDE.example.md` |
| `QUICK_START.md` | `QUICK_START.example.md` |
| `backend/DEPLOYMENT_GUIDE.md` | `backend/DEPLOYMENT_GUIDE.example.md` |
| `backend/.env` | `backend/.env.example` |
| `debug_frontend/.env` | `debug_frontend/.env.example` |
| `debug_hardware/.env` | `debug_hardware/.env.example` |
| `hardware/rpi_server/.env` | `hardware/rpi_server/.env.example` |

## 🔧 初期セットアップ手順

### 1. Cloud Run URLの取得

```bash
# Google Cloud CLIでURLを取得
gcloud run services describe fdx-home-backend-api \
  --region=asia-northeast1 \
  --format="value(status.url)"
```

### 2. 環境変数ファイルの作成

各ディレクトリで `.env.example` をコピーして `.env` を作成し、実際のURLを設定します：

```bash
# backendディレクトリ
cd backend
cp .env.example .env
# エディタで .env を開き、実際のURLを設定

# debug_frontendディレクトリ
cd ../debug_frontend
cp .env.example .env
# エディタで .env を開き、実際のURLを設定

# debug_hardwareディレクトリ
cd ../debug_hardware
cp .env.example .env
# エディタで .env を開き、実際のURLを設定

# hardware/rpi_serverディレクトリ
cd ../hardware/rpi_server
cp .env.example .env
# エディタで .env を開き、実際のURLを設定
```

### 3. ドキュメントファイルの作成

必要に応じて、exampleファイルをコピーして実際のURLを含むバージョンを作成します：

```bash
# テストガイド
cp TESTING_GUIDE.example.md TESTING_GUIDE.md
# エディタで TESTING_GUIDE.md を開き、実際のURLを設定

# クイックスタートガイド
cp QUICK_START.example.md QUICK_START.md
# エディタで QUICK_START.md を開き、実際のURLを設定

# デプロイガイド
cp backend/DEPLOYMENT_GUIDE.example.md backend/DEPLOYMENT_GUIDE.md
# エディタで backend/DEPLOYMENT_GUIDE.md を開き、実際のURLを設定
```

## ⚠️ 重要な注意事項

### Gitコミット前の確認

コミット前に、実際のURLが含まれていないことを確認してください：

```bash
# Git追跡ファイル内のURL検索
git grep -n "333203798555"  # 実際のプロジェクトIDで検索
git grep -n "asia-northeast1.run.app"  # Cloud Run URLで検索

# 除外されているファイルの確認
git check-ignore TESTING_GUIDE.md QUICK_START.md backend/.env
```

### .env ファイルのバックアップ

`.env` ファイルはGit管理外のため、以下の方法でバックアップを推奨します：

1. **チーム内の安全な場所で共有**（Google Drive、社内Wiki等）
2. **個人のローカルバックアップ**
3. **パスワード管理ツール**での保存

## 🔍 セキュリティチェックリスト

プルリクエスト作成前に以下を確認してください：

- [ ] `.env` ファイルがコミットされていない
- [ ] 実際のCloud Run URLがGit追跡ファイルに含まれていない
- [ ] Exampleファイルにはプレースホルダーのみが含まれている
- [ ] 新しい設定ファイルを追加した場合、`.gitignore` に追加されている
- [ ] コミット対象のファイルに機密情報が含まれていない

## 📚 関連ドキュメント

- `.gitignore` - Git除外設定
- `backend/.env.example` - バックエンド環境変数テンプレート
- `TESTING_GUIDE.example.md` - テストガイドテンプレート
- `QUICK_START.example.md` - クイックスタートテンプレート

---

**最終更新**: 2025年11月7日
