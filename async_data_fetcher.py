"""
Asynchronous Data Fetcher with WebSocket Support
Enhanced version with async/await pattern, WebSocket streaming, and robust error handling
"""

import asyncio
import aiohttp
import ccxt.async_support as ccxt
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime, timedelta
import json
from logger import setup_logger

logger = setup_logger('async_data_fetcher')


class AsyncDataFetcher:
    """Asynchronous data fetcher with WebSocket support for real-time streaming"""
    
    def __init__(self, exchange_id: str = 'binance', testnet: bool = False):
        """
        Initialize async data fetcher
        
        Args:
            exchange_id: Exchange identifier (default: binance)
            testnet: Use testnet/sandbox mode
        """
        self.exchange_id = exchange_id
        self.testnet = testnet
        self.exchange = None
        self.ws_connections: Dict[str, aiohttp.ClientWebSocketResponse] = {}
        self.price_cache: Dict[str, Dict] = {}
        self.cache_timeout = 5  # seconds
        
    async def initialize(self):
        """Initialize async exchange connection"""
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            self.exchange = exchange_class({
                'enableRateLimit': True,
                'asyncio_loop': asyncio.get_event_loop(),
                'options': {'defaultType': 'future' if self.testnet else 'spot'}
            })
            
            if self.testnet:
                self.exchange.set_sandbox_mode(True)
                
            await self.exchange.load_markets()
            logger.info(f"Async {self.exchange_id} exchange initialized successfully")
            
        except Exception as e:
            logger.exception(f"Failed to initialize async exchange: {e}")
            raise
    
    async def close(self):
        """Close all connections"""
        try:
            # Close WebSocket connections
            for symbol, ws in self.ws_connections.items():
                await ws.close()
                logger.info(f"Closed WebSocket for {symbol}")
            
            # Close exchange connection
            if self.exchange:
                await self.exchange.close()
                logger.info("Closed exchange connection")
                
        except Exception as e:
            logger.exception(f"Error closing connections: {e}")
    
    async def fetch_ohlcv_async(
        self, 
        symbol: str, 
        timeframe: str = '15m', 
        limit: int = 100,
        use_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data asynchronously with caching
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe
            limit: Number of candles
            use_cache: Use cached data if available
            
        Returns:
            DataFrame with OHLCV data or None on error
        """
        cache_key = f"{symbol}_{timeframe}_{limit}"
        
        # Check cache
        if use_cache and cache_key in self.price_cache:
            cached = self.price_cache[cache_key]
            age = (datetime.now() - cached['timestamp']).total_seconds()
            if age < self.cache_timeout:
                logger.debug(f"Using cached data for {symbol} (age: {age:.1f}s)")
                return cached['data']
        
        try:
            # Fetch data asynchronously
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                logger.warning(f"No OHLCV data received for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Update cache
            self.price_cache[cache_key] = {
                'data': df,
                'timestamp': datetime.now()
            }
            
            logger.debug(f"Fetched {len(df)} candles for {symbol}")
            return df
            
        except Exception as e:
            logger.exception(f"Error fetching OHLCV for {symbol}: {e}")
            return None
    
    async def fetch_ticker_async(self, symbol: str) -> Optional[Dict]:
        """
        Fetch current ticker data asynchronously
        
        Args:
            symbol: Trading pair
            
        Returns:
            Ticker dictionary or None
        """
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker
            
        except Exception as e:
            logger.exception(f"Error fetching ticker for {symbol}: {e}")
            return None
    
    async def fetch_multiple_tickers(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Fetch multiple tickers concurrently
        
        Args:
            symbols: List of trading pairs
            
        Returns:
            Dictionary of symbol -> ticker data
        """
        tasks = [self.fetch_ticker_async(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        tickers = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching {symbol}: {result}")
            elif result:
                tickers[symbol] = result
        
        return tickers
    
    async def stream_trades_websocket(
        self, 
        symbol: str, 
        callback: callable
    ):
        """
        Stream real-time trades via WebSocket
        
        Args:
            symbol: Trading pair
            callback: Async function to handle trade data
        """
        if self.exchange_id != 'binance':
            logger.warning(f"WebSocket streaming not implemented for {self.exchange_id}")
            return
        
        url = f"wss://stream.binance.com:9443/ws/{symbol.lower().replace('/', '')}@trade"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url) as ws:
                    self.ws_connections[symbol] = ws
                    logger.info(f"WebSocket connected for {symbol}")
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            await callback(data)
                            
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"WebSocket error: {ws.exception()}")
                            break
                            
        except Exception as e:
            logger.exception(f"WebSocket error for {symbol}: {e}")
        finally:
            if symbol in self.ws_connections:
                del self.ws_connections[symbol]
    
    async def stream_klines_websocket(
        self, 
        symbol: str, 
        interval: str,
        callback: callable
    ):
        """
        Stream real-time klines/candles via WebSocket
        
        Args:
            symbol: Trading pair
            interval: Kline interval (1m, 5m, 15m, etc.)
            callback: Async function to handle kline data
        """
        if self.exchange_id != 'binance':
            logger.warning(f"WebSocket streaming not implemented for {self.exchange_id}")
            return
        
        symbol_lower = symbol.lower().replace('/', '')
        url = f"wss://stream.binance.com:9443/ws/{symbol_lower}@kline_{interval}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url) as ws:
                    self.ws_connections[f"{symbol}_{interval}"] = ws
                    logger.info(f"Kline WebSocket connected for {symbol} {interval}")
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if 'k' in data:
                                kline = data['k']
                                await callback({
                                    'timestamp': kline['t'],
                                    'open': float(kline['o']),
                                    'high': float(kline['h']),
                                    'low': float(kline['l']),
                                    'close': float(kline['c']),
                                    'volume': float(kline['v']),
                                    'is_closed': kline['x']
                                })
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"WebSocket error: {ws.exception()}")
                            break
                            
        except Exception as e:
            logger.exception(f"Kline WebSocket error for {symbol}: {e}")
        finally:
            key = f"{symbol}_{interval}"
            if key in self.ws_connections:
                del self.ws_connections[key]
    
    async def get_orderbook_async(
        self, 
        symbol: str, 
        limit: int = 20
    ) -> Optional[Dict]:
        """
        Fetch order book asynchronously
        
        Args:
            symbol: Trading pair
            limit: Depth limit
            
        Returns:
            Order book dictionary or None
        """
        try:
            orderbook = await self.exchange.fetch_order_book(symbol, limit)
            return orderbook
            
        except Exception as e:
            logger.exception(f"Error fetching orderbook for {symbol}: {e}")
            return None
    
    async def calculate_market_metrics(
        self, 
        symbols: List[str]
    ) -> Dict[str, Dict]:
        """
        Calculate market metrics for multiple symbols concurrently
        
        Args:
            symbols: List of trading pairs
            
        Returns:
            Dictionary with market metrics per symbol
        """
        tasks = []
        for symbol in symbols:
            tasks.append(self._get_symbol_metrics(symbol))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        metrics = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"Error calculating metrics for {symbol}: {result}")
            elif result:
                metrics[symbol] = result
        
        return metrics
    
    async def _get_symbol_metrics(self, symbol: str) -> Optional[Dict]:
        """Calculate metrics for a single symbol"""
        try:
            # Fetch data concurrently
            ticker_task = self.fetch_ticker_async(symbol)
            ohlcv_task = self.fetch_ohlcv_async(symbol, '1h', 24)
            
            ticker, ohlcv = await asyncio.gather(ticker_task, ohlcv_task)
            
            if ticker is None or ohlcv is None:
                return None
            
            # Calculate metrics
            price_change_24h = ticker.get('percentage', 0)
            volume_24h = ticker.get('quoteVolume', 0)
            volatility = ohlcv['close'].pct_change().std() * 100
            
            return {
                'price': ticker['last'],
                'change_24h': price_change_24h,
                'volume_24h': volume_24h,
                'volatility': volatility,
                'bid': ticker.get('bid', 0),
                'ask': ticker.get('ask', 0),
                'spread': (ticker.get('ask', 0) - ticker.get('bid', 0)) / ticker.get('bid', 1) * 100
            }
            
        except Exception as e:
            logger.exception(f"Error calculating metrics for {symbol}: {e}")
            return None


