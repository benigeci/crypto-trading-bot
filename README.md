# 🤖 Cryptocurrency Trading Bot

A fully automated, production-ready cryptocurrency trading bot with advanced technical analysis, risk management, and 24/7 operation. Built with Python and designed for reliability and profitability.

## ✨ Features

### 🔍 Advanced Technical Analysis
- **Multiple Indicators**: RSI, MACD, EMA, Bollinger Bands, ADX, Stochastic, ATR, OBV
- **Signal Generation**: Multi-indicator confluence with configurable strength thresholds
- **Multi-Timeframe Analysis**: Analyze across multiple timeframes for better accuracy
- **Volume Analysis**: Volume confirmation and spike detection
- **Support/Resistance**: Automatic support and resistance level identification

### 💼 Trading Capabilities
- **Paper Trading**: Test strategies risk-free with simulated trading
- **Live Trading**: Automatic execution on Binance (or other supported exchanges)
- **Risk Management**: 
  - Configurable stop loss (fixed or trailing)
  - Multi-level take profit targets
  - Position sizing based on signal strength
  - Maximum position limits
- **Auto-Recovery**: Automatic error recovery and continuous operation

### 📊 Data & Analysis
- **Multiple Data Sources**: Primary (Binance) with backup (CoinGecko)
- **Real-time Data**: Live price feeds and order book data
- **Historical Data**: Comprehensive historical data for backtesting
- **Data Validation**: Automatic data quality checks
- **Rate Limiting**: Intelligent API rate limiting

### 🧪 Backtesting
- **Strategy Testing**: Test strategies on historical data
- **Performance Metrics**: Win rate, Sharpe ratio, max drawdown, profit factor
- **Equity Curve**: Visualize performance over time
- **Trade History**: Detailed analysis of all trades

### 💬 Telegram Integration
- **Real-time Notifications**: Signals, trades, and error alerts
- **Interactive Commands**: Query bot status, view signals, check performance
- **Remote Control**: Manage bot from anywhere via Telegram
- **Chart Generation**: Request price charts and technical analysis

### 📈 Database & Logging
- **SQLite Database**: Store trades, signals, portfolio, and performance
- **Comprehensive Logging**: Color-coded console and file logging
- **Performance Tracking**: Automatic performance metrics calculation
- **Trade History**: Complete audit trail of all operations

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Telegram account (for notifications)
- Binance account (optional, for live trading)

### Installation

1. **Clone or download this repository**
```powershell
cd "c:\Users\danyka\Desktop\bot"
```

2. **Create virtual environment**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. **Install dependencies**
```powershell
pip install -r requirements.txt
```

4. **Configure environment variables**
```powershell
# Copy the example environment file
Copy-Item .env.example .env

# Edit .env file with your settings
notepad .env
```

### Configuration

#### 1. Telegram Bot Setup

1. Create a new bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Copy the bot token
3. Get your chat ID:
   - Send a message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Copy your chat ID from the response

4. Add to `.env`:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

#### 2. Trading Configuration

**Paper Trading (Default - Safe for testing):**
```env
TRADING_MODE=paper
INITIAL_BALANCE=10000
```

**Live Trading (Use with caution):**
```env
TRADING_MODE=live
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
```

#### 3. Risk Management

Edit `config.yaml` to configure risk parameters:
```yaml
risk:
  max_positions: 3               # Maximum concurrent positions
  position_size_percent: 10      # Percentage of portfolio per trade
  stop_loss:
    enabled: true
    type: trailing               # fixed or trailing
    percent: 3                   # 3% stop loss
  take_profit:
    enabled: true
    levels:
      - percent: 5               # First target: 5%
        exit_percent: 50         # Exit 50% of position
      - percent: 10              # Second target: 10%
        exit_percent: 50         # Exit remaining 50%
```

### Running the Bot

#### First Run - Backtest
Before running live, test your strategy:
```powershell
python main.py
```
The bot will automatically run a backtest on historical data first.

#### Continuous Operation
For 24/7 operation:
```powershell
python main.py
```

The bot will:
1. Run initial backtest
2. Start monitoring configured symbols
3. Generate trading signals
4. Execute trades (if auto_trade enabled)
5. Send Telegram notifications
6. Continuously monitor and adjust positions

## 📱 Telegram Commands

Once the bot is running, use these commands in Telegram:

