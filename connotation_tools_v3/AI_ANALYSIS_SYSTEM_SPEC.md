# AI解析システム 仕様書（v3）

## 目的

動画から4DX@HOME v3向けのタイムラインJSONを生成する。
解析はGemini APIを用い、画像フレームとプロンプトに基づいて効果を推定する。

## 対象モジュール

- `analyze_video_gemini.py`（AI解析本体）
- `prompts.py`（プロンプト定義）
- `JSON_SPECIFICATION.md`（出力仕様）
- `results/`（出力先）

## 入力

### 必須

- 動画ファイル（例: `videos/ワイスピ.mp4`）

### 任意

- Gemini APIキー（環境変数 `GEMINI_API_KEY` またはコード内 `HARD_CODED_GEMINI_API_KEY`）

## 出力

- `results/<動画名>_timeline_YYYYMMDD_HHMMSS.json`
  - `JSON_SPECIFICATION.md` に準拠したイベント配列

## 解析パイプライン

1. 動画読み込み
2. 0.25秒間隔でフレーム抽出（4FPS）
3. フレームをリサイズ（横640px基準）
4. フレームをバッチ分割
5. Geminiへ送信しJSON応答を取得
6. 効果の正規化と差分化（start/stop/shot）
7. タイムラインJSONに書き出し

## 主要設定（`analyze_video_gemini.py`）

- サンプリング間隔: `SAMPLE_INTERVAL = 0.25`
- バッチサイズ: `BATCH_SIZE = 100`
- モデル: `MODEL_NAME = "gemini-2.5-pro"`
- 同時実行数: `MAX_CONCURRENT_REQUESTS = 10`

## 使用するプロンプト

`prompts.py` 内の `PROMPTS["4dx_home_v3"]` を使用。

- `PROMPT_NAME = "4dx_home_v3"`
- `DEFAULT_PROMPT = "4dx_home_v3"`

## 効果仕様（出力JSON）

詳細は `JSON_SPECIFICATION.md` を参照。
以下を含む:

- `vibration`, `flash`, `color`, `wind`
- `water`（`burst` / `stream`）
- `mist`（`burst` / `stream`）
- `led_strength`, `led_transition`

## エラー処理

- APIエラー時は待機してリトライ
- 解析失敗時は例外を出力
- `cv2.setLogLevel` が存在しない環境でも動作継続

## APIキー設定

推奨: 環境変数 `GEMINI_API_KEY`

PowerShell:
```
$env:GEMINI_API_KEY="AIza..."
```

## 実行例

```
python .\analyze_video_gemini.py ワイスピ.mp4
```

## 重要な前提

- 4FPS基準でタイムラインを生成
- 解析結果は後からエディターで編集可能
- 仕様変更は `JSON_SPECIFICATION.md` と `prompts.py` の両方に反映する
