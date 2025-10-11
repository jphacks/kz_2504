# 4DX@HOME システム通信実装仕様書

## 概要

4DX@HOMEシステムにおけるフロントエンド（TypeScript/React）とラズベリーパイ（Python）間の通信実装仕様を定義します。

## アーキテクチャ概要

```
┌─────────────────┐    HTTPS/WSS     ┌─────────────────┐    HTTP/Serial   ┌─────────────────┐
│   Frontend      │ ←──────────────→ │   Cloud Run     │ ←─────────────→ │  Raspberry Pi   │
│   (React/TS)    │                  │   (FastAPI)     │                  │   (Python)      │
└─────────────────┘                  └─────────────────┘                  └─────────────────┘
```

## 共通データ型定義

### セッション関連

```typescript
// TypeScript型定義
interface SessionInfo {
  session_code: string;      // 6文字の英数字セッションコード
  session_data: {
    created_at: string;      // ISO8601形式
    clients: string[];       // 接続中クライアントリスト
    status: 'waiting' | 'active' | 'ended';
  };
}

interface DeviceInfo {
  version: string;           // ソフトウェアバージョン
  ip_address: string;        // デバイスIPアドレス  
  device_id: string;         // 一意デバイスID
  hardware_type: string;     // ハードウェア種別
  serial_number?: string;    // シリアル番号（オプション）
  firmware_version?: string; // ファームウェアバージョン（オプション）
}

interface SessionCreateRequest {
  product_code: string;      // 製品コード (DH001等)
  capabilities: string[];    // デバイス機能リスト
  device_info: DeviceInfo;
}
```

```python
# Python型定義 (dataclasses)
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class DeviceInfo:
    version: str
    ip_address: str
    device_id: str
    hardware_type: str
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None

@dataclass
class SessionInfo:
    session_code: str
    session_data: Dict[str, Any]

@dataclass
class ActuatorCommand:
    command_type: str          # "vibration", "motion", "scent", "audio", "lighting"
    intensity: int             # 0-100
    duration: int              # ミリ秒
    timestamp: datetime
```

### 同期データ型

```typescript
// TypeScript
interface SyncCommand {
  session_code: string;
  command_type: 'vibration' | 'motion' | 'scent' | 'audio' | 'lighting';
  intensity: number;         // 0-100
  duration: number;          // ミリ秒
  video_time: number;        // 動画再生時刻（秒）- フロントエンドから直接送信
  timestamp: string;         // ISO8601
}

interface PlaybackTimeSync {
  session_code: string;
  current_time: number;      // 現在の動画再生時刻（秒）
  playback_rate: number;     // 再生速度（通常1.0）
  is_playing: boolean;       // 再生中かどうか
  timestamp: string;         // ISO8601
}

interface SyncDataFile {
  video_id: string;
  duration: number;          // 動画長（秒）
  sync_events: SyncEvent[];  // タイムライン同期イベント
}

interface SyncEvent {
  time: number;              // 動画時刻（秒）
  action: string;            // アクション種別
  intensity: number;         // 強度(0-100)
  duration: number;          // 継続時間(ms)
}

interface PlaybackEvent {
  session_code: string;
  event_type: 'play' | 'pause' | 'seek' | 'end';
  video_time: number;
  timestamp: string;
}
```

```python
# Python
@dataclass
class SyncCommand:
    session_code: str
    command_type: str
    intensity: int
    duration: int
    video_time: float          # フロントエンドから直接受信した再生時刻
    timestamp: datetime

@dataclass
class PlaybackTimeSync:
    session_code: str
    current_time: float        # 現在の動画再生時刻（秒）
    playback_rate: float       # 再生速度
    is_playing: bool           # 再生状態
    timestamp: datetime

@dataclass
class SyncDataFile:
    video_id: str
    duration: float
    sync_events: List['SyncEvent']

@dataclass
class SyncEvent:
    time: float                # 動画時刻（秒）
    action: str                # アクション種別
    intensity: int             # 強度(0-100)
    duration: int              # 継続時間(ms)

@dataclass
class DeviceStatus:
    device_id: str
    session_code: str
    status: str
    actuators: Dict[str, Dict[str, Any]]
    system: Dict[str, Any]
    timestamp: datetime
```

---

## フロントエンド（TypeScript/React）実装仕様

### 1. 基本設定・初期化

```typescript
// src/config/api.ts
export const API_CONFIG = {
  BASE_URL: 'https://fourdk-home-backend-333203798555.asia-northeast1.run.app',
  ENDPOINTS: {
    SESSION_CREATE: '/api/session/create',
    SESSION_INFO: '/api/session/{session_code}',
    HEALTH: '/health'
  },
  TIMEOUTS: {
    API_REQUEST: 10000,      // 10秒
    WEBSOCKET_CONNECT: 5000   // 5秒
  }
};

// src/types/session.ts
export interface SessionState {
  sessionCode: string | null;
  isConnected: boolean;
  connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
  deviceStatus: 'unknown' | 'ready' | 'busy' | 'error';
  lastHeartbeat: Date | null;
}
```

### 2. セッション管理サービス

