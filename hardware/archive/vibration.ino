/* ===== ESP-12E (ESP8266) ハプティクス簡易制御 MQTT 対応 (最適化版) =====
    Topics:
      /vibration/all    -> ON（定常強振動）
      /vibration/heart  -> HEART（ゆっくり鼓動）
      /vibration/off    -> OFF（やさしく停止）
============================================================================= */
#include <ESP8266WiFi.h>
#include <PubSubClient.h>

/* ===== Wi-Fi / MQTT 設定 ===== */
const char* WIFI_SSID = "KIT-GUEST";   // ここをあなたのSSIDに
const char* WIFI_PASS = "Lw8hjXtr";            // パス不要なら空欄のまま
const char* MQTT_HOST = "172.18.28.55";         // ← ラズパイのIPに変更
const uint16_t MQTT_PORT = 1883;

const char* TOPIC_ALL   = "/vibration/all";
const char* TOPIC_HEART = "/vibration/heart";
const char* TOPIC_OFF   = "/vibration/off";

/* ===== ピン定義 ===== */
const int PIN_BIG_L = 5;    // D1 on NodeMCU
const int PIN_BIG_R = 4;    // D2 on NodeMCU
const int PIN_MID   = 14;   // D5 on NodeMCU
const int PIN_SMALL = 12;   // D6 on NodeMCU

/* ===== PWM設定 ===== */
const int PWM_FREQ  = 2000;
const int PWM_RANGE = 1023;

inline int clampPct(int p){ if(p<0) p=0; if(p>100) p=100; return p; }
inline int pctToPwm(int p){ return (PWM_RANGE * clampPct(p)) / 100; }
inline void writePct(int pin, int p){ analogWrite(pin, pctToPwm(p)); }
inline void setAllPct(int bl,int br,int md,int sm){
  writePct(PIN_BIG_L, bl);
  writePct(PIN_BIG_R, br);
  writePct(PIN_MID,   md);
  writePct(PIN_SMALL, sm);
}
inline void allOff(){ setAllPct(0,0,0,0); }

enum Mode { MODE_IDLE, MODE_ON, MODE_HEART };
volatile Mode mode = MODE_IDLE;

/* ===== HEART（心拍・ゆっくり） ===== */
const int HEART_BPM = 52;
const int HEART_CYCLE = 60000 / HEART_BPM;
const int LUB_RISE = 80, LUB_HOLD = 110, LUB_FALL = 180;
const int GAP_BETWEEN = 160;
const int DUB_LEN = 140;
const int HEART_ELAPSED_APPROX = (LUB_RISE + LUB_HOLD + LUB_FALL) + 60 + GAP_BETWEEN + DUB_LEN;
unsigned long heartPhaseStart = 0;
int heartPhase = 0;

void linearPulsePct(int pin, int peakPct, int rise_ms, int hold_ms, int fall_ms) {
  const int step = 5;
  for (int t=0; t<rise_ms; t+=step){ delay(step); writePct(pin, (long)peakPct * t / rise_ms); }
  writePct(pin, peakPct);
  delay(hold_ms);
  for (int t=fall_ms; t>0; t-=step){ delay(step); writePct(pin, (long)peakPct * t / fall_ms); }
  writePct(pin, 0);
}

/* ===== ON（定常） ===== */
void fx_on() { setAllPct(90, 90, 45, 25); }

/* ===== OFF（やさしく停止） ===== */
void fx_stop() {
  setAllPct(25,25,12,6); delay(50);
  setAllPct(12,12,6,3);  delay(50);
  allOff();
}

/* ====== Wi-Fi / MQTT ====== */
WiFiClient espClient;
PubSubClient mqtt(espClient);

void ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Wi-Fi connecting");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println();
  Serial.print("Connected! IP=");
  Serial.println(WiFi.localIP());
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  Serial.print("[MQTT Received] Topic: ");
  Serial.println(topic);

  if (strcmp(topic, TOPIC_ALL) == 0) {
    mode = MODE_ON;
    Serial.println("  -> Action: Set mode to ON");
  } else if (strcmp(topic, TOPIC_HEART) == 0) {
    mode = MODE_HEART;
    heartPhase = 0;
    heartPhaseStart = millis();
    Serial.println("  -> Action: Set mode to HEARTBEAT");
  } else if (strcmp(topic, TOPIC_OFF) == 0) {
    mode = MODE_IDLE;
    fx_stop();
    Serial.println("  -> Action: Set mode to IDLE and stop motors");
  }
}

void ensureMQTT() {
  if (mqtt.connected()) return;
  while (!mqtt.connected()) {
    String cid = "esp8266-" + String(ESP.getChipId(), HEX);
    if (mqtt.connect(cid.c_str())) {
      mqtt.subscribe("/vibration/#", 1);
      Serial.println("MQTT connected & subscribed.");
    } else {
      Serial.print("MQTT connect failed, rc=");
      Serial.print(mqtt.state());
      Serial.println(". Retrying...");
      delay(1000);
    }
  }
}

/* ===== Arduino標準 ===== */
void setup() {
  Serial.begin(115200);
  pinMode(PIN_BIG_L, OUTPUT); pinMode(PIN_BIG_R, OUTPUT);
  pinMode(PIN_MID,   OUTPUT); pinMode(PIN_SMALL, OUTPUT);
  analogWriteFreq(PWM_FREQ);
  analogWriteRange(PWM_RANGE);
  allOff();
  ensureWiFi();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);
  ensureMQTT();
  Serial.println(F("[MQTT Haptics] Ready. Topics: /vibration/all, /vibration/heart, /vibration/off"));
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) ensureWiFi();
  if (!mqtt.connected()) ensureMQTT();
  mqtt.loop();

  if (mode == MODE_ON) {
    fx_on();
    delay(10);
  } else if (mode == MODE_HEART) {
    unsigned long now = millis();
    switch (heartPhase) {
      case 0: // LUB
        linearPulsePct(PIN_BIG_L, 100, LUB_RISE, LUB_HOLD, LUB_FALL);
        writePct(PIN_BIG_R, 55); delay(60); writePct(PIN_BIG_R, 0);
        heartPhase = 1; heartPhaseStart = millis();
        break;
      case 1: // 間
        if (now - heartPhaseStart >= (unsigned long)GAP_BETWEEN) {
          heartPhase = 2; heartPhaseStart = now;
        } else { delay(5); }
        break;
      case 2: // DUB
        writePct(PIN_BIG_R, 80); writePct(PIN_MID, 30); writePct(PIN_SMALL, 15);
        if (now - heartPhaseStart >= (unsigned long)DUB_LEN) {
          allOff();
          heartPhase = 3; heartPhaseStart = millis();
        } else { delay(5); }
        break;
      case 3: // 休符
        int rest = HEART_CYCLE - HEART_ELAPSED_APPROX;
        if (rest < 250) rest = 250;
        if (now - heartPhaseStart >= (unsigned long)rest) {
          heartPhase = 0; heartPhaseStart = millis();
        } else { delay(5); }
        break;
    }
  } else { // MODE_IDLE
    allOff();
    delay(10);
  }
}
