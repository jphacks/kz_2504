/*
  Flash and Color Controller for 4D Home Project

  Raspberry Piから送られてくるシリアルコマンドを解釈し、
  RGB LEDの色と、フラッシュ/ストロボ用の白色LEDを制御します。

  想定するコマンド:
  - "COLOR R G B" : RGB LEDを指定の色に設定 (例: "COLOR 255 0 0")
  - "FLASH 10"    : 白色LEDを短く点滅させる（バースト）
  - "FLASH 15"    : 白色LEDを少し長く点滅させる（ストロボ）
  - "ON"          : 白色LEDを常時点灯させる
  - "OFF"         : すべてのLEDを消灯させる
*/

// --- ピン設定 ---
// Common Cathode (コモンカソード) RGB LED用
const int RED_PIN = 3;   // 赤色 (PWM対応ピン)
const int GREEN_PIN = 5; // 緑色 (PWM対応ピン)
const int BLUE_PIN = 6;  // 青色 (PWM対応ピン)

// フラッシュ/常時点灯用の白色LED (トランジスタ経由)
const int WHITE_LED_PIN = 7;

void setup() {
  // シリアル通信を開始 (9600 bps)
  Serial.begin(9600);

  // LEDピンを出力に設定
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  pinMode(WHITE_LED_PIN, OUTPUT);

  // 起動時にすべてのLEDを消灯
  allLedsOff();
  
  Serial.println("Flash/Color Controller Initialized. Waiting for commands...");
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    // 受信したコマンドを処理
    processCommand(command);
  }
}

void processCommand(String cmd) {
  Serial.print("Received: '");
  Serial.print(cmd);
  Serial.println("'");

  if (cmd.startsWith("COLOR")) {
    // "COLOR R G B" の形式からR, G, Bの値を抽出
    int r, g, b;
    // sscanfはC言語スタイルの文字列解析関数で、特定の書式にマッチした値を抽出するのに便利
    sscanf(cmd.c_str(), "COLOR %d %d %d", &r, &g, &b);
    setRgbColor(r, g, b);
  } 
  else if (cmd.startsWith("FLASH")) {
    int duration;
    sscanf(cmd.c_str(), "FLASH %d", &duration);
    // durationの値に応じて点滅時間を変える
    // FLASH 10 -> 50ms, FLASH 15 -> 100ms など、お好みで調整
    flashWhiteLed(duration * 5); 
  } 
  else if (cmd == "ON") {
    digitalWrite(WHITE_LED_PIN, HIGH);
  } 
  else if (cmd == "OFF") {
    allLedsOff();
  }
}

// RGB LEDの色を設定する関数
void setRgbColor(int r, int g, int b) {
  // analogWriteは0-255の値でPWMのデューティ比を設定する
  analogWrite(RED_PIN, r);
  analogWrite(GREEN_PIN, g);
  analogWrite(BLUE_PIN, b);
}

// 白色LEDを点滅させる関数
void flashWhiteLed(int duration_ms) {
  digitalWrite(WHITE_LED_PIN, HIGH);
  delay(duration_ms);
  digitalWrite(WHITE_LED_PIN, LOW);
}

// すべてのLEDを消灯させる関数
void allLedsOff() {
  setRgbColor(0, 0, 0);
  digitalWrite(WHITE_LED_PIN, LOW);
}
