# -*- coding: utf-8 -*-
"""
【解析モード】ローカル動画シーン解析（MP4専用）- Gemini版
- MP4動画ファイルを読み込み
- 0.5秒間隔でフレームをスクリーンショット
- Google Geminiで各フレームをキャプション化
- 効果（光/風/水/色/衝撃）をJSON形式で出力

使い方:
    python analyze_video_gemini.py video.mp4

出力: results/{video_name}_timeline.json
"""

import os, sys, cv2, json, warnings, contextlib, base64
from typing import List, Tuple, Dict
from pathlib import Path
from PIL import Image
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

try:
    import google.generativeai as genai
except ImportError:
    print("❌ google-generativeai がインストールされていません。")
    print("以下のコマンドでインストールしてください:")
    print("  pip install google-generativeai")
    sys.exit(1)

# OpenCVとFFmpegの警告を完全に抑制
os.environ['OPENCV_LOG_LEVEL'] = 'FATAL'
os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'loglevel;fatal'
os.environ['OPENCV_VIDEOIO_DEBUG'] = '0'
warnings.filterwarnings('ignore')
cv2.setLogLevel(0)

@contextlib.contextmanager
def suppress_stderr():
    """標準エラー出力を抑制"""
    stderr_fd = sys.stderr.fileno()
    with open(os.devnull, 'w') as devnull:
        old_stderr = os.dup(stderr_fd)
        os.dup2(devnull.fileno(), stderr_fd)
        try:
            yield
        finally:
            os.dup2(old_stderr, stderr_fd)
            os.close(old_stderr)

# ===== 設定 =====
# スクリプトのディレクトリを基準にパスを解決
SCRIPT_DIR = Path(__file__).parent.absolute()
VIDEOS_DIR = str(SCRIPT_DIR / "videos")            # ユーザーが動画を配置するディレクトリ
RESULTS_DIR = str(SCRIPT_DIR / "results")          # JSON出力先
SAMPLE_INTERVAL = 0.25           # 0.25秒ごとにサンプリング（4DX@HOME仕様）
BATCH_SIZE = 100                 # 一度に処理するフレーム数（4DX@HOME仕様、最大480枚まで対応可能）
MODEL_NAME = "gemini-2.5-pro"    # Geminiモデル名（4DX@HOME仕様: gemini-2.5-pro固定）
TARGET_WIDTH = 640               # API負荷軽減の縮小幅
PROMPT_NAME = "4dx_home"        # 使用するプロンプト名（4DX@HOME専用プロンプト）
MAX_CONCURRENT_REQUESTS = 10     # 同時実行数の上限（Gemini APIの並列リクエスト数）

# 直接書きたい場合はここにキー文字列を入れる（例: "AIza..."）。空文字なら無効。
HARD_CODED_GEMINI_API_KEY = "/"
# 優先順: ハードコード > 環境変数
GEMINI_API_KEY = HARD_CODED_GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")

# Gemini APIの初期化
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("⚠️  GEMINI_API_KEY が設定されていません。")
    print("   環境変数 GEMINI_API_KEY を設定するか、")
    print("   コード内の HARD_CODED_GEMINI_API_KEY に設定してください。")

# ===== 効果ドメイン（4DX@HOME仕様）=====
EFFECT_DOMAIN = {
    "flash": ["steady", "slow_blink", "fast_blink"],  # 光: 点灯/遅い点滅/早い点滅
    "wind": ["on"],                                    # 風: オン/オフ
    "water": ["on"],                                   # 水しぶき: オン/オフ
    "color": ["red", "green", "blue", "yellow", "cyan", "purple"],  # 色: 赤/緑/青/黄色/シアン/紫
    "vibration": ["up_strong", "up_mid_strong", "up_mid_weak", "up_weak",  # 振動: 上の強/中強/中弱/弱（背中）
                  "down_strong", "down_mid_strong", "down_mid_weak", "down_weak",  # 下の強/中強/中弱/弱（おしり）
                  "up_down_strong", "up_down_mid_strong", "up_down_mid_weak", "up_down_weak",  # 上＆下同時（背中＆おしり、かなり強い）
                  "heartbeat"],  # ドキドキ
}

