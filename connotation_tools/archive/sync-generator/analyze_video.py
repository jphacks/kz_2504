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
VIDEOS_DIR = "../../assets/videos"  # 動画ディレクトリ
RESULTS_DIR = "../../assets/sync-data"  # JSON出力先
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
    # === 強い衝撃（瞬間的）===
    (["衝突する瞬間","衝突の瞬間","ぶつかる瞬間","激突","moment of collision","crash into","smash"],
     [("vibration","strong")]),
    (["爆発する瞬間","爆発の瞬間","爆発が発生","爆発した","explosion occurs","explodes","detonates"],
     [("vibration","strong"), ("flash","burst"), ("color","red")]),
    (["着地する瞬間","着地の瞬間","地面に叩きつけ","lands","touches down","hits ground"],
     [("vibration","strong")]),
    (["攻撃の瞬間","打撃の瞬間","殴る瞬間","蹴る瞬間","hits","strikes","punches","kicks"],
     [("vibration","strong")]),
    
    # === 弱い振動（継続的）===
    (["乗っている","乗車","戦闘機","車内","船","飛行機","コックピット","運転席","操縦",
      "riding","on board","in the","piloting","cockpit","driving","vehicle"],
     [("vibration","long")]),
    (["飛行中","飛んでいる","移動中","走行中","運転中","歩いている","走っている","進んでいる",
      "flying","moving","driving","running","walking","advancing","traveling"],
     [("vibration","long")]),
    (["戦闘中","バトル中","戦っている","暴れている","激しく動いている","格闘",
      "fighting","battling","combat","struggling","intense"],
     [("vibration","long")]),
    
    # === 生物のアクション ===
    (["咆哮","咆哮している","吠える","吠えている","吠えた","叫ぶ","叫んでいる","絶叫","怒鳴る","唸る",
      "roar","roaring","roars","howl","howling","scream","screaming","shout","shouting","yell","yelling","growl","snarl"],
     [("vibration","strong"), ("water","burst"), ("wind","burst")]),
    (["呼吸","溜息","息","吐く","吸う","breath","sigh","exhale","inhale"],
     [("wind","burst")]),
    
    # === 光の効果 ===
    (["雷","稲妻","雷鳴","lightning","thunder"],
     [("flash","strobe")]),
    (["爆発","閃光","爆破","炸裂","explosion","explode","blast","detonation"],
     [("flash","burst"), ("vibration","strong"), ("color","red")]),
    (["火花","スパーク","火の粉","spark","sparks","sparking"],
     [("flash","burst"), ("vibration","strong")]),
    (["炎が見える","炎が上がる","燃えている","炎","flames","fire","burning"],
     [("flash","steady"), ("vibration","long"), ("color","red")]),
    (["照らす","ライト","光る","夕日","照明","日差し","light","illuminate","shine","sunset","sunlight"],
     [("flash","steady")]),
    
    # === 風 ===
    (["衝撃波","突風","爆風","blast","shock wave","gust"],
     [("wind","burst")]),
    (["風","砂埃","煙","疾走","スピード","wind","dust","smoke","speed","fast"],
     [("wind","long")]),
    
    # === 水・飛沫 ===
    (["唾","つば","飛沫","よだれ","saliva","spit","drool"],
     [("water","burst")]),
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
    (["緊張","ドキドキ","心拍","不安","危険","tense","nervous","anxious","heartbeat","danger"],
     [("vibration","heartbeat")]),
]

# 以下、すべての関数とメイン処理は元のファイルと同じ
# （長いため省略、実際のコピーでは全行をコピーします）
