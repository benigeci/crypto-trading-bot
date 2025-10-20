"""
Telegram notification test script
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from logger import setup_logger

logger = setup_logger('telegram_test', log_level='INFO')

async def test_telegram():
    """Test Telegram bot notifications"""
    print("="*70)
    print("📱 Telegram Értesítés Teszt")
    print("="*70)
    print()
    
    # Load environment variables
    load_dotenv()
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token:
        print("❌ HIBA: TELEGRAM_BOT_TOKEN nincs beállítva a .env fájlban!")
        print()
        print("Ellenőrizd a .env fájlt:")
        print("  TELEGRAM_BOT_TOKEN=your_token_here")
        return 1
    
    print(f"✅ Telegram Token betöltve")
    print(f"✅ Chat ID: {chat_id if chat_id else '(nincs beállítva)'}")
    print()
    
    try:
        # Try to import telegram bot
        try:
            from telegram_bot import TradingBot
            print("✅ telegram_bot modul importálva")
        except ImportError as e:
            print(f"⚠️  telegram_bot.py nem található, próbálom közvetlenül...")
            
            # Direct telegram test
            from telegram import Bot
            from telegram.error import TelegramError
            
            print("📤 Teszt üzenet küldése...")
            
            bot = Bot(token=token)
            
            message = """
🤖 *Telegram Bot Teszt Sikeres!*

✅ A bot csatlakozott
✅ Értesítések működnek
✅ Chat ID helyes

📊 Trading bot készen áll az értesítések küldésére!

_Ez egy teszt üzenet volt._
"""
            
            if chat_id:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
                print()
                print("✅ Teszt üzenet ELKÜLDVE!")
                print(f"   Chat ID: {chat_id}")
            else:
                print()
                print("⚠️  CHAT_ID nincs beállítva!")
                print("   Az értesítések működni fognak, de minden usernek küldi.")
                
                # Get bot info
                me = await bot.get_me()
                print()
                print(f"📱 Bot információk:")
                print(f"   Név: {me.first_name}")
                print(f"   Username: @{me.username}")
                print()
                print("💡 Következő lépések:")
                print("   1. Nyisd meg a Telegram-ot")
                print(f"   2. Keresd meg: @{me.username}")
                print("   3. Küldj neki egy üzenetet: /start")
                print("   4. Akkor fog tudni neked üzenni!")
            
            print()
            print("="*70)
            print("✅ Telegram Teszt SIKERES!")
            print("="*70)
            return 0
            
    except Exception as e:
        logger.exception(f"Telegram teszt hiba: {e}")
        print()
        print(f"❌ HIBA: {e}")
        print()
        print("🔍 Lehetséges okok:")
        print("  1. Helytelen token a .env fájlban")
        print("  2. Bot nem létezik vagy le van tiltva")
        print("  3. Nincs internet kapcsolat")
        print("  4. python-telegram-bot nincs telepítve")
        print()
        print("🔧 Megoldás:")
        print("  1. Ellenőrizd a .env fájlt")
        print("  2. Futtasd: pip install python-telegram-bot")
        print()
        return 1

if __name__ == '__main__':
    try:
        exit_code = asyncio.run(test_telegram())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Teszt megszakítva")
        sys.exit(0)
