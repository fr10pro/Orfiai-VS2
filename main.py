import os
import uuid
import aiofiles
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

# Import database and models
from database import SessionLocal, engine, init_db
from models import Base, Video

# Initialize database automatically on import
init_db()

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
        Path(directory).mkdir(parents=True, exist_ok=True)

# Create directories on startup
create_directories()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")

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

# Main routes
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request, db: Session = Depends(get_db)):
    """Homepage showing all videos in grid layout"""
    try:
        videos = db.query(Video).order_by(Video.created_at.desc()).all()
        return templates.TemplateResponse("index.html", {
            "request": request,
            "videos": videos
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/watch/{video_id}", response_class=HTMLResponse)
async def watch_video(request: Request, video_id: int, db: Session = Depends(get_db)):
    """Individual video page with Streamtape embed"""
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        return templates.TemplateResponse("watch.html", {
            "request": request,
            "video": video
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    """Admin panel for managing videos"""
    try:
        videos = db.query(Video).order_by(Video.created_at.desc()).all()
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "videos": videos
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Admin CRUD operations
@app.post("/admin/upload")
async def upload_video(
    title: str = Form(...),
    description: Optional[str] = Form(""),
    hashtags: Optional[str] = Form(""),
    streamtape_url: str = Form(...),
    banner: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload new video with banner image and metadata"""
    try:
        validate_form_input(title, streamtape_url)
        
        file_path = await save_uploaded_file(banner)
        streamtape_id = extract_streamtape_id(streamtape_url)
        
        video = Video(
            title=title.strip(),
            description=description.strip() if description else None,
            hashtags=hashtags.strip() if hashtags else None,
            streamtape_url=streamtape_url.strip(),
            streamtape_id=streamtape_id,
            banner_path=file_path
        )
        
        db.add(video)
        db.commit()
        db.refresh(video)
        
        return RedirectResponse(url="/admin", status_code=303)
        
    except HTTPException:
        if 'file_path' in locals():
            delete_file_safely(file_path)
        raise
    except Exception as e:
        if 'file_path' in locals():
            delete_file_safely(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to upload video: {str(e)}")

@app.post("/admin/delete/{video_id}")
async def delete_video(video_id: int, db: Session = Depends(get_db)):
    """Delete video and associated banner file"""
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        delete_file_safely(video.banner_path)
        db.delete(video)
        db.commit()
        
        return RedirectResponse(url="/admin", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete video: {str(e)}")

@app.get("/admin/edit/{video_id}", response_class=HTMLResponse)
async def edit_video_form(request: Request, video_id: int, db: Session = Depends(get_db)):
    """Show edit form for video"""
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        return templates.TemplateResponse("edit.html", {
            "request": request,
            "video": video
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/admin/edit/{video_id}")
async def update_video(
    video_id: int,
    title: str = Form(...),
    description: Optional[str] = Form(""),
    hashtags: Optional[str] = Form(""),
    streamtape_url: str = Form(...),
    banner: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Update video information and optionally replace banner"""
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        validate_form_input(title, streamtape_url)
        
        old_banner_path = video.banner_path
        
        video.title = title.strip()
        video.description = description.strip() if description else None
        video.hashtags = hashtags.strip() if hashtags else None
        video.streamtape_url = streamtape_url.strip()
        video.streamtape_id = extract_streamtape_id(streamtape_url)
        
        if banner and banner.filename:
            new_banner_path = await save_uploaded_file(banner)
            video.banner_path = new_banner_path
            
            if old_banner_path != new_banner_path:
                delete_file_safely(old_banner_path)
        
        db.commit()
        
        return RedirectResponse(url="/admin", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update video: {str(e)}")

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
                    "hashtags": video.hashtag_list,
                    "banner_url": f"/{video.banner_path}",
                    "watch_url": f"/watch/{video.id}",
                    "created_at": video.created_at.isoformat(),
                    "updated_at": video.updated_at.isoformat()
                }
                for video in videos
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/video/{video_id}")
async def get_video_api(video_id: int, db: Session = Depends(get_db)):
    """API endpoint to get single video details as JSON"""
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        return {
            "status": "success",
            "video": {
                "id": video.id,
                "title": video.title,
                "description": video.description,
                "hashtags": video.hashtag_list,
                "streamtape_url": video.streamtape_url,
                "streamtape_id": video.streamtape_id,
                "embed_url": video.embed_url,
                "banner_url": f"/{video.banner_path}",
                "watch_url": f"/watch/{video.id}",
                "created_at": video.created_at.isoformat(),
                "updated_at": video.updated_at.isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get platform statistics"""
    try:
        total_videos = db.query(Video).count()
        recent_videos = db.query(Video).order_by(Video.created_at.desc()).limit(5).all()
        
        # Count total hashtags
        all_hashtags = []
        for video in db.query(Video).all():
            all_hashtags.extend(video.hashtag_list)
        unique_hashtags = len(set(all_hashtags))
        
        return {
            "status": "success",
            "stats": {
                "total_videos": total_videos,
                "unique_hashtags": unique_hashtags,
                "recent_videos": [
                    {
                        "id": video.id,
                        "title": video.title,
                        "created_at": video.created_at.isoformat()
                    }
                    for video in recent_videos
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    database_type = "SQLite" if "sqlite://" in os.getenv("DATABASE_URL", "sqlite://") else "PostgreSQL"
    return {
        "status": "healthy",
        "service": "StreamHub Video Platform",
        "version": "1.0.0",
        "database": database_type,
        "environment": os.getenv("RENDER_SERVICE_NAME", "development")
    }

# Error handling
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors with custom page"""
    try:
        return templates.TemplateResponse("404.html", {
            "request": request
        }, status_code=404)
    except Exception:
        return HTMLResponse(
            content="<h1>404 - Page Not Found</h1><a href='/'>Go Home</a>",
            status_code=404
        )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc: HTTPException):
    """Handle 500 errors with custom page"""
    try:
        return templates.TemplateResponse("500.html", {
            "request": request
        }, status_code=500)
    except Exception:
        return HTMLResponse(
            content="<h1>500 - Internal Server Error</h1><a href='/'>Go Home</a>",
            status_code=500
        )

# Application events
@app.on_event("startup")
async def startup_event():
    """Execute on application startup"""
    print("\n🎬 StreamHub Video Streaming Platform")
    print("=" * 50)
    print("✅ Starting up server...")
    print("📁 Creating directories...")
    create_directories()
    print("🗄️  Database initialized and ready...")
    print("🚀 Server ready!")
    
    # Show environment info
    env = os.getenv("RENDER_SERVICE_NAME", "development")
    database_type = "SQLite" if "sqlite://" in os.getenv("DATABASE_URL", "sqlite://") else "PostgreSQL"
    
    print(f"🌍 Environment: {env}")
    print(f"🗄️  Database: {database_type}")
    
    if env != "development":
        print("🔗 Production URLs:")
        service_url = os.getenv("RENDER_EXTERNAL_URL", "https://your-app.onrender.com")
        print(f"   • Homepage: {service_url}")
        print(f"   • Admin Panel: {service_url}/admin")
        print(f"   • API Docs: {service_url}/docs")
        print(f"   • Health Check: {service_url}/health")
    else:
        print("🔗 Local URLs:")
        print("   • Homepage: http://localhost:8000")
        print("   • Admin Panel: http://localhost:8000/admin")
        print("   • API Docs: http://localhost:8000/docs")
        print("   • Health Check: http://localhost:8000/health")
    
    print("=" * 50)

@app.on_event("shutdown")
async def shutdown_event():
    """Execute on application shutdown"""
    print("\n👋 StreamHub shutting down...")
    print("🔧 Cleaning up resources...")
    print("✅ Shutdown complete")

# Development server
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print("🎬 Starting StreamHub in development mode...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=[".", "templates", "static"],
        log_level="info"
    )
