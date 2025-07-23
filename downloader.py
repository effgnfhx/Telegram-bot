"""
Video Downloader Module
Handles video downloading using yt-dlp
"""

import os
import tempfile
import asyncio
import logging
from typing import Dict, Any
import yt_dlp

from config import Config
from utils import clean_filename

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self):
        self.config = Config()
        self.temp_dir = tempfile.mkdtemp(prefix="telegram_bot_")
        
        # Base yt-dlp options
        self.base_ydl_opts = {
            'outtmpl': os.path.join(self.temp_dir, '%(title)s.%(ext)s'),
            'restrictfilenames': True,
            'noplaylist': True,
            'ignoreerrors': True,
            'no_warnings': True,
            'quiet': True,
        }
        
        # Quality format options
        self.quality_formats = {
            'best': 'best[filesize<50M]/best',
            'hd': 'best[height<=720][filesize<50M]/best[height<=720]/best',
            'standard': 'best[height<=480][filesize<50M]/best[height<=480]/best',
            'low': 'best[height<=360][filesize<50M]/best[height<=360]/worst',
            'audio': 'bestaudio[filesize<50M]/bestaudio'
        }

    async def download_video(self, url: str, quality: str = 'best') -> Dict[str, Any]:
        """
        Download video from URL with specified quality
        
        Args:
            url: Video URL to download
            quality: Quality option ('best', 'hd', 'standard', 'low', 'audio')
            
        Returns:
            Dict containing success status, file path, error message, etc.
        """
        try:
            # Run yt-dlp in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._download_sync, url, quality)
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error downloading {url}: {e}")
            return {
                'success': False,
                'error': 'An unexpected error occurred during download'
            }

    def _download_sync(self, url: str, quality: str = 'best') -> Dict[str, Any]:
        """Synchronous download function"""
        try:
            # Build yt-dlp options with selected quality
            ydl_opts = self.base_ydl_opts.copy()
            ydl_opts['format'] = self.quality_formats.get(quality, self.quality_formats['best'])
            
            # Special handling for audio-only downloads
            if quality == 'audio':
                ydl_opts['extractaudio'] = True
                ydl_opts['audioformat'] = 'mp3'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return {
                        'success': False,
                        'error': 'Could not extract video information'
                    }
                
                # Check if video is available
                if info.get('is_live'):
                    return {
                        'success': False,
                        'error': 'Live streams are not supported'
                    }
                
                # Get video title and clean it
                title = info.get('title', 'Unknown')
                title = clean_filename(title)
                
                # Check estimated file size if available
                filesize = info.get('filesize') or info.get('filesize_approx')
                if filesize and filesize > self.config.max_file_size:
                    return {
                        'success': False,
                        'error': f'Video file too large (estimated {filesize // (1024*1024)}MB)'
                    }
                
                # Download the video
                ydl.download([url])
                
                # Find the downloaded file
                downloaded_files = []
                for file in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file)
                    if os.path.isfile(file_path):
                        downloaded_files.append(file_path)
                
                if not downloaded_files:
                    return {
                        'success': False,
                        'error': 'Download completed but no file found'
                    }
                
                # Get the most recent file (in case of multiple files)
                file_path = max(downloaded_files, key=os.path.getctime)
                file_size = os.path.getsize(file_path)
                
                # Final file size check
                if file_size > self.config.max_file_size:
                    os.remove(file_path)
                    return {
                        'success': False,
                        'error': f'Downloaded file too large ({file_size // (1024*1024)}MB)'
                    }
                
                return {
                    'success': True,
                    'file_path': file_path,
                    'file_size': file_size,
                    'title': title,
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader')
                }
                
        except yt_dlp.DownloadError as e:
            error_msg = str(e)
            if 'Private video' in error_msg:
                return {'success': False, 'error': 'This video is private'}
            elif 'Video unavailable' in error_msg:
                return {'success': False, 'error': 'Video is unavailable'}
            elif 'age-gated' in error_msg.lower():
                return {'success': False, 'error': 'Age-restricted content is not supported'}
            else:
                logger.error(f"yt-dlp download error for {url}: {e}")
                return {'success': False, 'error': 'Failed to download video'}
                
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return {
                'success': False,
                'error': 'Download failed due to an unexpected error'
            }

    def cleanup(self):
        """Clean up temporary directory"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            logger.error(f"Error cleaning up temp directory: {e}")

    def __del__(self):
        """Destructor to clean up resources"""
        self.cleanup()
