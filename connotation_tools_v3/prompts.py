# -*- coding: utf-8 -*-
"""
プロンプト管理ファイル
複数のプロンプトパターンを管理し、動画解析に使用します。

使い方:
    from prompts import get_prompt, list_prompts
    
    # 利用可能なプロンプト一覧を表示
    print(list_prompts())
    
    # プロンプトを取得
    prompt_text = get_prompt("default", num_frames=15)
"""

# ===== プロンプトテンプレート =====
# {num_frames} は実行時に置き換えられます

PROMPTS = {
    "default": """
以下の{num_frames}枚の動画フレームを順番に解析してください。
これは4DX映画館のような体感型エンターテインメント用です。
各フレームについて、日本語で詳細なキャプション（2-3文）を返してください。

【4DX体験のための超重要ポイント - 振動を積極的に！】

★ 振動の基本方針 ★
- 乗り物に乗っている間は常に「乗っている」と記載
- 動きや戦闘があるシーンは基本的に振動を出す
- 完全に静止しているシーン以外は何かしら動いている

1. 【乗り物搭乗の判定】最重要！
   ✓ 戦闘機/車/船/ロボット/馬に「乗っている」と必ず記載
   ✓ コックピット内/運転席/操縦席 → 「乗っている」
   ✓ 降りている場合のみ「降りている」と記載
   例: 「戦闘機に乗っており、飛行中」
   例: 「車内で運転しており、走行中」

2. 【爆発・炎・火花】見逃し厳禁！
   ✓ 炎が見える → 「炎が見える」と明記
   ✓ 火花が散る → 「火花が散っている」と明記
   ✓ 爆発の瞬間 → 「爆発している」と明記
   ✓ 爆風・煙・閃光も詳しく記載
   例: 「背景で爆発が起き、炎と煙が上がっている」

3. 【衝突・攻撃の瞬間】
   ✓ 物体がぶつかる瞬間 → 「衝突」と明記
   ✓ 武器が当たる瞬間 → 「打撃」と明記
   例: 「ロボットの拳が敵に当たる瞬間」

4. 【激しい動き・戦闘】
   ✓ 戦闘中/バトル中 → 「戦闘中」と明記
   ✓ 暴れている/激しく動く → 「激しく動いている」
   ✓ 急旋回/急加速 → 明記

5. 【視覚効果】
   ✓ 雷 → 「雷」、稲妻 → 「稲妻」
   ✓ 爆発の光 → 「爆発の閃光」
   ✓ 水しぶき/唾 → 「水しぶき」

6. 【静止の判定】
   ✓ 本当に何も動いていない場合のみ「静止」
   ✓ 少しでも動きがあれば「動いている」

出力は必ずJSONオブジェクトで、キー 'captions' に配列形式でキャプションのリストを含むこと。
例: {{"captions": ["キャプション1", "キャプション2", ...]}}
""",

    "detailed": """
以下の{num_frames}枚の動画フレームを順番に解析してください。
これは4DX映画館のような体感型エンターテインメント用です。
各フレームについて、日本語で非常に詳細なキャプション（3-5文）を返してください。

【超詳細解析モード】

★ 詳細に記載すべき要素 ★
1. 人物・キャラクターの状態（表情、動作、位置）
2. 背景・環境の描写（天候、時間帯、場所）
3. 動き・動作の詳細（速度、方向、強度）
4. 視覚効果（光、色、影、煙、火花）
5. 音が聞こえそうな要素（爆発、衝突、叫び）
6. 感情・雰囲気（緊張、興奮、恐怖、安らぎ）

【4DX効果の判定ポイント】
- 乗り物: 必ず「乗っている」「運転中」「飛行中」などと記載
- 爆発: 「爆発」「炸裂」「閃光」「炎」「煙」を明記
- 衝突: 「衝突」「激突」「打撃」「攻撃」を明記
- 動き: 「移動中」「走行中」「戦闘中」を明記
- 静止: 本当に静止している場合のみ「静止」と記載

出力は必ずJSONオブジェクトで、キー 'captions' に配列形式でキャプションのリストを含むこと。
例: {{"captions": ["詳細なキャプション1", "詳細なキャプション2", ...]}}
""",

    "simple": """
以下の{num_frames}枚の動画フレームを順番に解析してください。
各フレームについて、日本語で簡潔なキャプション（1-2文）を返してください。

【簡潔モード】
- シーンの主要な要素のみを記載
- 動きや効果を簡潔に表現
- 4DX効果に関連するキーワードを含める

出力は必ずJSONオブジェクトで、キー 'captions' に配列形式でキャプションのリストを含むこと。
例: {{"captions": ["キャプション1", "キャプション2", ...]}}
""",

    "action_focused": """
以下の{num_frames}枚の動画フレームを順番に解析してください。
これは4DX映画館のような体感型エンターテインメント用です。
アクションシーンに特化した解析を行ってください。

【アクション特化モード】

★ 重点的に記載すべき要素 ★
1. 戦闘・格闘の詳細（攻撃、防御、回避）
2. 爆発・衝突の瞬間（タイミング、強度、範囲）
3. 高速移動（飛行、走行、ジャンプ）
4. 武器・道具の使用（発射、命中、効果）
5. 環境の変化（破壊、変形、崩壊）

【4DX効果の判定（アクション重視）】
- 戦闘中は必ず「戦闘中」「バトル中」と記載
- 爆発は「爆発」「炸裂」と明記
- 衝突は「衝突」「激突」と明記
- 高速移動は「高速で移動」「疾走」と明記
- 武器使用は「発射」「命中」と明記

出力は必ずJSONオブジェクトで、キー 'captions' に配列形式でキャプションのリストを含むこと。
例: {{"captions": ["アクションキャプション1", "アクションキャプション2", ...]}}
""",

    "emotion_focused": """
以下の{num_frames}枚の動画フレームを順番に解析してください。
これは4DX映画館のような体感型エンターテインメント用です。
感情・雰囲気に重点を置いた解析を行ってください。

【感情・雰囲気特化モード】

★ 重点的に記載すべき要素 ★
1. キャラクターの感情（恐怖、興奮、緊張、安らぎ）
2. シーンの雰囲気（暗い、明るい、不穏、平和）
3. 緊張感の高まり（ドキドキ、不安、期待）
4. 感情の変化（驚き、安堵、絶望、希望）
5. 環境が与える印象（圧迫感、開放感、神秘性）

【4DX効果の判定（感情重視）】
- 緊張シーンは「緊張」「ドキドキ」「不安」と記載
- 恐怖シーンは「恐怖」「恐ろしい」と記載
- 興奮シーンは「興奮」「高揚」と記載
- 静かなシーンは「静か」「穏やか」と記載（振動なし）

出力は必ずJSONオブジェクトで、キー 'captions' に配列形式でキャプションのリストを含むこと。
例: {{"captions": ["感情キャプション1", "感情キャプション2", ...]}}
""",

    "custom_1": """
以下の{num_frames}枚の動画フレームを順番に解析してください。
カスタムプロンプト1です。ここを編集して独自のプロンプトを作成できます。

【カスタムプロンプト1】
- ここに独自の指示を記載
- プロンプトを自由に編集可能

出力は必ずJSONオブジェクトで、キー 'captions' に配列形式でキャプションのリストを含むこと。
例: {{"captions": ["キャプション1", "キャプション2", ...]}}
""",

    "custom_2": """
以下の{num_frames}枚の動画フレームを順番に解析してください。
カスタムプロンプト2です。ここを編集して独自のプロンプトを作成できます。

【カスタムプロンプト2】
- ここに独自の指示を記載
- プロンプトを自由に編集可能

出力は必ずJSONオブジェクトで、キー 'captions' に配列形式でキャプションのリストを含むこと。
例: {{"captions": ["キャプション1", "キャプション2", ...]}}
""",

    "4dx_home_v3": """
以下の{num_frames}枚の動画フレームを順番に解析してください。
これは4DX@HOME 3世代目デバイス向けの解析です。0.25秒間隔で切り取られた連続フレームです。

【重要】前後フレームとの差分を必ず確認し、変化（発生/消失/強弱）を明確に捉えてください。

各フレームについて、以下の2つを返してください：
1. 表現力の豊かな日本語キャプション（2-4文）
2. 4DX効果の判定（JSON形式）

【キャプションのスタイル】
- 事実に基づきつつ、情景・動き・空気感・感情のニュアンスまで描写する
- 動作や変化の「瞬間」を明確に書く（例: 直前/直後/一瞬/炸裂/着地）
- カメラの動きや距離感が分かる場合は書く
- ただし冗長にならないよう、1フレームにつき最大4文

【4DX効果の種類とモード】

★ 振動（vibration）★
- "up_strong", "up_mid_strong", "up_mid_weak", "up_weak"
- "down_strong", "down_mid_strong", "down_mid_weak", "down_weak"
- "up_down_strong", "up_down_mid_strong", "up_down_mid_weak", "up_down_weak"
- "heartbeat"

★ 光（flash）★
- "steady": 点灯（継続的な光）
- "blink": 点滅（チカチカ、雷/閃光/銃火）
- "breathe": 呼吸（ゆっくり明滅、ネオン/魔法/鼓動感）

★ 色（color）★
- "pink", "red", "orange", "yellow", "yellow_green", "green"
- "dark_green", "cyan", "blue", "purple", "white"

★ LED強さ（led_strength）★
- "off": 消灯
- "weak": 弱 (20%)
- "strong": 強 (100%)

★ LED変化（led_transition）★
- "instant": 一瞬 (パッと変わる)
- "fade": フェード (フワッと変わる)

★ 風（wind）★
- "burst": 風（爆風/疾走/息/風圧）

★ 水（water）★
- "burst": 水しぶき（着水/しぶき/雨粒）
- "stream": 水（連続噴射/雨の継続/水が流れ続ける）

★ ミスト（mist）★
- "burst": ミスト（霧/蒸気/煙/白い噴霧）
- "stream": ミスト（連続噴射/霧が継続する）

【効果判定の方針】
- 強い衝撃（爆発/激突/着地）は strong 系の振動
- 移動・走行・飛行・乗り物は弱〜中弱の振動を継続
- 緊張/恐怖/接近の演出は heartbeat を活用
- 光は「特別な光」が必要なときのみ使用（銃火・雷・爆発・閃光）
- 風は速度感/爆風/息の圧力があるときに短く
- 水は「着水・跳ね・しぶきの瞬間」に限定
- ミストは霧/蒸気/煙/砂埃がはっきり見える瞬間に使用
- ミスト＋色/光の組み合わせで演出強化が可能（例: オレンジの光＋ミストで爆発の余韻を表現）
- 効果の使い過ぎは避け、静寂と動のコントラストを作る

【出力形式】
必ずJSONオブジェクトで、以下の形式で返してください：

{{
  "frames": [
    {{
      "caption": "フレーム1のキャプション",
      "effects": {{
        "flash": "blink" または null,
        "color": "blue" または null,
        "vibration": "down_mid_weak" または null,
        "water": "burst" または "stream" または null,
        "wind": "burst" または null,
        "mist": "burst" または "stream" または null,
        "led_strength": "off" または "weak" または "strong" または null,
        "led_transition": "instant" または "fade" または null
      }}
    }},
    {{
      "caption": "フレーム2のキャプション",
      "effects": {{...}}
    }}
  ]
}}

効果がない場合は null を返してください。未定義のモードは使わないでください。
""",
}

