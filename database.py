"""
Database Module - SQLite database for storing trades, signals, and historical data
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import os
from contextlib import contextmanager


class TradingDatabase:
    """
    Database manager for the trading bot
    """
    
    def __init__(self, db_path='data/trading_bot.db'):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database schema
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    price REAL NOT NULL,
                    amount REAL NOT NULL,
                    total_value REAL NOT NULL,
                    commission REAL DEFAULT 0,
                    profit_loss REAL DEFAULT 0,
                    reason TEXT,
                    status TEXT DEFAULT 'completed',
                    order_id TEXT,
                    metadata TEXT
                )
            ''')
            
            # Signals table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    price REAL NOT NULL,
                    strength INTEGER,
                    indicators TEXT,
                    executed BOOLEAN DEFAULT 0,
                    metadata TEXT
                )
            ''')
            
            # Portfolio table (current holdings)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio (
                    symbol TEXT PRIMARY KEY,
                    amount REAL NOT NULL,
                    avg_buy_price REAL NOT NULL,
                    current_price REAL,
                    total_value REAL,
                    profit_loss REAL,
                    profit_loss_percent REAL,
                    last_updated TEXT
                )
            ''')
            
            # Balance table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS balance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    balance REAL NOT NULL,
                    equity REAL NOT NULL,
                    profit_loss REAL,
                    profit_loss_percent REAL
                )
            ''')
            
            # Performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    win_rate REAL,
                    total_profit REAL,
                    total_loss REAL,
                    net_profit REAL,
                    max_drawdown REAL,
                    sharpe_ratio REAL,
                    avg_trade_duration TEXT,
                    metadata TEXT
                )
            ''')
            
            # Market data cache table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    UNIQUE(timestamp, symbol, timeframe)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp)')
            
            conn.commit()
    
    def insert_trade(self, symbol: str, action: str, price: float, amount: float,
                     commission: float = 0, profit_loss: float = 0, reason: str = '', 
                     order_id: str = '', metadata: Dict = None) -> int:
        """
        Insert a new trade record
        
        Args:
            symbol: Trading pair
            action: BUY or SELL
            price: Execution price
            amount: Trade amount
            commission: Trading commission
            profit_loss: Profit or loss from the trade
            reason: Reason for trade
            order_id: Exchange order ID
            metadata: Additional metadata
        
        Returns:
            Trade ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            total_value = price * amount
            timestamp = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO trades (timestamp, symbol, action, price, amount, 
                                  total_value, commission, profit_loss, reason, order_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, symbol, action, price, amount, total_value, 
                  commission, profit_loss, reason, order_id, json.dumps(metadata) if metadata else None))
            
            return cursor.lastrowid
    
    def insert_signal(self, symbol: str, signal_type: str, price: float,
                     indicators: Dict, strength: int = None, metadata: Dict = None) -> int:
        """
        Insert a new signal record
        
        Args:
            symbol: Trading pair
            signal_type: BUY, SELL, or HOLD
            price: Current price
            indicators: Dictionary of indicator values
            strength: Signal strength (0-100)
            metadata: Additional metadata
        
        Returns:
            Signal ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            timestamp = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO signals (timestamp, symbol, signal_type, price, 
                                   strength, indicators, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, symbol, signal_type, price, strength,
                  json.dumps(indicators), json.dumps(metadata) if metadata else None))
            
            return cursor.lastrowid
    
    def update_portfolio(self, symbol: str, amount: float, avg_buy_price: float,
                        current_price: float = None):
        """
        Update portfolio holdings
        
        Args:
            symbol: Trading pair
            amount: Current amount held
            avg_buy_price: Average buy price
            current_price: Current market price
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            total_value = amount * (current_price or avg_buy_price)
            profit_loss = total_value - (amount * avg_buy_price)
            profit_loss_percent = (profit_loss / (amount * avg_buy_price)) * 100 if amount > 0 else 0
            
            cursor.execute('''
                INSERT OR REPLACE INTO portfolio 
                (symbol, amount, avg_buy_price, current_price, total_value, 
                 profit_loss, profit_loss_percent, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, amount, avg_buy_price, current_price, total_value,
                  profit_loss, profit_loss_percent, datetime.now().isoformat()))
    
    def update_balance(self, balance: float, equity: float, profit_loss: float = None,
                      profit_loss_percent: float = None):
        """
        Record balance snapshot
        
        Args:
            balance: Available balance
            equity: Total equity (balance + holdings value)
            profit_loss: Total profit/loss
            profit_loss_percent: Total profit/loss percentage
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO balance (timestamp, balance, equity, profit_loss, profit_loss_percent)
                VALUES (?, ?, ?, ?, ?)
            ''', (datetime.now().isoformat(), balance, equity, profit_loss, profit_loss_percent))
    
    def insert_market_data(self, symbol: str, timeframe: str, timestamp: str,
                          open_price: float, high: float, low: float, 
                          close: float, volume: float):
        """
        Insert market data (OHLCV)
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            timestamp: Candle timestamp
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Volume
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO market_data (timestamp, symbol, timeframe, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp, symbol, timeframe, open_price, high, low, close, volume))
            except sqlite3.IntegrityError:
                # Data already exists, skip
                pass
    
    def get_trades(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """
        Retrieve trade history
        
        Args:
            symbol: Filter by symbol (optional)
            limit: Maximum number of records
        
        Returns:
            List of trade records
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if symbol:
                cursor.execute('''
                    SELECT * FROM trades WHERE symbol = ? 
                    ORDER BY timestamp DESC LIMIT ?
                ''', (symbol, limit))
            else:
                cursor.execute('''
                    SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?
                ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_signals(self, symbol: str = None, executed: bool = None, limit: int = 100) -> List[Dict]:
        """
        Retrieve signal history
        
        Args:
            symbol: Filter by symbol (optional)
            executed: Filter by execution status (optional)
            limit: Maximum number of records
        
        Returns:
            List of signal records
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM signals WHERE 1=1'
            params = []
            
            if symbol:
                query += ' AND symbol = ?'
                params.append(symbol)
            
            if executed is not None:
                query += ' AND executed = ?'
                params.append(1 if executed else 0)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_portfolio(self) -> List[Dict]:
        """
        Get current portfolio holdings
        
        Returns:
            List of portfolio records
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM portfolio WHERE amount > 0')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_latest_balance(self) -> Optional[Dict]:
        """
        Get latest balance record
        
        Returns:
            Balance record or None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM balance ORDER BY timestamp DESC LIMIT 1')
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_performance_summary(self) -> Dict:
        """
        Calculate performance summary
        
        Returns:
            Dictionary with performance metrics
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total trades
            cursor.execute('SELECT COUNT(*) as total FROM trades')
            total_trades = cursor.fetchone()['total']
            
            # Winning/losing trades
            cursor.execute('SELECT COUNT(*) as winning FROM trades WHERE profit_loss > 0')
            winning_trades = cursor.fetchone()['winning']
            
            cursor.execute('SELECT COUNT(*) as losing FROM trades WHERE profit_loss < 0')
            losing_trades = cursor.fetchone()['losing']
            
            # Win rate
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Total profit/loss
            cursor.execute('SELECT SUM(profit_loss) as total_pnl FROM trades')
            total_pnl = cursor.fetchone()['total_pnl'] or 0
            
            # Current balance
            latest_balance = self.get_latest_balance()
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'total_profit_loss': round(total_pnl, 2),
                'current_balance': latest_balance['balance'] if latest_balance else 0,
                'current_equity': latest_balance['equity'] if latest_balance else 0
            }
    
    def clear_old_market_data(self, days: int = 30):
        """
        Clear old market data to save space
        
        Args:
            days: Keep data newer than this many days
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = datetime.now().replace(day=datetime.now().day - days).isoformat()
            cursor.execute('DELETE FROM market_data WHERE timestamp < ?', (cutoff_date,))
            conn.commit()


if __name__ == "__main__":
    # Test the database
    db = TradingDatabase('data/test_trading_bot.db')
    
    # Insert test trade
    trade_id = db.insert_trade('BTC/USDT', 'BUY', 45000.00, 0.1, commission=4.5, reason='Strong buy signal')
    print(f"Inserted trade ID: {trade_id}")
    
    # Insert test signal
    signal_id = db.insert_signal('BTC/USDT', 'BUY', 45000.00, {'RSI': 28, 'MACD': 'bullish'}, strength=85)
    print(f"Inserted signal ID: {signal_id}")
    
    # Update portfolio
    db.update_portfolio('BTC/USDT', 0.1, 45000.00, 46000.00)
    
    # Update balance
    db.update_balance(8550.00, 13150.00, 1150.00, 11.5)
    
    # Get trades
    trades = db.get_trades(limit=10)
    print(f"Total trades: {len(trades)}")
    
    # Get performance summary
    summary = db.get_performance_summary()
    print(f"Performance: {summary}")
