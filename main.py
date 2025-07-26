import os
import uuid
import aiofiles
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

# Import database and models with error handling
try:
    from database import SessionLocal, engine, init_db
    from models import Base, Video
    
    # Initialize database automatically
    init_db()
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"❌ Database initialization error: {e}")
    # Create fallback database setup
    from sqlalchemy import create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine("sqlite:///./streamhub.db", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

# Initialize FastAPI app
app = FastAPI(
    title="StreamHub - Video Streaming Platform",
    description="A complete video streaming platform with admin management and Streamtape integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Create directories function
def create_directories():
    """Create necessary directories if they don't exist"""
    directories = ["static", "static/banners", "templates"]
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            print(f"✅ Created directory: {directory}")
        except Exception as e:
            print(f"⚠️  Could not create directory {directory}: {e}")

# Create directories on startup
create_directories()

# Mount static files with error handling
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    print("✅ Static files mounted")
except Exception as e:
    print(f"⚠️  Static files mount error: {e}")

# Initialize Jinja2 templates with error handling
try:
    templates = Jinja2Templates(directory="templates")
    print("✅ Templates initialized")
except Exception as e:
    print(f"⚠️  Templates initialization error: {e}")
    templates = None

# Database dependency
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utility functions
def extract_streamtape_id(url: str) -> str:
    """Extract video ID from Streamtape URL"""
    try:
        if '/e/' in url:
            return url.split('/e/')[-1].split('/')[0]
        else:
            return url.split('/')[-1].replace('/', '')
    except Exception:
        return "invalid_id"

async def save_uploaded_file(file: UploadFile) -> str:
    """Save uploaded file using aiofiles and return path"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Generate unique filename
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = f"static/banners/{filename}"
    
    # Save file using aiofiles
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        return file_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

def delete_file_safely(file_path: str):
    """Safely delete file if it exists"""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass

def validate_form_input(title: str, streamtape_url: str):
    """Validate form inputs"""
    if not title or len(title.strip()) == 0:
        raise HTTPException(status_code=400, detail="Title is required")
    
    if len(title.strip()) > 255:
        raise HTTPException(status_code=400, detail="Title too long (max 255 characters)")
    
    if not streamtape_url or 'streamtape.com' not in streamtape_url:
        raise HTTPException(status_code=400, detail="Invalid Streamtape URL - must contain 'streamtape.com'")

# Basic test route
@app.get("/test")
async def test_route():
    """Test route to verify app is working"""
    return {"status": "working", "message": "StreamHub is operational"}

# Main routes with fallback handling
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request, db: Session = Depends(get_db)):
    """Homepage showing all videos in grid layout"""
    try:
        if templates is None:
            return HTMLResponse("""
            <html><head><title>StreamHub</title></head>
            <body>
                <h1>🎬 StreamHub Video Platform</h1>
                <p>✅ Server is running successfully!</p>
                <p><a href="/admin">Go to Admin Panel</a></p>
                <p><a href="/health">Health Check</a></p>
                <p><a href="/docs">API Documentation</a></p>
            </body></html>
            """)
        
        # Try to get videos from database
        try:
            videos = db.query(Video).order_by(Video.created_at.desc()).all()
        except Exception as e:
            print(f"Database query error: {e}")
            videos = []
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "videos": videos
        })
    except Exception as e:
        print(f"Homepage error: {e}")
        return HTMLResponse(f"""
        <html><head><title>StreamHub</title></head>
        <body>
            <h1>🎬 StreamHub Video Platform</h1>
            <p>✅ Server is running!</p>
            <p>⚠️  Template loading issue: {str(e)}</p>
            <p><a href="/health">Health Check</a></p>
            <p><a href="/docs">API Documentation</a></p>
        </body></html>
        """)

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    """Admin panel for managing videos"""
    try:
        if templates is None:
            return HTMLResponse("""
            <html><head><title>StreamHub Admin</title></head>
            <body>
                <h1>🔧 StreamHub Admin Panel</h1>
                <p>⚠️  Templates not loaded. Please check template files.</p>
                <p><a href="/">Back to Homepage</a></p>
            </body></html>
            """)
        
        try:
            videos = db.query(Video).order_by(Video.created_at.desc()).all()
        except Exception as e:
            print(f"Database query error: {e}")
            videos = []
        
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "videos": videos
        })
    except Exception as e:
        print(f"Admin panel error: {e}")
        return HTMLResponse(f"""
        <html><head><title>StreamHub Admin</title></head>
        <body>
            <h1>🔧 StreamHub Admin Panel</h1>
            <p>⚠️  Error loading admin panel: {str(e)}</p>
            <p><a href="/">Back to Homepage</a></p>
        </body></html>
        """)

@app.get("/watch/{video_id}", response_class=HTMLResponse)
async def watch_video(request: Request, video_id: int, db: Session = Depends(get_db)):
    """Individual video page with Streamtape embed"""
    try:
        if templates is None:
            return HTMLResponse(f"""
            <html><head><title>Video {video_id}</title></head>
            <body>
                <h1>🎬 Video Player</h1>
                <p>⚠️  Templates not loaded. Video ID: {video_id}</p>
                <p><a href="/">Back to Homepage</a></p>
            </body></html>
            """)
        
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
        except Exception as e:
            print(f"Database query error: {e}")
            video = None
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        return templates.TemplateResponse("watch.html", {
            "request": request,
            "video": video
        })
    except HTTPException:
        raise
    except Exception as e:
        print(f"Watch video error: {e}")
        return HTMLResponse(f"""
        <html><head><title>Video Error</title></head>
        <body>
            <h1>⚠️  Video Loading Error</h1>
            <p>Error: {str(e)}</p>
            <p><a href="/">Back to Homepage</a></p>
        </body></html>
        """)

# API endpoints
@app.get("/api/videos")
async def get_videos_api(db: Session = Depends(get_db)):
    """API endpoint to get all videos as JSON"""
    try:
        videos = db.query(Video).order_by(Video.created_at.desc()).all()
        return {
            "status": "success",
            "count": len(videos),
            "videos": [
                {
                    "id": video.id,
                    "title": video.title,
                    "description": video.description,
                    "created_at": video.created_at.isoformat(),
                }
                for video in videos
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "videos": []}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        database_type = "SQLite" if "sqlite://" in os.getenv("DATABASE_URL", "sqlite://") else "PostgreSQL"
        return {
            "status": "healthy",
            "service": "StreamHub Video Platform",
            "version": "1.0.0",
            "database": database_type,
            "environment": os.getenv("RENDER_SERVICE_NAME", "development"),
            "templates": "loaded" if templates else "missing",
            "directories": {
                "static": os.path.exists("static"),
                "templates": os.path.exists("templates"),
                "banners": os.path.exists("static/banners")
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Error handling
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    return HTMLResponse("""
    <html><head><title>404 - Not Found</title></head>
    <body>
        <h1>404 - Page Not Found</h1>
        <p>The requested page could not be found.</p>
        <p><a href="/">Go to Homepage</a></p>
    </body></html>
    """, status_code=404)

@app.exception_handler(500)
async def server_error_handler(request: Request, exc: HTTPException):
    """Handle 500 errors"""
    return HTMLResponse("""
    <html><head><title>500 - Server Error</title></head>
    <body>
        <h1>500 - Internal Server Error</h1>
        <p>Something went wrong on our server.</p>
        <p><a href="/">Go to Homepage</a></p>
    </body></html>
    """, status_code=500)

# Application events
@app.on_event("startup")
async def startup_event():
    """Execute on application startup"""
    print("\n🎬 StreamHub Video Streaming Platform")
    print("=" * 50)
    print("✅ Starting up server...")
    print("📁 Creating directories...")
    create_directories()
    
    # Check critical files
    critical_files = ["templates", "static", "database.py", "models.py"]
    for file_path in critical_files:
        if os.path.exists(file_path):
            print(f"✅ Found: {file_path}")
        else:
            print(f"⚠️  Missing: {file_path}")
    
    print("🚀 Server ready!")
    
    # Show environment info
    env = os.getenv("RENDER_SERVICE_NAME", "development")
    database_type = "SQLite" if "sqlite://" in os.getenv("DATABASE_URL", "sqlite://") else "PostgreSQL"
    
    print(f"🌍 Environment: {env}")
    print(f"🗄️  Database: {database_type}")
    print("=" * 50)

# Development server
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print("🎬 Starting StreamHub...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )
