#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <Servo.h> // Servoライブラリ

// ======== 設定（編集してください） ========
const char* WIFI_SSID     = "PiMQTT-AP";
const char* WIFI_PASSWORD = "AtHome1234";

const char* MQTT_HOST = "192.168.4.1"; // MQTTブローカーIP
const uint16_t MQTT_PORT = 1883;       // 通常 1883
const char* MQTT_CLIENT_ID = "ESP8266_4DX_Client"; // 固有のクライアントID

// ======== ピン設定 (ESP-12E / NodeMCU) ========

// D5ピン (GPIO 14)
const int SERVO_PIN = 14; 
// D2ピン (GPIO 4)
const int MOTOR_PIN = 4;  
// 内蔵LED (D4 = GPIO 2)
const int LED_PIN = 2;          
const bool LED_ACTIVE_LOW = true; // NodeMCUの内蔵LEDはLOWで点灯

// ======== 動作設定 ========
const int SERVO_START_POS = 180; // サーボの初期（戻る）位置
const int SERVO_END_POS   = 0;   // サーボの動作（行く）位置

// ハートビート間隔(ms)
const unsigned long HEARTBEAT_MS = 10000;
// 再接続リトライ間隔(ms)
const unsigned long RECONNECT_MS = 5000;

// ======== グローバル変数 ========
WiFiClient espClient;
PubSubClient client(espClient);
Servo myServo;

unsigned long lastHeartbeat = 0;
unsigned long lastReconnectAttempt = 0;

// 水（サーボ）のループ再生フラグ
bool waterLoopActive = false;
// サーボがattachされているか
bool servoAttached = false;


// ======== プロトタイプ宣言 ========
void setup_wifi();
void callback(char* topic, byte* payload, unsigned int length);
void reconnect();
void ledOn();
void ledOff();
void checkServoAttach();
void checkServoDetach();
void triggerWater();
void resetServo();

// ======== セットアップ ========
void setup() {
  Serial.begin(115200); // ESP8266では115200が一般的
  Serial.println("\n[Boot] Starting...");

  // ピンモード設定
  pinMode(LED_PIN, OUTPUT);
  pinMode(MOTOR_PIN, OUTPUT);
  
  digitalWrite(MOTOR_PIN, LOW); // モーターは初期状態でOFF
  ledOff(); // LED初期状態

  // サーボの初期位置設定
  Serial.println("[Setup] Initializing Servo...");
  myServo.attach(SERVO_PIN);
  servoAttached = true;
  myServo.write(SERVO_START_POS); // 180度の位置に設定
  delay(1000); // 180度に移動するのを待つ
  myServo.detach(); // 動力を抜いて待機
  servoAttached = false;
  Serial.println("[Setup] Servo set to 180 deg and detached.");

  setup_wifi(); // WiFi接続
  
  client.setServer(MQTT_HOST, MQTT_PORT);
  client.setCallback(callback); // MQTTコールバック関数を設定

  Serial.println("[Setup] Ready.");
}

// ======== WiFi接続 ========
void setup_wifi() {
  delay(10);
  Serial.print("[WiFi] Connecting to ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA); // STAモード（子機）
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int wifiStatusCount = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    ledOn(); // 接続試行中はLED点灯
    wifiStatusCount++;
    if (wifiStatusCount > 40) { // 20秒待ってもダメなら
        Serial.println("\n[WiFi] Failed to connect. Restarting...");
        ESP.restart(); // 再起動
    }
  }
  
  ledOff(); // 接続完了したらLED消灯
  Serial.println("\n[WiFi] Connected.");
  Serial.print("[WiFi] IP address: ");
  Serial.println(WiFi.localIP());
}

// ======== MQTTコールバック (メッセージ受信処理) ========
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("[MQTT] Message arrived [");
  Serial.print(topic);
  Serial.print("] ");

  // ペイロードをNULL終端文字列にコピー
  char msg[length + 1];
  memcpy(msg, payload, length);
  msg[length] = '\0';
  String payloadStr = String(msg);
  Serial.println(payloadStr);

  // --- /4dx/water ---
  if (strcmp(topic, "/4dx/water") == 0) {
    Serial.println("[Action] Triggering Water (Servo)");
    if (!waterLoopActive) { // ループ中でなければ単発動作
      triggerWater();
    }
  }
  // --- /4dx/wind ---
  else if (strcmp(topic, "/4dx/wind") == 0) {
    if (payloadStr.equalsIgnoreCase("ON")) {
      Serial.println("[Action] Wind: ON");
      digitalWrite(MOTOR_PIN, HIGH);
    } else if (payloadStr.equalsIgnoreCase("OFF")) {
      Serial.println("[Action] Wind: OFF");
      digitalWrite(MOTOR_PIN, LOW);
    }
  }
  // --- /4dx/water/loop/on ---
  else if (strcmp(topic, "/4dx/water/loop/on") == 0) {
    Serial.println("[Action] Water Loop: ON");
    waterLoopActive = true;
    checkServoAttach(); // ループ開始時にアタッチ
  }
  // --- /4dx/water/loop/off ---
  else if (strcmp(topic, "/4dx/water/loop/off") == 0) {
    Serial.println("[Action] Water Loop: OFF");
    waterLoopActive = false;
    resetServo(); // ループ停止時に初期位置に戻してデタッチ
  }
}

