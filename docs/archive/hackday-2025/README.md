# Hack Day アーカイブ

このディレクトリは、将来的にHack Day時点の仕様書をアーカイブする用途で準備されています。

## 📅 タイムライン

### Hack Day（2025年10月11-12日）
- 初回実装完了
- 基本的なシステム構成
- ローカル開発環境での動作確認

### Award Day 2025（2025年11月）
- **Cloud Runデプロイ完了**
- **3層アーキテクチャへの変更**
- **ストップ処理機能追加**
- **デバイステスト機能追加**
- **詳細ログシステム実装**

## 📂 現在の仕様書の状態

**2025年11月14日更新**: Hack Day時点の仕様書を本ディレクトリに移動し、新しい仕様書（Version 2.0.0）を`docs/`直下に配置しました。

### アーカイブされたファイル

- `backend-specification.md` - ⚠️ Hack Day時点（最新実装へのリンク付き）
- `frontend-specification.md` - ⚠️ Hack Day時点（最新実装へのリンク付き）
- `hardware-specification.md` - ⚠️ Hack Day時点（最新実装へのリンク付き）
- `images.md` - 📸 Hack Day時点の画像集

### 新しい仕様書（docs/直下）

**AwardDay（2025年11月）時点の最新実装を反映**:
- `../../backend-specification-awardday.md` - ✨ Version 2.0.0
- `../../frontend-specification-awardday.md` - ✨ Version 2.0.0
- `../../hardware-specification-awardday.md` - ✨ Version 2.0.0

各ファイルには以下が含まれています：
- Cloud Run デプロイ情報
- 3層アーキテクチャ詳細
- ストップ処理・デバイステスト機能
- 詳細なコード例とAPI仕様

## 🔗 最新情報へのリンク

最新の実装については、以下を参照してください：

### バックエンド
- **実装**: `../../../backend/app/`
- **デプロイガイド**: `../../../backend/DEPLOYMENT_GUIDE.md`
- **詳細設計**: `../../backend-report/`
- **デバッグ環境**: `../../../debug_hardware/`

### フロントエンド
- **実装**: `../../../frontend/4dathome-app/`
- **本番デプロイ**: https://kz-2504.onrender.com
- **デバッグ環境**: `../../../debug_frontend/`
- **本番フロー仕様**: `../../../debug_frontend/PRODUCTION_FLOW_SETUP.md`

### ハードウェア
- **Raspberry Pi Server**: `../../../hardware/rpi_server/`
- **アーキテクチャ**: `../../../debug_hardware/ARCHITECTURE.md`
- **API仕様**: `../../../debug_hardware/API_REFERENCE.md`

### ドキュメント
- **プロジェクトREADME**: `../../README.md`
- **クイックスタート**: `../../../QUICK_START.md`
- **テストガイド**: `../../../TESTING_GUIDE.md`

## 💡 今後のアーカイブ方針

将来、仕様書を全面的に刷新する場合は、Hack Day時点の仕様書をこのディレクトリに移動し、新しい仕様書を`docs/`直下に配置することを推奨します。

### アーカイブ手順（参考）

```powershell
# Hack Day時点の仕様書をアーカイブに移動
Move-Item docs\backend-specification.md docs\archive\hackday-2025\
Move-Item docs\frontend-specification.md docs\archive\hackday-2025\
Move-Item docs\hardware-specification.md docs\archive\hackday-2025\

# 新しい仕様書を作成
# （最新実装を反映した新仕様書を docs/ 直下に配置）
```

---

**作成日**: 2025年11月14日  
**目的**: Hack Day時点の仕様書を保存し、プロジェクトの進化を記録する
