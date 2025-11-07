#!/bin/bash
# 4DX@HOME Raspberry Pi Server - systemd Service Setup Script

SERVICE_NAME="4dx-home"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
USER="$(whoami)"

echo "========================================="
echo "4DX@HOME systemdサービス設定スクリプト"
echo "========================================="
echo "プロジェクトディレクトリ: $PROJECT_DIR"
echo "実行ユーザー: $USER"
echo ""

# セッションIDの入力
read -p "セッションID (デフォルト: default_session): " SESSION_ID
SESSION_ID=${SESSION_ID:-default_session}

# systemdサービスファイルの作成
echo "[1/3] systemdサービスファイルを作成中..."
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=4DX@HOME Raspberry Pi Server
After=network.target mosquitto.service
Wants=mosquitto.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/main.py $SESSION_ID
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=4dx-home

[Install]
WantedBy=multi-user.target
EOF

echo "✓ サービスファイルを作成しました: $SERVICE_FILE"

# systemdの再読み込み
echo "[2/3] systemdを再読み込み中..."
sudo systemctl daemon-reload

# サービスの有効化
echo "[3/3] サービスを有効化中..."
sudo systemctl enable "$SERVICE_NAME.service"

echo ""
echo "========================================="
echo "✓ systemdサービスの設定が完了しました"
echo "========================================="
echo ""
echo "サービスの操作方法:"
echo "  起動:   sudo systemctl start $SERVICE_NAME"
echo "  停止:   sudo systemctl stop $SERVICE_NAME"
echo "  再起動: sudo systemctl restart $SERVICE_NAME"
echo "  状態:   sudo systemctl status $SERVICE_NAME"
echo "  ログ:   sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "自動起動設定:"
echo "  有効化: sudo systemctl enable $SERVICE_NAME"
echo "  無効化: sudo systemctl disable $SERVICE_NAME"
echo ""