### Information Commands
- `/start` - Welcome message and introduction
- `/help` - Show all available commands
- `/status` - View bot status, balance, and positions
- `/performance` - Detailed performance metrics

### Trading Commands
- `/signals` - Get latest signals for all symbols
- `/analyze [symbol]` - Detailed technical analysis for a symbol
  - Example: `/analyze BTC/USDT`
- `/price [symbol]` - Get current price for a symbol
  - Example: `/price ETH/USDT`

### Portfolio Commands
- `/positions` - View all open positions
- `/trades` - View recent trade history
- `/chart [symbol]` - Generate price chart (upcoming feature)

## 🔧 Configuration Files

### `config.yaml` - Main Configuration
```yaml
symbols:                        # Cryptocurrencies to monitor
  - BTC/USDT
  - ETH/USDT
  - BNB/USDT

data:
  primary_timeframe: 15m        # Main analysis timeframe
  candles_limit: 500            # Historical candles to fetch

indicators:
  rsi:
    period: 14
    overbought: 70
    oversold: 30
  
  macd:
    fast_period: 12
    slow_period: 26
    signal_period: 9

strategy:
  signals:
    buy_conditions:
      min_indicators: 3         # Minimum indicators confirming buy
    sell_conditions:
      min_indicators: 3         # Minimum indicators confirming sell

bot:
  update_interval: 300          # Check every 5 minutes
  auto_trade: false             # Set to true for automatic trading
  paper_trading: true           # Paper trading mode
```

### `.env` - Environment Variables
```env
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Exchange API Keys (Optional - for live trading)
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here

# Trading Configuration
TRADING_MODE=paper              # paper or live
INITIAL_BALANCE=10000           # Starting balance for paper trading

# Bot Configuration
UPDATE_INTERVAL=300             # Update interval in seconds
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 📊 Project Structure

```
bot/
├── main.py                 # Main bot orchestrator
├── data_fetcher.py         # Fetch market data from exchanges
├── analyzer.py             # Technical analysis engine
├── trader.py               # Trade execution (paper & live)
├── backtester.py           # Backtesting framework
├── telegram_bot.py         # Telegram bot interface
├── database.py             # SQLite database manager
├── logger.py               # Logging system
├── config.yaml             # Main configuration
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── .env                    # Your environment variables (create this)
├── data/                   # Database files
│   └── trading_bot.db      # SQLite database
└── logs/                   # Log files
    ├── bot.log             # Main log
    ├── trades.log          # Trade log
    ├── signals.log         # Signal log
    └── errors.log          # Error log
