# JSONタイムラインファイル生成ガイド

## 📋 概要

このドキュメントでは、`demo用動画案１_timeline.json` のようなタイムラインJSONファイルを作成するための方法を説明します。

---

## 🎯 JSONファイルを作成するメインファイル

### **`analyze_video.py`** （最重要ファイル）

**役割**: MP4動画を解析して、4DX効果のタイムラインJSONを自動生成する

**主な機能**:
- 動画から0.5秒間隔でフレームを抽出
- GPT-4o-mini Vision APIで各フレームを解析
- キャプション生成と効果（振動/光/風/水/色）の自動判定
- タイムラインJSONファイルを出力

**出力先**: `results/{動画名}_timeline.json`

---

## 📁 関連ファイル一覧

### 1. **コアファイル**

| ファイル名 | 役割 | 説明 |
|-----------|------|------|
| `analyze_video.py` | **JSON生成** | 動画解析エンジン（625行） |
| `playback_video.py` | **JSON再生** | 生成されたJSONを使って動画を再生（394行） |
| `requirements.txt` | **依存パッケージ** | 必要なPythonパッケージ一覧 |

### 2. **ドキュメント**

| ファイル名 | 内容 |
|-----------|------|
| `README.md` | システム全体の詳細ドキュメント |
| `TECH_STACK.md` | 技術スタックの詳細 |
| `TIMING_GUIDE.md` | タイミング調整ガイド |

### 3. **実行スクリプト（Windows用）**

| ファイル名 | 用途 |
|-----------|------|
| `setup.bat` | 初回セットアップ（依存パッケージインストール） |
| `run_analyze.bat` | 解析実行（JSON生成） |
| `run_playback.bat` | 再生実行（JSONを使用） |

### 4. **ディレクトリ構造**

```
video_scene_processor/
├── analyze_video.py          ← JSON生成のメインファイル
├── playback_video.py          ← JSONを使用して再生
├── requirements.txt           ← 依存パッケージ
├── videos/                    ← 動画ファイルを配置する場所
│   └── demo用動画案１.mp4
└── results/                   ← JSONファイルの出力先
    └── demo用動画案１_timeline.json  ← 生成されるJSON
```

---

## 🚀 新しいJSONファイルを作成する方法

### 方法1: コマンドラインから実行（推奨）

#### ステップ1: 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

必要なパッケージ:
- `opencv-python` (動画処理)
- `requests` (OpenAI API通信)

#### ステップ2: OpenAI APIキーの設定

`analyze_video.py` の48行目を編集:

```python
HARD_CODED_OPENAI_API_KEY = "sk-proj-YOUR-API-KEY-HERE"
```

または、環境変数に設定:
```bash
set OPENAI_API_KEY=sk-proj-YOUR-API-KEY-HERE
```

#### ステップ3: 動画ファイルを配置

```
videos/
└── your_video.mp4  ← ここに動画を配置
```

#### ステップ4: 解析実行

```bash
# ファイル名のみ（videos/から自動検索）
python analyze_video.py your_video.mp4

# フルパス指定
python analyze_video.py videos/your_video.mp4

# または絶対パス
python analyze_video.py C:\path\to\your_video.mp4
```

#### ステップ5: 結果確認

生成されたJSONファイル:
```
results/your_video_timeline.json
```

---

### 方法2: Windowsバッチファイルを使用

#### 初回のみ: セットアップ

```batch
setup.bat
```

#### 解析実行

```batch
run_analyze.bat
```

（バッチファイル内で動画ファイル名を指定する必要があります）

---

## 📊 JSONファイルの構造