# ===== 効果の最小継続時間（秒）- 4DX@HOME仕様 =====
MIN_DURATION = {
    # 振動: 0.5秒以上（時には0.25秒でも可）
    "vibration:up_strong": 0.5,
    "vibration:up_mid_strong": 0.5,
    "vibration:up_mid_weak": 0.5,
    "vibration:up_weak": 0.5,
    "vibration:down_strong": 0.5,
    "vibration:down_mid_strong": 0.5,
    "vibration:down_mid_weak": 0.5,
    "vibration:down_weak": 0.5,
    "vibration:up_down_strong": 0.5,      # 上＆下同時: 強（かなり強い）
    "vibration:up_down_mid_strong": 0.5,   # 上＆下同時: 中強（かなり強い）
    "vibration:up_down_mid_weak": 0.5,     # 上＆下同時: 中弱（かなり強い）
    "vibration:up_down_weak": 0.5,         # 上＆下同時: 弱（かなり強い）
    "vibration:heartbeat": 0.5,  # ドキドキも0.5秒以上
    
    # 光: 2-3秒程度ゆっくり変化（映像に合わせて）
    "flash:steady": 2.0,         # 点灯: 2秒以上
    "flash:slow_blink": 2.0,     # 遅い点滅: 2秒以上
    "flash:fast_blink": 1.0,     # 早い点滅: 1秒以上
    
    # 色: 2-3秒程度ゆっくり変化
    "color:red": 2.0,
    "color:green": 2.0,
    "color:blue": 2.0,
    "color:yellow": 2.0,
    "color:cyan": 2.0,
    "color:purple": 2.0,
    
    # 風: 継続的に
    "wind:on": 1.0,
    
    # 水しぶき: 瞬間的
    "water:on": 0.5,
}

# ===== ルール: キャプション→効果（4DX@HOME仕様 - 新ルール）=====
# 注意: このルールは参考用。実際の判定はプロンプトでAIが行う
RULES = [
    # === 振動を停止する条件（最優先でチェック）===
    # これらのキーワードがある場合は振動を出さない
    # （decide_effects関数内で別途処理）
    
    # === 強い衝撃（瞬間的）===
    # 衝突の瞬間
    (["衝突する瞬間","衝突の瞬間","ぶつかる瞬間","激突","moment of collision","crash into","smash"],
     [("vibration","strong")]),
    
    # 爆発の瞬間
    (["爆発する瞬間","爆発の瞬間","爆発が発生","爆発した","explosion occurs","explodes","detonates"],
     [("vibration","strong"), ("flash","burst"), ("color","red")]),
    
    # 着地の瞬間
    (["着地する瞬間","着地の瞬間","地面に叩きつけ","lands","touches down","hits ground"],
     [("vibration","strong")]),
    
    # 攻撃の瞬間
    (["攻撃の瞬間","打撃の瞬間","殴る瞬間","蹴る瞬間","hits","strikes","punches","kicks"],
     [("vibration","strong")]),
    
    # === 弱い振動（継続的）===
    # 乗り物に乗っている間（最優先）
    (["乗っている","乗車","戦闘機","車内","船","飛行機","コックピット","運転席","操縦",
      "riding","on board","in the","piloting","cockpit","driving","vehicle"],
     [("vibration","long")]),
    
    # 移動中・飛行中
    (["飛行中","飛んでいる","移動中","走行中","運転中","歩いている","走っている","進んでいる",
      "flying","moving","driving","running","walking","advancing","traveling"],
     [("vibration","long")]),
    
    # 戦闘・バトル中（激しい動き）
    (["戦闘中","バトル中","戦っている","暴れている","激しく動いている","格闘",
      "fighting","battling","combat","struggling","intense"],
     [("vibration","long")]),
    
    # === 生物のアクション ===
    # 咆哮・吠える・叫び（衝撃波 + 唾・息の飛沫）- 最優先で検出
    (["咆哮","咆哮している","吠える","吠えている","吠えた","叫ぶ","叫んでいる","絶叫","怒鳴る","唸る",
      "roar","roaring","roars","howl","howling","scream","screaming","shout","shouting","yell","yelling","growl","snarl"],
     [("vibration","strong"), ("water","burst"), ("wind","burst")]),
    
    # 呼吸・溜息（風・息）
    (["呼吸","溜息","息","吐く","吸う","breath","sigh","exhale","inhale"],
     [("wind","burst")]),
    
    # === 光の効果 ===
    # 雷（チカチカ）
    (["雷","稲妻","雷鳴","lightning","thunder"],
     [("flash","strobe")]),
    
    # 爆発（光 + 振動 + 炎の色）
    (["爆発","閃光","爆破","炸裂","explosion","explode","blast","detonation"],
     [("flash","burst"), ("vibration","strong"), ("color","red")]),
    
    # 火花（光 + 振動）
    (["火花","スパーク","火の粉","spark","sparks","sparking"],
     [("flash","burst"), ("vibration","strong")]),
    
    # 炎が見える（光 + 振動 + 赤色）
    (["炎が見える","炎が上がる","燃えている","炎","flames","fire","burning"],
     [("flash","steady"), ("vibration","long"), ("color","red")]),
    
    # 照明・夕日（継続的な光）
    (["照らす","ライト","光る","夕日","照明","日差し","light","illuminate","shine","sunset","sunlight"],
     [("flash","steady")]),
    
    # === 風 ===
    # 衝撃波・爆風（一瞬）
    (["衝撃波","突風","爆風","blast","shock wave","gust"],
     [("wind","burst")]),
    
    # 継続的な風
    (["風","砂埃","煙","疾走","スピード","wind","dust","smoke","speed","fast"],
     [("wind","long")]),
    
    # === 水・飛沫 ===
    # 唾・息の飛沫
    (["唾","つば","飛沫","よだれ","saliva","spit","drool"],
     [("water","burst")]),
    
    # 水しぶき・波
    (["水","水しぶき","波","噴射","スプレー","濡れる","雨","汗","blood","water","splash","spray","wave","wet","rain"],
     [("water","burst")]),
    
    # === 色 ===
    (["赤","炎","火","オレンジ","血","red","flame","fire","orange","blood"],
     [("color","red")]),
    (["緑","森","草原","自然","green","forest","grass","nature"],
     [("color","green")]),
    (["青","空","海","水","blue","sky","ocean","water"],
     [("color","blue")]),
    
    # === その他の振動 ===
    # 緊張感（ドキドキ）
    (["緊張","ドキドキ","心拍","不安","危険","tense","nervous","anxious","heartbeat","danger"],
     [("vibration","heartbeat")]),
]

