# -*- coding: utf-8 -*-
"""
【解析モード】ローカル動画シーン解析（MP4専用）
- MP4動画ファイルを読み込み
- 0.5秒間隔でフレームをスクリーンショット
- GPT-4o-miniで各フレームをキャプション化
- 効果（光/風/水/色/衝撃）をJSON形式で出力

使い方:
    python analyze_video.py video.mp4

出力: results/{video_name}_timeline.json
"""

import os, sys, cv2, json, requests, warnings, contextlib
from typing import List, Tuple, Dict
from pathlib import Path
from datetime import datetime

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
VIDEOS_DIR = "videos"            # ユーザーが動画を配置するディレクトリ
RESULTS_DIR = "results"          # JSON出力先
SAMPLE_INTERVAL = 0.5            # 0.5秒ごとにサンプリング
BATCH_SIZE = 15                  # 一度に処理するフレーム数（10-20推奨）
MODEL_NAME = "gpt-4o-mini"
TARGET_WIDTH = 640               # API負荷軽減の縮小幅

# 直接書きたい場合はここにキー文字列を入れる（例: "sk-..."）。空文字なら無効。
HARD_CODED_OPENAI_API_KEY = ""
# 優先順: ハードコード > 環境変数
OPENAI_API_KEY = HARD_CODED_OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
API_URL = "https://api.openai.com/v1/chat/completions"

# ===== 効果ドメイン（4DX向け）=====
EFFECT_DOMAIN = {
    "flash": ["strobe", "burst", "steady"],      # 光: 交互ちかちか/一瞬光る/長めに光る
    "wind": ["burst", "long"],                    # 風: 一瞬の風/長い風
    "water": ["burst"],                           # 水: 一度発射のみ
    "color": ["red", "green", "blue"],            # 色: 赤/緑/青
    "vibration": ["heartbeat", "strong", "long"], # 衝撃: ドキドキ/強い衝撃/長い衝撃
}

# ===== 効果の最小継続時間（秒）=====
MIN_DURATION = {
    "vibration:heartbeat": 2.5,  # ドキドキは2.5秒以上
    "vibration:strong": 1.0,     # 強い衝撃は1秒以上
    "vibration:long": 1.0,       # 継続振動は1秒以上
    "wind:burst": 1.0,           # 一瞬の風は1秒以上
    "wind:long": 1.5,            # 長い風は1.5秒以上
    "water:burst": 1.0,          # 水は1秒以上
    "flash:burst": 0.5,          # 閃光は0.5秒（瞬間でOK）
    "flash:strobe": 1.5,         # ストロボは1.5秒以上
    "flash:steady": 1.5,         # 照明は1.5秒以上
    "color:red": 1.0,            # 色は1秒以上
    "color:green": 1.0,
    "color:blue": 1.0,
}

# ===== ルール: キャプション→効果（4DX向け - 精密版）=====
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
    import base64
    h, w = frame_bgr.shape[:2]
    if w > target_w:
        scale = target_w / float(w)
        frame_bgr = cv2.resize(frame_bgr, (target_w, int(h*scale)))
    ok, buf = cv2.imencode(".png", frame_bgr)
    if not ok:
        raise RuntimeError("PNGエンコード失敗")
    return base64.b64encode(buf.tobytes()).decode("utf-8")

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

