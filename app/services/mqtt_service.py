import json
import logging
import threading
import ssl
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app.models.book import BookCopy, ReturnBox
from app.models.return_transaction import ReturnTransaction, ReturnItem
from app.models.loan import Loan
from app.utils.timezone import now_gmt8

logger = logging.getLogger(__name__)


class MQTTService:
    """MQTT service for handling return box updates from ESP32."""
    
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.is_connected = False
        self._lock = threading.Lock()
        self._last_unlock_times: Dict[int, datetime] = {}
        self._unlock_cooldown_seconds = 5
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when MQTT client connects to broker."""
        if rc == 0:
            self.is_connected = True
            logger.info(f"MQTT client connected to {settings.mqtt_broker}:{settings.mqtt_port}")
            client.subscribe("+/Return", qos=1)  # Subscribe to ReturnBox01/Return, etc.
            client.subscribe("+/Inventory", qos=1)  # Subscribe to ReturnBox01/Inventory, etc.
            logger.info("Subscribed to +/Return and +/Inventory topics")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
            self.is_connected = False
    
    def on_disconnect(self, client, userdata, rc):
        """Callback when MQTT client disconnects from broker."""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"MQTT client disconnected unexpectedly (rc={rc})")
        else:
            logger.info("MQTT client disconnected")
    
    def on_message(self, client, userdata, msg):
        """Callback when a message is received on subscribed topic."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.info(f"Received message on topic {topic}: {payload}")
            
            if topic.startswith("ReturnBox") and topic.endswith("/Return"):
                self._handle_return_update(topic, payload)
            elif topic.startswith("ReturnBox") and topic.endswith("/Inventory"):
                self._handle_inventory_update(topic, payload)
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}", exc_info=True)
    
    def send_unlock_command(self, return_box_id: int):
        """Send unlock command to the specified return box.
        Prevents duplicate unlock commands within the cooldown period."""
        try:
            # Check if we recently sent an unlock command for this return box
            now = now_gmt8()
            last_unlock_time = self._last_unlock_times.get(return_box_id)
            
            if last_unlock_time:
                time_since_last = (now - last_unlock_time).total_seconds()
                if time_since_last < self._unlock_cooldown_seconds:
                    logger.warning(
                        f"Unlock command for return box {return_box_id} ignored: "
                        f"last unlock was {time_since_last:.1f} seconds ago "
                        f"(cooldown: {self._unlock_cooldown_seconds}s)"
                    )
                    return
            
            return_box_id_str = f"{return_box_id}"
            command_topic = settings.mqtt_command_topic_format.format(return_box_id=return_box_id_str)
            unlock_command = "UNLOCK"
            
            if self.client and self.is_connected:
                result = self.client.publish(command_topic, unlock_command, qos=1)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    self._last_unlock_times[return_box_id] = now
                    logger.info(f"Unlock command sent to {command_topic}")
                else:
                    logger.error(f"Failed to send unlock command to {command_topic}: rc={result.rc}")
            else:
                logger.error("MQTT client not connected, cannot send unlock command")
                
        except Exception as e:
            logger.error(f"Error sending unlock command: {e}", exc_info=True)
    
    def _handle_return_update(self, topic: str, payload: str):
        """Handle return update from ESP32 with EPC tags (books being returned)."""
        try:
            # Extract return box ID from topic (e.g., "ReturnBox01/Return" -> 1)
            topic_clean = topic.replace("/Return", "").replace("ReturnBox", "")
            try:
                return_box_id = int(topic_clean)
            except ValueError:
                logger.warning(f"Could not extract return_box_id from topic: {topic}")
                return
            
            data = json.loads(payload)
            epc_tags = []
            
            if isinstance(data, dict) and "Return" in data:
                epc_tags = data["Return"]
            elif isinstance(data, list):
                epc_tags = data
            else:
                logger.warning(f"Unexpected return payload format: {payload}")
                return
            
            if not epc_tags:
                logger.info(f"Empty return update received from return box {return_box_id}")
                return
            
            logger.info(f"Processing return update from return box {return_box_id}: {len(epc_tags)} EPC tags")
            
            db = SessionLocal()
            try:
                # Find book copies by EPC tags
                book_copies = db.query(BookCopy).filter(
                    BookCopy.book_epc.in_(epc_tags)
                ).all()
                
                if not book_copies:
                    logger.warning(f"No book copies found for EPC tags from return box {return_box_id}")
                    return
                
                # Verify return box exists
                return_box = db.query(ReturnBox).filter(ReturnBox.return_box_id == return_box_id).first()
                if not return_box:
                    logger.warning(f"Return box {return_box_id} not found in database")
                    return
                
                # Note: The actual return transaction creation should be handled by the API endpoint
                # This MQTT handler just logs the detection
                # The Flutter app should call the /api/library/return/scan endpoint with these EPC tags
                logger.info(f"Return box {return_box_id} detected {len(book_copies)} books: {[bc.book_epc for bc in book_copies]}")
                
            finally:
                db.close()
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in return update: {e}")
        except Exception as e:
            logger.error(f"Error handling return update: {e}", exc_info=True)
    
    def _handle_inventory_update(self, topic: str, payload: str):
        """Handle inventory update from ESP32. Called when door closes.
        Updates book copy status based on what's in the return box."""
        try:
            # Parse topic to extract return_box_id (e.g., "ReturnBox01/Inventory" -> 1)
            topic_clean = topic.replace("/Inventory", "").replace("ReturnBox", "")
            try:
                return_box_id = int(topic_clean)
            except ValueError:
                logger.warning(f"Could not extract return_box_id from topic: {topic}")
                return
            
            # Parse payload - ESP32 sends JSON array of EPC tags
            inventory_epc_tags = []
            try:
                data = json.loads(payload)
                if isinstance(data, list):
                    inventory_epc_tags = data
                elif isinstance(data, dict) and "Inventory" in data:
                    inventory_epc_tags = data["Inventory"]
                else:
                    logger.warning(f"Unexpected inventory payload format: {payload}")
                    return
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in inventory update: {e}")
                return
            
            logger.info(f"Processing inventory update from return box {return_box_id}: {len(inventory_epc_tags)} items")
            
            db = SessionLocal()
            try:
                # Get all book copies that should be in this return box's library
                return_box = db.query(ReturnBox).filter(ReturnBox.return_box_id == return_box_id).first()
                if not return_box:
                    logger.warning(f"Return box {return_box_id} not found")
                    return
                
                # Update book copy availability based on inventory
                # Books in inventory are "available" (in library), books not in inventory are "checked_out" or "returned"
                # This is a simplified logic - in reality, you'd need to track which books are supposed to be in the return box
                
                logger.info(f"Inventory update for return box {return_box_id}: {len(inventory_epc_tags)} books detected")
                
            except Exception as e:
                logger.error(f"Error handling inventory update: {e}", exc_info=True)
                db.rollback()
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error processing inventory update: {e}", exc_info=True)
    
    def _setup_tls(self):
        """Configure TLS/SSL for MQTT client."""
        if not settings.mqtt_use_tls:
            return
        
        try:
            # Create SSL context
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            
            # Load CA certificate if provided
            if settings.mqtt_ca_cert:
                ca_cert_path = Path(settings.mqtt_ca_cert)
                if not ca_cert_path.exists():
                    logger.error(f"CA certificate file not found: {ca_cert_path}")
                    raise FileNotFoundError(f"CA certificate file not found: {ca_cert_path}")
                context.load_verify_locations(cafile=str(ca_cert_path))
                logger.info(f"Loaded CA certificate from {ca_cert_path}")
            else:
                # Use system default CA certificates
                context.load_default_certs()
                logger.info("Using system default CA certificates")
            
            # Load client certificate and key if provided (mutual TLS)
            if settings.mqtt_client_cert and settings.mqtt_client_key:
                client_cert_path = Path(settings.mqtt_client_cert)
                client_key_path = Path(settings.mqtt_client_key)
                
                if not client_cert_path.exists():
                    logger.error(f"Client certificate file not found: {client_cert_path}")
                    raise FileNotFoundError(f"Client certificate file not found: {client_cert_path}")
                if not client_key_path.exists():
                    logger.error(f"Client key file not found: {client_key_path}")
                    raise FileNotFoundError(f"Client key file not found: {client_key_path}")
                
                context.load_cert_chain(
                    certfile=str(client_cert_path),
                    keyfile=str(client_key_path)
                )
                logger.info(f"Loaded client certificate from {client_cert_path} and key from {client_key_path}")
            
            # Configure TLS settings
            if settings.mqtt_tls_insecure:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                logger.warning("TLS insecure mode enabled - certificate verification disabled (not recommended for production)")
            else:
                context.check_hostname = True
                context.verify_mode = ssl.CERT_REQUIRED
            
            # Apply TLS context to MQTT client
            self.client.tls_set_context(context)
            logger.info("TLS/SSL configured for MQTT connection")
            
        except Exception as e:
            logger.error(f"Error setting up TLS for MQTT: {e}", exc_info=True)
            raise
    
    def connect(self):
        """Connect to MQTT broker with optional TLS/SSL support."""
        try:
            with self._lock:
                if self.client and self.is_connected:
                    logger.info("MQTT client already connected")
                    return
                
                # Create MQTT client
                client_id = f"library-return-backend-{threading.current_thread().ident}"
                self.client = mqtt.Client(client_id=client_id, clean_session=True)
                
                # Set callbacks
                self.client.on_connect = self.on_connect
                self.client.on_disconnect = self.on_disconnect
                self.client.on_message = self.on_message
                
                # Configure TLS/SSL if enabled
                if settings.mqtt_use_tls:
                    self._setup_tls()
                    # Use secure port (8883) if default port is still 1883
                    if settings.mqtt_port == 1883:
                        logger.warning("TLS enabled but port is 1883. Consider using port 8883 for MQTT over TLS.")
                
                # Set username and password if provided
                if settings.mqtt_username and settings.mqtt_password:
                    self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
                
                # Connect to broker (non-blocking, will connect in background)
                protocol = "TLS" if settings.mqtt_use_tls else "TCP"
                logger.info(f"Connecting to MQTT broker at {settings.mqtt_broker}:{settings.mqtt_port} over {protocol}")
                try:
                    self.client.connect(settings.mqtt_broker, settings.mqtt_port, keepalive=60)
                    # Start network loop in a separate thread (will attempt reconnection automatically)
                    self.client.loop_start()
                    logger.info("MQTT client connection initiated (will connect when broker is available)")
                except Exception as conn_error:
                    logger.warning(f"Initial MQTT connection failed: {conn_error}. The service will retry automatically.")
                    logger.warning("Make sure MQTT broker is running. The service will continue to retry in the background.")
                    # Still start the loop - it will handle reconnection attempts
                    self.client.loop_start()
                
        except Exception as e:
            logger.error(f"Error setting up MQTT client: {e}", exc_info=True)
            self.is_connected = False
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        try:
            with self._lock:
                if self.client:
                    self.client.loop_stop()
                    self.client.disconnect()
                    self.is_connected = False
                    logger.info("MQTT client disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting from MQTT broker: {e}", exc_info=True)
    
    def is_running(self) -> bool:
        """Check if MQTT service is running and connected."""
        return self.is_connected and self.client is not None


mqtt_service = MQTTService()
