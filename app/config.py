from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 3000
    
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "library_return"
    db_user: str = "postgres"
    db_password: str = "postgres"
    
    jwt_secret_key: str = "your-secret-key-change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440
    
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_command_topic_format: str = "ReturnBox0{return_box_id}/Command"
    
    # Library settings
    daily_fine_rate: float = 0.50  # $0.50 per day overdue
    max_fine_amount: float = 10.00  # Maximum fine cap
    loan_period_days: int = 14  # Default loan period
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
