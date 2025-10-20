# ⚡ Quick Start Guide - Get Running in 5 Minutes

## Prerequisites Check
- ✅ Windows PC
- ✅ Internet connection
- ✅ Telegram account

## 🚀 Fast Setup (5 Minutes)

### Step 1: Run Setup (1 minute)
Double-click: `setup.bat`

This will:
- Check Python installation
- Create virtual environment
- Install all dependencies
- Create configuration files

### Step 2: Configure Telegram Bot (2 minutes)

1. **Create Telegram Bot:**
   - Open Telegram
   - Search for `@BotFather`
   - Send: `/newbot`
   - Follow instructions
   - Copy your bot token (looks like: `123456:ABC-DEF1234...`)

2. **Get Your Chat ID:**
   - Send any message to your new bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find `"chat":{"id":123456789` - that's your chat ID

3. **Edit .env file:**
   - Open `.env` in Notepad
   - Replace `your_telegram_bot_token_here` with your bot token
   - Replace `your_telegram_chat_id_here` with your chat ID
   - Save and close

### Step 3: Test Installation (1 minute)
```powershell
python test_bot.py
```

You should see all tests pass ✓

### Step 4: Start Bot (1 minute)
Double-click: `start_bot.bat`

Or run:
```powershell
python main.py
```

### Step 5: Verify on Telegram
Open Telegram and send to your bot:
```
/start
/status
/signals
```

## 🎉 Done! Your Bot is Running!

The bot will:
- ✅ Monitor BTC/USDT, ETH/USDT, BNB/USDT
- ✅ Generate trading signals every 5 minutes
- ✅ Run in paper trading mode (no real money)
- ✅ Send notifications via Telegram
- ✅ Log all activity to `logs/` folder

## 📊 What Happens Next?

1. **Bot runs automatically** - Scans markets every 5 minutes
2. **Generates signals** - Uses 10+ technical indicators
3. **Notifies you** - Sends Telegram messages for important events
4. **Paper trades** - Simulates trades without real money
5. **Tracks performance** - Records everything in database

## 🎮 Telegram Commands

Essential commands to try:

```
/status - See balance and positions
/signals - View current trading signals
/analyze BTC/USDT - Deep analysis of Bitcoin
/price ETH/USDT - Get Ethereum price
/performance - View your trading stats
/trades - See recent trade history
```

## ⚙️ Configuration (Optional)

### Change Monitored Coins
Edit `config.yaml`:
```yaml
symbols:
  - BTC/USDT
  - ETH/USDT
  - BNB/USDT
  - SOL/USDT  # Add more here
```

### Adjust Update Frequency
Edit `.env`:
```env
UPDATE_INTERVAL=300  # Seconds (300 = 5 minutes)
```

### Risk Settings
Edit `config.yaml`:
```yaml
risk:
  position_size_percent: 10  # 10% per trade
  stop_loss:
    percent: 3  # 3% stop loss
```

## 📈 Monitor Performance

### Check Logs
```powershell
# Main log
Get-Content logs\bot.log -Tail 20

# Trade history
Get-Content logs\trades.log -Tail 10

# Signals
Get-Content logs\signals.log -Tail 10
```

### Performance Metrics
Send `/performance` in Telegram to see:
- Total trades
- Win rate
- Profit/loss
- Current balance

## 🔄 Stopping the Bot

Press `Ctrl+C` in the terminal window

## 🚨 Troubleshooting

### Bot won't start?
1. Check Python is installed: `python --version`
2. Run setup again: `setup.bat`
3. Check `.env` file has your Telegram token

### No Telegram notifications?
1. Verify bot token in `.env`
2. Verify chat ID in `.env`
3. Send `/start` to your bot
4. Restart bot: Close terminal, run `start_bot.bat`

### No signals generated?
- Wait 5-10 minutes (initial data fetching)
- Check logs: `logs\bot.log`
- Try: `/signals` command in Telegram

## 🎯 Next Steps

1. **Monitor for 24 hours** - Let bot run and observe
2. **Review performance** - Check win rate and signals
3. **Adjust settings** - Tune parameters in `config.yaml`
4. **Read full docs** - See `README.md` for details

## ⚠️ Important Reminders

- 🟢 Bot is in **PAPER TRADING** mode - No real money
- 🟢 Safe to test and experiment
- 🔴 For live trading, read `DEPLOYMENT.md` carefully
- 🔴 Never share your API keys

## 📚 Learn More

- `README.md` - Complete documentation
- `DEPLOYMENT.md` - Detailed setup guide
- `config.yaml` - All configuration options

## 💬 Quick Reference Card

| Command | Description |
|---------|-------------|
| `/start` | Welcome and help |
| `/status` | Bot status and balance |
| `/signals` | Latest trading signals |
| `/positions` | Open positions |
| `/trades` | Recent trades |
| `/performance` | Performance metrics |
| `/analyze BTC/USDT` | Analyze a coin |
| `/price BTC/USDT` | Get current price |

---

**Congratulations! Your automated crypto trading bot is running! 🎉📈**

For questions, check the full documentation in `README.md`
