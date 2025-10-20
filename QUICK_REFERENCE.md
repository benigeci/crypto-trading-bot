# ⚡ QUICK REFERENCE - Trading Bot Commands

## 🚀 INSTALLATION

```powershell
# Install enhanced dependencies
pip install -r requirements_enhanced.txt

# Verify installation
python -c "import sklearn; import xgboost; print('✅ ML libraries installed')"
```

---

## 🧪 TESTING

```powershell
# Test original bot
python test_bot.py

# Test multi-API aggregator
python multi_api_aggregator.py

# Test advanced indicators
python advanced_indicators.py

# Test ML predictor (trains models)
python ml_predictor.py

# Test risk manager
python advanced_risk_manager.py
```

---

## 🤖 RUNNING THE BOT

```powershell
# Paper trading (safe)
python main.py

# Background mode (Windows)
Start-Process python -ArgumentList "main.py" -WindowStyle Hidden

# Stop bot
# Press Ctrl+C in terminal
```

---

## 📊 TELEGRAM COMMANDS

### Basic
```
/start          - Start bot
/help           - Show all commands
/status         - Balance, equity, positions
/performance    - Win rate, Sharpe, drawdown
/signals        - Last 5 trading signals
/trades         - Last 10 trades
/positions      - Current open positions
/balance        - Detailed balance info
```

### Enhanced
```
/risk           - Risk exposure analysis
/health         - System health check
/ml_stats       - ML model performance
/api_health     - Check all APIs
/pause          - Pause trading
/resume         - Resume trading
/emergency_stop - Close all & stop
/optimize       - Trigger optimization
/backtest       - Run backtest
```

---

## 📁 FILE LOCATIONS

```
bot/
├── main.py                      # Main bot
├── multi_api_aggregator.py      # Data fetching
├── advanced_indicators.py       # Indicators
├── ml_predictor.py              # ML models
├── advanced_risk_manager.py     # Risk mgmt
├── logs/bot.log                 # Logs
├── models/                      # ML models
│   ├── rf_classifier.joblib
│   ├── xgb_regressor.joblib
│   ├── scaler.joblib
│   └── feature_cols.joblib
├── trading_bot.db               # Database
└── .env                         # Config
```

---

## 🔍 MONITORING

```powershell
# View live logs
Get-Content logs/bot.log -Wait -Tail 50

# Search for errors
Select-String -Path logs/bot.log -Pattern "ERROR"

# Search for trades
Select-String -Path logs/bot.log -Pattern "Trade executed"

# Check database
sqlite3 trading_bot.db "SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;"
```

---

## 🛡️ RISK CHECKS

```python
# Check circuit breaker status
python -c "from advanced_risk_manager import AdvancedRiskManager; rm = AdvancedRiskManager(); print(rm.get_risk_report())"

# Check ML model accuracy
python -c "from ml_predictor import MLPricePredictor; ml = MLPricePredictor(); ml.load_models(); print(ml.model_metrics)"

# Check API health
python -c "from multi_api_aggregator import MultiAPIDataAggregator; agg = MultiAPIDataAggregator(); print(agg.get_api_health_report())"
```

---

## 🎯 ML MODEL TRAINING

```python
# Train on specific symbol
python -c "
from data_fetcher import DataFetcher
from analyzer import TechnicalAnalyzer
from ml_predictor import MLPricePredictor

fetcher = DataFetcher()
analyzer = TechnicalAnalyzer()
ml = MLPricePredictor()

df = fetcher.get_ohlcv('BTC/USDT', '1h', 1000)
df = analyzer.calculate_all_indicators(df)

acc = ml.train_random_forest(df)
mae = ml.train_xgboost(df)

print(f'RF Accuracy: {acc:.1%}')
print(f'XGB MAE: ${mae:.2f}')
"
```

---

## 📈 BACKTESTING

```python
# Run backtest
python -c "
from backtester import Backtester
from datetime import datetime, timedelta

bt = Backtester()
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

results = bt.run_backtest('BTC/USDT', start_date, end_date)
print(results)
"
```

---

## 🔧 CONFIGURATION

### .env Template
```env
# Trading
TRADING_MODE=paper              # paper or live
INITIAL_CAPITAL=10000
MAX_POSITION_SIZE=0.10          # 10%
STOP_LOSS_PERCENT=3
TAKE_PROFIT_PERCENT=5
UPDATE_INTERVAL=300             # seconds
SYMBOLS=BTC/USDT,ETH/USDT

# Risk
MAX_DAILY_LOSS=0.02             # 2%
MAX_WEEKLY_LOSS=0.05            # 5%
CIRCUIT_BREAKER_LOSS=0.05       # 5%

# APIs
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## 🚨 EMERGENCY PROCEDURES

### Circuit Breaker Activated
```python
# Check reason
python -c "from logger import get_logger; import re; log = open('logs/bot.log').read(); print([l for l in log.split('\n') if 'CIRCUIT BREAKER' in l][-5:])"

