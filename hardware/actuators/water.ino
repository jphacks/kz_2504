/*
  Water Controller for 4D Home Project

  サーボモーターを使用して水しぶきエフェクトを制御します。
  Raspberry Piから "SPLASH" コマンドをシリアル通信で受信すると、
  指定された角度に素早く動いて元に戻るアクションを実行します。

  - シリアルポートをリッスン (9600 baud)
  - 'SPLASH' コマンドを待機
  - SERVO_PINで指定されたピンのサーボを制御
*/

// Arduino標準のサーボモーターライブラリを読み込みます
#include <Servo.h>

// --- 設定項目 ---
// サーボモーターを接続するピン番号 (PWM対応ピンを推奨します。例: 3, 5, 6, 9, 10, 11)
const int SERVO_PIN = 9;

// サーボの角度
const int NEUTRAL_ANGLE = 0; // 待機中の角度
const int ACTION_ANGLE = 180;   // 水を出すとき（作動時）の角度

// アクションの速さに関連する待ち時間 (ミリ秒)
const int ACTION_DELAY = 1000; // 0度まで動いた後、元に戻るまでの待ち時間 (1秒)

// サーボモーターのオブジェクトを作成
Servo waterServo;

void setup() {
  // サーボモーターを指定したピンに接続
  waterServo.attach(SERVO_PIN);
  // 最初に待機位置にサーボを動かす
  waterServo.write(NEUTRAL_ANGLE);
  
  // ラズベリーパイとのシリアル通信を開始 (9600 bps)
  Serial.begin(9600);
  Serial.println("Water Controller Initialized. Waiting for 'SPLASH' command...");
  Serial.println("INFO: Make sure to use an external power supply for the servo.");
}

void loop() {
  // シリアルポートにデータが送られてきたか確認
  if (Serial.available() > 0) {
    // 改行コードまでコマンドを読み込む
    String command = Serial.readStringUntil('\n');
    // コマンド前後の余白を削除
    command.trim();
    
    // 受信したコマンドが "SPLASH" だったら
    if (command == "SPLASH") {
      Serial.println("Received: SPLASH -> Performing splash action...");
      
      // 「プシュッ」というアクションを実行
      waterServo.write(ACTION_ANGLE);   // 0度へ動かす
      delay(ACTION_DELAY);              // 1秒待つ
      waterServo.write(NEUTRAL_ANGLE);  // すぐに180度へ戻す
    }
  }
}

