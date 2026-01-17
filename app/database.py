from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus
from app.config import settings

# Build database URL with SSL support
db_user = quote_plus(settings.db_user)
db_password = quote_plus(settings.db_password)
db_host = settings.db_host
db_port = settings.db_port
db_name = settings.db_name

DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# SSL connection arguments
connect_args = {}
if settings.db_ssl_mode != "disable":
    connect_args["sslmode"] = settings.db_ssl_mode
    if settings.db_ssl_cert:
        connect_args["sslcert"] = settings.db_ssl_cert
    if settings.db_ssl_key:
        connect_args["sslkey"] = settings.db_ssl_key
    if settings.db_ssl_root_cert:
        connect_args["sslrootcert"] = settings.db_ssl_root_cert

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
    echo=False,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
