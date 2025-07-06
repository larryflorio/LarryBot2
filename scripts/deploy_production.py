#!/usr/bin/env python3
"""
Production deployment script for LarryBot2.
Handles environment setup, validation, and deployment.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any


class ProductionDeployer:
    """Production deployment manager for LarryBot2."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.scripts_dir = self.project_root / 'scripts'
        self.config_dir = self.project_root / 'larrybot' / 'config'
        
    def deploy(self) -> bool:
        """Run the complete production deployment process."""
        print("🚀 Starting LarryBot2 Production Deployment")
        print("=" * 50)
        
        try:
            # Step 1: Environment validation
            if not self._validate_environment():
                return False
            
            # Step 2: Security setup
            if not self._setup_security():
                return False
            
            # Step 3: Configuration validation
            if not self._validate_configuration():
                return False
            
            # Step 4: Health check
            if not self._run_health_check():
                return False
            
            # Step 5: Database setup
            if not self._setup_database():
                return False
            
            # Step 6: Final validation
            if not self._final_validation():
                return False
            
            print("\n✅ Production deployment completed successfully!")
            print("\n📋 Next steps:")
            print("1. Start the bot: python -m larrybot")
            print("2. Monitor health: python -c \"from larrybot.core.health_monitor import run_health_check; from larrybot.config.production import ProductionConfig; print(run_health_check(ProductionConfig()))\"")
            print("3. Check logs for any issues")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Deployment failed: {e}")
            return False
    
    def _validate_environment(self) -> bool:
        """Validate the deployment environment."""
        print("\n🔍 Step 1: Validating Environment")
        
        # Check Python version
        if sys.version_info < (3, 8):
            print("❌ Python 3.8 or higher is required")
            return False
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        
        # Check required packages
        required_packages = [
            'telegram', 'sqlalchemy', 'alembic', 'dotenv',
            'httpx', 'asyncio', 'logging', 'psutil'
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
                print(f"✅ {package}")
            except ImportError:
                missing_packages.append(package)
                print(f"❌ {package} (missing)")
        
        if missing_packages:
            print(f"\n📦 Installing missing packages: {', '.join(missing_packages)}")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing_packages, check=True)
                print("✅ Packages installed successfully")
            except subprocess.CalledProcessError:
                print("❌ Failed to install packages")
                return False
        
        # Check environment variables
        required_vars = ['TELEGRAM_BOT_TOKEN', 'ALLOWED_TELEGRAM_USER_ID']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            print("Please set these variables or create a .env.production file")
            return False
        
        print("✅ Environment validation passed")
        return True
    
    def _setup_security(self) -> bool:
        """Set up security configurations."""
        print("\n🔒 Step 2: Setting Up Security")
        
        try:
            # Set secure file permissions
            files_to_secure = [
                '.env', '.env.production', '.env.local',
                'larrybot.db'
            ]
            
            for file_path in files_to_secure:
                if os.path.exists(file_path):
                    os.chmod(file_path, 0o600)  # Owner read/write only
                    print(f"✅ Secured {file_path}")
            
            # Create logs directory with secure permissions
            logs_dir = self.project_root / 'logs'
            logs_dir.mkdir(exist_ok=True)
            os.chmod(logs_dir, 0o700)  # Owner read/write/execute only
            print("✅ Created secure logs directory")
            
            print("✅ Security setup completed")
            return True
            
        except Exception as e:
            print(f"❌ Security setup failed: {e}")
            return False
    
    def _validate_configuration(self) -> bool:
        """Validate production configuration."""
        print("\n⚙️ Step 3: Validating Configuration")
        
        try:
            # Import and validate production config
            sys.path.insert(0, str(self.project_root))
            from larrybot.config.production import ProductionConfig
            from larrybot.config.validation import validate_config
            
            config = ProductionConfig()
            is_valid, errors, warnings = validate_config(config)
            
            if errors:
                print("❌ Configuration errors:")
                for error in errors:
                    print(f"  - {error}")
                return False
            
            if warnings:
                print("⚠️ Configuration warnings:")
                for warning in warnings:
                    print(f"  - {warning}")
            
            print("✅ Configuration validation passed")
            return True
            
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            return False
    
    def _run_health_check(self) -> bool:
        """Run initial health check."""
        print("\n🏥 Step 4: Running Health Check")
        
        try:
            from larrybot.config.production import ProductionConfig
            from larrybot.core.health_monitor import run_health_check
            
            config = ProductionConfig()
            health_result = run_health_check(config)
            
            print(f"📊 Health Status: {health_result['status']}")
            
            # Show critical issues
            critical_checks = [check for check in health_result['checks'] 
                             if check['status'] == 'critical']
            
            if critical_checks:
                print("❌ Critical health issues found:")
                for check in critical_checks:
                    print(f"  - {check['name']}: {check['message']}")
                return False
            
            # Show warnings
            warning_checks = [check for check in health_result['checks'] 
                            if check['status'] == 'warning']
            
            if warning_checks:
                print("⚠️ Health warnings:")
                for check in warning_checks:
                    print(f"  - {check['name']}: {check['message']}")
            
            print("✅ Health check passed")
            return True
            
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    def _setup_database(self) -> bool:
        """Set up database for production."""
        print("\n🗄️ Step 5: Setting Up Database")
        
        try:
            # Run database migrations
            print("📦 Running database migrations...")
            result = subprocess.run([
                sys.executable, '-m', 'alembic', 'upgrade', 'head'
            ], cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Database migration failed: {result.stderr}")
                return False
            
            print("✅ Database migrations completed")
            
            # Set database file permissions
            db_path = self.project_root / 'larrybot.db'
            if db_path.exists():
                os.chmod(db_path, 0o600)
                print("✅ Database file secured")
            
            print("✅ Database setup completed")
            return True
            
        except Exception as e:
            print(f"❌ Database setup failed: {e}")
            return False
    
    def _final_validation(self) -> bool:
        """Final validation before deployment."""
        print("\n✅ Step 6: Final Validation")
        
        try:
            # Final health check
            from larrybot.config.production import ProductionConfig
            from larrybot.core.health_monitor import run_health_check
            
            config = ProductionConfig()
            health_result = run_health_check(config)
            
            if health_result['status'] == 'critical':
                print("❌ Final health check failed - critical issues found")
                return False
            
            print("✅ Final validation passed")
            return True
            
        except Exception as e:
            print(f"❌ Final validation failed: {e}")
            return False


def main():
    """Main deployment function."""
    deployer = ProductionDeployer()
    
    if deployer.deploy():
        print("\n🎉 LarryBot2 is ready for production!")
        sys.exit(0)
    else:
        print("\n💥 Deployment failed. Please fix the issues and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main() 