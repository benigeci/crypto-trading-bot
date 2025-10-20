"""
Test Runner - Validate all bot components
"""
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logger import get_logger
from database import TradingDatabase
from data_fetcher import DataFetcher
from analyzer import TechnicalAnalyzer
from trader import Trader
from backtester import Backtester


class BotTester:
    """
    Comprehensive testing suite for the trading bot
    """
    
    def __init__(self):
        self.logger = get_logger(log_level='INFO')
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
    
    def run_test(self, test_name, test_func):
        """
        Run a single test
        
        Args:
            test_name: Name of the test
            test_func: Test function to execute
        """
        self.logger.info(f"Running test: {test_name}")
        
        try:
            result = test_func()
            if result:
                self.logger.info(f"✓ PASSED: {test_name}")
                self.tests_passed += 1
                self.test_results.append((test_name, 'PASSED', ''))
            else:
                self.logger.error(f"✗ FAILED: {test_name}")
                self.tests_failed += 1
                self.test_results.append((test_name, 'FAILED', 'Test returned False'))
        except Exception as e:
            self.logger.error(f"✗ FAILED: {test_name} - {str(e)}")
            self.tests_failed += 1
            self.test_results.append((test_name, 'FAILED', str(e)))
    
    def test_logger(self):
        """Test logging system"""
        try:
            logger = get_logger(log_level='DEBUG')
            logger.debug("Debug test")
            logger.info("Info test")
            logger.warning("Warning test")
            logger.log_signal('BUY', 'TEST/USDT', 100.0, {'RSI': 30}, 85)
            logger.log_trade('BUY', 'TEST/USDT', 100.0, 1.0, 'Test trade')
            return True
        except Exception as e:
            self.logger.error(f"Logger test failed: {e}")
            return False
    
    def test_database(self):
        """Test database operations"""
        try:
            db = TradingDatabase('data/test_bot.db')
            
            # Test insert trade
            trade_id = db.insert_trade('BTC/USDT', 'BUY', 45000.0, 0.1, reason='Test')
            assert trade_id > 0, "Failed to insert trade"
            
            # Test insert signal
            signal_id = db.insert_signal('BTC/USDT', 'BUY', 45000.0, {'RSI': 30}, 85)
            assert signal_id > 0, "Failed to insert signal"
            
            # Test update portfolio
            db.update_portfolio('BTC/USDT', 0.1, 45000.0, 46000.0)
            
            # Test update balance
            db.update_balance(10000.0, 14600.0, 4600.0, 46.0)
            
            # Test get trades
            trades = db.get_trades(limit=10)
            assert len(trades) > 0, "No trades retrieved"
            
            # Test get signals
            signals = db.get_signals(limit=10)
            assert len(signals) > 0, "No signals retrieved"
            
            # Test performance summary
            summary = db.get_performance_summary()
            assert 'total_trades' in summary, "Performance summary incomplete"
            
            self.logger.info(f"Database test: {len(trades)} trades, {len(signals)} signals")
            return True
            
        except Exception as e:
            self.logger.error(f"Database test failed: {e}")
            return False
    
    def test_data_fetcher(self):
        """Test data fetching"""
        try:
            fetcher = DataFetcher(primary_source='binance')
            
            # Test fetch OHLCV
            df = fetcher.fetch_ohlcv('BTC/USDT', '15m', 100)
            assert df is not None, "Failed to fetch OHLCV data"
            assert len(df) > 0, "Empty dataframe returned"
            assert 'close' in df.columns, "Missing required columns"
            
            # Test fetch current price
            price = fetcher.fetch_current_price('BTC/USDT')
            assert price is not None, "Failed to fetch current price"
            assert price > 0, "Invalid price returned"
            
            # Test fetch ticker
            ticker = fetcher.fetch_ticker_info('BTC/USDT')
            assert ticker is not None, "Failed to fetch ticker info"
            assert 'price' in ticker, "Ticker info incomplete"
            
            self.logger.info(f"Data fetcher test: {len(df)} candles, price: ${price}")
            return True
            
        except Exception as e:
            self.logger.error(f"Data fetcher test failed: {e}")
            return False
    
    def test_analyzer(self):
        """Test technical analysis"""
        try:
            fetcher = DataFetcher()
            df = fetcher.fetch_ohlcv('BTC/USDT', '15m', 500)
            
            if df is None:
                self.logger.warning("Could not fetch data for analyzer test")
                return False
            
            analyzer = TechnicalAnalyzer()
            
            # Test indicator calculation
            df_with_indicators = analyzer.calculate_all_indicators(df)
            
            # Check if indicators are calculated
            required_indicators = ['rsi', 'macd', 'ema_9', 'bb_upper', 'volume_ma']
            for indicator in required_indicators:
                assert indicator in df_with_indicators.columns, f"Missing indicator: {indicator}"
            
            # Test signal generation
            signal, strength, indicators = analyzer.generate_signal(df_with_indicators, 'BTC/USDT')
            assert signal in ['BUY', 'SELL', 'HOLD'], "Invalid signal type"
            assert 0 <= strength <= 100, "Invalid signal strength"
            assert isinstance(indicators, dict), "Invalid indicators format"
            
            self.logger.info(f"Analyzer test: Signal={signal}, Strength={strength}%")
            return True
            
        except Exception as e:
            self.logger.error(f"Analyzer test failed: {e}")
            return False
    
    def test_trader(self):
        """Test trading execution (paper mode)"""
        try:
            trader = Trader(mode='paper', initial_balance=10000)
            
            # Test buy
            trade = trader.execute_buy('BTC/USDT', 45000.0, 'Test buy', 85)
            assert trade is not None, "Buy execution failed"
            assert trade['action'] == 'BUY', "Invalid trade action"
            
            # Test status
            status = trader.get_status()
            assert status['positions'] == 1, "Position not recorded"
            assert status['balance'] < 10000, "Balance not updated"
            
            # Test stop loss check
            action = trader.check_stop_loss_take_profit('BTC/USDT', 43000.0)
            assert action == 'SELL', "Stop loss not triggered"
            
            # Test sell
            trade = trader.execute_sell('BTC/USDT', 46000.0, 'Test sell')
            assert trade is not None, "Sell execution failed"
            assert trade['action'] == 'SELL', "Invalid trade action"
            assert 'profit_loss' in trade, "P/L not calculated"
            
            # Final status
            final_status = trader.get_status()
            assert final_status['positions'] == 0, "Position not closed"
            
            self.logger.info(f"Trader test: Final balance=${final_status['balance']:.2f}")
            return True
            
        except Exception as e:
            self.logger.error(f"Trader test failed: {e}")
            return False
    
    def test_backtester(self):
        """Test backtesting"""
        try:
            fetcher = DataFetcher()
            df = fetcher.fetch_ohlcv('BTC/USDT', '1h', 500)
            
            if df is None:
                self.logger.warning("Could not fetch data for backtest")
                return False
            
            analyzer = TechnicalAnalyzer()
            backtester = Backtester(initial_balance=10000)
            
            # Run backtest
            results = backtester.run_backtest(df, 'BTC/USDT', analyzer)
            
            # Verify results
            assert 'total_trades' in results, "Missing total_trades"
            assert 'win_rate' in results, "Missing win_rate"
            assert 'total_return' in results, "Missing total_return"
            assert 'final_balance' in results, "Missing final_balance"
            
            self.logger.info(f"Backtest: {results['total_trades']} trades, "
                           f"{results['win_rate']}% win rate, "
                           f"{results['total_return']}% return")
            return True
            
        except Exception as e:
            self.logger.error(f"Backtester test failed: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        self.logger.info("=" * 60)
        self.logger.info("Starting Bot Component Tests")
        self.logger.info("=" * 60)
        
        # Run tests
        self.run_test("Logger System", self.test_logger)
        self.run_test("Database Operations", self.test_database)
        self.run_test("Data Fetcher", self.test_data_fetcher)
        self.run_test("Technical Analyzer", self.test_analyzer)
        self.run_test("Trader (Paper Mode)", self.test_trader)
        self.run_test("Backtester", self.test_backtester)
        
        # Print summary
        self.logger.info("=" * 60)
        self.logger.info("Test Summary")
        self.logger.info("=" * 60)
        
        for test_name, status, error in self.test_results:
            symbol = "✓" if status == "PASSED" else "✗"
            self.logger.info(f"{symbol} {test_name}: {status}")
            if error:
                self.logger.error(f"  Error: {error}")
        
        total_tests = self.tests_passed + self.tests_failed
        pass_rate = (self.tests_passed / total_tests * 100) if total_tests > 0 else 0
        
        self.logger.info("=" * 60)
        self.logger.info(f"Total Tests: {total_tests}")
        self.logger.info(f"Passed: {self.tests_passed}")
        self.logger.info(f"Failed: {self.tests_failed}")
        self.logger.info(f"Pass Rate: {pass_rate:.1f}%")
        self.logger.info("=" * 60)
        
        return self.tests_failed == 0


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║              🧪  BOT COMPONENT TESTING  🧪               ║
    ║                                                           ║
    ║         Validating all bot systems and modules           ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    tester = BotTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ All tests passed! Bot is ready to run.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please review the errors above.")
        sys.exit(1)
