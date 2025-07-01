import pytest
import os
import sys
import subprocess
from unittest.mock import patch, mock_open
from larrybot.config.loader import Config


def run_subprocess_test(test_code: str):
    """Helper to run a test in a subprocess with a clean environment."""
    import tempfile
    import textwrap
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(textwrap.dedent(test_code))
        test_file = f.name
    # Run pytest on the temp file with a clean environment
    env = {}
    result = subprocess.run([
        sys.executable, '-m', 'pytest', test_file, '-v', '--tb=short'
    ], capture_output=True, env=env, text=True)
    os.unlink(test_file)
    return result

class TestConfig:
    """Test cases for the Config class."""

    def test_config_initialization_default_env_file(self):
        """Test that Config initializes with default .env file."""
        with patch('larrybot.config.loader.load_dotenv') as mock_load_dotenv:
            config = Config()
            mock_load_dotenv.assert_called_once_with('.env')

    def test_config_initialization_custom_env_file(self):
        """Test that Config initializes with custom env file."""
        with patch('larrybot.config.loader.load_dotenv') as mock_load_dotenv:
            config = Config('custom.env')
            mock_load_dotenv.assert_called_once_with('custom.env')

    def test_config_with_valid_environment_variables(self):
        """Test that Config loads valid environment variables."""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'test_token_123',
            'ALLOWED_TELEGRAM_USER_ID': '123456789'
        }):
            config = Config()
            assert config.TELEGRAM_BOT_TOKEN == 'test_token_123'
            assert config.ALLOWED_TELEGRAM_USER_ID == 123456789

    def test_config_with_missing_environment_variables(self):
        """Test that Config uses default values for missing environment variables (subprocess)."""
        test_code = '''
        import pytest
        from unittest.mock import patch
        from larrybot.config.loader import Config
        def test():
            with patch('larrybot.config.loader.load_dotenv', lambda *a, **k: None):
                config = Config()
                assert config.TELEGRAM_BOT_TOKEN == ''
                assert config.ALLOWED_TELEGRAM_USER_ID == 0
        '''
        result = run_subprocess_test(test_code)
        assert result.returncode == 0, result.stdout + result.stderr

    def test_config_with_invalid_user_id(self):
        """Test that Config handles invalid user ID gracefully."""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'test_token',
            'ALLOWED_TELEGRAM_USER_ID': 'invalid_id'
        }):
            with pytest.raises(ValueError, match="invalid literal for int"):
                config = Config()

    def test_config_validation_with_valid_config(self):
        """Test that validation passes with valid configuration."""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'test_token_123',
            'ALLOWED_TELEGRAM_USER_ID': '123456789'
        }):
            config = Config()
            # Should not raise any exception
            config.validate()

    def test_config_validation_missing_bot_token(self):
        """Test that validation fails when bot token is missing (subprocess)."""
        test_code = '''
        import pytest
        from unittest.mock import patch
        from larrybot.config.loader import Config
        def test():
            import os
            with patch('larrybot.config.loader.load_dotenv', lambda *a, **k: None):
                os.environ['ALLOWED_TELEGRAM_USER_ID'] = '123456789'
                config = Config()
                with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN is required"):
                    config.validate()
        '''
        result = run_subprocess_test(test_code)
        assert result.returncode == 0, result.stdout + result.stderr

    def test_config_validation_missing_user_id(self):
        """Test that validation fails when user ID is missing (subprocess)."""
        test_code = '''
        import pytest
        from unittest.mock import patch
        from larrybot.config.loader import Config
        def test():
            import os
            with patch('larrybot.config.loader.load_dotenv', lambda *a, **k: None):
                os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_123'
                config = Config()
                with pytest.raises(ValueError, match="ALLOWED_TELEGRAM_USER_ID is required"):
                    config.validate()
        '''
        result = run_subprocess_test(test_code)
        assert result.returncode == 0, result.stdout + result.stderr

    def test_config_validation_empty_bot_token(self):
        """Test that validation fails when bot token is empty."""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': '',
            'ALLOWED_TELEGRAM_USER_ID': '123456789'
        }):
            config = Config()
            with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN is required"):
                config.validate()

    def test_config_validation_zero_user_id(self):
        """Test that validation fails when user ID is zero."""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'test_token_123',
            'ALLOWED_TELEGRAM_USER_ID': '0'
        }):
            config = Config()
            with pytest.raises(ValueError, match="ALLOWED_TELEGRAM_USER_ID is required"):
                config.validate()

    def test_config_validation_both_missing(self):
        """Test that validation fails when both required values are missing (subprocess)."""
        test_code = '''
        import pytest
        from unittest.mock import patch
        from larrybot.config.loader import Config
        def test():
            with patch('larrybot.config.loader.load_dotenv', lambda *a, **k: None):
                config = Config()
                with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN is required"):
                    config.validate()
        '''
        result = run_subprocess_test(test_code)
        assert result.returncode == 0, result.stdout + result.stderr

    def test_config_with_whitespace_values(self):
        """Test that Config handles whitespace in environment variables."""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': '  test_token  ',
            'ALLOWED_TELEGRAM_USER_ID': '  123456789  '
        }):
            config = Config()
            assert config.TELEGRAM_BOT_TOKEN == '  test_token  '
            assert config.ALLOWED_TELEGRAM_USER_ID == 123456789

    def test_config_with_special_characters(self):
        """Test that Config handles special characters in environment variables."""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'test_token_with_special_chars!@#$%^&*()',
            'ALLOWED_TELEGRAM_USER_ID': '987654321'
        }):
            config = Config()
            assert config.TELEGRAM_BOT_TOKEN == 'test_token_with_special_chars!@#$%^&*()'
            assert config.ALLOWED_TELEGRAM_USER_ID == 987654321 