// ======== MQTT再接続 ========
void reconnect() {
  // MQTTが切断されていたら再接続を試みる
  if (!client.connected()) {
    unsigned long now = millis();
    if (now - lastReconnectAttempt > RECONNECT_MS) {
      lastReconnectAttempt = now;
      Serial.print("[MQTT] Attempting connection...");
      ledOn(); // 接続試行中
      
      if (client.connect(MQTT_CLIENT_ID)) {
        Serial.println(" connected.");
        ledOff();
        
        // 監視するトピックを購読 (Subscribe)
        client.subscribe("/4dx/water");
        client.subscribe("/4dx/wind");
        client.subscribe("/4dx/water/loop/on");
        client.subscribe("/4dx/water/loop/off");
        Serial.println("[MQTT] Subscribed to topics.");
        
      } else {
        Serial.print(" failed, rc=");
        Serial.print(client.state());
        Serial.println(" try again in 5 seconds");
        ledOff();
      }
    }
  }
}

// ======== メインループ ========
void loop() {
  
  // WiFi接続チェック
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Connection lost. Reconnecting...");
    setup_wifi();
  }

  // MQTT接続チェックと再接続
  if (!client.connected()) {
    reconnect();
  }
  
  // MQTTクライアントのループ処理 (必須)
  client.loop();

  unsigned long now = millis();

  // --- ハートビート (生存通知) ---
  if (now - lastHeartbeat > HEARTBEAT_MS) {
    lastHeartbeat = now;
    Serial.println("[MQTT] Sending heartbeat...");
    client.publish("/4dx/heartbeat", "alive");
    
    // ハートビート時にLEDを短く点滅
    ledOn();
    delay(50);
    ledOff();
  }

  // --- 水のループ処理 ---
  if (waterLoopActive) {
    // waterLoopActiveがtrueの間、triggerWater()を実行し続ける
    triggerWater();
  }
}

// ======== ヘルパー関数 ========

// LED点灯 (Active Low対応)
void ledOn() {
  digitalWrite(LED_PIN, LED_ACTIVE_LOW ? LOW : HIGH);
}

// LED消灯 (Active Low対応)
void ledOff() {
  digitalWrite(LED_PIN, LED_ACTIVE_LOW ? HIGH : LOW);
}

// サーボがデタッチされていたらアタッチする
void checkServoAttach() {
  if (!servoAttached) {
    Serial.println("[Servo] Attaching...");
    myServo.attach(SERVO_PIN);
    servoAttached = true;
    delay(500); // attachが安定するまで待つ
  }
}

// (ループ中でない限り)サーボをデタッチする
void checkServoDetach() {
  if (servoAttached && !waterLoopActive) {
    Serial.println("[Servo] Detaching...");
    myServo.detach();
    servoAttached = false;
  }
}

// 水の動作（サーボ往復）
void triggerWater() {
  checkServoAttach(); // 必要ならアタッチ

  Serial.println("[Servo] Moving to END (0 deg)...");
  myServo.write(SERVO_END_POS); // 0度へ移動
  delay(1000); // 移動待機

  Serial.println("[Servo] Moving to START (180 deg)...");
  myServo.write(SERVO_START_POS); // 180度へ戻る
  delay(1000); // 移動待機
  
  checkServoDetach(); // ループ中でなければデタッチ
}

// サーボを初期位置に戻してデタッチ
void resetServo() {
  checkServoAttach(); // 必要ならアタッチ
  
  Serial.println("[Servo] Resetting to START (180 deg)...");
  myServo.write(SERVO_START_POS);
  delay(1000);
  
  // resetServoはループオフ時に呼ばれる前提
  if (servoAttached) {
    Serial.println("[Servo] Detaching...");
    myServo.detach();
    servoAttached = false;
  }
}
