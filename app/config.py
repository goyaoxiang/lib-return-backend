from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path

# Get the backend directory (parent of app directory)
BACKEND_DIR = Path(__file__).parent.parent
ENV_FILE = BACKEND_DIR / ".env"

class Settings(BaseSettings):
    # Server settings (non-confidential, can have defaults)
    host: str = "0.0.0.0"
    port: int = 3000
    
    # HTTPS/SSL settings for uvicorn
    ssl_enabled: bool = False  # Enable HTTPS/SSL
    ssl_certfile: Optional[str] = None  # Path to SSL certificate file (e.g., /etc/letsencrypt/live/domain.com/fullchain.pem)
    ssl_keyfile: Optional[str] = None  # Path to SSL private key file (e.g., /etc/letsencrypt/live/domain.com/privkey.pem)
    
    # Database settings - confidential values from .env
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str  # Required from .env
    db_user: str  # Required from .env
    db_password: str  # Required from .env (confidential - no default)
    
    # JWT settings - confidential values from .env
    jwt_secret_key: str  # Required from .env (confidential - no default)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440
    
    # MQTT settings - confidential values from .env
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None  # Optional, from .env if provided
    mqtt_password: Optional[str] = None  # Optional, from .env if provided (confidential)
    mqtt_command_topic_format: str = "ReturnBox0{return_box_id}/Command"
    
    # MQTT TLS/SSL settings - for secured MQTT
    mqtt_use_tls: bool = False  # Enable TLS/SSL for MQTT
    mqtt_tls_insecure: bool = False  # Allow insecure TLS (for self-signed certs, not recommended for production)
    mqtt_ca_cert: Optional[str] = None  # Path to CA certificate file (required for TLS)
    mqtt_client_cert: Optional[str] = None  # Path to client certificate file (optional, for mutual TLS)
    mqtt_client_key: Optional[str] = None  # Path to client private key file (optional, for mutual TLS)
    
    # Database SSL settings
    db_ssl_mode: str = "prefer"  # Options: disable, allow, prefer, require, verify-ca, verify-full
    db_ssl_cert: Optional[str] = None  # Path to client certificate
    db_ssl_key: Optional[str] = None  # Path to client key
    db_ssl_root_cert: Optional[str] = None  # Path to root certificate
    
    class Config:
        env_file = str(ENV_FILE) if ENV_FILE.exists() else ".env"
        case_sensitive = False

settings = Settings()
