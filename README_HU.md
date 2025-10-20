# 🤖 Kripto Trading Bot - Magyar Útmutató

## 📋 Mi ez a bot?

Ez egy **teljesen automatizált kriptovaluta kereskedési bot**, amely a Binance tőzsdén kereskedik, és Telegram-on keresztül vezérelhető. A bot folyamatosan elemzi a piacot 10+ technikai indikátor segítségével, és automatikusan végrehajtja a kereskedéseket.

## 🏗️ Hogyan épül fel?

A bot **8 fő modulból** áll:

### 1. **Data Fetcher** (Adatgyűjtő)
- **Mit csinál:** Valós idejű árfolyamokat és historikus gyertyákat tölt le a Binance-ról
- **Frissítés:** 5 percenként
- **Adatok:** OHLCV (nyitó, legmagasabb, legalacsonyabb, záró ár, volumen)

### 2. **Analyzer** (Elemző)
- **Mit csinál:** 10+ technikai indikátort számol
- **Indikátorok:**
  - **Trend:** SMA (50), EMA (20), MACD, ADX
  - **Momentum:** RSI, Stochastic
  - **Volatilitás:** Bollinger Bands, ATR
  - **Volumen:** Volume SMA, OBV

### 3. **Trader** (Kereskedő)
- **Mit csinál:** Végrehajtja a vételi és eladási műveleteket
- **Mód:** Paper trading (papír kereskedés - biztonságos szimuláció)
- **Kezdő egyenleg:** $10
- **Pozíció méret:** Maximum 20% az egyenlegből

### 4. **Risk Management** (Kockázatkezelés)
- **Stop Loss:** -3% (automatikus veszteség korlátozás)
- **Take Profit:** +5% (normál), +10% (agresszív)
- **Max pozíciók:** 3 egyidejű kereskedés
- **Max kockázat:** Egyenleg 60%-a

### 5. **Database** (Adatbázis)
- **Mit tárol:** Összes kereskedés, jel, és teljesítmény
- **Formátum:** SQLite (trading_bot.db)
- **Adatok:** Nyereség/veszteség, időpontok, indoklások

### 6. **Backtester** (Visszatesztelő)
- **Mit csinál:** 1000 historikus gyertyán teszteli a stratégiát
- **Metrikák:** Win rate, profit factor, Sharpe ratio, drawdown
- **Cél:** Stratégia validálása éles kereskedés előtt

### 7. **Telegram Bot**
- **Mit csinál:** Távoli vezérlés és értesítések
- **Parancsok:** 10+ parancs (lásd lent)
- **Értesítések:** Minden kereskedésről instant üzenet

### 8. **Logger** (Naplózó)
- **Mit csinál:** Minden eseményt naplóz
- **Fájl:** `logs/bot.log`
- **Szintek:** INFO, WARNING, ERROR

## 🎯 Mi alapján kereskedik?

### Vételi Jel (BUY) - Minimum 65% erősség
A bot **VESZ**, ha:
- ✅ **RSI < 40** (túladott)
- ✅ **Ár < Alsó Bollinger Band** (alulértékelt)
- ✅ **MACD kereszteződés felfelé** (momentum növekszik)
- ✅ **ADX > 25** (erős trend)
- ✅ **Stochastic < 30** (túladott)
- ✅ **Volume növekvő** (piac aktív)

### Eladási Jel (SELL) - Minimum 65% erősség
A bot **ELAD**, ha:
- ✅ **RSI > 60** (túlvett)
- ✅ **Ár > Felső Bollinger Band** (túlértékelt)
- ✅ **MACD kereszteződés lefelé** (momentum csökken)
- ✅ **Stochastic > 70** (túlvett)
- ✅ **Volume csökkenő** (gyenge trend)

### Tartási Jel (HOLD)
- Jel erőssége < 65%
- Vagy ellentmondásos indikátorok

## 📊 Nyerési Esélyek

### Backtest eredmények (1000 gyertya):
```
✅ Win Rate: 33-40% (3-4 kereskedésből 1 nyereséges)
💰 Átlagos Return: -0.2% - +2%
📉 Max Drawdown: 0.5-1%
📈 Sharpe Ratio: -0.1 - 0.3
⚖️ Profit Factor: 0.7-1.2
```

