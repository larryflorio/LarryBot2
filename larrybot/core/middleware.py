from typing import List, Callable, Any, Optional
from telegram import Update
from telegram.ext import ContextTypes
from abc import ABC, abstractmethod
import time

class Middleware(ABC):
    """Abstract base class for middleware components."""
    
    @abstractmethod
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE, next_middleware: Callable) -> Any:
        """Process the request and call the next middleware in the chain."""
        pass

class LoggingMiddleware(Middleware):
    """Middleware for logging command execution."""
    
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE, next_middleware: Callable) -> Any:
        """Log command execution and timing."""
        start_time = time.time()
        
        # Log incoming command
        if update.message and update.message.text:
            print(f"Executing command: {update.message.text}")
        
        try:
            result = await next_middleware(update, context)
            execution_time = time.time() - start_time
            print(f"Command completed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"Command failed after {execution_time:.3f}s: {e}")
            raise

class PerformanceMonitoringMiddleware(Middleware):
    """Middleware for collecting performance metrics."""
    
    def __init__(self, metrics_collector):
        self.metrics_collector = metrics_collector
    
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE, next_middleware: Callable) -> Any:
        """Collect performance metrics for command execution."""
        start_time = time.time()
        success = True
        error_message = None
        
        # Get command info
        command = update.message.text if update.message and update.message.text else "unknown"
        
        try:
            result = await next_middleware(update, context)
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            execution_time = time.time() - start_time
            
            # Record metrics
            self.metrics_collector.record_command(
                command=command,
                execution_time=execution_time,
                success=success,
                error_message=error_message
            )
        
        return result

class AuthorizationMiddleware(Middleware):
    """Middleware for checking user authorization."""
    
    def __init__(self, allowed_user_id: int):
        self.allowed_user_id = allowed_user_id
    
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE, next_middleware: Callable) -> Any:
        """Check if the user is authorized to use the bot."""
        if update.effective_user and update.effective_user.id != self.allowed_user_id:
            await update.message.reply_text("You are not authorized to use this bot.")
            return
        
        return await next_middleware(update, context)

class RateLimitingMiddleware(Middleware):
    """Middleware for rate limiting commands."""
    
    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests = max_requests_per_minute
        self.requests = []
    
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE, next_middleware: Callable) -> Any:
        """Check rate limits before processing command."""
        current_time = time.time()
        
        # Clean old requests (older than 1 minute)
        self.requests = [req_time for req_time in self.requests 
                        if current_time - req_time < 60]
        
        # Check rate limit
        if len(self.requests) >= self.max_requests:
            await update.message.reply_text("Rate limit exceeded. Please wait before sending more commands.")
            return
        
        # Add current request
        self.requests.append(current_time)
        
        return await next_middleware(update, context)

class MiddlewareChain:
    """Chain of middleware components."""
    
    def __init__(self):
        self.middleware: List[Middleware] = []
    
    def add_middleware(self, middleware: Middleware) -> None:
        """Add middleware to the chain."""
        self.middleware.append(middleware)
    
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE, final_handler: Callable) -> Any:
        """Execute the middleware chain."""
        async def execute_middleware(index: int) -> Any:
            if index >= len(self.middleware):
                return await final_handler(update, context)
            
            return await self.middleware[index].process(update, context, 
                                                       lambda u, c: execute_middleware(index + 1))
        
        return await execute_middleware(0) 