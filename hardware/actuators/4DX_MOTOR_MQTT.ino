#include <ESP8266WiFi.h>
#include <PubSubClient.h>

// *******************************************************************
// ★★★ デバイス設定 (ESP4に書き込む時だけ 4 に変更) ★★★
// *******************************************************************
#define DEVICE_ID 4 // 3 = ESP3 (Motor 1), 4 = ESP4 (Motor 2)
// *******************************************************************


// ======== WiFi/MQTT 設定 ========
const char* WIFI_SSID     = "PiMQTT-AP";
const char* WIFI_PASSWORD = "AtHome1234";
const char* MQTT_HOST     = "192.168.4.1";
const uint16_t MQTT_PORT  = 1883;

// ======== デバイスIDに応じて設定を自動分岐 ========
#if DEVICE_ID == 3
  const char* MQTT_CLIENT_ID    = "ESP8266_Motor_1";
  const char* MQTT_CONTROL_TOPIC = "/4dx/motor1/control";
  const char* HEARTBEAT_PAYLOAD = "alive_esp3_motor1";
#elif DEVICE_ID == 4
  const char* MQTT_CLIENT_ID    = "ESP8266_Motor_2";
  const char* MQTT_CONTROL_TOPIC = "/4dx/motor2/control";
  const char* HEARTBEAT_PAYLOAD = "alive_esp4_motor2";
#else
  #error "DEVICE_ID must be 3 or 4"
#endif

// ======== (★ロジックV4) ピン設定 ========
const int MOTOR_PIN_D5 = 14; // 振動 強 (STRONG)
const int MOTOR_PIN_D6 = 12; // 振動 中強 (MEDIUM_STRONG)
const int MOTOR_PIN_D7 = 13; // 振動 中強 / 中弱 (MEDIUM_STRONG / MEDIUM_WEAK)
const int MOTOR_PIN_D8 = 15; // 振動 弱 (WEAK)

// ======== グローバル変数 ========
WiFiClient espClient;
PubSubClient client(espClient);
unsigned long lastReconnectAttempt = 0;
unsigned long lastHeartbeat = 0;
const unsigned long HEARTBEAT_MS = 10000; // 10秒に1回

// --- モーター制御モード ---
enum MotorMode {
  MOTOR_OFF,
  MOTOR_WEAK,
  MOTOR_MEDIUM_WEAK,
  MOTOR_MEDIUM_STRONG,
  MOTOR_STRONG,
  MOTOR_HEARTBEAT,
  MOTOR_RUMBLE_FAST, 
  MOTOR_RUMBLE_SLOW
};
MotorMode currentMotorMode = MOTOR_OFF;

// --- ノンブロッキング制御用タイマー ---
unsigned long lastPatternTime = 0;
int patternStep = 0;

// **********************************
// * セットアップ処理
// **********************************
void setup() {
  Serial.begin(115200);
  Serial.println("Booting Motor Controller (Logic V5)..."); // バージョン更新
  Serial.printf("DEVICE_ID: %d\n", DEVICE_ID);

  // --- ピンモード設定 ---
  pinMode(MOTOR_PIN_D5, OUTPUT);
  pinMode(MOTOR_PIN_D6, OUTPUT);
  pinMode(MOTOR_PIN_D7, OUTPUT);
  pinMode(MOTOR_PIN_D8, OUTPUT);
  
  // 初期状態は全OFF
  setAllMotors(LOW);

  // --- WiFi/MQTT接続 ---
  setup_wifi();
  client.setServer(MQTT_HOST, MQTT_PORT);
  client.setCallback(callback);
}

// **********************************
// * メインループ
// **********************************
void loop() {
  // MQTT接続維持
  if (!client.connected()) {
    reconnect();
  }
  client.loop(); // MQTTメッセージの受信処理

  // ハートビート送信
  unsigned long now = millis();
  if (now - lastHeartbeat > HEARTBEAT_MS) {
    lastHeartbeat = now;
    client.publish("/4dx/heartbeat", HEARTBEAT_PAYLOAD);
    Serial.println("[MQTT] Sending heartbeat...");
  }

  // ノンブロッキング モーター制御
  handleMotors(now);
}

// **********************************
// * WiFi / MQTT 関連
// **********************************

void setup_wifi() {
  delay(10);
  Serial.print("Connecting to ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
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
      client.subscribe(MQTT_CONTROL_TOPIC);
      Serial.printf("[MQTT] Subscribed to %s\n", MQTT_CONTROL_TOPIC);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
    }
  }
}

// **********************************
// * MQTTメッセージ受信処理
// **********************************
void callback(char* topicStr, byte* payloadB, unsigned int length) {
  // ペイロードをクリーンなStringに変換
  String payload = "";
  for (int i = 0; i < length; i++) {
    payload += (char)payloadB[i];
  }
  payload.trim();
  
  Serial.print("Message arrived [");
  Serial.print(topicStr);
  Serial.print("] ");
  Serial.println(payload);

  // モード切替時は、一旦ステートをリセット
  patternStep = 0;
  lastPatternTime = 0;
  
  if (payload == "STRONG") {
    currentMotorMode = MOTOR_STRONG;
  } else if (payload == "MEDIUM_STRONG") {
    currentMotorMode = MOTOR_MEDIUM_STRONG;
  } else if (payload == "MEDIUM_WEAK") {
    currentMotorMode = MOTOR_MEDIUM_WEAK;
  } else if (payload == "WEAK") {
    currentMotorMode = MOTOR_WEAK;
  } else if (payload == "HEARTBEAT") {
    currentMotorMode = MOTOR_HEARTBEAT;
  } else if (payload == "RUMBLE_FAST") { 
    currentMotorMode = MOTOR_RUMBLE_FAST;
  } else if (payload == "RUMBLE_SLOW") { 
    currentMotorMode = MOTOR_RUMBLE_SLOW;
  } else { // "OFF" または不明なコマンド
    currentMotorMode = MOTOR_OFF;
  }
}