# Reset (requires manual confirmation)
# Send /reset_circuit_breaker in Telegram
# Or manually in code (NOT RECOMMENDED)
```

### System Crash
```powershell
# Check logs
tail -n 100 logs/bot.log

# Restart bot
python main.py

# Check positions
python -c "from trader import Trader; t = Trader(mode='live'); print(t.get_positions())"
```

### Manual Position Close
```python
# Close all positions
python -c "
from trader import Trader
trader = Trader(mode='live')
positions = trader.get_positions()
for pos in positions:
    trader.close_position(pos['symbol'])
"
```

---

## 📊 PERFORMANCE ANALYSIS

```python
# Get statistics
python -c "
from database import TradingDatabase
db = TradingDatabase()

trades = db.get_all_trades()
print(f'Total Trades: {len(trades)}')

wins = [t for t in trades if t['profit_loss'] > 0]
print(f'Win Rate: {len(wins)/len(trades)*100:.1f}%')

total_profit = sum(t['profit_loss'] for t in trades)
print(f'Total P&L: ${total_profit:.2f}')
"
```

---

## 🔐 SECURITY

```powershell
# Encrypt .env
cipher /e .env

# Set permissions
icacls .env /inheritance:r /grant:r "%USERNAME%:F"

# Check API key security
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key Length:', len(os.getenv('BINANCE_API_KEY', '')))"
```

---

## 🎯 OPTIMIZATION

```python
# Get ML feature importance
python -c "
from ml_predictor import MLPricePredictor
ml = MLPricePredictor()
ml.load_models()
importance = ml.get_feature_importance()
print(importance.head(10))
"

# Get trade statistics for Kelly
python -c "
from advanced_risk_manager import AdvancedRiskManager
rm = AdvancedRiskManager()
stats = rm.get_trade_statistics()
print(stats)
"
```

---

## 📱 ALERTS SETUP

Add to your Telegram bot:
```python
# Daily report (add to main.py)
async def send_daily_report():
    report = f'''
📊 Daily Trading Report
━━━━━━━━━━━━━━━━━━━━
Balance: ${balance:.2f}
P&L: ${pnl:.2f} ({pnl_pct:.1f}%)
Trades: {num_trades}
Win Rate: {win_rate:.1f}%
'''
    await telegram_bot.send_message(report)
```

---

## 🎓 USEFUL QUERIES

```sql
-- Top 10 profitable trades
SELECT symbol, profit_loss, timestamp 
FROM trades 
WHERE profit_loss > 0 
ORDER BY profit_loss DESC 
LIMIT 10;

-- Worst 10 trades
SELECT symbol, profit_loss, timestamp 
FROM trades 
WHERE profit_loss < 0 
ORDER BY profit_loss ASC 
LIMIT 10;

-- Win rate by symbol
SELECT 
    symbol,
    COUNT(*) as total_trades,
    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(100.0 * SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) as win_rate,
    ROUND(SUM(profit_loss), 2) as total_pnl
FROM trades 
GROUP BY symbol;
```

---

## 🚀 DEPLOYMENT CHECKLIST

```
☐ Install dependencies
☐ Train ML models
☐ Test all modules
☐ Run paper trading 7 days
☐ Verify profitability
☐ Secure API keys
☐ Enable 2FA
☐ Set IP whitelist
☐ Configure Telegram
☐ Set risk limits
☐ Start with $100
☐ Monitor 24/7
```

---

## 📞 QUICK HELP

| Issue | Command |
|-------|---------|
| Bot crashed | `python main.py` |
| Check errors | `Select-String -Path logs/bot.log -Pattern "ERROR"` |
| Test APIs | `python multi_api_aggregator.py` |
| Retrain ML | `python ml_predictor.py` |
| Check positions | Telegram: `/positions` |
| Stop trading | Telegram: `/pause` |
| Emergency stop | Telegram: `/emergency_stop` |
| View performance | Telegram: `/performance` |
| System health | Telegram: `/health` |

---

## 🎯 PERFORMANCE TARGETS

```
Week 1:    Break-even (learn)
Week 2-4:  +5-10% (optimize)
Month 2:   +10-20% (scale)
Month 3+:  +15-30% (compound)
```

---

## ⚠️ CRITICAL REMINDERS

```
❌ NEVER disable risk controls
❌ NEVER trade without stop loss
❌ NEVER ignore circuit breakers
❌ NEVER leave unmonitored >24h

✅ ALWAYS start with paper trading
✅ ALWAYS monitor closely
✅ ALWAYS respect limits
✅ ALWAYS keep backups
```

---

**Quick Start:**
```powershell
pip install -r requirements_enhanced.txt
python ml_predictor.py
python main.py
```

**Good luck! 🚀💰**

---

*Last Updated: 2025-01-20*
*Version: 2.0 Enhanced*