# ===== ユーティリティ =====
def resize_and_b64(frame_bgr, target_w=TARGET_WIDTH):
    """画像を縮小してPNG→Base64化"""
    h, w = frame_bgr.shape[:2]
    if w > target_w:
        scale = target_w / float(w)
        frame_bgr = cv2.resize(frame_bgr, (target_w, int(h*scale)))
    ok, buf = cv2.imencode(".png", frame_bgr)
    if not ok:
        raise RuntimeError("PNGエンコード失敗")
    return base64.b64encode(buf.tobytes()).decode("utf-8")

def base64_to_pil_image(base64_str: str) -> Image.Image:
    """Base64文字列をPIL Imageに変換"""
    image_data = base64.b64decode(base64_str)
    return Image.open(io.BytesIO(image_data))

def get_video_info(video_path: str) -> Tuple[float, int, float]:
    """動画情報を取得"""
    with suppress_stderr():
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"動画を開けない: {video_path}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0.0
        cap.release()
    return fps, total_frames, duration

def format_actions_for_prompt(effs: List[Tuple[str,str]]) -> str:
    if not effs:
        return "(none)"
    return ", ".join([f"{e}:{m}" for e, m in effs])

def format_delta_for_prompt(delta_events: List[Dict]) -> str:
    if not delta_events:
        return "(none)"
    parts = []
    for ev in delta_events:
        if ev.get("action") in ("start", "stop"):
            parts.append(f"{ev['action']} {ev['effect']}:{ev['mode']}")
    return ", ".join(parts) if parts else "(none)"

def list_available_models():
    """利用可能なGeminiモデルをリストアップ"""
    if not GEMINI_API_KEY:
        print("⚠️  APIキーが設定されていないため、モデル一覧を取得できません。")
        return []
    
    try:
        models = genai.list_models()
        available = []
        for m in models:
            # generateContentメソッドをサポートしているモデルを取得
            if hasattr(m, 'supported_generation_methods') and 'generateContent' in m.supported_generation_methods:
                model_name = m.name.replace('models/', '')
                available.append(model_name)
        return available
    except Exception as e:
        print(f"⚠️  モデル一覧の取得に失敗: {e}")
        import traceback
        traceback.print_exc()
        return []

