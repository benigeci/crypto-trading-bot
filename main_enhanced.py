"""
Enhanced Trading Bot Main Entry Point
Integrates all enhanced modules for production-ready trading
"""

import asyncio
import argparse
import signal
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from logger import setup_logger
from config_models import BotConfig
from security_manager import SecurityManager
from async_data_fetcher import AsyncDataFetcher
from adaptive_strategy import AdaptiveStrategyEngine
from enhanced_risk_manager import EnhancedRiskManager
from enhanced_ml_predictor import EnhancedMLPredictor

try:
    from telegram_bot import TradingBot as TelegramBot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

logger = setup_logger('main_enhanced')


class EnhancedTradingBot:
    """
    Production-ready trading bot with all enhancements
    """
    
    def __init__(self, config_path: str = 'config.yaml', master_password: str = None):
        """
        Initialize enhanced trading bot
        
        Args:
            config_path: Path to configuration file
            master_password: Master password for credential decryption
        """
        self.running = False
        self.master_password = master_password
        
        # Load configuration
        logger.info("Loading configuration...")
        self.config = BotConfig.from_yaml(config_path)
        
        # Validate for live trading if needed
        if self.config.trading.mode == 'live':
            logger.warning("⚠️ Live trading mode enabled!")
            self.config.validate_for_live_trading()
        
        # Initialize security manager
        logger.info("Initializing security manager...")
        self.security_mgr = SecurityManager(master_password=master_password)
        self.security_mgr.load_encrypted_credentials()
        
        # Get credentials
        api_key = self.security_mgr.get_credential('EXCHANGE_API_KEY')
        api_secret = self.security_mgr.get_credential('EXCHANGE_API_SECRET')
        
        if not api_key or not api_secret:
            logger.warning("No encrypted credentials found, loading from environment...")
            api_key = self.config.exchange.api_key.get_secret_value()
            api_secret = self.config.exchange.api_secret.get_secret_value()
        
        # Initialize async data fetcher
        logger.info("Initializing async data fetcher...")
        self.data_fetcher = AsyncDataFetcher(
            exchange_id=self.config.exchange.name,
            credentials={
                'apiKey': api_key,
                'secret': api_secret
            },
            testnet=self.config.exchange.testnet
        )
        
        # Initialize adaptive strategy
        logger.info("Initializing adaptive strategy engine...")
        self.strategy = AdaptiveStrategyEngine(
            base_weights={
                'rsi': self.config.indicators.rsi_weight,
                'macd': self.config.indicators.macd_weight,
                'bollinger': self.config.indicators.bb_weight,
                'ema_trend': self.config.indicators.ema_weight,
                'volume': self.config.indicators.volume_weight,
                'ml_prediction': self.config.ml.ensemble_weights.get('ml_model', 2.0)
            }
        )
        
        # Initialize risk manager
        logger.info("Initializing enhanced risk manager...")
        self.risk_mgr = EnhancedRiskManager(
            initial_capital=self.config.trading.initial_balance,
            max_position_size_pct=self.config.trading.position_size_pct,
            max_daily_loss_pct=self.config.risk_management.max_daily_loss_pct,
            use_kelly_criterion=(self.config.risk_management.position_sizing_method == 'kelly'),
            kelly_fraction=self.config.risk_management.kelly_fraction,
            enable_trailing_stop=self.config.risk_management.trailing_stop,
            trailing_stop_pct=self.config.risk_management.trailing_stop_pct
        )
        
        # Initialize ML predictor
        if self.config.ml.enabled:
            logger.info("Initializing ML predictor...")
            self.ml_predictor = EnhancedMLPredictor(
                model_dir='./models',
                retrain_interval_hours=self.config.ml.retrain_interval_hours,
                min_training_samples=self.config.ml.min_training_samples,
                ensemble_weights=self.config.ml.ensemble_weights
            )
        else:
            self.ml_predictor = None
            logger.info("ML predictor disabled")
        
        # Initialize Telegram bot
        if TELEGRAM_AVAILABLE and self.config.telegram.enabled:
            logger.info("Initializing Telegram bot...")
            telegram_token = self.security_mgr.get_credential('TELEGRAM_BOT_TOKEN')
            if not telegram_token:
                telegram_token = self.config.telegram.bot_token.get_secret_value()
            
            self.telegram_bot = TelegramBot(
                token=telegram_token,
                chat_id=self.config.telegram.chat_id
            )
        else:
            self.telegram_bot = None
        
        # Trading state
        self.positions = {}
        self.last_update = {}
        
    async def initialize(self):
        """Initialize async components"""
        logger.info("Initializing async components...")
        await self.data_fetcher.initialize()
        logger.info("✅ Initialization complete")
    
    async def update_market_data(self, symbol: str) -> pd.DataFrame:
        """
        Fetch and update market data for a symbol
        
        Args:
            symbol: Trading pair
            
        Returns:
            DataFrame with OHLCV and indicators
        """
        try:
            # Fetch OHLCV data
            df = await self.data_fetcher.fetch_ohlcv_async(
                symbol=symbol,
                timeframe=self.config.trading.timeframe,
                limit=500,
                use_cache=True
            )
            
            if df is None or df.empty:
                logger.warning(f"No data received for {symbol}")
                return None
            
            # Calculate indicators (assuming you have an indicator module)
            # df = self.calculate_indicators(df)
            
            return df
            
        except Exception as e:
            logger.exception(f"Error updating market data for {symbol}: {e}")
            return None
    
    async def analyze_and_trade(self, symbol: str):
        """
        Analyze market and execute trades for a symbol
        
        Args:
            symbol: Trading pair
        """
        try:
            # Update market data
            df = await self.update_market_data(symbol)
            if df is None:
                return
            
            # Get ML prediction
            ml_prediction = None
            if self.ml_predictor is not None:
                ml_result = self.ml_predictor.predict(df)
                ml_prediction = {
                    'signal': ml_result.signal,
                    'confidence': ml_result.confidence
                }
            else:
                ml_prediction = {'signal': 0.0, 'confidence': 0.5}
            
            # Generate adaptive signal
            signal = await self.strategy.generate_ensemble_signal(df, ml_prediction)
            
            logger.info(
                f"\n{'='*60}\n"
                f"📊 {symbol} Analysis\n"
                f"{'='*60}\n"
                f"Action: {signal.action}\n"
                f"Strength: {signal.strength:.1f}/100\n"
                f"Confidence: {signal.confidence:.2f}\n"
                f"Regime: {signal.regime.volatility}, {signal.regime.trend}, "
                f"{signal.regime.volume}\n"
                f"Components:\n"
            )
            for component, value in signal.components.items():
                logger.info(f"  {component}: {value:.3f}")
            logger.info(f"\nReasoning:")
            for reason in signal.reasoning:
                logger.info(f"  • {reason}")
            logger.info(f"{'='*60}\n")
            
            # Check if we can trade
            can_trade, reason = self.risk_mgr.can_open_position(symbol)
            if not can_trade:
                logger.info(f"Cannot trade {symbol}: {reason}")
                return
            
            current_price = df['close'].iloc[-1]
            
            # Execute trading logic
            if signal.action == 'BUY' and symbol not in self.positions:
                await self.execute_buy(symbol, df, signal, current_price)
            
            elif signal.action == 'SELL' and symbol in self.positions:
                await self.execute_sell(symbol, current_price, reason="Signal")
            
            # Update existing positions (trailing stop, TP levels)
            if symbol in self.positions:
                await self.update_position(symbol, current_price)
            
        except Exception as e:
            logger.exception(f"Error analyzing {symbol}: {e}")
    
    async def execute_buy(
        self,
        symbol: str,
        df: pd.DataFrame,
        signal,
        current_price: float
    ):
        """Execute buy order"""
        try:
            # Calculate position size
            position_size = self.risk_mgr.calculate_dynamic_position_size(
                symbol=symbol,
                df=df,
                signal_strength=signal.strength,
                signal_confidence=signal.confidence
            )
            
            # Calculate stop-loss and take-profit
            stop_loss = self.risk_mgr.calculate_stop_loss(current_price, df, 'long')
            take_profits = self.risk_mgr.calculate_take_profit_levels(
                current_price,
                stop_loss,
                'long',
                levels=3
            )
            
            logger.info(
                f"\n🟢 BUY ORDER: {symbol}\n"
                f"  Size: {position_size:.8f}\n"
                f"  Entry: ${current_price:.2f}\n"
                f"  Stop Loss: ${stop_loss:.2f} ({((stop_loss/current_price-1)*100):.2f}%)\n"
                f"  Take Profits:\n"
                f"    TP1: ${take_profits[0]:.2f} ({((take_profits[0]/current_price-1)*100):.2f}%)\n"
                f"    TP2: ${take_profits[1]:.2f} ({((take_profits[1]/current_price-1)*100):.2f}%)\n"
                f"    TP3: ${take_profits[2]:.2f} ({((take_profits[2]/current_price-1)*100):.2f}%)\n"
            )
            
            # Paper trading or live execution
            if self.config.trading.mode == 'paper':
                logger.info("📝 Paper trading: Order recorded but not executed")
                
                # Create position object
                from enhanced_risk_manager import Position
                position = Position(
                    symbol=symbol,
                    side='long',
                    entry_price=current_price,
                    size=position_size,
                    stop_loss=stop_loss,
                    take_profit=take_profits,
                    entry_time=datetime.now()
                )
                
                self.positions[symbol] = position
                self.risk_mgr.positions[symbol] = position
                
                # Send Telegram notification
                if self.telegram_bot:
                    message = (
                        f"🟢 *BUY Signal*: {symbol}\n"
                        f"Strength: {signal.strength:.0f}/100\n"
                        f"Confidence: {signal.confidence:.2f}\n"
                        f"Entry: ${current_price:.2f}\n"
                        f"Stop Loss: ${stop_loss:.2f}\n"
                        f"TP: ${take_profits[0]:.2f} / ${take_profits[1]:.2f} / ${take_profits[2]:.2f}\n"
                        f"Regime: {signal.regime.volatility}, {signal.regime.trend}"
                    )
                    await self.telegram_bot.send_message(message)
            
            else:
                # Live trading execution
                logger.warning("🔴 Live trading execution not yet implemented!")
                # Here you would place actual orders via CCXT
                
        except Exception as e:
            logger.exception(f"Error executing buy for {symbol}: {e}")
    
    async def execute_sell(self, symbol: str, current_price: float, reason: str):
        """Execute sell order"""
        try:
            position = self.positions.get(symbol)
            if not position:
                return
            
            # Calculate P&L
            position.update_pnl(current_price)
            pnl_pct = position.get_pnl_pct()
            
            logger.info(
                f"\n🔴 SELL ORDER: {symbol}\n"
                f"  Entry: ${position.entry_price:.2f}\n"
                f"  Exit: ${current_price:.2f}\n"
                f"  P&L: ${position.unrealized_pnl:.2f} ({pnl_pct:.2f}%)\n"
                f"  Reason: {reason}\n"
            )
            
            # Paper trading
            if self.config.trading.mode == 'paper':
                logger.info("📝 Paper trading: Order recorded but not executed")
                
                # Update capital
                position.realized_pnl = position.unrealized_pnl
                self.risk_mgr.current_capital += position.realized_pnl
                self.risk_mgr.closed_positions.append(position)
                
                # Update peak capital
                if self.risk_mgr.current_capital > self.risk_mgr.peak_capital:
                    self.risk_mgr.peak_capital = self.risk_mgr.current_capital
                
                # Remove position
                del self.positions[symbol]
                del self.risk_mgr.positions[symbol]
                
                # Send Telegram notification
                if self.telegram_bot:
                    emoji = "🟢" if position.realized_pnl > 0 else "🔴"
                    message = (
                        f"{emoji} *Position Closed*: {symbol}\n"
                        f"Entry: ${position.entry_price:.2f}\n"
                        f"Exit: ${current_price:.2f}\n"
                        f"P&L: ${position.realized_pnl:.2f} ({pnl_pct:.2f}%)\n"
                        f"Reason: {reason}\n"
                        f"Capital: ${self.risk_mgr.current_capital:.2f}"
                    )
                    await self.telegram_bot.send_message(message)
            
        except Exception as e:
            logger.exception(f"Error executing sell for {symbol}: {e}")
    
    async def update_position(self, symbol: str, current_price: float):
        """Update existing position (trailing stop, TP levels)"""
        try:
            position = self.positions.get(symbol)
            if not position:
                return
            
            # Update P&L
            position.update_pnl(current_price)
            
            # Check stop-loss
            if position.side == 'long' and current_price <= position.stop_loss:
                logger.warning(f"⚠️ Stop-loss hit for {symbol}")
                await self.execute_sell(symbol, current_price, "Stop-loss")
                return
            
            # Check take-profit levels
            if position.side == 'long':
                for i, tp in enumerate(position.take_profit):
                    if current_price >= tp:
                        logger.info(f"✅ Take-profit {i+1} hit for {symbol}")
                        await self.execute_sell(symbol, current_price, f"Take-profit {i+1}")
                        return
            
            # Update trailing stop
            new_stop = self.risk_mgr.update_trailing_stop(symbol, current_price)
            if new_stop:
                logger.info(f"📈 Trailing stop updated for {symbol}: ${new_stop:.2f}")
            
        except Exception as e:
            logger.exception(f"Error updating position {symbol}: {e}")
    
    async def trading_loop(self):
        """Main trading loop"""
        logger.info("🚀 Starting trading loop...")
        
        while self.running:
            try:
                # Reset daily metrics
                self.risk_mgr.reset_daily_metrics()
                
                # Check circuit breaker
                if self.risk_mgr.check_circuit_breaker():
                    logger.warning("⚠️ Circuit breaker active, skipping trading cycle")
                    await asyncio.sleep(300)  # Wait 5 minutes
                    continue
                
                # Analyze each symbol
                for symbol in self.config.trading.symbols:
                    await self.analyze_and_trade(symbol)
                    await asyncio.sleep(1)  # Rate limiting
                
                # Log risk metrics
                metrics = self.risk_mgr.get_risk_metrics()
                logger.info(
                    f"\n📊 Risk Metrics:\n"
                    f"  Capital: ${self.risk_mgr.current_capital:.2f}\n"
                    f"  Daily P&L: {metrics.daily_pnl_pct:.2f}%\n"
                    f"  Drawdown: {metrics.current_drawdown:.2f}%\n"
                    f"  Risk Score: {metrics.risk_score:.1f}/100\n"
                    f"  Win Rate: {metrics.win_rate:.2%}\n"
                    f"  Profit Factor: {metrics.profit_factor:.2f}\n"
                )
                
                # Send daily summary via Telegram
                if self.telegram_bot and datetime.now().hour == 0:
                    await self.send_daily_summary(metrics)
                
                # Wait for next update
                await asyncio.sleep(self.config.trading.update_interval_seconds)
                
            except Exception as e:
                logger.exception(f"Error in trading loop: {e}")
                await asyncio.sleep(60)
    
    async def send_daily_summary(self, metrics):
        """Send daily summary to Telegram"""
        try:
            emoji = "🟢" if metrics.daily_pnl >= 0 else "🔴"
            message = (
                f"{emoji} *Daily Summary*\n"
                f"Date: {datetime.now().strftime('%Y-%m-%d')}\n"
                f"Capital: ${self.risk_mgr.current_capital:.2f}\n"
                f"P&L: ${metrics.daily_pnl:.2f} ({metrics.daily_pnl_pct:.2f}%)\n"
                f"Drawdown: {metrics.current_drawdown:.2f}%\n"
                f"Win Rate: {metrics.win_rate:.2%}\n"
                f"Profit Factor: {metrics.profit_factor:.2f}\n"
                f"Risk Score: {metrics.risk_score:.1f}/100\n"
                f"Open Positions: {len(self.positions)}\n"
                f"Total Trades: {len(self.risk_mgr.closed_positions)}"
            )
            await self.telegram_bot.send_message(message)
        except Exception as e:
            logger.exception(f"Error sending daily summary: {e}")
    
    async def start(self):
        """Start the trading bot"""
        try:
            logger.info("=" * 60)
            logger.info("🤖 Enhanced Trading Bot Starting...")
            logger.info("=" * 60)
            logger.info(f"Mode: {self.config.trading.mode.upper()}")
            logger.info(f"Exchange: {self.config.exchange.name}")
            logger.info(f"Symbols: {', '.join(self.config.trading.symbols)}")
            logger.info(f"Timeframe: {self.config.trading.timeframe}")
            logger.info(f"Initial Capital: ${self.config.trading.initial_balance:.2f}")
            logger.info("=" * 60)
            
            # Initialize async components
            await self.initialize()
            
            # Start trading loop
            self.running = True
            await self.trading_loop()
            
        except Exception as e:
            logger.exception(f"Error starting bot: {e}")
            await self.stop()
    
    async def stop(self):
        """Stop the trading bot"""
        logger.info("🛑 Stopping trading bot...")
        self.running = False
        
        # Close all positions if in live mode
        if self.config.trading.mode == 'live':
            logger.warning("Closing all open positions...")
            # Implement position closing logic
        
        # Close connections
        await self.data_fetcher.close()
        
        logger.info("✅ Trading bot stopped")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Enhanced Crypto Trading Bot')
    parser.add_argument('--config', default='config.yaml', help='Config file path')
    parser.add_argument('--mode', choices=['paper', 'live'], help='Trading mode (overrides config)')
    parser.add_argument('--password', help='Master password for credential decryption')
    args = parser.parse_args()
    
    # Create bot instance
    bot = EnhancedTradingBot(
        config_path=args.config,
        master_password=args.password
    )
    
    # Override mode if specified
    if args.mode:
        bot.config.trading.mode = args.mode
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("\n⚠️ Shutdown signal received")
        asyncio.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start bot
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Keyboard interrupt received")
        await bot.stop()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        await bot.stop()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
