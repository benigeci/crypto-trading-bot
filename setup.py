#!/usr/bin/env python3
"""
Setup Script for Enhanced Trading Bot
Automates initial setup and configuration
"""

import os
import sys
from pathlib import Path
import subprocess


def print_banner():
    """Print setup banner"""
    print("=" * 60)
    print("🤖 Enhanced Crypto Trading Bot - Setup")
    print("=" * 60)
    print()


def check_python_version():
    """Check Python version"""
    print("✓ Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9+ is required!")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        sys.exit(1)
    print(f"  Python {version.major}.{version.minor}.{version.micro} detected ✓")
    print()


def create_directories():
    """Create necessary directories"""
    print("✓ Creating directories...")
    directories = [
        'data',
        'logs',
        'models',
        'backups'
    ]
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(exist_ok=True)
        print(f"  Created: {directory}/")
    print()


def install_dependencies():
    """Install Python dependencies"""
    print("✓ Installing dependencies...")
    print("  This may take a few minutes...")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True,
            capture_output=True
        )
        print("  Dependencies installed successfully ✓")
    except subprocess.CalledProcessError as e:
        print("❌ Error installing dependencies:")
        print(e.stderr.decode())
        sys.exit(1)
    print()


def setup_environment():
    """Setup .env file"""
    print("✓ Setting up environment variables...")
    
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if env_file.exists():
        print("  .env file already exists")
        response = input("  Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("  Skipping .env setup")
            print()
            return
    
    # Copy .env.example to .env if exists
    if env_example.exists():
        import shutil
        shutil.copy(env_example, env_file)
        print("  Created .env from .env.example")
    else:
        # Create basic .env
        with open(env_file, 'w') as f:
            f.write("# Enhanced Trading Bot Environment Variables\n")
            f.write("EXCHANGE_API_KEY=\n")
            f.write("EXCHANGE_API_SECRET=\n")
            f.write("TELEGRAM_BOT_TOKEN=\n")
            f.write("TELEGRAM_CHAT_ID=\n")
        print("  Created basic .env file")
    
    print("  ⚠️  IMPORTANT: Edit .env and add your API credentials!")
    print()


def setup_config():
    """Setup configuration file"""
    print("✓ Setting up configuration...")
    
    config_file = Path('config.yaml')
    config_enhanced = Path('config_enhanced.yaml')
    
    if config_file.exists():
        print("  config.yaml already exists")
        response = input("  Use enhanced config? (Y/n): ")
        if response.lower() != 'n':
            if config_enhanced.exists():
                import shutil
                shutil.copy(config_enhanced, config_file)
                print("  Updated config.yaml from config_enhanced.yaml")
    else:
        if config_enhanced.exists():
            import shutil
            shutil.copy(config_enhanced, config_file)
            print("  Created config.yaml from config_enhanced.yaml")
        else:
            print("  ⚠️  No config template found, please create config.yaml manually")
    
    print()


def initialize_security():
    """Initialize security manager"""
    print("✓ Initializing security...")
    
    try:
        from security_manager import SecurityManager
        
        print("  Do you want to encrypt your .env file?")
        response = input("  (Recommended for production) (Y/n): ")
        
        if response.lower() != 'n':
            password = input("  Enter master password (leave empty to auto-generate): ")
            
            if not password:
                import secrets
                password = secrets.token_hex(16)
                print(f"  Generated master password: {password}")
                print("  ⚠️  SAVE THIS PASSWORD SECURELY!")
            
            sec_mgr = SecurityManager(master_password=password)
            sec_mgr.load_from_env('.env')
            
            print("  ✓ Credentials encrypted successfully")
            print("  Created: .env.encrypted")
            print("  Created: .secret_key")
            print("  ⚠️  Keep these files secure and backed up!")
    except Exception as e:
        print(f"  ⚠️  Could not initialize security: {e}")
        print("  You can run this manually later")
    
    print()


def run_tests():
    """Run basic tests"""
    print("✓ Running basic tests...")
    
    tests = [
        ("Importing config_models", "from config_models import BotConfig"),
        ("Importing async_data_fetcher", "from async_data_fetcher import AsyncDataFetcher"),
        ("Importing adaptive_strategy", "from adaptive_strategy import AdaptiveStrategyEngine"),
        ("Importing enhanced_risk_manager", "from enhanced_risk_manager import EnhancedRiskManager"),
        ("Importing enhanced_ml_predictor", "from enhanced_ml_predictor import EnhancedMLPredictor"),
        ("Importing security_manager", "from security_manager import SecurityManager"),
    ]
    
    failed = []
    for test_name, test_code in tests:
        try:
            exec(test_code)
            print(f"  ✓ {test_name}")
        except Exception as e:
            print(f"  ❌ {test_name}: {e}")
            failed.append(test_name)
    
    if failed:
        print(f"\n  ⚠️  {len(failed)} tests failed")
        print("  Please check your installation")
    else:
        print("\n  All tests passed ✓")
    
    print()


def print_next_steps():
    """Print next steps"""
    print("=" * 60)
    print("✅ Setup Complete!")
    print("=" * 60)
    print()
    print("📝 Next Steps:")
    print()
    print("1. Edit .env file with your API credentials:")
    print("   - EXCHANGE_API_KEY")
    print("   - EXCHANGE_API_SECRET")
    print("   - TELEGRAM_BOT_TOKEN")
    print("   - TELEGRAM_CHAT_ID")
    print()
    print("2. Review config.yaml and adjust settings:")
    print("   - Set trading.mode to 'paper' for testing")
    print("   - Configure risk management parameters")
    print("   - Adjust ML and strategy settings")
    print()
    print("3. Run the bot in paper trading mode:")
    print("   python main_enhanced.py --mode paper")
    print()
    print("4. Monitor the logs:")
    print("   tail -f logs/trading_bot.log")
    print()
    print("5. When ready for live trading:")
    print("   - Test thoroughly in paper mode (30+ days)")
    print("   - Set trading.mode to 'live' in config.yaml")
    print("   - Start with small capital")
    print("   - Monitor closely")
    print()
    print("📚 Documentation:")
    print("   - README_UPDATE.md - Complete feature guide")
    print("   - config_enhanced.yaml - Configuration reference")
    print()
    print("⚠️  Important Security Notes:")
    print("   - Never commit .env to version control")
    print("   - Backup .env.encrypted and .secret_key")
    print("   - Rotate API keys every 90 days")
    print("   - Use testnet for initial testing")
    print()
    print("💬 Support:")
    print("   - GitHub: https://github.com/benigeci/crypto-trading-bot")
    print()
    print("=" * 60)


def main():
    """Main setup function"""
    try:
        print_banner()
        check_python_version()
        create_directories()
        
        # Ask if user wants to install dependencies
        response = input("Install dependencies now? (Y/n): ")
        if response.lower() != 'n':
            install_dependencies()
        else:
            print("  Skipping dependency installation")
            print("  Run: pip install -r requirements.txt")
            print()
        
        setup_environment()
        setup_config()
        
        # Ask if user wants to initialize security
        response = input("Initialize security encryption? (Y/n): ")
        if response.lower() != 'n':
            initialize_security()
        
        # Run tests
        response = input("Run basic tests? (Y/n): ")
        if response.lower() != 'n':
            run_tests()
        
        print_next_steps()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