def caption_batch_vlm(frames_data: List[Dict]) -> List[str]:
    """バッチ処理: 複数フレームを一度に解析"""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY 未設定。環境変数に設定するか、コード内のHARD_CODED_OPENAI_API_KEYに設定してください。")
    
    content = [
        {"type": "text", "text": (
            f"以下の{len(frames_data)}枚の動画フレームを順番に解析してください。\n"
            "これは4DX映画館のような体感型エンターテインメント用です。\n"
            "各フレームについて、日本語で詳細なキャプション（2-3文）を返してください。\n"
            "\n"
            "【4DX体験のための超重要ポイント - 振動を積極的に！】\n"
            "\n"
            "★ 振動の基本方針 ★\n"
            "- 乗り物に乗っている間は常に「乗っている」と記載\n"
            "- 動きや戦闘があるシーンは基本的に振動を出す\n"
            "- 完全に静止しているシーン以外は何かしら動いている\n"
            "\n"
            "1. 【乗り物搭乗の判定】最重要！\n"
            "   ✓ 戦闘機/車/船/ロボット/馬に「乗っている」と必ず記載\n"
            "   ✓ コックピット内/運転席/操縦席 → 「乗っている」\n"
            "   ✓ 降りている場合のみ「降りている」と記載\n"
            "   例: 「戦闘機に乗っており、飛行中」\n"
            "   例: 「車内で運転しており、走行中」\n"
            "\n"
            "2. 【爆発・炎・火花】見逃し厳禁！\n"
            "   ✓ 炎が見える → 「炎が見える」と明記\n"
            "   ✓ 火花が散る → 「火花が散っている」と明記\n"
            "   ✓ 爆発の瞬間 → 「爆発している」と明記\n"
            "   ✓ 爆風・煙・閃光も詳しく記載\n"
            "   例: 「背景で爆発が起き、炎と煙が上がっている」\n"
            "\n"
            "3. 【衝突・攻撃の瞬間】\n"
            "   ✓ 物体がぶつかる瞬間 → 「衝突」と明記\n"
            "   ✓ 武器が当たる瞬間 → 「打撃」と明記\n"
            "   例: 「ロボットの拳が敵に当たる瞬間」\n"
            "\n"
            "4. 【激しい動き・戦闘】\n"
            "   ✓ 戦闘中/バトル中 → 「戦闘中」と明記\n"
            "   ✓ 暴れている/激しく動く → 「激しく動いている」\n"
            "   ✓ 急旋回/急加速 → 明記\n"
            "\n"
            "5. 【視覚効果】\n"
            "   ✓ 雷 → 「雷」、稲妻 → 「稲妻」\n"
            "   ✓ 爆発の光 → 「爆発の閃光」\n"
            "   ✓ 水しぶき/唾 → 「水しぶき」\n"
            "\n"
            "6. 【静止の判定】\n"
            "   ✓ 本当に何も動いていない場合のみ「静止」\n"
            "   ✓ 少しでも動きがあれば「動いている」\n"
            "\n"
            "出力は必ずJSONオブジェクトで、キー 'captions' に配列形式でキャプションのリストを含むこと。\n"
            "例: {\"captions\": [\"キャプション1\", \"キャプション2\", ...]}"
        )}
    ]
    
    for frame_data in frames_data:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{frame_data['b64_image']}"}
        })
    
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.2,
        "max_tokens": 512 * len(frames_data),
        "response_format": {"type": "json_object"}
    }
    
    r = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=120)
    if r.status_code != 200:
        print(f"API Error {r.status_code}: {r.text}")
        raise RuntimeError(f"API呼び出し失敗: {r.status_code}")
    
    txt = r.json()["choices"][0]["message"]["content"]
    try:
        obj = json.loads(txt)
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
        
        return captions
    except Exception as e:
        raise RuntimeError(f"JSON解析失敗: {e} / raw={txt[:300]}")

def get_effect_display_name(effect: str, mode: str) -> str:
    """効果の日本語表示名を取得"""
    effect_names = {
        "flash:strobe": "⚡雷の光",
        "flash:burst": "💥閃光",
        "flash:steady": "☀️照明",
        "wind:burst": "💨一瞬の風",
        "wind:long": "🌬️長い風",
        "water:burst": "💦水しぶき",
        "color:red": "🔴赤色",
        "color:green": "🟢緑色",
        "color:blue": "🔵青色",
        "vibration:heartbeat": "💓ドキドキ",
        "vibration:strong": "💥強い衝撃",
        "vibration:long": "📳弱い振動",
    }
    return effect_names.get(f"{effect}:{mode}", f"{effect}:{mode}")

def decide_effects(caption: str) -> List[Tuple[str,str]]:
    """キャプションから効果集合を決定（4DX向け - 精密版）"""
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
                effect_start_times: Dict[Tuple[str,str], float]) -> List[Dict]:
    """
    前回との差分で start/stop を生成
    最小継続時間を考慮して、短すぎる効果は継続させる
    水は一度きりの"shot"イベントとして扱う
    """
    events = []
    ps, cs = set(prev_eff), set(curr_eff)
    
    # 水の効果を特別処理（一度きりの発射）
    water_effects = {eff for eff in (cs - ps) if eff[0] == "water"}
    for eff in water_effects:
        # 水は "shot" アクションで一度だけ発火
        events.append({"t": round(t,3), "action":"shot", "effect":eff[0], "mode":eff[1]})
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
        
        # 振動は複数のモードを同時に持てる（例: strong + long）
        # それ以外は上書き
        can_coexist = (eff[0] == "vibration")
        
        # 上書きされたかどうか
        is_overwritten = len(same_type_different_mode) > 0 and not can_coexist
        
        # 最小継続時間に達していない かつ 上書きされていない場合は継続
        if duration < min_duration and not is_overwritten:
            # 継続させる
            cs.add(eff)
        else:
            # 停止
            events.append({"t": round(t,3), "action":"stop", "effect":eff[0], "mode":eff[1]})
            # 開始時刻を削除
            if eff in effect_start_times:
                del effect_start_times[eff]
    
    # 新規開始の効果（水以外）
    for eff in (cs - ps):
        if eff[0] == "water":
            continue  # 水は既に処理済み
        events.append({"t": round(t,3), "action":"start","effect":eff[0], "mode":eff[1]})
        effect_start_times[eff] = t  # 開始時刻を記録
    
    return events, list(cs)

