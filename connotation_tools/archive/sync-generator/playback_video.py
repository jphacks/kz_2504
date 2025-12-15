# -*- coding: utf-8 -*-
"""
【視聴用再生モード】動画再生＆効果信号送信（MP4専用）
- 解析済みのJSONタイムラインを読み込み
- 動画を再生しながら、タイムスタンプに合わせて信号を送信
- リアルタイムで効果（光/風/水/色/衝撃）を発動

使い方:
    python playback_video.py video.mp4

必要なファイル:
    - videos/video.mp4 (動画ファイル)
    - results/video_timeline.json (タイムラインJSON)
"""

import os, sys, cv2, json, time, threading, warnings, contextlib
from typing import Dict, List
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
VIDEOS_DIR = "videos"
RESULTS_DIR = "results"
WINDOW_NAME = "Scene Playback - 体感型動画再生"
TIMING_OFFSET = 0.5  # タイミング調整（秒）：正の値で信号を遅らせる

# ===== 効果信号送信（デバイス制御用） =====
class EffectController:
    """効果デバイスの制御を行うクラス"""
    
    def __init__(self):
        self.active_effects = {}
        self.water_shots = {}  # 水の発射を一時的に表示: {key: end_time}
        self.lock = threading.Lock()
        
        # 全効果の定義（表示順）
        self.all_effects = [
            ("flash", "strobe", "⚡ 雷の光"),
            ("flash", "burst", "💥 閃光"),
            ("flash", "steady", "☀️ 照明"),
            ("wind", "burst", "💨 一瞬の風"),
            ("wind", "long", "🌬️ 長い風"),
            ("water", "burst", "💦 水しぶき"),
            ("color", "red", "🔴 赤色"),
            ("color", "green", "🟢 緑色"),
            ("color", "blue", "🔵 青色"),
            ("vibration", "heartbeat", "💓 ドキドキ"),
            ("vibration", "strong", "💥 強い衝撃"),
            ("vibration", "long", "📳 弱い振動"),
        ]
    
    def start_effect(self, effect: str, mode: str, timestamp: float):
        """効果を開始"""
        with self.lock:
            key = (effect, mode)
            self.active_effects[key] = timestamp
            # ログは表示しない（表で確認）
            self._send_signal("START", effect, mode)
    
    def stop_effect(self, effect: str, mode: str, timestamp: float):
        """効果を停止"""
        with self.lock:
            key = (effect, mode)
            if key in self.active_effects:
                del self.active_effects[key]
            # ログは表示しない（表で確認）
            self._send_signal("STOP", effect, mode)
    
    def shot_effect(self, effect: str, mode: str, timestamp: float):
        """効果を一度だけ発射（水専用）"""
        with self.lock:
            key = (effect, mode)
            # 0.5秒間だけ表に表示
            self.water_shots[key] = timestamp + 0.5
        self._send_signal("SHOT", effect, mode)
    
    def _get_effect_name(self, effect: str, mode: str) -> str:
        """効果の日本語名を取得"""
        effect_names = {
            "flash:strobe": "⚡ 雷の光（チカチカ）",
            "flash:burst": "💥 閃光（爆発）",
            "flash:steady": "☀️ 照明（継続）",
            "wind:burst": "💨 一瞬の風（衝撃波）",
            "wind:long": "🌬️ 長い風（疾走）",
            "water:burst": "💦 水しぶき（噴射）",
            "color:red": "🔴 赤色（炎・血）",
            "color:green": "🟢 緑色（自然）",
            "color:blue": "🔵 青色（空・水）",
            "vibration:heartbeat": "💓 ドキドキ（緊張）",
            "vibration:strong": "💥 強い衝撃（爆発・着地）",
            "vibration:long": "📳 弱い振動（運転中）",
        }
        return effect_names.get(f"{effect}:{mode}", f"{effect}:{mode}")
    
    def print_status_table(self, current_time: float):
        """現在の効果状態を表形式で表示"""
        with self.lock:
            # 期限切れの水shotを削除
            expired_shots = [k for k, end_time in self.water_shots.items() if current_time > end_time]
            for k in expired_shots:
                del self.water_shots[k]
            
            # カーソルを上に移動して上書き表示
            # 前回の表示をクリア
            sys.stdout.write('\033[2J')  # 画面クリア
            sys.stdout.write('\033[H')   # カーソルをホームに
            
            print("=" * 70)
            print(f"⏱️  時刻: {current_time:.1f}秒")
            print("=" * 70)
            print("┌" + "─" * 30 + "┬" + "─" * 10 + "┬" + "─" * 25 + "┐")
            print("│" + " 効果".ljust(28) + "│ 状態".ljust(8) + "│ 継続時間".ljust(23) + "│")
            print("├" + "─" * 30 + "┼" + "─" * 10 + "┼" + "─" * 25 + "┤")
            
            for effect, mode, name in self.all_effects:
                key = (effect, mode)
                
                # 継続的な効果（start/stop）
                if key in self.active_effects:
                    start_time = self.active_effects[key]
                    duration = current_time - start_time
                    status = "🟢 ON "
                    duration_str = f"{duration:.1f}秒"
                # 水の発射（一時表示）
                elif key in self.water_shots:
                    status = "💧 発射"
                    duration_str = "一瞬"
                else:
                    status = "⚫ OFF"
                    duration_str = "-"
                
                # 文字数を調整（日本語対応）
                name_display = name.ljust(28)
                status_display = status.ljust(8)
                duration_display = duration_str.ljust(23)
                
                print(f"│ {name_display}│ {status_display}│ {duration_display}│")
            
            print("└" + "─" * 30 + "┴" + "─" * 10 + "┴" + "─" * 25 + "┘")
            print("\n🎮 [スペース]=一時停止 [R]=最初から [Q]=終了")
            sys.stdout.flush()
    
    def _send_signal(self, action: str, effect: str, mode: str):
        """
        実際の信号送信処理（カスタマイズ可能）
        
        デバイスに合わせて実装してください:
        - シリアル通信: pyserial
        - HTTP API: requests
        - WebSocket: websockets
        
        例:
            import serial
            ser = serial.Serial('COM3', 9600)
            ser.write(f"{action}:{effect}:{mode}\n".encode())
        """
        # 現時点ではコンソール出力のみ
        pass
    
    def get_active_effects(self) -> List[str]:
        """現在アクティブな効果のリストを取得"""
        with self.lock:
            return [f"{eff}:{mode}" for eff, mode in self.active_effects.keys()]
    
    def stop_all(self):
        """すべての効果を停止"""
        with self.lock:
            for (effect, mode) in list(self.active_effects.keys()):
                self._send_signal("STOP", effect, mode)
            self.active_effects.clear()
            self.water_shots.clear()

