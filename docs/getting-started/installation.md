# Installation Guide

Complete installation guide for LarryBot2 with detailed setup instructions and quality verification.

## 📋 System Requirements

### Minimum Requirements
- **Python**: 3.9 or higher
- **RAM**: 512MB available
- **Storage**: 100MB free space
- **OS**: Windows 10+, macOS 10.14+, or Linux

### Recommended Requirements
- **Python**: 3.11 or higher
- **RAM**: 1GB available
- **Storage**: 500MB free space
- **Database**: SQLite (included) or PostgreSQL

## 🔧 Installation Steps

### Step 1: Install Python

#### Windows
1. Download Python from [python.org](https://python.org)
2. Run installer with "Add to PATH" checked
3. Verify installation:
   ```bash
   python --version
   pip --version
   ```

#### macOS (Recommended: pyenv + Homebrew for Developers)

> **Why use pyenv + Homebrew?**
> - Ensures Python is built with OpenSSL (not LibreSSL), avoiding SSL warnings and compatibility issues with libraries like urllib3.
> - Allows easy management of multiple Python versions.

**Step 1: Install Homebrew (if not already installed)**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Step 2: Install pyenv**
```bash
brew install pyenv
```

**Step 3: Install OpenSSL and xz (for lzma support)**
```bash
brew install openssl xz
```

**Step 4: Install Python with OpenSSL support using pyenv**
```bash
env PYTHON_CONFIGURE_OPTS="--with-openssl=$(brew --prefix openssl) --with-lzma=$(brew --prefix xz)" pyenv install 3.9.6
pyenv global 3.9.6
```

**Step 5: Create and activate virtual environment**
```bash
python -m venv venv
source venv/bin/activate
```

**Step 6: Continue with dependency installation**
```bash
pip install -r requirements.txt
```

> For more details, see the [Testing Guide](../developer-guide/development/testing.md).

---

#### macOS (Alternative: System Python)
```bash
# Using Homebrew (recommended)
brew install python

# Or download from python.org
# Verify installation
python3 --version
pip3 --version
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Verify installation
python3 --version
pip3 --version
```

### Step 2: Clone Repository

```bash
# Clone the repository
git clone <repository-url>
cd LarryBot2

# Verify you're in the right directory
ls -la
```

### Step 3: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# Verify activation (should show venv path)
which python
```

### Step 4: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements (includes testing dependencies)
pip install -r requirements.txt

# Verify installation
python -c "import telegram; print('Dependencies installed successfully')"
```

> **Note:** Testing dependencies (pytest, pytest-asyncio, pytest-cov, coverage) are included in requirements.txt. No additional installation is needed to run the test suite.

### Step 5: Database Setup

```bash
# Initialize database
alembic upgrade head

# Verify database creation
ls -la *.db
```

### Step 6: Configuration

#### Create Environment File
```bash
# Copy example environment file
cp .env.example .env

# Edit the file with your settings
nano .env  # or use your preferred editor
```

#### Required Environment Variables

```bash
# Required: Your Telegram bot token
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Required: Your Telegram user ID
ALLOWED_TELEGRAM_USER_ID=your_user_id_here

# Optional: Database URL (defaults to SQLite)
DATABASE_PATH=larrybot.db

# Optional: Logging level
LOG_LEVEL=INFO

# Optional: Google Calendar credentials (for calendar integration)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
```

#### Get Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Copy the token provided
5. Add token to your `.env` file

#### Get Your Telegram User ID

1. Open Telegram and search for [@userinfobot](https://t.me/userinfobot)
2. Send any message to the bot
3. Copy your user ID (number only)
4. Add user ID to your `.env` file

### Step 7: Quality Verification

#### Run Test Suite
```bash
# Run comprehensive test suite (dependencies already installed)
python -m pytest --cov=larrybot --cov-report=term-missing -v

# Expected results:
# - 492 tests passing
# - 85% coverage (3,238 statements)
# - 0 failures, 5 warnings (non-critical)
```

#### Verify Test Coverage
```bash
# Check specific component coverage
python -m pytest --cov=larrybot.handlers.bot tests/test_handlers_bot_comprehensive.py -v
python -m pytest --cov=larrybot.services.health_service tests/test_services_health_service_comprehensive.py -v
```

#### Test Command Registration
```bash
# Verify all 91 commands are registered
python test_commands.py

# Expected output:
# ✅ Found 62 registered commands
# ✅ All Core Commands Present
# ✅ Loaded 12 plugins
```

### Step 8: Start the Bot

```bash
# Start LarryBot2
python -m larrybot

# You should see:
# Starting LarryBot...
# LarryBot initialized. Starting Telegram bot handler...
```

## 🚨 Troubleshooting

### Common Installation Issues

#### Python Version Issues
```bash
# Check Python version
python --version
# Should be 3.9 or higher

# If not, install correct version
# macOS: brew install python@3.9
# Ubuntu: sudo apt install python3.9
# Windows: Download from python.org
```

#### Virtual Environment Issues
```bash
# If virtual environment not activated
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# If virtual environment corrupted
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Dependency Installation Issues
```bash
# If pip fails to install packages
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall

# If SSL certificate issues
pip install -r requirements.txt --trusted-host pypi.org --trusted-host pypi.python.org
```

#### Configuration Issues
```bash
# If .env file not found
cp .env.example .env

# If configuration validation fails
python -c "from larrybot.config.loader import Config; Config().validate()"

# Check for common errors:
# - TELEGRAM_BOT_TOKEN not set
# - ALLOWED_TELEGRAM_USER_ID not set
# - Invalid token format
# - Invalid user ID format
```

#### Database Issues
```bash
# If database migration fails
rm larrybot.db  # Remove existing database
alembic upgrade head  # Recreate database

# If permission denied
chmod 644 larrybot.db
```

### Platform-Specific Issues

#### macOS Issues
```bash
# If OpenSSL issues
brew install openssl
export LDFLAGS="-L$(brew --prefix openssl)/lib"
export CPPFLAGS="-I$(brew --prefix openssl)/include"

# If pyenv issues
brew install pyenv
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
```

#### Windows Issues
```bash
# If pip not found
python -m ensurepip --upgrade

# If virtual environment activation fails
# Use PowerShell or Command Prompt
# Make sure execution policy allows scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Linux Issues
```bash
# If build dependencies missing
sudo apt install build-essential libssl-dev libffi-dev python3-dev

# If permission issues
sudo chown -R $USER:$USER /path/to/LarryBot2
```

## ✅ Verification Checklist

Before proceeding, ensure you have:

- [ ] Python 3.9+ installed and working
- [ ] Virtual environment created and activated
- [ ] All dependencies installed successfully
- [ ] Database initialized with `alembic upgrade head`
- [ ] `.env` file created with valid configuration
- [ ] Test suite passes (492 tests)
- [ ] Command registration verified (91 commands)
- [ ] Bot starts without errors

## 🔧 Next Steps

After successful installation:

1. **Configure your bot** - See [Configuration Guide](configuration.md)
2. **Learn the commands** - See [User Guide](../user-guide/README.md)
3. **Set up calendar integration** - See [Calendar Integration](../user-guide/commands/calendar-integration.md)
4. **Explore advanced features** - See [Advanced Tasks](../user-guide/features/advanced-tasks.md)

## 📞 Getting Help

If you encounter issues:

1. **Check this troubleshooting section**
2. **Review the [Troubleshooting Guide](troubleshooting.md)**
3. **Enable debug logging** in your `.env` file: `LOG_LEVEL=DEBUG`
4. **Check the logs** when running the bot
5. **Report issues** with detailed error messages

---

**Related Guides:** [Configuration](configuration.md) | [Troubleshooting](troubleshooting.md) | [Quick Start](quick-start.md)

**Last Updated**: June 28, 2025 