def caption_batch_vlm(frames_data: List[Dict], model_name: str = None, prompt_name: str = None) -> Tuple[List[str], List[Dict]]:
    """バッチ処理: 複数フレームを一度に解析（Gemini版）"""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY 未設定。環境変数に設定するか、コード内のHARD_CODED_GEMINI_API_KEYに設定してください。")
    
    # プロンプトをインポート
    try:
        from prompts import get_prompt
    except ImportError:
        raise RuntimeError("prompts.py が見つかりません。同じディレクトリに配置してください。")
    
    # モデル名が指定されていない場合、利用可能なモデルを自動選択
    if model_name is None:
        model_name = get_available_model()
    
    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        # モデルが見つからない場合、利用可能なモデルを表示
        error_msg = str(e)
        if "not found" in error_msg.lower() or "404" in error_msg:
            print(f"\n❌ モデル '{MODEL_NAME}' が見つかりません。")
            print("📋 利用可能なモデルを確認中...")
            available = list_available_models()
            if available:
                print("✅ 利用可能なモデル:")
                for m in available:
                    print(f"   - {m}")
                print(f"\n💡 コード内の MODEL_NAME を上記のいずれかに変更してください。")
            else:
                print("⚠️  利用可能なモデルを取得できませんでした。")
        raise RuntimeError(f"Geminiモデルの初期化に失敗: {e}")
    
    # プロンプトの取得
    prompt_text = get_prompt(prompt_name, num_frames=len(frames_data))
    
    # 画像をPIL Imageに変換
    images = []
    for frame_data in frames_data:
        pil_image = base64_to_pil_image(frame_data['b64_image'])
        images.append(pil_image)
    
    # Gemini APIに送信（画像とテキストを組み合わせ）
    content = [prompt_text] + images
    
    try:
        # 生成設定
        generation_config = {
            "temperature": 0.2,
            "max_output_tokens": 2048 * len(frames_data),  # 4DX@HOME仕様: 効果情報も含むため増やす
            "response_mime_type": "application/json",
        }
        
        response = model.generate_content(
            content,
            generation_config=generation_config
        )
        
        # レスポンスからテキストを取得
        response_text = response.text
        
        # JSONを解析
        try:
            obj = json.loads(response_text)
            
            # 4DX@HOME仕様: frames形式かcaptions形式かを判定
            if "frames" in obj:
                # 新しい形式（4DX@HOME）
                frames_data_result = obj.get("frames", [])
                captions = []
                effects_list = []
                
                for frame_result in frames_data_result:
                    captions.append(frame_result.get("caption", "シーンが続く"))
                    effects_list.append(frame_result.get("effects", {}))
                
                # 不足分を補完
                while len(captions) < len(frames_data):
                    captions.append(captions[-1] if captions else "シーンが続く")
                    effects_list.append({})
                
                return captions, effects_list
            else:
                # 旧形式（captionsのみ）
                captions = obj.get("captions", [])
                if not isinstance(captions, list):
                    raise ValueError("captions が配列ではありません")
                
                if len(captions) != len(frames_data):
                    if len(captions) > len(frames_data):
                        print(f"      ⚠️  キャプション数が多い（期待={len(frames_data)}, 取得={len(captions)}）-> 最初の{len(frames_data)}個を使用")
                        captions = captions[:len(frames_data)]
                    else:
                        print(f"      ⚠️  キャプション数が少ない（期待={len(frames_data)}, 取得={len(captions)}）-> 調整中...")
                        combined = " ".join(captions)
                        captions = [combined] + captions[1:] if len(captions) > 0 else []
                        while len(captions) < len(frames_data):
                            captions.append(captions[-1] if captions else "シーンが続く")
                
                # 旧形式の場合は効果なし
                return captions, [{}] * len(captions)
                
        except json.JSONDecodeError as e:
            # JSON解析に失敗した場合、テキストから直接抽出を試みる
            print(f"      ⚠️  JSON解析失敗、テキストから抽出を試みます...")
            # レスポンステキストを行ごとに分割してキャプションとして使用
            lines = [line.strip() for line in response_text.split('\n') if line.strip()]
            if len(lines) >= len(frames_data):
                captions = lines[:len(frames_data)]
            else:
                # 不足分を補完
                while len(lines) < len(frames_data):
                    lines.append(lines[-1] if lines else "シーンが続く")
                captions = lines
            
            return captions, [{}] * len(captions)
                
    except Exception as e:
        raise RuntimeError(f"Gemini API呼び出し失敗: {e}")

def get_effect_display_name(effect: str, mode: str) -> str:
    """効果の日本語表示名を取得（4DX@HOME仕様）"""
    effect_names = {
        # 光
        "flash:steady": "💡点灯",
        "flash:slow_blink": "💡遅い点滅",
        "flash:fast_blink": "⚡早い点滅",
        # 色
        "color:red": "🔴赤",
        "color:green": "🟢緑",
        "color:blue": "🔵青",
        "color:yellow": "🟡黄色",
        "color:cyan": "🔷シアン",
        "color:purple": "🟣紫",
        # 振動
        "vibration:up_strong": "📳上:強",
        "vibration:up_mid_strong": "📳上:中強",
        "vibration:up_mid_weak": "📳上:中弱",
        "vibration:up_weak": "📳上:弱",
        "vibration:down_strong": "📳下:強",
        "vibration:down_mid_strong": "📳下:中強",
        "vibration:down_mid_weak": "📳下:中弱",
        "vibration:down_weak": "📳下:弱",
        "vibration:heartbeat": "💓ドキドキ",
        # 風・水
        "wind:on": "💨風",
        "water:on": "💦水しぶき",
    }
    return effect_names.get(f"{effect}:{mode}", f"{effect}:{mode}")

def decide_effects_from_json(effects_dict: Dict) -> List[Tuple[str,str]]:
    """JSON形式の効果情報から効果リストを生成（4DX@HOME仕様）"""
    chosen: List[Tuple[str,str]] = []
    
    # 各効果タイプをチェック
    for effect_type in ["flash", "color", "vibration", "water", "wind"]:
        mode = effects_dict.get(effect_type)
        if mode and mode != "null" and mode is not None:
            # 水と風は内部で "on" として扱う（出力時に既存JSON形式に変換）
            if effect_type == "water" and mode == "on":
                chosen.append((effect_type, "on"))  # 内部処理用
            elif effect_type == "wind" and mode == "on":
                chosen.append((effect_type, "on"))  # 内部処理用、出力時に "burst" に変換
            else:
                chosen.append((effect_type, mode))
    
    return chosen

