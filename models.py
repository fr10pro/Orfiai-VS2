from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    hashtags = Column(String(500), nullable=True)
    streamtape_url = Column(String(500), nullable=False)
    streamtape_id = Column(String(100), nullable=False, index=True)
    banner_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add database indexes for better performance
    __table_args__ = (
        Index('ix_videos_created_title', 'created_at', 'title'),
        Index('ix_videos_streamtape_id', 'streamtape_id'),
    )
    
    @property
    def hashtag_list(self):
        """Return hashtags as a list"""
        if not self.hashtags:
            return []
        return [tag.strip() for tag in self.hashtags.split(',') if tag.strip()]
    
    @property
    def embed_url(self):
        """Generate embed URL for Streamtape"""
        return f"https://streamtape.com/e/{self.streamtape_id}/"
    
    @property
    def formatted_created_at(self):
        """Return formatted creation date"""
        return self.created_at.strftime('%B %d, %Y')
    
    @property
    def formatted_updated_at(self):
        """Return formatted update date"""
        return self.updated_at.strftime('%B %d, %Y at %I:%M %p')
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'hashtags': self.hashtag_list,
            'streamtape_url': self.streamtape_url,
            'streamtape_id': self.streamtape_id,
            'embed_url': self.embed_url,
            'banner_path': self.banner_path,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f"<Video(id={self.id}, title='{self.title}', created='{self.formatted_created_at}')>"
