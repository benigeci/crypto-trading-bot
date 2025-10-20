"""
Data Fetcher Module - Fetch real-time and historical cryptocurrency data
"""
import ccxt
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np
from logger import get_logger


class DataFetcher:
    """
    Multi-source cryptocurrency data fetcher with error handling and validation
    """
    
    def __init__(self, primary_source='binance', backup_source='coingecko',
                 api_key=None, api_secret=None):
        """
        Initialize data fetcher
        
        Args:
            primary_source: Primary data source (binance, coinbase, etc.)
            backup_source: Backup data source
            api_key: API key for exchange (optional)
            api_secret: API secret for exchange (optional)
        """
        self.logger = get_logger()
        self.primary_source = primary_source
        self.backup_source = backup_source
        
        # Initialize primary exchange (public access - no auth needed for price data)
        try:
            if primary_source.lower() == 'binance':
                self.exchange = ccxt.binance({
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot'
                    }
                })
                # Load markets (public endpoint, no timestamp required)
                self.exchange.load_markets()
            else:
                # Generic exchange initialization
                exchange_class = getattr(ccxt, primary_source.lower())
                self.exchange = exchange_class({
                    'enableRateLimit': True
                })
                if self.exchange:
                    self.exchange.load_markets()
            
            self.logger.info(f"Initialized {primary_source} exchange connection")
        except Exception as e:
            self.logger.error(f"Failed to initialize exchange: {e}")
            self.exchange = None
        
        # Rate limiting
        self.last_request_time = {}
        self.min_request_interval = 1.0  # Minimum seconds between requests
        
        # CoinGecko API
        self.coingecko_base_url = "https://api.coingecko.com/api/v3"
        
    def _rate_limit(self, source: str):
        """
        Implement rate limiting
        
        Args:
            source: Data source identifier
        """
        current_time = time.time()
        last_time = self.last_request_time.get(source, 0)
        
        time_since_last = current_time - last_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time[source] = time.time()
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = '15m', 
                    limit: int = 500) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV (candlestick) data
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to fetch
        
        Returns:
            DataFrame with OHLCV data or None
        """
        try:
            self._rate_limit(self.primary_source)
            
            if self.exchange is None:
                raise Exception("Exchange not initialized")
            
            # Fetch OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                self.logger.warning(f"No OHLCV data returned for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Validate data
            if not self._validate_ohlcv(df):
                self.logger.warning(f"OHLCV data validation failed for {symbol}")
                return None
            
            self.logger.debug(f"Fetched {len(df)} candles for {symbol} ({timeframe})")
            return df
            
        except ccxt.NetworkError as e:
            self.logger.error(f"Network error fetching OHLCV for {symbol}: {e}")
            return self._fetch_ohlcv_backup(symbol, timeframe, limit)
        except ccxt.ExchangeError as e:
            self.logger.error(f"Exchange error fetching OHLCV for {symbol}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error fetching OHLCV for {symbol}: {e}")
            return None
    
    def _fetch_ohlcv_backup(self, symbol: str, timeframe: str, limit: int) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV from backup source (CoinGecko)
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            limit: Number of candles
        
        Returns:
            DataFrame with OHLCV data or None
        """
        try:
            self.logger.info(f"Attempting backup fetch from {self.backup_source} for {symbol}")
            
            # Convert symbol format (BTC/USDT -> bitcoin)
            coin_id = self._symbol_to_coingecko_id(symbol)
            
            # Determine days based on timeframe and limit
            days = self._calculate_days_from_timeframe(timeframe, limit)
            
            # Fetch from CoinGecko
            url = f"{self.coingecko_base_url}/coins/{coin_id}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': days,
                'interval': 'hourly' if timeframe in ['1h', '4h'] else 'daily'
            }
            
            self._rate_limit('coingecko')
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            prices = data.get('prices', [])
            
            if not prices:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(prices, columns=['timestamp', 'close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # For simplified OHLCV, use close price
            df['open'] = df['close']
            df['high'] = df['close']
            df['low'] = df['close']
            df['volume'] = 0  # Volume not available in simple endpoint
            
            self.logger.info(f"Successfully fetched {len(df)} candles from backup source")
            return df
            
        except Exception as e:
            self.logger.error(f"Backup fetch failed: {e}")
            return None
    
    def fetch_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetch current market price
        
        Args:
            symbol: Trading pair
        
        Returns:
            Current price or None
        """
        try:
            self._rate_limit(self.primary_source)
            
            if self.exchange is None:
                raise Exception("Exchange not initialized")
            
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker.get('last') or ticker.get('close')
            
            if price:
                self.logger.debug(f"Current price for {symbol}: {price}")
                return float(price)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching current price for {symbol}: {e}")
            return None
    
    def fetch_ticker_info(self, symbol: str) -> Optional[Dict]:
        """
        Fetch comprehensive ticker information
        
        Args:
            symbol: Trading pair
        
        Returns:
            Dictionary with ticker data or None
        """
        try:
            self._rate_limit(self.primary_source)
            
            if self.exchange is None:
                raise Exception("Exchange not initialized")
            
            ticker = self.exchange.fetch_ticker(symbol)
            
            return {
                'symbol': symbol,
                'price': ticker.get('last'),
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
                'high_24h': ticker.get('high'),
                'low_24h': ticker.get('low'),
                'volume_24h': ticker.get('quoteVolume'),
                'change_24h': ticker.get('change'),
                'change_percent_24h': ticker.get('percentage'),
                'timestamp': ticker.get('timestamp')
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching ticker info for {symbol}: {e}")
            return None
    
    def fetch_order_book(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """
        Fetch order book data
        
        Args:
            symbol: Trading pair
            limit: Number of orders to fetch per side
        
        Returns:
            Dictionary with bids and asks or None
        """
        try:
            self._rate_limit(self.primary_source)
            
            if self.exchange is None:
                raise Exception("Exchange not initialized")
            
            order_book = self.exchange.fetch_order_book(symbol, limit=limit)
            
            return {
                'symbol': symbol,
                'bids': order_book['bids'][:limit],
                'asks': order_book['asks'][:limit],
                'timestamp': order_book.get('timestamp')
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching order book for {symbol}: {e}")
            return None
    
    def fetch_multiple_symbols(self, symbols: List[str], timeframe: str = '15m',
                              limit: int = 500) -> Dict[str, pd.DataFrame]:
        """
        Fetch OHLCV data for multiple symbols
        
        Args:
            symbols: List of trading pairs
            timeframe: Candle timeframe
            limit: Number of candles per symbol
        
        Returns:
            Dictionary mapping symbols to DataFrames
        """
        results = {}
        
        for symbol in symbols:
            self.logger.info(f"Fetching data for {symbol}...")
            df = self.fetch_ohlcv(symbol, timeframe, limit)
            
            if df is not None:
                results[symbol] = df
            else:
                self.logger.warning(f"Failed to fetch data for {symbol}")
            
            # Small delay between requests
            time.sleep(0.5)
        
        self.logger.info(f"Successfully fetched data for {len(results)}/{len(symbols)} symbols")
        return results
    
    def _validate_ohlcv(self, df: pd.DataFrame) -> bool:
        """
        Validate OHLCV data quality
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            True if valid, False otherwise
        """
        if df is None or df.empty:
            return False
        
        # Check for required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            return False
        
        # Check for null values
        if df[required_columns].isnull().any().any():
            self.logger.warning("OHLCV data contains null values")
            return False
        
        # Check for negative values
        if (df[required_columns] < 0).any().any():
            self.logger.warning("OHLCV data contains negative values")
            return False
        
        # Check high >= low
        if (df['high'] < df['low']).any():
            self.logger.warning("OHLCV data has high < low")
            return False
        
        # Check high >= open, close and low <= open, close
        if not ((df['high'] >= df['open']).all() and (df['high'] >= df['close']).all()):
            self.logger.warning("OHLCV data has invalid high prices")
            return False
        
        if not ((df['low'] <= df['open']).all() and (df['low'] <= df['close']).all()):
            self.logger.warning("OHLCV data has invalid low prices")
            return False
        
        return True
    
    def _symbol_to_coingecko_id(self, symbol: str) -> str:
        """
        Convert trading pair to CoinGecko coin ID
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
        
        Returns:
            CoinGecko coin ID
        """
        # Simple mapping (expand as needed)
        mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'BNB': 'binancecoin',
            'SOL': 'solana',
            'ADA': 'cardano',
            'XRP': 'ripple',
            'DOT': 'polkadot',
            'DOGE': 'dogecoin',
            'MATIC': 'matic-network',
            'AVAX': 'avalanche-2'
        }
        
        base = symbol.split('/')[0]
        return mapping.get(base, base.lower())
    
    def _calculate_days_from_timeframe(self, timeframe: str, limit: int) -> int:
        """
        Calculate number of days based on timeframe and limit
        
        Args:
            timeframe: Candle timeframe
            limit: Number of candles
        
        Returns:
            Number of days
        """
        timeframe_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        
        minutes = timeframe_minutes.get(timeframe, 15)
        total_minutes = minutes * limit
        days = max(1, total_minutes // 1440)
        
        return min(days, 365)  # CoinGecko max is 365 days


if __name__ == "__main__":
    # Test the data fetcher
    fetcher = DataFetcher(primary_source='binance')
    
    # Test single symbol fetch
    df = fetcher.fetch_ohlcv('BTC/USDT', '15m', 100)
    if df is not None:
        print(f"Fetched {len(df)} candles")
        print(df.head())
        print(df.tail())
    
    # Test current price
    price = fetcher.fetch_current_price('BTC/USDT')
    print(f"Current BTC price: ${price}")
    
    # Test ticker info
    ticker = fetcher.fetch_ticker_info('BTC/USDT')
    print(f"Ticker info: {ticker}")
