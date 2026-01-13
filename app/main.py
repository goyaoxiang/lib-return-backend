import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routes import auth, return as return_route, loan, book, mqtt
from app.services.mqtt_service import mqtt_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(return_route.router)
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
