"""
Rate Limiter Module
Implements rate limiting to prevent abuse
"""

import time
import logging
from typing import Dict, List
from collections import defaultdict, deque

from config import Config

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter using sliding window approach"""
    
    def __init__(self):
        self.config = Config()
        # Dictionary to store request timestamps for each user
        self.user_requests: Dict[int, deque] = defaultdict(deque)
        
        # Cleanup interval (seconds)
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes

    def is_allowed(self, user_id: int) -> bool:
        """
        Check if user is allowed to make a request
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if request is allowed, False if rate limited
        """
        current_time = time.time()
        
        # Cleanup old entries periodically
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries()
            self.last_cleanup = current_time
        
        user_queue = self.user_requests[user_id]
        
        # Remove old requests outside the time window
        window_start = current_time - self.config.rate_limit_window
        while user_queue and user_queue[0] < window_start:
            user_queue.popleft()
        
        # Check if user has exceeded the limit
        if len(user_queue) >= self.config.rate_limit_requests:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False
        
        return True

    def record_request(self, user_id: int) -> None:
        """
        Record a request for the user
        
        Args:
            user_id: Telegram user ID
        """
        current_time = time.time()
        self.user_requests[user_id].append(current_time)
        
        logger.debug(f"Recorded request for user {user_id} at {current_time}")

    def get_user_request_count(self, user_id: int) -> int:
        """
        Get current request count for user within the time window
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Number of requests in the current window
        """
        current_time = time.time()
        user_queue = self.user_requests[user_id]
        
        # Remove old requests
        window_start = current_time - self.config.rate_limit_window
        while user_queue and user_queue[0] < window_start:
            user_queue.popleft()
        
        return len(user_queue)

    def get_time_until_reset(self, user_id: int) -> int:
        """
        Get time until user can make another request
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Seconds until next request is allowed, 0 if immediately allowed
        """
        if self.is_allowed(user_id):
            return 0
        
        user_queue = self.user_requests[user_id]
        if not user_queue:
            return 0
        
        # Time until the oldest request expires
        oldest_request = user_queue[0]
        reset_time = oldest_request + self.config.rate_limit_window
        current_time = time.time()
        
        return max(0, int(reset_time - current_time))

    def _cleanup_old_entries(self) -> None:
        """Clean up old entries to prevent memory leaks"""
        current_time = time.time()
        window_start = current_time - self.config.rate_limit_window
        
        users_to_remove = []
        
        for user_id, user_queue in self.user_requests.items():
            # Remove old requests
            while user_queue and user_queue[0] < window_start:
                user_queue.popleft()
            
            # Mark empty queues for removal
            if not user_queue:
                users_to_remove.append(user_id)
        
        # Remove empty user entries
        for user_id in users_to_remove:
            del self.user_requests[user_id]
        
        logger.debug(f"Cleaned up {len(users_to_remove)} empty user entries")

    def clear_user_history(self, user_id: int) -> None:
        """
        Clear request history for a specific user
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self.user_requests:
            del self.user_requests[user_id]
            logger.info(f"Cleared rate limit history for user {user_id}")

    def get_stats(self) -> Dict:
        """Get rate limiter statistics"""
        total_users = len(self.user_requests)
        total_requests = sum(len(queue) for queue in self.user_requests.values())
        
        return {
            'total_tracked_users': total_users,
            'total_active_requests': total_requests,
            'config_limit': self.config.rate_limit_requests,
            'config_window': self.config.rate_limit_window
        }
