"""
Database models for the Telegram Video Downloader Bot
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class FavoriteDownload(Base):
    """Model for storing user's favorite downloads"""
    __tablename__ = 'favorite_downloads'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    platform = Column(String(50), nullable=False)
    thumbnail_url = Column(Text, nullable=True)
    duration = Column(String(20), nullable=True)
    file_size = Column(Integer, nullable=True)
    quality = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<FavoriteDownload(user_id={self.user_id}, title='{self.title[:50]}...')>"

class DownloadHistory(Base):
    """Model for tracking download history and statistics"""
    __tablename__ = 'download_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    platform = Column(String(50), nullable=False)
    quality = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=False)
    download_time = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<DownloadHistory(user_id={self.user_id}, title='{self.title[:50]}...', success={self.success})>"

# Database setup
def get_database_engine():
    """Create and return database engine"""
    database_url = os.getenv('postgresql://neondb_owner:npg_gJP0Hbe7owui@ep-proud-sunset-afvf5ulw.c-2.us-west-2.aws.neon.tech/neondb?sslmode=require')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    # Handle postgres:// vs postgresql:// for SQLAlchemy
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=300)
    return engine

def create_tables():
    """Create all database tables"""
    engine = get_database_engine()
    Base.metadata.create_all(engine)
    return engine

def get_session():
    """Get database session"""
    engine = get_database_engine()
    Session = sessionmaker(bind=engine)
    return Session()