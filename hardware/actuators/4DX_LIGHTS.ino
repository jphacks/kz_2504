#include <ESP8266WiFi.h>
#include <PubSubClient.h>

// ======== WiFi/MQTT 設定 ========
const char* WIFI_SSID     = "PiMQTT-AP";
const char* WIFI_PASSWORD = "AtHome1234";

const char* MQTT_HOST = "192.168.4.1";
const uint16_t MQTT_PORT = 1883;
const char* MQTT_CLIENT_ID = "ESP8266_LED_Controller";

// ======== ピン設定 (動作確認が取れたピン定義) ========
// --- 単体LED ---
const int SINGLE_LED_PIN = 4; // D2 (GPIO 4)

// --- RGB LEDテープ (PWMピン) ---
const int R_PIN = 14; // D5 (GPIO 14)
const int G_PIN = 12; // D6 (GPIO 12)
const int B_PIN = 13; // D7 (GPIO 13)

// ======== PWM設定 ========
// ESP8266のanalogWriteは 0 (OFF) ～ 1023 (ON)
const int PWM_MAX = 1023;

// ======== 動作設定 (追加) ========
const unsigned long HEARTBEAT_MS = 10000; // ハートビート間隔(ms)

// ======== グローバル変数 ========
WiFiClient espClient;
PubSubClient client(espClient);
unsigned long lastReconnectAttempt = 0;
unsigned long lastHeartbeat = 0; // ハートビート用 (追加)

// --- 単体LEDの状態管理 ---
enum LedMode {
  LED_OFF,
  LED_ON,
  LED_BLINK_SLOW,
  LED_BLINK_FAST
};
LedMode currentLedMode = LED_OFF;
unsigned long lastBlinkTime = 0;
bool ledState = false;


// **********************************
// * セットアップ処理
// **********************************
void setup() {
  Serial.begin(115200);
  
  // --- ピンモード設定 ---
  pinMode(SINGLE_LED_PIN, OUTPUT);
  // (修正) LOWで点灯する回路のため、初期状態(OFF)はHIGHにする
  digitalWrite(SINGLE_LED_PIN, HIGH); 

  pinMode(R_PIN, OUTPUT);
  pinMode(G_PIN, OUTPUT);
  pinMode(B_PIN, OUTPUT);
  
  // PWM周波数の初期化
  analogWriteRange(PWM_MAX);

  // --- 起動時の色を「赤」に設定 (ご要望) ---
  Serial.println("Setting initial color to RED");
  setColor(255, 0, 0); // 起動時は赤

  // --- WiFi/MQTT接続 ---
  setup_wifi();
  client.setServer(MQTT_HOST, MQTT_PORT);
  client.setCallback(callback);
}

// **********************************
// * メインループ (修正)
// **********************************
void loop() {
  // MQTT接続維持
  if (!client.connected()) {
    reconnect();
  }
  client.loop(); // MQTTメッセージの受信処理

  // 単体LEDのチカチカ処理
  handleLedBlink();

  // --- ハートビート (生存通知) (ここから追加) ---
  unsigned long now = millis();
  if (now - lastHeartbeat > HEARTBEAT_MS) {
    lastHeartbeat = now;
    Serial.println("[MQTT] Sending heartbeat (ESP2_LED)...");
    // 1号機(alive)と区別するため、ペイロードを変更
    client.publish("/4dx/heartbeat", "alive_esp2_led");
  }
  // (ここまで追加)
}

// **********************************
// * WiFi / MQTT 関連
// **********************************

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  unsigned long now = millis();
  if (now - lastReconnectAttempt > 5000) {
    lastReconnectAttempt = now;
    Serial.print("[MQTT] Attempting connection...");
    
    if (client.connect(MQTT_CLIENT_ID)) {
      Serial.println("connected!");
      // 接続成功時にトピックを購読(Subscribe)
      subscribeTopics();
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
    }
  }
}

void subscribeTopics() {
  // このESPが受信するトピックを定義
  client.subscribe("/4dx/light");
  client.subscribe("/4dx/color");

  Serial.println("[MQTT] Subscribed to /4dx/light");
  Serial.println("[MQTT] Subscribed to /4dx/color");
}

