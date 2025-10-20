# 🚀 Deployment and Operation Guide

## Step-by-Step Setup

### 1. Initial Setup

#### Install Python
```powershell
# Check Python version (must be 3.8+)
python --version

# If not installed, download from: https://www.python.org/downloads/
```

#### Create Virtual Environment
```powershell
cd "c:\Users\danyka\Desktop\bot"
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### Install Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configuration

#### Create .env File
```powershell
Copy-Item .env.example .env
notepad .env
```

**Minimum Configuration (Paper Trading):**
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=123456789

# Trading Mode
TRADING_MODE=paper
INITIAL_BALANCE=10000

# Bot Settings
UPDATE_INTERVAL=300
LOG_LEVEL=INFO
```

#### Configure Trading Symbols
Edit `config.yaml`:
```yaml
symbols:
  - BTC/USDT
  - ETH/USDT
  - BNB/USDT
  # Add more symbols as needed
```

### 3. Testing

#### Run Component Tests
```powershell
python test_bot.py
```

This will validate:
- ✅ Logger system
- ✅ Database operations
- ✅ Data fetching
- ✅ Technical analysis
- ✅ Trading execution (paper mode)
- ✅ Backtesting

#### Run Backtest
```powershell
python -c "from main import TradingBot; bot = TradingBot(); bot.run_backtest()"
```

### 4. Running the Bot

#### Start Bot
```powershell
python main.py
```

#### Background Execution (Windows)
Create `start_bot.bat`:
```batch
@echo off
cd /d "c:\Users\danyka\Desktop\bot"
call venv\Scripts\activate.bat
python main.py
pause
```

Double-click `start_bot.bat` to start the bot.

#### Keep Bot Running
For 24/7 operation, consider:
1. **Windows Task Scheduler**: Schedule `start_bot.bat` to run at startup
2. **Screen/tmux**: Use terminal multiplexer (if available)
3. **PM2**: Process manager for Node.js (can run Python scripts)

### 5. Monitoring

#### Check Logs
```powershell
# View main log
Get-Content logs\bot.log -Tail 50 -Wait

# View trade log
Get-Content logs\trades.log -Tail 20

# View error log
Get-Content logs\errors.log -Tail 20
```

#### Telegram Commands
- `/status` - Check bot status
- `/signals` - View current signals
- `/positions` - Check open positions
- `/performance` - View performance metrics

### 6. Live Trading Setup (Optional)

⚠️ **USE WITH CAUTION - REAL MONEY AT RISK**

