"""
Configuration module for the Telegram Video Downloader Bot
"""

import os
from typing import Optional

class Config:
    """Configuration class for bot settings"""
    
    def __init__(self):
        # Telegram Bot Token (required)
        self.telegram_token: str = os.getenv('7623419865:AAEd0P28WTFzQEQI-4HoJavHiGbwkLuV2Dk')
        if not self.telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        # File size limit (default 1GB - increased from 50MB)
        self.max_file_size: int = int(os.getenv("MAX_FILE_SIZE", str(1024 * 1024 * 1024)))
        
        # Rate limiting settings
        self.rate_limit_requests: int = int(os.getenv("RATE_LIMIT_REQUESTS", "5"))
        self.rate_limit_window: int = int(os.getenv("RATE_LIMIT_WINDOW", "300"))  # 5 minutes
        
        # Download timeout (seconds)
        self.download_timeout: int = int(os.getenv("DOWNLOAD_TIMEOUT", "300"))  # 5 minutes
        
        # Supported domains for validation
        self.supported_domains = [
            'youtube.com', 'youtu.be', 'www.youtube.com',
            'tiktok.com', 'www.tiktok.com', 'vm.tiktok.com',
            'instagram.com', 'www.instagram.com',
            'twitter.com', 'www.twitter.com', 'x.com', 'www.x.com',
            'facebook.com', 'www.facebook.com', 'fb.watch',
            'vimeo.com', 'www.vimeo.com',
            'dailymotion.com', 'www.dailymotion.com',
            'twitch.tv', 'www.twitch.tv',
            'reddit.com', 'www.reddit.com', 'v.redd.it',
            'streamable.com', 'www.streamable.com'
        ]
        
        # Log level
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        
        # Debug mode
        self.debug: bool = os.getenv("DEBUG", "False").lower() in ["true", "1", "yes"]

    def validate(self) -> bool:
        """Validate configuration"""
        if not self.telegram_token:
            return False
        
        if self.max_file_size <= 0:
            return False
            
        if self.rate_limit_requests <= 0 or self.rate_limit_window <= 0:
            return False
            
        return True

    def __str__(self) -> str:
        """String representation (excluding sensitive data)"""
        return f"Config(max_file_size={self.max_file_size}, rate_limit={self.rate_limit_requests}/{self.rate_limit_window}s)"
