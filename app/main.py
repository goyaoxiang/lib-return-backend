import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request

from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings
from app.database import engine, Base
from app.routes import auth, returns, loan, book, mqtt
from app.services.mqtt_service import mqtt_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log incoming requests for debugging."""
    async def dispatch(self, request: Request, call_next):
        # Log request details for debugging auth issues
        auth_header = request.headers.get("Authorization")
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"{request.method} {request.url.path} - IP: {client_ip} - Auth: {'Present' if auth_header else 'Missing'}")
        if auth_header:
            # Log first 20 chars of token for debugging (don't log full token for security)
            logger.debug(f"Token preview: {auth_header[:20]}...")
        
        response = await call_next(request)
        return response

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to start/stop MQTT service with FastAPI."""
    logger.info("Starting MQTT service...")
    mqtt_service.connect()
    
    yield
    
    logger.info("Stopping MQTT service...")
    mqtt_service.disconnect()


app = FastAPI(
    title="Library Book Return API",
    description="Backend API for Smart Library Book Return System",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Logging middleware (last, to log everything)
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(auth.router)
app.include_router(returns.router)
app.include_router(loan.router)
app.include_router(book.router)
app.include_router(mqtt.router)

@app.get("/")
async def root():
    return {"message": "Library Book Return API", "version": "1.0.0"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
