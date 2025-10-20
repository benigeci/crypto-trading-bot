"""
Telegram Bot Interface - User interaction and notifications
"""
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, MessageHandler, filters
)
from telegram.constants import ParseMode
import asyncio
from typing import Dict
from logger import get_logger
from database import TradingDatabase
import io


class TelegramBot:
    """
    Telegram bot for trading bot control and notifications
    """
    
    def __init__(self, token: str, chat_id: str, trader, analyzer, data_fetcher, config: Dict = None):
        """
        Initialize Telegram bot
        
        Args:
            token: Telegram bot token
            chat_id: Authorized chat ID
            trader: Trader instance
            analyzer: Analyzer instance
            data_fetcher: DataFetcher instance
            config: Bot configuration
        """
        self.logger = get_logger()
        self.token = token
        self.chat_id = chat_id
        self.trader = trader
        self.analyzer = analyzer
        self.data_fetcher = data_fetcher
        self.config = config or {}
        self.db = TradingDatabase()
        
        # Initialize application
        self.app = Application.builder().token(token).build()
        
        # Register handlers
        self._register_handlers()
        
        self.logger.info("Telegram bot initialized")
    
    def _register_handlers(self):
        """Register command and callback handlers"""
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("signals", self.cmd_signals))
        self.app.add_handler(CommandHandler("positions", self.cmd_positions))
        self.app.add_handler(CommandHandler("trades", self.cmd_trades))
        self.app.add_handler(CommandHandler("performance", self.cmd_performance))
        self.app.add_handler(CommandHandler("chart", self.cmd_chart))
        self.app.add_handler(CommandHandler("analyze", self.cmd_analyze))
        self.app.add_handler(CommandHandler("price", self.cmd_price))
        self.app.add_handler(CommandHandler("trade", self.cmd_trade))  # ÚJ!
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command - Welcome message"""
        welcome_text = """
🤖 *Crypto Trading Bot*

Welcome! I'm your automated cryptocurrency trading assistant.

*Available Commands:*
/help - Show all commands
/status - Bot status and balance
/signals - Latest trading signals
/positions - Current positions
/trades - Recent trades
/performance - Performance metrics
/chart [symbol] - Price chart
/analyze [symbol] - Technical analysis
/price [symbol] - Current price

*🆕 NEW FEATURE:*
/trade [symbol] [amount] - Get instant BUY/SELL signal with SL/TP!
  Example: `/trade BTC/USDT 10`

