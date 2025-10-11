# 💰 GCP無料枠デプロイメントガイド

## 🎯 **目標**
- クレジットカード登録必要だが料金発生を避ける
- 無料枠内でCloud Runデプロイを実現
- 予算アラートで安全性確保

## 📊 **GCP無料枠 制限値**

### **Cloud Run 無料枠**
```
✅ リクエスト数: 月2,000,000回まで
✅ CPU時間: 月180,000 vCPU秒まで  
✅ メモリ時間: 月360,000 GiB秒まで
✅ ネットワーク: 月1GB まで
```

### **Container Registry 無料枠**
```
✅ ストレージ: 0.5GB まで
✅ ネットワーク: 月1GB まで  
```

### **Cloud Build 無料枠**
```
✅ ビルド時間: 1日120分まで
```

## 🔧 **無料枠内設定手順**

### **Step 1: GCPコンソールアクセス**
1. https://console.cloud.google.com にアクセス
2. プロジェクト選択で `fourdk-home-2024` を確認
3. 「プロジェクトを選択」→ `fourdk-home-2024` (4DXatHOME Backend) をクリック

### **Step 2: 課金設定（無料枠保護付き）**
1. 左メニュー「お支払い」をクリック  
2. 「課金アカウントをリンク」を選択
3. **重要**: 「無料試用版の有効化」を選択（$300クレジット）
4. クレジットカード情報入力（検証用、自動課金なし）
5. **「無料枠を超過した場合は自動的に課金しない」設定を確認**

### **Step 3: 予算アラート設定**
```bash
# 予算上限設定（$5で警告）
1. 「予算とアラート」→「予算を作成」
2. 予算名: "4DXatHOME Safety Budget"  
3. 予算額: $5 USD
4. アラート: 50%, 90%, 100%で通知
5. プロジェクト停止: 100%で設定（推奨）
```

### **Step 4: API有効化**
```bash
# コマンドラインで実行
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

## ⚠️ **料金発生回避のベストプラクティス**

### **Cloud Run設定**
```yaml
# 最小リソース設定
CPU: 0.25 vCPU (最小値)
メモリ: 256Mi (最小値)  
最大インスタンス数: 1
リクエストタイムアウト: 60秒
同時実行数: 1
```

### **監視ポイント**
- ✅ 月間リクエスト数 < 2,000,000
- ✅ CPU使用時間 < 180,000秒
- ✅ メモリ使用量 < 360,000 GiB秒
- ✅ ストレージ < 0.5GB

### **料金発生回避チェックリスト**
- [ ] 無料試用版($300クレジット)有効化
- [ ] 自動課金無効化設定
- [ ] 予算アラート設定($5上限)
- [ ] 最小リソース設定
- [ ] 定期的な使用量確認

## 🚀 **次のアクション**

### **課金設定後に実行**
```bash
# プロジェクト確認
gcloud config get-value project

# API有効化
gcloud services enable run.googleapis.com containerregistry.googleapis.com cloudbuild.googleapis.com

# 課金設定確認  
gcloud services list --enabled
```

## 📞 **サポート情報**

### **課金に関する質問**
- GCPサポート: https://cloud.google.com/support
- 無料枠詳細: https://cloud.google.com/free/docs/free-cloud-features

### **緊急時対応**
1. プロジェクト無効化: `gcloud projects delete fourdk-home-2024`
2. 予算超過アラート確認
3. リソース削除: Cloud Runサービス停止

---

**⚠️ 重要**: 無料枠を超過しても自動課金されない設定を必ず確認してください。