```typescript
// src/services/SessionService.ts
import { API_CONFIG } from '../config/api';

export class SessionService {
  private baseUrl: string;
  
  constructor() {
    this.baseUrl = API_CONFIG.BASE_URL;
  }

  /**
   * セッションコード入力でセッション参加
   */
  async joinSession(sessionCode: string): Promise<SessionInfo> {
    const response = await fetch(
      `${this.baseUrl}/api/session/${sessionCode}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': '4DX-WebApp/1.0.0'
        },
        signal: AbortSignal.timeout(API_CONFIG.TIMEOUTS.API_REQUEST)
      }
    );

    if (!response.ok) {
      throw new Error(`セッション参加失敗: ${response.status}`);
    }

    return await response.json();
  }

  /**
   * 新規セッション作成（デバイス未接続時）
   */
  async createSession(userInfo: any): Promise<SessionInfo> {
    const response = await fetch(
      `${this.baseUrl}/api/session/create`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': '4DX-WebApp/1.0.0'
        },
        body: JSON.stringify({
          user_initiated: true,
          user_info: userInfo
        }),
        signal: AbortSignal.timeout(API_CONFIG.TIMEOUTS.API_REQUEST)
      }
    );

    if (!response.ok) {
      throw new Error(`セッション作成失敗: ${response.status}`);
    }

    return await response.json();
  }

  /**
   * セッション状態監視（ポーリング）
   */
  async monitorSession(sessionCode: string, 
                      onStatusChange: (status: SessionInfo) => void,
                      intervalMs: number = 10000): Promise<() => void> {
    
    let isActive = true;
    
    const poll = async () => {
      while (isActive) {
        try {
          const sessionInfo = await this.joinSession(sessionCode);
          onStatusChange(sessionInfo);
          await new Promise(resolve => setTimeout(resolve, intervalMs));
        } catch (error) {
          console.error('セッション監視エラー:', error);
          await new Promise(resolve => setTimeout(resolve, 5000)); // エラー時は5秒待機
        }
      }
    };
    
    poll(); // 開始
    
    // 停止関数を返却
    return () => { isActive = false; };
  }
}
```

### 3. 動画再生制御サービス

```typescript
// src/services/VideoService.ts
export class VideoService {
  private sessionCode: string | null = null;
  private currentTime: number = 0;
  private isPlaying: boolean = false;
  
  constructor(private sessionService: SessionService) {}

  setSession(sessionCode: string) {
    this.sessionCode = sessionCode;
  }

  /**
   * 動画再生開始
   */
  async startPlayback(videoId: string): Promise<void> {
    if (!this.sessionCode) {
      throw new Error('セッションが設定されていません');
    }

    this.isPlaying = true;
    this.currentTime = 0;

    // 再生開始イベント送信（実際のAPIエンドポイント実装時）
    const playbackData = {
      session_code: this.sessionCode,
      video_id: videoId,
      action: 'play',
      timestamp: 0.0,
      user_id: this.generateUserId()
    };

    console.log('動画再生開始:', playbackData);
    
    // 進捗送信開始
    this.startProgressTracking();
  }

  /**
   * 再生進捗追跡
   */
  private startProgressTracking(): void {
    const interval = setInterval(() => {
      if (!this.isPlaying) {
        clearInterval(interval);
        return;
      }

      this.currentTime += 0.1; // 0.1秒ずつ増加
      
      // 1秒ごとに進捗送信
      if (Math.floor(this.currentTime * 10) % 10 === 0) {
        this.sendProgress();
      }
    }, 100);
  }

  /**
   * 再生進捗送信
   */
  private async sendProgress(): Promise<void> {
    const progressData = {
      session_code: this.sessionCode,
      current_time: this.currentTime,
      playback_rate: 1.0,
      timestamp: new Date().toISOString()
    };

    console.log('再生進捗:', progressData);
    // 実際のAPI実装時: await this.sessionService.sendProgress(progressData);
  }

  /**
   * 一時停止
   */
  async pause(): Promise<void> {
    this.isPlaying = false;
    
    const pauseData = {
      session_code: this.sessionCode,
      event_type: 'pause',
      video_time: this.currentTime,
      timestamp: new Date().toISOString()
    };

    console.log('動画一時停止:', pauseData);
  }

  /**
   * 再生再開
   */
  async resume(): Promise<void> {
    this.isPlaying = true;
    
    const resumeData = {
      session_code: this.sessionCode,
      event_type: 'resume', 
      video_time: this.currentTime,
      timestamp: new Date().toISOString()
    };

    console.log('動画再生再開:', resumeData);
    this.startProgressTracking();
  }

  /**
   * シーク
   */
  async seek(targetTime: number): Promise<void> {
    const oldTime = this.currentTime;
    this.currentTime = targetTime;

    const seekData = {
      session_code: this.sessionCode,
      event_type: 'seek',
      from_time: oldTime,
      to_time: targetTime,
      timestamp: new Date().toISOString()
    };

    console.log('動画シーク:', seekData);
  }

  private generateUserId(): string {
    return `user_${Math.random().toString(36).substr(2, 9)}`;
  }
}
```

### 4. 同期制御サービス

```typescript
// src/services/SyncService.ts
export class SyncService {
  private sessionCode: string | null = null;
  
  constructor(private sessionService: SessionService) {}

  setSession(sessionCode: string) {
    this.sessionCode = sessionCode;
  }

  /**
   * 動画再生時刻同期送信（リアルタイム）
   */
  async sendPlaybackTimeSync(
    currentTime: number,
    isPlaying: boolean,
    playbackRate: number = 1.0
  ): Promise<void> {
    
    if (!this.sessionCode) {
      throw new Error('セッションが設定されていません');
    }

    const timeSync: PlaybackTimeSync = {
      session_code: this.sessionCode,
      current_time: currentTime,
      playback_rate: playbackRate,
      is_playing: isPlaying,
      timestamp: new Date().toISOString()
    };

    console.log('再生時刻同期送信:', timeSync);
    
    // 実際のAPI実装時:
    // await this.sessionService.sendPlaybackTimeSync(timeSync);
  }

  /**
   * 同期データファイル送信（待機画面時）
   */
  async sendSyncDataFile(videoId: string, syncData: SyncDataFile): Promise<void> {
    
    if (!this.sessionCode) {
      throw new Error('セッションが設定されていません');
    }

    console.log('同期データファイル送信:', videoId, syncData);
    
    // 実際のAPI実装時:
    // await this.sessionService.sendSyncDataFile(this.sessionCode, syncData);
  }