#### Get Binance API Keys
1. Login to [Binance](https://www.binance.com/)
2. Go to Account → API Management
3. Create new API key
4. **Important**: Set permissions to **Read + Spot & Margin Trading** only (NO withdrawals)
5. Save API Key and Secret Key

#### Configure Live Trading
Edit `.env`:
```env
TRADING_MODE=live
BINANCE_API_KEY=your_actual_api_key_here
BINANCE_API_SECRET=your_actual_secret_key_here
```

#### Start with Small Amount
- Test with minimum trade amounts first
- Monitor closely for first few days
- Gradually increase position sizes

## 📊 Performance Optimization

### 1. Symbol Selection
Choose highly liquid pairs:
- ✅ BTC/USDT, ETH/USDT (High volume)
- ✅ Major altcoins (BNB, SOL, ADA)
- ❌ Low volume pairs (high slippage)

### 2. Timeframe Optimization
- **1m, 5m**: High frequency, more signals, higher noise
- **15m, 1h**: Balanced, recommended for most strategies
- **4h, 1d**: Lower frequency, stronger signals, fewer trades

### 3. Indicator Tuning
Edit `config.yaml`:
```yaml
indicators:
  rsi:
    period: 14          # Lower = more sensitive
    overbought: 70      # Lower = earlier sell signals
    oversold: 30        # Higher = earlier buy signals
```

### 4. Risk Management
```yaml
risk:
  position_size_percent: 10    # Lower = safer, higher = aggressive
  stop_loss:
    percent: 3                  # Tighter = protect capital, looser = avoid stop-outs
  take_profit:
    levels:
      - percent: 5              # First target
      - percent: 10             # Second target
```

## 🔧 Troubleshooting

### Issue: Bot crashes frequently
**Solutions:**
1. Check logs for errors: `logs\errors.log`
2. Verify API keys are correct
3. Check internet connection
4. Update dependencies: `pip install -r requirements.txt --upgrade`

### Issue: No signals generated
**Solutions:**
1. Check if data is being fetched: `/price BTC/USDT` in Telegram
2. Lower signal strength threshold in config
3. Try different symbols
4. Check indicator configuration

### Issue: Telegram bot not responding
**Solutions:**
1. Verify bot token in `.env`
2. Check chat ID is correct
3. Send `/start` command to bot
4. Restart bot: `Ctrl+C` then `python main.py`

### Issue: API rate limit errors
**Solutions:**
1. Increase update interval: `UPDATE_INTERVAL=600` (10 minutes)
2. Reduce number of symbols
3. Use backup data source (CoinGecko)

### Issue: Database errors
**Solutions:**
1. Delete database: `Remove-Item data\trading_bot.db`
2. Restart bot (will create new database)
3. Check disk space

## 📈 Monitoring and Maintenance

### Daily Tasks
- [ ] Check bot status via Telegram: `/status`
- [ ] Review recent trades: `/trades`
- [ ] Monitor performance: `/performance`
- [ ] Check for errors in logs

### Weekly Tasks
- [ ] Review backtest results
- [ ] Analyze win rate and performance
- [ ] Adjust risk parameters if needed
- [ ] Update cryptocurrency symbols

### Monthly Tasks
- [ ] Full performance analysis
- [ ] Strategy optimization
- [ ] Update dependencies: `pip install -r requirements.txt --upgrade`
- [ ] Backup database: `Copy-Item data\trading_bot.db data\backup_YYYYMMDD.db`

## 🔐 Security Best Practices

### API Key Security
- ✅ Never share API keys
- ✅ Use read + trade permissions only (NO withdrawals)
- ✅ Enable IP whitelist on Binance
- ✅ Use 2FA on exchange account
- ✅ Keep `.env` file secure

### System Security
- ✅ Use strong Windows password
- ✅ Keep Windows updated
- ✅ Use antivirus software
- ✅ Backup database regularly
- ✅ Monitor bot activity

## 📊 Performance Tracking

### Key Metrics to Monitor
1. **Win Rate**: Target > 55%
2. **Total Return**: Positive and growing
3. **Max Drawdown**: Keep < 20%
4. **Sharpe Ratio**: Target > 1.0
5. **Profit Factor**: Target > 1.5

### Performance Analysis
```powershell
# Generate performance report
python -c "
from database import TradingDatabase
db = TradingDatabase()
summary = db.get_performance_summary()
print(summary)
"
```

## 🚀 Advanced Deployment

### Windows Task Scheduler
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: At startup
4. Action: Start a program
5. Program: `c:\Users\danyka\Desktop\bot\venv\Scripts\python.exe`
6. Arguments: `c:\Users\danyka\Desktop\bot\main.py`
7. Start in: `c:\Users\danyka\Desktop\bot`

### Cloud Deployment (Optional)
For 24/7 uptime without local PC:
- **AWS EC2**: Free tier available
- **Google Cloud**: $300 free credits
- **DigitalOcean**: $5/month droplet
- **Heroku**: Free tier (limited hours)

## 📞 Support Checklist

Before seeking help:
- [ ] Check README.md for guidance
- [ ] Review logs: `logs\errors.log`
- [ ] Verify configuration: `.env` and `config.yaml`
- [ ] Test components: `python test_bot.py`
- [ ] Check API credentials
- [ ] Verify internet connection

## 🎯 Success Checklist

- [ ] Python 3.8+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed successfully
- [ ] `.env` file configured
- [ ] `config.yaml` customized
- [ ] Telegram bot configured and responding
- [ ] Component tests passed
- [ ] Backtest completed successfully
- [ ] Bot running in paper trading mode
- [ ] Monitoring via Telegram working
- [ ] Logs being generated correctly
- [ ] Performance being tracked

## 📝 Notes

- **Start with paper trading** - Test for at least 1 week
- **Monitor closely** - Check bot multiple times daily initially
- **Adjust gradually** - Make small configuration changes
- **Keep records** - Document what works and what doesn't
- **Be patient** - Trading success takes time

---

**Good luck with your trading bot! 🚀📈**
