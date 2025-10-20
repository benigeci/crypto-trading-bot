"""
Advanced Technical Indicators - Additional indicators for enhanced analysis
Includes Ichimoku, Fibonacci, Pivot Points, and multi-timeframe analysis
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from logger import get_logger


class AdvancedIndicators:
    """
    Advanced technical indicators beyond basic RSI/MACD
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize advanced indicators
        
        Args:
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.config = config or {}
    
    def calculate_ichimoku(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Ichimoku Cloud indicator
        
        Ichimoku components:
        - Tenkan-sen (Conversion Line): (9-period high + 9-period low)/2
        - Kijun-sen (Base Line): (26-period high + 26-period low)/2
        - Senkou Span A (Leading Span A): (Tenkan-sen + Kijun-sen)/2 shifted 26 periods ahead
        - Senkou Span B (Leading Span B): (52-period high + 52-period low)/2 shifted 26 periods ahead
        - Chikou Span (Lagging Span): Close shifted 26 periods back
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with Ichimoku components
        """
        high_9 = df['high'].rolling(window=9).max()
        low_9 = df['low'].rolling(window=9).min()
        df['ichimoku_tenkan'] = (high_9 + low_9) / 2
        
        high_26 = df['high'].rolling(window=26).max()
        low_26 = df['low'].rolling(window=26).min()
        df['ichimoku_kijun'] = (high_26 + low_26) / 2
        
        df['ichimoku_senkou_a'] = ((df['ichimoku_tenkan'] + df['ichimoku_kijun']) / 2).shift(26)
        
        high_52 = df['high'].rolling(window=52).max()
        low_52 = df['low'].rolling(window=52).min()
        df['ichimoku_senkou_b'] = ((high_52 + low_52) / 2).shift(26)
        
        df['ichimoku_chikou'] = df['close'].shift(-26)
        
        # Cloud signals
        df['ichimoku_cloud_bullish'] = df['ichimoku_senkou_a'] > df['ichimoku_senkou_b']
        df['ichimoku_above_cloud'] = df['close'] > df[['ichimoku_senkou_a', 'ichimoku_senkou_b']].max(axis=1)
        df['ichimoku_below_cloud'] = df['close'] < df[['ichimoku_senkou_a', 'ichimoku_senkou_b']].min(axis=1)
        
        return df
    
    def calculate_fibonacci_levels(self, df: pd.DataFrame, lookback: int = 100) -> Dict[str, float]:
        """
        Calculate Fibonacci retracement levels based on recent swing high/low
        
        Args:
            df: DataFrame with OHLCV data
            lookback: Number of periods to look back for swing high/low
            
        Returns:
            Dictionary with Fibonacci levels
        """
        # Find swing high and low
        recent = df.tail(lookback)
        swing_high = recent['high'].max()
        swing_low = recent['low'].min()
        
        diff = swing_high - swing_low
        
        # Standard Fibonacci retracement levels
        levels = {
            'swing_high': swing_high,
            'fib_0.236': swing_high - (0.236 * diff),
            'fib_0.382': swing_high - (0.382 * diff),
            'fib_0.500': swing_high - (0.500 * diff),
            'fib_0.618': swing_high - (0.618 * diff),  # Golden ratio
            'fib_0.786': swing_high - (0.786 * diff),
            'swing_low': swing_low
        }
        
        return levels
    
    def calculate_pivot_points(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate traditional pivot points for intraday trading
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Dictionary with pivot levels
        """
        # Use previous day's data
        yesterday = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
        
        high = yesterday['high']
        low = yesterday['low']
        close = yesterday['close']
        
        # Pivot point (PP)
        pp = (high + low + close) / 3
        
        # Support and resistance levels
        pivots = {
            'PP': pp,
            'R1': (2 * pp) - low,
            'R2': pp + (high - low),
            'R3': high + 2 * (pp - low),
            'S1': (2 * pp) - high,
            'S2': pp - (high - low),
            'S3': low - 2 * (high - pp)
        }
        
        return pivots
    
    def calculate_volume_profile(self, df: pd.DataFrame, bins: int = 20) -> pd.DataFrame:
        """
        Calculate volume profile - shows where most trading volume occurred
        
        Args:
            df: DataFrame with OHLCV data
            bins: Number of price bins
            
        Returns:
            DataFrame with volume profile
        """
        # Create price bins
        price_min = df['low'].min()
        price_max = df['high'].max()
        bin_edges = np.linspace(price_min, price_max, bins + 1)
        
        # Aggregate volume by price level
        volume_profile = []
        
        for i in range(len(bin_edges) - 1):
            bin_low = bin_edges[i]
            bin_high = bin_edges[i + 1]
            bin_mid = (bin_low + bin_high) / 2
            
            # Sum volume where price was in this range
            mask = (df['low'] <= bin_high) & (df['high'] >= bin_low)
            volume_in_bin = df.loc[mask, 'volume'].sum()
            
            volume_profile.append({
                'price': bin_mid,
                'volume': volume_in_bin
            })
        
        vp_df = pd.DataFrame(volume_profile)
        
        # Find Point of Control (POC) - price with highest volume
        poc_idx = vp_df['volume'].idxmax()
        poc_price = vp_df.loc[poc_idx, 'price']
        
        # Find Value Area (70% of volume)
        total_volume = vp_df['volume'].sum()
        target_volume = total_volume * 0.70
        
        vp_sorted = vp_df.sort_values('volume', ascending=False)
        cumsum = 0
        value_area_prices = []
        
        for _, row in vp_sorted.iterrows():
            cumsum += row['volume']
            value_area_prices.append(row['price'])
            if cumsum >= target_volume:
                break
        
        return {
            'profile': vp_df,
            'poc': poc_price,
            'value_area_high': max(value_area_prices),
            'value_area_low': min(value_area_prices)
        }
    
    def detect_candlestick_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect common candlestick patterns
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with pattern flags
        """
        df = df.copy()
        
        # Calculate candle body and wicks
        df['body'] = abs(df['close'] - df['open'])
        df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
        df['is_bullish'] = df['close'] > df['open']
        df['is_bearish'] = df['close'] < df['open']
        
        # Doji - Small body, long wicks
        avg_body = df['body'].rolling(20).mean()
        df['pattern_doji'] = (df['body'] < avg_body * 0.1) & \
                             ((df['upper_wick'] + df['lower_wick']) > df['body'] * 3)
        
        # Hammer - Small body at top, long lower wick (bullish reversal)
        df['pattern_hammer'] = df['is_bullish'] & \
                               (df['lower_wick'] > df['body'] * 2) & \
                               (df['upper_wick'] < df['body'] * 0.5)
        
        # Shooting Star - Small body at bottom, long upper wick (bearish reversal)
        df['pattern_shooting_star'] = df['is_bearish'] & \
                                      (df['upper_wick'] > df['body'] * 2) & \
                                      (df['lower_wick'] < df['body'] * 0.5)
        
        # Engulfing patterns
        if len(df) >= 2:
            prev_body = df['body'].shift(1)
            prev_bullish = df['is_bullish'].shift(1)
            
            # Bullish Engulfing
            df['pattern_bullish_engulfing'] = df['is_bullish'] & \
                                              ~prev_bullish & \
                                              (df['body'] > prev_body * 1.5)
            
            # Bearish Engulfing
            df['pattern_bearish_engulfing'] = df['is_bearish'] & \
                                              prev_bullish & \
                                              (df['body'] > prev_body * 1.5)
        
        return df
    
    def calculate_order_flow_imbalance(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Estimate order flow imbalance based on volume and price movement
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with order flow metrics
        """
        df = df.copy()
        
        # Volume delta (buying vs selling pressure)
        price_change = df['close'] - df['open']
        df['volume_delta'] = np.where(price_change > 0, 
                                       df['volume'], 
                                       -df['volume'])
        
        # Cumulative volume delta
        df['cvd'] = df['volume_delta'].cumsum()
        
        # Buy/Sell volume estimate (simplified)
        total_range = df['high'] - df['low']
        close_position = (df['close'] - df['low']) / total_range
        
        df['buy_volume'] = df['volume'] * close_position
        df['sell_volume'] = df['volume'] * (1 - close_position)
        
        # Order flow imbalance ratio
        df['ofi_ratio'] = df['buy_volume'] / (df['sell_volume'] + 1e-10)
        
        # Smooth the ratio
        df['ofi_ratio_ma'] = df['ofi_ratio'].rolling(10).mean()
        
        return df
    
    def analyze_market_structure(self, df: pd.DataFrame, swing_strength: int = 5) -> Dict:
        """
        Analyze market structure - higher highs, higher lows, etc.
        
        Args:
            df: DataFrame with OHLCV data
            swing_strength: Number of candles for swing detection
            
        Returns:
            Dictionary with market structure analysis
        """
        # Find swing highs and lows
        df = df.copy()
        
        # Swing high: local maximum
        df['swing_high'] = False
        df['swing_low'] = False
        
        for i in range(swing_strength, len(df) - swing_strength):
            # Check if current high is highest in range
            if df['high'].iloc[i] == df['high'].iloc[i-swing_strength:i+swing_strength+1].max():
                df.loc[df.index[i], 'swing_high'] = True
            
            # Check if current low is lowest in range
            if df['low'].iloc[i] == df['low'].iloc[i-swing_strength:i+swing_strength+1].min():
                df.loc[df.index[i], 'swing_low'] = True
        
        # Get recent swings
        recent_highs = df[df['swing_high']].tail(3)
        recent_lows = df[df['swing_low']].tail(3)
        
        # Determine trend structure
        structure = 'neutral'
        
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            # Higher highs and higher lows = uptrend
            higher_highs = all(recent_highs['high'].iloc[i] > recent_highs['high'].iloc[i-1] 
                              for i in range(1, len(recent_highs)))
            higher_lows = all(recent_lows['low'].iloc[i] > recent_lows['low'].iloc[i-1] 
                             for i in range(1, len(recent_lows)))
            
            # Lower highs and lower lows = downtrend
            lower_highs = all(recent_highs['high'].iloc[i] < recent_highs['high'].iloc[i-1] 
                             for i in range(1, len(recent_highs)))
            lower_lows = all(recent_lows['low'].iloc[i] < recent_lows['low'].iloc[i-1] 
                            for i in range(1, len(recent_lows)))
            
            if higher_highs and higher_lows:
                structure = 'uptrend'
            elif lower_highs and lower_lows:
                structure = 'downtrend'
            else:
                structure = 'consolidation'
        
        return {
            'structure': structure,
            'swing_highs': recent_highs['high'].tolist(),
            'swing_lows': recent_lows['low'].tolist(),
            'current_high': df['high'].iloc[-1],
            'current_low': df['low'].iloc[-1]
        }
    
    def calculate_support_resistance(self, df: pd.DataFrame, 
                                     num_levels: int = 5,
                                     proximity: float = 0.02) -> Dict:
        """
        Calculate support and resistance levels using clustering
        
        Args:
            df: DataFrame with OHLCV data
            num_levels: Number of S/R levels to find
            proximity: Price proximity threshold (2% by default)
            
        Returns:
            Dictionary with support and resistance levels
        """
        # Collect all potential S/R levels
        levels = []
        levels.extend(df['high'].tolist())
        levels.extend(df['low'].tolist())
        
        # Cluster nearby levels
        levels = sorted(set(levels))
        clustered_levels = []
        
        i = 0
        while i < len(levels):
            cluster = [levels[i]]
            j = i + 1
            
            # Group nearby levels
            while j < len(levels):
                if abs(levels[j] - levels[i]) / levels[i] < proximity:
                    cluster.append(levels[j])
                    j += 1
                else:
                    break
            
            # Use average of cluster
            clustered_levels.append(np.mean(cluster))
            i = j
        
        # Find levels with most touches
        level_touches = []
        
        for level in clustered_levels:
            touches = 0
            
            for _, row in df.iterrows():
                # Check if price touched this level
                if abs(row['high'] - level) / level < proximity or \
                   abs(row['low'] - level) / level < proximity:
                    touches += 1
            
            level_touches.append((level, touches))
        
        # Sort by number of touches and get top levels
        level_touches.sort(key=lambda x: x[1], reverse=True)
        top_levels = level_touches[:num_levels]
        
        current_price = df['close'].iloc[-1]
        
        # Classify as support or resistance
        support_levels = [level for level, _ in top_levels if level < current_price]
        resistance_levels = [level for level, _ in top_levels if level > current_price]
        
        return {
            'support': sorted(support_levels, reverse=True),
            'resistance': sorted(resistance_levels),
            'current_price': current_price,
            'nearest_support': max(support_levels) if support_levels else None,
            'nearest_resistance': min(resistance_levels) if resistance_levels else None
        }


# Example usage
if __name__ == "__main__":
    from data_fetcher import DataFetcher
    
    print("\n" + "="*60)
    print("TESTING ADVANCED INDICATORS")
    print("="*60)
    
    # Fetch sample data
    fetcher = DataFetcher()
    df = fetcher.fetch_ohlcv('BTC/USDT', timeframe='1h', limit=200)
    
    if df is not None:
        advanced = AdvancedIndicators()
        
        # Ichimoku
        print("\n📊 Calculating Ichimoku Cloud...")
        df = advanced.calculate_ichimoku(df)
        print(f"  Tenkan-sen: {df['ichimoku_tenkan'].iloc[-1]:.2f}")
        print(f"  Kijun-sen: {df['ichimoku_kijun'].iloc[-1]:.2f}")
        print(f"  Cloud: {'Bullish ✅' if df['ichimoku_cloud_bullish'].iloc[-1] else 'Bearish ❌'}")
        
        # Fibonacci
        print("\n📐 Calculating Fibonacci Levels...")
        fib = advanced.calculate_fibonacci_levels(df)
        for level, price in fib.items():
            print(f"  {level}: ${price:.2f}")
        
        # Pivot Points
        print("\n🎯 Calculating Pivot Points...")
        pivots = advanced.calculate_pivot_points(df)
        for level, price in pivots.items():
            print(f"  {level}: ${price:.2f}")
        
        # Support/Resistance
        print("\n🔰 Calculating Support/Resistance...")
        sr = advanced.calculate_support_resistance(df)
        print(f"  Current: ${sr['current_price']:.2f}")
        print(f"  Support: {[f'${x:.2f}' for x in sr['support']]}")
        print(f"  Resistance: {[f'${x:.2f}' for x in sr['resistance']]}")
        
        # Market Structure
        print("\n🏗️ Analyzing Market Structure...")
        structure = advanced.analyze_market_structure(df)
        print(f"  Structure: {structure['structure'].upper()}")
        
        print("\n✅ All indicators calculated successfully!")
    else:
        print("❌ Failed to fetch data")