  /**
   * 同期コマンド送信（タイムライン上のイベント）
   */
  async sendSyncCommand(
    commandType: 'vibration' | 'motion' | 'scent' | 'audio' | 'lighting',
    intensity: number,
    duration: number,
    videoTime: number
  ): Promise<void> {
    
    if (!this.sessionCode) {
      throw new Error('セッションが設定されていません');
    }

    const syncCommand: SyncCommand = {
      session_code: this.sessionCode,
      command_type: commandType,
      intensity: Math.max(0, Math.min(100, intensity)), // 0-100に制限
      duration: Math.max(0, duration),
      video_time: videoTime,  // フロントエンドから直接送信
      timestamp: new Date().toISOString()
    };

    console.log('同期コマンド送信:', syncCommand);
    
    // 実際のAPI実装時:
    // await this.sessionService.sendSyncCommand(syncCommand);
  }

  /**
   * 同期データファイル読み込み（待機画面時）
   */
  async loadSyncDataFile(videoId: string): Promise<SyncDataFile | null> {
    try {
      // 同期データファイルを読み込み（実際はAPIまたはローカルファイル）
      const response = await fetch(`/assets/sync-data/${videoId}.json`);
      
      if (!response.ok) {
        throw new Error(`同期データ取得失敗: ${response.status}`);
      }
      
      const syncData: SyncDataFile = await response.json();
      
      // ラズパイに事前送信
      await this.sendSyncDataFile(videoId, syncData);
      
      return syncData;
      
    } catch (error) {
      console.error('同期データ読み込みエラー:', error);
      return null;
    }
  }

  /**
   * リアルタイム同期開始（再生時刻ベース）
   */
  startRealTimeSync(videoElement: HTMLVideoElement, syncData: SyncDataFile | null): void {
    
    // 1. 再生時刻同期送信を開始
    const timeSyncInterval = setInterval(() => {
      this.sendPlaybackTimeSync(
        videoElement.currentTime,
        !videoElement.paused,
        videoElement.playbackRate
      );
    }, 100); // 100msごとに送信

    // 2. タイムライン同期イベント処理
    let timelineInterval: number | null = null;
    
    if (syncData) {
      timelineInterval = setInterval(() => {
        const currentTime = videoElement.currentTime;
        
        // 現在時刻に対応する同期イベントを検索
        const activeEvents = syncData.sync_events.filter(event => {
          const eventStart = event.time;
          const eventEnd = event.time + (event.duration / 1000);
          return currentTime >= eventStart && currentTime <= eventEnd;
        });
        
        // アクティブイベントをデバイスに送信
        activeEvents.forEach(event => {
          this.sendSyncCommand(
            event.action as any,
            event.intensity,
            event.duration,
            currentTime
          );
        });
        
      }, 50); // 50msごとにチェック
    }

    // 停止用タイマーID保存
    (window as any).syncIntervals = {
      timeSync: timeSyncInterval,
      timeline: timelineInterval
    };
  }

  /**
   * リアルタイム同期停止
   */
  stopRealTimeSync(): void {
    const intervals = (window as any).syncIntervals;
    
    if (intervals) {
      if (intervals.timeSync) {
        clearInterval(intervals.timeSync);
      }
      if (intervals.timeline) {
        clearInterval(intervals.timeline);
      }
      delete (window as any).syncIntervals;
    }
  }
}
```

### 5. React フック実装

```typescript
// src/hooks/useSession.ts
import { useState, useEffect, useCallback } from 'react';
import { SessionService, VideoService, SyncService } from '../services';

export const useSession = () => {
  const [sessionState, setSessionState] = useState<SessionState>({
    sessionCode: null,
    isConnected: false,
    connectionStatus: 'disconnected',
    deviceStatus: 'unknown',
    lastHeartbeat: null
  });

  const sessionService = new SessionService();
  const videoService = new VideoService(sessionService);
  const syncService = new SyncService(sessionService);

  const joinSession = useCallback(async (sessionCode: string) => {
    setSessionState(prev => ({ ...prev, connectionStatus: 'connecting' }));
    
    try {
      const sessionInfo = await sessionService.joinSession(sessionCode);
      
      setSessionState(prev => ({
        ...prev,
        sessionCode,
        isConnected: true,
        connectionStatus: 'connected',
        lastHeartbeat: new Date()
      }));

      videoService.setSession(sessionCode);
      syncService.setSession(sessionCode);

      // セッション監視開始
      const stopMonitoring = await sessionService.monitorSession(
        sessionCode,
        (info) => {
          setSessionState(prev => ({
            ...prev,
            deviceStatus: info.session_data.status === 'active' ? 'ready' : 'unknown',
            lastHeartbeat: new Date()
          }));
        }
      );

      // クリーンアップ関数保存
      (window as any).stopSessionMonitoring = stopMonitoring;

    } catch (error) {
      setSessionState(prev => ({ 
        ...prev, 
        connectionStatus: 'error',
        isConnected: false 
      }));
      throw error;
    }
  }, []);

  const leaveSession = useCallback(() => {
    // 監視停止
    if ((window as any).stopSessionMonitoring) {
      (window as any).stopSessionMonitoring();
      delete (window as any).stopSessionMonitoring;
    }

    syncService.stopRealTimeSync();
    
    setSessionState({
      sessionCode: null,
      isConnected: false,
      connectionStatus: 'disconnected',
      deviceStatus: 'unknown',
      lastHeartbeat: null
    });
  }, []);

  useEffect(() => {
    // クリーンアップ
    return () => {
      leaveSession();
    };
  }, [leaveSession]);

  return {
    sessionState,
    joinSession,
    leaveSession,
    videoService,
    syncService
  };
};
```

### 6. React コンポーネント例

```typescript
// src/components/SessionManager.tsx
import React, { useState } from 'react';
import { useSession } from '../hooks/useSession';

