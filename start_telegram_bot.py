"""
Telegram Bot Command Interface
Run the trading bot with Telegram controls
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from telegram_bot import TradingBot
from logger import setup_logger

logger = setup_logger('telegram_interface', log_level='INFO')

async def start_telegram_bot():
    """Start the Telegram bot interface"""
    print("="*70)
    print("📱 Telegram Bot Interface - Trading Bot Control")
    print("="*70)
    print()
    
    try:
        # Load .env
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not token:
            print("❌ TELEGRAM_BOT_TOKEN nincs beállítva a .env fájlban!")
            return 1
        
        print(f"✅ Token betöltve")
        print(f"✅ Chat ID: {chat_id if chat_id else 'Nincs beállítva (minden user)'}")
        print()
        
        # Initialize bot
        bot = TradingBot(token=token, chat_id=chat_id)
        
        print("🤖 Telegram bot inicializálva!")
        print()
        print("📱 Elérhető parancsok:")
        print("  /start - Bot indítás")
        print("  /status - Jelenlegi állapot")
        print("  /balance - Egyenleg")
        print("  /positions - Nyitott pozíciók")
        print("  /performance - Teljesítmény")
        print("  /help - Segítség")
        print()
        print("🔔 Várakozás Telegram üzenetekre...")
        print("   (Nyisd meg a Telegram-ot és írd: /start)")
        print()
        print("⚠️  Nyomj Ctrl+C a leállításhoz")
        print()
        
        # Start bot
        await bot.start()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Bot leállítva (Ctrl+C)")
        return 0
    except Exception as e:
        logger.exception(f"Telegram bot hiba: {e}")
        print(f"\n❌ Hiba: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(asyncio.run(start_telegram_bot()))
