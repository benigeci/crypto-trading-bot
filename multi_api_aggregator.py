"""
Multi-API Data Aggregator - Redundant data fetching with automatic failover
Provides reliable market data from multiple sources with validation
"""
import ccxt
import requests
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from logger import get_logger


class MultiAPIDataAggregator:
    """
    Fetches cryptocurrency data from multiple sources with automatic failover
    and cross-validation for maximum reliability
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize multi-API aggregator
        
        Args:
            config: Configuration dictionary with API settings
        """
        self.logger = get_logger()
        self.config = config or {}
        
        # API priorities (1 = highest)
        self.api_priority = {
            'binance': 1,
            'coingecko': 2,
            'cryptocompare': 3
        }
        
        # Initialize exchanges
        self._init_binance()
        
        # API keys from environment
        import os
        self.coingecko_api_key = os.getenv('COINGECKO_API_KEY')
        self.cryptocompare_api_key = os.getenv('CRYPTOCOMPARE_API_KEY')
        
        # Performance tracking
        self.api_health = {
            'binance': {'success': 0, 'failures': 0, 'latency': []},
            'coingecko': {'success': 0, 'failures': 0, 'latency': []},
            'cryptocompare': {'success': 0, 'failures': 0, 'latency': []}
        }
        
        # Data validation thresholds
        self.price_deviation_threshold = 0.02  # 2% max deviation between sources
        self.max_latency_ms = 500  # 500ms max acceptable latency
        
        self.logger.info("Multi-API data aggregator initialized")
        
    def _init_binance(self):
        """Initialize Binance exchange"""
        try:
            self.binance = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            self.binance.load_markets()
            self.logger.info("✅ Binance API initialized")
        except Exception as e:
            self.logger.error(f"❌ Binance initialization failed: {e}")
            self.binance = None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price with automatic failover and validation
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            
        Returns:
            Current price or None if all sources fail
        """
        prices = {}
        
        # Try each API in priority order
        apis = sorted(self.api_priority.items(), key=lambda x: x[1])
        
        for api_name, _ in apis:
            try:
                start_time = time.time()
                
                if api_name == 'binance':
                    price = self._get_price_binance(symbol)
                elif api_name == 'coingecko':
                    price = self._get_price_coingecko(symbol)
                elif api_name == 'cryptocompare':
                    price = self._get_price_cryptocompare(symbol)
                else:
                    continue
                
                latency_ms = (time.time() - start_time) * 1000
                
                if price:
                    prices[api_name] = price
                    self._record_success(api_name, latency_ms)
                    self.logger.debug(f"✅ {api_name}: ${price:.2f} ({latency_ms:.0f}ms)")
                else:
                    self._record_failure(api_name)
                    
            except Exception as e:
                self._record_failure(api_name)
                self.logger.warning(f"❌ {api_name} failed: {e}")
        
        # Validate and return consensus price
        if len(prices) == 0:
            self.logger.error(f"❌ All APIs failed for {symbol}")
            return None
        
        return self._validate_and_consensus(prices, symbol)
    
    def _get_price_binance(self, symbol: str) -> Optional[float]:
        """Get price from Binance"""
        if not self.binance:
            return None
        
        ticker = self.binance.fetch_ticker(symbol)
        return float(ticker['last'])
    
    def _get_price_coingecko(self, symbol: str) -> Optional[float]:
        """Get price from CoinGecko"""
        # Convert symbol format (BTC/USDT -> bitcoin, usdt)
        base, quote = symbol.split('/')
        
        coin_map = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'BNB': 'binancecoin',
            'SOL': 'solana',
            'ADA': 'cardano',
            'XRP': 'ripple',
            'DOT': 'polkadot',
            'DOGE': 'dogecoin',
            'AVAX': 'avalanche-2',
            'MATIC': 'matic-network'
        }
        
        coin_id = coin_map.get(base)
        if not coin_id:
            return None
        
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': coin_id,
            'vs_currencies': quote.lower()
        }
        
        if self.coingecko_api_key:
            params['x_cg_pro_api_key'] = self.coingecko_api_key
        
        response = requests.get(url, params=params, timeout=3, verify=True)
        response.raise_for_status()
        
        data = response.json()
        return float(data[coin_id][quote.lower()])
    
    def _get_price_cryptocompare(self, symbol: str) -> Optional[float]:
        """Get price from CryptoCompare"""
        base, quote = symbol.split('/')
        
        url = f"https://min-api.cryptocompare.com/data/price"
        params = {
            'fsym': base,
            'tsyms': quote
        }
        
        headers = {}
        if self.cryptocompare_api_key:
            headers['authorization'] = f'Apikey {self.cryptocompare_api_key}'
        
        response = requests.get(url, params=params, headers=headers, timeout=3, verify=True)
        response.raise_for_status()
        
        data = response.json()
        return float(data[quote])
    
    def _validate_and_consensus(self, prices: Dict[str, float], symbol: str) -> float:
        """
        Validate prices from multiple sources and return consensus
        
        Args:
            prices: Dictionary of {api_name: price}
            symbol: Trading pair
            
        Returns:
            Consensus price
        """
        if len(prices) == 1:
            # Only one source, return it
            return list(prices.values())[0]
        
        # Calculate median price
        price_values = list(prices.values())
        median_price = np.median(price_values)
        
        # Check for outliers
        valid_prices = []
        for api_name, price in prices.items():
            deviation = abs(price - median_price) / median_price
            
            if deviation > self.price_deviation_threshold:
                self.logger.warning(
                    f"⚠️ Price deviation alert for {symbol}: "
                    f"{api_name}=${price:.2f} vs median=${median_price:.2f} "
                    f"({deviation*100:.1f}% deviation)"
                )
            else:
                valid_prices.append(price)
        
        # Return average of valid prices
        if valid_prices:
            consensus = np.mean(valid_prices)
            self.logger.debug(f"✅ Consensus price for {symbol}: ${consensus:.2f}")
            return consensus
        else:
            # All prices are outliers, return median anyway
            self.logger.warning(f"⚠️ All prices are outliers for {symbol}, using median")
            return median_price
    
    def get_ohlcv(self, symbol: str, timeframe: str = '5m', 
                   limit: int = 100) -> Optional[pd.DataFrame]:
        """
        Get OHLCV data with failover
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            limit: Number of candles
            
        Returns:
            DataFrame with OHLCV data or None
        """
        # Try Binance first (most reliable for OHLCV)
        try:
            start_time = time.time()
            
            if self.binance:
                ohlcv = self.binance.fetch_ohlcv(symbol, timeframe, limit=limit)
                
                if ohlcv:
                    df = pd.DataFrame(
                        ohlcv,
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    )
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    
                    latency_ms = (time.time() - start_time) * 1000
                    self._record_success('binance', latency_ms)
                    
                    self.logger.debug(
                        f"✅ Fetched {len(df)} candles for {symbol} ({latency_ms:.0f}ms)"
                    )
                    return df
        except Exception as e:
            self._record_failure('binance')
            self.logger.error(f"❌ Failed to fetch OHLCV from Binance: {e}")
        
        # TODO: Add CryptoCompare OHLCV as backup
        
        return None
    
    def _record_success(self, api_name: str, latency_ms: float):
        """Record successful API call"""
        if api_name in self.api_health:
            self.api_health[api_name]['success'] += 1
            self.api_health[api_name]['latency'].append(latency_ms)
            
            # Keep only last 100 latency measurements
            if len(self.api_health[api_name]['latency']) > 100:
                self.api_health[api_name]['latency'].pop(0)
            
            # Alert on high latency
            if latency_ms > self.max_latency_ms:
                self.logger.warning(
                    f"⚠️ High latency alert: {api_name} took {latency_ms:.0f}ms"
                )
    
    def _record_failure(self, api_name: str):
        """Record failed API call"""
        if api_name in self.api_health:
            self.api_health[api_name]['failures'] += 1
    
    def get_api_health_report(self) -> Dict:
        """
        Get comprehensive health report for all APIs
        
        Returns:
            Dictionary with health metrics
        """
        report = {}
        
        for api_name, health in self.api_health.items():
            total_calls = health['success'] + health['failures']
            
            if total_calls > 0:
                success_rate = (health['success'] / total_calls) * 100
                avg_latency = np.mean(health['latency']) if health['latency'] else 0
                
                report[api_name] = {
                    'success_rate': f"{success_rate:.1f}%",
                    'total_calls': total_calls,
                    'successes': health['success'],
                    'failures': health['failures'],
                    'avg_latency_ms': f"{avg_latency:.0f}",
                    'max_latency_ms': f"{max(health['latency']):.0f}" if health['latency'] else 'N/A',
                    'status': '✅ Healthy' if success_rate >= 95 and avg_latency < self.max_latency_ms else '⚠️ Degraded'
                }
            else:
                report[api_name] = {
                    'status': '❌ Not used',
                    'total_calls': 0
                }
        
        return report
    
    def test_all_apis(self, symbol: str = 'BTC/USDT') -> Dict:
        """
        Test all APIs and return status
        
        Args:
            symbol: Symbol to test with
            
        Returns:
            Test results
        """
        self.logger.info(f"Testing all APIs with {symbol}...")
        
        results = {}
        
        # Test Binance
        try:
            start = time.time()
            price = self._get_price_binance(symbol)
            latency = (time.time() - start) * 1000
            
            results['binance'] = {
                'status': '✅ OK' if price else '❌ Failed',
                'price': f"${price:.2f}" if price else 'N/A',
                'latency_ms': f"{latency:.0f}"
            }
        except Exception as e:
            results['binance'] = {'status': f'❌ Error: {str(e)}'}
        
        # Test CoinGecko
        try:
            start = time.time()
            price = self._get_price_coingecko(symbol)
            latency = (time.time() - start) * 1000
            
            results['coingecko'] = {
                'status': '✅ OK' if price else '❌ Failed',
                'price': f"${price:.2f}" if price else 'N/A',
                'latency_ms': f"{latency:.0f}"
            }
        except Exception as e:
            results['coingecko'] = {'status': f'❌ Error: {str(e)[:50]}'}
        
        # Test CryptoCompare
        try:
            start = time.time()
            price = self._get_price_cryptocompare(symbol)
            latency = (time.time() - start) * 1000
            
            results['cryptocompare'] = {
                'status': '✅ OK' if price else '❌ Failed',
                'price': f"${price:.2f}" if price else 'N/A',
                'latency_ms': f"{latency:.0f}"
            }
        except Exception as e:
            results['cryptocompare'] = {'status': f'❌ Error: {str(e)[:50]}'}
        
        return results


# Example usage
if __name__ == "__main__":
    aggregator = MultiAPIDataAggregator()
    
    print("\n" + "="*60)
    print("TESTING MULTI-API DATA AGGREGATOR")
    print("="*60)
    
    # Test only Binance (fastest and most reliable)
    print("\n✅ Testing Binance API...")
    try:
        test_price = aggregator._get_price_binance('BTC/USDT')
        print(f"  Binance: ✅ Working - BTC/USDT = ${test_price:,.2f}")
    except Exception as e:
        print(f"  Binance: ❌ Failed - {e}")
    
    # Get price with consensus
    print("\n" + "-"*60)
    print("Fetching BTC/USDT price from all sources...")
    price = aggregator.get_current_price('BTC/USDT')
    print(f"✅ Consensus Price: ${price:.2f}")
    
    # Health report
    print("\n" + "-"*60)
    print("API Health Report:")
    health = aggregator.get_api_health_report()
    for api, metrics in health.items():
        print(f"\n  {api}:")
        for key, value in metrics.items():
            print(f"    {key}: {value}")
