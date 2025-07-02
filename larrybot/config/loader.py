import os
from dotenv import load_dotenv

class Config:
    """
    Loads and provides access to environment-based configuration for LarryBot.
    Single-user system: designed for personal use with one authorized user.
    """
    def __init__(self, env_file: str = '.env'):
        load_dotenv(env_file)
        
        # Required configuration
        self.TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.ALLOWED_TELEGRAM_USER_ID: int = int(os.getenv('ALLOWED_TELEGRAM_USER_ID', '0'))
        
        # Optional configuration with defaults
        self.DATABASE_PATH: str = os.getenv('DATABASE_PATH', 'larrybot.db')
        self.GOOGLE_CLIENT_SECRET_PATH: str = os.getenv('GOOGLE_CLIENT_SECRET_PATH', 'client_secret.json')
        self.LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
        self.MAX_REQUESTS_PER_MINUTE: int = int(os.getenv('MAX_REQUESTS_PER_MINUTE', '60'))
        self.NLP_ENABLED: bool = os.getenv('NLP_ENABLED', 'true').lower() == 'true'
        self.NLP_MODEL: str = os.getenv('NLP_MODEL', 'en_core_web_sm')

    def validate(self) -> None:
        """Validate required configuration values."""
        errors = []
        
        if not self.TELEGRAM_BOT_TOKEN:
            errors.append('TELEGRAM_BOT_TOKEN is required in the environment.')
        
        if not self.ALLOWED_TELEGRAM_USER_ID:
            errors.append('ALLOWED_TELEGRAM_USER_ID is required in the environment.')
        elif self.ALLOWED_TELEGRAM_USER_ID <= 0:
            errors.append('ALLOWED_TELEGRAM_USER_ID must be a positive integer.')
        
        if self.MAX_REQUESTS_PER_MINUTE <= 0:
            errors.append('MAX_REQUESTS_PER_MINUTE must be a positive integer.')
        
        if errors:
            error_message = '\n'.join(errors)
            raise ValueError(f'Configuration validation failed:\n{error_message}')
    
    def get_single_user_info(self) -> dict:
        """Get information about the single-user configuration, including NLP settings."""
        return {
            "authorized_user_id": self.ALLOWED_TELEGRAM_USER_ID,
            "bot_token_configured": bool(self.TELEGRAM_BOT_TOKEN),
            "database_path": self.DATABASE_PATH,
            "rate_limit_per_minute": self.MAX_REQUESTS_PER_MINUTE,
            "log_level": self.LOG_LEVEL,
            "nlp_enabled": self.NLP_ENABLED,
            "nlp_model": self.NLP_MODEL
        } 