```

## 🔬 Technical Indicators

The bot uses the following indicators for signal generation:

### Trend Indicators
- **EMA (Exponential Moving Average)**: 9, 21, 50, 200 periods
- **MACD (Moving Average Convergence Divergence)**: Trend momentum
- **ADX (Average Directional Index)**: Trend strength

### Momentum Indicators
- **RSI (Relative Strength Index)**: Overbought/oversold conditions
- **Stochastic Oscillator**: Price momentum

### Volatility Indicators
- **Bollinger Bands**: Price volatility and extremes
- **ATR (Average True Range)**: Volatility measurement

### Volume Indicators
- **Volume MA**: Average volume
- **OBV (On-Balance Volume)**: Volume flow
- **Volume Ratio**: Volume spikes

## 📈 Signal Generation Logic

The bot generates signals based on **indicator confluence**:

### Buy Signal (Minimum 60% strength required)
- ✅ RSI < 30 (Oversold)
- ✅ MACD Bullish Crossover
- ✅ Price Above EMA 9
- ✅ Price at Lower Bollinger Band
- ✅ High Volume Confirmation
- ✅ Strong Uptrend (ADX > 25)

### Sell Signal (Minimum 60% strength required)
- ✅ RSI > 70 (Overbought)
- ✅ MACD Bearish Crossover
- ✅ Price Below EMA 9
- ✅ Price at Upper Bollinger Band
- ✅ High Volume Confirmation
- ✅ Strong Downtrend (ADX > 25)

**Signal Strength**: 0-100% based on indicator confluence

## 🧪 Backtesting

Test your strategy before live trading:

```python
# The bot automatically runs backtest on startup
# Or run manually:
python -c "
from main import TradingBot
bot = TradingBot()
bot.run_backtest(symbol='BTC/USDT', timeframe='1h', candles=1000)
"
```

**Backtest Metrics:**
- Total trades and win rate
- Total return percentage
- Net profit/loss
- Maximum drawdown
- Sharpe ratio
- Profit factor
- Average hold time

## 🛡️ Risk Management

### Position Sizing
- Maximum 10% of portfolio per trade (configurable)
- Dynamic sizing based on signal strength (optional)
- Maximum concurrent positions limit

### Stop Loss
- **Fixed Stop Loss**: Set percentage below entry
- **Trailing Stop Loss**: Follows price up, protects profits

### Take Profit
- Multiple profit targets
- Partial position exits at each level
- Automatic profit locking

### Portfolio Protection
- Maximum portfolio risk limit
- Automatic position monitoring
- Emergency exit conditions

## 🔄 24/7 Operation

The bot is designed for continuous operation:

### Auto-Recovery
- Automatic error recovery
- Reconnection on network failures
- State persistence in database

### Monitoring
- Real-time logging
- Telegram notifications
- Performance tracking
- Error alerts

### Maintenance
- Automatic log rotation
- Database cleanup
- Performance optimization

## 📊 Database Schema

The bot maintains a comprehensive SQLite database:

### Tables
- **trades**: All executed trades with P/L
- **signals**: Historical trading signals
- **portfolio**: Current holdings and positions
- **balance**: Balance history and snapshots
- **performance**: Performance metrics over time
- **market_data**: Cached OHLCV data

## 🐛 Troubleshooting

### Common Issues

**Bot won't start:**
- Check `.env` file exists and is configured
- Verify Python version (3.8+)
- Install all dependencies: `pip install -r requirements.txt`

**No data fetched:**
- Check internet connection
- Verify API keys (for live trading)
- Check API rate limits

**Telegram bot not responding:**
- Verify bot token is correct
- Check chat ID is correct
- Ensure bot is started with `/start` command

**No signals generated:**
- Check if data is being fetched successfully
- Review indicator configuration in `config.yaml`
- Check minimum signal strength threshold

## ⚠️ Important Warnings

### For Live Trading:
1. **Start with Paper Trading**: Test thoroughly before using real money
2. **Use API Keys Safely**: Never share your API keys
3. **Set Permissions**: Limit API key permissions (no withdrawals)
4. **Monitor Regularly**: Check bot performance frequently
5. **Start Small**: Begin with small amounts
6. **Understand Risks**: Cryptocurrency trading is risky

### Security:
- Keep `.env` file secure and never commit it
- Use strong API key permissions (read + trade only)
- Enable 2FA on exchange accounts
- Regularly review trade history

## 📚 Advanced Usage

### Custom Indicators
Modify `analyzer.py` to add custom indicators:
```python
def _calculate_custom_indicator(self, df):
    # Add your custom indicator logic
    df['custom_indicator'] = ...
    return df
```

### Custom Strategies
Modify signal generation logic in `analyzer.py`:
```python
def generate_signal(self, df, symbol):
    # Implement your custom strategy
    # Return: signal_type, strength, indicators
```

### Multiple Timeframe Analysis
Enable in `config.yaml`:
```yaml
strategy:
  signals:
    multiple_timeframes: true
```

## 🤝 Contributing

This is a complete, production-ready trading bot. Feel free to:
- Customize indicators and strategies
- Add new data sources
- Enhance Telegram commands
- Improve risk management

## 📄 License

This project is provided as-is for educational purposes.

## ⚡ Performance Tips

1. **Optimize Update Interval**: Balance between responsiveness and API limits
2. **Select Good Symbols**: Choose liquid trading pairs
3. **Tune Indicators**: Adjust indicator parameters for better signals
4. **Monitor Logs**: Regularly check logs for issues
5. **Backtest Often**: Test strategy changes before deploying

## 🎯 Next Steps

1. ✅ Complete this setup guide
2. ✅ Configure `.env` file
3. ✅ Run initial backtest
4. ✅ Start in paper trading mode
5. ✅ Monitor performance for several days
6. ✅ Adjust configuration as needed
7. ⚠️ Consider live trading (optional, use caution)

## 📞 Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review configuration files
3. Verify API credentials
4. Check Telegram bot connection

---

**Made with ❤️ for automated cryptocurrency trading**

**Disclaimer**: Trading cryptocurrencies carries risk. This bot is for educational purposes. Use at your own risk.
