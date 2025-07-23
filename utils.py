"""
Utility functions for the Telegram Video Downloader Bot
"""

import re
import os
import string
from typing import List, Optional
from urllib.parse import urlparse

from config import Config

def is_video_url(text: str) -> bool:
    """
    Check if the text contains a valid video URL from supported platforms
    
    Args:
        text: Text to check for video URLs
        
    Returns:
        True if text contains a supported video URL
    """
    config = Config()
    
    # Basic URL pattern
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    
    urls = url_pattern.findall(text)
    
    for url in urls:
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Remove 'www.' prefix for comparison
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check if domain is in supported list
            for supported_domain in config.supported_domains:
                if supported_domain.startswith('www.'):
                    supported_domain = supported_domain[4:]
                
                if domain == supported_domain or domain.endswith('.' + supported_domain):
                    return True
                    
        except Exception:
            continue
    
    return False

def extract_urls(text: str) -> List[str]:
    """
    Extract all URLs from text
    
    Args:
        text: Text to extract URLs from
        
    Returns:
        List of URLs found in text
    """
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    
    return url_pattern.findall(text)

def clean_filename(filename: str, max_length: int = 100) -> str:
    """
    Clean filename by removing invalid characters and limiting length
    
    Args:
        filename: Original filename
        max_length: Maximum length for the filename
        
    Returns:
        Cleaned filename
    """
    if not filename:
        return "unknown"
    
    # Remove invalid characters
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    cleaned = ''.join(c for c in filename if c in valid_chars)
    
    # Replace multiple spaces with single space
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Limit length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rsplit(' ', 1)[0]  # Cut at word boundary
    
    # Ensure filename is not empty
    if not cleaned:
        cleaned = "video"
    
    return cleaned

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    size_float = float(size_bytes)
    
    while size_float >= 1024 and i < len(size_names) - 1:
        size_float = size_float / 1024.0
        i += 1
    
    return f"{size_float:.1f} {size_names[i]}"

def format_duration(seconds: Optional[int]) -> str:
    """
    Format duration in human readable format
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string (e.g., "3:45")
    """
    if seconds is None:
        return "Unknown"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def is_valid_file_extension(filename: str) -> bool:
    """
    Check if file has a valid video extension
    
    Args:
        filename: Filename to check
        
    Returns:
        True if filename has valid video extension
    """
    valid_extensions = [
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', 
        '.webm', '.m4v', '.3gp', '.ogv', '.ts', '.m2ts'
    ]
    
    file_ext = os.path.splitext(filename.lower())[1]
    return file_ext in valid_extensions

def sanitize_url(url: str) -> str:
    """
    Sanitize URL by removing tracking parameters and normalizing
    
    Args:
        url: URL to sanitize
        
    Returns:
        Sanitized URL
    """
    # Remove common tracking parameters
    tracking_params = [
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'ref', 'src'
    ]
    
    try:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Remove tracking parameters
        cleaned_params = {k: v for k, v in query_params.items() if k not in tracking_params}
        
        # Rebuild URL
        new_query = urlencode(cleaned_params, doseq=True)
        cleaned_url = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, new_query, parsed.fragment
        ))
        
        return cleaned_url
        
    except Exception:
        # If parsing fails, return original URL
        return url

def get_platform_name(url: str) -> str:
    """
    Get platform name from URL
    
    Args:
        url: Video URL
        
    Returns:
        Platform name (e.g., "YouTube", "TikTok")
    """
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        if 'youtube.com' in domain or 'youtu.be' in domain:
            return "YouTube"
        elif 'tiktok.com' in domain:
            return "TikTok"
        elif 'instagram.com' in domain:
            return "Instagram"
        elif 'twitter.com' in domain or 'x.com' in domain:
            return "Twitter/X"
        elif 'facebook.com' in domain:
            return "Facebook"
        elif 'vimeo.com' in domain:
            return "Vimeo"
        elif 'twitch.tv' in domain:
            return "Twitch"
        elif 'reddit.com' in domain:
            return "Reddit"
        else:
            return "Unknown Platform"
            
    except Exception:
        return "Unknown Platform"