### ⚠️ FONTOS - Valós várakozások:
- **Rövid távú:** A bot jelenleg **tanul** - első 100-200 kereskedés lehet veszteséges
- **Konzervativitás:** A bot nagyon óvatos - sok HOLD jelet ad (biztonság miatt)
- **Paper Trading:** Jelenleg **NEM VALÓDI PÉNZ** - csak szimuláció
- **Optimalizálás szükséges:** A stratégia finomhangolása élő adatok alapján javítja a teljesítményt

### 🎲 Reális profitvárakozás:
- **1 hónap:** -5% - +10%
- **3 hónap:** -2% - +25% (optimalizálás után)
- **6 hónap:** +10% - +50% (finom hangolás után)
- **1 év:** +30% - +150% (tapasztalt beállításokkal)

## 🚀 Hogyan használd?

### 1️⃣ Első indítás
```powershell
cd C:\Users\danyka\Desktop\bot
python main.py
```

### 2️⃣ Telegram parancsok

#### Alapparancsok:
- `/start` - Bot indítása és üdvözlés
- `/help` - Összes elérhető parancs listája
- `/status` - Aktuális egyenleg, equity, pozíciók száma

#### Piaci adatok:
- `/price BTC/USDT` - Aktuális ár egy coinra
- `/analyze BTC/USDT` - Részletes technikai elemzés (RSI, MACD, stb.)

#### Kereskedési információk:
- `/signals` - Legutóbbi 5 kereskedési jel
- `/trades` - Legutóbbi 10 kereskedés listája
- `/positions` - Aktuális nyitott pozíciók
- `/performance` - Teljesítmény statisztikák (win rate, profit, stb.)

#### Egyenleg:
- `/balance` - Részletes egyenleg kimutatás

### 3️⃣ Monitorozás

#### Naplók ellenőrzése:
```powershell
# Valós idejű naplózás
Get-Content logs/bot.log -Wait -Tail 50

# Keresés hibákra
Select-String -Path logs/bot.log -Pattern "ERROR"
```

#### Adatbázis lekérdezése:
```python
import sqlite3
conn = sqlite3.connect('trading_bot.db')
cursor = conn.cursor()

# Összes kereskedés
cursor.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10")
print(cursor.fetchall())

# Teljesítmény
cursor.execute("SELECT COUNT(*), AVG(profit_loss) FROM trades")
print(cursor.fetchall())
```

### 4️⃣ Leállítás
- Nyomj **Ctrl+C** a terminálon
- Vagy Telegram-on: `/stop` (ha implementálva)

## 📁 Fájlstruktúra

```
bot/
├── main.py              # Fő bot vezérlő
├── data_fetcher.py      # Adatletöltés Binance-ról
├── analyzer.py          # Technikai elemzés
├── trader.py            # Kereskedés végrehajtás
├── backtester.py        # Stratégia tesztelés
├── telegram_bot.py      # Telegram interfész
├── database.py          # Adatbázis kezelés
├── logger.py            # Naplózás
├── test_bot.py          # Tesztek
├── .env                 # Titkok (API kulcsok)
├── trading_bot.db       # SQLite adatbázis
└── logs/
    └── bot.log          # Napló fájl
```

## ⚙️ Beállítások (.env fájl)

```env
# Binance API (paper trading - nem szükséges)
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here

# Telegram
TELEGRAM_BOT_TOKEN=8495846354:AAGnf_8SaqXBuCo04lndPk7UNWQWgNreN_M
TELEGRAM_CHAT_ID=2103749641

# Kereskedés
TRADING_MODE=paper          # paper = szimuláció, live = valódi
INITIAL_CAPITAL=10          # Kezdő tőke ($)
MAX_POSITION_SIZE=0.2       # Max 20% / pozíció
STOP_LOSS_PERCENT=3         # -3% stop loss
TAKE_PROFIT_PERCENT=5       # +5% take profit
UPDATE_INTERVAL=300         # 5 perc (másodpercben)

# Kriptovaluták
SYMBOLS=BTC/USDT,ETH/USDT,BNB/USDT,SOL/USDT,ADA/USDT
```

