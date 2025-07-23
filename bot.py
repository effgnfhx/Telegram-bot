"""
Telegram Video Downloader Bot
Handles Telegram bot interactions and coordinates video downloading
"""

import os
import logging
import asyncio
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ChatAction, ParseMode

from config import Config
from downloader import VideoDownloader
from rate_limiter import RateLimiter
from database_service import DatabaseService
from utils import is_video_url, format_file_size, clean_filename, get_platform_name

logger = logging.getLogger(__name__)

class VideoDownloaderBot:
    def __init__(self):
        self.config = Config()
        self.downloader = VideoDownloader()
        self.rate_limiter = RateLimiter()
        self.db_service = DatabaseService()
        
        # Initialize Telegram application
        self.application = Application.builder().token(self.config.telegram_token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("favorites", self.favorites_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(CallbackQueryHandler(self.callback_handler))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)

    def start(self):
        """Start the bot"""
        logger.info("Starting Telegram Video Downloader Bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not update.message:
            return
            
        welcome_message = (
            "🎥 *Video Downloader Bot*\n\n"
            "I can download videos from:\n"
            "• YouTube\n"
            "• TikTok\n"
            "• Instagram\n"
            "• And many other platforms!\n\n"
            "Just send me a video URL and I'll download it for you.\n\n"
            "Use /help for more information."
        )
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        if not update.message:
            return
            
        help_message = (
            "🆘 *Help - Video Downloader Bot*\n\n"
            "*Commands:*\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/favorites - View your favorite downloads\n"
            "/stats - View your download statistics\n\n"
            "*How to use:*\n"
            "1. Send me a video URL from supported platforms\n"
            "2. Choose your preferred quality (Best, HD, Standard, Low, Audio)\n"
            "3. Wait for the download to complete\n"
            "4. Receive your video file!\n"
            "5. Optionally save it to favorites for later access\n\n"
            "*Supported platforms:*\n"
            "• YouTube (youtube.com, youtu.be)\n"
            "• TikTok (tiktok.com)\n"
            "• Instagram (instagram.com)\n"
            "• Twitter/X (twitter.com, x.com)\n"
            "• Facebook (facebook.com)\n"
            "• And many more!\n\n"
            "*Limitations:*\n"
            "• Maximum file size: 1GB\n"
            "• Rate limited to prevent abuse\n"
            "• Private/age-restricted content may not work\n\n"
            "*Note:* Please respect platform terms of service and copyright laws."
        )
        await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)

    async def favorites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /favorites command - show user's favorite downloads"""
        if not update.message or not update.message.from_user:
            return
            
        user_id = update.message.from_user.id
        
        favorites = self.db_service.get_user_favorites(user_id, limit=10)
        favorites_count = self.db_service.get_favorites_count(user_id)
        
        if not favorites:
            await update.message.reply_text(
                "⭐ *Your Favorites*\n\n"
                "You don't have any favorite downloads yet!\n\n"
                "💡 When downloading videos, you can save them to favorites for quick access later.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        message = f"⭐ *Your Favorites* ({favorites_count} total)\n\n"
        
        keyboard = []
        for i, fav in enumerate(favorites[:5], 1):
            # Truncate long titles
            title = fav['title'][:50] + "..." if len(fav['title']) > 50 else fav['title']
            platform_emoji = {'youtube': '📺', 'tiktok': '🎵', 'instagram': '📸', 'twitter': '🐦', 'facebook': '📘'}.get(fav['platform'].lower(), '🎥')
            
            message += f"{i}. {platform_emoji} *{title}*\n"
            if fav['duration']:
                message += f"   ⏱️ Duration: {fav['duration']}\n"
            if fav['file_size']:
                message += f"   📏 Size: {format_file_size(fav['file_size'])}\n"
            message += f"   📅 Added: {fav['created_at'].strftime('%Y-%m-%d')}\n\n"
            
            # Add inline buttons for each favorite
            keyboard.append([
                InlineKeyboardButton(f"📥 Download #{i}", callback_data=f"dl_fav:{fav['id']}"),
                InlineKeyboardButton(f"🗑️ Remove #{i}", callback_data=f"rm_fav:{fav['id']}")
            ])
        
        # Add navigation buttons if there are more favorites
        nav_buttons = []
        if favorites_count > 5:
            nav_buttons.append(InlineKeyboardButton("➡️ Show More", callback_data="fav_pg:1"))
        nav_buttons.append(InlineKeyboardButton("🔍 Search Favorites", callback_data="search_fav"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command - show user's download statistics"""
        if not update.message or not update.message.from_user:
            return
            
        user_id = update.message.from_user.id
        stats = self.db_service.get_user_download_stats(user_id)
        
        message = (
            "📊 *Your Download Statistics*\n\n"
            f"📥 Total Downloads: {stats['total_downloads']}\n"
            f"✅ Successful: {stats['successful_downloads']}\n"
            f"⭐ Favorites: {stats['total_favorites']}\n"
            f"📈 Success Rate: {stats['success_rate']}%\n\n"
        )
        
        if stats['platform_breakdown']:
            message += "*Platform Breakdown:*\n"
            for platform, count in stats['platform_breakdown'].items():
                platform_emoji = {'youtube': '📺', 'tiktok': '🎵', 'instagram': '📸', 'twitter': '🐦', 'facebook': '📘'}.get(platform.lower(), '🎥')
                message += f"{platform_emoji} {platform.title()}: {count}\n"
        
        if stats['total_downloads'] == 0:
            message = (
                "📊 *Your Download Statistics*\n\n"
                "You haven't downloaded any videos yet!\n\n"
                "💡 Start by sending me a video URL to get your first download."
            )
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages with potential video URLs"""
        if not update.effective_user or not update.message or not update.message.text:
            return
            
        user_id = update.effective_user.id
        message_text = update.message.text.strip()
        
        # Check if message contains a video URL
        if not is_video_url(message_text):
            await update.message.reply_text(
                "❌ Please send a valid video URL from supported platforms.\n"
                "Use /help to see supported platforms."
            )
            return
        
        # Check rate limiting
        if not self.rate_limiter.is_allowed(user_id):
            await update.message.reply_text(
                "⏳ You're sending requests too quickly. Please wait before trying again."
            )
            return
        
        # Record the request
        self.rate_limiter.record_request(user_id)
        
        await self.show_quality_selection(update, message_text)

    async def show_quality_selection(self, update: Update, url: str):
        """Show quality selection interface with inline keyboard"""
        from utils import get_platform_name
        platform = get_platform_name(url)
        
        # Store URL in bot context with a simple ID
        user_id = update.message.from_user.id
        msg_id = update.message.message_id
        url_key = f"{user_id}_{msg_id}"
        
        # Store the URL temporarily (we'll clean it up after use)
        if not hasattr(self, '_temp_urls'):
            self._temp_urls = {}
        self._temp_urls[url_key] = url
        
        # Create inline keyboard with quality options (short callback data)
        keyboard = [
            [
                InlineKeyboardButton("🎬 Best Quality", callback_data=f"q:best:{url_key}"),
                InlineKeyboardButton("🎥 HD (720p)", callback_data=f"q:hd:{url_key}")
            ],
            [
                InlineKeyboardButton("📺 Standard (480p)", callback_data=f"q:std:{url_key}"),
                InlineKeyboardButton("📱 Low (360p)", callback_data=f"q:low:{url_key}")
            ],
            [
                InlineKeyboardButton("🎵 Audio Only", callback_data=f"q:audio:{url_key}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎥 {platform} video detected!\n\n"
            "📋 Choose your preferred quality:\n\n"
            "🎬 **Best** - Highest available quality\n"
            "🎥 **HD** - 720p video quality\n"
            "📺 **Standard** - 480p video quality\n"
            "📱 **Low** - 360p video quality\n"
            "🎵 **Audio Only** - MP3 audio file\n\n"
            "💡 *All downloads are optimized for the new 1GB limit*",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries (quality selection, favorites, etc.)"""
        query = update.callback_query
        if not query:
            return
            
        await query.answer()
        
        try:
            callback_data = query.data
            if not callback_data:
                await query.edit_message_text("❌ Invalid callback data.")
                return
            
            if callback_data.startswith("q:"):
                await self.handle_quality_selection(query, callback_data)
            elif callback_data.startswith("add_fav:"):
                await self.handle_add_favorite(query, callback_data)
            elif callback_data.startswith("dl_fav:"):
                await self.handle_download_favorite(query, callback_data)
            elif callback_data.startswith("rm_fav:"):
                await self.handle_remove_favorite(query, callback_data)
            elif callback_data.startswith("fav_pg:"):
                await self.handle_favorites_pagination(query, callback_data)
            elif callback_data == "search_fav":
                await self.handle_search_favorites(query)
            else:
                await query.edit_message_text("❌ Unknown action. Please try again.")
                
        except Exception as e:
            logger.error(f"Error in callback handler: {e}")
            try:
                await query.edit_message_text("❌ An error occurred. Please try again.")
            except:
                pass

    async def handle_quality_selection(self, query, callback_data: str):
        """Handle quality selection callback"""
        _, quality, url_key = callback_data.split(":", 2)
        
        # Retrieve URL from temporary storage
        if not hasattr(self, '_temp_urls') or url_key not in self._temp_urls:
            await query.edit_message_text("❌ Session expired. Please send the URL again.")
            return
            
        url = self._temp_urls[url_key]
        
        # Clean up temporary storage
        del self._temp_urls[url_key]
        
        # Edit message to show selection
        quality_names = {
            'best': 'Best Quality 🎬',
            'hd': 'HD (720p) 🎥',
            'std': 'Standard (480p) 📺',
            'low': 'Low (360p) 📱',
            'audio': 'Audio Only 🎵'
        }
        
        await query.edit_message_text(
            f"✅ Selected: {quality_names.get(quality, quality)}\n\n"
            "🔄 Starting download...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Start download with selected quality
        await self.download_and_send_video_with_quality(query, url, quality)

    async def handle_add_favorite(self, query, callback_data: str):
        """Handle adding video to favorites"""
        try:
            # Parse: "add_fav:fav_key"
            _, fav_key = callback_data.split(":", 1)
            
            # Retrieve favorite data from temporary storage
            if not hasattr(self, '_temp_favorites') or fav_key not in self._temp_favorites:
                await query.edit_message_text("❌ Session expired. Please try downloading again.")
                return
                
            fav_data = self._temp_favorites[fav_key]
            user_id = query.from_user.id
            username = query.from_user.username or query.from_user.first_name
            
            success = self.db_service.add_favorite(
                user_id=user_id,
                username=username,
                url=fav_data['url'],
                title=fav_data['title'],
                platform=fav_data['platform'],
                duration=fav_data['duration'],
                file_size=fav_data['file_size'],
                quality=fav_data['quality']
            )
            
            # Clean up temporary storage
            del self._temp_favorites[fav_key]
            
            if success:
                await query.edit_message_text(
                    f"⭐ *Added to Favorites!*\n\n"
                    f"📺 {fav_data['title']}\n\n"
                    "You can view all your favorites with /favorites",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await query.edit_message_text(
                    f"ℹ️ *Already in Favorites*\n\n"
                    f"📺 {fav_data['title']}\n\n"
                    "This video is already saved in your favorites.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Error adding favorite: {e}")
            await query.edit_message_text("❌ Error adding to favorites.")

    async def handle_download_favorite(self, query, callback_data: str):
        """Handle downloading a favorite video"""
        favorite_id = int(callback_data.split(":", 1)[1])
        user_id = query.from_user.id
        
        # Get favorite details
        favorites = self.db_service.get_user_favorites(user_id, limit=100)
        favorite = next((f for f in favorites if f['id'] == favorite_id), None)
        
        if not favorite:
            await query.edit_message_text("❌ Favorite not found.")
            return
        
        await query.edit_message_text(
            f"✅ Downloading from favorites...\n\n"
            f"📺 {favorite['title'][:50]}...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Start quality selection for favorite
        await self.show_quality_selection_for_favorite(query, favorite)

    async def handle_remove_favorite(self, query, callback_data: str):
        """Handle removing a favorite video"""
        favorite_id = int(callback_data.split(":", 1)[1])
        user_id = query.from_user.id
        
        success = self.db_service.remove_favorite(user_id, favorite_id)
        
        if success:
            await query.edit_message_text(
                "🗑️ *Removed from Favorites*\n\n"
                "The video has been removed from your favorites.\n\n"
                "Use /favorites to view your remaining favorites.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text("❌ Error removing favorite.")

    async def handle_favorites_pagination(self, query, callback_data: str):
        """Handle favorites pagination"""
        page = int(callback_data.split(":", 1)[1])
        user_id = query.from_user.id
        
        # Get favorites for the requested page
        offset = page * 5
        favorites = self.db_service.get_user_favorites(user_id, limit=5, offset=offset)
        favorites_count = self.db_service.get_favorites_count(user_id)
        
        if not favorites:
            await query.edit_message_text("No more favorites to show.")
            return
        
        message = f"⭐ *Your Favorites* ({favorites_count} total) - Page {page + 1}\n\n"
        
        keyboard = []
        for i, fav in enumerate(favorites, 1):
            title = fav['title'][:50] + "..." if len(fav['title']) > 50 else fav['title']
            platform_emoji = {'youtube': '📺', 'tiktok': '🎵', 'instagram': '📸', 'twitter': '🐦', 'facebook': '📘'}.get(fav['platform'].lower(), '🎥')
            
            message += f"{offset + i}. {platform_emoji} *{title}*\n"
            if fav['duration']:
                message += f"   ⏱️ Duration: {fav['duration']}\n"
            if fav['file_size']:
                message += f"   📏 Size: {format_file_size(fav['file_size'])}\n"
            message += f"   📅 Added: {fav['created_at'].strftime('%Y-%m-%d')}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"📥 Download #{offset + i}", callback_data=f"dl_fav:{fav['id']}"),
                InlineKeyboardButton(f"🗑️ Remove #{offset + i}", callback_data=f"rm_fav:{fav['id']}")
            ])
        
        # Navigation buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"fav_pg:{page - 1}"))
        if (page + 1) * 5 < favorites_count:
            nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"fav_pg:{page + 1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    async def handle_search_favorites(self, query):
        """Handle search favorites request"""
        await query.edit_message_text(
            "🔍 *Search Favorites*\n\n"
            "Send me a search term to find videos in your favorites.\n\n"
            "You can search by:\n"
            "• Video title\n"
            "• Platform name\n\n"
            "Just send your search term as a regular message.",
            parse_mode=ParseMode.MARKDOWN
        )

    async def show_quality_selection_for_favorite(self, query, favorite: dict):
        """Show quality selection for a favorite video"""
        url = favorite['url']
        title = favorite['title']
        
        # Create inline keyboard with quality options
        keyboard = [
            [
                InlineKeyboardButton("🎬 Best Quality", callback_data=f"quality:best:{url}"),
                InlineKeyboardButton("🎥 HD (720p)", callback_data=f"quality:hd:{url}")
            ],
            [
                InlineKeyboardButton("📺 Standard (480p)", callback_data=f"quality:standard:{url}"),
                InlineKeyboardButton("📱 Low (360p)", callback_data=f"quality:low:{url}")
            ],
            [
                InlineKeyboardButton("🎵 Audio Only", callback_data=f"quality:audio:{url}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎥 *{title[:50]}{'...' if len(title) > 50 else ''}*\n\n"
            "📋 Choose your preferred quality:\n\n"
            "🎬 **Best** - Highest available quality\n"
            "🎥 **HD** - 720p video quality\n"
            "📺 **Standard** - 480p video quality\n"
            "📱 **Low** - 360p video quality\n"
            "🎵 **Audio Only** - MP3 audio file",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def download_and_send_video_with_quality(self, query, url: str, quality: str):
        """Download video with specified quality"""
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        status_message = query.message
        
        try:
            # Start download progress animation and actual download concurrently
            progress_task = asyncio.create_task(self.show_download_progress(status_message, url))
            download_task = asyncio.create_task(self.downloader.download_video(url, quality))
            
            # Wait for download to complete
            download_result = await download_task
            
            # Cancel progress animation if it's still running
            if not progress_task.done():
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass
            
            if not download_result['success']:
                await status_message.edit_text(f"❌ Download failed: {download_result['error']}")
                return
            
            file_path = download_result['file_path']
            file_size = download_result['file_size']
            title = download_result['title']
            
            # Check file size (Telegram limit is 50MB for bots)
            if file_size > self.config.max_file_size:
                await status_message.edit_text(
                    f"❌ File too large ({format_file_size(file_size)})\n"
                    f"Maximum allowed size: {format_file_size(self.config.max_file_size)}\n\n"
                    "💡 Try selecting a lower quality option."
                )
                # Clean up file
                if os.path.exists(file_path):
                    os.remove(file_path)
                return
            
            # Send the video/audio
            await status_message.edit_text("📤 Uploading...")
            
            with open(file_path, 'rb') as media_file:
                quality_emoji = {'best': '🎬', 'hd': '🎥', 'standard': '📺', 'low': '📱', 'audio': '🎵'}
                caption = f"{quality_emoji.get(quality, '🎬')} {title}\n📏 Size: {format_file_size(file_size)}"
                
                if quality == 'audio':
                    await query.get_bot().send_audio(
                        chat_id=chat_id,
                        audio=media_file,
                        caption=caption,
                        read_timeout=300,
                        write_timeout=300
                    )
                else:
                    await query.get_bot().send_video(
                        chat_id=chat_id,
                        video=media_file,
                        caption=caption,
                        supports_streaming=True,
                        read_timeout=300,
                        write_timeout=300
                    )
            
            # Record download in history
            username = query.from_user.username or query.from_user.first_name or "Unknown"
            platform = get_platform_name(url)
            self.db_service.record_download(
                user_id=user_id,
                username=username,
                url=url,
                title=title,
                platform=platform,
                quality=quality,
                file_size=file_size,
                success=True
            )
            
            # Store favorite data temporarily and show "Add to Favorites" option
            fav_key = f"fav_{user_id}_{status_message.message_id}"
            if not hasattr(self, '_temp_favorites'):
                self._temp_favorites = {}
            self._temp_favorites[fav_key] = {
                'url': url,
                'title': title,
                'platform': platform,
                'duration': download_result.get('duration'),
                'file_size': file_size,
                'quality': quality
            }
            
            keyboard = [[
                InlineKeyboardButton("⭐ Add to Favorites", callback_data=f"add_fav:{fav_key}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.get_bot().send_message(
                chat_id=chat_id,
                text=f"✅ *Download Complete!*\n\n📺 {title}\n📏 Size: {format_file_size(file_size)}",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Delete status message and clean up file
            await status_message.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
                
            logger.info(f"Successfully sent {quality} quality video to user {user_id}: {title}")
            
        except Exception as e:
            logger.error(f"Error processing video for user {user_id}: {e}")
            
            # Record failed download
            try:
                username = query.from_user.username or query.from_user.first_name or "Unknown"
                platform = get_platform_name(url)
                self.db_service.record_download(
                    user_id=user_id,
                    username=username,
                    url=url,
                    title="Failed Download",
                    platform=platform,
                    quality=quality,
                    file_size=0,
                    success=False,
                    error_message=str(e)
                )
            except:
                pass
            
            try:
                await status_message.edit_text(
                    "❌ An error occurred while processing your video. Please try again later."
                )
            except:
                pass

    async def show_download_progress(self, status_message, url: str):
        """Show animated download progress with multiple animation styles"""
        from utils import get_platform_name
        platform = get_platform_name(url)
        
        # Multiple progress bar styles for variety
        progress_styles = [
            # Classic progress bar
            [
                "⬇️ Downloading video ⬜⬜⬜⬜⬜ 0%",
                "⬇️ Downloading video ⬛⬜⬜⬜⬜ 20%",
                "⬇️ Downloading video ⬛⬛⬜⬜⬜ 40%", 
                "⬇️ Downloading video ⬛⬛⬛⬜⬜ 60%",
                "⬇️ Downloading video ⬛⬛⬛⬛⬜ 80%",
                "⬇️ Downloading video ⬛⬛⬛⬛⬛ 100%"
            ],
            # Spinning loader
            [
                "⬇️ Downloading video ⠋",
                "⬇️ Downloading video ⠙", 
                "⬇️ Downloading video ⠹",
                "⬇️ Downloading video ⠸",
                "⬇️ Downloading video ⠼",
                "⬇️ Downloading video ⠴",
                "⬇️ Downloading video ⠦",
                "⬇️ Downloading video ⠧"
            ],
            # Dots animation
            [
                "⬇️ Downloading video .",
                "⬇️ Downloading video ..",
                "⬇️ Downloading video ...",
                "⬇️ Downloading video ....",
                "⬇️ Downloading video .....",
                "⬇️ Downloading video ......",
            ]
        ]
        
        import random
        chosen_style = random.choice(progress_styles)
        
        try:
            frame_index = 0
            while True:
                current_frame = chosen_style[frame_index % len(chosen_style)]
                await status_message.edit_text(f"🎥 {platform} video detected!\n{current_frame}")
                await asyncio.sleep(0.6)  # Smooth animation timing
                frame_index += 1
                
        except asyncio.CancelledError:
            # Animation was cancelled, show completion message
            await status_message.edit_text("✅ Download complete! Processing video...")
        except Exception as e:
            # If animation fails, just show a simple downloading message
            await status_message.edit_text("⬇️ Downloading video...")

    async def download_and_send_video(self, update: Update, url: str):
        """Download video and send to user"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        status_message = None
        
        # Send "uploading video" action
        await update.get_bot().send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VIDEO)
        
        try:
            # Send initial message
            status_message = await update.message.reply_text("🔄 Processing your video request...")
            
            # Start download progress animation and actual download concurrently
            progress_task = asyncio.create_task(self.show_download_progress(status_message, url))
            download_task = asyncio.create_task(self.downloader.download_video(url))
            
            # Wait for download to complete
            download_result = await download_task
            
            # Cancel progress animation if it's still running
            if not progress_task.done():
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass
            
            if not download_result['success']:
                await status_message.edit_text(f"❌ Download failed: {download_result['error']}")
                return
            
            file_path = download_result['file_path']
            file_size = download_result['file_size']
            title = download_result['title']
            
            # Check file size (Telegram limit is 50MB for bots)
            if file_size > self.config.max_file_size:
                await status_message.edit_text(
                    f"❌ File too large ({format_file_size(file_size)})\n"
                    f"Maximum allowed size: {format_file_size(self.config.max_file_size)}"
                )
                # Clean up file
                if os.path.exists(file_path):
                    os.remove(file_path)
                return
            
            # Send the video
            await status_message.edit_text("📤 Uploading video...")
            
            with open(file_path, 'rb') as video_file:
                await update.get_bot().send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption=f"🎥 {title}\n📏 Size: {format_file_size(file_size)}",
                    supports_streaming=True,
                    read_timeout=300,
                    write_timeout=300
                )
            
            # Delete status message and clean up file
            await status_message.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
                
            logger.info(f"Successfully sent video to user {user_id}: {title}")
            
        except Exception as e:
            logger.error(f"Error processing video for user {user_id}: {e}")
            try:
                if status_message:
                    await status_message.edit_text(
                        "❌ An error occurred while processing your video. Please try again later."
                    )
                else:
                    await update.message.reply_text(
                        "❌ An error occurred while processing your video. Please try again later."
                    )
            except:
                await update.message.reply_text(
                    "❌ An error occurred while processing your video. Please try again later."
                )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ An unexpected error occurred. Please try again later."
                )
            except Exception as e:
                logger.error(f"Failed to send error message: {e}")
