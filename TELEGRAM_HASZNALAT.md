# 📱 Telegram Bot Használat

## 🎯 2 Módszer van a Bot Futtatására:

### Módszer 1: Terminál (Telegram opcionális) ⚡
```cmd
python main_enhanced.py --mode paper
```
- ✅ Bot fut
- ✅ Kereskedik
- 📊 Terminálban látod a logokat
- 🔔 **Ha Telegram be van kapcsolva** → értesítéseket küld

### Módszer 2: Csak Telegram Vezérlés 📱
```cmd
python start_telegram_bot.py
```
- ✅ Bot Telegram-on keresztül vezérelhető
- 📱 Parancsok a telefonodról
- 🔔 Minden értesítés Telegram-on

---

## 🚀 AJÁNLOTT: Futtatás Terminálból

Ez a **legegyszerűbb** módszer:

```cmd
python main_enhanced.py --mode paper
```

**Mit csinál?**
- ✅ Elindítja a trading botot
- ✅ Paper trading módban (nincs valós pénz)
- ✅ Logok a terminálban ÉS logs/ mappában
- 🔔 **Telegram értesítéseket küld** (ha a config-ban be van kapcsolva)

**Telegram értesítések típusai:**
- 🟢 Vételi szignál
- 🔴 Eladási szignál  
- 💰 Pozíció nyitás
- 📊 Pozíció zárás
- ⚠️ Kockázati figyelmeztetések
- 📈 Napi összefoglaló

---

## 📱 Telegram Beállítás Ellenőrzése

A `.env` fájlodban már be van állítva:
```env
TELEGRAM_BOT_TOKEN=8495846354:AAGnf_8SaqXBuCo04lndPk7UNWQWgNreN_M
TELEGRAM_CHAT_ID=2103749641
```

✅ **Már működnie kellene!**

---

## 🧪 Telegram Teszt

Ellenőrizd, hogy működik-e:

```cmd
python main_enhanced.py --test-notifications
```

Ez küld egy teszt üzenetet Telegram-ra.

---

## 📱 Ha Telegram Bot Vezérlést Akarsz

### 1. Indítsd el a Telegram bot interfészt:
```cmd
python start_telegram_bot.py
```

### 2. Nyisd meg a Telegram-ot

### 3. Keresd meg a botod:
- Név: ami a BotFather-ben létrehoztál
- Username: @valami_bot

### 4. Indítsd el:
```
/start
```

### 5. Elérhető parancsok:
```
/start - Bot indítása
/status - Jelenlegi státusz
/balance - Egyenleg lekérdezése
/positions - Nyitott pozíciók
/performance - Teljesítmény statisztikák
/signals - Utolsó szignálok
/help - Segítség
```

---

## ⚙️ Telegram Ki/Be Kapcsolása

### Telegram Értesítések KIKAPCSOLÁSA

Szerkeszd a `config_enhanced.yaml` fájlt:

```yaml
telegram:
  enabled: false  # <- Állítsd false-ra
```

Vagy indítsd a botot paraméter nélkül - akkor is működik.

### Telegram Értesítések BEKAPCSOLÁSA

```yaml
telegram:
  enabled: true
  notify_signals: true      # Szignálok
  notify_trades: true       # Kereskedések
  notify_daily_summary: true # Napi összefoglaló
  notify_risk_alerts: true  # Kockázati figyelmeztetések
```

---

## 🎯 Amit Én Javaslok:

### MOST (Teszteléshez):
```cmd
python demo_enhanced.py
```
Gyors teszt 5 másodperc alatt.

### UTÁNA (Normál használat):
```cmd
python main_enhanced.py --mode paper
```
- Teljes bot működés
- Terminálban látod a logokat
- **Telegram automatikusan küld értesítéseket** (ha enabled: true)

### HA Telegram-ról akarod vezérelni:
```cmd
python start_telegram_bot.py
```
Ekkor a telefonodról irányítod.

---

## 🔍 Hogyan Nézem a Telegram Üzeneteket?

Ha a bot fut (`python main_enhanced.py --mode paper`), akkor:

1. **Automatikusan küldi az üzeneteket** a beállított chat ID-re
2. Nyisd meg a Telegram-ot
3. Keresd meg a botod
4. Ott látod az értesítéseket

**NINCS SZÜKSÉG külön telegram bot futtatásra!**

---

## 📊 Összefoglalás

| Módszer | Parancs | Telegram Értesítés | Vezérlés |
|---------|---------|-------------------|----------|
| **Normál (Ajánlott)** | `python main_enhanced.py --mode paper` | ✅ Automatikus | ❌ Terminál |
| **Telegram Vezérlés** | `python start_telegram_bot.py` | ✅ Automatikus | ✅ Telegram parancsok |
| **Telegram Kikapcsolva** | Állítsd `enabled: false` | ❌ Nincs | ❌ Terminál |

---

## 🚀 MOST FUTTASD EZT:

### Ha csak tesztelni akarod:
```cmd
python demo_enhanced.py
```

### Ha a teljes botot akarod (Telegram ÉRTESÍTÉSekkel):
```cmd
python main_enhanced.py --mode paper
```

### Ha Telegram-ból akarod VEZÉRELNI:
```cmd
python start_telegram_bot.py
```

---

## ❓ Gyakori Kérdések

**K: Szükséges a Telegram?**
✅ NEM! A bot Telegram nélkül is működik.

**K: Ha Telegram van beállítva, automatikusan küld értesítéseket?**
✅ IGEN! Ha `enabled: true` a config-ban.

**K: Hogyan kapcsolom ki a Telegram értesítéseket?**
✅ `config_enhanced.yaml` → `telegram.enabled: false`

**K: Kapok értesítést ha fut a bot?**
✅ IGEN! Vételi/eladási szignálokról, pozíciókról, teljesítményről.

**K: Tudok parancsokat küldeni Telegram-ról?**
✅ IGEN! De ehhez a `start_telegram_bot.py`-t kell futtatni.

---

## 🎉 Kezdéshez:

```cmd
python main_enhanced.py --mode paper
```

Ez **minden**t elindít:
- ✅ Trading bot
- ✅ Telegram értesítések (automatikusan)
- ✅ Logolás
- ✅ Paper trading

**Nyisd meg a Telegram-ot és látni fogod az értesítéseket! 📱**

---

*Ha bármi kérdésed van, nézd meg a logokat:*
```cmd
Get-Content logs\bot.log -Wait -Tail 20
```
