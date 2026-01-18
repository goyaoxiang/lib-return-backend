# Library Return Backend

FastAPI backend server for the smart library return system. Handles authentication, book loans, returns, and MQTT communication with ESP32 return boxes.

## Description

REST API backend that:

- Manages user authentication and authorization
- Tracks book loans and returns
- Communicates with ESP32 return boxes via MQTT
- Stores data in PostgreSQL database

## Environment Setup

1. Copy `.env.example` to `.env`

2. Update `.env` with your configuration:

```env
# Database
DB_NAME=library_return
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# JWT
JWT_SECRET_KEY=your_secret_key_here

# MQTT
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USERNAME=your_mqtt_username
MQTT_PASSWORD=your_mqtt_password
MQTT_USE_TLS=false
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 3000
```
