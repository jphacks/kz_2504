// Utility Functions
// TODO: Implement helper functions

export const generateSessionCode = (): string => {
  // TODO: Generate session code (will be handled by server)
  return Math.random().toString(36).substring(2, 6).toUpperCase();
};

export const formatTime = (seconds: number): string => {
  // TODO: Format video time display
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

export const validateSessionCode = (code: string): boolean => {
  // TODO: Validate session code format
  return /^[A-Z0-9]{4}$/.test(code);
};