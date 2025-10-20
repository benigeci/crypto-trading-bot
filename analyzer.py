"""
Technical Analysis Module - Calculate indicators and generate trading signals
"""
import pandas as pd
import numpy as np
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import VolumeWeightedAveragePrice, OnBalanceVolumeIndicator
from typing import Dict, List, Tuple, Optional
from logger import get_logger


class TechnicalAnalyzer:
    """
    Comprehensive technical analysis engine with multiple indicators
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize technical analyzer
        
        Args:
            config: Configuration dictionary with indicator parameters
        """
        self.logger = get_logger()
        self.config = config or {}
        
        # Default indicator parameters
        self.rsi_period = self.config.get('rsi', {}).get('period', 14)
        self.rsi_overbought = self.config.get('rsi', {}).get('overbought', 70)
        self.rsi_oversold = self.config.get('rsi', {}).get('oversold', 30)
        
        self.macd_fast = self.config.get('macd', {}).get('fast_period', 12)
        self.macd_slow = self.config.get('macd', {}).get('slow_period', 26)
        self.macd_signal = self.config.get('macd', {}).get('signal_period', 9)
        
        self.ema_periods = self.config.get('ema', {}).get('periods', [9, 21, 50, 200])
        
        self.bb_period = self.config.get('bollinger_bands', {}).get('period', 20)
        self.bb_std = self.config.get('bollinger_bands', {}).get('std_dev', 2)
        
        self.volume_ma_period = self.config.get('volume', {}).get('ma_period', 20)
        self.volume_spike_threshold = self.config.get('volume', {}).get('spike_threshold', 1.5)
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            DataFrame with added indicator columns
        """
        if df is None or df.empty:
            self.logger.error("Empty dataframe provided for indicator calculation")
            return df
        
        try:
            # Make a copy to avoid modifying original
            df = df.copy()
            
            # RSI
            df = self._calculate_rsi(df)
            
            # MACD
            df = self._calculate_macd(df)
            
            # EMA
            df = self._calculate_ema(df)
            
            # Bollinger Bands
            df = self._calculate_bollinger_bands(df)
            
            # Volume indicators
            df = self._calculate_volume_indicators(df)
            
            # ATR (Average True Range)
            df = self._calculate_atr(df)
            
            # ADX (Average Directional Index)
            df = self._calculate_adx(df)
            
            # Stochastic
            df = self._calculate_stochastic(df)
            
            # Support/Resistance
            df = self._calculate_support_resistance(df)
            
            self.logger.debug(f"Calculated all indicators for {len(df)} candles")
            return df
            
        except Exception as e:
            self.logger.error(f"Error calculating indicators: {e}", exc_info=True)
            return df
    
    def _calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Relative Strength Index"""
        try:
            rsi = RSIIndicator(close=df['close'], window=self.rsi_period)
            df['rsi'] = rsi.rsi()
            return df
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            return df
    
    def _calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate MACD indicator"""
        try:
            macd = MACD(
                close=df['close'],
                window_fast=self.macd_fast,
                window_slow=self.macd_slow,
                window_sign=self.macd_signal
            )
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_diff'] = macd.macd_diff()
            return df
        except Exception as e:
            self.logger.error(f"Error calculating MACD: {e}")
            return df
    
    def _calculate_ema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Exponential Moving Averages"""
        try:
            for period in self.ema_periods:
                ema = EMAIndicator(close=df['close'], window=period)
                df[f'ema_{period}'] = ema.ema_indicator()
            return df
        except Exception as e:
            self.logger.error(f"Error calculating EMA: {e}")
            return df
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Bollinger Bands"""
        try:
            bb = BollingerBands(
                close=df['close'],
                window=self.bb_period,
                window_dev=self.bb_std
            )
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_lower'] = bb.bollinger_lband()
            df['bb_width'] = bb.bollinger_wband()
            df['bb_pband'] = bb.bollinger_pband()
            return df
        except Exception as e:
            self.logger.error(f"Error calculating Bollinger Bands: {e}")
            return df
    
    def _calculate_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate volume-based indicators"""
        try:
            # Volume moving average
            df['volume_ma'] = df['volume'].rolling(window=self.volume_ma_period).mean()
            
            # Volume ratio
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            # On-Balance Volume
            obv = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume'])
            df['obv'] = obv.on_balance_volume()
            
            return df
        except Exception as e:
            self.logger.error(f"Error calculating volume indicators: {e}")
            return df
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Calculate Average True Range"""
        try:
            atr = AverageTrueRange(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                window=period
            )
            df['atr'] = atr.average_true_range()
            return df
        except Exception as e:
            self.logger.error(f"Error calculating ATR: {e}")
            return df
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Calculate Average Directional Index"""
        try:
            adx = ADXIndicator(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                window=period
            )
            df['adx'] = adx.adx()
            df['adx_pos'] = adx.adx_pos()
            df['adx_neg'] = adx.adx_neg()
            return df
        except Exception as e:
            self.logger.error(f"Error calculating ADX: {e}")
            return df
    
    def _calculate_stochastic(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Calculate Stochastic Oscillator"""
        try:
            stoch = StochasticOscillator(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                window=period,
                smooth_window=3
            )
            df['stoch_k'] = stoch.stoch()
            df['stoch_d'] = stoch.stoch_signal()
            return df
        except Exception as e:
            self.logger.error(f"Error calculating Stochastic: {e}")
            return df
    
    def _calculate_support_resistance(self, df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """Calculate support and resistance levels"""
        try:
            df['resistance'] = df['high'].rolling(window=window).max()
            df['support'] = df['low'].rolling(window=window).min()
            return df
        except Exception as e:
            self.logger.error(f"Error calculating support/resistance: {e}")
            return df
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Tuple[str, int, Dict]:
        """
        Generate trading signal based on multiple indicators
        
        Args:
            df: DataFrame with calculated indicators
            symbol: Trading pair symbol
        
        Returns:
            Tuple of (signal_type, strength, indicators_dict)
            signal_type: 'BUY', 'SELL', or 'HOLD'
            strength: Signal strength (0-100)
            indicators_dict: Dictionary of indicator values
        """
        if df is None or df.empty or len(df) < 2:
            return 'HOLD', 0, {}
        
        try:
            # Get latest values
            current = df.iloc[-1]
            previous = df.iloc[-2]
            
            # Initialize signal counters
            buy_signals = 0
            sell_signals = 0
            total_weight = 0
            
            indicators = {}
            
            # RSI Analysis (Weight: 20)
            if 'rsi' in current and not pd.isna(current['rsi']):
                rsi = current['rsi']
                indicators['rsi'] = round(rsi, 2)
                
                if rsi < self.rsi_oversold:
                    buy_signals += 20
                    indicators['rsi_signal'] = 'oversold'
                elif rsi > self.rsi_overbought:
                    sell_signals += 20
                    indicators['rsi_signal'] = 'overbought'
                else:
                    indicators['rsi_signal'] = 'neutral'
                
                total_weight += 20
            
            # MACD Analysis (Weight: 25)
            if 'macd' in current and 'macd_signal' in current:
                macd = current['macd']
                macd_signal = current['macd_signal']
                macd_diff = current['macd_diff']
                prev_macd_diff = previous['macd_diff']
                
                indicators['macd'] = round(macd, 4)
                indicators['macd_signal'] = round(macd_signal, 4)
                
                # Bullish crossover
                if prev_macd_diff < 0 and macd_diff > 0:
                    buy_signals += 25
                    indicators['macd_cross'] = 'bullish'
                # Bearish crossover
                elif prev_macd_diff > 0 and macd_diff < 0:
                    sell_signals += 25
                    indicators['macd_cross'] = 'bearish'
                else:
                    indicators['macd_cross'] = 'neutral'
                
                total_weight += 25
            
            # EMA Analysis (Weight: 20)
            ema_buy = 0
            ema_sell = 0
            
            if f'ema_{self.ema_periods[0]}' in current:
                price = current['close']
                indicators['price'] = round(price, 2)
                
                # Check EMA alignment
                for i, period in enumerate(self.ema_periods[:-1]):
                    if f'ema_{period}' in current and f'ema_{self.ema_periods[i+1]}' in current:
                        ema_short = current[f'ema_{period}']
                        ema_long = current[f'ema_{self.ema_periods[i+1]}']
                        
                        if ema_short > ema_long:
                            ema_buy += 1
                        else:
                            ema_sell += 1
                
                # Price relative to shortest EMA
                ema_9 = current[f'ema_{self.ema_periods[0]}']
                indicators['ema_9'] = round(ema_9, 2)
                
                if price > ema_9:
                    ema_buy += 1
                else:
                    ema_sell += 1
                
                # Calculate EMA score
                if ema_buy > ema_sell:
                    buy_signals += 20
                    indicators['ema_trend'] = 'bullish'
                elif ema_sell > ema_buy:
                    sell_signals += 20
                    indicators['ema_trend'] = 'bearish'
                else:
                    indicators['ema_trend'] = 'neutral'
                
                total_weight += 20
            
            # Bollinger Bands Analysis (Weight: 15)
            if 'bb_upper' in current and 'bb_lower' in current:
                price = current['close']
                bb_upper = current['bb_upper']
                bb_lower = current['bb_lower']
                bb_pband = current['bb_pband']
                
                indicators['bb_position'] = round(bb_pband, 2)
                
                if price <= bb_lower:
                    buy_signals += 15
                    indicators['bb_signal'] = 'lower_band'
                elif price >= bb_upper:
                    sell_signals += 15
                    indicators['bb_signal'] = 'upper_band'
                else:
                    indicators['bb_signal'] = 'middle'
                
                total_weight += 15
            
            # Volume Analysis (Weight: 10)
            if 'volume_ratio' in current:
                volume_ratio = current['volume_ratio']
                indicators['volume_ratio'] = round(volume_ratio, 2)
                
                if volume_ratio > self.volume_spike_threshold:
                    # High volume confirms the trend
                    if buy_signals > sell_signals:
                        buy_signals += 10
                    else:
                        sell_signals += 10
                    indicators['volume_signal'] = 'high'
                else:
                    indicators['volume_signal'] = 'normal'
                
                total_weight += 10
            
            # ADX Trend Strength (Weight: 10)
            if 'adx' in current:
                adx = current['adx']
                indicators['adx'] = round(adx, 2)
                
                if adx > 25:  # Strong trend
                    if current.get('adx_pos', 0) > current.get('adx_neg', 0):
                        buy_signals += 10
                        indicators['adx_trend'] = 'strong_uptrend'
                    else:
                        sell_signals += 10
                        indicators['adx_trend'] = 'strong_downtrend'
                else:
                    indicators['adx_trend'] = 'weak'
                
                total_weight += 10
            
            # Calculate final signal
            if total_weight == 0:
                return 'HOLD', 0, indicators
            
            buy_strength = int((buy_signals / total_weight) * 100)
            sell_strength = int((sell_signals / total_weight) * 100)
            
            # Determine signal type
            signal_type = 'HOLD'
            strength = 0
            
            min_strength = 60  # Minimum strength to generate signal
            
            if buy_strength > sell_strength and buy_strength >= min_strength:
                signal_type = 'BUY'
                strength = buy_strength
            elif sell_strength > buy_strength and sell_strength >= min_strength:
                signal_type = 'SELL'
                strength = sell_strength
            else:
                signal_type = 'HOLD'
                strength = max(buy_strength, sell_strength)
            
            self.logger.info(
                f"Signal for {symbol}: {signal_type} (Strength: {strength}%) | "
                f"Buy: {buy_strength}%, Sell: {sell_strength}%"
            )
            
            return signal_type, strength, indicators
            
        except Exception as e:
            self.logger.error(f"Error generating signal for {symbol}: {e}", exc_info=True)
            return 'HOLD', 0, {}
    
    def analyze_multiple_timeframes(self, dataframes: Dict[str, pd.DataFrame], 
                                   symbol: str) -> Dict:
        """
        Analyze multiple timeframes for confluence
        
        Args:
            dataframes: Dictionary mapping timeframes to DataFrames
            symbol: Trading pair symbol
        
        Returns:
            Dictionary with multi-timeframe analysis
        """
        results = {}
        
        for timeframe, df in dataframes.items():
            df_with_indicators = self.calculate_all_indicators(df)
            signal, strength, indicators = self.generate_signal(df_with_indicators, symbol)
            
            results[timeframe] = {
                'signal': signal,
                'strength': strength,
                'indicators': indicators
            }
        
        # Determine overall signal based on confluence
        buy_count = sum(1 for r in results.values() if r['signal'] == 'BUY')
        sell_count = sum(1 for r in results.values() if r['signal'] == 'SELL')
        
        overall_signal = 'HOLD'
        if buy_count > sell_count and buy_count >= len(results) * 0.6:
            overall_signal = 'BUY'
        elif sell_count > buy_count and sell_count >= len(results) * 0.6:
            overall_signal = 'SELL'
        
        results['overall'] = {
            'signal': overall_signal,
            'buy_timeframes': buy_count,
            'sell_timeframes': sell_count,
            'total_timeframes': len(results) - 1
        }
        
        return results


if __name__ == "__main__":
    # Test the analyzer
    from data_fetcher import DataFetcher
    
    fetcher = DataFetcher()
    df = fetcher.fetch_ohlcv('BTC/USDT', '15m', 500)
    
    if df is not None:
        analyzer = TechnicalAnalyzer()
        df_with_indicators = analyzer.calculate_all_indicators(df)
        
        print("Latest indicators:")
        print(df_with_indicators.iloc[-1][['close', 'rsi', 'macd', 'ema_9', 'ema_21']])
        
        signal, strength, indicators = analyzer.generate_signal(df_with_indicators, 'BTC/USDT')
        print(f"\nSignal: {signal} (Strength: {strength}%)")
        print(f"Indicators: {indicators}")