生成されるJSONファイルの形式:

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
    },
    {
      "t": 1.5,
      "action": "stop",
      "effect": "vibration",
      "mode": "long"
    },
    {
      "t": 2.0,
      "action": "shot",
      "effect": "water",
      "mode": "burst"
    }
  ]
}
```

### イベントタイプ

1. **`caption`**: シーンのキャプション（説明文）
2. **`start`**: 効果の開始（振動/光/風/色）
3. **`stop`**: 効果の停止
4. **`shot`**: 一度きりの発射（水専用）

---

## ⚙️ カスタマイズ設定

### サンプリング間隔の変更

`analyze_video.py` の42行目:

```python
SAMPLE_INTERVAL = 0.5   # 標準（0.5秒ごと）
SAMPLE_INTERVAL = 0.25  # 精密（0.25秒ごと、より詳細）
SAMPLE_INTERVAL = 1.0   # 高速（1秒ごと、処理が速い）
```

### バッチサイズの変更

`analyze_video.py` の43行目:

```python
BATCH_SIZE = 15  # 一度に処理するフレーム数（10-20推奨）
```

### 最小継続時間の調整

`analyze_video.py` の63-76行目:

```python
MIN_DURATION = {
    "vibration:heartbeat": 2.5,  # ドキドキの長さ
    "vibration:strong": 1.0,     # 衝撃の長さ
    "wind:long": 1.5,            # 風の長さ
    # ... カスタマイズ可能
}
```

---

## 🔍 処理の流れ

```
1. 動画ファイル読み込み
   ↓
2. 0.5秒間隔でフレーム抽出
   ↓
3. 15枚ずつバッチ処理
   ↓
4. GPT-4o-mini Vision APIで解析
   ↓
5. キャプション生成
   ↓
6. ルールベースで効果判定
   ↓
7. 差分計算（start/stop）
   ↓
8. 最小継続時間を適用
   ↓
9. JSONファイル出力
```

---

## 📝 使用例

### 例1: 基本的な使用

```bash
# 1. 動画を配置
videos/my_action_video.mp4

# 2. 解析実行
python analyze_video.py my_action_video.mp4

# 3. 結果確認
results/my_action_video_timeline.json
```

### 例2: フルパス指定

```bash
python analyze_video.py "C:\Users\saise\OneDrive\ドキュメント\JPHACKS\video_scene_processor\videos\demo用動画案１.mp4"
```

---

## 🎯 対応している効果

### 振動（vibration）
- `long`: 弱い振動（乗り物搭乗中・移動中）
- `strong`: 強い衝撃（爆発・衝突・攻撃）
- `heartbeat`: ドキドキ（緊張シーン）

### 光（flash）
- `strobe`: ストロボ（雷・稲妻）
- `burst`: 閃光（爆発・火花）
- `steady`: 照明（炎・夕日）

### 風（wind）
- `burst`: 一瞬の風（衝撃波・爆風）
- `long`: 長い風（疾走・砂埃）

### 水（water）
- `burst`: 水しぶき（水・波・唾）

### 色（color）
- `red`: 赤色（炎・火・爆発）
- `green`: 緑色（森・草原）
- `blue`: 青色（空・海）

---

## ⚠️ 注意事項

### 1. APIキーの設定
- OpenAI APIキーが必要です
- `analyze_video.py` の48行目に設定してください

### 2. 動画ファイル形式
- **MP4形式のみ対応**
- 他の形式は事前に変換が必要

### 3. 処理時間
- 約2-3分/分の動画（バッチ処理）
- 長い動画は時間がかかります

### 4. APIコスト
- GPT-4o-mini Vision APIの使用料が発生します
- バッチ処理により効率化されています

### 5. レート制限
- APIレート制限に達した場合、自動で60秒待機してリトライします
- バッチ間に15秒の待機時間があります

---

## 🐛 トラブルシューティング

### エラー: "動画ファイルが見つかりません"
→ `videos/` ディレクトリに動画を配置してください

### エラー: "OPENAI_API_KEY 未設定"
→ `analyze_video.py` の48行目にAPIキーを設定してください

### エラー: "Rate limit exceeded"
→ 自動で60秒待機してリトライします（待機してください）

### エラー: "Connection timeout"
→ インターネット接続を確認してください

---

## 📚 関連ドキュメント

- **詳細な使い方**: `README.md`
- **技術詳細**: `TECH_STACK.md`
- **タイミング調整**: `TIMING_GUIDE.md`

---

## 🎬 まとめ

### JSONファイルを作成する手順

1. ✅ `analyze_video.py` がメインファイル
2. ✅ 動画を `videos/` に配置
3. ✅ OpenAI APIキーを設定
4. ✅ `python analyze_video.py 動画名.mp4` を実行
5. ✅ `results/動画名_timeline.json` が生成される

### 関連ファイル

- **生成**: `analyze_video.py`
- **使用**: `playback_video.py`
- **設定**: `requirements.txt`
- **ドキュメント**: `README.md`

---

**🎬 新しいJSONファイルを作成して、4DX体験を楽しんでください！**


