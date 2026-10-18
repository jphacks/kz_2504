import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Optional

from PIL import Image
import google.generativeai as genai

from prompts import get_prompt

SCRIPT_DIR = Path(__file__).parent.absolute()
VIDEOS_DIR = SCRIPT_DIR / "videos"
FRAMES_DIR = SCRIPT_DIR / "frames"
EDITOR_RESULTS_DIR = SCRIPT_DIR / "editor_results"
DEFAULT_SPEC_PATH = SCRIPT_DIR / "JSON_SPECIFICATION.md"

MODEL_NAME = "gemini-2.5-pro"

# 直接書きたい場合はここにキー文字列を入れる（例: "AIza..."）。空文字なら無効。
HARD_CODED_GEMINI_API_KEY = "/"
# 優先順: ハードコード > 環境変数
GEMINI_API_KEY = HARD_CODED_GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("⚠️  GEMINI_API_KEY が設定されていません。")
    print("   環境変数 GEMINI_API_KEY を設定するか、")
    print("   コード内の HARD_CODED_GEMINI_API_KEY に設定してください。")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_images(frames_dir: Path, max_frames: int) -> List[Image.Image]:
    if not frames_dir.exists():
        return []
    files = sorted([p for p in frames_dir.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")])
    if not files:
        return []
    if max_frames <= 0:
        max_frames = len(files)
    if len(files) <= max_frames:
        chosen = files
    else:
        step = len(files) / float(max_frames)
        chosen = [files[int(i * step)] for i in range(max_frames)]
    images = []
    for f in chosen:
        try:
            images.append(Image.open(f))
        except Exception:
            continue
    return images


def maybe_upload_video(video_path: Path):
    if not video_path.exists():
        return None
    if hasattr(genai, "upload_file"):
        try:
            return genai.upload_file(str(video_path))
        except Exception:
            return None
    return None


def build_prompt(spec_text: str, json_text: str, prev_prompt: str) -> str:
    return (
        "あなたは4DX@HOMEのタイムライン生成を最適化する研究者です。\n"
        "以下の素材をすべて参照して、新しい仕様書とプロンプトを作成してください。\n"
        "\n"
        "目的:\n"
        "- エディターで作成されたJSONの意図と品質を完全に再現できるAIを作る\n"
        "- 前のプロンプトとの差分や改善点、デバイス仕様の変更点を明確に反映する\n"
        "- 4FPS(0.25秒)基準のタイムライン生成に最適化する\n"
        "\n"
        "入力:\n"
        "- 仕様書(最新)\n"
        "- エディターのJSON(正解データ)\n"
        "- 以前のプロンプト(参照用)\n"
        "- 動画/フレーム画像(映像コンテキスト)\n"
        "\n"
        "出力形式は必ずJSONで、以下のキーを含めてください:\n"
        "{\n"
        "  \"spec_markdown\": \"...\",\n"
        "  \"prompt_text\": \"...\",\n"
        "  \"notes\": \"...\"\n"
        "}\n"
        "\n"
        "注意:\n"
        "- spec_markdownはMarkdown形式で、旧仕様との差分も分かるように書く\n"
        "- prompt_textはGemini向けの最終プロンプト全文\n"
        "- notesには意図の読み取り方、重要なヒューリスティック、再現性の注意点を書く\n"
        "\n"
        "==== 仕様書(最新) ====\n"
        f"{spec_text}\n"
        "\n"
        "==== エディターJSON(正解) ====\n"
        f"{json_text}\n"
        "\n"
        "==== 以前のプロンプト ====\n"
        f"{prev_prompt}\n"
    )


def main():
    parser = argparse.ArgumentParser(description="Editor JSONから仕様書/プロンプトを再生成")
    parser.add_argument("video", help="動画ファイル名またはパス")
    parser.add_argument("--json", dest="json_path", default=None, help="エディターJSONパス")
    parser.add_argument("--spec", dest="spec_path", default=None, help="仕様書パス")
    parser.add_argument("--max-frames", dest="max_frames", type=int, default=120, help="送信する最大フレーム数")
    parser.add_argument("--model", dest="model", default=MODEL_NAME, help="Geminiモデル名")
    parser.add_argument("--out-dir", dest="out_dir", default=str(SCRIPT_DIR / "research_outputs"), help="出力先ディレクトリ")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        candidate = VIDEOS_DIR / args.video
        if candidate.exists():
            video_path = candidate

    json_path = Path(args.json_path) if args.json_path else None
    if json_path is None or not json_path.exists():
        base = video_path.stem
        json_path = EDITOR_RESULTS_DIR / f"{base}_timeline.json"
    if not json_path.exists():
        raise FileNotFoundError(f"JSONが見つかりません: {json_path}")

    spec_path = Path(args.spec_path) if args.spec_path else DEFAULT_SPEC_PATH
    if not spec_path.exists():
        raise FileNotFoundError(f"仕様書が見つかりません: {spec_path}")

    frames_dir = FRAMES_DIR / video_path.stem
    images = load_images(frames_dir, args.max_frames)

    spec_text = read_text(spec_path)
    json_text = read_text(json_path)
    prev_prompt = get_prompt(num_frames=len(images) if images else 15)
    prompt_text = build_prompt(spec_text, json_text, prev_prompt)

    model = genai.GenerativeModel(args.model)

    content = [prompt_text]
    uploaded_video = maybe_upload_video(video_path)
    if uploaded_video is not None:
        content.append(uploaded_video)
    if images:
        content.extend(images)

    generation_config = {
        "temperature": 0.2,
        "max_output_tokens": 4096,
        "response_mime_type": "application/json",
    }

    response = model.generate_content(content, generation_config=generation_config)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result_text = response.text
    result_path = out_dir / "gemini_spec_prompt.json"
    result_path.write_text(result_text, encoding="utf-8")

    try:
        result = json.loads(result_text)
        (out_dir / "generated_spec.md").write_text(result.get("spec_markdown", ""), encoding="utf-8")
        (out_dir / "generated_prompt.txt").write_text(result.get("prompt_text", ""), encoding="utf-8")
        (out_dir / "notes.txt").write_text(result.get("notes", ""), encoding="utf-8")
    except Exception:
        pass

    print(f"✅ 完了: {result_path}")
    if uploaded_video is None:
        print("⚠️ 動画はアップロードされませんでした（SDK未対応 or 失敗）。")


if __name__ == "__main__":
    main()