def analyze_video(video_path: str):
    """動画を解析してタイムラインJSONを生成"""
    print("\n" + "=" * 60)
    print("📸【解析モード】ローカル動画シーン解析")
    print("=" * 60)
    
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
    
    # サンプリングタイムスタンプを生成
    timestamps = []
    t = 0.0
    while t <= duration:
        timestamps.append(t)
        t += SAMPLE_INTERVAL
    
    print(f"  📊 サンプリング点数: {len(timestamps)}枚")
    print(f"  ⏱️  サンプリング間隔: {SAMPLE_INTERVAL}秒")
    print(f"  📦 バッチサイズ: {BATCH_SIZE}フレーム/回")
    print(f"  🤖 予想API呼び出し: {(len(timestamps) + BATCH_SIZE - 1) // BATCH_SIZE}回")
    estimated_time = (len(timestamps) + BATCH_SIZE - 1) // BATCH_SIZE * 20
    print(f"  ⏳ 予想処理時間: 約{estimated_time//60}分{estimated_time%60}秒")
    print(f"\n🎬 AI解析を開始します...\n")
    
    # フレームをバッチ処理
    events: List[Dict] = []
    prev_effects: List[Tuple[str,str]] = []
    effect_start_times: Dict[Tuple[str,str], float] = {}  # 各効果の開始時刻を記録
    
    for batch_start in range(0, len(timestamps), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(timestamps))
        batch_timestamps = timestamps[batch_start:batch_end]
        
        batch_num = batch_start//BATCH_SIZE + 1
        total_batches = (len(timestamps) + BATCH_SIZE - 1)//BATCH_SIZE
        print(f"  📦 バッチ {batch_num}/{total_batches}: フレーム {batch_start+1}~{batch_end}枚目")
        
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
        
        if not frames_data:
            continue
        
        # バッチでキャプション取得
        print(f"    🤖 AI解析中... ({len(frames_data)}枚)", end=" ")
        try:
            captions = caption_batch_vlm(frames_data)
            print(f"✓")
        except Exception as e:
            print(f"\n    ❌ エラー発生: {e}")
            print(f"    ⏳ 60秒待機してからリトライします...")
            import time
            time.sleep(60)
            captions = caption_batch_vlm(frames_data)
            print(f"    ✅ リトライ成功！")
        
        # 各フレームのキャプションを処理
        for frame_data, cap_text in zip(frames_data, captions):
            t = frame_data["timestamp"]
            
            print(f"    💬 t={t:.1f}s: {cap_text[:60]}{'...' if len(cap_text) > 60 else ''}")
            
            events.append({"t": round(t,3), "action":"caption", "text": cap_text})
            
            # 効果判定
            curr_effects = decide_effects(cap_text)
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
        
        print()  # 空行
        
        # レート制限回避のため、次のバッチまで待機
        if batch_end < len(timestamps):
            import time
            print(f"    ⏳ API制限回避のため15秒待機中...\n")
            time.sleep(15)
    
    cap.release()
    
    if not events:
        raise RuntimeError("有効フレームが取得できなかった")
    
    # 終了時にONのものは必ずstopを出す（最小継続時間を適用）
    if prev_effects:
        end_t = timestamps[-1] if timestamps else 0.0
        for eff in prev_effects:
            # 最小継続時間を確認
            effect_key = f"{eff[0]}:{eff[1]}"
            start_time = effect_start_times.get(eff, 0.0)
            duration = end_t - start_time
            min_duration = MIN_DURATION.get(effect_key, 0.5)
            
            # 最小継続時間に達していない場合は、延長してから停止
            stop_time = max(end_t, start_time + min_duration)
            events.append({"t": round(stop_time,3), "action":"stop", "effect": eff[0], "mode": eff[1]})
    
    # 結果ディレクトリ作成
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    # 出力ファイル名（動画名をベースに）
    video_name = Path(video_path).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_json = os.path.join(RESULTS_DIR, f"{video_name}_timeline_{timestamp}.json")
    
    # JSON出力
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump({"events": events}, f, ensure_ascii=False, indent=2)
    
    print(f"\n" + "=" * 60)
    print(f"✅ 解析完了しました！")
    print(f"  📄 出力ファイル: {output_json}")
    print(f"  📊 総イベント数: {len(events)}個")
    caption_count = sum(1 for e in events if e.get('action') == 'caption')
    effect_count = len(events) - caption_count
    print(f"  💬 キャプション: {caption_count}個")
    print(f"  ⚡ 効果イベント: {effect_count}個")
    print("=" * 60)
    
    return output_json

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("使い方: python analyze_video.py <動画ファイル>")
        print(f"\n利用可能な動画 ({VIDEOS_DIR}/):")
        if os.path.exists(VIDEOS_DIR):
            mp4_files = [f for f in os.listdir(VIDEOS_DIR) if f.lower().endswith('.mp4')]
            if mp4_files:
                for f in mp4_files:
                    print(f"  - {f}")
            else:
                print(f"  （{VIDEOS_DIR}/ に .mp4 ファイルを配置してください）")
        sys.exit(1)
    
    video_file = sys.argv[1]
    
    # videosディレクトリ内のファイル名のみの場合はパスを追加
    if not os.path.exists(video_file) and os.path.exists(os.path.join(VIDEOS_DIR, video_file)):
        video_file = os.path.join(VIDEOS_DIR, video_file)
    
    analyze_video(video_file)

