# Gemini版 使い方ガイド

## 📋 概要

`analyze_video_gemini.py` は、OpenAI GPT-4o-mini の代わりに **Google Gemini API** を使用して動画を解析するバージョンです。

---

## 🚀 セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements_gemini.txt
```

または個別にインストール:

```bash
pip install opencv-python google-generativeai Pillow
```

### 2. Gemini APIキーの取得

1. [Google AI Studio](https://makersuite.google.com/app/apikey) にアクセス
2. 「Create API Key」をクリック
3. APIキーをコピー

### 3. APIキーの設定

#### 方法1: コード内に直接設定（開発用）

`analyze_video_gemini.py` の48行目を編集:

```python
HARD_CODED_GEMINI_API_KEY = "AIzaSy-YOUR-API-KEY-HERE"
```

#### 方法2: 環境変数に設定（推奨）

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="AIzaSy-YOUR-API-KEY-HERE"
```

**Windows (コマンドプロンプト):**
```cmd
set GEMINI_API_KEY=AIzaSy-YOUR-API-KEY-HERE
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY="AIzaSy-YOUR-API-KEY-HERE"
```

---

## 💻 使い方

### 基本的な使用

```bash
python analyze_video_gemini.py your_video.mp4
```

### ファイル名のみ指定（videos/から自動検索）

```bash
python analyze_video_gemini.py demo用動画案１.mp4
```

### フルパス指定

```bash
python analyze_video_gemini.py "C:\path\to\your_video.mp4"
```

---

## ⚙️ 設定のカスタマイズ

### モデルの変更

`analyze_video_gemini.py` の44行目:

```python
MODEL_NAME = "gemini-1.5-pro"    # 高精度版（推奨）
MODEL_NAME = "gemini-1.5-flash"  # 高速版（コスト削減）
```

### その他の設定

- **サンプリング間隔**: 42行目の `SAMPLE_INTERVAL`
- **バッチサイズ**: 43行目の `BATCH_SIZE`
- **最小継続時間**: 63-76行目の `MIN_DURATION`

---

## 🔄 OpenAI版との違い

| 項目 | OpenAI版 | Gemini版 |
|------|----------|----------|
| **ファイル名** | `analyze_video.py` | `analyze_video_gemini.py` |
| **API** | OpenAI GPT-4o-mini | Google Gemini 1.5 Pro/Flash |
| **ライブラリ** | `requests` | `google-generativeai` |
| **画像形式** | Base64文字列 | PIL Image |
| **レスポンス** | JSON形式 | JSON形式（設定可能） |
| **コスト** | 有料 | 無料枠あり |

---

## 📊 出力形式

出力形式は OpenAI版と**完全に同じ**です:

```json
{
  "events": [
    {
      "t": 0.0,
      "action": "caption",
      "text": "シーンの説明文"
    },
    {
      "t": 0.0,
      "action": "start",
      "effect": "vibration",
      "mode": "long"
    }
  ]
}
```

生成されたJSONファイルは、`playback_video.py` でそのまま使用できます。

---

## 🎯 モデルの選択

### gemini-1.5-pro（推奨）

- **精度**: 高い
- **速度**: やや遅い
- **コスト**: 無料枠あり（1分あたり15リクエスト）
- **用途**: 高品質な解析が必要な場合

### gemini-1.5-flash

- **精度**: やや低い（ただし十分）
- **速度**: 速い
- **コスト**: 無料枠あり（1分あたり60リクエスト）
- **用途**: 高速処理が必要な場合

---

## ⚠️ 注意事項

### 1. APIキーの管理

- APIキーは機密情報です。GitHubなどに公開しないでください
- 環境変数を使用することを推奨します

### 2. レート制限

- Gemini APIには無料枠があります
- 大量の動画を処理する場合は、レート制限に注意してください
- バッチ間に15秒の待機時間が設定されています

### 3. エラーハンドリング

- API呼び出しに失敗した場合、自動で60秒待機してリトライします
- それでも失敗する場合は、APIキーやネットワーク接続を確認してください

---

## 🐛 トラブルシューティング

### エラー: "google-generativeai がインストールされていません"

```bash
pip install google-generativeai
```

### エラー: "GEMINI_API_KEY 未設定"

- 環境変数 `GEMINI_API_KEY` を設定するか
- `analyze_video_gemini.py` の48行目に直接設定してください

### エラー: "API呼び出し失敗"

- APIキーが正しいか確認
- インターネット接続を確認
- Gemini APIのステータスを確認: https://status.cloud.google.com/

### エラー: "Rate limit exceeded"

- バッチ間に15秒の待機時間があります
- より長い待機時間が必要な場合は、コード内の `time.sleep(15)` を増やしてください

---

## 📚 関連ファイル

- **メインファイル**: `analyze_video_gemini.py`
- **依存パッケージ**: `requirements_gemini.txt`
- **再生用**: `playback_video.py`（OpenAI版と同じ）
- **元のバージョン**: `analyze_video.py`（OpenAI版）

---

## 💡 使い分けの目安

### Gemini版を使う場合

- ✅ 無料で試したい
- ✅ GoogleのAIを使いたい
- ✅ コストを抑えたい

### OpenAI版を使う場合

- ✅ より高い精度が必要
- ✅ OpenAIのAPIキーを持っている
- ✅ 既存のワークフローに統合したい

---

## 🎬 まとめ

1. ✅ `pip install -r requirements_gemini.txt` でインストール
2. ✅ Gemini APIキーを取得・設定
3. ✅ `python analyze_video_gemini.py 動画名.mp4` で実行
4. ✅ `results/動画名_timeline.json` が生成される

**🎉 Gemini版で4DX体験を楽しんでください！**