// **********************************
// * モーター制御ヘルパー (★ロジックV5 修正)
// **********************************

/**
 * @brief モーター制御のメイン関数 (loopから毎周期呼ばれる)
 */
void handleMotors(unsigned long now) {
  
  // ----- モードに応じた処理 -----
  
  switch (currentMotorMode) {
    
    case MOTOR_OFF:
      setAllMotors(LOW);
      break;
      
    case MOTOR_WEAK: // 弱 (D8)
      // 「振動弱はD8のモーターを動かす」
      digitalWrite(MOTOR_PIN_D5, LOW);
      digitalWrite(MOTOR_PIN_D6, LOW);
      digitalWrite(MOTOR_PIN_D7, LOW);
      digitalWrite(MOTOR_PIN_D8, HIGH); // ★
      break;
      
    case MOTOR_MEDIUM_WEAK: // 中弱 (D7)
      // 「振動中弱はD7のモーターを動かす」
      digitalWrite(MOTOR_PIN_D5, LOW);
      digitalWrite(MOTOR_PIN_D6, LOW);
      digitalWrite(MOTOR_PIN_D7, HIGH); // ★
      digitalWrite(MOTOR_PIN_D8, LOW);
      break;
      
    case MOTOR_MEDIUM_STRONG: // 中強 (D6 + D7)
      // 「振動中強はD6とD7のモーターを動かす」
      digitalWrite(MOTOR_PIN_D5, LOW);
      digitalWrite(MOTOR_PIN_D6, HIGH); // ★
      digitalWrite(MOTOR_PIN_D7, HIGH); // ★
      digitalWrite(MOTOR_PIN_D8, LOW);
      break;
      
    case MOTOR_STRONG: // 強 (全部)
      // (★V5 修正) 「振動強は全部のモーターを回してほしい」
      setAllMotors(HIGH); // ★
      break;

    // ----- ここからノンブロッキング・パターン -----
    
    case MOTOR_HEARTBEAT: // 心拍 (ドッ..クン.......ドッ..クン...)
      // (★ロジックV4 修正)
      // ドッ = 中弱 (D7), クン = (V4の)強 (D5) -> V5ではロジック維持
      // ステップ0: (1.5秒待機) ドッ (中弱 D7)
      if (patternStep == 0 && (now - lastPatternTime > 1500)) { 
        setAllMotors(LOW);
        digitalWrite(MOTOR_PIN_D7, HIGH); // 中弱(D7)
        lastPatternTime = now;
        patternStep = 1;
      }
      // ステップ1: (200ms) OFF
      else if (patternStep == 1 && (now - lastPatternTime > 200)) { 
        setAllMotors(LOW);
        lastPatternTime = now;
        patternStep = 2;
      }
      // ステップ2: (100ms) クン (V4の強 D5)
      else if (patternStep == 2 && (now - lastPatternTime > 100)) { 
        digitalWrite(MOTOR_PIN_D5, HIGH); // V4の強(D5)
        lastPatternTime = now;
        patternStep = 3;
      }
      // ステップ3: (150ms) OFF
      else if (patternStep == 3 && (now - lastPatternTime > 150)) { 
        setAllMotors(LOW);
        lastPatternTime = now;
        patternStep = 0; // ループ
      }
      break;
      
    case MOTOR_RUMBLE_FAST: // (変更なし) ドンドンドン (速)
      // ステップ0: (0.15秒待機) ドン (全モーター)
      if (patternStep == 0 && (now - lastPatternTime > 150)) {
        setAllMotors(HIGH);
        lastPatternTime = now;
        patternStep = 1;
      }
      // ステップ1: (100ms) OFF
      else if (patternStep == 1 && (now - lastPatternTime > 100)) {
        setAllMotors(LOW);
        lastPatternTime = now;
        patternStep = 0; // ループ
      }
      break;
      
    case MOTOR_RUMBLE_SLOW: // (変更なし) ドン...ドン... (遅)
      // ステップ0: (0.3秒待機) ドン (全モーター)
      if (patternStep == 0 && (now - lastPatternTime > 300)) {
        setAllMotors(HIGH);
        lastPatternTime = now;
        patternStep = 1;
      }
      // ステップ1: (300ms) OFF
      else if (patternStep == 1 && (now - lastPatternTime > 300)) {
        setAllMotors(LOW);
        lastPatternTime = now;
        patternStep = 0; // ループ
      }
      break;
  }
}

/**
 * @brief 全モーターの ON/OFF を一括設定
 */
void setAllMotors(bool state) {
  digitalWrite(MOTOR_PIN_D5, state);
  digitalWrite(MOTOR_PIN_D6, state);
  digitalWrite(MOTOR_PIN_D7, state);
  digitalWrite(MOTOR_PIN_D8, state);
}

