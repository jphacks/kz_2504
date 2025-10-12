# 💰 GCP無料枠 デプロイ戦略

## 🆓 **無料枠の制限と対策**

### **Cloud Runの無料枠**
- ✅ **リクエスト**: 200万回/月まで無料
- ✅ **CPU時間**: 18万vCPU秒/月まで無料
- ✅ **メモリ**: 36万GiB秒/月まで無料
- ✅ **ネットワーク**: 1GB/月まで無料

### **Container Registry/Artifact Registry**
- ✅ **ストレージ**: 0.5GB/月まで無料
- ✅ **ネットワーク**: 1GB/月まで無料

### **Cloud Build**
- ✅ **ビルド時間**: 120分/日まで無料

## 💡 **料金発生を防ぐ安全設定**

### **1. 予算アラート設定**
```
予算上限: $1 USD（最小設定）
アラート: 50%、90%、100%で通知
自動停止: 100%到達時
```

### **2. Cloud Runリソース制限**
```yaml
# 最小構成設定
resources:
  limits:
    cpu: "1000m"        # 1 vCPU
    memory: "512Mi"     # 512MB RAM
  requests:
    cpu: "100m"         # 0.1 vCPU（最小）
    memory: "128Mi"     # 128MB RAM（最小）

# 同時実行制限
concurrency: 80         # 同時接続数制限
max_instances: 10       # 最大インスタンス数
min_instances: 0        # 最小インスタンス数（0で節約）
```

### **3. 自動スケールダウン設定**
```
timeout: 300s           # 5分でタイムアウト
idle_timeout: 60s       # 1分でアイドルタイムアウト
```

## 📋 **安全な課金設定手順**

### **Step 1: 予算・アラート設定（最優先）**
1. GCPコンソール → 請求
2. 予算とアラート作成
3. $1制限、50%/90%/100%アラート
4. 請求管理者にメール通知

### **Step 2: 課金アカウント作成**
1. クレジットカード情報登録
2. $300無料クレジット確認
3. 自動課金ON（無料枠超過時のみ）

### **Step 3: API有効化**
```bash
# 必要最小限のAPIのみ
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com  
gcloud services enable cloudbuild.googleapis.com
```

## 🔒 **料金発生防止策**

### **リソース監視コマンド**
```bash
# 使用量確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10
gcloud run services list --region=asia-northeast1

# 予算状況確認
gcloud billing budgets list --billing-account=BILLING_ACCOUNT_ID
```

### **緊急停止コマンド**
```bash
# Cloud Runサービス停止
gcloud run services delete fourdk-home --region=asia-northeast1

# 全リソース確認・削除
gcloud projects delete fourdk-home-2024  # 最終手段
```

## 📊 **予想コスト試算**

### **4DX@HOME使用パターン**
```
想定利用:
- デモ・テスト: 1週間
- リクエスト: 1日1000回 × 7日 = 7,000回
- CPU時間: 1リクエスト1秒 × 7,000 = 7,000秒
- メモリ: 128MB × 7,000秒 = 896MB秒
- ストレージ: Docker image 250MB

計算結果: 完全に無料枠内
```

### **超過リスク要因**
- ❌ 大量のWebSocket接続（長時間保持）
- ❌ 高頻度のAPI呼び出し
- ❌ 複数インスタンスの常時稼働
- ❌ 大きなDockerイメージ（>500MB）

### **対策**
- ✅ WebSocket接続タイムアウト設定
- ✅ API呼び出し制限
- ✅ min_instances=0設定
- ✅ 軽量Dockerイメージ（250MB）

## 🚀 **実行プラン**

### **今すぐ実行**
1. **予算アラート設定** ← 最優先
2. **課金アカウント作成**
3. **API有効化**
4. **最小リソースでデプロイ**

### **デプロイ後**
1. **使用量モニタリング**
2. **パフォーマンステスト**
3. **必要に応じてリソース調整**

---

## ⚠️ **重要な注意点**

- 無料枠を超過する前に必ずアラート通知
- $300無料クレジット（12ヶ月有効）を活用
- 開発・テスト期間終了後はリソース削除推奨
- 本番運用時は適切な予算設定

**安全第一で進めましょう！**