export const SessionManager: React.FC = () => {
  const [sessionCodeInput, setSessionCodeInput] = useState('');
  const { sessionState, joinSession, leaveSession, videoService, syncService } = useSession();

  const handleJoinSession = async () => {
    if (sessionCodeInput.length === 6) {
      try {
        await joinSession(sessionCodeInput.toUpperCase());
        alert('セッション参加成功！');
      } catch (error) {
        alert(`セッション参加失敗: ${error.message}`);
      }
    }
  };

  const handleStartVideo = async () => {
    if (sessionState.isConnected) {
      // 1. 動画要素取得
      const videoElement = document.getElementById('mainVideo') as HTMLVideoElement;
      
      if (!videoElement) {
        alert('動画要素が見つかりません');
        return;
      }
      
      // 2. 同期データファイル読み込み（待機画面時に実行）
      const syncData = await syncService.loadSyncDataFile('sample_4dx_video');
      
      // 3. 動画再生開始
      await videoService.startPlayback('sample_4dx_video');
      
      // 4. リアルタイム同期開始
      syncService.startRealTimeSync(videoElement, syncData);
      
      alert('動画再生開始！');
    }
  };

  return (
    <div className="session-manager">
      <h2>4DX@HOME セッション管理</h2>
      
      {!sessionState.isConnected ? (
        <div className="join-session">
          <input
            type="text"
            value={sessionCodeInput}
            onChange={(e) => setSessionCodeInput(e.target.value.toUpperCase())}
            placeholder="セッションコード（6文字）"
            maxLength={6}
          />
          <button 
            onClick={handleJoinSession}
            disabled={sessionCodeInput.length !== 6}
          >
            セッション参加
          </button>
        </div>
      ) : (
        <div className="session-controls">
          <p>セッション: {sessionState.sessionCode}</p>
          <p>ステータス: {sessionState.connectionStatus}</p>
          <p>デバイス: {sessionState.deviceStatus}</p>
          
          <button onClick={handleStartVideo}>
            動画開始
          </button>
          <button onClick={leaveSession}>
            セッション退出
          </button>
        </div>
      )}
    </div>
  );
};
```

---

## ラズベリーパイ（Python）実装仕様

### 1. 基本設定・初期化

```python
# config/settings.py
from dataclasses import dataclass
from typing import List, Dict, Any
import os

@dataclass
class APIConfig:
    BASE_URL: str = "https://fourdk-home-backend-333203798555.asia-northeast1.run.app"
    ENDPOINTS: Dict[str, str] = None
    TIMEOUTS: Dict[str, int] = None
    
    def __post_init__(self):
        if self.ENDPOINTS is None:
            self.ENDPOINTS = {
                'SESSION_CREATE': '/api/session/create',
                'SESSION_INFO': '/api/session/{session_code}',
                'HEALTH': '/health'
            }
        
        if self.TIMEOUTS is None:
            self.TIMEOUTS = {
                'API_REQUEST': 10,
                'HEARTBEAT_INTERVAL': 30,
                'STATUS_REPORT_INTERVAL': 60
            }

@dataclass
class HardwareConfig:
    DEVICE_ID: str
    PRODUCT_CODE: str = "DH001"
    CAPABILITIES: List[str] = None
    GPIO_PINS: Dict[str, int] = None
    
    def __post_init__(self):
        if self.CAPABILITIES is None:
            self.CAPABILITIES = ["vibration", "motion", "scent", "audio", "lighting"]
        
        if self.GPIO_PINS is None:
            self.GPIO_PINS = {
                'vibration_motor': 18,
                'servo_motor': 12,
                'scent_valve_1': 16,
                'scent_valve_2': 20,
                'scent_valve_3': 21,
                'audio_relay': 26,
                'led_strip': 19
            }

# デバイス固有設定
def get_device_config() -> HardwareConfig:
    # MACアドレスベースのデバイスID生成
    import uuid
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) 
                   for i in range(0,8*6,8)][::-1])
    device_id = f"raspi-4dx-{mac.replace(':', '')[-6:]}"
    
    return HardwareConfig(DEVICE_ID=device_id)
```

### 2. デバイス通信サービス

```python
# services/device_communication.py
import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from dataclasses import asdict

from config.settings import APIConfig, HardwareConfig, get_device_config
from models.device_models import DeviceInfo, SessionInfo, ActuatorCommand, DeviceStatus

logger = logging.getLogger(__name__)