# デフォルトのプロンプト名
DEFAULT_PROMPT = "4dx_home_v3"

# ===== 関数 =====

def get_prompt(prompt_name: str = None, num_frames: int = 15) -> str:
    """
    プロンプトを取得する
    
    Args:
        prompt_name: プロンプト名（Noneの場合はデフォルト）
        num_frames: フレーム数（{num_frames}を置き換える）
    
    Returns:
        プロンプトテキスト
    """
    if prompt_name is None:
        prompt_name = DEFAULT_PROMPT
    
    if prompt_name not in PROMPTS:
        print(f"⚠️  警告: プロンプト '{prompt_name}' が見つかりません。デフォルトを使用します。")
        prompt_name = DEFAULT_PROMPT
    
    prompt = PROMPTS[prompt_name]
    return prompt.format(num_frames=num_frames)

def list_prompts() -> list:
    """
    利用可能なプロンプト一覧を取得
    
    Returns:
        プロンプト名のリスト
    """
    return list(PROMPTS.keys())

def add_prompt(name: str, prompt_text: str):
    """
    新しいプロンプトを追加
    
    Args:
        name: プロンプト名
        prompt_text: プロンプトテキスト（{num_frames}を含むことができます）
    """
    PROMPTS[name] = prompt_text
    print(f"✅ プロンプト '{name}' を追加しました。")

