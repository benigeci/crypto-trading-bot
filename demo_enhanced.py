"""
Quick start demo for the enhanced bot in paper trading mode
"""
import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from logger import setup_logger
from config_models import BotConfig

logger = setup_logger('demo', log_level='INFO')

async def demo_run():
    """
    Demo run of the enhanced bot
    """
    print("="*70)
    print("🤖 Enhanced Trading Bot - Quick Demo")
    print("="*70)
    print()
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = BotConfig.from_yaml('config_enhanced.yaml')
        
        print(f"✅ Configuration loaded successfully!")
        print(f"   Trading Mode: {config.trading.mode}")
        print(f"   Initial Balance: ${config.trading.initial_balance:,.2f}")
        print(f"   Symbols: {', '.join(config.trading.symbols)}")
        print(f"   Timeframe: {config.trading.timeframe}")
        print()
        
        # Import enhanced modules
        logger.info("Importing enhanced modules...")
        from async_data_fetcher import AsyncDataFetcher
        from adaptive_strategy import AdaptiveStrategyEngine
        from enhanced_risk_manager import EnhancedRiskManager
        from enhanced_ml_predictor import EnhancedMLPredictor
        
        print("✅ All modules imported successfully!")
        print()
        
        # Initialize data fetcher
        logger.info("Initializing async data fetcher...")
        data_fetcher = AsyncDataFetcher(
            exchange_id=config.exchange.name,
            testnet=False
        )
        await data_fetcher.initialize()
        print("✅ Data fetcher initialized!")
        print()
        
        # Fetch sample data
        symbol = config.trading.symbols[0]
        logger.info(f"Fetching data for {symbol}...")
        df = await data_fetcher.fetch_ohlcv_async(
            symbol=symbol,
            timeframe=config.trading.timeframe,
            limit=100
        )
        
        if df is not None and not df.empty:
            print(f"✅ Data fetched successfully for {symbol}!")
            print(f"   Candles: {len(df)}")
            print(f"   Latest price: ${df['close'].iloc[-1]:,.2f}")
            print(f"   24h change: {((df['close'].iloc[-1] / df['close'].iloc[-24] - 1) * 100):.2f}%")
            print()
        
        # Initialize strategy
        logger.info("Initializing adaptive strategy...")
        strategy = AdaptiveStrategyEngine()
        print("✅ Adaptive strategy initialized!")
        print()
        
        # Initialize risk manager
        logger.info("Initializing risk manager...")
        risk_mgr = EnhancedRiskManager(
            initial_capital=config.trading.initial_balance,
            max_position_size_pct=config.trading.position_size_pct,
            max_daily_loss_pct=config.risk_management.max_daily_loss_pct
        )
        print("✅ Risk manager initialized!")
        print()
        
        # Get risk metrics
        metrics = risk_mgr.get_risk_metrics()
        print(f"📊 Risk Metrics:")
        print(f"   Capital: ${risk_mgr.current_capital:,.2f}")
        print(f"   Risk Score: {metrics.risk_score:.1f}/100")
        print()
        
        # Close connections
        await data_fetcher.close()
        
        print("="*70)
        print("✅ Demo completed successfully!")
        print("="*70)
        print()
        print("🚀 Ready to run the full bot!")
        print()
        print("To start paper trading:")
        print("  python main_enhanced.py --mode paper")
        print()
        print("Or double-click:")
        print("  start_enhanced_paper.bat")
        print()
        
    except Exception as e:
        logger.exception(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        print("\nPlease check:")
        print("  1. All dependencies are installed (pip install -r requirements.txt)")
        print("  2. .env file has correct API keys")
        print("  3. config_enhanced.yaml exists")
        return 1
    
    return 0

if __name__ == '__main__':
    try:
        exit_code = asyncio.run(demo_run())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(0)
