"""
Main Bot Orchestrator - Coordinates all modules for 24/7 operation
"""
import os
import sys
import time
import yaml
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List

from logger import get_logger
from database import TradingDatabase
from data_fetcher import DataFetcher
from analyzer import TechnicalAnalyzer
from trader import Trader
from telegram_bot import TelegramBot
from backtester import Backtester


class TradingBot:
    """
    Main trading bot orchestrator
    """
    
    def __init__(self, config_path='config.yaml'):
        """
        Initialize trading bot
        
        Args:
            config_path: Path to configuration file
        """
        # Load environment variables
        load_dotenv()
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize logger
        log_level = os.getenv('LOG_LEVEL', self.config.get('logging', {}).get('level', 'INFO'))
        self.logger = get_logger(log_level=log_level)
        
        self.logger.info("=" * 60)
        self.logger.info("Initializing Crypto Trading Bot")
        self.logger.info("=" * 60)
        
        # Initialize database
        db_path = self.config.get('database', {}).get('path', 'data/trading_bot.db')
        self.db = TradingDatabase(db_path)
        self.logger.info("Database initialized")
        
        # Initialize data fetcher
        self.data_fetcher = DataFetcher(
            primary_source=self.config.get('data', {}).get('sources', {}).get('primary', 'binance'),
            backup_source=self.config.get('data', {}).get('sources', {}).get('backup', 'coingecko'),
            api_key=os.getenv('BINANCE_API_KEY'),
            api_secret=os.getenv('BINANCE_API_SECRET')
        )
        self.logger.info("Data fetcher initialized")
        
        # Initialize technical analyzer
        self.analyzer = TechnicalAnalyzer(config=self.config.get('indicators', {}))
        self.logger.info("Technical analyzer initialized")
        
        # Initialize trader
        trading_mode = os.getenv('TRADING_MODE', 'paper')
        initial_balance = float(os.getenv('INITIAL_BALANCE', 10000))
        
        self.trader = Trader(
            mode=trading_mode,
            initial_balance=initial_balance,
            api_key=os.getenv('BINANCE_API_KEY') if trading_mode == 'live' else None,
            api_secret=os.getenv('BINANCE_API_SECRET') if trading_mode == 'live' else None,
            config=self.config
        )
        self.logger.info(f"Trader initialized in {trading_mode} mode")
        
        # Initialize Telegram bot
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if telegram_token and telegram_chat_id:
            self.telegram_bot = TelegramBot(
                token=telegram_token,
                chat_id=telegram_chat_id,
                trader=self.trader,
                analyzer=self.analyzer,
                data_fetcher=self.data_fetcher,
                config=self.config
            )
            self.logger.info("Telegram bot initialized")
        else:
            self.telegram_bot = None
            self.logger.warning("Telegram bot not configured (missing token or chat ID)")
        
        # Bot settings
        self.symbols = self.config.get('symbols', ['BTC/USDT'])
        self.timeframe = self.config.get('data', {}).get('primary_timeframe', '15m')
        self.update_interval = int(os.getenv('UPDATE_INTERVAL', 
                                    self.config.get('bot', {}).get('update_interval', 300)))
        self.auto_trade = self.config.get('bot', {}).get('auto_trade', False)
        
        # State
        self.running = False
        self.last_signals = {}
        
        self.logger.info("Trading bot initialization complete")
        self.logger.info(f"Monitoring symbols: {', '.join(self.symbols)}")
        self.logger.info(f"Update interval: {self.update_interval} seconds")
    
    def run_backtest(self, symbol: str = 'BTC/USDT', timeframe: str = '1h', 
                    candles: int = 1000):
        """
        Run backtest before starting live trading
        
        Args:
            symbol: Trading pair to backtest
            timeframe: Timeframe for backtest
            candles: Number of candles to fetch
        """
        self.logger.info("=" * 60)
        self.logger.info(f"Running Backtest for {symbol}")
        self.logger.info("=" * 60)
        
        # Fetch historical data
        df = self.data_fetcher.fetch_ohlcv(symbol, timeframe, candles)
        
        if df is None:
            self.logger.error("Failed to fetch data for backtest")
            return None
        
        # Run backtest
        backtester = Backtester(
            initial_balance=self.trader.initial_balance,
            commission=0.001,
            slippage=0.0005
        )
        
        results = backtester.run_backtest(
            df, symbol, self.analyzer,
            stop_loss_percent=self.config.get('risk', {}).get('stop_loss', {}).get('percent', 3),
            take_profit_percent=self.config.get('risk', {}).get('take_profit', {}).get('levels', [{}])[0].get('percent', 5)
        )
        
        # Display results
        self.logger.info("=" * 60)
        self.logger.info("Backtest Results")
        self.logger.info("=" * 60)
        self.logger.info(f"Total Trades: {results['total_trades']}")
        self.logger.info(f"Win Rate: {results['win_rate']}%")
        self.logger.info(f"Total Return: {results['total_return']}%")
        self.logger.info(f"Net Profit: ${results['net_profit']}")
        self.logger.info(f"Max Drawdown: {results['max_drawdown']}%")
        self.logger.info(f"Sharpe Ratio: {results['sharpe_ratio']}")
        self.logger.info(f"Profit Factor: {results['profit_factor']}")
        self.logger.info("=" * 60)
        
        return results
    
    async def analyze_and_trade(self, symbol: str):
        """
        Analyze symbol and execute trade if signal is strong
        
        Args:
            symbol: Trading pair to analyze
        """
        try:
            # Fetch data
            df = self.data_fetcher.fetch_ohlcv(symbol, self.timeframe, 500)
            
            if df is None:
                self.logger.warning(f"Could not fetch data for {symbol}")
                return
            
            # Calculate indicators and generate signal
            df = self.analyzer.calculate_all_indicators(df)
            signal, strength, indicators = self.analyzer.generate_signal(df, symbol)
            
            current_price = df.iloc[-1]['close']
            
            # Store signal in database
            self.db.insert_signal(
                symbol=symbol,
                signal_type=signal,
                price=current_price,
                indicators=indicators,
                strength=strength
            )
            
            # Check if signal has changed
            last_signal = self.last_signals.get(symbol, {}).get('signal')
            if last_signal != signal and signal != 'HOLD':
                self.logger.info(f"New signal for {symbol}: {signal} (Strength: {strength}%)")
                
                # Notify via Telegram
                if self.telegram_bot and self.config.get('bot', {}).get('notifications', {}).get('signals', True):
                    await self.telegram_bot.notify_signal(symbol, signal, strength, current_price)
            
            # Update last signal
            self.last_signals[symbol] = {
                'signal': signal,
                'strength': strength,
                'price': current_price,
                'timestamp': datetime.now()
            }
            
            # Execute trade if auto_trade is enabled
            if self.auto_trade and signal in ['BUY', 'SELL']:
                await self._execute_auto_trade(symbol, signal, current_price, strength)
            
            # Check stop loss / take profit for existing positions
            self._check_risk_management(symbol, current_price)
            
        except Exception as e:
            self.logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
    
    async def _execute_auto_trade(self, symbol: str, signal: str, price: float, strength: int):
        """
        Execute automatic trade based on signal
        
        Args:
            symbol: Trading pair
            signal: BUY or SELL
            price: Current price
            strength: Signal strength
        """
        try:
            if signal == 'BUY':
                trade = self.trader.execute_buy(
                    symbol=symbol,
                    price=price,
                    reason=f'Auto trade - Signal strength: {strength}%',
                    signal_strength=strength
                )
                
                if trade and self.telegram_bot:
                    await self.telegram_bot.notify_trade('BUY', symbol, price, trade['amount'])
            
            elif signal == 'SELL':
                trade = self.trader.execute_sell(
                    symbol=symbol,
                    price=price,
                    reason=f'Auto trade - Signal strength: {strength}%'
                )
                
                if trade and self.telegram_bot:
                    await self.telegram_bot.notify_trade('SELL', symbol, price, trade['amount'])
            
        except Exception as e:
            self.logger.error(f"Error executing auto trade for {symbol}: {e}", exc_info=True)
    
    def _check_risk_management(self, symbol: str, current_price: float):
        """
        Check stop loss and take profit conditions
        
        Args:
            symbol: Trading pair
            current_price: Current price
        """
        try:
            action = self.trader.check_stop_loss_take_profit(symbol, current_price)
            
            if action == 'SELL':
                self.logger.warning(f"Risk management triggered for {symbol}")
                trade = self.trader.execute_sell(
                    symbol=symbol,
                    price=current_price,
                    reason='Risk management - Stop loss or take profit'
                )
                
                if trade and self.telegram_bot:
                    asyncio.create_task(
                        self.telegram_bot.notify_trade('SELL', symbol, current_price, trade['amount'])
                    )
        
        except Exception as e:
            self.logger.error(f"Error checking risk management for {symbol}: {e}", exc_info=True)
    
    async def trading_loop(self):
        """
        Main trading loop - runs continuously
        """
        self.logger.info("Starting trading loop...")
        
        while self.running:
            try:
                self.logger.info(f"Scanning {len(self.symbols)} symbols...")
                
                # Analyze each symbol
                for symbol in self.symbols:
                    await self.analyze_and_trade(symbol)
                    await asyncio.sleep(1)  # Small delay between symbols
                
                # Update portfolio in database
                status = self.trader.get_status()
                self.db.update_balance(
                    balance=status['balance'],
                    equity=status['equity'],
                    profit_loss=status.get('total_pnl', 0),
                    profit_loss_percent=status.get('total_pnl_percent', 0)
                )
                
                # Log status
                self.logger.info(f"Balance: ${status['balance']:.2f}, Equity: ${status['equity']:.2f}, "
                               f"Positions: {status['positions']}")
                
                # Wait for next update
                self.logger.info(f"Waiting {self.update_interval} seconds until next scan...")
                await asyncio.sleep(self.update_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}", exc_info=True)
                self.logger.info("Recovering from error in 10 seconds...")
                await asyncio.sleep(10)
    
    async def run_async(self):
        """
        Run bot asynchronously
        """
        self.running = True
        
        # Start Telegram bot in background if configured
        if self.telegram_bot:
            asyncio.create_task(self._run_telegram_bot())
        
        # Send startup notification
        if self.telegram_bot:
            await self.telegram_bot.send_notification(
                "🤖 *Trading Bot Started*\n\n"
                f"Mode: {self.trader.mode.upper()}\n"
                f"Symbols: {', '.join(self.symbols)}\n"
                f"Update Interval: {self.update_interval}s"
            )
        
        # Run trading loop
        await self.trading_loop()
    
    async def _run_telegram_bot(self):
        """Run Telegram bot in background"""
        try:
            await self.telegram_bot.app.initialize()
            await self.telegram_bot.app.start()
            await self.telegram_bot.app.updater.start_polling()
            
            # Keep running
            while self.running:
                await asyncio.sleep(1)
            
            await self.telegram_bot.app.updater.stop()
            await self.telegram_bot.app.stop()
            await self.telegram_bot.app.shutdown()
        except Exception as e:
            self.logger.error(f"Error running Telegram bot: {e}", exc_info=True)
    
    def run(self):
        """
        Run the trading bot
        """
        try:
            # Run backtest first if configured
            if self.config.get('bot', {}).get('run_backtest_on_start', True):
                self.run_backtest(symbol=self.symbols[0])
            
            # Start bot
            asyncio.run(self.run_async())
            
        except KeyboardInterrupt:
            self.logger.info("Shutting down trading bot...")
        except Exception as e:
            self.logger.critical(f"Fatal error: {e}", exc_info=True)
        finally:
            self.running = False
            self.logger.info("Trading bot stopped")


def main():
    """Main entry point"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║           🤖  CRYPTOCURRENCY TRADING BOT  🤖             ║
    ║                                                           ║
    ║     Automated 24/7 Trading with Technical Analysis       ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️  WARNING: .env file not found!")
        print("Please create a .env file based on .env.example")
        print("Configure your API keys and settings before running the bot.")
        sys.exit(1)
    
    # Initialize and run bot
    bot = TradingBot()
    bot.run()


if __name__ == "__main__":
    main()
