"""
4DX@HOME MQTT Broker Client
4DXHOMEの既存MQTT通信ロジックを継承し、ESP-12Eデバイスへの制御を行う
"""

import logging
import paho.mqtt.client as mqtt
from typing import Optional, Callable, Dict
from config import Config

logger = logging.getLogger(__name__)


class MQTTBrokerClient:
    """MQTT Broker接続・制御クライアント"""
    
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.is_connected: bool = False
        self.on_heartbeat_callback: Optional[Callable[[str], None]] = None
        
    def connect(self) -> None:
        """MQTTブローカーに接続"""
        try:
            self.client = mqtt.Client(client_id=Config.MQTT_CLIENT_ID)
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            logger.info(
                f"MQTT接続開始: {Config.MQTT_BROKER_HOST}:{Config.MQTT_BROKER_PORT}"
            )
            
            self.client.connect(
                Config.MQTT_BROKER_HOST,
                Config.MQTT_BROKER_PORT,
                Config.MQTT_KEEPALIVE
            )
            
            # ループ開始（バックグラウンド）
            self.client.loop_start()
            
        except Exception as e:
            logger.error(f"MQTT接続エラー: {e}", exc_info=True)
            raise
    
    def disconnect(self) -> None:
        """MQTTブローカーから切断"""
        if self.client:
            logger.info("MQTT切断開始")
            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False
    
    def publish(self, topic: str, payload: str, qos: int = 1) -> None:
        """MQTTメッセージを配信
        
        Args:
            topic: MQTTトピック (例: /4dx/water)
            payload: ペイロード文字列 (例: trigger, STRONG)
            qos: QoSレベル (0, 1, 2)
        """
        if not self.is_connected:
            logger.warning(f"MQTT未接続のため配信スキップ: {topic} = {payload}")
            return
        
        try:
            result = self.client.publish(topic, payload, qos=qos)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"MQTT配信成功: {topic} = {payload}")
            else:
                logger.error(f"MQTT配信失敗: {topic} = {payload}, rc={result.rc}")
        
        except Exception as e:
            logger.error(f"MQTT配信エラー: {e}", exc_info=True)
    
    def subscribe_heartbeat(self, callback: Callable[[str], None]) -> None:
        """ハートビートトピックをサブスクライブ
        
        Args:
            callback: デバイスIDを受け取るコールバック関数
        """
        self.on_heartbeat_callback = callback
        
        if self.is_connected and self.client:
            self.client.subscribe("/4dx/heartbeat")
            logger.info("ハートビートトピックをサブスクライブ")
    
    def _on_connect(
        self,
        client: mqtt.Client,
        userdata,
        flags: Dict,
        rc: int
    ) -> None:
        """MQTT接続確立時のコールバック"""
        if rc == 0:
            self.is_connected = True
            logger.info("MQTT接続成功")
            
            # ハートビートトピックを自動サブスクライブ
            client.subscribe("/4dx/heartbeat")
            logger.info("ハートビートトピックをサブスクライブ")
        else:
            logger.error(f"MQTT接続失敗: rc={rc}")
    
    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata,
        rc: int
    ) -> None:
        """MQTT切断時のコールバック"""
        self.is_connected = False
        
        if rc == 0:
            logger.info("MQTT正常切断")
        else:
            logger.warning(f"MQTT異常切断: rc={rc}")
    
    def _on_message(
        self,
        client: mqtt.Client,
        userdata,
        msg: mqtt.MQTTMessage
    ) -> None:
        """MQTTメッセージ受信時のコールバック"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        logger.debug(f"MQTT受信: {topic} = {payload}")
        
        # ハートビート処理
        if topic == "/4dx/heartbeat" and self.on_heartbeat_callback:
            device_id = payload
            self.on_heartbeat_callback(device_id)