// **********************************
// * MQTTメッセージ受信処理
// **********************************

void callback(char* topicStr, byte* payloadB, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topicStr);
  Serial.print("] ");

  // ペイロードを文字列に変換
  String payload = "";
  for (int i = 0; i < length; i++) {
    payload += (char)payloadB[i];
  }
  Serial.println(payload);

  String topic = String(topicStr);
  payload.toUpperCase(); // ペイロードを大文字に統一 (RED, red どちらでもOKに)

  // --- トピックに応じて処理を分岐 ---

  // (1) 単体LEDの制御
  if (topic == "/4dx/light") {
    if (payload == "ON") {
      currentLedMode = LED_ON;
      // (修正) ONにするためLOWを出力
      digitalWrite(SINGLE_LED_PIN, LOW); 
    } else if (payload == "OFF") {
      currentLedMode = LED_OFF;
      // (修正) OFFにするためHIGHを出力
      digitalWrite(SINGLE_LED_PIN, HIGH); 
    } else if (payload == "BLINK_SLOW") {
      currentLedMode = LED_BLINK_SLOW;
    } else if (payload == "BLINK_FAST") {
      currentLedMode = LED_BLINK_FAST;
    }
  }

  // (2) RGB LEDテープの制御 (ご要望の6色のみ)
  if (topic == "/4dx/color") {
    if (payload == "RED") {
      setColor(255, 0, 0);
    } else if (payload == "GREEN") {
      setColor(0, 255, 0);
    } else if (payload == "BLUE") {
      setColor(0, 0, 255);
    } else if (payload == "CYAN") {
      setColor(0, 255, 255);
    } else if (payload == "YELLOW") {
      setColor(255, 255, 0);
    } else if (payload == "PURPLE") {
      setColor(128, 0, 128);
    }
    // OFFやその他の色は無視 (ご要望)
  }
}

// **********************************
// * LED制御ヘルパー
// **********************************

/**
 * @brief RGB LEDの色を設定 (0-255指定)
 * @param r 赤 (0-255)
 * @param g 緑 (0-255)
 * @param b 青 (0-255)
 * (動作確認が取れたロジック)
 */
void setColor(int r, int g, int b) {
  // 0-255 の値を 0-1023 (PWM範囲) にマッピング
  int r_pwm = map(r, 0, 255, 0, PWM_MAX);
  int g_pwm = map(g, 0, 255, 0, PWM_MAX);
  int b_pwm = map(b, 0, 255, 0, PWM_MAX);

  // 共通アノード接続のため、PWM値を反転させる
  // (0が最大輝度, 1023が消灯)
  r_pwm = PWM_MAX - r_pwm;
  g_pwm = PWM_MAX - g_pwm;
  b_pwm = PWM_MAX - b_pwm;

  Serial.printf("Setting Color (R:%d, G:%d, B:%d) -> PWM (R:%d, G:%d, B:%d)\n", r, g, b, r_pwm, g_pwm, b_pwm);

  // PWM (analogWrite) で出力
  analogWrite(R_PIN, r_pwm);
  analogWrite(G_PIN, g_pwm);
  analogWrite(B_PIN, b_pwm);
}

/**
 * @brief 単体LEDのチカチカ処理 (loop()から毎周期呼び出す)
 */
void handleLedBlink() {
  unsigned long now = millis();
  unsigned long interval = 0;

  // モードによって点滅間隔(interval)を決定
  if (currentLedMode == LED_BLINK_SLOW) {
    interval = 500; // ゆっくり (500ms間隔)
  } else if (currentLedMode == LED_BLINK_FAST) {
    interval = 150; // 早く (150ms間隔)
  } else {
    return; // ON または OFF モードなら何もしない
  }

  // intervalの時間が経過していたら
  if (now - lastBlinkTime > interval) {
    lastBlinkTime = now;
    // LEDの状態を反転
    ledState = !ledState; 
    // (修正) ledState (bool) と実際の出力 (HIGH/LOW) を反転させる
    // ledState が true (1) の時 -> LOW (0) を出力
    // ledState が false (0) の時 -> HIGH (1) を出力
    digitalWrite(SINGLE_LED_PIN, !ledState);
  }
}

