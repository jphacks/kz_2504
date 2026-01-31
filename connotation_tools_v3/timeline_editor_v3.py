# -*- coding: utf-8 -*-
import sys
import os
import cv2
import json
import numpy as np
import bisect
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout,
    QWidget, QFrame, QGridLayout, QLineEdit, QMessageBox, QSlider
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap

# --- ライブラリインポート (librosa/moviepy はオプション: 無くてもエディタは起動、音声メトリクスだけ無効) ---
LIBROSA_AVAILABLE = False
MOVIEPY_AVAILABLE = False
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    print("⚠️ librosa がありません。音声メトリクス（音量・ベース等）は無効です。")
try:
    try:
        from moviepy import VideoFileClip
    except ImportError:
        from moviepy.editor import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    print("⚠️ moviepy がありません。音声メトリクスは無効です。")
if not (LIBROSA_AVAILABLE and MOVIEPY_AVAILABLE):
    print("   → エディタは使えます。音声解析を使う場合は: brew install cmake のあと pip install librosa moviepy")

# --- 設定・定数 ---
SCRIPT_DIR = Path(__file__).parent.absolute()
VIDEOS_DIR = str(SCRIPT_DIR / "videos")
FRAMES_DIR = str(SCRIPT_DIR / "frames")
EDITOR_RESULTS_DIR = str(SCRIPT_DIR / "editor_results")
FRAME_INTERVAL = 0.25  # 秒
FRAME_TIMES_FILENAME = "frame_times.json"

# 色定義 (v3仕様)
COLOR_KEYS = [
    "pink", "red", "orange", "yellow", "yellow_green", "green",
    "dark_green", "cyan", "blue", "purple", "white"
]
COLOR_LABELS = {
    "pink": "ピンク", "red": "赤", "orange": "オレンジ", "yellow": "黄色",
    "yellow_green": "黄緑", "green": "緑", "dark_green": "深緑",
    "cyan": "シアン", "blue": "青", "purple": "紫", "white": "白"
}
COLOR_RGB = {
    "pink": (255, 105, 180), "red": (255, 0, 0), "orange": (255, 165, 0),
    "yellow": (255, 255, 0), "yellow_green": (154, 205, 50), "green": (0, 128, 0),
    "dark_green": (0, 100, 0), "cyan": (0, 255, 255), "blue": (0, 0, 255),
    "purple": (128, 0, 128), "white": (255, 255, 255)
}

FLASH_MODES = [None, "steady", "blink", "breathe"]
FLASH_LABELS = {
    None: "OFF",
    "steady": "点灯",
    "blink": "点滅",
    "breathe": "呼吸"
}

VIB_GROUPS = {
    "up": ["up_weak", "up_mid_weak", "up_mid_strong", "up_strong"],
    "down": ["down_weak", "down_mid_weak", "down_mid_strong", "down_strong"],
    "up_down": ["up_down_weak", "up_down_mid_weak", "up_down_mid_strong", "up_down_strong"],
    "heartbeat": ["heartbeat"]
}
VIB_LABELS = {
    "weak": "弱",
    "mid_weak": "中弱",
    "mid_strong": "中強",
    "strong": "強",
    "heartbeat": "ドキドキ"
}

# --- データモデル ---
class FrameData:
    def __init__(self):
        self.caption = ""
        self.wind = False
        self.water = False
        self.water_on = False
        self.mist = False
        self.mist_on = False
        self.led_strength = None
        self.led_transition = None
        self.vibration = set()
        self.flash = None
        self.color = None