def decide_effects(caption: str, effects_dict: Dict = None) -> List[Tuple[str,str]]:
    """キャプションまたはJSON効果情報から効果集合を決定（4DX@HOME仕様）"""
    # 4DX@HOME仕様: JSON効果情報が優先
    if effects_dict:
        return decide_effects_from_json(effects_dict)
    
    # フォールバック: 旧方式（キャプションから判定）
    cap_l = caption.lower()
    chosen: List[Tuple[str,str]] = []
    
    # === 振動を止める条件（厳格に判定）===
    # 完全に静止している場合のみ
    is_static = any(kw in caption or kw in cap_l for kw in 
                    ["完全に静止", "全く動いていない", "静止している",
                     "completely still", "totally motionless"])
    
    # 降りていて かつ 静止している（両方必要）
    is_dismounted_and_static = (
        any(kw in caption or kw in cap_l for kw in ["降りている", "降りた", "dismounted"]) and
        is_static
    )
    
    # === 振動を出す条件 ===
    # ジャンプ中・空中の判定（乗り物なしで空中にいる場合）
    is_airborne = any(kw in caption or kw in cap_l for kw in 
                      ["ジャンプ", "空中", "飛ぶ", "浮かぶ", "宙", "jump", "airborne", "flying", "mid-air"])
    
    # 乗り物に乗っているかの判定（より詳細に）
    is_riding = any(kw in caption or kw in cap_l for kw in 
                    ["乗っている", "乗車", "戦闘機に", "車に", "船に", "飛行機に", "馬に",
                     "riding", "on board", "in the", "in vehicle", "piloting", "driving"])
    
    # ルールマッチング
    for kws, effs in RULES:
        if any((kw in caption) or (kw.lower() in cap_l) for kw in kws):
            chosen.extend(effs)
    
    # === 振動の除外ロジック（緩く） ===
    # 1. 完全に静止している場合のみ弱い振動を除外
    if is_dismounted_and_static:
        chosen = [(e, m) for e, m in chosen if not (e == "vibration" and m == "long")]
    
    # 2. 空中かつ乗り物に乗っていない場合のみ、継続的な振動を除外
    # （乗り物に乗っていれば空中でも振動あり）
    if is_airborne and not is_riding:
        chosen = [(e, m) for e, m in chosen if not (e == "vibration" and m in ["long", "heartbeat"])]
    
    # 重複除去
    seen, uniq = set(), []
    for e in chosen:
        if e not in seen:
            seen.add(e); uniq.append(e)
    return uniq

def diff_events(prev_eff: List[Tuple[str,str]], curr_eff: List[Tuple[str,str]], t: float, 
                effect_start_times: Dict[Tuple[str,str], float]) -> Tuple[List[Dict], List[Tuple[str,str]]]:
    """
    前回との差分で start/stop を生成（4DX@HOME仕様）
    最小継続時間を考慮して、短すぎる効果は継続させる
    水は shot アクション、風は start/stop で制御（既存JSON形式に合わせる）
    """
    events = []
    ps, cs = set(prev_eff), set(curr_eff)
    
    # 水の効果を特別処理（一度きりの発射 - 既存JSON形式に合わせる）
    water_effects = {eff for eff in (cs - ps) if eff[0] == "water"}
    for eff in water_effects:
        # 水は "shot" アクションで一度だけ発火（既存JSON形式: "burst" モード）
        events.append({"t": round(t,3), "action":"shot", "effect":eff[0], "mode":"burst"})
        # csから削除（start/stopの対象外）
        cs.discard(eff)
    
    # 水以外の効果を処理
    # 停止候補の効果
    for eff in (ps - cs):
        if eff[0] == "water":
            continue  # 水は既に処理済み
        
        effect_key = f"{eff[0]}:{eff[1]}"
        start_time = effect_start_times.get(eff, 0.0)
        duration = t - start_time
        min_duration = MIN_DURATION.get(effect_key, 0.5)
        
        # 同じeffect typeの別modeが来た場合の判定
        same_type_different_mode = [e for e in cs if e[0] == eff[0] and e != eff]
        
        # 振動は複数のモードを同時に持てる
        # 光・色は上書き（同じタイプの別モードが来たら切り替え）
        # 風は単一（on/off、既存JSON形式では "burst" モード）
        can_coexist = (eff[0] == "vibration")
        
        # 上書きされたかどうか
        is_overwritten = len(same_type_different_mode) > 0 and not can_coexist
        
        # 最小継続時間に達していない かつ 上書きされていない場合は継続
        if duration < min_duration and not is_overwritten:
            # 継続させる
            cs.add(eff)
        else:
            # 停止（風の場合は "burst" モードに変換）
            mode = eff[1]
            if eff[0] == "wind" and mode == "on":
                mode = "burst"  # 既存JSON形式に合わせる
            events.append({"t": round(t,3), "action":"stop", "effect":eff[0], "mode":mode})
            # 開始時刻を削除
            if eff in effect_start_times:
                del effect_start_times[eff]
    
    # 新規開始の効果（水以外）
    for eff in (cs - ps):
        if eff[0] == "water":
            continue  # 水は既に処理済み
        
        # 風の場合は "on" を "burst" に変換（既存JSON形式に合わせる）
        mode = eff[1]
        if eff[0] == "wind" and mode == "on":
            mode = "burst"
        
        events.append({"t": round(t,3), "action":"start","effect":eff[0], "mode":mode})
        effect_start_times[eff] = t  # 開始時刻を記録
    
    return events, list(cs)