The bot is running 24/7 and will notify you of important events.
        """
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command"""
        help_text = """
📚 *Command Reference*

*Status & Information:*
/status - View bot status, balance, and equity
/performance - See detailed performance metrics
/positions - List all open positions
/trades - View recent trade history

*Market Analysis:*
/signals - Get latest trading signals for all symbols
/analyze [symbol] - Detailed technical analysis for a symbol
/price [symbol] - Get current price for a symbol
/chart [symbol] - Generate price chart with indicators

*🆕 TRADING SIGNALS (NEW!):*
/trade [symbol] [amount] - Get BUY/SELL signal with Stop Loss & Take Profit
  Example: `/trade BTC/USDT 10` - Signal for BTC with $10
  Example: `/trade ETH/USDT 50` - Signal for ETH with $50

*Examples:*
`/analyze BTC/USDT` - Analyze Bitcoin
`/price ETH/USDT` - Get Ethereum price
`/trade SOL/USDT 20` - Get Solana trade signal with $20

The bot automatically monitors markets and executes trades based on signals.
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Status command - Show bot status"""
        try:
            status = self.trader.get_status()
            
            status_text = f"""
📊 *Bot Status*

*Mode:* {status['mode'].upper()}
*Balance:* ${status['balance']:.2f} USDT
*Equity:* ${status['equity']:.2f} USDT
*Open Positions:* {status['positions']}
"""
            
            if status['mode'] == 'paper':
                status_text += f"""
*Total P/L:* ${status.get('total_pnl', 0):.2f} ({status.get('total_pnl_percent', 0):.2f}%)
*Initial Balance:* ${self.trader.initial_balance:.2f}
"""
            
            # Add position details
            if status.get('position_details'):
                status_text += "\n*Position Details:*\n"
                for symbol, pos in status['position_details'].items():
                    current_price = self.data_fetcher.fetch_current_price(symbol)
                    pnl = (current_price - pos['entry_price']) * pos['amount'] if current_price else 0
                    pnl_percent = (pnl / (pos['entry_price'] * pos['amount'])) * 100 if current_price else 0
                    
                    status_text += f"\n{symbol}:\n"
                    status_text += f"  Amount: {pos['amount']:.8f}\n"
                    status_text += f"  Entry: ${pos['entry_price']:.2f}\n"
                    status_text += f"  Current: ${current_price:.2f}\n" if current_price else ""
                    status_text += f"  P/L: ${pnl:.2f} ({pnl_percent:+.2f}%)\n"
            
            await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            self.logger.error(f"Error in status command: {e}")
            await update.message.reply_text("❌ Error fetching status")
    
    async def cmd_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Signals command - Show latest signals"""
        try:
            symbols = self.config.get('symbols', ['BTC/USDT', 'ETH/USDT'])
            timeframe = self.config.get('data', {}).get('primary_timeframe', '15m')
            
            signals_text = "📡 *Latest Trading Signals*\n\n"
            
            for symbol in symbols:
                df = self.data_fetcher.fetch_ohlcv(symbol, timeframe, 200)
                
                if df is not None:
                    df = self.analyzer.calculate_all_indicators(df)
                    signal, strength, indicators = self.analyzer.generate_signal(df, symbol)
                    
                    # Signal emoji
                    emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
                    
                    signals_text += f"{emoji} *{symbol}*\n"
                    signals_text += f"Signal: {signal} (Strength: {strength}%)\n"
                    signals_text += f"Price: ${df.iloc[-1]['close']:.2f}\n"
                    signals_text += f"RSI: {indicators.get('rsi', 'N/A')}\n"
                    signals_text += f"Trend: {indicators.get('ema_trend', 'N/A')}\n\n"
            
            await update.message.reply_text(signals_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            self.logger.error(f"Error in signals command: {e}")
            await update.message.reply_text("❌ Error fetching signals")
    
    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Positions command - Show open positions"""
        try:
            portfolio = self.db.get_portfolio()
            
            if not portfolio:
                await update.message.reply_text("📭 No open positions")
                return
            
            positions_text = "💼 *Open Positions*\n\n"
            
            for pos in portfolio:
                symbol = pos['symbol']
                amount = pos['amount']
                entry_price = pos['avg_buy_price']
                current_price = pos.get('current_price', entry_price)
                pnl = pos.get('profit_loss', 0)
                pnl_percent = pos.get('profit_loss_percent', 0)
                
                emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
                
                positions_text += f"{emoji} *{symbol}*\n"
                positions_text += f"Amount: {amount:.8f}\n"
                positions_text += f"Entry: ${entry_price:.2f}\n"
                positions_text += f"Current: ${current_price:.2f}\n"
                positions_text += f"P/L: ${pnl:.2f} ({pnl_percent:+.2f}%)\n\n"
            
            await update.message.reply_text(positions_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            self.logger.error(f"Error in positions command: {e}")
            await update.message.reply_text("❌ Error fetching positions")
    
    async def cmd_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Trades command - Show recent trades"""
        try:
            trades = self.db.get_trades(limit=10)
            
            if not trades:
                await update.message.reply_text("📭 No recent trades")
                return
            
            trades_text = "📜 *Recent Trades*\n\n"
            
            for trade in trades[:5]:  # Show last 5
                action = trade['action']
                symbol = trade['symbol']
                price = trade['price']
                amount = trade['amount']
                timestamp = trade['timestamp'][:16]  # Date and time only
                pnl = trade.get('profit_loss', 0)
                
                emoji = "🟢" if action == "BUY" else "🔴"
                
                trades_text += f"{emoji} *{action}* {symbol}\n"
                trades_text += f"Price: ${price:.2f}\n"
                trades_text += f"Amount: {amount:.8f}\n"
                trades_text += f"Time: {timestamp}\n"
                
                if pnl != 0:
                    pnl_emoji = "💰" if pnl > 0 else "💸"
                    trades_text += f"{pnl_emoji} P/L: ${pnl:.2f}\n"
                
                trades_text += "\n"
            
            await update.message.reply_text(trades_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            self.logger.error(f"Error in trades command: {e}")
            await update.message.reply_text("❌ Error fetching trades")
    
    async def cmd_performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Performance command - Show performance metrics"""
        try:
            summary = self.db.get_performance_summary()
            
            performance_text = f"""
📈 *Performance Metrics*

*Total Trades:* {summary['total_trades']}
*Winning Trades:* {summary['winning_trades']} 🟢
*Losing Trades:* {summary['losing_trades']} 🔴
*Win Rate:* {summary['win_rate']:.2f}%

*Total P/L:* ${summary['total_profit_loss']:.2f}

*Current Balance:* ${summary['current_balance']:.2f}
*Current Equity:* ${summary['current_equity']:.2f}
"""
            
            await update.message.reply_text(performance_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            self.logger.error(f"Error in performance command: {e}")
            await update.message.reply_text("❌ Error fetching performance")
    
    async def cmd_chart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Chart command - Generate price chart"""
        try:
            # Get symbol from command
            if context.args:
                symbol = context.args[0]
            else:
                symbol = 'BTC/USDT'
            
            await update.message.reply_text(f"📊 Generating chart for {symbol}...")
            
            # This is a placeholder - actual chart generation would use matplotlib
            chart_text = f"Chart for {symbol} would be displayed here.\nUse matplotlib to generate actual charts."
            
            await update.message.reply_text(chart_text)
            
        except Exception as e:
            self.logger.error(f"Error in chart command: {e}")
            await update.message.reply_text("❌ Error generating chart")
    
    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Analyze command - Detailed technical analysis"""
        try:
            # Get symbol from command
            if context.args:
                symbol = context.args[0]
            else:
                await update.message.reply_text("Usage: /analyze [symbol]\nExample: /analyze BTC/USDT")
                return
            
            await update.message.reply_text(f"🔍 Analyzing {symbol}...")
            
            # Fetch data
            df = self.data_fetcher.fetch_ohlcv(symbol, '15m', 200)
            
            if df is None:
                await update.message.reply_text(f"❌ Could not fetch data for {symbol}")
                return
            
            # Analyze
            df = self.analyzer.calculate_all_indicators(df)
            signal, strength, indicators = self.analyzer.generate_signal(df, symbol)
            
            # Build analysis text
            current = df.iloc[-1]
            
            emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
            
            analysis_text = f"""
{emoji} *Technical Analysis - {symbol}*

*Signal:* {signal} (Strength: {strength}%)
*Price:* ${current['close']:.2f}

*Indicators:*
• RSI: {indicators.get('rsi', 'N/A')} - {indicators.get('rsi_signal', 'N/A')}
• MACD: {indicators.get('macd_cross', 'N/A')}
• EMA Trend: {indicators.get('ema_trend', 'N/A')}
• Bollinger: {indicators.get('bb_signal', 'N/A')}
• Volume: {indicators.get('volume_signal', 'N/A')}
• ADX: {indicators.get('adx', 'N/A')} - {indicators.get('adx_trend', 'N/A')}

*Price Levels:*
• Support: ${current.get('support', 0):.2f}
• Resistance: ${current.get('resistance', 0):.2f}
"""
            
            await update.message.reply_text(analysis_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            self.logger.error(f"Error in analyze command: {e}")
            await update.message.reply_text(f"Error analyzing {symbol}: {str(e)}")
    
    async def cmd_trade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Trade Signal Generator - Get BUY/SELL signals with Stop Loss and Take Profit
        Usage: /trade SYMBOL AMOUNT
        Example: /trade BTC/USDT 10
        """
        try:
            # Parse arguments
            if len(context.args) < 2:
                help_text = """
🎯 *Trade Signal Generator*

*Usage:* `/trade SYMBOL AMOUNT`

*Examples:*
• `/trade BTC/USDT 10` - Get signal for Bitcoin with $10
• `/trade ETH/USDT 50` - Get signal for Ethereum with $50
• `/trade SOL/USDT 20` - Get signal for Solana with $20

*I will provide:*
✅ Current market analysis
✅ BUY or SELL recommendation
✅ Entry price
✅ Stop Loss level
✅ Take Profit targets (3 levels)
✅ Risk/Reward ratio
✅ Position size
                """
                await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
                return
            
            symbol = context.args[0].upper()
            if '/' not in symbol:
                symbol = f"{symbol}/USDT"
            
            try:
                amount_usd = float(context.args[1])
            except ValueError:
                await update.message.reply_text("❌ Invalid amount! Use a number (e.g., 10, 50, 100)")
                return
            
            if amount_usd <= 0:
                await update.message.reply_text("❌ Amount must be greater than 0!")
                return
            
            await update.message.reply_text(f"🔍 Analyzing {symbol} with ${amount_usd:.2f}...")
            
            # Fetch data
            df = self.data_fetcher.fetch_ohlcv(symbol, '15m', 200)
            
            if df is None or df.empty:
                await update.message.reply_text(f"❌ Could not fetch data for {symbol}. Check symbol name!")
                return
            
            # Get current price
            current_price = self.data_fetcher.fetch_current_price(symbol)
            if not current_price:
                current_price = df.iloc[-1]['close']
            
            # Calculate indicators
            df = self.analyzer.calculate_all_indicators(df)
            signal, strength, indicators = self.analyzer.generate_signal(df, symbol)
            
            # Calculate position size
            coin_amount = amount_usd / current_price
            
            # Calculate ATR for dynamic stop loss
            atr = df.iloc[-1].get('atr', current_price * 0.02)  # Default 2% if no ATR
            
            # Calculate Stop Loss (2x ATR below entry)
            stop_loss_distance = atr * 2
            stop_loss_price = current_price - stop_loss_distance
            stop_loss_percent = (stop_loss_distance / current_price) * 100
            
            # Calculate Take Profit levels (2x, 3x, 5x risk)
            tp1_price = current_price + (stop_loss_distance * 2)
            tp2_price = current_price + (stop_loss_distance * 3)
            tp3_price = current_price + (stop_loss_distance * 5)
            
            tp1_percent = ((tp1_price - current_price) / current_price) * 100
            tp2_percent = ((tp2_price - current_price) / current_price) * 100
            tp3_percent = ((tp3_price - current_price) / current_price) * 100
            
            # Risk calculation
            risk_amount = amount_usd * (stop_loss_percent / 100)
            potential_profit_tp1 = amount_usd * (tp1_percent / 100)
            potential_profit_tp2 = amount_usd * (tp2_percent / 100)
            potential_profit_tp3 = amount_usd * (tp3_percent / 100)
            
            # Get recommendation emoji
            if signal == "BUY" and strength >= 60:
                emoji = "🟢 STRONG BUY"
                recommendation = "**Recommendation: ENTER LONG POSITION**"
            elif signal == "BUY" and strength >= 40:
                emoji = "🟡 MODERATE BUY"
                recommendation = "**Recommendation: CONSIDER ENTERING**"
            elif signal == "SELL" and strength >= 60:
                emoji = "🔴 STRONG SELL"
                recommendation = "**Recommendation: AVOID or SHORT**"
            elif signal == "SELL" and strength >= 40:
                emoji = "🟠 MODERATE SELL"
                recommendation = "**Recommendation: WAIT FOR BETTER ENTRY**"
            else:
                emoji = "⚪ NEUTRAL"
                recommendation = "**Recommendation: NO CLEAR SIGNAL - WAIT**"
            
            # Build comprehensive trading signal
            signal_text = f"""
{emoji}

📊 *TRADING SIGNAL FOR {symbol}*
━━━━━━━━━━━━━━━━━━━━━━

{recommendation}

💰 *ENTRY DETAILS:*
• Current Price: `${current_price:.2f}`
• Signal: **{signal}** ({strength}% strength)
• Investment: `${amount_usd:.2f}`
• Coin Amount: `{coin_amount:.8f} {symbol.split('/')[0]}`

🛑 *STOP LOSS:*
• Price: `${stop_loss_price:.2f}`
• Distance: `-{stop_loss_percent:.2f}%`
• Max Loss: `${risk_amount:.2f}`

🎯 *TAKE PROFIT TARGETS:*

**Target 1 (50% position):**
• Price: `${tp1_price:.2f}`
• Profit: `+{tp1_percent:.2f}%`
• Gain: `+${potential_profit_tp1:.2f}`

**Target 2 (30% position):**
• Price: `${tp2_price:.2f}`
• Profit: `+{tp2_percent:.2f}%`
• Gain: `+${potential_profit_tp2:.2f}`

**Target 3 (20% position):**
• Price: `${tp3_price:.2f}`
• Profit: `+{tp3_percent:.2f}%`
• Gain: `+${potential_profit_tp3:.2f}`

⚖️ *RISK/REWARD RATIO:*
• Risk: `${risk_amount:.2f}` ({stop_loss_percent:.2f}%)
• Reward (TP1): `${potential_profit_tp1:.2f}` ({tp1_percent:.2f}%)
• R/R Ratio: **1:{tp1_percent/stop_loss_percent:.2f}**

📊 *TECHNICAL INDICATORS:*
"""
            
            # Add key indicators
            rsi = df.iloc[-1].get('rsi', 0)
            if rsi > 70:
                signal_text += f"• RSI: {rsi:.1f} (🔴 Overbought)\n"
            elif rsi < 30:
                signal_text += f"• RSI: {rsi:.1f} (🟢 Oversold)\n"
            else:
                signal_text += f"• RSI: {rsi:.1f} (⚪ Neutral)\n"
            
            # MACD
            macd_cross = indicators.get('macd_cross', 'N/A')
            if macd_cross == 'BULLISH':
                signal_text += f"• MACD: 🟢 Bullish Crossover\n"
            elif macd_cross == 'BEARISH':
                signal_text += f"• MACD: 🔴 Bearish Crossover\n"
            else:
                signal_text += f"• MACD: ⚪ No Signal\n"
            
            # EMA Trend
            ema_trend = indicators.get('ema_trend', 'N/A')
            if ema_trend == 'BULLISH':
                signal_text += f"• EMA Trend: 🟢 Uptrend\n"
            elif ema_trend == 'BEARISH':
                signal_text += f"• EMA Trend: 🔴 Downtrend\n"
            else:
                signal_text += f"• EMA Trend: ⚪ Sideways\n"
            
            # Volume
            volume_signal = indicators.get('volume_signal', 'NEUTRAL')
            if 'HIGH' in volume_signal:
                signal_text += f"• Volume: 🟢 High ({volume_signal})\n"
            else:
                signal_text += f"• Volume: ⚪ {volume_signal}\n"
            
            signal_text += f"""
━━━━━━━━━━━━━━━━━━━━━━

⚠️ *IMPORTANT NOTES:*
1. This is NOT financial advice
2. Always use stop loss
3. Take profits gradually (50%→30%→20%)
4. Never invest more than you can afford to lose
5. Market conditions can change rapidly

💡 *Pro Tip:* Set stop loss immediately after entry!
            """
            
            await update.message.reply_text(signal_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            self.logger.error(f"Error in trade command: {e}")
            await update.message.reply_text(f"❌ Error generating signal: {str(e)}")
    
    async def cmd_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Price command - Get current price"""
        try:
            # Get symbol from command
            if context.args:
                symbol = context.args[0]
            else:
                symbol = 'BTC/USDT'
            
            price = self.data_fetcher.fetch_current_price(symbol)
            
            if price:
                ticker = self.data_fetcher.fetch_ticker_info(symbol)
                
                price_text = f"""
💵 *{symbol}*

*Price:* ${price:.2f}
*24h High:* ${ticker.get('high_24h', 0):.2f}
*24h Low:* ${ticker.get('low_24h', 0):.2f}
*24h Change:* {ticker.get('change_percent_24h', 0):.2f}%
*24h Volume:* ${ticker.get('volume_24h', 0):,.0f}
"""
                await update.message.reply_text(price_text, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(f"❌ Could not fetch price for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error in price command: {e}")
            await update.message.reply_text("❌ Error fetching price")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        # Handle different button actions here
        await query.edit_message_text(text=f"Button pressed: {query.data}")
    
    async def send_notification(self, message: str, parse_mode=ParseMode.MARKDOWN):
        """
        Send notification to user
        
        Args:
            message: Message text
            parse_mode: Message parse mode
        """
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
    
    async def notify_signal(self, symbol: str, signal: str, strength: int, price: float):
        """Notify about trading signal"""
        emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
        
        message = f"""
{emoji} *New {signal} Signal*

*Symbol:* {symbol}
*Strength:* {strength}%
*Price:* ${price:.2f}

The bot will evaluate this signal based on your settings.
"""
        await self.send_notification(message)
    
    async def notify_trade(self, action: str, symbol: str, price: float, amount: float):
        """Notify about trade execution"""
        emoji = "🟢" if action == "BUY" else "🔴"
        
        message = f"""
{emoji} *Trade Executed*

*Action:* {action}
*Symbol:* {symbol}
*Price:* ${price:.2f}
*Amount:* {amount:.8f}
*Total:* ${price * amount:.2f}
"""
        await self.send_notification(message)
    
    def run(self):
        """Run the bot"""
        self.logger.info("Starting Telegram bot...")
        self.app.run_polling()


if __name__ == "__main__":
    # Test bot (requires real token and setup)
    print("Telegram bot module ready. Configure token in main.py to run.")
