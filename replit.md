# Video Downloader Telegram Bot

## Overview

This is a Telegram bot that downloads videos from various platforms including YouTube, TikTok, Instagram, Twitter, Facebook, Vimeo, and others. The bot uses yt-dlp for video downloading and implements rate limiting to prevent abuse. It's designed to handle video downloads asynchronously and provides a clean interface for users to download videos by sending URLs.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The application follows a modular architecture with clear separation of concerns:

- **Bot Interface Layer**: Handles Telegram bot interactions and user commands
- **Download Engine**: Manages video downloading using yt-dlp
- **Rate Limiting**: Prevents abuse through sliding window rate limiting
- **Configuration Management**: Centralized configuration using environment variables
- **Utility Layer**: Common functions for URL validation and file handling

## Key Components

### Bot Module (`bot.py`)
- **Purpose**: Main bot interface handling Telegram interactions
- **Key Features**: Command handling (/start, /help, /favorites, /stats), message processing, error handling, video quality selection, animated progress indicators, favorites management
- **Dependencies**: telegram-python-bot library, async/await pattern, PostgreSQL database
- **Design Decision**: Uses the python-telegram-bot library for robust Telegram API integration
- **Recent Enhancement**: Added comprehensive favorites system with database storage, download statistics, and search functionality

### Video Downloader (`downloader.py`)
- **Purpose**: Core video downloading functionality
- **Technology**: yt-dlp (youtube-dl fork with active maintenance)
- **Features**: Supports multiple platforms, file size limits, temporary file management, quality selection (Best/HD/Standard/Low/Audio)
- **Design Decision**: Chose yt-dlp over youtube-dl for better platform support and active maintenance
- **Recent Enhancement**: Added quality-specific format selection with optimized settings for different resolutions

### Rate Limiter (`rate_limiter.py`)
- **Purpose**: Prevent abuse and manage bot usage
- **Algorithm**: Sliding window approach with per-user tracking
- **Storage**: In-memory using deques for efficient operations
- **Design Decision**: In-memory storage chosen for simplicity, suitable for single-instance deployment

### Configuration (`config.py`)
- **Purpose**: Centralized configuration management
- **Approach**: Environment variable-based configuration with sensible defaults
- **Validation**: Built-in configuration validation
- **Supported Platforms**: Whitelist of supported video domains
- **Recent Change**: Increased maximum file size limit from 50MB to 1GB (July 2025)

### Database Service (`database_service.py`)
- **Purpose**: Database operations for favorites and download history
- **Features**: Add/remove favorites, download statistics, search functionality, pagination
- **Technology**: SQLAlchemy with PostgreSQL backend
- **Design Decision**: Dedicated service layer for clean separation of database concerns

### Database Models (`models.py`)
- **Purpose**: Database schema definitions
- **Models**: FavoriteDownload, DownloadHistory
- **Features**: User favorites tracking, download statistics, error logging
- **Design**: SQLAlchemy ORM models with proper indexing and relationships

### Utilities (`utils.py`)
- **Purpose**: Common helper functions
- **Functions**: URL validation, filename sanitization, file size formatting, platform detection
- **Design**: Pure functions for easy testing and reuse

## Data Flow

1. **User Input**: User sends video URL to Telegram bot
2. **Validation**: Bot validates URL against supported domains
3. **Rate Limiting**: Check if user is within rate limits
4. **Download Process**: 
   - yt-dlp downloads video to temporary directory
   - File size is checked against Telegram limits
   - Video is sent back to user
5. **Cleanup**: Temporary files are cleaned up after sending

## External Dependencies

### Core Dependencies
- **python-telegram-bot**: Telegram Bot API wrapper
- **yt-dlp**: Video downloading engine
- **asyncio**: Asynchronous programming support

### Platform Support
- YouTube, TikTok, Instagram, Twitter/X
- Facebook, Vimeo, Dailymotion
- Twitch, Reddit, Streamable

### Infrastructure Requirements
- **Environment Variables**: TELEGRAM_BOT_TOKEN (required)
- **File System**: Temporary directory for video downloads
- **Network**: Outbound connections to video platforms

## Deployment Strategy

### Environment Configuration
- **Required**: TELEGRAM_BOT_TOKEN
- **Optional**: MAX_FILE_SIZE, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW, DOWNLOAD_TIMEOUT, LOG_LEVEL, DEBUG

### Resource Considerations
- **Memory**: In-memory rate limiting data
- **Storage**: Temporary file storage for downloads
- **Network**: Bandwidth for video downloads
- **CPU**: Video processing and encoding

### Logging and Monitoring
- **File Logging**: bot.log for persistent logs
- **Console Logging**: Real-time monitoring
- **Error Handling**: Comprehensive error catching and reporting

### Scalability Considerations
- **Single Instance**: Current design optimized for single bot instance
- **Rate Limiting**: Per-user limits prevent individual abuse
- **File Cleanup**: Automatic temporary file management prevents disk space issues

The architecture prioritizes simplicity and reliability over complex scalability, making it suitable for personal or small-scale use cases while maintaining clean, maintainable code structure.