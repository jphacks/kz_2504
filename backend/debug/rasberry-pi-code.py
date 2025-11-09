#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import socket
import threading
import time
import subprocess
import paho.mqtt.client as mqtt
import serial # pyserialライブラリを使用
from concurrent.futures import ThreadPoolExecutor
 
# --- グローバル設定 ---
HOST = '127.0.0.1'
PORT = 65432
MAX_WORKERS = 10
 
# --- ハードウェア設定 ---
SERIAL_PORTS = {
    'wind': '/dev/ttyACM2',
    'water': '/dev/ttyACM0',
    'flash': '/dev/ttyACM1'
}
MQTT_HOST = "172.18.28.55"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "raspberrypi_controller"
 
MQTT_TOPICS = {
    'heart': '/vibration/heart',
    'all':   '/vibration/all',
    'off':   '/vibration/off'
}
 
# --- ロジック ---
 
class VibrationController:
    """MQTT経由で振動を制御するクラス"""
    def __init__(self, host, port, client_id):
        self.client = mqtt.Client(client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.is_connected = False
        self.lock = threading.Lock()
       
        try:
            print(f"[MQTT] Connecting to broker at {host}:{port}...")
            self.client.connect(host, port, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"❌ [MQTT] Connection failed: {e}")
 
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✅ [MQTT] Broker connected successfully.")
            self.is_connected = True
        else:
            print(f"❌ [MQTT] Connection failed. Return code: {rc}")
 
    def on_disconnect(self, client, userdata, rc):
        print("⚠️ [MQTT] Disconnected from broker.")
        self.is_connected = False
 
    def control(self, mode, state):
        with self.lock:
            if not self.is_connected:
                # print("❌ [MQTT] Not connected, cannot send command.")
                return
 
            topic = None
            if state == 'off': topic = MQTT_TOPICS['off']
            elif mode == 'heartbeat': topic = MQTT_TOPICS['heart']
            elif mode in ['strong', 'long']: topic = MQTT_TOPICS['all']
 
            if topic: self.client.publish(topic, "", qos=1)
   
    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
        print("[MQTT] Connection closed.")
 
class SerialController:
    """pyserialを使用してシリアルポートを安定して制御するクラス"""
    def __init__(self, ports):
        self.ports = ports
        self.connections = {}
        self.lock = threading.Lock()
 
        for device, port_name in self.ports.items():
            try:
                # タイムアウトを設定してブロックを防ぐ
                self.connections[device] = serial.Serial(port_name, 9600, timeout=1)
                print(f"✅ [Serial] Connected to {device} on {port_name}")
                time.sleep(2) # Arduinoのリセットを待つ
            except serial.SerialException as e:
                print(f"❌ [Serial] FAILED to connect to {device} on {port_name}: {e}")
                self.connections[device] = None
 
    def send_command(self, device, command):
        with self.lock:
            connection = self.connections.get(device)
            if not (connection and connection.is_open):
                # print(f"❌ [Serial] Connection for '{device}' not available.")
                return
 
            try:
                # Arduinoは改行コード(\n)でコマンドの終わりを認識する
                line_to_send = (command + '\n').encode('utf-8')
                connection.write(line_to_send)
                # print(f"📤 [Serial] Sent to '{device}': {command}")
            except serial.SerialException as e:
                print(f"❌ [Serial] Error writing to {device}: {e}")
 
    def stop_all(self):
        with self.lock:
            for device, connection in self.connections.items():
                if connection and connection.is_open:
                    print(f"🔌 [Serial] Closing connection to {device}")
                    connection.close()
 
class TimelinePlayer:
    """タイムラインを管理し、ハードウェアを並列制御するクラス"""
    def __init__(self, vibration_controller, serial_controller, executor):
        self.vibration_controller = vibration_controller
        self.serial_controller = serial_controller
        self.executor = executor
        self.timeline_events = []
        self.effects_map = []
        self.active_continuous_effects = set()
        self.active_color = None
        self.prev_time = -1.0
        self.lock = threading.Lock()
 
    def set_timeline(self, events):
        with self.lock:
            self.timeline_events = sorted(events, key=lambda x: x.get('t', 0))
            self.prev_time = -1.0
            self.build_effects_map()
            self.executor.submit(self.reset_all_effects)
            print(f"🗓️ [Player] New timeline received with {len(self.timeline_events)} events.")
 
    def build_effects_map(self):
        self.effects_map.clear()
        start_events = [e for e in self.timeline_events if e.get('action') == 'start']
        for start_event in start_events:
            key = (start_event.get('effect'), start_event.get('mode'))
            start_time = start_event.get('t', 0.0)
            end_time = float('inf')
            for stop_event in self.timeline_events:
                if stop_event.get('t', 0.0) > start_time and \
                   stop_event.get('action') == 'stop' and \
                   stop_event.get('effect') == key[0] and \
                   stop_event.get('mode') == key[1]:
                    end_time = stop_event.get('t', 0.0)
                    break
            self.effects_map.append({'key': key, 'start': start_time, 'end': end_time})
 
    def update_to_time(self, current_time):
        with self.lock:
            if not self.timeline_events: return
 
            target_continuous_effects = set()
            target_color = None
            for interval in self.effects_map:
                effect, mode = interval['key']
                if interval['start'] <= current_time < interval['end']:
                    if effect == 'color': target_color = mode
                    else: target_continuous_effects.add(interval['key'])
 
            effects_to_start = target_continuous_effects - self.active_continuous_effects
            for effect, mode in effects_to_start:
                print(f"▶️ [Player] At {current_time:.2f}s: Starting {effect}/{mode}")
                self.executor.submit(self.control_effect, effect, mode, 'on')
 
            effects_to_stop = self.active_continuous_effects - target_continuous_effects
            for effect, mode in effects_to_stop:
                print(f"🛑 [Player] At {current_time:.2f}s: Stopping {effect}/{mode}")
                self.executor.submit(self.control_effect, effect, mode, 'off')
           
            self.active_continuous_effects = target_continuous_effects
 
            if target_color != self.active_color:
                if target_color:
                    print(f"🎨 [Player] At {current_time:.2f}s: Color -> {target_color}")
                    self.executor.submit(self.control_effect, 'color', target_color, 'on')
                else:
                    print(f"⚫ [Player] At {current_time:.2f}s: Color -> OFF")
                    self.executor.submit(self.control_effect, 'color', self.active_color, 'off')
                self.active_color = target_color
 
            if current_time > self.prev_time:
                for event in self.timeline_events:
                    if event.get('action') == 'shot':
                        event_time = event.get('t', 0.0)
                        if self.prev_time < event_time <= current_time:
                            print(f"💥 [Player] At {current_time:.2f}s: Shot {event.get('effect')}/{event.get('mode')}")
                            self.executor.submit(self.control_effect, event.get('effect'), event.get('mode'), 'on')
 
            self.prev_time = current_time
 
    def control_effect(self, effect, mode, state):
        if effect == 'vibration': self.vibration_controller.control(mode, state)
        elif effect == 'wind': self.serial_controller.send_command('wind', "ON" if state == 'on' else "OFF")
        elif effect == 'water' and state == 'on': self.serial_controller.send_command('water', "SPLASH")
        elif effect == 'flash':
            command = None
            if state == 'on':
                if mode == 'strobe': command = "FLASH 15"
                elif mode == 'burst': command = "FLASH 10"
                elif mode == 'steady': command = "ON"
            elif state == 'off': command = "OFF"
            if command: self.serial_controller.send_command('flash', command)
        elif effect == 'color':
            command = "COLOR 0 0 0"
            if state == 'on':
                if mode == 'red': command = "COLOR 255 0 0"
                elif mode == 'blue': command = "COLOR 0 0 255"
                elif mode == 'green': command = "COLOR 0 255 0"
            self.serial_controller.send_command('flash', command)
 
    def reset_all_effects(self):
        with self.lock:
            print("🔄 [Player] Resetting all effects...")
            self.executor.submit(self.vibration_controller.control, None, 'off')
            self.executor.submit(self.serial_controller.send_command, 'wind', 'OFF')
            self.executor.submit(self.serial_controller.send_command, 'flash', 'OFF')
            self.executor.submit(self.serial_controller.send_command, 'flash', 'COLOR 0 0 0')
            self.active_continuous_effects.clear()
            self.active_color = None
            self.prev_time = -1.0
 
def handle_client(conn, addr, player):
    print(f"🔗 Client connected: {addr}")
    try:
        while True:
            header = conn.recv(4)
            if not header: break
            data_size = int.from_bytes(header, 'big')
            if data_size == 0: continue
            data_bytes = b''
            while len(data_bytes) < data_size:
                packet = conn.recv(data_size - len(data_bytes))
                if not packet: break
                data_bytes += packet
            if len(data_bytes) < data_size: break
            data = json.loads(data_bytes.decode('utf-8'))
            if 'events' in data: player.set_timeline(data['events'])
            elif 'currentTime' in data: player.update_to_time(data['currentTime'])
    except (ConnectionResetError, BrokenPipeError): print(f"💔 Client connection lost: {addr}")
    except json.JSONDecodeError: print("❌ Received invalid JSON data.")
    except Exception as e: print(f"💥 Handler error: {e}")
    finally:
        print(f"🔌 Client connection closed: {addr}")
        player.reset_all_effects()
        conn.close()
 
def main():
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    serial_controller = SerialController(SERIAL_PORTS)
    vibration_controller = VibrationController(MQTT_HOST, MQTT_PORT, MQTT_CLIENT_ID)
    player = TimelinePlayer(vibration_controller, serial_controller, executor)
 
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"✅ Server started. Waiting for connection at {HOST}:{PORT}...")
        try:
            while True:
                conn, addr = s.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr, player))
                thread.daemon = True
                thread.start()
        except KeyboardInterrupt:
            print("\nShutting down server...")
        finally:
            player.reset_all_effects()
            serial_controller.stop_all()
            vibration_controller.stop()
            executor.shutdown(wait=True)
            print("✅ Server shut down gracefully.")
 
if __name__ == '__main__':
    main()