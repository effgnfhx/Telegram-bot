"""
Database service for managing favorites and download history
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from models import FavoriteDownload, DownloadHistory, get_session, create_tables

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service class for database operations"""
    
    def __init__(self):
        """Initialize database service and create tables if needed"""
        try:
            create_tables()
            logger.info("Database service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def add_favorite(self, user_id: int, username: str, url: str, title: str, 
                    platform: str, thumbnail_url: Optional[str] = None, 
                    duration: Optional[str] = None, file_size: Optional[int] = None,
                    quality: Optional[str] = None) -> bool:
        """Add a video to user's favorites"""
        session = get_session()
        try:
            # Check if already exists
            existing = session.query(FavoriteDownload).filter_by(
                user_id=user_id, url=url, is_active=True
            ).first()
            
            if existing:
                logger.info(f"Video already in favorites for user {user_id}: {title}")
                return False
            
            favorite = FavoriteDownload(
                user_id=user_id,
                username=username,
                url=url,
                title=title,
                platform=platform,
                thumbnail_url=thumbnail_url,
                duration=duration,
                file_size=file_size,
                quality=quality
            )
            
            session.add(favorite)
            session.commit()
            logger.info(f"Added favorite for user {user_id}: {title}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error adding favorite: {e}")
            return False
        finally:
            session.close()
    
    def remove_favorite(self, user_id: int, favorite_id: int) -> bool:
        """Remove a video from user's favorites"""
        session = get_session()
        try:
            favorite = session.query(FavoriteDownload).filter_by(
                id=favorite_id, user_id=user_id, is_active=True
            ).first()
            
            if not favorite:
                return False
            
            favorite.is_active = False
            session.commit()
            logger.info(f"Removed favorite {favorite_id} for user {user_id}")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error removing favorite: {e}")
            return False
        finally:
            session.close()
    
    def get_user_favorites(self, user_id: int, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get user's favorite downloads"""
        session = get_session()
        try:
            favorites = session.query(FavoriteDownload).filter_by(
                user_id=user_id, is_active=True
            ).order_by(FavoriteDownload.created_at.desc()).offset(offset).limit(limit).all()
            
            result = []
            for fav in favorites:
                result.append({
                    'id': fav.id,
                    'title': fav.title,
                    'url': fav.url,
                    'platform': fav.platform,
                    'duration': fav.duration,
                    'file_size': fav.file_size,
                    'quality': fav.quality,
                    'created_at': fav.created_at,
                    'thumbnail_url': fav.thumbnail_url
                })
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting favorites: {e}")
            return []
        finally:
            session.close()
    
    def get_favorites_count(self, user_id: int) -> int:
        """Get total count of user's favorites"""
        session = get_session()
        try:
            count = session.query(FavoriteDownload).filter_by(
                user_id=user_id, is_active=True
            ).count()
            return count
        except SQLAlchemyError as e:
            logger.error(f"Database error getting favorites count: {e}")
            return 0
        finally:
            session.close()
    
    def record_download(self, user_id: int, username: str, url: str, title: str,
                       platform: str, quality: str, file_size: int, 
                       success: bool = True, error_message: Optional[str] = None) -> bool:
        """Record a download in history"""
        session = get_session()
        try:
            download = DownloadHistory(
                user_id=user_id,
                username=username,
                url=url,
                title=title,
                platform=platform,
                quality=quality,
                file_size=file_size,
                success=success,
                error_message=error_message
            )
            
            session.add(download)
            session.commit()
            logger.info(f"Recorded download for user {user_id}: {title} ({'success' if success else 'failed'})")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error recording download: {e}")
            return False
        finally:
            session.close()
    
    def get_user_download_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user's download statistics"""
        session = get_session()
        try:
            total_downloads = session.query(DownloadHistory).filter_by(user_id=user_id).count()
            successful_downloads = session.query(DownloadHistory).filter_by(
                user_id=user_id, success=True
            ).count()
            total_favorites = session.query(FavoriteDownload).filter_by(
                user_id=user_id, is_active=True
            ).count()
            
            # Get platform breakdown
            platform_stats = session.query(
                DownloadHistory.platform, 
                session.query().func.count(DownloadHistory.id)
            ).filter_by(user_id=user_id, success=True).group_by(DownloadHistory.platform).all()
            
            platform_breakdown = {platform: count for platform, count in platform_stats}
            
            return {
                'total_downloads': total_downloads,
                'successful_downloads': successful_downloads,
                'total_favorites': total_favorites,
                'success_rate': round(successful_downloads / total_downloads * 100, 1) if total_downloads > 0 else 0,
                'platform_breakdown': platform_breakdown
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting user stats: {e}")
            return {
                'total_downloads': 0,
                'successful_downloads': 0,
                'total_favorites': 0,
                'success_rate': 0,
                'platform_breakdown': {}
            }
        finally:
            session.close()
    
    def search_favorites(self, user_id: int, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search user's favorites by title or platform"""
        session = get_session()
        try:
            search_pattern = f"%{query.lower()}%"
            favorites = session.query(FavoriteDownload).filter(
                FavoriteDownload.user_id == user_id,
                FavoriteDownload.is_active == True,
                session.query().func.lower(FavoriteDownload.title).like(search_pattern) |
                session.query().func.lower(FavoriteDownload.platform).like(search_pattern)
            ).order_by(FavoriteDownload.created_at.desc()).limit(limit).all()
            
            result = []
            for fav in favorites:
                result.append({
                    'id': fav.id,
                    'title': fav.title,
                    'url': fav.url,
                    'platform': fav.platform,
                    'duration': fav.duration,
                    'file_size': fav.file_size,
                    'quality': fav.quality,
                    'created_at': fav.created_at
                })
            
            return result
            
        except SQLAlchemyError as e:
            logger.error(f"Database error searching favorites: {e}")
            return []
        finally:
            session.close()