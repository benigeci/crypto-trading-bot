"""
Adaptive Strategy Engine with Dynamic Thresholds and Ensemble Logic
Combines technical indicators, ML predictions, and market sentiment with adaptive weighting
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import asyncio
from logger import setup_logger

logger = setup_logger('adaptive_strategy')


class SignalStrength(Enum):
    """Signal strength levels"""
    STRONG_BUY = 5
    BUY = 4
    WEAK_BUY = 3
    NEUTRAL = 2
    WEAK_SELL = 1
    SELL = 0
    STRONG_SELL = -1


@dataclass
class MarketRegime:
    """Market regime classification"""
    volatility: str  # 'low', 'medium', 'high'
    trend: str  # 'bullish', 'bearish', 'ranging'
    volume: str  # 'low', 'normal', 'high'
    confidence: float  # 0-1


@dataclass
class AdaptiveSignal:
    """Adaptive trading signal with metadata"""
    action: str  # 'BUY', 'SELL', 'HOLD'
    strength: float  # 0-100
    confidence: float  # 0-1
    regime: MarketRegime
    components: Dict[str, float]  # Individual signal contributions
    reasoning: List[str]  # Human-readable explanations


class AdaptiveStrategyEngine:
    """
    Advanced strategy engine with adaptive thresholds and ensemble decision-making
    """
    
    def __init__(
        self,
        base_rsi_oversold: float = 30,
        base_rsi_overbought: float = 70,
        volatility_adjustment: bool = True,
        ml_enabled: bool = True
    ):
        """
        Initialize adaptive strategy engine
        
        Args:
            base_rsi_oversold: Base RSI oversold level
            base_rsi_overbought: Base RSI overbought level
            volatility_adjustment: Enable volatility-based threshold adjustment
            ml_enabled: Enable ML prediction integration
        """
        self.base_rsi_oversold = base_rsi_oversold
        self.base_rsi_overbought = base_rsi_overbought
        self.volatility_adjustment = volatility_adjustment
        self.ml_enabled = ml_enabled
        
        # Component weights (will be adjusted based on market regime)
        self.base_weights = {
            'rsi': 1.0,
            'macd': 1.5,
            'bollinger': 1.2,
            'ema_trend': 1.3,
            'volume': 1.0,
            'stochastic': 0.8,
            'atr': 0.7,
            'ml_prediction': 2.0 if ml_enabled else 0.0
        }
        
        self.current_weights = self.base_weights.copy()
        self.regime_history: List[MarketRegime] = []
        
    def detect_market_regime(self, df: pd.DataFrame) -> MarketRegime:
        """
        Detect current market regime
        
        Args:
            df: DataFrame with OHLCV and indicators
            
        Returns:
            MarketRegime classification
        """
        try:
            # Calculate volatility (ATR-based)
            if 'atr' in df.columns:
                atr = df['atr'].iloc[-1]
                avg_atr = df['atr'].rolling(20).mean().iloc[-1]
                volatility_ratio = atr / avg_atr if avg_atr > 0 else 1.0
                
                if volatility_ratio > 1.5:
                    volatility = 'high'
                elif volatility_ratio < 0.7:
                    volatility = 'low'
                else:
                    volatility = 'medium'
            else:
                # Fallback: use close price std
                returns_std = df['close'].pct_change().tail(20).std()
                if returns_std > 0.03:
                    volatility = 'high'
                elif returns_std < 0.01:
                    volatility = 'low'
                else:
                    volatility = 'medium'
            
            # Detect trend
            if 'ema_12' in df.columns and 'ema_26' in df.columns:
                ema_fast = df['ema_12'].iloc[-1]
                ema_slow = df['ema_26'].iloc[-1]
                ema_diff_pct = (ema_fast - ema_slow) / ema_slow * 100
                
                if ema_diff_pct > 2:
                    trend = 'bullish'
                elif ema_diff_pct < -2:
                    trend = 'bearish'
                else:
                    trend = 'ranging'
            else:
                # Fallback: simple price trend
                sma_20 = df['close'].rolling(20).mean().iloc[-1]
                current_price = df['close'].iloc[-1]
                
                if current_price > sma_20 * 1.02:
                    trend = 'bullish'
                elif current_price < sma_20 * 0.98:
                    trend = 'bearish'
                else:
                    trend = 'ranging'
            
            # Analyze volume
            if 'volume' in df.columns:
                current_volume = df['volume'].iloc[-1]
                avg_volume = df['volume'].rolling(20).mean().iloc[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
                
                if volume_ratio > 1.5:
                    volume = 'high'
                elif volume_ratio < 0.7:
                    volume = 'low'
                else:
                    volume = 'normal'
            else:
                volume = 'normal'
            
            # Calculate confidence based on indicator availability
            available_indicators = sum([
                'atr' in df.columns,
                'ema_12' in df.columns,
                'volume' in df.columns,
                'rsi' in df.columns
            ])
            confidence = available_indicators / 4.0
            
            regime = MarketRegime(
                volatility=volatility,
                trend=trend,
                volume=volume,
                confidence=confidence
            )
            
            self.regime_history.append(regime)
            if len(self.regime_history) > 100:
                self.regime_history = self.regime_history[-100:]
            
            logger.debug(f"Market regime: {regime}")
            return regime
            
        except Exception as e:
            logger.exception(f"Error detecting market regime: {e}")
            return MarketRegime('medium', 'ranging', 'normal', 0.5)
    
    def adjust_thresholds_for_volatility(
        self, 
        regime: MarketRegime
    ) -> Tuple[float, float]:
        """
        Adjust RSI thresholds based on market volatility
        
        Args:
            regime: Current market regime
            
        Returns:
            Tuple of (oversold_threshold, overbought_threshold)
        """
        if not self.volatility_adjustment:
            return self.base_rsi_oversold, self.base_rsi_overbought
        
        # High volatility: widen thresholds (20-80)
        # Low volatility: tighten thresholds (35-65)
        if regime.volatility == 'high':
            oversold = max(20, self.base_rsi_oversold - 10)
            overbought = min(80, self.base_rsi_overbought + 10)
        elif regime.volatility == 'low':
            oversold = min(35, self.base_rsi_oversold + 5)
            overbought = max(65, self.base_rsi_overbought - 5)
        else:
            oversold = self.base_rsi_oversold
            overbought = self.base_rsi_overbought
        
        logger.debug(f"Adjusted RSI thresholds: {oversold}/{overbought} (volatility: {regime.volatility})")
        return oversold, overbought
    
    def adjust_weights_for_regime(self, regime: MarketRegime):
        """
        Adjust component weights based on market regime
        
        Args:
            regime: Current market regime
        """
        weights = self.base_weights.copy()
        
        # High volatility: trust momentum indicators more
        if regime.volatility == 'high':
            weights['macd'] *= 1.3
            weights['rsi'] *= 0.8
            weights['bollinger'] *= 1.2
        
        # Low volatility: trust mean reversion more
        elif regime.volatility == 'low':
            weights['rsi'] *= 1.3
            weights['bollinger'] *= 1.4
            weights['macd'] *= 0.8
        
        # Trending market: trust trend indicators
        if regime.trend in ['bullish', 'bearish']:
            weights['ema_trend'] *= 1.4
            weights['macd'] *= 1.2
        
        # Ranging market: trust oscillators
        elif regime.trend == 'ranging':
            weights['rsi'] *= 1.3
            weights['stochastic'] *= 1.2
        
        # High volume: increase all weights
        if regime.volume == 'high':
            weights['volume'] *= 1.5
            for key in weights:
                if key != 'volume':
                    weights[key] *= 1.1
        
        # Normalize weights
        total_weight = sum(weights.values())
        self.current_weights = {k: v / total_weight for k, v in weights.items()}
        
        logger.debug(f"Adjusted weights: {self.current_weights}")
    
    def calculate_rsi_signal(
        self, 
        df: pd.DataFrame, 
        oversold: float, 
        overbought: float
    ) -> Tuple[float, str]:
        """Calculate RSI-based signal"""
        if 'rsi' not in df.columns:
            return 0.0, "RSI not available"
        
        rsi = df['rsi'].iloc[-1]
        
        if rsi < oversold:
            signal = (oversold - rsi) / oversold  # 0 to 1
            reason = f"RSI oversold: {rsi:.1f} < {oversold}"
        elif rsi > overbought:
            signal = -(rsi - overbought) / (100 - overbought)  # 0 to -1
            reason = f"RSI overbought: {rsi:.1f} > {overbought}"
        else:
            # Neutral zone: slight bias
            mid = (oversold + overbought) / 2
            signal = (mid - rsi) / (overbought - oversold) * 0.5
            reason = f"RSI neutral: {rsi:.1f}"
        
        return signal, reason
    
    def calculate_macd_signal(self, df: pd.DataFrame) -> Tuple[float, str]:
        """Calculate MACD-based signal"""
        if 'macd' not in df.columns or 'macd_signal' not in df.columns:
            return 0.0, "MACD not available"
        
        macd = df['macd'].iloc[-1]
        macd_signal = df['macd_signal'].iloc[-1]
        macd_prev = df['macd'].iloc[-2]
        signal_prev = df['macd_signal'].iloc[-2]
        
        # Bullish crossover
        if macd > macd_signal and macd_prev <= signal_prev:
            signal = 0.8
            reason = "MACD bullish crossover"
        # Bearish crossover
        elif macd < macd_signal and macd_prev >= signal_prev:
            signal = -0.8
            reason = "MACD bearish crossover"
        # Strong momentum
        elif macd > macd_signal:
            diff = abs(macd - macd_signal)
            signal = min(0.6, diff * 10)
            reason = f"MACD bullish: {diff:.4f}"
        else:
            diff = abs(macd - macd_signal)
            signal = -min(0.6, diff * 10)
            reason = f"MACD bearish: {diff:.4f}"
        
        return signal, reason
    
    def calculate_bollinger_signal(self, df: pd.DataFrame) -> Tuple[float, str]:
        """Calculate Bollinger Bands signal"""
        if 'bb_upper' not in df.columns or 'bb_lower' not in df.columns:
            return 0.0, "Bollinger Bands not available"
        
        close = df['close'].iloc[-1]
        bb_upper = df['bb_upper'].iloc[-1]
        bb_middle = df['bb_middle'].iloc[-1]
        bb_lower = df['bb_lower'].iloc[-1]
        
        bb_range = bb_upper - bb_lower
        if bb_range == 0:
            return 0.0, "Bollinger Bands collapsed"
        
        # Position within bands
        position = (close - bb_lower) / bb_range
        
        if position < 0.2:
            signal = 0.7
            reason = f"Price near lower BB: {position:.2%}"
        elif position > 0.8:
            signal = -0.7
            reason = f"Price near upper BB: {position:.2%}"
        elif position < 0.4:
            signal = 0.3
            reason = f"Price below middle BB: {position:.2%}"
        elif position > 0.6:
            signal = -0.3
            reason = f"Price above middle BB: {position:.2%}"
        else:
            signal = 0.0
            reason = f"Price in BB middle: {position:.2%}"
        
        return signal, reason
    
    def calculate_ema_trend_signal(self, df: pd.DataFrame) -> Tuple[float, str]:
        """Calculate EMA trend signal"""
        if 'ema_12' not in df.columns or 'ema_26' not in df.columns:
            return 0.0, "EMA not available"
        
        ema_fast = df['ema_12'].iloc[-1]
        ema_slow = df['ema_26'].iloc[-1]
        close = df['close'].iloc[-1]
        
        # EMA crossover
        ema_fast_prev = df['ema_12'].iloc[-2]
        ema_slow_prev = df['ema_26'].iloc[-2]
        
        if ema_fast > ema_slow and ema_fast_prev <= ema_slow_prev:
            signal = 0.9
            reason = "EMA bullish crossover"
        elif ema_fast < ema_slow and ema_fast_prev >= ema_slow_prev:
            signal = -0.9
            reason = "EMA bearish crossover"
        elif ema_fast > ema_slow:
            diff_pct = (ema_fast - ema_slow) / ema_slow * 100
            signal = min(0.7, diff_pct / 5)
            reason = f"EMA bullish: {diff_pct:.2f}%"
        else:
            diff_pct = (ema_slow - ema_fast) / ema_slow * 100
            signal = -min(0.7, diff_pct / 5)
            reason = f"EMA bearish: {diff_pct:.2f}%"
        
        return signal, reason
    
    def calculate_volume_signal(self, df: pd.DataFrame) -> Tuple[float, str]:
        """Calculate volume-based signal"""
        if 'volume' not in df.columns:
            return 0.0, "Volume not available"
        
        volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        
        if avg_volume == 0:
            return 0.0, "No volume data"
        
        volume_ratio = volume / avg_volume
        price_change = df['close'].pct_change().iloc[-1]
        
        # High volume with price increase = bullish
        # High volume with price decrease = bearish
        if volume_ratio > 1.5:
            if price_change > 0:
                signal = min(0.8, volume_ratio * 0.3)
                reason = f"High volume + price up: {volume_ratio:.2f}x"
            else:
                signal = -min(0.8, volume_ratio * 0.3)
                reason = f"High volume + price down: {volume_ratio:.2f}x"
        elif volume_ratio < 0.7:
            signal = 0.0
            reason = f"Low volume: {volume_ratio:.2f}x"
        else:
            signal = 0.0
            reason = f"Normal volume: {volume_ratio:.2f}x"
        
        return signal, reason
    
    async def generate_ensemble_signal(
        self, 
        df: pd.DataFrame,
        ml_prediction: Optional[Dict] = None
    ) -> AdaptiveSignal:
        """
        Generate ensemble trading signal combining all components
        
        Args:
            df: DataFrame with OHLCV and indicators
            ml_prediction: Optional ML prediction dict with 'signal' and 'confidence'
            
        Returns:
            AdaptiveSignal with action, strength, and reasoning
        """
        try:
            # Detect market regime
            regime = self.detect_market_regime(df)
            
            # Adjust weights for current regime
            self.adjust_weights_for_regime(regime)
            
            # Adjust RSI thresholds
            rsi_oversold, rsi_overbought = self.adjust_thresholds_for_volatility(regime)
            
            # Calculate individual signals
            signals = {}
            reasons = []
            
            # RSI
            rsi_signal, rsi_reason = self.calculate_rsi_signal(df, rsi_oversold, rsi_overbought)
            signals['rsi'] = rsi_signal
            reasons.append(rsi_reason)
            
            # MACD
            macd_signal, macd_reason = self.calculate_macd_signal(df)
            signals['macd'] = macd_signal
            reasons.append(macd_reason)
            
            # Bollinger Bands
            bb_signal, bb_reason = self.calculate_bollinger_signal(df)
            signals['bollinger'] = bb_signal
            reasons.append(bb_reason)
            
            # EMA Trend
            ema_signal, ema_reason = self.calculate_ema_trend_signal(df)
            signals['ema_trend'] = ema_signal
            reasons.append(ema_reason)
            
            # Volume
            volume_signal, volume_reason = self.calculate_volume_signal(df)
            signals['volume'] = volume_signal
            reasons.append(volume_reason)
            
            # ML Prediction
            if self.ml_enabled and ml_prediction:
                ml_signal = ml_prediction.get('signal', 0)  # -1 to 1
                ml_confidence = ml_prediction.get('confidence', 0.5)
                signals['ml_prediction'] = ml_signal * ml_confidence
                reasons.append(f"ML: {ml_signal:.2f} (conf: {ml_confidence:.2%})")
            else:
                signals['ml_prediction'] = 0.0
            
            # Calculate weighted ensemble score
            weighted_score = 0.0
            total_weight = 0.0
            
            for component, signal in signals.items():
                weight = self.current_weights.get(component, 0)
                weighted_score += signal * weight
                total_weight += weight
            
            if total_weight > 0:
                weighted_score /= total_weight
            
            # Normalize to 0-100 scale
            strength = (weighted_score + 1) * 50  # -1 to 1 → 0 to 100
            
            # Determine action
            if strength >= 65:
                action = 'BUY'
            elif strength <= 35:
                action = 'SELL'
            else:
                action = 'HOLD'
            
            # Calculate confidence based on signal agreement
            signal_values = [s for s in signals.values() if s != 0]
            if signal_values:
                signal_std = np.std(signal_values)
                confidence = max(0.5, 1.0 - signal_std)
            else:
                confidence = 0.5
            
            # Adjust confidence based on regime confidence
            confidence *= regime.confidence
            
            return AdaptiveSignal(
                action=action,
                strength=strength,
                confidence=confidence,
                regime=regime,
                components=signals,
                reasoning=reasons
            )
            
        except Exception as e:
            logger.exception(f"Error generating ensemble signal: {e}")
            return AdaptiveSignal(
                action='HOLD',
                strength=50.0,
                confidence=0.0,
                regime=MarketRegime('medium', 'ranging', 'normal', 0.0),
                components={},
                reasoning=[f"Error: {str(e)}"]
            )
    
    def get_regime_statistics(self) -> Dict:
        """Get statistics about market regime history"""
        if not self.regime_history:
            return {}
        
        volatility_counts = {}
        trend_counts = {}
        volume_counts = {}
        
        for regime in self.regime_history:
            volatility_counts[regime.volatility] = volatility_counts.get(regime.volatility, 0) + 1
            trend_counts[regime.trend] = trend_counts.get(regime.trend, 0) + 1
            volume_counts[regime.volume] = volume_counts.get(regime.volume, 0) + 1
        
        total = len(self.regime_history)
        
        return {
            'volatility_distribution': {k: v/total for k, v in volatility_counts.items()},
            'trend_distribution': {k: v/total for k, v in trend_counts.items()},
            'volume_distribution': {k: v/total for k, v in volume_counts.items()},
            'sample_size': total
        }


# Example usage
if __name__ == '__main__':
    # Create sample data
    dates = pd.date_range('2024-01-01', periods=100, freq='15min')
    df = pd.DataFrame({
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, 100),
        'rsi': np.random.randint(20, 80, 100),
        'macd': np.random.randn(100) * 0.1,
        'macd_signal': np.random.randn(100) * 0.1,
        'bb_upper': 105,
        'bb_middle': 100,
        'bb_lower': 95,
        'ema_12': np.random.randn(100).cumsum() + 100,
        'ema_26': np.random.randn(100).cumsum() + 99,
        'atr': np.random.rand(100) * 2
    }, index=dates)
    
    # Initialize engine
    engine = AdaptiveStrategyEngine(
        volatility_adjustment=True,
        ml_enabled=True
    )
    
    # Generate signal
    async def test():
        ml_pred = {'signal': 0.6, 'confidence': 0.75}
        signal = await engine.generate_ensemble_signal(df, ml_pred)
        
        print(f"\nAction: {signal.action}")
        print(f"Strength: {signal.strength:.1f}")
        print(f"Confidence: {signal.confidence:.2%}")
        print(f"\nMarket Regime:")
        print(f"  Volatility: {signal.regime.volatility}")
        print(f"  Trend: {signal.regime.trend}")
        print(f"  Volume: {signal.regime.volume}")
        print(f"\nComponent Signals:")
        for comp, value in signal.components.items():
            print(f"  {comp}: {value:.3f}")
        print(f"\nReasoning:")
        for reason in signal.reasoning:
            print(f"  - {reason}")
    
    asyncio.run(test())