# --- 動画処理クラス ---
class VideoProcessor:
    def __init__(self, video_name):
        self.video_path = self._resolve_video_path(video_name)
        video_basename = os.path.splitext(os.path.basename(self.video_path))[0]
        self.output_dir = os.path.join(FRAMES_DIR, video_basename)
        self.frame_paths = []
        self.frame_times = []
        self.frame_interval = FRAME_INTERVAL

        # 音声解析データ格納用
        self.audio_metrics = {
            "volume": [],
            "bass": [],
            "high": [],
            "attack": []
        }

        if not os.path.exists(self.video_path):
            print(f"Error: Video not found at {self.video_path}")
            sys.exit(1)

        # 1. 画像切り出し
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            self._extract_frames()
        else:
            print("既存の画像が見つかりました。ロード中...")
            files = sorted([f for f in os.listdir(self.output_dir) if f.endswith('.jpg')])
            if not files:
                self._extract_frames()
            else:
                self.frame_paths = [os.path.join(self.output_dir, f) for f in files]

        # フレームの実時間を取得（VFR対策）
        self._compute_frame_times()

        # 2. 高度音声解析
        self._analyze_audio_advanced()

    def _resolve_video_path(self, video_name):
        if os.path.exists(video_name):
            return video_name
        candidate = os.path.join(VIDEOS_DIR, video_name)
        return candidate

    def _extract_frames(self):
        print("フレーム切り出し中 (0.25秒間隔)...")
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        duration = (total_frames / fps) if fps > 0 and total_frames > 0 else None

        saved_count = 0
        times = []

        if duration is not None:
            t = 0.0
            while t <= duration + 1e-6:
                cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
                ret, frame = cap.read()
                if not ret:
                    break
                h, w = frame.shape[:2]
                new_w = 640
                new_h = int(h * (new_w / w))
                frame = cv2.resize(frame, (new_w, new_h))
                filename = os.path.join(self.output_dir, f"frame_{saved_count:05d}.jpg")
                try:
                    is_success, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                    if is_success:
                        with open(filename, "wb") as f:
                            buffer.tofile(f)
                        self.frame_paths.append(filename)
                        times.append(round(t, 6))
                        saved_count += 1
                except Exception:
                    pass
                t += FRAME_INTERVAL
        else:
            next_t = 0.0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                pos_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
                pos_t = (pos_msec / 1000.0) if pos_msec and pos_msec > 0 else None
                if pos_t is None or pos_t + 1e-6 < next_t:
                    continue
                h, w = frame.shape[:2]
                new_w = 640
                new_h = int(h * (new_w / w))
                frame = cv2.resize(frame, (new_w, new_h))
                filename = os.path.join(self.output_dir, f"frame_{saved_count:05d}.jpg")
                try:
                    is_success, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                    if is_success:
                        with open(filename, "wb") as f:
                            buffer.tofile(f)
                        self.frame_paths.append(filename)
                        times.append(round(next_t, 6))
                        saved_count += 1
                except Exception:
                    pass
                next_t += FRAME_INTERVAL
        cap.release()
        print(f"画像生成完了: {len(self.frame_paths)} 枚")
        self.frame_times = times
        self._save_frame_times()

    def _compute_frame_times(self):
        times = self._load_frame_times()
        if not times:
            times = [i * FRAME_INTERVAL for i in range(len(self.frame_paths))]
        if len(times) != len(self.frame_paths):
            times = [i * FRAME_INTERVAL for i in range(len(self.frame_paths))]
        self.frame_times = times
        if len(times) > 1:
            self.frame_interval = (times[-1] - times[0]) / (len(times) - 1)

    def _frame_times_path(self):
        return os.path.join(self.output_dir, FRAME_TIMES_FILENAME)

    def _save_frame_times(self):
        if not self.frame_times:
            return
        try:
            path = self._frame_times_path()
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"frame_times": self.frame_times}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_frame_times(self):
        path = self._frame_times_path()
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            times = data.get("frame_times")
            if isinstance(times, list) and times:
                return times
        except Exception:
            return None
        return None

    def _analyze_audio_advanced(self):
        print("音声詳細解析中 (Librosa使用)... これには時間がかかります")
        if not (LIBROSA_AVAILABLE and MOVIEPY_AVAILABLE):
            self._fill_empty_metrics(len(self.frame_paths))
            return
        try:
            temp_wav = "temp_audio.wav"
            clip = VideoFileClip(self.video_path)

            if clip.audio is None:
                print("警告: 音声トラックがありません。")
                self._fill_empty_metrics(len(self.frame_paths))
                return

            clip.audio.write_audiofile(
                temp_wav, fps=22050, nbytes=2, codec='pcm_s16le', logger=None
            )
            clip.close()

            y, sr = librosa.load(temp_wav, sr=22050)
            os.remove(temp_wav)

            total_frames = len(self.frame_paths)
            times_video = np.arange(total_frames) * FRAME_INTERVAL

            rms = librosa.feature.rms(y=y)[0]
            times_rms = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
            vol_interp = np.interp(times_video, times_rms, rms)
            self.audio_metrics["volume"] = (vol_interp * 1000).clip(0, 999).tolist()

            S = np.abs(librosa.stft(y))
            freqs = librosa.fft_frequencies(sr=sr)
            bass_indices = np.where(freqs < 200)[0]
            bass_energy = np.mean(S[bass_indices, :], axis=0)
            times_stft = librosa.frames_to_time(np.arange(len(bass_energy)), sr=sr)
            bass_interp = np.interp(times_video, times_stft, bass_energy)
            self.audio_metrics["bass"] = (bass_interp * 50).clip(0, 999).tolist()

            zcr = librosa.feature.zero_crossing_rate(y)[0]
            times_zcr = librosa.frames_to_time(np.arange(len(zcr)), sr=sr)
            zcr_interp = np.interp(times_video, times_zcr, zcr)
            self.audio_metrics["high"] = (zcr_interp * 500).clip(0, 999).tolist()

            onset = librosa.onset.onset_strength(y=y, sr=sr)
            times_onset = librosa.frames_to_time(np.arange(len(onset)), sr=sr)
            onset_interp = np.interp(times_video, times_onset, onset)
            self.audio_metrics["attack"] = (onset_interp * 10).clip(0, 999).tolist()

            print("解析完了。")

        except Exception as e:
            print(f"音声解析エラー: {e}")
            self._fill_empty_metrics(len(self.frame_paths))

    def _fill_empty_metrics(self, length):
        zeroes = [0.0] * length
        self.audio_metrics = {k: zeroes for k in self.audio_metrics}