def get_available_model():
    """利用可能なモデルを取得し、設定されたモデルまたは最初の利用可能なモデルを返す"""
    # 4DX@HOME仕様: gemini-2.5-pro固定
    if MODEL_NAME == "gemini-2.5-pro":
        return MODEL_NAME
    
    available_models = list_available_models()
    if available_models:
        # 設定されたモデルが利用可能な場合
        if MODEL_NAME in available_models:
            return MODEL_NAME
        # 設定されたモデルが利用不可の場合、最初の利用可能なモデルを使用
        else:
            print(f"⚠️  設定されているモデル '{MODEL_NAME}' が利用できません。")
            print(f"   → 利用可能なモデル '{available_models[0]}' を自動的に使用します。")
            return available_models[0]
    else:
        # モデル一覧が取得できない場合、設定されたモデルをそのまま使用
        print("⚠️  利用可能なモデルを取得できませんでした。")
        print(f"   設定されているモデル '{MODEL_NAME}' で試行します...")
        return MODEL_NAME

def analyze_video(video_path: str):
    """動画を解析してタイムラインJSONを生成"""
    print("\n" + "=" * 60)
    print("📸【解析モード】ローカル動画シーン解析（Gemini版）")
    print("=" * 60)
    
    # 利用可能なモデルを確認
    print("\n📋 利用可能なモデルを確認中...")
    available_models = list_available_models()
    if available_models:
        print(f"✅ 利用可能なモデル: {', '.join(available_models)}")
    else:
        print("⚠️  利用可能なモデルを取得できませんでした。")
    print()
    
    # 動画ファイルの存在確認
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")
    
    # MP4チェック
    if not video_path.lower().endswith('.mp4'):
        raise ValueError(f"MP4ファイルのみ対応しています: {video_path}")
    
    # 動画を開く
    with suppress_stderr():
        cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"動画を開けない: {video_path}")
    
    with suppress_stderr():
        fps, total_frames, duration = get_video_info(video_path)
    
    print(f"\n動画情報:")
    print(f"  パス: {video_path}")
    print(f"  FPS: {fps:.2f}")
    print(f"  総フレーム数: {total_frames}")
    print(f"  長さ: {duration:.2f}秒")
    
    # 使用するモデルを決定
    actual_model = get_available_model()
    print(f"  使用モデル: {actual_model}")
    
    # サンプリングタイムスタンプを生成
    timestamps = []
    t = 0.0
    while t <= duration:
        timestamps.append(t)
        t += SAMPLE_INTERVAL
    
    print(f"  📊 サンプリング点数: {len(timestamps)}枚")
    print(f"  ⏱️  サンプリング間隔: {SAMPLE_INTERVAL}秒")
    print(f"  📦 バッチサイズ: {BATCH_SIZE}フレーム/回")
    total_batches = (len(timestamps) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"  🤖 予想API呼び出し: {total_batches}回")
    print(f"  🚀 並列実行数: {MAX_CONCURRENT_REQUESTS}（同時実行）")
    
    # 予想処理時間の計算（並列実行を考慮）
    TIME_PER_100_FRAMES = 130  # 秒（100枚で約2分10秒を基準）
    estimated_time_per_batch = (BATCH_SIZE / 100.0) * TIME_PER_100_FRAMES
    # 並列実行により、実際の処理時間は短縮される
    estimated_total_time = (estimated_time_per_batch * total_batches) / MAX_CONCURRENT_REQUESTS
    
    estimated_minutes = int(estimated_total_time // 60)
    estimated_seconds = int(estimated_total_time % 60)
    print(f"  ⏳ 予想処理時間: 約{estimated_minutes}分{estimated_seconds}秒（並列実行考慮）")
    print(f"\n🎬 AI解析を開始します...\n")
    
    # 処理開始時刻を記録
    import time
    start_time = time.time()
    
    # すべてのバッチのフレームデータを事前に準備
    print(f"\n📦 フレームデータを準備中...")
    all_batches = []
    for batch_start in range(0, len(timestamps), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(timestamps))
        batch_timestamps = timestamps[batch_start:batch_end]
        
        batch_num = batch_start//BATCH_SIZE + 1
        total_batches = (len(timestamps) + BATCH_SIZE - 1)//BATCH_SIZE
        
        # バッチ内のフレームを収集
        frames_data = []
        for t in batch_timestamps:
            with suppress_stderr():
                frame_idx = int(t * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ok, frame = cap.read()
            if not ok:
                print(f"    ⚠️  [警告] フレーム {frame_idx} (t={t:.1f}s) の読み込み失敗")
                continue
            
            b64img = resize_and_b64(frame)
            frames_data.append({"b64_image": b64img, "timestamp": t})
        
        if frames_data:
            all_batches.append({
                "batch_num": batch_num,
                "total_batches": total_batches,
                "batch_start": batch_start,
                "batch_end": batch_end,
                "frames_data": frames_data
            })
    
    cap.release()
    
    print(f"✅ {len(all_batches)}個のバッチを準備完了")
    print(f"🚀 並列実行開始（同時実行数: {MAX_CONCURRENT_REQUESTS}）\n")
    
    # バッチ処理関数（並列実行用）
    def process_batch(batch_info: Dict) -> Tuple[int, List[Tuple[Dict, str, Dict]]]:
        """単一バッチを処理して結果を返す"""
        batch_num = batch_info["batch_num"]
        total_batches = batch_info["total_batches"]
        batch_start = batch_info["batch_start"]
        batch_end = batch_info["batch_end"]
        frames_data = batch_info["frames_data"]
        
        batch_start_time = time.time()
        print(f"  📦 バッチ {batch_num}/{total_batches}: フレーム {batch_start+1}~{batch_end}枚目 [開始]")
        
        # バッチでキャプション取得（リトライロジック付き）
        api_start_time = time.time()
        print(f"    🤖 AI解析中... ({len(frames_data)}枚)", end=" ", flush=True)
        try:
            captions, effects_list = caption_batch_vlm(frames_data, actual_model, PROMPT_NAME)
            api_elapsed = time.time() - api_start_time
            print(f"✓ ({api_elapsed:.1f}秒)")
        except Exception as e:
            print(f"\n    ❌ エラー発生: {e}")
            print(f"    ⏳ 60秒待機してからリトライします...")
            time.sleep(60)
            try:
                captions, effects_list = caption_batch_vlm(frames_data, actual_model, PROMPT_NAME)
                print(f"    ✅ リトライ成功！")
            except Exception as e2:
                print(f"    ❌ リトライも失敗: {e2}")
                raise
        
        # 結果をまとめる
        results = []
        for frame_data, cap_text, effects_dict in zip(frames_data, captions, effects_list):
            results.append((frame_data, cap_text, effects_dict))
        
        batch_elapsed = time.time() - batch_start_time
        print(f"    ✅ バッチ {batch_num}/{total_batches} 完了 ({batch_elapsed:.1f}秒)")
        
        return batch_num, results
    
    # 並列実行
    batch_results: Dict[int, List[Tuple[Dict, str, Dict]]] = {}
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
        # すべてのバッチを並列実行に投入
        future_to_batch = {executor.submit(process_batch, batch_info): batch_info 
                          for batch_info in all_batches}
        
        # 完了したバッチから順に処理
        completed_count = 0
        for future in as_completed(future_to_batch):
            try:
                batch_num, results = future.result()
                batch_results[batch_num] = results
                completed_count += 1
                print(f"  📊 進捗: {completed_count}/{len(all_batches)}バッチ完了\n")
            except Exception as e:
                batch_info = future_to_batch[future]
                print(f"  ❌ バッチ {batch_info['batch_num']} でエラー: {e}")
                raise
    
    # バッチ結果を時系列順にソートして処理
    events: List[Dict] = []
    prev_effects: List[Tuple[str,str]] = []
    effect_start_times: Dict[Tuple[str,str], float] = {}  # 各効果の開始時刻を記録
    
    # バッチ番号でソート
    sorted_batch_nums = sorted(batch_results.keys())
    for batch_num in sorted_batch_nums:
        results = batch_results[batch_num]
        
        # 各フレームのキャプションと効果を処理
        for frame_data, cap_text, effects_dict in results:
            t = frame_data["timestamp"]
            
            print(f"    💬 t={t:.2f}s: {cap_text[:60]}{'...' if len(cap_text) > 60 else ''}")
            
            events.append({"t": round(t,3), "action":"caption", "text": cap_text})
            
            # 効果判定（4DX@HOME仕様: JSON効果情報を使用）
            curr_effects = decide_effects(cap_text, effects_dict)
            if curr_effects:
                effect_names = []
                for e, m in curr_effects:
                    name = get_effect_display_name(e, m)
                    effect_names.append(name)
                print(f"       ⚡ {', '.join(effect_names)}")
            
            # 差分イベント生成（最小継続時間を考慮）
            delta, updated_effects = diff_events(prev_effects, curr_effects, t, effect_start_times)
            events.extend(delta)
            prev_effects = updated_effects  # 継続された効果を含む
    
    if not events:
        raise RuntimeError("有効フレームが取得できなかった")
    
    # 終了時にONのものは必ずstopを出す（最小継続時間を適用）
    end_t = timestamps[-1] if timestamps else 0.0
    
    if prev_effects:
        for eff in prev_effects:
            # 最小継続時間を確認
            effect_key = f"{eff[0]}:{eff[1]}"
            start_time = effect_start_times.get(eff, 0.0)
            duration = end_t - start_time
            min_duration = MIN_DURATION.get(effect_key, 0.5)
            
            # 最小継続時間に達していない場合は、延長してから停止
            stop_time = max(end_t, start_time + min_duration)
            events.append({"t": round(stop_time,3), "action":"stop", "effect": eff[0], "mode": eff[1]})
    
    # 最終的にすべての効果を確実に停止（動画の最後のタイムスタンプで）
    # すべての効果タイプとモードの組み合わせを停止
    final_stop_time = end_t + 0.1  # 少し余裕を持たせる
    all_effect_types = ["flash", "color", "vibration", "wind"]
    for effect_type in all_effect_types:
        if effect_type in EFFECT_DOMAIN:
            for mode in EFFECT_DOMAIN[effect_type]:
                # 既に停止イベントがあるかチェック（最後の0.2秒以内）
                already_stopped = any(
                    e.get("action") == "stop" and 
                    e.get("effect") == effect_type and 
                    e.get("mode") == mode and
                    abs(e.get("t", 0) - final_stop_time) < 0.2
                    for e in events
                )
                if not already_stopped:
                    # 風の場合は "on" を "burst" に変換（既存JSON形式に合わせる）
                    output_mode = "burst" if (effect_type == "wind" and mode == "on") else mode
                    events.append({
                        "t": round(final_stop_time, 3),
                        "action": "stop",
                        "effect": effect_type,
                        "mode": output_mode
                    })
    
    # 結果ディレクトリ作成
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # 出力ファイル名（動画名をベースに）
    video_name = Path(video_path).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_json = os.path.join(RESULTS_DIR, f"{video_name}_timeline_{timestamp}.json")
    
    # JSON出力
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({"events": events}, f, ensure_ascii=False, indent=2)
    
    # 処理終了時刻を記録
    end_time = time.time()
    total_elapsed = end_time - start_time
    total_minutes = int(total_elapsed // 60)
    total_seconds = int(total_elapsed % 60)
    
    print(f"\n" + "=" * 60)
    print(f"✅ 解析完了しました！")
    print(f"  📄 出力ファイル: {output_json}")
    print(f"  📊 総イベント数: {len(events)}個")
    caption_count = sum(1 for e in events if e.get('action') == 'caption')
    effect_count = len(events) - caption_count
    print(f"  💬 キャプション: {caption_count}個")
    print(f"  ⚡ 効果イベント: {effect_count}個")
    print(f"  ⏱️  実際の処理時間: {total_minutes}分{total_seconds}秒 ({total_elapsed:.1f}秒)")
    print("=" * 60)
    
    return output_json

if __name__ == "__main__":
    import sys
    
    # モデル一覧を確認するオプション
    if len(sys.argv) > 1 and sys.argv[1] == "--list-models":
        print("📋 利用可能なGeminiモデルを確認中...\n")
        available = list_available_models()
        if available:
            print("✅ 利用可能なモデル:")
            for m in available:
                print(f"   - {m}")
            print(f"\n💡 現在の設定: MODEL_NAME = '{MODEL_NAME}'")
            print(f"   コード内の MODEL_NAME を上記のいずれかに変更してください。")
        else:
            print("⚠️  利用可能なモデルを取得できませんでした。")
            print("   APIキーが正しく設定されているか確認してください。")
        sys.exit(0)
    
    # プロンプト一覧を確認するオプション
    if len(sys.argv) > 1 and sys.argv[1] == "--list-prompts":
        try:
            from prompts import list_prompts, DEFAULT_PROMPT
            print("📋 利用可能なプロンプト:")
            for name in list_prompts():
                marker = " (デフォルト)" if name == DEFAULT_PROMPT else ""
                print(f"   - {name}{marker}")
            print(f"\n💡 現在の設定: PROMPT_NAME = {PROMPT_NAME if PROMPT_NAME else 'None (デフォルト)'}")
            print(f"   コード内の PROMPT_NAME を上記のいずれかに変更してください。")
        except ImportError:
            print("⚠️  prompts.py が見つかりません。")
        sys.exit(0)
    
    if len(sys.argv) < 2:
        print("使い方: python analyze_video_gemini.py <動画ファイル>")
        print("        python analyze_video_gemini.py --list-models   # 利用可能なモデルを表示")
        print("        python analyze_video_gemini.py --list-prompts  # 利用可能なプロンプトを表示")
        print(f"\n利用可能な動画 ({VIDEOS_DIR}):")
        if os.path.exists(VIDEOS_DIR):
            mp4_files = [f for f in os.listdir(VIDEOS_DIR) if f.lower().endswith('.mp4')]
            if mp4_files:
                for f in mp4_files:
                    print(f"  - {f}")
            else:
                print(f"  （{VIDEOS_DIR} に .mp4 ファイルを配置してください）")
        else:
            print(f"  （{VIDEOS_DIR} ディレクトリが見つかりません）")
        sys.exit(1)
    
    video_file = sys.argv[1]
    
    # videosディレクトリ内のファイル名のみの場合はパスを追加
    if not os.path.exists(video_file) and os.path.exists(os.path.join(VIDEOS_DIR, video_file)):
        video_file = os.path.join(VIDEOS_DIR, video_file)
    
    analyze_video(video_file)

