"""
Quick test script to verify all modules are working
"""
import sys

def test_imports():
    """Test all module imports"""
    print("🔍 Testing module imports...")
    
    modules = [
        ('logger', 'Logger'),
        ('config_models', 'Configuration Models'),
        ('async_data_fetcher', 'Async Data Fetcher'),
        ('adaptive_strategy', 'Adaptive Strategy'),
        ('enhanced_risk_manager', 'Enhanced Risk Manager'),
        ('enhanced_ml_predictor', 'Enhanced ML Predictor'),
        ('security_manager', 'Security Manager'),
    ]
    
    failed = []
    
    for module, name in modules:
        try:
            __import__(module)
            print(f"  ✅ {name} - OK")
        except Exception as e:
            print(f"  ❌ {name} - FAILED: {e}")
            failed.append((name, str(e)))
    
    print()
    
    if failed:
        print(f"⚠️  {len(failed)} module(s) failed to import:")
        for name, error in failed:
            print(f"  - {name}: {error}")
        return False
    else:
        print("✅ All modules imported successfully!")
        return True

def test_config():
    """Test configuration loading"""
    print("\n🔍 Testing configuration...")
    
    try:
        from config_models import BotConfig
        
        # Try to load config
        config = BotConfig.from_yaml('config_enhanced.yaml')
        print(f"  ✅ Configuration loaded successfully")
        print(f"  📊 Trading mode: {config.trading.mode}")
        print(f"  💰 Initial balance: ${config.trading.initial_balance}")
        print(f"  📈 Symbols: {', '.join(config.trading.symbols)}")
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration failed: {e}")
        return False

def test_directories():
    """Test required directories"""
    print("\n🔍 Testing directories...")
    
    import os
    
    directories = ['data', 'logs', 'models', 'backups']
    all_exist = True
    
    for directory in directories:
        if os.path.exists(directory):
            print(f"  ✅ {directory}/ - exists")
        else:
            print(f"  ❌ {directory}/ - missing")
            all_exist = False
            try:
                os.makedirs(directory)
                print(f"     Created {directory}/")
            except Exception as e:
                print(f"     Failed to create: {e}")
    
    return all_exist

def test_dependencies():
    """Test critical dependencies"""
    print("\n🔍 Testing dependencies...")
    
    deps = [
        ('pandas', 'Pandas'),
        ('numpy', 'NumPy'),
        ('ccxt', 'CCXT'),
        ('sklearn', 'Scikit-learn'),
        ('xgboost', 'XGBoost'),
        ('pydantic', 'Pydantic'),
        ('cryptography', 'Cryptography'),
        ('aiohttp', 'Aiohttp'),
    ]
    
    failed = []
    
    for module, name in deps:
        try:
            __import__(module)
            print(f"  ✅ {name} - installed")
        except Exception as e:
            print(f"  ❌ {name} - missing")
            failed.append(name)
    
    if failed:
        print(f"\n⚠️  {len(failed)} dependencies missing:")
        print("  Run: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Run all tests"""
    print("="*60)
    print("🤖 Enhanced Trading Bot - System Check")
    print("="*60)
    print()
    
    results = []
    
    # Test dependencies
    results.append(("Dependencies", test_dependencies()))
    
    # Test imports
    results.append(("Module Imports", test_imports()))
    
    # Test directories
    results.append(("Directories", test_directories()))
    
    # Test config
    results.append(("Configuration", test_config()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print()
    
    if passed == total:
        print(f"✅ All tests passed! ({passed}/{total})")
        print("\n🚀 Ready to run the bot!")
        print("\n📝 Next steps:")
        print("  1. Edit .env with your API credentials")
        print("  2. Review config_enhanced.yaml settings")
        print("  3. Run: python main_enhanced.py --mode paper")
        return 0
    else:
        print(f"⚠️  {total - passed} test(s) failed ({passed}/{total} passed)")
        print("\n🔧 Please fix the issues above before running the bot")
        return 1

if __name__ == '__main__':
    sys.exit(main())
