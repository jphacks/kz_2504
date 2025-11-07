#!/bin/bash
# 4DX@HOME Raspberry Pi Server - Dependency Installation Script

echo "========================================="
echo "4DX@HOME Raspberry Pi Server"
echo "依存関係インストールスクリプト"
echo "========================================="

# 1. システムパッケージの更新
echo "[1/5] システムパッケージを更新中..."
sudo apt-get update
sudo apt-get upgrade -y

# 2. 必要なシステムパッケージのインストール
echo "[2/5] システムパッケージをインストール中..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    mosquitto \
    mosquitto-clients \
    git

# 3. Mosquitto MQTTブローカーの設定
echo "[3/5] MQTTブローカーを設定中..."
sudo systemctl enable mosquitto
sudo systemctl start mosquitto

# MQTTブローカーの接続確認
if systemctl is-active --quiet mosquitto; then
    echo "✓ Mosquittoが正常に起動しました"
else
    echo "✗ Mosquittoの起動に失敗しました"
    exit 1
fi

# 4. Python仮想環境の作成
echo "[4/5] Python仮想環境を作成中..."
cd "$(dirname "$0")/.." || exit 1
python3 -m venv venv
source venv/bin/activate

# 5. Pythonパッケージのインストール
echo "[5/5] Pythonパッケージをインストール中..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "========================================="
echo "✓ 依存関係のインストールが完了しました"
echo "========================================="
echo ""
echo "次のステップ:"
echo "1. .envファイルを作成してください:"
echo "   cp .env.example .env"
echo "   nano .env"
echo ""
echo "2. サーバーを起動してください:"
echo "   source venv/bin/activate"
echo "   python main.py <session_id>"
echo ""
echo "3. systemdサービスとして自動起動する場合:"
echo "   sudo bash scripts/setup_systemd.sh"
echo ""