def remove_prompt(name: str):
    """
    プロンプトを削除
    
    Args:
        name: プロンプト名
    """
    if name == DEFAULT_PROMPT:
        print(f"⚠️  エラー: デフォルトプロンプト '{name}' は削除できません。")
        return
    
    if name in PROMPTS:
        del PROMPTS[name]
        print(f"✅ プロンプト '{name}' を削除しました。")
    else:
        print(f"⚠️  エラー: プロンプト '{name}' が見つかりません。")

def show_prompt(prompt_name: str = None):
    """
    プロンプトの内容を表示
    
    Args:
        prompt_name: プロンプト名（Noneの場合はデフォルト）
    """
    if prompt_name is None:
        prompt_name = DEFAULT_PROMPT
    
    if prompt_name not in PROMPTS:
        print(f"⚠️  エラー: プロンプト '{prompt_name}' が見つかりません。")
        return
    
    print(f"\n📝 プロンプト: {prompt_name}")
    print("=" * 60)
    print(PROMPTS[prompt_name].format(num_frames=15))
    print("=" * 60)

if __name__ == "__main__":
    # コマンドラインから実行した場合
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list":
            print("📋 利用可能なプロンプト:")
            for name in list_prompts():
                marker = " (デフォルト)" if name == DEFAULT_PROMPT else ""
                print(f"   - {name}{marker}")
        
        elif command == "show":
            prompt_name = sys.argv[2] if len(sys.argv) > 2 else None
            show_prompt(prompt_name)
        
        elif command == "add":
            if len(sys.argv) < 4:
                print("使い方: python prompts.py add <プロンプト名> <プロンプトテキスト>")
            else:
                name = sys.argv[2]
                text = sys.argv[3]
                add_prompt(name, text)
        
        else:
            print("使い方:")
            print("  python prompts.py list              # プロンプト一覧")
            print("  python prompts.py show [名前]       # プロンプト表示")
            print("  python prompts.py add <名> <テキスト>  # プロンプト追加")
    else:
        print("📋 利用可能なプロンプト:")
        for name in list_prompts():
            marker = " (デフォルト)" if name == DEFAULT_PROMPT else ""
            print(f"   - {name}{marker}")