class DeviceCommunicationService:
    """デバイス通信サービス"""
    
    def __init__(self):
        self.api_config = APIConfig()
        self.hw_config = get_device_config()
        self.session_code: Optional[str] = None
        self.is_connected: bool = False
        self.last_heartbeat: Optional[datetime] = None
        
        # デバイス情報
        self.device_info = DeviceInfo(
            version="2.1.0",
            ip_address=self._get_local_ip(),
            device_id=self.hw_config.DEVICE_ID,
            hardware_type="raspberry_pi_4b",
            serial_number=self._get_serial_number(),
            firmware_version="1.4.2"
        )
    
    async def register_device(self) -> bool:
        """デバイス登録（セッション作成）"""
        try:
            logger.info("Cloud Runにデバイス登録中...")
            
            registration_data = {
                "product_code": self.hw_config.PRODUCT_CODE,
                "capabilities": self.hw_config.CAPABILITIES,
                "device_info": asdict(self.device_info)
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': f'RaspberryPi-4DX/{self.device_info.device_id}'
                }
                
                async with session.post(
                    f"{self.api_config.BASE_URL}/api/session/create",
                    json=registration_data,
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        self.session_code = data.get("session_code")
                        self.is_connected = True
                        
                        logger.info(f"デバイス登録成功: {self.session_code}")
                        return True
                    else:
                        logger.error(f"デバイス登録失敗: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"デバイス登録エラー: {e}")
            return False
    
    async def get_session_status(self) -> Optional[SessionInfo]:
        """セッション状態取得"""
        if not self.session_code:
            return None
            
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                headers = {
                    'User-Agent': f'RaspberryPi-4DX/{self.device_info.device_id}'
                }
                
                async with session.get(
                    f"{self.api_config.BASE_URL}/api/session/{self.session_code}",
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"セッション状態: {data.get('session_data', {}).get('status', 'unknown')}")
                        return SessionInfo(
                            session_code=data.get("session_code"),
                            session_data=data.get("session_data", {})
                        )
                    else:
                        logger.error(f"セッション状態取得失敗: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"セッション状態取得エラー: {e}")
            return None
    
    async def send_heartbeat(self) -> bool:
        """ハートビート送信"""
        try:
            status_data = DeviceStatus(
                device_id=self.device_info.device_id,
                session_code=self.session_code,
                status="ready",
                actuators=self._get_actuator_status(),
                system=self._get_system_status(),
                timestamp=datetime.now()
            )
            
            logger.info(f"ハートビート送信 - CPU温度: {status_data.system['cpu_temp']}°C")
            self.last_heartbeat = datetime.now()
            
            # 実際のAPI実装時はHTTP POSTで送信
            return True
            
        except Exception as e:
            logger.error(f"ハートビート送信エラー: {e}")
            return False
    
    async def start_periodic_tasks(self):
        """定期タスク開始"""
        # ハートビート送信タスク
        asyncio.create_task(self._heartbeat_loop())
        
        # システム状態報告タスク  
        asyncio.create_task(self._status_report_loop())
        
        logger.info("定期タスク開始完了")
    
    async def _heartbeat_loop(self):
        """ハートビート送信ループ"""
        while self.is_connected:
            try:
                await self.send_heartbeat()
                await asyncio.sleep(self.api_config.TIMEOUTS['HEARTBEAT_INTERVAL'])
            except Exception as e:
                logger.error(f"ハートビートエラー: {e}")
                await asyncio.sleep(5)
    
    async def _status_report_loop(self):
        """システム状態報告ループ"""
        while self.is_connected:
            try:
                await self.get_session_status()
                await asyncio.sleep(self.api_config.TIMEOUTS['STATUS_REPORT_INTERVAL'])
            except Exception as e:
                logger.error(f"状態報告エラー: {e}")
                await asyncio.sleep(10)
    
    def _get_local_ip(self) -> str:
        """ローカルIP取得"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return "127.0.0.1"
    
    def _get_serial_number(self) -> Optional[str]:
        """ラズパイシリアル番号取得"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Serial'):
                        return line.split(':')[1].strip()
        except:
            pass
        return None
    
    def _get_actuator_status(self) -> Dict[str, Dict[str, Any]]:
        """アクチュエーター状態取得"""
        return {
            "vibration": {"status": "ready", "last_command": None},
            "motion": {"status": "ready", "position": 0},
            "scent": {"status": "ready", "active_cartridge": None},
            "audio": {"status": "ready", "volume": 50},
            "lighting": {"status": "ready", "color": "#ffffff"}
        }
    
    def _get_system_status(self) -> Dict[str, Any]:
        """システム状態取得"""
        import random
        
        # 実際の実装では以下のような情報を取得
        # - CPU温度: /sys/class/thermal/thermal_zone0/temp
        # - メモリ使用量: psutil.virtual_memory()
        # - ネットワーク強度: iwconfig の解析
        
        return {
            "cpu_temp": round(random.uniform(40.0, 65.0), 1),
            "memory_usage": round(random.uniform(20.0, 80.0), 1),
            "disk_usage": round(random.uniform(10.0, 60.0), 1),
            "network_strength": random.randint(70, 100),
            "uptime": "2d 14h 23m"
        }
```

### 3. アクチュエーター制御サービス

```python
# services/actuator_service.py
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

# GPIOライブラリ（実環境でのみ）
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("GPIOライブラリが利用できません（開発環境）")

from config.settings import HardwareConfig, get_device_config
from models.device_models import ActuatorCommand

logger = logging.getLogger(__name__)

@dataclass
class ActuatorState:
    status: str  # "ready", "busy", "error"
    current_intensity: int = 0
    is_active: bool = False
    last_command: Optional[ActuatorCommand] = None

class ActuatorService:
    """アクチュエーター制御サービス"""
    
    def __init__(self):
        self.hw_config = get_device_config()
        self.actuator_states: Dict[str, ActuatorState] = {}
        self.command_queue: asyncio.Queue = asyncio.Queue()
        self.is_running: bool = False
        
        # アクチュエーター初期化
        self._initialize_actuators()
        
        # GPIO初期化（実環境のみ）
        if GPIO_AVAILABLE:
            self._setup_gpio()
    
    def _initialize_actuators(self):
        """アクチュエーター状態初期化"""
        for capability in self.hw_config.CAPABILITIES:
            self.actuator_states[capability] = ActuatorState(status="ready")
        
        logger.info(f"アクチュエーター初期化完了: {list(self.actuator_states.keys())}")
    
    def _setup_gpio(self):
        """GPIO設定（実環境のみ）"""
        if not GPIO_AVAILABLE:
            return
            
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # 各GPIOピン設定
        for actuator, pin in self.hw_config.GPIO_PINS.items():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
        
        logger.info("GPIO設定完了")
    
    async def start_command_processor(self):
        """コマンド処理開始"""
        self.is_running = True
        asyncio.create_task(self._command_processing_loop())
        logger.info("アクチュエーターコマンド処理開始")
    
    async def execute_command(self, command: ActuatorCommand) -> bool:
        """コマンド実行"""
        try:
            # コマンドキューに追加
            await self.command_queue.put(command)
            logger.info(f"コマンド受信: {command.command_type} (強度:{command.intensity})")
            return True
            
        except Exception as e:
            logger.error(f"コマンド実行エラー: {e}")
            return False
    
    async def _command_processing_loop(self):
        """コマンド処理ループ"""
        while self.is_running:
            try:
                # コマンド取得（タイムアウト付き）
                command = await asyncio.wait_for(
                    self.command_queue.get(), 
                    timeout=1.0
                )
                
                # 実行開始
                await self._execute_actuator_command(command)
                
            except asyncio.TimeoutError:
                # タイムアウト時は継続
                continue
            except Exception as e:
                logger.error(f"コマンド処理エラー: {e}")
    
    async def _execute_actuator_command(self, command: ActuatorCommand):
        """個別アクチュエーターコマンド実行"""
        actuator_type = command.command_type
        
        if actuator_type not in self.actuator_states:
            logger.error(f"未知のアクチュエータータイプ: {actuator_type}")
            return
        
        state = self.actuator_states[actuator_type]
        
        # 実行中チェック
        if state.is_active:
            logger.warning(f"{actuator_type}実行中のため新コマンドをスキップ")
            return
        
        try:
            # 実行開始
            state.is_active = True
            state.current_intensity = command.intensity
            state.last_command = command
            state.status = "busy"
            
            logger.info(f"⚡ {actuator_type}実行開始: 強度{command.intensity}, 時間{command.duration}ms")
            
            # アクチュエータータイプ別実行
            if actuator_type == "vibration":
                await self._execute_vibration(command)
            elif actuator_type == "motion":
                await self._execute_motion(command)
            elif actuator_type == "scent":
                await self._execute_scent(command)
            elif actuator_type == "audio":
                await self._execute_audio(command)
            elif actuator_type == "lighting":
                await self._execute_lighting(command)
            
            logger.info(f"✅ {actuator_type}実行完了")
            
        except Exception as e:
            logger.error(f"{actuator_type}実行エラー: {e}")
            state.status = "error"
            
        finally:
            # 実行終了
            state.is_active = False
            state.current_intensity = 0
            if state.status != "error":
                state.status = "ready"
    
    async def _execute_vibration(self, command: ActuatorCommand):
        """振動モーター制御"""
        pin = self.hw_config.GPIO_PINS.get('vibration_motor')
        
        if GPIO_AVAILABLE and pin:
            # PWM制御
            pwm = GPIO.PWM(pin, 1000)  # 1kHz
            duty_cycle = command.intensity  # 0-100
            
            pwm.start(duty_cycle)
            await asyncio.sleep(command.duration / 1000.0)
            pwm.stop()
        else:
            # シミュレーション
            logger.info(f"[SIM] 振動モーター: 強度{command.intensity}% 時間{command.duration}ms")
            await asyncio.sleep(command.duration / 1000.0)
    
    async def _execute_motion(self, command: ActuatorCommand):
        """モーション（サーボモーター）制御"""
        pin = self.hw_config.GPIO_PINS.get('servo_motor')
        
        if GPIO_AVAILABLE and pin:
            # サーボ角度制御（強度を角度にマッピング）
            angle = int((command.intensity / 100.0) * 180)  # 0-180度
            
            pwm = GPIO.PWM(pin, 50)  # 50Hz
            duty = 2.5 + (angle / 18.0)  # 角度をデューティ比に変換
            
            pwm.start(duty)
            await asyncio.sleep(command.duration / 1000.0)
            pwm.ChangeDutyCycle(7.5)  # 中立位置に戻す
            await asyncio.sleep(0.5)
            pwm.stop()
        else:
            # シミュレーション
            angle = int((command.intensity / 100.0) * 180)
            logger.info(f"[SIM] サーボモーター: 角度{angle}度 時間{command.duration}ms")
            await asyncio.sleep(command.duration / 1000.0)
    
    async def _execute_scent(self, command: ActuatorCommand):
        """香り（バルブ）制御"""
        # 強度に応じてバルブ選択
        valve_pins = [
            self.hw_config.GPIO_PINS.get('scent_valve_1'),
            self.hw_config.GPIO_PINS.get('scent_valve_2'),
            self.hw_config.GPIO_PINS.get('scent_valve_3')
        ]
        
        # 強度によるバルブ選択ロジック
        valve_index = min(int(command.intensity / 34), 2)  # 0,1,2
        valve_pin = valve_pins[valve_index]
        
        if GPIO_AVAILABLE and valve_pin:
            GPIO.output(valve_pin, GPIO.HIGH)
            await asyncio.sleep(command.duration / 1000.0)
            GPIO.output(valve_pin, GPIO.LOW)
        else:
            scent_types = ["citrus", "lavender", "mint"]
            logger.info(f"[SIM] 香りバルブ: {scent_types[valve_index]} 時間{command.duration}ms")
            await asyncio.sleep(command.duration / 1000.0)
    
    async def _execute_audio(self, command: ActuatorCommand):
        """オーディオ制御"""
        pin = self.hw_config.GPIO_PINS.get('audio_relay')
        
        if GPIO_AVAILABLE and pin:
            # オーディオリレー制御（音量制御は別途必要）
            GPIO.output(pin, GPIO.HIGH)
            await asyncio.sleep(command.duration / 1000.0)
            GPIO.output(pin, GPIO.LOW)
        else:
            logger.info(f"[SIM] オーディオ: 音量{command.intensity}% 時間{command.duration}ms")
            await asyncio.sleep(command.duration / 1000.0)
    
    async def _execute_lighting(self, command: ActuatorCommand):
        """照明（LED）制御"""
        pin = self.hw_config.GPIO_PINS.get('led_strip')
        
        if GPIO_AVAILABLE and pin:
            # PWM制御でブライトネス調整
            pwm = GPIO.PWM(pin, 1000)
            brightness = command.intensity
            
            pwm.start(brightness)
            await asyncio.sleep(command.duration / 1000.0)
            pwm.stop()
        else:
            logger.info(f"[SIM] LED照明: 明度{command.intensity}% 時間{command.duration}ms")
            await asyncio.sleep(command.duration / 1000.0)
    
    def get_actuator_status(self) -> Dict[str, Dict[str, Any]]:
        """全アクチュエーター状態取得"""
        status = {}
        for actuator_type, state in self.actuator_states.items():
            status[actuator_type] = {
                "status": state.status,
                "current_intensity": state.current_intensity,
                "is_active": state.is_active,
                "last_command_time": state.last_command.timestamp.isoformat() if state.last_command else None
            }
        return status
    
    def stop_all_actuators(self):
        """全アクチュエーター停止"""
        self.is_running = False
        
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        
        logger.info("全アクチュエーター停止完了")
```

### 4. コマンド受信シミュレーター

```python
# services/command_receiver.py
import asyncio
import random
import logging
from datetime import datetime
from typing import Callable, Optional

from models.device_models import ActuatorCommand
from services.actuator_service import ActuatorService

logger = logging.getLogger(__name__)

class CommandReceiver:
    """コマンド受信サービス（WebSocket代替）"""
    
    def __init__(self, actuator_service: ActuatorService):
        self.actuator_service = actuator_service
        self.is_running: bool = False
        self.session_code: Optional[str] = None
        self.sync_data: Optional[SyncDataFile] = None
        self.current_video_time: float = 0.0
        self.is_video_playing: bool = False
    
    def set_session(self, session_code: str):
        """セッション設定"""
        self.session_code = session_code
    
    async def start_command_listening(self):
        """コマンド受信開始（シミュレーション）"""
        if not self.session_code:
            logger.error("セッションが設定されていません")
            return
        
        self.is_running = True
        logger.info("コマンド受信開始")
        
        # 実際の実装ではWebSocket接続
        # 現在はランダムコマンド生成でシミュレート
        asyncio.create_task(self._simulate_command_reception())
    
    def stop_command_listening(self):
        """コマンド受信停止"""
        self.is_running = False
        logger.info("コマンド受信停止")
    
    async def receive_sync_data_file(self, sync_data: SyncDataFile):
        """同期データファイル受信（待機画面時）"""
        self.sync_data = sync_data
        logger.info(f"同期データファイル受信: {sync_data.video_id}, イベント数: {len(sync_data.sync_events)}")
        
        # 同期データの前処理（必要に応じて）
        self._preprocess_sync_data()
    
    async def receive_playback_time_sync(self, time_sync: PlaybackTimeSync):
        """再生時刻同期受信（リアルタイム）"""
        self.current_video_time = time_sync.current_time
        self.is_video_playing = time_sync.is_playing
        
        logger.debug(f"再生時刻同期: {time_sync.current_time:.1f}秒, 再生中: {time_sync.is_playing}")
        
        # タイムライン同期イベント処理
        if self.sync_data and self.is_video_playing:
            await self._process_timeline_events(time_sync.current_time)
    
    async def receive_sync_command(self, sync_command: SyncCommand):
        """同期コマンド受信（直接実行）"""
        command = ActuatorCommand(
            command_type=sync_command.command_type,
            intensity=sync_command.intensity,
            duration=sync_command.duration,
            timestamp=sync_command.timestamp
        )
        
        logger.info(f"同期コマンド受信: {command.command_type} (時刻:{sync_command.video_time:.1f}s)")
        
        # 即座に実行
        await self.actuator_service.execute_command(command)
    
    def _preprocess_sync_data(self):
        """同期データの前処理"""
        if not self.sync_data:
            return
        
        # イベントを時刻順にソート
        self.sync_data.sync_events.sort(key=lambda x: x.time)
        
        # 重複イベントの除去（必要に応じて）
        logger.info(f"同期データ前処理完了: {len(self.sync_data.sync_events)}イベント")
    
    async def _process_timeline_events(self, current_time: float):
        """タイムライン同期イベント処理"""
        if not self.sync_data:
            return
        
        # 許容誤差（秒）
        tolerance = 0.1
        
        # 現在時刻に対応するイベントを検索
        active_events = [
            event for event in self.sync_data.sync_events
            if abs(event.time - current_time) <= tolerance
        ]
        
        # イベントを実行
        for event in active_events:
            command = ActuatorCommand(
                command_type=event.action,
                intensity=event.intensity,
                duration=event.duration,
                timestamp=datetime.now()
            )
            
            logger.info(f"タイムラインイベント実行: {event.action} @ {event.time:.1f}s")
            await self.actuator_service.execute_command(command)
    
    async def _simulate_command_reception(self):
        """コマンド受信シミュレート"""
        command_types = ["vibration", "motion", "scent", "audio", "lighting"]
        
        while self.is_running:
            try:
                # ランダムにコマンド生成（実際はWebSocketで受信）
                if random.random() < 0.3:  # 30%の確率
                    command_type = random.choice(command_types)
                    intensity = random.randint(30, 100)
                    duration = random.randint(500, 3000)
                    
                    command = ActuatorCommand(
                        command_type=command_type,
                        intensity=intensity,
                        duration=duration,
                        timestamp=datetime.now()
                    )
                    
                    # アクチュエーター実行
                    await self.actuator_service.execute_command(command)
                
                await asyncio.sleep(2)  # 2秒間隔
                
            except Exception as e:
                logger.error(f"コマンド受信エラー: {e}")
                await asyncio.sleep(5)
```

### 5. メインアプリケーション

```python
# main.py
import asyncio
import logging
import signal
import sys
from datetime import datetime

from services.device_communication import DeviceCommunicationService
from services.actuator_service import ActuatorService  
from services.command_receiver import CommandReceiver

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class RaspberryPi4DXDevice:
    """ラズパイ4DXデバイスメインクラス"""
    
    def __init__(self):
        self.communication_service = DeviceCommunicationService()
        self.actuator_service = ActuatorService()
        self.command_receiver = CommandReceiver(self.actuator_service)
        self.is_running = False
    
    async def initialize(self) -> bool:
        """デバイス初期化"""
        try:
            logger.info("🚀 4DX@HOME ラズパイデバイス初期化開始")
            
            # 1. デバイス登録
            if not await self.communication_service.register_device():
                logger.error("デバイス登録に失敗しました")
                return False
            
            # 2. アクチュエーター初期化
            await self.actuator_service.start_command_processor()
            
            # 3. コマンド受信設定
            session_code = self.communication_service.session_code
            self.command_receiver.set_session(session_code)
            
            logger.info("✅ デバイス初期化完了")
            return True
            
        except Exception as e:
            logger.error(f"初期化エラー: {e}")
            return False
    
    async def run(self):
        """メイン実行"""
        if not await self.initialize():
            return
        
        self.is_running = True
        
        try:
            # サービス開始
            await self.communication_service.start_periodic_tasks()
            await self.command_receiver.start_command_listening()
            
            logger.info("🔄 4DX@HOMEデバイス動作開始")
            logger.info(f"📋 セッションコード: {self.communication_service.session_code}")
            logger.info("   💓 ハートビート送信中")
            logger.info("   📊 状態報告送信中")
            logger.info("   📥 コマンド受信待機中")
            
            # 実行ループ
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("🛑 キーボード割り込み受信")
        except Exception as e:
            logger.error(f"実行エラー: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """シャットダウン"""
        logger.info("🛑 4DX@HOMEデバイス停止中...")
        
        self.is_running = False
        self.communication_service.is_connected = False
        self.command_receiver.stop_command_listening()
        self.actuator_service.stop_all_actuators()
        
        logger.info("✅ 4DX@HOMEデバイス停止完了")
    
    def handle_signal(self, signum, frame):
        """シグナルハンドラー"""
        logger.info(f"シグナル受信: {signum}")
        self.is_running = False

async def main():
    """メイン関数"""
    device = RaspberryPi4DXDevice()
    
    # シグナルハンドラー設定
    signal.signal(signal.SIGINT, device.handle_signal)
    signal.signal(signal.SIGTERM, device.handle_signal)
    
    await device.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("プログラム終了")
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        sys.exit(1)
```

### 6. 実行・デプロイ用スクリプト

```python
# scripts/run_device.py
#!/usr/bin/env python3
"""
4DX@HOME ラズパイデバイス実行スクリプト
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path

def setup_environment():
    """環境設定"""
    # 必要なライブラリインストール
    requirements = [
        "aiohttp>=3.8.0",
        "asyncio",
        "RPi.GPIO;platform_machine=='armv7l'"  # ラズパイのみ
    ]
    
    for req in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", req])
        except subprocess.CalledProcessError as e:
            print(f"ライブラリインストールエラー: {e}")

def run_device(config_file=None):
    """デバイス実行"""
    # 設定ファイルロード
    if config_file and Path(config_file).exists():
        os.environ['DEVICE_CONFIG'] = config_file
    
    # メインアプリケーション実行
    from main import main
    import asyncio
    
    print("4DX@HOME ラズパイデバイス開始...")
    asyncio.run(main())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="4DX@HOME ラズパイデバイス")
    parser.add_argument("--config", help="設定ファイルパス")
    parser.add_argument("--setup", action="store_true", help="環境セットアップ")
    
    args = parser.parse_args()
    
    if args.setup:
        setup_environment()
    
    run_device(args.config)
```

### 7. systemd サービス設定

```ini
# /etc/systemd/system/4dx-home-device.service
[Unit]
Description=4DX@HOME Device Service
After=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/4dx-home-device
Environment=PYTHONPATH=/home/pi/4dx-home-device
ExecStart=/usr/bin/python3 /home/pi/4dx-home-device/main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

## 通信フロー図

```
Frontend (TS)          Cloud Run (Python)          Raspberry Pi (Python)
     │                         │                           │
     │ 1. POST /session/create │                           │
     │ ─────────────────────────→                           │
     │                         │ 2. Create Session        │
     │                         │ ←─────────────────────────┤
     │ ← Session Code          │                           │
     │                         │                           │
     │ 3. GET /session/{code}  │                           │
     │ ─────────────────────────→                           │
     │ ← Session Info          │                           │
     │                         │                           │
     │ 4. Send Sync Commands   │ 5. Forward to Device     │
     │ ─────────────────────────→ ─────────────────────────→│
     │                         │                           │ 6. Execute Actuators
     │                         │ 7. Execution Feedback   │
     │ 8. Status Updates       │ ←─────────────────────────┤
     │ ←─────────────────────────                           │
     │                         │                           │
     │ 9. Heartbeat/Monitor    │ 10. Device Status        │
     │ ─────────────────────────→ ←─────────────────────────┤
     │ ← Device Status         │                           │
```

## エラーハンドリング

### フロントエンド（TypeScript）
- ネットワークエラー時の自動再接続
- セッション切断時の適切なUI状態表示
- API呼び出し失敗時のエラーメッセージ表示

### ラズベリーパイ（Python）
- 通信切断時の自動再接続機能
- アクチュエーター制御失敗時の安全停止
- システムエラー時のログ記録とアラート

## セキュリティ考慮事項

- HTTPS/WSS通信の強制
- セッションコードの適切な管理
- デバイス認証の実装
- 不正なコマンドの検証と拒否

この仕様書に基づいて実装することで、Cloud Run環境で動作する完全な4DX@HOMEシステムが構築できます。