# --- UIクラス ---
class EditorWindow(QMainWindow):
    def __init__(self, video_name, json_name=None):
        super().__init__()
        self.video_name = video_name
        self.json_name = json_name
        self.processor = VideoProcessor(video_name)
        self.total_frames = len(self.processor.frame_paths)
        self.frame_times = self.processor.frame_times

        if self.total_frames == 0:
            QMessageBox.critical(self, "エラー", "フレームが生成されませんでした。")
            sys.exit(1)

        self.current_idx = 0
        self.timeline_data = [FrameData() for _ in range(self.total_frames)]

        json_path = self._get_json_path()
        if os.path.exists(json_path):
            self.load_existing_json(json_path)

        self.is_playing = False
        self.is_comment_mode = False
        self.play_timer = QTimer()
        self.play_timer.timeout.connect(self.play_next_frame)

        self.initUI()
        self.update_display()
        self.setFocus()

    def initUI(self):
        self.setWindowTitle(f"4DX Editor [v3] - {os.path.basename(self.video_name)}")
        self.setGeometry(100, 100, 1280, 850)
        self.setStyleSheet("background-color: #222; color: #EEE; font-family: 'Yu Gothic', 'Meiryo', sans-serif;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. 画像
        self.image_label = QLabel("Loading...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(640, 360)
        self.image_label.setStyleSheet("border: 2px solid #555; background-color: #000;")
        main_layout.addWidget(self.image_label, stretch=3)

        # 2. シークバー
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, self.total_frames - 1)
        self.slider.setValue(0)
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 8px; background: #444; border-radius: 4px; }
            QSlider::handle:horizontal { background: cyan; width: 16px; margin: -4px 0; border-radius: 8px; }
        """)
        self.slider.valueChanged.connect(self.slider_moved)
        main_layout.addWidget(self.slider)

        # 3. コメント
        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("キャプション... (Enter/↑で確定, Escでキャンセル)")
        self.comment_input.setStyleSheet("background-color: #EEE; color: #000; font-size: 18px; padding: 5px;")
        self.comment_input.hide()
        main_layout.addWidget(self.comment_input)

        # 4. オーディオ分析メーター
        audio_panel = QFrame()
        audio_panel.setStyleSheet("background-color: #111; border: 1px solid #444; border-radius: 3px;")
        audio_layout = QGridLayout(audio_panel)
        audio_layout.setContentsMargins(5, 5, 5, 5)

        lbl_style = "font-size: 12px; color: #AAA;"

        self.lbl_vol = QLabel("0")
        self.lbl_bass = QLabel("0")
        self.lbl_high = QLabel("0")
        self.lbl_atk = QLabel("0")

        audio_layout.addWidget(QLabel("音量(Vol)", styleSheet=lbl_style), 0, 0)
        audio_layout.addWidget(self.lbl_vol, 0, 1)
        audio_layout.addWidget(QLabel("重低音(Bass)", styleSheet=lbl_style), 0, 2)
        audio_layout.addWidget(self.lbl_bass, 0, 3)
        audio_layout.addWidget(QLabel("高音(High)", styleSheet=lbl_style), 0, 4)
        audio_layout.addWidget(self.lbl_high, 0, 5)
        audio_layout.addWidget(QLabel("衝撃(Attack)", styleSheet=lbl_style), 0, 6)
        audio_layout.addWidget(self.lbl_atk, 0, 7)

        main_layout.addWidget(audio_panel)

        # 5. ダッシュボード
        dashboard = QFrame()
        dashboard.setStyleSheet("background-color: #333; border-radius: 5px;")
        dash_layout = QGridLayout(dashboard)

        label_style = "font-weight: bold; font-size: 14px; color: #AAA;"
        value_style = "font-weight: bold; font-size: 16px; color: #FFF;"

        self.lbl_time = QLabel("00:00.00")
        self.lbl_time.setStyleSheet("font-size: 24px; color: cyan;")
        dash_layout.addWidget(QLabel("時間:", styleSheet=label_style), 0, 0)
        dash_layout.addWidget(self.lbl_time, 0, 1)

        self.lbl_caption_disp = QLabel("")
        self.lbl_caption_disp.setStyleSheet("color: yellow; font-size: 18px; font-weight: bold;")
        dash_layout.addWidget(QLabel("キャプション:", styleSheet=label_style), 0, 2)
        dash_layout.addWidget(self.lbl_caption_disp, 0, 3, 1, 4)

        self.status_labels = {}
        def add_stat(row, col, key, title, width=1):
            l_title = QLabel(title)
            l_title.setStyleSheet(label_style)
            l_val = QLabel("OFF")
            l_val.setStyleSheet(value_style)
            dash_layout.addWidget(l_title, row, col)
            dash_layout.addWidget(l_val, row, col+1, 1, width)
            self.status_labels[key] = l_val

        add_stat(1, 0, "wind", "風 [W]")
        add_stat(1, 2, "water", "水 [M]")
        add_stat(1, 4, "mist", "ミスト [F]")
        add_stat(2, 0, "flash", "光 [P]")
        add_stat(2, 2, "color", "色 [1-9,0,-,^]")
        add_stat(3, 0, "vib_up", "振動UP [Z/X/C/V]")
        add_stat(3, 2, "vib_down", "振動DOWN [A/S/D/G]")
        add_stat(3, 4, "vib_updown", "上下同時 [Shift+Z/X/C/V]")
        add_stat(4, 0, "vib_heart", "心臓 [H]")
        main_layout.addWidget(dashboard, stretch=2)

        # 6. ヘルプ
        help_text = (
            "<b>[←/→]</b>: 移動 | <b>[Shift+←/→]</b>: 10コマ移動 | <b>[PgUp/PgDn]</b>: 1秒移動<br>"
            "<b>[↓]</b>: 再生/停止 | <b>[R]</b>: 最初から | <b>[Enter/Ctrl+S]</b>: 保存<br>"
            "<b>[W]</b>: 風 | <b>[M]</b>: 水(開始/停止) | <b>[Shift+M]</b>: 水(一瞬)<br>"
            "<b>[F]</b>: ミスト(開始/停止) | <b>[Shift+F]</b>: ミスト(一瞬)<br>"
            "<b>[Z/X/C/V]</b>: 背中(弱/中弱/中強/強) | <b>[A/S/D/G]</b>: お尻(弱/中弱/中強/強)<br>"
            "<b>[Shift+Z/X/C/V]</b>: 上下同時(弱/中弱/中強/強) | <b>[H]</b>: ドキドキ<br>"
            "<b>[1-9, 0, -]</b>: 色選択 | <b>[^]</b>: 色OFF | <b>[P]</b>: 光切替 | <b>[Space]</b>: 効果OFF<br>"
            "※自動フィル: 変更操作をすると、次に設定が変わるフレームの手前まで一括適用されます"
        )
        lbl_help = QLabel(help_text)
        lbl_help.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_help.setStyleSheet("color: #888; font-size: 12px;")
        main_layout.addWidget(lbl_help)

    def load_existing_json(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            events = data.get("events", [])
            self._apply_events_to_frames(events)
            print("JSONデータをロードしました。")
        except Exception as e:
            print(f"JSON読み込みエラー: {e}")

    def _get_json_path(self):
        if not self.json_name:
            base = os.path.splitext(os.path.basename(self.video_name))[0]
            self.json_name = f"{base}_timeline.json"
        json_path = os.path.join(EDITOR_RESULTS_DIR, self.json_name)
        if not json_path.endswith('.json'):
            json_path += ".json"
        return json_path

    def _apply_events_to_frames(self, events):
        events = sorted(events, key=lambda e: e.get("t", 0))
        active_effects = set()
        current_caption = ""
        event_idx = 0

        # shotイベントは最も近いフレームに割り当てる
        shot_map = {}
        for ev in events:
            if ev.get("action") == "shot" and ev.get("effect") in ("water", "mist"):
                t = ev.get("t", 0)
                idx = self._find_nearest_frame_index(t)
                idx = max(0, min(self.total_frames - 1, idx))
                shot_map.setdefault(idx, set()).add(ev.get("effect"))

        for i in range(self.total_frames):
            t = self.frame_times[i] if i < len(self.frame_times) else i * FRAME_INTERVAL
            while event_idx < len(events) and events[event_idx].get("t", 0) <= t + 1e-6:
                ev = events[event_idx]
                action = ev.get("action")
                if action == "caption":
                    current_caption = ev.get("text", "")
                elif action == "start":
                    effect = ev.get("effect")
                    mode = ev.get("mode")
                    # 色/光/風/LEDは同種の効果を上書き
                    if effect in ("color", "flash", "wind", "led_strength", "led_transition"):
                        active_effects = {e for e in active_effects if e[0] != effect}
                    active_effects.add((effect, mode))
                elif action == "stop":
                    effect = ev.get("effect")
                    mode = ev.get("mode")
                    if (effect, mode) in active_effects:
                        active_effects.remove((effect, mode))
                event_idx += 1

            d = self.timeline_data[i]
            d.caption = current_caption
            d.wind = ("wind", "burst") in active_effects
            d.flash = next((m for (e, m) in active_effects if e == "flash"), None)
            d.color = next((m for (e, m) in active_effects if e == "color"), None)
            d.vibration = {m for (e, m) in active_effects if e == "vibration"}
            d.water = "water" in shot_map.get(i, set())
            d.mist = "mist" in shot_map.get(i, set())
            d.water_on = any(e == "water" for (e, _m) in active_effects)
            d.mist_on = any(e == "mist" for (e, _m) in active_effects)
            d.led_strength = next((m for (e, m) in active_effects if e == "led_strength"), None)
            d.led_transition = next((m for (e, m) in active_effects if e == "led_transition"), None)

    def get_current_data(self):
        return self.timeline_data[self.current_idx]

    def slider_moved(self, val):
        self.current_idx = val
        self.update_display(update_slider=False)
        self.setFocus()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_display(update_slider=False)

    def update_display(self, update_slider=True):
        if update_slider:
            self.slider.blockSignals(True)
            self.slider.setValue(self.current_idx)
            self.slider.blockSignals(False)

        if 0 <= self.current_idx < len(self.processor.frame_paths):
            path = self.processor.frame_paths[self.current_idx]
            pixmap = QPixmap(path)
            if pixmap.isNull():
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    pixmap.loadFromData(data)
                except Exception:
                    pass
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

        def get_metric(name):
            if self.current_idx < len(self.processor.audio_metrics[name]):
                return self.processor.audio_metrics[name][self.current_idx]
            return 0.0

        def make_bar(val):
            bars = int(val / 10)
            text = f"{int(val):3d} " + "|" * bars
            return text

        vol = get_metric("volume")
        self.lbl_vol.setText(make_bar(vol))
        self.lbl_vol.setStyleSheet("color: #00FF00; font-weight: bold;")

        bass = get_metric("bass")
        self.lbl_bass.setText(make_bar(bass))
        self.lbl_bass.setStyleSheet("color: #FFA500; font-weight: bold;")

        high = get_metric("high")
        self.lbl_high.setText(make_bar(high))
        self.lbl_high.setStyleSheet("color: #00FFFF; font-weight: bold;")

        atk = get_metric("attack")
        self.lbl_atk.setText(make_bar(atk * 5))
        self.lbl_atk.setStyleSheet("color: #FF4444; font-weight: bold;")

        d = self.get_current_data()
        t = self.frame_times[self.current_idx] if self.current_idx < len(self.frame_times) else self.current_idx * FRAME_INTERVAL
        self.lbl_time.setText(f"{int(t//60):02d}:{t%60:05.2f}")
        self.lbl_caption_disp.setText(d.caption)

        def set_lbl(key, text, active=False, color="white"):
            lbl = self.status_labels[key]
            lbl.setText(text)
            lbl.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {color if active else '#555'};")

        set_lbl("wind", "ON" if d.wind else "OFF", d.wind, "cyan")
        if d.water_on:
            set_lbl("water", "ON", True, "blue")
        elif d.water:
            set_lbl("water", "発射!", True, "blue")
        else:
            set_lbl("water", "OFF", False)
        if d.mist_on:
            set_lbl("mist", "ON", True, "#AAA")
        elif d.mist:
            set_lbl("mist", "発射!", True, "#AAA")
        else:
            set_lbl("mist", "OFF", False)

        flash_txt = FLASH_LABELS.get(d.flash, "OFF")
        set_lbl("flash", flash_txt, d.flash is not None, "yellow")

        if d.color:
            color_label = COLOR_LABELS.get(d.color, d.color)
            rgb = COLOR_RGB.get(d.color, (255, 255, 255))
            ui_color = f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"
            set_lbl("color", color_label, True, ui_color)
        else:
            set_lbl("color", "OFF", False)

        up = get_vib_group_level(d.vibration, "up")
        down = get_vib_group_level(d.vibration, "down")
        updown = get_vib_group_level(d.vibration, "up_down")
        heartbeat = "heartbeat" in d.vibration

        set_lbl("vib_up", format_vib_mode(up), up is not None, "orange")
        set_lbl("vib_down", format_vib_mode(down), down is not None, "orange")
        set_lbl("vib_updown", format_vib_mode(updown), updown is not None, "orange")
        set_lbl("vib_heart", "ドキドキ" if heartbeat else "OFF", heartbeat, "red")

    # --- 伝播ロジック ---
    def propagate_value(self, attr_name, old_val, new_val):
        for i in range(self.current_idx + 1, self.total_frames):
            frame = self.timeline_data[i]
            current_val = getattr(frame, attr_name)
            if current_val != old_val:
                break
            setattr(frame, attr_name, new_val)

    def propagate_vibration_group(self, group, old_mode, new_mode):
        for i in range(self.current_idx + 1, self.total_frames):
            frame = self.timeline_data[i]
            current_mode = get_vib_group_level(frame.vibration, group)
            if current_mode != old_mode:
                break
            apply_vib_group(frame.vibration, group, new_mode)

    # --- アクション ---
    def toggle_wind(self):
        d = self.get_current_data()
        old_val = d.wind
        new_val = not d.wind
        d.wind = new_val
        self.propagate_value("wind", old_val, new_val)
        self.update_display()

    def toggle_stream(self, effect_name):
        d = self.get_current_data()
        if effect_name == "water":
            old_val = d.water_on
            new_val = not d.water_on
            d.water_on = new_val
            self.propagate_value("water_on", old_val, new_val)
        elif effect_name == "mist":
            old_val = d.mist_on
            new_val = not d.mist_on
            d.mist_on = new_val
            self.propagate_value("mist_on", old_val, new_val)
        self.update_display()

    def toggle_shot(self, effect_name):
        d = self.get_current_data()
        if effect_name == "water":
            d.water = not d.water
        elif effect_name == "mist":
            d.mist = not d.mist
        self.update_display()

    def cycle_flash(self, reverse=False):
        d = self.get_current_data()
        old_val = d.flash
        idx = FLASH_MODES.index(old_val) if old_val in FLASH_MODES else 0
        step = -1 if reverse else 1
        new_val = FLASH_MODES[(idx + step) % len(FLASH_MODES)]
        d.flash = new_val
        self.propagate_value("flash", old_val, new_val)
        self.update_display()

    def set_color_key(self, idx):
        d = self.get_current_data()
        old_val = d.color
        new_val = COLOR_KEYS[idx] if idx is not None and 0 <= idx < len(COLOR_KEYS) else None
        d.color = new_val
        self.propagate_value("color", old_val, new_val)
        self.update_display()

    def toggle_vibration_group(self, group, mode):
        d = self.get_current_data()
        old_mode = get_vib_group_level(d.vibration, group)
        new_mode = None if mode == old_mode else mode

        # 現フレームに反映
        apply_vib_group(d.vibration, group, new_mode)
        self.propagate_vibration_group(group, old_mode, new_mode)

        # 競合の解消（up/down と up_down は排他）
        if group in ("up", "down") and get_vib_group_level(d.vibration, "up_down"):
            old_ud = get_vib_group_level(d.vibration, "up_down")
            apply_vib_group(d.vibration, "up_down", None)
            self.propagate_vibration_group("up_down", old_ud, None)
        if group == "up_down":
            old_up = get_vib_group_level(d.vibration, "up")
            old_down = get_vib_group_level(d.vibration, "down")
            if old_up:
                apply_vib_group(d.vibration, "up", None)
                self.propagate_vibration_group("up", old_up, None)
            if old_down:
                apply_vib_group(d.vibration, "down", None)
                self.propagate_vibration_group("down", old_down, None)

        self.update_display()

    def toggle_heartbeat(self):
        d = self.get_current_data()
        old_mode = "heartbeat" if "heartbeat" in d.vibration else None
        new_mode = None if old_mode else "heartbeat"
        if old_mode:
            d.vibration.remove("heartbeat")
        else:
            d.vibration.add("heartbeat")
        self.propagate_vibration_group("heartbeat", old_mode, new_mode)
        self.update_display()

    def clear_effects(self):
        d = self.get_current_data()
        d.wind = False
        d.water = False
        d.water_on = False
        d.mist = False
        d.mist_on = False
        d.led_strength = None
        d.led_transition = None
        d.vibration = set()
        d.flash = None
        d.color = None
        self.update_display()

    def jump_frames(self, delta):
        self.current_idx = max(0, min(self.total_frames - 1, self.current_idx + delta))
        self.update_display()

    def seek_by_seconds(self, delta_seconds):
        if not self.frame_times:
            self.jump_frames(int(delta_seconds / FRAME_INTERVAL))
            return
        current_time = self.frame_times[self.current_idx]
        target_time = current_time + delta_seconds
        idx = self._find_nearest_frame_index(target_time)
        self.current_idx = max(0, min(self.total_frames - 1, idx))
        self.update_display()

    def keyPressEvent(self, event):
        if self.is_comment_mode:
            if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.get_current_data().caption = self.comment_input.text()
                self.comment_input.hide()
                self.setFocus()
                self.is_comment_mode = False
                self.update_display()
            elif event.key() == Qt.Key.Key_Escape:
                self.comment_input.hide()
                self.setFocus()
                self.is_comment_mode = False
            return

        key = event.key()
        mods = event.modifiers()

        if key == Qt.Key.Key_Right:
            self.jump_frames(10 if mods & Qt.KeyboardModifier.ShiftModifier else 1)
        elif key == Qt.Key.Key_Left:
            self.jump_frames(-10 if mods & Qt.KeyboardModifier.ShiftModifier else -1)
        elif key == Qt.Key.Key_PageDown:
            self.seek_by_seconds(1.0)
        elif key == Qt.Key.Key_PageUp:
            self.seek_by_seconds(-1.0)
        elif key == Qt.Key.Key_Home:
            self.current_idx = 0
            self.update_display()
        elif key == Qt.Key.Key_End:
            self.current_idx = self.total_frames - 1
            self.update_display()
        elif key == Qt.Key.Key_Down:
            if not self.is_playing:
                self.start_preview()
            else:
                self.stop_preview()
        elif key == Qt.Key.Key_Up:
            self.is_comment_mode = True
            self.comment_input.setText(self.get_current_data().caption)
            self.comment_input.show()
            self.comment_input.setFocus()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.save_json()
        elif key == Qt.Key.Key_S and mods & Qt.KeyboardModifier.ControlModifier:
            self.save_json()
        elif key == Qt.Key.Key_R:
            self.current_idx = 0
            self.update_display()
        elif key == Qt.Key.Key_W:
            self.toggle_wind()
        elif key == Qt.Key.Key_M and mods & Qt.KeyboardModifier.ShiftModifier:
            self.toggle_shot("water")
        elif key == Qt.Key.Key_M:
            self.toggle_stream("water")
        elif key == Qt.Key.Key_F and mods & Qt.KeyboardModifier.ShiftModifier:
            self.toggle_shot("mist")
        elif key == Qt.Key.Key_F:
            self.toggle_stream("mist")
        elif key == Qt.Key.Key_Z and mods & Qt.KeyboardModifier.ShiftModifier:
            self.toggle_vibration_group("up_down", "up_down_weak")
        elif key == Qt.Key.Key_X and mods & Qt.KeyboardModifier.ShiftModifier:
            self.toggle_vibration_group("up_down", "up_down_mid_weak")
        elif key == Qt.Key.Key_C and mods & Qt.KeyboardModifier.ShiftModifier:
            self.toggle_vibration_group("up_down", "up_down_mid_strong")
        elif key == Qt.Key.Key_V and mods & Qt.KeyboardModifier.ShiftModifier:
            self.toggle_vibration_group("up_down", "up_down_strong")
        elif key == Qt.Key.Key_Z:
            self.toggle_vibration_group("up", "up_weak")
        elif key == Qt.Key.Key_X:
            self.toggle_vibration_group("up", "up_mid_weak")
        elif key == Qt.Key.Key_C:
            self.toggle_vibration_group("up", "up_mid_strong")
        elif key == Qt.Key.Key_V:
            self.toggle_vibration_group("up", "up_strong")
        elif key == Qt.Key.Key_A:
            self.toggle_vibration_group("down", "down_weak")
        elif key == Qt.Key.Key_S:
            self.toggle_vibration_group("down", "down_mid_weak")
        elif key == Qt.Key.Key_D:
            self.toggle_vibration_group("down", "down_mid_strong")
        elif key == Qt.Key.Key_G:
            self.toggle_vibration_group("down", "down_strong")
        elif key == Qt.Key.Key_H:
            self.toggle_heartbeat()
        elif key == Qt.Key.Key_1:
            self.set_color_key(0)
        elif key == Qt.Key.Key_2:
            self.set_color_key(1)
        elif key == Qt.Key.Key_3:
            self.set_color_key(2)
        elif key == Qt.Key.Key_4:
            self.set_color_key(3)
        elif key == Qt.Key.Key_5:
            self.set_color_key(4)
        elif key == Qt.Key.Key_6:
            self.set_color_key(5)
        elif key == Qt.Key.Key_7:
            self.set_color_key(6)
        elif key == Qt.Key.Key_8:
            self.set_color_key(7)
        elif key == Qt.Key.Key_9:
            self.set_color_key(8)
        elif key == Qt.Key.Key_0:
            self.set_color_key(9)
        elif key == Qt.Key.Key_Minus:
            self.set_color_key(10)
        elif key in (Qt.Key.Key_AsciiCircum, Qt.Key.Key_Backslash, Qt.Key.Key_BracketRight, Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self.set_color_key(None)
        elif key == Qt.Key.Key_P:
            self.cycle_flash(reverse=bool(mods & Qt.KeyboardModifier.ShiftModifier))
        elif key == Qt.Key.Key_Space:
            self.clear_effects()

    def start_preview(self):
        self.is_playing = True
        self.play_timer.start(int(self.processor.frame_interval * 1000))

    def stop_preview(self):
        self.is_playing = False
        self.play_timer.stop()

    def play_next_frame(self):
        if self.current_idx < self.total_frames - 1:
            self.current_idx += 1
            self.update_display()
        else:
            self.stop_preview()

    def _build_events(self):
        events = []
        prev_caption = None
        prev_effects = set()

        for i, d in enumerate(self.timeline_data):
            t = round(self.frame_times[i] if i < len(self.frame_times) else i * FRAME_INTERVAL, 3)

            if d.caption and d.caption != prev_caption:
                events.append({"t": t, "action": "caption", "text": d.caption})
                prev_caption = d.caption

            # shot系
            if d.water:
                events.append({"t": t, "action": "shot", "effect": "water", "mode": "burst"})
            if d.mist:
                events.append({"t": t, "action": "shot", "effect": "mist", "mode": "burst"})

            curr_effects = set()
            if d.wind:
                curr_effects.add(("wind", "burst"))
            if d.water_on:
                curr_effects.add(("water", "stream"))
            if d.mist_on:
                curr_effects.add(("mist", "stream"))
            if d.flash:
                curr_effects.add(("flash", d.flash))
            if d.color:
                curr_effects.add(("color", d.color))
            if d.led_strength:
                curr_effects.add(("led_strength", d.led_strength))
            if d.led_transition:
                curr_effects.add(("led_transition", d.led_transition))
            for v in d.vibration:
                curr_effects.add(("vibration", v))

            stops = sorted(prev_effects - curr_effects)
            starts = sorted(curr_effects - prev_effects)

            for eff, mode in stops:
                events.append({"t": t, "action": "stop", "effect": eff, "mode": mode})
            for eff, mode in starts:
                events.append({"t": t, "action": "start", "effect": eff, "mode": mode})

            prev_effects = curr_effects

        # 最後に残っている効果は停止
        if prev_effects:
            last_time = self.frame_times[-1] if self.frame_times else (self.total_frames - 1) * FRAME_INTERVAL
            end_t = round(last_time + 0.1, 3)
            for eff, mode in sorted(prev_effects):
                events.append({"t": end_t, "action": "stop", "effect": eff, "mode": mode})

        return events

    def _find_nearest_frame_index(self, t):
        if not self.frame_times:
            return int(round(t / FRAME_INTERVAL))
        idx = bisect.bisect_left(self.frame_times, t)
        if idx <= 0:
            return 0
        if idx >= len(self.frame_times):
            return len(self.frame_times) - 1
        before = self.frame_times[idx - 1]
        after = self.frame_times[idx]
        return idx - 1 if abs(t - before) <= abs(after - t) else idx

    def save_json(self):
        save_path = self._get_json_path()

        os.makedirs(EDITOR_RESULTS_DIR, exist_ok=True)
        output = {"events": self._build_events()}
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        QMessageBox.information(self, "保存完了", f"JSONファイルを保存しました:\n{save_path}")

# --- ヘルパー ---
def get_vib_group_level(vib_set, group):
    for mode in VIB_GROUPS.get(group, []):
        if mode in vib_set:
            return mode
    return None

def apply_vib_group(vib_set, group, new_mode):
    for mode in VIB_GROUPS.get(group, []):
        if mode in vib_set:
            vib_set.remove(mode)
    if new_mode:
        vib_set.add(new_mode)

def format_vib_mode(mode):
    if not mode:
        return "OFF"
    if mode == "heartbeat":
        return VIB_LABELS["heartbeat"]
    parts = mode.split("_")
    intensity = "_".join(parts[1:]) if len(parts) > 1 else ""
    return VIB_LABELS.get(intensity, mode)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    print("--- 4DX Editor [v3] Launcher ---")

    # 動画選択
    video_in = ""
    if len(sys.argv) >= 2:
        video_in = sys.argv[1].strip()
    else:
        print("動画ファイル名 (videosフォルダ内) を入力してください。")
        video_in = input("動画ファイル名: ").strip()

    if not video_in:
        sys.exit()

    # 保存JSON名（任意）
    json_in = ""
    if len(sys.argv) >= 3:
        json_in = sys.argv[2].strip()
    else:
        json_in = input("保存JSON名 (空でデフォルト): ").strip()

    window = EditorWindow(video_in, json_in if json_in else None)
    window.show()
    sys.exit(app.exec())
