import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database URL configuration - SQLite with auto-creation
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./streamhub.db")

# Handle PostgreSQL URL format if provided
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine with appropriate settings
if "postgresql://" in DATABASE_URL:
    # PostgreSQL configuration (if DATABASE_URL is provided)
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )
    print("🐘 Using PostgreSQL database")
else:
    # SQLite configuration - auto-creates database file
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
    print("📁 Using SQLite database (auto-created)")

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

def init_db():
    """Initialize database tables - called automatically on startup"""
    try:
        # Import models to register them with Base
        from models import Video
        
        # Create all tables automatically
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
        
        # Test database connection
        db = SessionLocal()
        try:
            # Simple query to verify connection
            db.execute("SELECT 1")
            print("✅ Database connection verified")
        except Exception as e:
            print(f"⚠️  Database connection test failed: {e}")
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        # Don't raise error - let app continue with potential fallback

def get_db_info():
    """Get database connection information for debugging"""
    db_type = "PostgreSQL" if "postgresql://" in DATABASE_URL else "SQLite"
    return {
        "type": db_type,
        "url": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "local file",
        "status": "connected"
    }
