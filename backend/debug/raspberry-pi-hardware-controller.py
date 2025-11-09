#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4DX@HOME ハードウェア制御モジュール
GPIO制御とArduino通信による実際のアクチュエーター制御

Author: 4DX@HOME Team  
Date: 2025-10-12
"""

import asyncio
import json
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import serial

# ハードウェア制御用ライブラリ（ラズベリーパイ環境でのみ利用可能）
try:
    import RPi.GPIO as GPIO
    from gpiozero import PWMOutputDevice, LED, Servo
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("⚠️ GPIO ライブラリが利用できません（開発環境）")

# ===============================
# ハードウェア設定
# ===============================

@dataclass
class ActuatorConfig:
    """アクチュエーター設定"""
    pin: int
    pwm_frequency: int = 1000
    is_pwm: bool = True
    is_relay: bool = False
    inverted: bool = False

@dataclass
class HardwareConfig:
    """ハードウェア全体設定"""
    # GPIO ピンアサイン
    actuators: Dict[str, ActuatorConfig] = None
    
    # Arduino Serial通信
    arduino_port: str = "/dev/ttyACM0"
    arduino_baudrate: int = 115200
    arduino_timeout: float = 0.1
    
    # PWM設定
    pwm_range: int = 100
    
    def __post_init__(self):
        if self.actuators is None:
            self.actuators = {
                "VIBRATION": ActuatorConfig(pin=18, pwm_frequency=1000, is_pwm=True),
                "WATER": ActuatorConfig(pin=23, is_relay=True, is_pwm=False),
                "WIND": ActuatorConfig(pin=24, pwm_frequency=25000, is_pwm=True),
                "FLASH": ActuatorConfig(pin=25, pwm_frequency=5000, is_pwm=True),
                "COLOR_R": ActuatorConfig(pin=12, pwm_frequency=2000, is_pwm=True),
                "COLOR_G": ActuatorConfig(pin=13, pwm_frequency=2000, is_pwm=True),
                "COLOR_B": ActuatorConfig(pin=19, pwm_frequency=2000, is_pwm=True),
            }

class ActuatorType(str, Enum):
    """アクチュエータータイプ"""
    VIBRATION = "VIBRATION"
    WATER = "WATER"
    WIND = "WIND"
    FLASH = "FLASH"
    COLOR = "COLOR"

# ===============================
# ハードウェア制御クラス
# ===============================

class HardwareController:
    """ハードウェア制御メインクラス"""
    
    def __init__(self, config: HardwareConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        
        # GPIO制御オブジェクト
        self.pwm_devices: Dict[str, PWMOutputDevice] = {}
        self.relay_devices: Dict[str, LED] = {}
        
        # Arduino通信
        self.arduino_serial: Optional[serial.Serial] = None
        
        # 状態管理
        self.is_initialized = False
        self.active_effects: Dict[str, asyncio.Task] = {}
        
        self.logger.info("🔧 ハードウェアコントローラー初期化開始")

    async def initialize(self) -> bool:
        """ハードウェア初期化"""
        try:
            # GPIO初期化
            if not await self._initialize_gpio():
                return False
            
            # Arduino接続
            if not await self._initialize_arduino():
                self.logger.warning("⚠️ Arduino接続失敗（GPIO制御のみ使用）")
            
            self.is_initialized = True
            self.logger.info("✅ ハードウェア初期化完了")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ ハードウェア初期化エラー: {e}")
            return False

    async def _initialize_gpio(self) -> bool:
        """GPIO初期化"""
        if not GPIO_AVAILABLE:
            self.logger.warning("⚠️ GPIO制御無効（開発環境）")
            return True
        
        try:
            self.logger.info("🔌 GPIO初期化開始")
            
            # GPIO設定
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # 各アクチュエーター初期化
            for actuator_name, config in self.config.actuators.items():
                if config.is_pwm:
                    # PWM制御デバイス
                    device = PWMOutputDevice(
                        config.pin,
                        frequency=config.pwm_frequency,
                        initial_value=0.0
                    )
                    self.pwm_devices[actuator_name] = device
                    
                    self.logger.debug(f"🔸 PWM初期化: {actuator_name} -> Pin{config.pin} "
                                    f"({config.pwm_frequency}Hz)")
                
                elif config.is_relay:
                    # リレー制御デバイス
                    device = LED(config.pin)
                    device.off()  # 初期状態はOFF
                    self.relay_devices[actuator_name] = device
                    
                    self.logger.debug(f"🔸 リレー初期化: {actuator_name} -> Pin{config.pin}")
            
            self.logger.info(f"✅ GPIO初期化完了: PWM={len(self.pwm_devices)}, "
                           f"リレー={len(self.relay_devices)}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ GPIO初期化エラー: {e}")
            return False

    async def _initialize_arduino(self) -> bool:
        """Arduino Serial通信初期化"""
        try:
            self.logger.info(f"🔗 Arduino接続開始: {self.config.arduino_port}")
            
            self.arduino_serial = serial.Serial(
                port=self.config.arduino_port,
                baudrate=self.config.arduino_baudrate,
                timeout=self.config.arduino_timeout,
                write_timeout=self.config.arduino_timeout
            )
            
            # 接続テスト
            if await self._arduino_ping():
                self.logger.info("✅ Arduino接続成功")
                return True
            else:
                self.logger.error("❌ Arduino ping失敗")
                return False
                
        except serial.SerialException as e:
            self.logger.error(f"❌ Arduino接続エラー: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Arduino初期化エラー: {e}")
            return False

    async def _arduino_ping(self) -> bool:
        """Arduino接続テスト"""
        if not self.arduino_serial:
            return False
        
        try:
            # Pingコマンド送信
            ping_command = {"command": "ping", "timestamp": time.time()}
            await self._send_arduino_command(ping_command)
            
            # レスポンス待機
            response = await self._receive_arduino_response(timeout=1.0)
            
            if response and response.get("status") == "pong":
                return True
                
        except Exception as e:
            self.logger.debug(f"Arduino ping エラー: {e}")
        
        return False

    async def execute_effect(self, actuator: str, intensity: float, duration: float, pattern: str) -> Dict[str, Any]:
        """エフェクト実行メイン"""
        if not self.is_initialized:
            raise RuntimeError("ハードウェアが初期化されていません")
        
        start_time = time.time()
        actuator_upper = actuator.upper()
        
        self.logger.info(f"⚡ エフェクト実行開始: {actuator_upper} 強度={intensity:.1%} "
                        f"時間={duration:.2f}s パターン={pattern}")
        
        try:
            # 既存のエフェクトを停止
            await self._stop_actuator(actuator_upper)
            
            # エフェクト実行
            if actuator_upper == ActuatorType.VIBRATION:
                result = await self._control_vibration(intensity, duration, pattern)
            elif actuator_upper == ActuatorType.WATER:
                result = await self._control_water(intensity, duration, pattern)
            elif actuator_upper == ActuatorType.WIND:
                result = await self._control_wind(intensity, duration, pattern)
            elif actuator_upper == ActuatorType.FLASH:
                result = await self._control_flash(intensity, duration, pattern)
            elif actuator_upper == ActuatorType.COLOR:
                result = await self._control_color(intensity, duration, pattern)
            else:
                raise ValueError(f"未対応のアクチュエーター: {actuator_upper}")
            
            execution_time = (time.time() - start_time) * 1000
            
            self.logger.info(f"✅ エフェクト実行完了: {actuator_upper} ({execution_time:.1f}ms)")
            
            return {
                "actuator": actuator_upper,
                "intensity": intensity,
                "duration": duration,
                "pattern": pattern,
                "execution_time_ms": execution_time,
                "status": "completed",
                "result": result
            }
            
        except Exception as e:
            self.logger.error(f"❌ エフェクト実行エラー ({actuator_upper}): {e}")
            return {
                "actuator": actuator_upper,
                "status": "error", 
                "error": str(e)
            }

    async def _control_vibration(self, intensity: float, duration: float, pattern: str) -> Dict[str, Any]:
        """振動制御"""
        self.logger.debug(f"🔸 振動制御: 強度={intensity:.1%}, パターン={pattern}")
        
        if GPIO_AVAILABLE and "VIBRATION" in self.pwm_devices:
            pwm_device = self.pwm_devices["VIBRATION"]
            
            if pattern == "pulse":
                # パルス振動
                await self._pulse_effect(pwm_device, intensity, duration, frequency=10)
            elif pattern == "heartbeat":
                # ハートビート振動
                await self._heartbeat_effect(pwm_device, intensity, duration)
            elif pattern in ["strong", "steady", "continuous"]:
                # 連続振動
                pwm_device.value = intensity
                await asyncio.sleep(duration)
                pwm_device.value = 0.0
            else:
                # デフォルト振動
                pwm_device.value = intensity * 0.8  # 少し弱めに
                await asyncio.sleep(duration)
                pwm_device.value = 0.0
        
        # Arduino制御も並行実行
        arduino_result = await self._send_actuator_command("VIBRATION", intensity, duration, pattern)
        
        return {
            "gpio_control": GPIO_AVAILABLE,
            "arduino_control": arduino_result is not None,
            "pattern_applied": pattern
        }

    async def _control_water(self, intensity: float, duration: float, pattern: str) -> Dict[str, Any]:
        """水噴射制御"""
        self.logger.debug(f"💧 水制御: 強度={intensity:.1%}, 時間={duration:.2f}s")
        
        if GPIO_AVAILABLE and "WATER" in self.relay_devices:
            relay_device = self.relay_devices["WATER"]
            
            if pattern == "shot":
                # 短時間噴射
                relay_device.on()
                await asyncio.sleep(min(duration, 0.5))  # 最大0.5秒
                relay_device.off()
            elif pattern == "pulse":
                # パルス噴射
                pulse_count = int(duration * 2)  # 0.5秒間隔
                for _ in range(pulse_count):
                    relay_device.on()
                    await asyncio.sleep(0.1)
                    relay_device.off()
                    await asyncio.sleep(0.4)
            else:
                # 通常噴射（強度に応じてデューティ比調整）
                on_time = 0.1 * intensity
                off_time = 0.1 * (1.0 - intensity)
                
                cycles = int(duration / (on_time + off_time))
                for _ in range(cycles):
                    relay_device.on()
                    await asyncio.sleep(on_time)
                    relay_device.off()
                    await asyncio.sleep(off_time)
        
        # Arduino制御
        arduino_result = await self._send_actuator_command("WATER", intensity, duration, pattern)
        
        return {
            "gpio_control": GPIO_AVAILABLE,
            "arduino_control": arduino_result is not None
        }

    async def _control_wind(self, intensity: float, duration: float, pattern: str) -> Dict[str, Any]:
        """ファン制御"""
        self.logger.debug(f"💨 ファン制御: 強度={intensity:.1%}, パターン={pattern}")
        
        if GPIO_AVAILABLE and "WIND" in self.pwm_devices:
            pwm_device = self.pwm_devices["WIND"]
            
            if pattern == "gust":
                # 突風効果
                await self._gust_effect(pwm_device, intensity, duration)
            elif pattern == "wave":
                # 波風効果  
                await self._wave_effect(pwm_device, intensity, duration)
            else:
                # 一定風力
                pwm_device.value = intensity
                await asyncio.sleep(duration)
                pwm_device.value = 0.0
        
        # Arduino制御
        arduino_result = await self._send_actuator_command("WIND", intensity, duration, pattern)
        
        return {
            "gpio_control": GPIO_AVAILABLE,
            "arduino_control": arduino_result is not None,
            "pattern_applied": pattern
        }

    async def _control_flash(self, intensity: float, duration: float, pattern: str) -> Dict[str, Any]:
        """フラッシュ制御"""
        self.logger.debug(f"⚡ フラッシュ制御: 強度={intensity:.1%}, パターン={pattern}")
        
        if GPIO_AVAILABLE and "FLASH" in self.pwm_devices:
            pwm_device = self.pwm_devices["FLASH"]
            
            if pattern == "strobe":
                # ストロボ効果
                await self._strobe_effect(pwm_device, intensity, duration, frequency=20)
            elif pattern == "fade":
                # フェード効果
                await self._fade_effect(pwm_device, intensity, duration)
            elif pattern == "shot":
                # フラッシュショット
                pwm_device.value = intensity
                await asyncio.sleep(min(duration, 0.1))
                pwm_device.value = 0.0
            else:
                # 通常点灯
                pwm_device.value = intensity
                await asyncio.sleep(duration)
                pwm_device.value = 0.0
        
        # Arduino制御
        arduino_result = await self._send_actuator_command("FLASH", intensity, duration, pattern)
        
        return {
            "gpio_control": GPIO_AVAILABLE,
            "arduino_control": arduino_result is not None,
            "pattern_applied": pattern
        }

    async def _control_color(self, intensity: float, duration: float, pattern: str) -> Dict[str, Any]:
        """カラー照明制御"""
        self.logger.debug(f"🎨 カラー制御: 強度={intensity:.1%}, パターン={pattern}")
        
        # RGB値生成（パターンに応じて）
        r, g, b = self._generate_rgb_values(pattern, intensity)
        
        if GPIO_AVAILABLE:
            # RGB各チャンネル制御
            for color, value in [("COLOR_R", r), ("COLOR_G", g), ("COLOR_B", b)]:
                if color in self.pwm_devices:
                    pwm_device = self.pwm_devices[color]
                    pwm_device.value = value
            
            # 持続時間待機
            await asyncio.sleep(duration)
            
            # 消灯
            for color in ["COLOR_R", "COLOR_G", "COLOR_B"]:
                if color in self.pwm_devices:
                    self.pwm_devices[color].value = 0.0
        
        # Arduino制御
        arduino_result = await self._send_color_command(r, g, b, duration, pattern)
        
        return {
            "gpio_control": GPIO_AVAILABLE,
            "arduino_control": arduino_result is not None,
            "rgb_values": {"r": r, "g": g, "b": b},
            "pattern_applied": pattern
        }

    # エフェクトパターン実装
    async def _pulse_effect(self, device, intensity: float, duration: float, frequency: float = 10):
        """パルス効果"""
        cycle_time = 1.0 / frequency
        cycles = int(duration * frequency)
        
        for _ in range(cycles):
            device.value = intensity
            await asyncio.sleep(cycle_time / 2)
            device.value = 0.0
            await asyncio.sleep(cycle_time / 2)

    async def _heartbeat_effect(self, device, intensity: float, duration: float):
        """ハートビート効果"""
        beats_per_minute = 72
        beat_interval = 60.0 / beats_per_minute
        beats = int(duration / beat_interval)
        
        for _ in range(beats):
            # ドクン
            device.value = intensity
            await asyncio.sleep(0.1)
            device.value = 0.0
            await asyncio.sleep(0.1)
            
            # ドクン（より強く）
            device.value = intensity * 1.2
            await asyncio.sleep(0.15)
            device.value = 0.0
            
            # 休止
            await asyncio.sleep(beat_interval - 0.35)

    async def _gust_effect(self, device, intensity: float, duration: float):
        """突風効果"""
        # 急上昇
        steps = 10
        for i in range(steps):
            device.value = intensity * (i / steps)
            await asyncio.sleep(duration * 0.2 / steps)
        
        # 最大風力維持
        device.value = intensity
        await asyncio.sleep(duration * 0.3)
        
        # 急下降
        for i in range(steps, 0, -1):
            device.value = intensity * (i / steps)
            await asyncio.sleep(duration * 0.5 / steps)
        
        device.value = 0.0

    async def _wave_effect(self, device, intensity: float, duration: float):
        """波風効果"""
        waves = 3
        wave_duration = duration / waves
        
        for _ in range(waves):
            # 上昇
            steps = 20
            for i in range(steps):
                value = intensity * 0.5 * (1 + math.sin(math.pi * i / steps - math.pi/2))
                device.value = value
                await asyncio.sleep(wave_duration / steps)

    async def _strobe_effect(self, device, intensity: float, duration: float, frequency: float = 20):
        """ストロボ効果"""
        cycle_time = 1.0 / frequency
        cycles = int(duration * frequency)
        
        for _ in range(cycles):
            device.value = intensity
            await asyncio.sleep(cycle_time * 0.1)  # 短時間点灯
            device.value = 0.0
            await asyncio.sleep(cycle_time * 0.9)  # 長時間消灯

    async def _fade_effect(self, device, intensity: float, duration: float):
        """フェード効果"""
        steps = 50
        half_duration = duration / 2
        
        # フェードイン
        for i in range(steps):
            device.value = intensity * (i / steps)
            await asyncio.sleep(half_duration / steps)
        
        # フェードアウト
        for i in range(steps, 0, -1):
            device.value = intensity * (i / steps)
            await asyncio.sleep(half_duration / steps)
        
        device.value = 0.0

    def _generate_rgb_values(self, pattern: str, intensity: float) -> tuple:
        """パターンに応じたRGB値生成"""
        if pattern == "red":
            return (intensity, 0.0, 0.0)
        elif pattern == "blue":
            return (0.0, 0.0, intensity)
        elif pattern == "green":
            return (0.0, intensity, 0.0)
        elif pattern == "yellow":
            return (intensity, intensity, 0.0)
        elif pattern == "purple":
            return (intensity, 0.0, intensity)
        elif pattern == "white":
            return (intensity, intensity, intensity)
        else:
            # デフォルト（暖色系）
            return (intensity * 0.8, intensity * 0.4, 0.0)

    # Arduino通信メソッド
    async def _send_actuator_command(self, actuator: str, intensity: float, duration: float, pattern: str) -> Optional[Dict]:
        """Arduino アクチュエーター制御コマンド送信"""
        command = {
            "command": "actuator_control",
            "actuator": actuator,
            "intensity": intensity,
            "duration": duration,
            "pattern": pattern,
            "timestamp": time.time()
        }
        
        return await self._send_arduino_command(command)

    async def _send_color_command(self, r: float, g: float, b: float, duration: float, pattern: str) -> Optional[Dict]:
        """Arduino カラー制御コマンド送信"""
        command = {
            "command": "color_control",
            "rgb": {"r": r, "g": g, "b": b},
            "duration": duration,
            "pattern": pattern,
            "timestamp": time.time()
        }
        
        return await self._send_arduino_command(command)

    async def _send_arduino_command(self, command: Dict) -> Optional[Dict]:
        """Arduino コマンド送信（汎用）"""
        if not self.arduino_serial:
            return None
        
        try:
            command_json = json.dumps(command) + "\n"
            self.arduino_serial.write(command_json.encode('utf-8'))
            self.arduino_serial.flush()
            
            self.logger.debug(f"📤 Arduino送信: {command['command']}")
            
            # レスポンス受信
            response = await self._receive_arduino_response()
            return response
            
        except Exception as e:
            self.logger.error(f"❌ Arduino送信エラー: {e}")
            return None

    async def _receive_arduino_response(self, timeout: float = 0.5) -> Optional[Dict]:
        """Arduino レスポンス受信"""
        if not self.arduino_serial:
            return None
        
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.arduino_serial.in_waiting > 0:
                    line = self.arduino_serial.readline().decode('utf-8').strip()
                    if line:
                        response = json.loads(line)
                        self.logger.debug(f"📥 Arduino受信: {response}")
                        return response
                await asyncio.sleep(0.01)
            
            self.logger.debug("Arduino レスポンス タイムアウト")
            return None
            
        except Exception as e:
            self.logger.debug(f"Arduino受信エラー: {e}")
            return None

    async def _stop_actuator(self, actuator: str):
        """アクチュエーター停止"""
        # 既存のタスクを停止
        if actuator in self.active_effects:
            self.active_effects[actuator].cancel()
            del self.active_effects[actuator]
        
        # GPIO デバイス停止
        actuator_upper = actuator.upper()
        
        if actuator_upper in self.pwm_devices:
            self.pwm_devices[actuator_upper].value = 0.0
        
        if actuator_upper in self.relay_devices:
            self.relay_devices[actuator_upper].off()
        
        # RGB個別停止
        if actuator_upper == "COLOR":
            for color in ["COLOR_R", "COLOR_G", "COLOR_B"]:
                if color in self.pwm_devices:
                    self.pwm_devices[color].value = 0.0

    async def stop_all_effects(self):
        """全エフェクト緊急停止"""
        self.logger.info("🛑 全エフェクト緊急停止")
        
        # 全タスクキャンセル
        for task in self.active_effects.values():
            task.cancel()
        self.active_effects.clear()
        
        # 全GPIO デバイス停止
        for device in self.pwm_devices.values():
            device.value = 0.0
        
        for device in self.relay_devices.values():
            device.off()
        
        # Arduino 緊急停止コマンド
        if self.arduino_serial:
            stop_command = {"command": "emergency_stop", "timestamp": time.time()}
            await self._send_arduino_command(stop_command)

    def cleanup(self):
        """リソースクリーンアップ"""
        self.logger.info("🧹 ハードウェア リソースクリーンアップ")
        
        try:
            # GPIO クリーンアップ
            for device in self.pwm_devices.values():
                device.close()
            
            for device in self.relay_devices.values():
                device.close()
            
            if GPIO_AVAILABLE:
                GPIO.cleanup()
            
            # Arduino接続切断
            if self.arduino_serial:
                self.arduino_serial.close()
                
        except Exception as e:
            self.logger.error(f"❌ クリーンアップエラー: {e}")

# ===============================
# 数学関数（パターン効果用）
# ===============================

import math

# ===============================
# テスト用メイン関数
# ===============================

async def test_hardware():
    """ハードウェア制御テスト"""
    import logging
    
    # ログ設定
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("test")
    
    # 設定
    config = HardwareConfig()
    
    # コントローラー作成
    controller = HardwareController(config, logger)
    
    try:
        # 初期化
        if not await controller.initialize():
            logger.error("❌ 初期化失敗")
            return
        
        # テスト実行
        logger.info("🔧 ハードウェアテスト開始")
        
        # 振動テスト
        await controller.execute_effect("VIBRATION", 0.5, 2.0, "pulse")
        await asyncio.sleep(1)
        
        # フラッシュテスト
        await controller.execute_effect("FLASH", 0.8, 1.0, "strobe")
        await asyncio.sleep(1)
        
        # カラーテスト
        await controller.execute_effect("COLOR", 0.6, 3.0, "red")
        
        logger.info("✅ ハードウェアテスト完了")
        
    except KeyboardInterrupt:
        logger.info("🛑 ユーザー停止")
    finally:
        await controller.stop_all_effects()
        controller.cleanup()

if __name__ == "__main__":
    print("🔧 4DX@HOME ハードウェア制御テスト")
    asyncio.run(test_hardware())