# ===== タイムライン処理 =====
class TimelinePlayer:
    """タイムラインを再生するクラス"""
    
    def __init__(self, timeline_path: str):
        with open(timeline_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.events = data.get("events", [])
        self.current_index = 0
        self.controller = EffectController()
        
        # イベントを時刻順にソート
        self.events.sort(key=lambda e: e.get("t", 0))
    
    def process_events_at_time(self, current_time: float, timing_offset: float = 0.0):
        """現在時刻に対応するイベントを処理"""
        while self.current_index < len(self.events):
            event = self.events[self.current_index]
            event_time = event.get("t", 0) + timing_offset  # オフセットを適用
            
            if event_time > current_time:
                break
            
            action = event.get("action")
            
            if action == "start":
                effect = event.get("effect")
                mode = event.get("mode")
                self.controller.start_effect(effect, mode, event_time)
            
            elif action == "stop":
                effect = event.get("effect")
                mode = event.get("mode")
                self.controller.stop_effect(effect, mode, event_time)
            
            elif action == "shot":
                # 水の一度きりの発射
                effect = event.get("effect")
                mode = event.get("mode")
                self.controller.shot_effect(effect, mode, event_time)
            
            self.current_index += 1
    
    def reset(self):
        """タイムラインを最初から再生"""
        self.current_index = 0
        self.controller.stop_all()
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        self.controller.stop_all()

# ===== 動画再生 =====
def get_video_info(video_path: str):
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

def playback_video(video_path: str):
    """動画を再生しながら効果を発動"""
    
    # 動画ファイルの存在確認
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")
    
    # タイムラインJSONのパスを決定
    video_name = Path(video_path).stem
    timeline_path = os.path.join(RESULTS_DIR, f"{video_name}_timeline.json")
    
    if not os.path.exists(timeline_path):
        raise FileNotFoundError(
            f"タイムラインファイルが見つかりません: {timeline_path}\n"
            f"先に解析モード (analyze_video.py) を実行してください。"
        )
    
    # タイムラインを読み込み
    player = TimelinePlayer(timeline_path)
    
    # 動画を開く
    with suppress_stderr():
        cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"動画を開けない: {video_path}")
    
    with suppress_stderr():
        fps, total_frames, duration = get_video_info(video_path)
    
    print(f"\n🎬 動画再生開始！")
    print(f"📺 長さ: {duration:.1f}秒 ({int(duration//60)}分{int(duration%60)}秒)")
    print(f"🎮 操作: [スペース]=一時停止 [R]=最初から [Q]=終了")
    print("-" * 60)
    
    # 再生開始
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    
    # 再生制御
    paused = False
    start_time = time.time()
    pause_offset = 0.0
    frame_delay = int(1000 / fps)
    last_table_update = 0.0
    
    # 初期表示
    player.controller.print_status_table(0.0)
    
    try:
        while True:
            if not paused:
                current_time = time.time() - start_time - pause_offset
                
                # 対応するフレームに移動
                with suppress_stderr():
                    target_frame = int(current_time * fps)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                    ret, frame = cap.read()
                
                if not ret or current_time > duration:
                    break
                
                # タイムラインイベントを処理（オフセット適用）
                player.process_events_at_time(current_time, TIMING_OFFSET)
                
                # 状態表を定期的に更新（0.1秒ごと）
                if current_time - last_table_update >= 0.1:
                    player.controller.print_status_table(current_time)
                    last_table_update = current_time
                
                # アクティブな効果を表示
                active_effects = player.controller.get_active_effects()
                display_frame = frame.copy()
                
                # 時刻とアクティブ効果をオーバーレイ表示
                time_text = f"Time: {current_time:.2f}s / {duration:.2f}s"
                cv2.putText(display_frame, time_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                if active_effects:
                    effects_text = f"Active: {', '.join(active_effects)}"
                    cv2.putText(display_frame, effects_text, (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                cv2.imshow(WINDOW_NAME, display_frame)
            
            # キー入力処理
            key = cv2.waitKey(frame_delay if not paused else 100) & 0xFF
            
            if key == ord('q') or key == 27:  # Q or ESC
                break
            elif key == ord(' '):  # Space
                paused = not paused
                if paused:
                    pause_start = time.time()
                else:
                    pause_offset += time.time() - pause_start
            elif key == ord('r'):  # R
                player.reset()
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                start_time = time.time()
                pause_offset = 0.0
                paused = False
    
    except KeyboardInterrupt:
        pass
    
    finally:
        player.cleanup()
        cap.release()
        cv2.destroyAllWindows()
        print("\n✅ 再生終了しました")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("使い方: python playback_video.py <動画ファイル>")
        print(f"\n解析済み動画 ({RESULTS_DIR}/):")
        if os.path.exists(RESULTS_DIR):
            json_files = [f.replace('_timeline.json', '.mp4') 
                         for f in os.listdir(RESULTS_DIR) if f.endswith('_timeline.json')]
            if json_files:
                for f in json_files:
                    print(f"  - {f}")
            else:
                print(f"  （先に analyze_video.py を実行してください）")
        sys.exit(1)
    
    video_file = sys.argv[1]
    
    # videosディレクトリ内のファイル名のみの場合はパスを追加
    if not os.path.exists(video_file) and os.path.exists(os.path.join(VIDEOS_DIR, video_file)):
        video_file = os.path.join(VIDEOS_DIR, video_file)
    
    playback_video(video_file)

