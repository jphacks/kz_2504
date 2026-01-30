# 🎬 4DX@HOME v3 タイムライン生成ツール

任意のMP4動画を解析して、3世代目デバイス仕様に準拠したタイムラインJSONを自動生成するツールです。

## ✅ 対応効果（v3仕様）

- **振動（vibration）**: up / down / up_down + heartbeat
- **光（flash）**: steady / blink / breathe
- **色（color）**: pink / red / orange / yellow / yellow_green / green / dark_green / cyan / blue / purple / white
- **LED強さ（led_strength）**: off / weak / strong
- **LED変化（led_transition）**: instant / fade
- **風（wind）**: burst
- **水（water）**: burst（shot）/ stream（start/stop）
- **ミスト（mist）**: burst（shot）/ stream（start/stop）

仕様詳細は `JSON_SPECIFICATION.md` を参照してください。

## 🚀 セットアップ

```bash
pip install -r requirements_gemini.txt
```

Gemini APIキーを環境変数に設定してください:

```bash
set GEMINI_API_KEY=YOUR_KEY
```

## 💻 使い方

### 1) 解析（動画 → JSON）
```bash
python analyze_video_gemini.py my_video.mp4
```

### 2) 再生（JSON → 効果）
```bash
python playback_video.py my_video.mp4
```

### Windows 簡易実行
```
setup.bat
run_analyze.bat
run_playback.bat
```

## 📂 ディレクトリ構成

```
connotation_tools_v3/
├── analyze_video_gemini.py
├── playback_video.py
├── prompts.py
├── requirements_gemini.txt
├── JSON_SPECIFICATION.md
├── PROMPT_GUIDE.md
├── setup.bat
├── run_analyze.bat
├── run_playback.bat
├── videos/
└── results/
```

## 📝 プロンプト

デフォルトのプロンプトは `4dx_home_v3` です。  
詳細は `PROMPT_GUIDE.md` を参照してください。

