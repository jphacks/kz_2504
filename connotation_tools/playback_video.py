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

import os, sys, cv2, json, time, threading, warnings, contextlib, math
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import numpy as np
import subprocess
import signal
import platform

# 音声再生用
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("⚠️ 警告: pygameがインストールされていません。音声は再生されません。")
    print("   インストール: pip install pygame")

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
VIDEOS_DIR = str(SCRIPT_DIR / "videos")
RESULTS_DIR = str(SCRIPT_DIR / "results")
WINDOW_NAME = "Scene Playback - 体感型動画再生"
TIMING_OFFSET = -0.5  # タイミング調整（秒）：正の値で信号を遅らせる、負の値で早める

# ===== 効果信号送信（デバイス制御用） =====
class EffectController:
    """効果デバイスの制御を行うクラス"""
    
    def __init__(self):
        self.active_effects = {}
        self.shot_effects = {}  # shot系の発射を一時的に表示: {key: (start_time, end_time)}
        self.lock = threading.Lock()
        
        # 全効果の定義（表示順）- 4DX@HOME仕様
        self.all_effects = [
            # 光
            ("flash", "steady", "💡 点灯"),
            ("flash", "blink", "⚡ 点滅"),
            ("flash", "breathe", "💡 呼吸"),
            # 風
            ("wind", "burst", "💨 風"),
            # 水・ミスト
            ("water", "burst", "💦 水しぶき"),
            ("mist", "burst", "🌫️ ミスト"),
            # 色
            ("color", "pink", "🩷 ピンク"),
            ("color", "red", "🔴 赤"),
            ("color", "orange", "🟠 オレンジ"),
            ("color", "yellow", "🟡 黄色"),
            ("color", "yellow_green", "🟢 黄緑"),
            ("color", "green", "🟢 緑"),
            ("color", "dark_green", "🟢 深緑"),
            ("color", "cyan", "🔷 シアン"),
            ("color", "blue", "🔵 青"),
            ("color", "purple", "🟣 紫"),
            ("color", "white", "⚪ 白"),
            # 振動（上=背中、下=おしり）
            ("vibration", "up_strong", "📳 上:強（背中）"),
            ("vibration", "up_mid_strong", "📳 上:中強（背中）"),
            ("vibration", "up_mid_weak", "📳 上:中弱（背中）"),
            ("vibration", "up_weak", "📳 上:弱（背中）"),
            ("vibration", "down_strong", "📳 下:強（おしり）"),
            ("vibration", "down_mid_strong", "📳 下:中強（おしり）"),
            ("vibration", "down_mid_weak", "📳 下:中弱（おしり）"),
            ("vibration", "down_weak", "📳 下:弱（おしり）"),
            ("vibration", "up_down_strong", "📳 上＆下:強（かなり強い）"),
            ("vibration", "up_down_mid_strong", "📳 上＆下:中強（かなり強い）"),
            ("vibration", "up_down_mid_weak", "📳 上＆下:中弱（かなり強い）"),
            ("vibration", "up_down_weak", "📳 上＆下:弱（かなり強い）"),
            ("vibration", "heartbeat", "💓 ドキドキ"),
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
        """効果を一度だけ発射（shot系）"""
        with self.lock:
            key = (effect, mode)
            # 0.5秒間だけ表に表示
            end_time = timestamp + 0.5
            self.shot_effects[key] = (timestamp, end_time)
        self._send_signal("SHOT", effect, mode)
    
    def _get_effect_name(self, effect: str, mode: str) -> str:
        """効果の日本語名を取得（4DX@HOME仕様）"""
        effect_names = {
            # 光
            "flash:steady": "💡 点灯",
            "flash:blink": "⚡ 点滅",
            "flash:breathe": "💡 呼吸",
            # 風
            "wind:burst": "💨 風",
            # 水・ミスト
            "water:burst": "💦 水しぶき",
            "mist:burst": "🌫️ ミスト",
            # 色
            "color:pink": "🩷 ピンク",
            "color:red": "🔴 赤",
            "color:orange": "🟠 オレンジ",
            "color:yellow_green": "🟢 黄緑",
            "color:green": "🟢 緑",
            "color:dark_green": "🟢 深緑",
            "color:blue": "🔵 青",
            "color:yellow": "🟡 黄色",
            "color:cyan": "🔷 シアン",
            "color:purple": "🟣 紫",
            "color:white": "⚪ 白",
            # 振動
            "vibration:up_strong": "📳 上:強（背中）",
            "vibration:up_mid_strong": "📳 上:中強（背中）",
            "vibration:up_mid_weak": "📳 上:中弱（背中）",
            "vibration:up_weak": "📳 上:弱（背中）",
            "vibration:down_strong": "📳 下:強（おしり）",
            "vibration:down_mid_strong": "📳 下:中強（おしり）",
            "vibration:down_mid_weak": "📳 下:中弱（おしり）",
            "vibration:down_weak": "📳 下:弱（おしり）",
            "vibration:up_down_strong": "📳 上＆下:強（かなり強い）",
            "vibration:up_down_mid_strong": "📳 上＆下:中強（かなり強い）",
            "vibration:up_down_mid_weak": "📳 上＆下:中弱（かなり強い）",
            "vibration:up_down_weak": "📳 上＆下:弱（かなり強い）",
            "vibration:heartbeat": "💓 ドキドキ",
        }
        return effect_names.get(f"{effect}:{mode}", f"{effect}:{mode}")
    
    def print_status_table(self, current_time: float):
        """現在の効果状態を表形式で表示"""
        with self.lock:
            # 期限切れの水shotを削除
            expired_shots = [k for k, (start_time, end_time) in self.shot_effects.items() if current_time > end_time]
            for k in expired_shots:
                del self.shot_effects[k]
            
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
                # shot系の発射（一時表示）
                elif key in self.shot_effects:
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
    
    def get_vibration_state(self, current_time: float) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """振動の状態を取得: (上(背中)の強度, 下(おしり)の強度, 特別モード)"""
        with self.lock:
            up_intensity = None
            down_intensity = None
            special_mode = None
            
            for (effect, mode), start_time in self.active_effects.items():
                if effect == "vibration":
                    if mode == "heartbeat":
                        special_mode = "heartbeat"
                    elif mode.startswith("up_down_"):
                        # 上下同時
                        intensity = mode.replace("up_down_", "")
                        up_intensity = intensity
                        down_intensity = intensity
                    elif mode.startswith("up_"):
                        # 上のみ
                        up_intensity = mode.replace("up_", "")
                    elif mode.startswith("down_"):
                        # 下のみ
                        down_intensity = mode.replace("down_", "")
            
            return up_intensity, down_intensity, special_mode
    
    def get_shot_effect_active(self, effect: str, current_time: float) -> Tuple[bool, Optional[float]]:
        """指定のshotエフェクトが発射中かどうかと開始時刻を返す"""
        with self.lock:
            expired_shots = [k for k, (start_time, end_time) in self.shot_effects.items() if current_time > end_time]
            for k in expired_shots:
                del self.shot_effects[k]
            
            start_times = [
                start_time for (eff, _), (start_time, _end_time) in self.shot_effects.items()
                if eff == effect
            ]
            if start_times:
                return True, min(start_times)
            return False, None
    
    def get_active_color(self) -> Optional[str]:
        """現在アクティブな色を取得"""
        with self.lock:
            for (effect, mode) in self.active_effects.keys():
                if effect == "color":
                    return mode
            return None
    
    def get_active_flash(self) -> Optional[str]:
        """現在アクティブな光を取得"""
        with self.lock:
            for (effect, mode) in self.active_effects.keys():
                if effect == "flash":
                    return mode
            return None
    
    def is_wind_active(self) -> bool:
        """風がアクティブかどうか"""
        with self.lock:
            return ("wind", "burst") in self.active_effects
    
    def stop_all(self):
        """すべての効果を停止"""
        with self.lock:
            for (effect, mode) in list(self.active_effects.keys()):
                self._send_signal("STOP", effect, mode)
            self.active_effects.clear()
            self.shot_effects.clear()

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

# ===== 視覚化用のヘルパー関数 =====
def draw_rounded_rect(img: np.ndarray, pt1: Tuple[int, int], pt2: Tuple[int, int], 
                     color: Tuple[int, int, int], thickness: int = -1, radius: int = 10):
    """角丸矩形を描画"""
    x1, y1 = pt1
    x2, y2 = pt2
    if thickness == -1:
        # 塗りつぶし
        cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y2), color, -1)
        cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, -1)
        cv2.circle(img, (x1 + radius, y1 + radius), radius, color, -1)
        cv2.circle(img, (x2 - radius, y1 + radius), radius, color, -1)
        cv2.circle(img, (x1 + radius, y2 - radius), radius, color, -1)
        cv2.circle(img, (x2 - radius, y2 - radius), radius, color, -1)
    else:
        # 枠線
        cv2.line(img, (x1 + radius, y1), (x2 - radius, y1), color, thickness)
        cv2.line(img, (x1 + radius, y2), (x2 - radius, y2), color, thickness)
        cv2.line(img, (x1, y1 + radius), (x1, y2 - radius), color, thickness)
        cv2.line(img, (x2, y1 + radius), (x2, y2 - radius), color, thickness)
        cv2.ellipse(img, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, thickness)
        cv2.ellipse(img, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, thickness)
        cv2.ellipse(img, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, color, thickness)
        cv2.ellipse(img, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, color, thickness)

