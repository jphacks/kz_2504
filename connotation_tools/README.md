# 🎬 AI 4DX タイムライン生成システム

任意のMP4動画を解析して、4DX映画館のような体感エンターテインメント用のタイムラインJSONを自動生成するシステムです。

**開発: JPHACKS 2025**

---

## 📖 目次

1. [概要](#概要)
2. [主な機能](#主な機能)
3. [対応効果](#対応効果)
4. [セットアップ](#セットアップ)
5. [使い方](#使い方)
6. [技術スタック](#技術スタック)
7. [システム詳細](#システム詳細)
8. [カスタマイズ](#カスタマイズ)
9. [トラブルシューティング](#トラブルシューティング)

---

## 🎯 概要

### このシステムは何をするのか？

1. **MP4動画を入力**
2. **AIが自動解析**（OpenAI GPT-4o-mini または Google Gemini 2.5 Pro）
3. **4DX効果のタイムラインJSONを生成**
4. **動画再生しながら効果信号をリアルタイム送信**

### 何が革新的か？

- ✅ **どんな動画でも4DX化可能** - 専用コンテンツ不要
- ✅ **AI自動判定** - 手動設定不要
- ✅ **リアルタイム同期** - 動画と効果が完全同期
- ✅ **2つのAIエンジン対応** - OpenAI版とGemini版
- ✅ **4DX@HOME仕様対応** - 精密な振動制御（背中/おしり別制御）
- ✅ **拡張可能** - デバイス制御をカスタマイズ可能

---

## 🎮 主な機能

### 1. 📸 解析モード（動画→JSON）

```
MP4動画 → AI解析 → タイムラインJSON
```

#### OpenAI版（`analyze_video.py`）
- **0.5秒間隔**でフレーム抽出
- **GPT-4o-mini Vision**で各フレームをシーン理解
- **バッチサイズ15**で効率的に処理
- 効果（光/風/水/色/振動）を自動判定
- JSON形式で出力

#### Gemini版（`analyze_video_gemini.py`）- 4DX@HOME仕様
- **0.25秒間隔**でフレーム抽出（より精密）
- **Gemini 2.5 Pro**で各フレームをシーン理解
- **バッチサイズ100**で大量処理
- **並列実行**（最大10リクエスト同時実行）
- **プロンプトシステム**対応（`prompts.py`）
- **JSON形式で効果情報も返す**（キャプション + 効果）
- 4DX@HOME専用の精密な振動制御

### 2. 🎬 視聴用再生モード（JSON→体験）

```
動画 + JSON → リアルタイム再生 → 効果信号送信
```

- 動画を再生しながらタイムライン処理
- **リアルタイム効果パネル表示**（右側に固定表示）
- **音声再生対応**（pygame + ffmpeg）
- デバイス制御信号を送信（カスタマイズ可能）
- キーボード操作（一時停止、最初から、終了）

---

## 📋 対応効果

### 💥 振動（vibration）

#### OpenAI版
- **弱い振動（long）** - 乗り物搭乗中・移動中・戦闘中に継続（最小1秒）
- **強い衝撃（strong）** - 爆発・衝突・攻撃・咆哮の瞬間（最小1秒）
- **ドキドキ（heartbeat）** - 緊張シーン（最小2.5秒）
- ※複数モード同時発動可能（例: long + strong）

#### Gemini版（4DX@HOME仕様）- 精密制御
- **上（背中）の振動**:
  - `up_strong` - 強（強烈なシーンのみ）
  - `up_mid_strong` - 中強（強烈なシーンのみ）
  - `up_mid_weak` - 中弱（多少の振動を再現）
  - `up_weak` - 弱（多少の振動を再現）
- **下（おしり）の振動**:
  - `down_strong` - 強（強烈なシーンのみ）
  - `down_mid_strong` - 中強（強烈なシーンのみ）
  - `down_mid_weak` - 中弱（多少の振動を再現）
  - `down_weak` - 弱（多少の振動を再現）
- **上＆下同時**（相乗効果で強い）:
  - `up_down_strong` - 強（かなり強い）
  - `up_down_mid_strong` - 中強（かなり強い）
  - `up_down_mid_weak` - 中弱（かなり強い）
  - `up_down_weak` - 弱（かなり強い）
- **ドキドキ（heartbeat）** - 緊張シーン（最小0.5秒）

### ⚡ 光（flash）

#### OpenAI版
- **ストロボ（strobe）** - 雷・稲妻でチカチカ（最小1.5秒）
- **閃光（burst）** - 爆発・火花の一瞬の光（最小0.5秒）
- **照明（steady）** - 炎・夕日・照明の継続光（最小1.5秒）

#### Gemini版（4DX@HOME仕様）
- **点灯（steady）** - 継続的な光（最小2秒）
- **遅い点滅（slow_blink）** - ゆっくりチカチカ（最小2秒）
- **早い点滅（fast_blink）** - 速くチカチカ（最小1秒）
- ※通常のシーンでは光は使わない。銃の火、閃光、爆発、雷など特別な光を表現する必要があるときのみ使用

### 💨 風（wind）

#### OpenAI版
- **一瞬の風（burst）** - 衝撃波・爆風・息（最小1.0秒）
- **長い風（long）** - 疾走・砂埃・煙（最小1.5秒）

#### Gemini版（4DX@HOME仕様）
- **オン（on）** - 風を出す（最小1.0秒、出力時は`burst`モードに変換）

### 💦 水（water）

#### 両バージョン共通
- **水しぶき（burst/on）** - 水・波・唾・汗の噴射（**shot型: 一度きり**、最小0.5秒）

### 🎨 色（color）

#### OpenAI版
- **赤（red）** - 炎・火・爆発・血（最小1.0秒）
- **緑（green）** - 森・草原・自然（最小1.0秒）
- **青（blue）** - 空・海・水（最小1.0秒）

#### Gemini版（4DX@HOME仕様）
- **赤（red）** - 炎・火・爆発・血（最小2秒）
- **緑（green）** - 森・草原・自然（最小2秒）
- **青（blue）** - 空・海・水（最小2秒）
- **黄色（yellow）** - 明るいシーン（最小2秒）
- **シアン（cyan）** - 水・空（最小2秒）
- **紫（purple）** - 幻想的なシーン（最小2秒）

---

## 🎯 特別なルール

### 咆哮・叫び
```
検出: "咆哮", "吠える", "叫ぶ" など
↓
同時発動:
💥 強い衝撃（衝撃波）
💦 水しぶき（唾の飛沫）
💨 一瞬の風（息）
```

### 爆発
```
検出: "爆発", "炸裂", "炎が見える" など
↓
同時発動:
💥 強い衝撃
⚡ 閃光（fast_blink）
🔴 赤色（炎）
```

### 乗り物搭乗中
```
検出: "戦闘機に乗っている", "車内" など
↓
継続的に:
📳 弱い振動（エンジン・揺れ）
```

### 最小継続時間

#### OpenAI版
```
💓 ドキドキ: 2.5秒以上
💥 衝撃・風・水: 1.0秒以上
⚡ 光・色: 0.5-1.5秒
```

#### Gemini版（4DX@HOME仕様）
```
📳 振動: 0.5秒以上（時には0.25秒でも可）
⚡ 光: 1-2秒以上
🎨 色: 2秒以上
💨 風: 1.0秒以上
💦 水: 0.5秒以上
```

---

## 🚀 セットアップ

### 1. 依存パッケージのインストール

#### OpenAI版
```bash
pip install -r requirements.txt
```

必要なパッケージ:
- `opencv-python` - 動画処理
- `requests` - OpenAI API 通信

#### Gemini版（4DX@HOME仕様）
```bash
pip install -r requirements_gemini.txt
```

必要なパッケージ:
- `opencv-python` - 動画処理
- `google-generativeai` - Gemini API 通信
- `Pillow` - 画像処理

### 2. APIキーの設定

#### OpenAI版
`analyze_video.py` を開いて、49行目を編集：

```python
HARD_CODED_OPENAI_API_KEY = "sk-proj-YOUR-API-KEY-HERE"
```

または環境変数に設定：
```bash
export OPENAI_API_KEY="sk-proj-YOUR-API-KEY-HERE"
```

#### Gemini版
`analyze_video_gemini.py` を開いて、64行目を編集：

```python
HARD_CODED_GEMINI_API_KEY = "AIza..."
```

または環境変数に設定：
```bash
export GEMINI_API_KEY="AIza..."
```

### 3. 動画を配置

```
connotation_tools/
└── videos/
    └── your_video.mp4  ← ここに動画を配置
```

---

## 💻 使い方

### 基本フロー

```bash
# 1. 動画を videos/ に配置
videos/my_video.mp4

# 2. 解析（タイムラインJSON生成）
# OpenAI版
python analyze_video.py my_video.mp4

# Gemini版（4DX@HOME仕様）
python analyze_video_gemini.py my_video.mp4

# 3. 視聴用再生（動画 + 効果体験）
python playback_video.py my_video.mp4
```

### Windows 簡易実行

```batch
setup.bat          # 初回のみ
run_analyze.bat    # 解析（OpenAI版）
run_playback.bat   # 再生
```

### 詳細な使用例

#### 解析モード（OpenAI版）
```bash
# ファイル名のみ（videos/ から自動検索）
python analyze_video.py demo.mp4

# フルパス指定
python analyze_video.py videos/demo.mp4

# 引数なしでヘルプ表示
python analyze_video.py
```

**出力:** `results/demo_timeline_YYYYMMDD_HHMMSS.json`

#### 解析モード（Gemini版）
```bash
# ファイル名のみ（videos/ から自動検索）
python analyze_video_gemini.py demo.mp4

# フルパス指定
python analyze_video_gemini.py videos/demo.mp4

# 利用可能なモデルを表示
python analyze_video_gemini.py --list-models

# 利用可能なプロンプトを表示
python analyze_video_gemini.py --list-prompts

# 引数なしでヘルプ表示
python analyze_video_gemini.py
```

**出力:** `results/demo_timeline_YYYYMMDD_HHMMSS.json`

#### 視聴用再生モード
```bash
python playback_video.py demo.mp4
```

**操作方法:**
- `[スペース]`: 一時停止/再生
- `[R]`: 最初から再生
- `[Q/ESC]`: 終了

---

## 🔧 技術スタック

### プログラミング言語
- **Python 3.7+**

### AI・機械学習

#### OpenAI版
- **OpenAI GPT-4o-mini (Vision API)**
  - マルチモーダルAI（画像 + テキスト）
  - シーン理解・キャプション生成
  - バッチ処理（15枚同時解析）

#### Gemini版
- **Google Gemini 2.5 Pro**
  - マルチモーダルAI（画像 + テキスト）
  - シーン理解・キャプション生成 + 効果判定
  - バッチ処理（100枚同時解析）
  - 並列実行（最大10リクエスト同時実行）

### 動画処理
- **OpenCV (opencv-python)**
  - 動画読み込み・フレーム抽出
  - リアルタイム動画再生
  - 画像処理（リサイズ、エンコード）

### 音声処理
- **pygame** - 音声再生
- **ffmpeg** - 音声抽出（オプション）

### 通信
- **requests** - OpenAI API との HTTP 通信
- **google-generativeai** - Gemini API との通信

### データフォーマット
- **JSON** - タイムラインデータ
- **Base64** - 画像エンコーディング

---

## 🏗️ システム詳細

### アーキテクチャ

#### OpenAI版（解析モード）
```
MP4動画
  ↓
OpenCV: フレーム抽出（0.5秒間隔）
  ↓
画像圧縮（640px）+ Base64エンコード
  ↓
バッチ処理（15枚ずつ）
  ↓
GPT-4o-mini Vision API
  ↓
日本語キャプション生成
  ↓
ルールベース効果判定
  ↓
差分計算 + 最小継続時間制御
  ↓
タイムラインJSON
```

#### Gemini版（解析モード）- 4DX@HOME仕様
```
MP4動画
  ↓
OpenCV: フレーム抽出（0.25秒間隔）
  ↓
画像圧縮（640px）+ Base64エンコード
  ↓
バッチ処理（100枚ずつ）
  ↓
並列実行（最大10リクエスト同時実行）
  ↓
Gemini 2.5 Pro API
  ↓
日本語キャプション生成 + 効果判定（JSON形式）
  ↓
プロンプトシステム（prompts.py）
  ↓
差分計算 + 最小継続時間制御
  ↓
タイムラインJSON
```

#### 視聴用再生モード
```
タイムラインJSON + MP4動画
  ↓
OpenCV: 動画再生
  ↓
pygame: 音声再生（オプション）
  ↓
システム時刻でタイムライン同期
  ↓
イベント処理（start/stop/shot）
  ↓
リアルタイム効果パネル表示
  ↓
デバイス制御信号送信
```

### 主要アルゴリズム

#### 1. バッチ処理

##### OpenAI版
```
293フレーム → 293回API呼び出し ❌
293フレーム → 20回API呼び出し ✅（15枚ずつ）
→ API コストを 1/15 に削減
```

##### Gemini版
```
293フレーム → 293回API呼び出し ❌
293フレーム → 3回API呼び出し ✅（100枚ずつ）
→ API コストを 1/100 に削減
→ 並列実行により処理時間も短縮
```

#### 2. ルールベース判定（OpenAI版）
```python
キャプション: "戦闘機に乗っており、敵に咆哮している"
↓
キーワードマッチング:
- "戦闘機" → vibration:long
- "乗っている" → vibration:long
- "咆哮" → vibration:strong + water:burst + wind:burst
↓
効果リスト生成
```

#### 3. AI効果判定（Gemini版）
```python
キャプション: "戦闘機に乗っており、敵に咆哮している"
↓
AIがJSON形式で効果を返す:
{
  "caption": "...",
  "effects": {
    "vibration": "up_mid_weak",
    "water": "on",
    "wind": "on"
  }
}
↓
効果リスト生成
```

#### 4. 最小継続時間制御
```python
t=0.0秒: vibration:heartbeat 開始
t=0.5秒: heartbeat 検出されず
→ でも最小時間未満なので継続（チラつき防止）
t=0.5秒: 最小時間達成
→ 停止可能
```

#### 5. 上書きシステム
```python
# 振動は複数モード同時OK
vibration:long + vibration:strong = 両方発動

# 色・光は上書き
color:red → color:blue に即座に切り替え
```

#### 6. 水は一度きり
```json
{"t": 3.0, "action": "shot", "effect": "water", "mode": "burst"}
// start/stop なし、shot のみ
```

---

## 🎨 出力JSON形式

```json
{
  "events": [
    {
      "t": 0.0,
      "action": "caption",
      "text": "戦闘機に乗っており、空中を飛行中"
    },
    {
      "t": 0.0,
      "action": "start",
      "effect": "vibration",
      "mode": "long"
    },
    {
      "t": 5.5,
      "action": "start",
      "effect": "vibration",
      "mode": "strong"
    },
    {
      "t": 5.5,
      "action": "shot",
      "effect": "water",
      "mode": "burst"
    },
    {
      "t": 6.5,
      "action": "stop",
      "effect": "vibration",
      "mode": "strong"
    }
  ]
}
```

---

## ⚙️ カスタマイズ

### サンプリング間隔の変更

#### OpenAI版
`analyze_video.py` の43行目:

```python
SAMPLE_INTERVAL = 0.5   # 標準（推奨）
SAMPLE_INTERVAL = 0.25  # 精密（衝突・爆発を正確に検出）
SAMPLE_INTERVAL = 1.0   # 高速（長い動画向け）
```

#### Gemini版
`analyze_video_gemini.py` の56行目:

```python
SAMPLE_INTERVAL = 0.25  # 4DX@HOME仕様（推奨）
SAMPLE_INTERVAL = 0.5   # 標準
SAMPLE_INTERVAL = 0.1   # 超精密（処理時間が長くなる）
```

### バッチサイズの変更

#### OpenAI版
`analyze_video.py` の44行目:

```python
BATCH_SIZE = 15  # 標準（推奨）
BATCH_SIZE = 10  # 小さい（メモリ節約）
BATCH_SIZE = 20  # 大きい（高速化、ただしAPI制限に注意）
```

#### Gemini版
`analyze_video_gemini.py` の57行目:

```python
BATCH_SIZE = 100  # 4DX@HOME仕様（推奨、最大480枚まで対応可能）
BATCH_SIZE = 50   # 小さい（メモリ節約）
BATCH_SIZE = 200  # 大きい（高速化、ただしAPI制限に注意）
```

### 並列実行数の変更（Gemini版のみ）

`analyze_video_gemini.py` の61行目:

```python
MAX_CONCURRENT_REQUESTS = 10  # 標準（推奨）
MAX_CONCURRENT_REQUESTS = 5   # 少ない（API制限に安全）
MAX_CONCURRENT_REQUESTS = 20  # 多い（高速化、ただしAPI制限に注意）
```

### 最小継続時間の変更

#### OpenAI版
`analyze_video.py` の64-77行目:

```python
MIN_DURATION = {
    "vibration:heartbeat": 2.5,  # ドキドキの長さ
    "vibration:strong": 1.0,     # 衝撃の長さ
    "wind:long": 1.5,            # 風の長さ
    # ...カスタマイズ可能
}
```

#### Gemini版
`analyze_video_gemini.py` の89-123行目:

```python
MIN_DURATION = {
    "vibration:up_strong": 0.5,
    "vibration:up_mid_strong": 0.5,
    # ...カスタマイズ可能
}
```

### タイミングオフセットの調整

`playback_video.py` の59行目:

```python
TIMING_OFFSET = -0.5  # 信号が早い場合は増やす（正の値）
TIMING_OFFSET = 0.3   # 信号が遅い場合は減らす（負の値）
TIMING_OFFSET = 0.0   # オフセットなし
```

### プロンプトのカスタマイズ（Gemini版のみ）

`prompts.py` を編集して、独自のプロンプトを追加できます。

```python
PROMPTS = {
    "my_custom_prompt": """
    カスタムプロンプトの内容...
    """,
}
```

使用するプロンプトを変更するには、`analyze_video_gemini.py` の60行目を編集：

```python
PROMPT_NAME = "my_custom_prompt"  # デフォルトは "4dx_home"
```

### デバイス制御のカスタマイズ

`playback_video.py` の `EffectController._send_signal()` を編集:

```python
def _send_signal(self, action, effect, mode):
    # シリアル通信（Arduino）
    import serial
    ser = serial.Serial('COM3', 9600)
    ser.write(f"{action}:{effect}:{mode}\n".encode())
    
    # または HTTP API
    import requests
    requests.post("http://localhost:8080/effect",
                  json={"action": action, "effect": effect, "mode": mode})
```

---

## 📂 ファイル構成

```
connotation_tools/
├── analyze_video.py           # 解析エンジン（OpenAI版、627行）
├── analyze_video_gemini.py   # 解析エンジン（Gemini版、936行）
├── playback_video.py         # 再生エンジン（987行）
├── prompts.py                # プロンプト管理（447行）
├── requirements.txt          # 依存パッケージ（OpenAI版）
├── requirements_gemini.txt    # 依存パッケージ（Gemini版）
├── README.md                 # このファイル
├── TECH_STACK.md             # 技術詳細
├── TIMING_GUIDE.md           # タイミング調整ガイド
├── JSON_SPECIFICATION.md     # JSON仕様
├── JSON生成ガイド.md         # JSON生成ガイド
├── PROMPT_GUIDE.md           # プロンプトガイド
├── Gemini版使い方.md         # Gemini版の使い方
├── setup.bat                 # セットアップ（Windows）
├── run_analyze.bat           # 解析実行（Windows）
├── run_playback.bat          # 再生実行（Windows）
├── videos/                   # 動画配置フォルダ
│   ├── .gitkeep
│   └── your_video.mp4        # ← ここに動画を配置
└── results/                   # JSON出力フォルダ
    ├── .gitkeep
    └── your_video_timeline_YYYYMMDD_HHMMSS.json
```

---

## 🎯 開発の経緯

### フェーズ1: test1（初期プロトタイプ）
- ローカル動画ファイルの処理
- 基本的な効果判定
- 単一フレーム処理

### フェーズ2: youtube_scene_processor
- YouTube動画対応（後に法的問題で廃止）
- バッチ処理の導入
- レート制限対策

### フェーズ3: video_scene_processor（OpenAI版）
- **MP4専用に特化**（法的に安全）
- **4DX向けに最適化**
- **振動の精密制御**
- **リアルタイム状態表示**
- **最小継続時間システム**
- **タイミング同期機能**

### フェーズ4: connotation_tools（Gemini版追加）
- **Gemini 2.5 Pro対応**
- **4DX@HOME仕様対応**
- **0.25秒間隔の精密サンプリング**
- **並列実行による高速化**
- **プロンプトシステム**
- **AI効果判定（JSON形式）**
- **精密な振動制御（背中/おしり別制御）**
- **効果パネル表示**
- **音声再生対応**

---

## 🔬 技術的特徴

### 1. バッチ処理によるAPI効率化

#### OpenAI版
```
従来: 1枚ずつ → 293回のAPI呼び出し
改善: 15枚ずつ → 約20回のAPI呼び出し
→ 15倍高速化、コスト1/15
```

#### Gemini版
```
従来: 1枚ずつ → 293回のAPI呼び出し
改善: 100枚ずつ + 並列実行 → 約3回のAPI呼び出し
→ 100倍高速化、コスト1/100、処理時間も大幅短縮
```

### 2. 最小継続時間制御
```
効果が0.5秒でON/OFFされない
最小継続時間を保証してチラつき防止
```

### 3. インテリジェント判定

#### OpenAI版（ルールベース）
```python
- 空中判定: ジャンプ中は振動なし
- 乗り物判定: 搭乗中は常に振動
- 静止判定: 完全に静止のみ振動停止
- 瞬間検出: 衝突・爆発の正確なタイミング
```

#### Gemini版（AI判定）
```python
- AIが直接効果を判定（JSON形式）
- 前後のフレームの差分を考慮
- 4DX@HOME専用プロンプトで精密制御
- 振動の強度を適切に選択（強/中強/中弱/弱）
```

### 4. 複数モード同時発動
```
振動: strong + long + heartbeat 同時OK
他: 上書きシステム（color:red → color:blue）
```

### 5. 水の特別処理
```
start/stop ではなく shot イベント
一度きりの噴射を表現
```

### 6. 並列実行（Gemini版のみ）
```
複数のバッチを同時に処理
最大10リクエスト同時実行
処理時間を大幅短縮
```

---

## 📊 パフォーマンス

### OpenAI版

| 項目 | 値 |
|------|-----|
| 処理速度 | 約2-3分/分の動画（バッチ処理） |
| API呼び出し | 約4回/分（15枚バッチ） |
| サンプリング | 2フレーム/秒（0.5秒間隔） |
| 同期精度 | フレーム単位（30fps対応） |
| タイミング調整 | ±0.5秒オフセット可能 |

### Gemini版（4DX@HOME仕様）

| 項目 | 値 |
|------|-----|
| 処理速度 | 約1-2分/分の動画（並列実行） |
| API呼び出し | 約0.6回/分（100枚バッチ + 並列実行） |
| サンプリング | 4フレーム/秒（0.25秒間隔） |
| 同期精度 | フレーム単位（30fps対応） |
| タイミング調整 | ±0.5秒オフセット可能 |
| 並列実行数 | 最大10リクエスト同時実行 |

---

## 🎬 視聴用再生モードの表示

### リアルタイム効果パネル

再生中、動画の右側に固定表示される効果パネル：

```
┌─────────────────────────────────────┐
│         4DX EFFECTS                 │
├─────────────────────────────────────┤
│ VIBRATION                           │
│ [📳 上:強] UP: STRONG               │
│ [📳 下:弱] DOWN: WEAK               │
│                                     │
│ WATER                               │
│ [💦] ACTIVE / OFF                   │
│                                     │
│ COLOR                               │
│ [🔴] RED / OFF                      │
│                                     │
│ LIGHT                               │
│ [💡] FAST_BLINK / OFF               │
│                                     │
│ WIND                                │
│ [💨] ACTIVE / OFF                   │
└─────────────────────────────────────┘
```

- **リアルタイム更新**（0.5秒ごと）
- **ON/OFF が一目瞭然**
- **振動の強度表示**（上/下別）
- **水の発射アニメーション**
- **色・光の状態表示**

---

## 🎯 ルール詳細

### 振動の判定ロジック

#### OpenAI版
```python
# 弱い振動を出す条件
✓ 乗り物に乗っている
✓ 移動中・飛行中
✓ 戦闘中・暴れている

# 強い衝撃を出す条件
✓ 爆発の瞬間
✓ 衝突の瞬間
✓ 攻撃・打撃の瞬間
✓ 着地の瞬間
✓ 咆哮・叫び

# 振動を止める条件
✓ 完全に静止している
✓ 降りていて かつ 静止
✓ 空中（乗り物なし）
```

#### Gemini版（4DX@HOME仕様）
```python
# 振動の強度選択ルール
- 強烈なシーン（爆発、強烈な衝撃、強烈な着地）→ 中強以上
- 多少の振動を再現 → 中弱以下
- 上＆下同時は相乗効果で強くなるが、単独の中強よりは弱い

# 振動のメリハリ
- 静かなシーンでは完全に停止
- 動きのあるシーンで明確に再開
- 曖昧な中間状態は避ける

# ホラー・恐竜・怪物シーン
- 敵が近づいている間は heartbeat を継続
- シーンが切り替わったら停止
```

### 4DX向けプロンプト

AIに以下を指示:
1. 乗り物の状態を必ず記載
2. 衝突・爆発の「瞬間」を正確に
3. 炎・火花を見逃さない
4. 動き・静止を明確に
5. 咆哮・叫びは詳しく記載
6. 前後のフレームの差分をしっかり見る（Gemini版）

---

## 📈 処理フロー詳細

### 解析モードの処理

#### OpenAI版
```
1. 動画読み込み
   ↓
2. FPS・長さ・フレーム数を取得
   ↓
3. サンプリング点を計算（0.5秒間隔）
   ↓
4. バッチごとに処理（15枚ずつ）
   ├─ フレーム抽出
   ├─ 画像リサイズ（640px）
   ├─ Base64エンコード
   ├─ API呼び出し（バッチ）
   ├─ キャプション取得
   ├─ 効果判定（ルールベース）
   ├─ 差分計算
   └─ イベント生成
   ↓
5. 最小継続時間適用
   ↓
6. JSON出力
```

#### Gemini版
```
1. 動画読み込み
   ↓
2. FPS・長さ・フレーム数を取得
   ↓
3. サンプリング点を計算（0.25秒間隔）
   ↓
4. すべてのバッチのフレームデータを事前準備
   ↓
5. 並列実行（最大10リクエスト同時実行）
   ├─ バッチごとに処理（100枚ずつ）
   │  ├─ フレーム抽出
   │  ├─ 画像リサイズ（640px）
   │  ├─ Base64エンコード
   │  ├─ API呼び出し（バッチ）
   │  ├─ キャプション取得 + 効果判定（JSON形式）
   │  └─ 結果を保存
   ↓
6. バッチ結果を時系列順にソート
   ↓
7. 差分計算 + 最小継続時間適用
   ↓
8. JSON出力
```

### 再生モードの処理

```
1. JSON読み込み
   ↓
2. 動画読み込み
   ↓
3. 音声抽出（ffmpeg + pygame）
   ↓
4. リアルタイム再生ループ
   ├─ 現在時刻計算
   ├─ フレーム取得
   ├─ イベント処理（timing offset適用）
   ├─ 効果パネル更新（0.5秒ごと）
   ├─ 動画表示
   └─ キー入力処理
```

---

## 🐛 トラブルシューティング

### エラー: "動画ファイルが見つかりません"
→ `videos/` ディレクトリに動画を配置してください

### エラー: "OPENAI_API_KEY 未設定" / "GEMINI_API_KEY 未設定"
→ コード内のAPIキーを設定するか、環境変数に設定してください

### エラー: "タイムラインファイルが見つかりません"
→ 先に `analyze_video.py` または `analyze_video_gemini.py` を実行してください

### エラー: "Rate limit exceeded"
→ 自動で60秒待機してリトライします
→ バッチ間に15秒の待機時間あり（OpenAI版）

### エラー: "Connection timeout"
→ インターネット接続を確認
→ APIの状態を確認

### エラー: "モデルが見つかりません"（Gemini版）
→ `python analyze_video_gemini.py --list-models` で利用可能なモデルを確認
→ コード内の `MODEL_NAME` を確認

### 振動が少ない
→ AIのキャプションに「乗っている」「戦闘中」が含まれているか確認
→ JSONファイルを確認してルールを追加（OpenAI版）
→ プロンプトを調整（Gemini版）

### タイミングがずれる
→ `TIMING_OFFSET` を調整（0.3 ~ 0.7秒）

### 効果がチラつく
→ `MIN_DURATION` を長くする

### 音声が再生されない
→ `pygame` がインストールされているか確認: `pip install pygame`
→ `ffmpeg` がインストールされているか確認: https://ffmpeg.org/download.html

---

## 💡 推奨動画

### 自分で撮影
- ✅ スマホで撮影したアクション動画
- ✅ 車載カメラの映像
- ✅ スポーツ・アクティビティ

### 著作権フリー動画
- ✅ [Pexels Videos](https://www.pexels.com/videos/)
- ✅ [Pixabay](https://pixabay.com/videos/)
- ✅ クリエイティブ・コモンズライセンス

---

## ⚠️ 注意事項

### 法的に安全な使用
- ✅ 自分で撮影した動画
- ✅ 著作権フリー動画
- ✅ 使用許可を得た動画
- ❌ 著作権のある動画の無断使用

### 推奨動画スペック
- 形式: MP4
- 長さ: 10秒～5分（推奨）
- 解像度: 任意（自動リサイズ）
- FPS: 任意（対応）

---

## 🎓 応用例

### 現在の実装
- MP4動画の処理
- JSON タイムライン生成
- コンソール出力 + 効果パネル表示
- 音声再生

### 拡張可能性
- 🔌 Arduino/マイコン連携
- 🌐 WebSocket リアルタイム配信
- 🎮 Unity/Unreal Engine 統合
- 💡 スマートライト制御（Philips Hue等）
- 🪑 振動シート制御
- 💨 風扇制御
- 💦 水噴射装置制御

---

## 📊 統計情報

### 開発規模
- **総コード行数**: 約3,000行
- **主要ファイル**: 4ファイル
- **ドキュメント**: 7ファイル
- **対応効果**: 12-20パターン（バージョンによる）
- **検出ルール**: 約20個（OpenAI版）

### 処理性能

#### OpenAI版
- **30秒動画**: 約1.5分で処理
- **1分動画**: 約3分で処理
- **5分動画**: 約15分で処理

#### Gemini版
- **30秒動画**: 約1分で処理（並列実行）
- **1分動画**: 約2分で処理（並列実行）
- **5分動画**: 約10分で処理（並列実行）

---

## 🌟 主な改善履歴

### v1.0（初期版）
- 基本的な動画処理
- 単一フレーム処理

### v2.0（バッチ処理）
- 15枚バッチ処理導入
- API効率化

### v3.0（4DX最適化）
- 4DX向けプロンプト
- 振動の精密制御
- 最小継続時間システム

### v4.0（最終版 - OpenAI）
- リアルタイム状態表
- 振動の複数モード同時発動
- タイミング同期機能
- 咆哮・炎・火花の強化検出
- 水の shot イベント

### v5.0（Gemini版追加）
- Gemini 2.5 Pro対応
- 4DX@HOME仕様対応
- 0.25秒間隔の精密サンプリング
- 並列実行による高速化
- プロンプトシステム
- AI効果判定（JSON形式）
- 精密な振動制御（背中/おしり別制御）
- 効果パネル表示
- 音声再生対応

---

## 📄 ライセンス・クレジット

### 開発
- JPHACKS 2025

### 使用技術
- OpenAI GPT-4o-mini
- Google Gemini 2.5 Pro
- OpenCV
- Python

### 免責事項
本システムは研究・教育目的のプロトタイプです。
著作権のある動画の無断使用は法律で禁止されています。
自己責任でご使用ください。

---

## 🙏 謝辞

このシステムは、AI技術と動画処理技術を組み合わせて、
次世代の体感型エンターテインメントを実現することを目指しています。

**AIで映像体験を変革する。**

---

**🎬 Enjoy 4DX Experience! ✨**