class AsyncMultiExchangeAggregator:
    """Aggregate data from multiple exchanges asynchronously"""
    
    def __init__(self, exchanges: List[str] = None):
        """
        Initialize multi-exchange aggregator
        
        Args:
            exchanges: List of exchange IDs (default: ['binance', 'kraken', 'coinbase'])
        """
        self.exchanges = exchanges or ['binance', 'kraken', 'coinbasepro']
        self.fetchers: Dict[str, AsyncDataFetcher] = {}
        
    async def initialize(self):
        """Initialize all exchange connections"""
        for exchange_id in self.exchanges:
            try:
                fetcher = AsyncDataFetcher(exchange_id)
                await fetcher.initialize()
                self.fetchers[exchange_id] = fetcher
                logger.info(f"Initialized {exchange_id}")
            except Exception as e:
                logger.error(f"Failed to initialize {exchange_id}: {e}")
    
    async def close(self):
        """Close all exchange connections"""
        for fetcher in self.fetchers.values():
            await fetcher.close()
    
    async def get_aggregated_price(
        self, 
        symbol: str,
        method: str = 'median'
    ) -> Optional[float]:
        """
        Get aggregated price from multiple exchanges
        
        Args:
            symbol: Trading pair
            method: Aggregation method ('mean', 'median', 'weighted')
            
        Returns:
            Aggregated price or None
        """
        tasks = [
            fetcher.fetch_ticker_async(symbol) 
            for fetcher in self.fetchers.values()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        prices = []
        volumes = []
        
        for result in results:
            if isinstance(result, dict) and 'last' in result:
                prices.append(result['last'])
                volumes.append(result.get('quoteVolume', 0))
        
        if not prices:
            return None
        
        if method == 'mean':
            return sum(prices) / len(prices)
        elif method == 'median':
            prices.sort()
            n = len(prices)
            return prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
        elif method == 'weighted':
            total_volume = sum(volumes)
            if total_volume == 0:
                return sum(prices) / len(prices)
            return sum(p * v for p, v in zip(prices, volumes)) / total_volume
        
        return None


# Example usage
async def main():
    """Example usage of async data fetcher"""
    fetcher = AsyncDataFetcher('binance')
    
    try:
        await fetcher.initialize()
        
        # Fetch OHLCV
        df = await fetcher.fetch_ohlcv_async('BTC/USDT', '15m', 100)
        print(f"Fetched {len(df)} candles")
        
        # Fetch multiple tickers
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        tickers = await fetcher.fetch_multiple_tickers(symbols)
        for symbol, ticker in tickers.items():
            print(f"{symbol}: ${ticker['last']:.2f}")
        
        # Calculate market metrics
        metrics = await fetcher.calculate_market_metrics(symbols)
        for symbol, data in metrics.items():
            print(f"{symbol} volatility: {data['volatility']:.2f}%")
        
    finally:
        await fetcher.close()


if __name__ == '__main__':
    asyncio.run(main())
