// TypeScript Type Definitions
// TODO: Define comprehensive types for 4DX@HOME

export interface AppState {
  // TODO: Define application state
  connectionState: 'disconnected' | 'connecting' | 'connected' | 'error';
  sessionCode: string;
  currentScreen: 'waiting' | 'player';
}

export interface SessionData {
  // TODO: Define session data structure
  sessionId: string;
  sessionCode: string;
}

export interface SyncMessage {
  // TODO: Define sync message structure
  event: string;
  data: {
    current_time: number;
    playback_rate?: number;
  };
}