def draw_vibration_icon(img: np.ndarray, x: int, y: int, size: int, 
                       intensity: Optional[str], is_up: bool, current_time: float,
                       is_blinking: bool = False) -> np.ndarray:
    """振動アイコンを描画（大きなアイコン）"""
    center_x, center_y = x + size // 2, y + size // 2
    icon_size = size // 2
    
    # 点滅処理
    if is_blinking:
        blink = int(current_time * 3) % 2  # 1.5Hzの点滅
        if blink == 0:
            # 点滅時は非表示
            return img
    
    if intensity is None:
        # 非アクティブ: グレーのアイコン
        color = (100, 100, 100)
        alpha = 0.4
        wave_amplitude = 0  # 波形の振幅は0
    else:
        # 強度に応じて色を設定
        intensity_map = {
            "weak": (100, 200, 100),      # 緑
            "mid_weak": (150, 200, 100),  # 黄緑
            "mid_strong": (200, 200, 100), # 黄色
            "strong": (200, 100, 100),    # 赤
        }
        color = intensity_map.get(intensity, (200, 100, 100))
        color = (int(color[2]), int(color[1]), int(color[0]))  # BGR変換
        alpha = 0.8
        
        # 強度に応じた波形の振幅（0が基本、強度が強いほど振幅が大きくなる）
        amplitude_map = {
            "weak": 8,        # 弱: 振幅8
            "mid_weak": 12,   # 中弱: 振幅12
            "mid_strong": 18, # 中強: 振幅18
            "strong": 25,     # 強: 振幅25（MAX）
        }
        wave_amplitude = amplitude_map.get(intensity, 15)
    
    # アイコン背景（丸）
    overlay = img.copy()
    cv2.circle(overlay, (center_x, center_y), icon_size, color, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    
    # アイコンの輪郭
    cv2.circle(img, (center_x, center_y), icon_size, (255, 255, 255), 3)
    
    # 振動波形を描画（強度に応じた振幅）
    wave_width = icon_size
    wave_center_y = center_y
    num_points = 40
    
    points = []
    for i in range(num_points):
        px = center_x - wave_width // 2 + (i * wave_width // (num_points - 1))
        # 波形: 基本は0（center_y）、強度に応じて振幅が変わる
        phase = i * 0.3 + current_time * 3  # 波の位相
        if is_up:
            # 上向きの波形（上に振れる）
            py = wave_center_y - int(wave_amplitude * math.sin(phase))
        else:
            # 下向きの波形（下に振れる）
            py = wave_center_y + int(wave_amplitude * math.sin(phase))
        points.append([px, py])
    
    if len(points) > 1:
        pts = np.array(points, np.int32)
        cv2.polylines(img, [pts], False, (255, 255, 255), 2)
        # 基準線（0の位置）を薄く表示
        cv2.line(img, (center_x - wave_width // 2, wave_center_y), 
                (center_x + wave_width // 2, wave_center_y), (150, 150, 150), 1)
    
    return img

def draw_water_icon(img: np.ndarray, x: int, y: int, size: int, 
                   active: bool, current_time: float, shot_start_time: Optional[float] = None) -> np.ndarray:
    """水アイコンを描画"""
    center_x, center_y = x + size // 2, y + size // 2
    icon_size = size // 2
    
    if active and shot_start_time is not None:
        elapsed = current_time - shot_start_time
        if elapsed < 0.5:
            # アクティブ: 青のアイコン + アニメーション
            color = (255, 150, 100)  # BGR: 青
            alpha = 0.8
            
            # 水滴アニメーション
            drop_y = center_y - icon_size // 2 + int(elapsed * 30)
            if drop_y < center_y + icon_size // 2:
                drop_size = max(5, int(icon_size * 0.3 * (1 - elapsed * 0.5)))
                cv2.circle(img, (center_x, drop_y), drop_size, (255, 200, 150), -1)
                cv2.circle(img, (center_x, drop_y), drop_size, (255, 255, 255), 2)
        else:
            color = (255, 150, 100)
            alpha = 0.8
    elif active:
        # アクティブ（継続中）
        color = (255, 150, 100)
        alpha = 0.8
    else:
        # 非アクティブ: グレー
        color = (100, 100, 100)
        alpha = 0.4
    
    # アイコン背景
    overlay = img.copy()
    cv2.circle(overlay, (center_x, center_y), icon_size, color, -1)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    
    # 輪郭
    cv2.circle(img, (center_x, center_y), icon_size, (255, 255, 255), 3)
    
    # 水滴アイコン（3つの水滴）
    drop_radius = icon_size // 4
    for i, offset_y in enumerate([-drop_radius, 0, drop_radius]):
        cv2.circle(img, (center_x, center_y + offset_y), drop_radius - 2, (200, 230, 255), -1)
        cv2.circle(img, (center_x, center_y + offset_y), drop_radius - 2, (255, 255, 255), 1)
    
    return img

def draw_effect_panel(img: np.ndarray, controller: EffectController, current_time: float, 
                     frame_width: int, frame_height: int) -> np.ndarray:
    """効果パネルを固定サイズで右側に描画"""
    # 固定サイズのパネル
    panel_width = 380
    panel_height = min(900, frame_height - 40)
    panel_x = frame_width - panel_width - 20
    panel_y = 20
    panel_radius = 15
    
    # パネル背景（グラデーション風の濃い背景）
    overlay = img.copy()
    draw_rounded_rect(overlay, (panel_x, panel_y), 
                     (panel_x + panel_width, panel_y + panel_height), 
                     (25, 25, 35), -1, panel_radius)
    cv2.addWeighted(overlay, 0.85, img, 0.15, 0, img)
    
    # パネルの枠線（光る感じ）
    draw_rounded_rect(img, (panel_x, panel_y), 
                     (panel_x + panel_width, panel_y + panel_height), 
                     (100, 100, 120), 2, panel_radius)
    
    # タイトル背景
    title_height = 60
    draw_rounded_rect(img, (panel_x + 10, panel_y + 10), 
                     (panel_x + panel_width - 10, panel_y + 10 + title_height), 
                     (40, 50, 70), -1, 10)
    
    y_offset = panel_y + 30
    
    # タイトル
    cv2.putText(img, "4DX EFFECTS", (panel_x + 20, y_offset + 35), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, (200, 220, 255), 3)
    cv2.putText(img, "4DX EFFECTS", (panel_x + 20, y_offset + 35), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, (150, 180, 200), 1)
    y_offset += 80
    
    # セクション間のスペーサー
    def draw_section_header(title: str, y: int) -> int:
        cv2.putText(img, title, (panel_x + 20, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 200, 220), 2)
        return y + 30
    
    # 振動セクション
    y_offset = draw_section_header("VIBRATION", y_offset)
    
    up_intensity, down_intensity, special_mode = controller.get_vibration_state(current_time)
    
    # ハートビート時はUPを点滅させる
    is_heartbeat = (special_mode == "heartbeat")
    is_up_blinking = is_heartbeat
    
    # 上（背中）アイコン
    icon_size = 80
    icon_x = panel_x + 30
    draw_vibration_icon(img, icon_x, y_offset, icon_size, up_intensity, True, current_time, 
                       is_blinking=is_up_blinking)
    label_y = y_offset + icon_size // 2
    cv2.putText(img, "UP", (icon_x + icon_size + 15, label_y - 10), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    if is_heartbeat:
        cv2.putText(img, "HEARTBEAT", (icon_x + icon_size + 15, label_y + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 150, 150), 1)
    elif up_intensity:
        intensity_label = up_intensity.replace("_", " ").upper()
        cv2.putText(img, intensity_label, (icon_x + icon_size + 15, label_y + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    else:
        cv2.putText(img, "OFF", (icon_x + icon_size + 15, label_y + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 120, 120), 1)
    y_offset += icon_size + 20
    
    # 下（おしり）アイコン
    draw_vibration_icon(img, icon_x, y_offset, icon_size, down_intensity, False, current_time)
    label_y = y_offset + icon_size // 2
    cv2.putText(img, "DOWN", (icon_x + icon_size + 15, label_y - 10), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    if down_intensity:
        intensity_label = down_intensity.replace("_", " ").upper()
        cv2.putText(img, intensity_label, (icon_x + icon_size + 15, label_y + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    else:
        cv2.putText(img, "OFF", (icon_x + icon_size + 15, label_y + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 120, 120), 1)
    y_offset += icon_size + 20
    
    # 水セクション
    y_offset += 10
    y_offset = draw_section_header("WATER", y_offset)
    
    water_active, water_start_time = controller.get_shot_effect_active("water", current_time)
    icon_size = 80
    icon_x = panel_x + 30
    draw_water_icon(img, icon_x, y_offset, icon_size, water_active, current_time, water_start_time)
    label_y = y_offset + icon_size // 2
    if water_active:
        cv2.putText(img, "ACTIVE", (icon_x + icon_size + 15, label_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 200, 255), 2)
        if water_start_time:
            cv2.putText(img, "SPLASH!", (icon_x + icon_size + 15, label_y + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 230, 255), 1)
    else:
        cv2.putText(img, "OFF", (icon_x + icon_size + 15, label_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 120, 120), 2)
    y_offset += icon_size + 20
    
    # ミストセクション
    y_offset += 10
    y_offset = draw_section_header("MIST", y_offset)
    
    mist_active, mist_start_time = controller.get_shot_effect_active("mist", current_time)
    icon_size = 80
    icon_x = panel_x + 30
    draw_water_icon(img, icon_x, y_offset, icon_size, mist_active, current_time, mist_start_time)
    label_y = y_offset + icon_size // 2
    if mist_active:
        cv2.putText(img, "ACTIVE", (icon_x + icon_size + 15, label_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        if mist_start_time:
            cv2.putText(img, "MIST!", (icon_x + icon_size + 15, label_y + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)
    else:
        cv2.putText(img, "OFF", (icon_x + icon_size + 15, label_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 120, 120), 2)
    y_offset += icon_size + 20
    
    # 色セクション
    y_offset += 10
    y_offset = draw_section_header("COLOR", y_offset)
    
    active_color = controller.get_active_color()
    icon_size = 80
    icon_x = panel_x + 30
    center_x, center_y = icon_x + icon_size // 2, y_offset + icon_size // 2
    
    if active_color:
        color_map = {
            "pink": (203, 105, 255),
            "red": (0, 0, 255),
            "orange": (0, 100, 255),
            "yellow": (0, 255, 255),
            "yellow_green": (0, 255, 150),
            "green": (0, 255, 0),
            "dark_green": (0, 100, 0),
            "cyan": (255, 255, 0),
            "blue": (255, 0, 0),
            "purple": (255, 0, 255),
            "white": (255, 255, 255),
        }
        color_bgr = color_map.get(active_color, (255, 255, 255))
        overlay = img.copy()
        cv2.circle(overlay, (center_x, center_y), icon_size // 2, color_bgr, -1)
        cv2.addWeighted(overlay, 0.8, img, 0.2, 0, img)
        cv2.circle(img, (center_x, center_y), icon_size // 2, (255, 255, 255), 3)
    else:
        # グレーのアイコン
        overlay = img.copy()
        cv2.circle(overlay, (center_x, center_y), icon_size // 2, (100, 100, 100), -1)
        cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)
        cv2.circle(img, (center_x, center_y), icon_size // 2, (150, 150, 150), 2)
    
    label_y = y_offset + icon_size // 2
    if active_color:
        cv2.putText(img, active_color.upper(), (icon_x + icon_size + 15, label_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    else:
        cv2.putText(img, "OFF", (icon_x + icon_size + 15, label_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 120, 120), 2)
    y_offset += icon_size + 20
    
    # 光セクション
    y_offset += 10
    y_offset = draw_section_header("LIGHT", y_offset)
    
    active_flash = controller.get_active_flash()
    icon_size = 80
    icon_x = panel_x + 30
    center_x, center_y = icon_x + icon_size // 2, y_offset + icon_size // 2
    
    if active_flash:
        if active_flash == "blink":
            blink = int(current_time * 6) % 2
            light_intensity = 255 if blink else 170
        elif active_flash == "breathe":
            light_intensity = int(180 + 60 * (1 + math.sin(current_time * 2.0)) / 2)
        else:  # steady
            light_intensity = 255
        overlay = img.copy()
        cv2.circle(overlay, (center_x, center_y), icon_size // 2, 
                  (light_intensity, light_intensity, 200), -1)
        cv2.addWeighted(overlay, 0.8, img, 0.2, 0, img)
        cv2.circle(img, (center_x, center_y), icon_size // 2, (255, 255, 255), 3)
        # 光の放射線
        for i in range(8):
            angle = i * math.pi / 4
            x1 = center_x + int((icon_size // 2 - 5) * math.cos(angle))
            y1 = center_y + int((icon_size // 2 - 5) * math.sin(angle))
            x2 = center_x + int((icon_size // 2 + 10) * math.cos(angle))
            y2 = center_y + int((icon_size // 2 + 10) * math.sin(angle))
            cv2.line(img, (x1, y1), (x2, y2), (255, 255, 200), 2)
    else:
        # グレーのアイコン
        overlay = img.copy()
        cv2.circle(overlay, (center_x, center_y), icon_size // 2, (100, 100, 100), -1)
        cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)
        cv2.circle(img, (center_x, center_y), icon_size // 2, (150, 150, 150), 2)
    
    label_y = y_offset + icon_size // 2
    if active_flash:
        flash_label = active_flash.replace("_", " ").upper()
        cv2.putText(img, flash_label, (icon_x + icon_size + 15, label_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    else:
        cv2.putText(img, "OFF", (icon_x + icon_size + 15, label_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 120, 120), 2)
    y_offset += icon_size + 20
    
    # 風セクション
    y_offset += 10
    y_offset = draw_section_header("WIND", y_offset)
    
    wind_active = controller.is_wind_active()
    icon_size = 80
    icon_x = panel_x + 30
    center_x, center_y = icon_x + icon_size // 2, y_offset + icon_size // 2
    
    if wind_active:
        overlay = img.copy()
        cv2.circle(overlay, (center_x, center_y), icon_size // 2, (200, 220, 255), -1)
        cv2.addWeighted(overlay, 0.8, img, 0.2, 0, img)
        cv2.circle(img, (center_x, center_y), icon_size // 2, (255, 255, 255), 3)
        # 風の矢印（アニメーション付き）
        for i in range(3):
            angle_offset = current_time * 1.5 + i * 0.5
            x1 = center_x - icon_size // 3 + int(10 * math.cos(angle_offset))
            y1 = center_y + int(10 * math.sin(angle_offset))
            x2 = center_x + icon_size // 3 + int(10 * math.cos(angle_offset))
            y2 = y1
            cv2.arrowedLine(img, (x1, y1), (x2, y2), (255, 255, 255), 2, tipLength=0.3)
    else:
        # グレーのアイコン
        overlay = img.copy()
        cv2.circle(overlay, (center_x, center_y), icon_size // 2, (100, 100, 100), -1)
        cv2.addWeighted(overlay, 0.4, img, 0.6, 0, img)
        cv2.circle(img, (center_x, center_y), icon_size // 2, (150, 150, 150), 2)
        # グレーの矢印
        x1 = center_x - icon_size // 3
        y1 = center_y
        x2 = center_x + icon_size // 3
        y2 = center_y
        cv2.arrowedLine(img, (x1, y1), (x2, y2), (150, 150, 150), 2, tipLength=0.3)
    
    label_y = y_offset + icon_size // 2
    if wind_active:
        cv2.putText(img, "ACTIVE", (icon_x + icon_size + 15, label_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 220, 255), 2)
    else:
        cv2.putText(img, "OFF", (icon_x + icon_size + 15, label_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 120, 120), 2)
    
    return img

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
    
    # 音声再生の初期化
    audio_playing = False
    audio_start_time = None
    audio_sound = None
    temp_audio_file = None
    
    print(f"\n🎬 動画再生開始！")
    print(f"📺 長さ: {duration:.1f}秒 ({int(duration//60)}分{int(duration%60)}秒)")
    
    # 音声再生の準備（ffmpeg + pygame）
    if PYGAME_AVAILABLE:
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            # ffmpegを使って音声を抽出して一時WAVファイルに保存
            import tempfile
            temp_audio_file = os.path.join(tempfile.gettempdir(), f"temp_audio_{os.getpid()}.wav")
            
            if platform.system() == 'Windows':
                ffmpeg_cmd = 'ffmpeg.exe'
            else:
                ffmpeg_cmd = 'ffmpeg'
            
            # 音声を抽出
            extract_cmd = [
                ffmpeg_cmd,
                '-i', video_path,
                '-vn',  # ビデオなし
                '-acodec', 'pcm_s16le',  # WAV形式
                '-ar', '44100',  # サンプリングレート
                '-ac', '2',  # ステレオ
                '-y',  # 上書き
                temp_audio_file
            ]
            
            result = subprocess.run(
                extract_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10
            )
            
            if result.returncode == 0 and os.path.exists(temp_audio_file):
                # 音声ファイルを読み込んで再生
                audio_sound = pygame.mixer.Sound(temp_audio_file)
                print("🔊 音声: 準備完了")
            else:
                print("⚠️ 音声抽出に失敗しました。音声なしで再生します。")
                temp_audio_file = None
        except FileNotFoundError:
            print("⚠️ ffmpegが見つかりません。音声は再生されません。")
            print("   ffmpegをインストールしてください: https://ffmpeg.org/download.html")
        except subprocess.TimeoutExpired:
            print("⚠️ 音声抽出がタイムアウトしました。音声なしで再生します。")
        except Exception as e:
            print(f"⚠️ 音声初期化エラー: {e}")
            print("   音声なしで再生します。")
    else:
        print("⚠️ pygameがインストールされていません。音声は再生されません。")
        print("   インストール: pip install pygame")
    
    print(f"🎮 操作: [スペース]=一時停止 [R]=最初から [Q]=終了")
    print("-" * 60)
    
    # 再生開始（ウィンドウ表示）
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    
    # 再生制御
    paused = False
    start_time = time.time()
    pause_offset = 0.0
    frame_delay = int(1000 / fps)
    last_table_update = 0.0
    
    # 音声再生開始
    if audio_sound:
        try:
            audio_channel = audio_sound.play(loops=0)
            audio_playing = True
            audio_start_time = time.time()
        except Exception as e:
            print(f"⚠️ 音声再生開始エラー: {e}")
    
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
                
                # 状態表を定期的に更新（0.5秒ごと、頻度を下げる）
                if current_time - last_table_update >= 0.5:
                    player.controller.print_status_table(current_time)
                    last_table_update = current_time
                
                # アクティブな効果を表示
                display_frame = frame.copy()
                
                # 時刻表示
                time_text = f"Time: {current_time:.2f}s / {duration:.2f}s"
                cv2.putText(display_frame, time_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(display_frame, time_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
                
                # 効果パネルを描画
                frame_height, frame_width = display_frame.shape[:2]
                display_frame = draw_effect_panel(display_frame, player.controller, current_time, 
                                                 frame_width, frame_height)
                
                cv2.imshow(WINDOW_NAME, display_frame)
            
            # キー入力処理
            key = cv2.waitKey(frame_delay if not paused else 100) & 0xFF
            
            if key == ord('q') or key == 27:  # Q or ESC
                break
            elif key == ord(' '):  # Space
                paused = not paused
                if paused:
                    pause_start = time.time()
                    # 音声も一時停止
                    if audio_sound:
                        pygame.mixer.pause()
                else:
                    pause_offset += time.time() - pause_start
                    # 音声も再開
                    if audio_sound:
                        pygame.mixer.unpause()
            elif key == ord('r'):  # R
                player.reset()
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                start_time = time.time()
                pause_offset = 0.0
                paused = False
                # 音声も最初から
                if audio_sound:
                    pygame.mixer.stop()
                    try:
                        audio_channel = audio_sound.play(loops=0)
                        audio_start_time = time.time()
                    except:
                        pass
    
    except KeyboardInterrupt:
        pass
    
    finally:
        # 音声を停止
        if audio_sound:
            try:
                pygame.mixer.stop()
            except:
                pass
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.quit()
            except:
                pass
        # 一時音声ファイルを削除
        if temp_audio_file and os.path.exists(temp_audio_file):
            try:
                os.remove(temp_audio_file)
            except:
                pass
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