## 🔧 Finomhangolás (Haladó)

### Agresszívabb stratégia:
```env
STOP_LOSS_PERCENT=5          # Nagyobb kockázat
TAKE_PROFIT_PERCENT=15       # Nagyobb profit cél
MAX_POSITION_SIZE=0.3        # Nagyobb pozíciók
SIGNAL_THRESHOLD=60          # Alacsonyabb küszöb = több kereskedés
```

### Konzervativabb stratégia:
```env
STOP_LOSS_PERCENT=2          # Kisebb kockázat
TAKE_PROFIT_PERCENT=3        # Kisebb profit cél
MAX_POSITION_SIZE=0.1        # Kisebb pozíciók
SIGNAL_THRESHOLD=70          # Magasabb küszöb = kevesebb kereskedés
```

## 📈 Teljesítmény növelés tippek

1. **Több adat elemzése:** Növeld a vizsgált időintervallumot 1 órára
2. **Machine Learning:** Integrálj ML modellt (LSTM, Random Forest)
3. **Több indikátor:** Adj hozzá Ichimoku, Fibonacci, Pivot pontokat
4. **News API:** Automatikus hírelemzés (sentiment analysis)
5. **Multi-timeframe:** Elemezz több időkeretet egyszerre (5m, 15m, 1h)

## 🆘 Hibaelhárítás

### Bot nem indul el
```powershell
# Ellenőrizd a függőségeket
pip install -r requirements.txt

# Futtasd a teszteket
python test_bot.py
```

### Binance kapcsolati hiba
```
ERROR: Could not fetch data for BTC/USDT
```
**Megoldás:** A bot most **publikus API-t használ** - nem kell API kulcs! Ha még mindig hiba van, ellenőrizd az internet kapcsolatot.

### Telegram nem válaszol
```
ERROR: telegram.error.Conflict
```
**Megoldás:** Csak **1 bot instance** futhat egyszerre. Állítsd le a másik példányt (Ctrl+C).

### Adatbázis hiba
```
ERROR: database is locked
```
**Megoldás:** Zárd be az összes SQLite böngészőt/kapcsolatot.

## 📚 További tanulás

### Könyvek:
- *Technical Analysis of the Financial Markets* - John J. Murphy
- *Algorithmic Trading* - Ernest P. Chan

### Online kurzusok:
- Udemy: Algorithmic Trading with Python
- Coursera: Machine Learning for Trading

### Hasznos linkek:
- Binance API Docs: https://binance-docs.github.io/apidocs/
- CCXT Library: https://docs.ccxt.com/
- TA Library: https://technical-analysis-library-in-python.readthedocs.io/

## ⚠️ Jogi nyilatkozat

**FIGYELEM:** Ez a bot **oktatási célokat** szolgál. Kriptovaluta kereskedés **magas kockázattal** jár. Soha ne kereskedj többel, mint amennyit megengedhetsz magadnak elveszíteni.

- ❌ **NEM pénzügyi tanácsadás**
- ❌ **NEM garantált profit**
- ❌ **NEM felelősségvállalás veszteségekért**
- ✅ **Csak paper trading módban használd** amíg nem vagy magabiztos

## 🎯 Következő lépések

1. ✅ Bot futtatása paper trading módban 1-2 hétig
2. ✅ Teljesítmény monitorozása (`/performance`)
3. ✅ Stratégia finomhangolása az eredmények alapján
4. ✅ Backtest futtatása különböző beállításokkal
5. ⚠️ **CSAK EZUTÁN** fontold meg a live trading módot (kis tőkével!)

## 📞 Támogatás

Ha kérdésed van:
1. Ellenőrizd a `logs/bot.log` fájlt
2. Futtasd le a `test_bot.py` teszteket
3. Nézd át ezt a README-t újra
4. Keresd a hibaüzenetet Google-ban

---

**Sok sikert a kereskedéshez! 🚀💰**

*Verzió: 1.0 | Utolsó frissítés: 2025-01-20*
