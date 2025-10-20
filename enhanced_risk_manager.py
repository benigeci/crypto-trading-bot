"""
Enhanced Risk Manager with Dynamic Position Sizing and Capital Preservation
Advanced risk management with volatility-based sizing, circuit breakers, and real-time SL/TP
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from logger import setup_logger

logger = setup_logger('enhanced_risk_manager')


@dataclass
class Position:
    """Trading position with risk parameters"""
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    size: float  # in base currency
    stop_loss: float
    take_profit: List[float]  # Multiple TP levels
    entry_time: datetime
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    trailing_stop_active: bool = False
    highest_price: float = 0.0
    lowest_price: float = float('inf')
    
    def update_pnl(self, current_price: float):
        """Update unrealized PNL"""
        if self.side == 'long':
            self.unrealized_pnl = (current_price - self.entry_price) * self.size
            if current_price > self.highest_price:
                self.highest_price = current_price
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.size
            if current_price < self.lowest_price:
                self.lowest_price = current_price
    
    def get_pnl_pct(self) -> float:
        """Get PNL as percentage"""
        if self.entry_price == 0:
            return 0.0
        return (self.unrealized_pnl / (self.entry_price * self.size)) * 100


@dataclass
class RiskMetrics:
    """Real-time risk metrics"""
    total_exposure: float
    daily_pnl: float
    daily_pnl_pct: float
    max_drawdown: float
    current_drawdown: float
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    var_95: float  # Value at Risk 95%
    circuit_breaker_active: bool
    risk_score: float  # 0-100, higher = more risk


class EnhancedRiskManager:
    """
    Enhanced risk management with dynamic position sizing and capital preservation
    """
    
    def __init__(
        self,
        initial_capital: float,
        max_position_size_pct: float = 10.0,
        max_daily_loss_pct: float = 5.0,
        max_drawdown_pct: float = 20.0,
        use_kelly_criterion: bool = True,
        kelly_fraction: float = 0.25,
        enable_trailing_stop: bool = True,
        trailing_stop_pct: float = 1.0
    ):
        """
        Initialize enhanced risk manager
        
        Args:
            initial_capital: Starting capital
            max_position_size_pct: Maximum position size as % of capital
            max_daily_loss_pct: Maximum daily loss as % of capital
            max_drawdown_pct: Maximum drawdown as % of peak capital
            use_kelly_criterion: Use Kelly Criterion for position sizing
            kelly_fraction: Fraction of Kelly to use (0.25 = 1/4 Kelly)
            enable_trailing_stop: Enable trailing stop-loss
            trailing_stop_pct: Trailing stop distance as % of price
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        
        self.max_position_size_pct = max_position_size_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        
        self.use_kelly_criterion = use_kelly_criterion
        self.kelly_fraction = kelly_fraction
        
        self.enable_trailing_stop = enable_trailing_stop
        self.trailing_stop_pct = trailing_stop_pct
        
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        
        self.daily_start_capital = initial_capital
        self.day_start_date = datetime.now().date()
        
        self.circuit_breaker_active = False
        self.circuit_breaker_until: Optional[datetime] = None
        
        self.trade_history: List[Dict] = []
        
    def calculate_position_size_volatility(
        self,
        symbol: str,
        df: pd.DataFrame,
        risk_per_trade_pct: float = 2.0
    ) -> float:
        """
        Calculate position size based on volatility (ATR)
        
        Args:
            symbol: Trading pair
            df: DataFrame with price data and ATR
            risk_per_trade_pct: Risk per trade as % of capital
            
        Returns:
            Position size in base currency
        """
        try:
            if 'atr' not in df.columns:
                logger.warning(f"ATR not available for {symbol}, using fixed size")
                return self.calculate_fixed_position_size()
            
            current_price = df['close'].iloc[-1]
            atr = df['atr'].iloc[-1]
            
            if atr == 0 or current_price == 0:
                return self.calculate_fixed_position_size()
            
            # Risk amount in USDT
            risk_amount = self.current_capital * (risk_per_trade_pct / 100)
            
            # ATR-based stop distance (2x ATR)
            stop_distance = atr * 2
            stop_distance_pct = (stop_distance / current_price) * 100
            
            # Position size = Risk Amount / Stop Distance
            position_size_usd = risk_amount / (stop_distance_pct / 100)
            
            # Convert to base currency
            position_size = position_size_usd / current_price
            
            # Apply maximum position size limit
            max_position_usd = self.current_capital * (self.max_position_size_pct / 100)
            if position_size_usd > max_position_usd:
                position_size = max_position_usd / current_price
                logger.info(f"Position size capped at {self.max_position_size_pct}% of capital")
            
            logger.debug(
                f"Volatility-based sizing: {position_size:.8f} {symbol.split('/')[0]} "
                f"(ATR: {atr:.2f}, Stop: {stop_distance_pct:.2f}%)"
            )
            
            return position_size
            
        except Exception as e:
            logger.exception(f"Error calculating volatility-based position size: {e}")
            return self.calculate_fixed_position_size()
    
    def calculate_kelly_position_size(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        Calculate position size using Kelly Criterion
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average win amount
            avg_loss: Average loss amount (positive)
            
        Returns:
            Position size as % of capital
        """
        try:
            if avg_loss == 0 or win_rate == 0:
                return self.max_position_size_pct / 2
            
            # Kelly formula: f = (bp - q) / b
            # where b = avg_win/avg_loss, p = win_rate, q = 1-p
            win_loss_ratio = avg_win / avg_loss
            kelly_pct = (win_loss_ratio * win_rate - (1 - win_rate)) / win_loss_ratio
            
            # Apply Kelly fraction for safety
            kelly_pct *= self.kelly_fraction
            
            # Clamp between 1% and max position size
            kelly_pct = max(1.0, min(kelly_pct * 100, self.max_position_size_pct))
            
            logger.debug(
                f"Kelly sizing: {kelly_pct:.2f}% "
                f"(WR: {win_rate:.2%}, W/L: {win_loss_ratio:.2f})"
            )
            
            return kelly_pct
            
        except Exception as e:
            logger.exception(f"Error calculating Kelly position size: {e}")
            return self.max_position_size_pct / 2
    
    def calculate_fixed_position_size(self) -> float:
        """Calculate fixed position size"""
        return self.current_capital * (self.max_position_size_pct / 100)
    
    def calculate_dynamic_position_size(
        self,
        symbol: str,
        df: pd.DataFrame,
        signal_strength: float = 50.0,
        signal_confidence: float = 0.5
    ) -> float:
        """
        Calculate dynamic position size combining multiple factors
        
        Args:
            symbol: Trading pair
            df: DataFrame with price data
            signal_strength: Signal strength 0-100
            signal_confidence: Signal confidence 0-1
            
        Returns:
            Position size in base currency
        """
        try:
            current_price = df['close'].iloc[-1]
            
            # 1. Base size from volatility
            base_size = self.calculate_position_size_volatility(symbol, df)
            
            # 2. Adjust for signal strength (50 = neutral, 100 = strong)
            strength_multiplier = (signal_strength / 50.0) ** 0.5  # 0.7 to 1.4
            
            # 3. Adjust for signal confidence
            confidence_multiplier = 0.5 + (signal_confidence * 0.5)  # 0.5 to 1.0
            
            # 4. Adjust for current drawdown
            current_dd = self.get_current_drawdown_pct()
            if current_dd > self.max_drawdown_pct / 2:
                dd_multiplier = 0.5  # Reduce size in drawdown
            else:
                dd_multiplier = 1.0
            
            # 5. Adjust for daily P&L
            daily_pnl_pct = self.get_daily_pnl_pct()
            if daily_pnl_pct < -self.max_daily_loss_pct / 2:
                pnl_multiplier = 0.5  # Reduce size after losses
            elif daily_pnl_pct > self.max_daily_loss_pct:
                pnl_multiplier = 1.2  # Increase size after wins
            else:
                pnl_multiplier = 1.0
            
            # 6. Apply Kelly sizing if enabled
            if self.use_kelly_criterion and len(self.closed_positions) >= 10:
                win_rate, avg_win, avg_loss = self.calculate_win_statistics()
                kelly_pct = self.calculate_kelly_position_size(win_rate, avg_win, avg_loss)
                kelly_multiplier = kelly_pct / self.max_position_size_pct
            else:
                kelly_multiplier = 1.0
            
            # Combine all multipliers
            final_multiplier = (
                strength_multiplier *
                confidence_multiplier *
                dd_multiplier *
                pnl_multiplier *
                kelly_multiplier
            )
            
            position_size = base_size * final_multiplier
            
            # Ensure minimum and maximum limits
            min_size = (self.current_capital * 0.01) / current_price  # 1% minimum
            max_size = (self.current_capital * self.max_position_size_pct / 100) / current_price
            
            position_size = max(min_size, min(position_size, max_size))
            
            logger.info(
                f"Dynamic position size: {position_size:.8f} "
                f"(multipliers: str={strength_multiplier:.2f}, "
                f"conf={confidence_multiplier:.2f}, dd={dd_multiplier:.2f}, "
                f"pnl={pnl_multiplier:.2f}, kelly={kelly_multiplier:.2f})"
            )
            
            return position_size
            
        except Exception as e:
            logger.exception(f"Error calculating dynamic position size: {e}")
            return self.calculate_fixed_position_size() / df['close'].iloc[-1]
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        df: pd.DataFrame,
        side: str = 'long'
    ) -> float:
        """
        Calculate dynamic stop-loss based on ATR
        
        Args:
            entry_price: Entry price
            df: DataFrame with ATR
            side: 'long' or 'short'
            
        Returns:
            Stop-loss price
        """
        try:
            if 'atr' in df.columns:
                atr = df['atr'].iloc[-1]
                stop_distance = atr * 2  # 2x ATR
            else:
                # Fallback: 2% stop
                stop_distance = entry_price * 0.02
            
            # Ensure stop is between 1% and 5%
            min_stop = entry_price * 0.01
            max_stop = entry_price * 0.05
            stop_distance = max(min_stop, min(stop_distance, max_stop))
            
            if side == 'long':
                stop_loss = entry_price - stop_distance
            else:
                stop_loss = entry_price + stop_distance
            
            logger.debug(f"Stop-loss calculated: {stop_loss:.2f} (distance: {stop_distance:.2f})")
            return stop_loss
            
        except Exception as e:
            logger.exception(f"Error calculating stop-loss: {e}")
            return entry_price * 0.98 if side == 'long' else entry_price * 1.02
    
    def calculate_take_profit_levels(
        self,
        entry_price: float,
        stop_loss: float,
        side: str = 'long',
        levels: int = 3
    ) -> List[float]:
        """
        Calculate multiple take-profit levels based on risk
        
        Args:
            entry_price: Entry price
            stop_loss: Stop-loss price
            side: 'long' or 'short'
            levels: Number of TP levels
            
        Returns:
            List of take-profit prices
        """
        try:
            risk = abs(entry_price - stop_loss)
            
            # TP at 2x, 3x, 5x risk
            risk_multiples = [2, 3, 5][:levels]
            
            take_profits = []
            for multiple in risk_multiples:
                if side == 'long':
                    tp = entry_price + (risk * multiple)
                else:
                    tp = entry_price - (risk * multiple)
                take_profits.append(tp)
            
            logger.debug(f"Take-profit levels: {take_profits}")
            return take_profits
            
        except Exception as e:
            logger.exception(f"Error calculating take-profit levels: {e}")
            return [entry_price * 1.04] if side == 'long' else [entry_price * 0.96]
    
    def update_trailing_stop(
        self,
        symbol: str,
        current_price: float
    ) -> Optional[float]:
        """
        Update trailing stop for a position
        
        Args:
            symbol: Trading pair
            current_price: Current market price
            
        Returns:
            New stop-loss price or None
        """
        if symbol not in self.positions or not self.enable_trailing_stop:
            return None
        
        position = self.positions[symbol]
        
        if not position.trailing_stop_active:
            # Activate trailing stop after profit threshold (e.g., 2% profit)
            profit_pct = position.get_pnl_pct()
            if profit_pct >= 2.0:
                position.trailing_stop_active = True
                logger.info(f"Trailing stop activated for {symbol} at {profit_pct:.2f}% profit")
        
        if position.trailing_stop_active:
            if position.side == 'long':
                # Trail stop up
                new_stop = position.highest_price * (1 - self.trailing_stop_pct / 100)
                if new_stop > position.stop_loss:
                    old_stop = position.stop_loss
                    position.stop_loss = new_stop
                    logger.info(
                        f"Trailing stop updated for {symbol}: "
                        f"{old_stop:.2f} → {new_stop:.2f}"
                    )
                    return new_stop
            else:
                # Trail stop down
                new_stop = position.lowest_price * (1 + self.trailing_stop_pct / 100)
                if new_stop < position.stop_loss:
                    old_stop = position.stop_loss
                    position.stop_loss = new_stop
                    logger.info(
                        f"Trailing stop updated for {symbol}: "
                        f"{old_stop:.2f} → {new_stop:.2f}"
                    )
                    return new_stop
        
        return None
    
    def check_circuit_breaker(self) -> bool:
        """
        Check if circuit breaker should be triggered
        
        Returns:
            True if circuit breaker is active
        """
        # Check if already active and expired
        if self.circuit_breaker_active:
            if self.circuit_breaker_until and datetime.now() > self.circuit_breaker_until:
                self.circuit_breaker_active = False
                self.circuit_breaker_until = None
                logger.info("Circuit breaker deactivated")
            else:
                return True
        
        # Check daily loss limit
        daily_pnl_pct = self.get_daily_pnl_pct()
        if daily_pnl_pct <= -self.max_daily_loss_pct:
            self.activate_circuit_breaker("Daily loss limit reached", hours=24)
            return True
        
        # Check max drawdown
        current_dd = self.get_current_drawdown_pct()
        if current_dd >= self.max_drawdown_pct:
            self.activate_circuit_breaker("Maximum drawdown reached", hours=48)
            return True
        
        # Check consecutive losses
        if len(self.closed_positions) >= 5:
            last_5 = self.closed_positions[-5:]
            consecutive_losses = all(p.realized_pnl < 0 for p in last_5)
            if consecutive_losses:
                self.activate_circuit_breaker("5 consecutive losses", hours=12)
                return True
        
        return False
    
    def activate_circuit_breaker(self, reason: str, hours: int = 24):
        """
        Activate circuit breaker to stop trading
        
        Args:
            reason: Reason for activation
            hours: Duration in hours
        """
        self.circuit_breaker_active = True
        self.circuit_breaker_until = datetime.now() + timedelta(hours=hours)
        
        logger.warning(
            f"🔴 CIRCUIT BREAKER ACTIVATED: {reason} "
            f"(until {self.circuit_breaker_until.strftime('%Y-%m-%d %H:%M')})"
        )
        
        # Close all positions at market
        for symbol in list(self.positions.keys()):
            logger.warning(f"Closing position {symbol} due to circuit breaker")
            # Note: Actual closing would happen in main trading logic
    
    def get_daily_pnl_pct(self) -> float:
        """Get daily P&L as percentage"""
        if self.daily_start_capital == 0:
            return 0.0
        return ((self.current_capital - self.daily_start_capital) / self.daily_start_capital) * 100
    
    def get_current_drawdown_pct(self) -> float:
        """Get current drawdown as percentage"""
        if self.peak_capital == 0:
            return 0.0
        return ((self.peak_capital - self.current_capital) / self.peak_capital) * 100
    
    def calculate_win_statistics(self) -> Tuple[float, float, float]:
        """
        Calculate win rate and average win/loss
        
        Returns:
            Tuple of (win_rate, avg_win, avg_loss)
        """
        if not self.closed_positions:
            return 0.5, 0.0, 0.0
        
        wins = [p.realized_pnl for p in self.closed_positions if p.realized_pnl > 0]
        losses = [abs(p.realized_pnl) for p in self.closed_positions if p.realized_pnl < 0]
        
        win_rate = len(wins) / len(self.closed_positions)
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0
        
        return win_rate, avg_win, avg_loss
    
    def get_risk_metrics(self) -> RiskMetrics:
        """
        Calculate comprehensive risk metrics
        
        Returns:
            RiskMetrics object
        """
        try:
            # Total exposure
            total_exposure = sum(
                p.entry_price * p.size for p in self.positions.values()
            )
            exposure_pct = (total_exposure / self.current_capital) * 100 if self.current_capital > 0 else 0
            
            # Daily P&L
            daily_pnl = self.current_capital - self.daily_start_capital
            daily_pnl_pct = self.get_daily_pnl_pct()
            
            # Drawdown
            current_dd = self.get_current_drawdown_pct()
            
            # Performance metrics
            if len(self.closed_positions) >= 10:
                win_rate, avg_win, avg_loss = self.calculate_win_statistics()
                profit_factor = (avg_win * win_rate) / (avg_loss * (1 - win_rate)) if avg_loss > 0 else 0
                
                # Sharpe ratio (simplified)
                returns = [p.realized_pnl / self.initial_capital for p in self.closed_positions]
                if len(returns) > 1:
                    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
                else:
                    sharpe = 0.0
                
                # Value at Risk (95%)
                var_95 = np.percentile([p.realized_pnl for p in self.closed_positions], 5)
            else:
                win_rate = 0.5
                profit_factor = 0.0
                sharpe = 0.0
                var_95 = 0.0
            
            # Risk score (0-100, higher = more risk)
            risk_score = (
                exposure_pct * 0.3 +
                abs(daily_pnl_pct) * 5 * 0.3 +
                current_dd * 2 * 0.4
            )
            risk_score = min(100, max(0, risk_score))
            
            return RiskMetrics(
                total_exposure=exposure_pct,
                daily_pnl=daily_pnl,
                daily_pnl_pct=daily_pnl_pct,
                max_drawdown=self.max_drawdown_pct,
                current_drawdown=current_dd,
                win_rate=win_rate,
                profit_factor=profit_factor,
                sharpe_ratio=sharpe,
                var_95=var_95,
                circuit_breaker_active=self.circuit_breaker_active,
                risk_score=risk_score
            )
            
        except Exception as e:
            logger.exception(f"Error calculating risk metrics: {e}")
            return RiskMetrics(
                total_exposure=0, daily_pnl=0, daily_pnl_pct=0,
                max_drawdown=0, current_drawdown=0, win_rate=0,
                profit_factor=0, sharpe_ratio=0, var_95=0,
                circuit_breaker_active=False, risk_score=0
            )
    
    def can_open_position(self, symbol: str) -> Tuple[bool, str]:
        """
        Check if new position can be opened
        
        Returns:
            Tuple of (can_open, reason)
        """
        # Circuit breaker check
        if self.check_circuit_breaker():
            return False, "Circuit breaker active"
        
        # Daily loss limit
        if self.get_daily_pnl_pct() <= -self.max_daily_loss_pct:
            return False, "Daily loss limit reached"
        
        # Drawdown limit
        if self.get_current_drawdown_pct() >= self.max_drawdown_pct:
            return False, "Maximum drawdown reached"
        
        # Check if already have position
        if symbol in self.positions:
            return False, "Position already open for this symbol"
        
        # Check max concurrent positions
        max_positions = 5  # Could be configurable
        if len(self.positions) >= max_positions:
            return False, f"Maximum {max_positions} positions already open"
        
        return True, "OK"
    
    def reset_daily_metrics(self):
        """Reset daily metrics at day start"""
        current_date = datetime.now().date()
        if current_date != self.day_start_date:
            self.daily_start_capital = self.current_capital
            self.day_start_date = current_date
            logger.info(f"Daily metrics reset. Starting capital: ${self.current_capital:.2f}")


# Example usage
if __name__ == '__main__':
    # Initialize risk manager
    risk_mgr = EnhancedRiskManager(
        initial_capital=10000,
        max_position_size_pct=10,
        max_daily_loss_pct=5,
        use_kelly_criterion=True,
        enable_trailing_stop=True
    )
    
    # Create sample data
    df = pd.DataFrame({
        'close': [100, 101, 102, 103, 104],
        'atr': [2, 2.1, 2.0, 1.9, 2.1]
    })
    
    # Calculate position size
    size = risk_mgr.calculate_dynamic_position_size(
        'BTC/USDT',
        df,
        signal_strength=75,
        signal_confidence=0.8
    )
    print(f"Position size: {size:.8f} BTC")
    
    # Calculate stop-loss and take-profit
    entry_price = 104
    stop_loss = risk_mgr.calculate_stop_loss(entry_price, df, 'long')
    take_profits = risk_mgr.calculate_take_profit_levels(entry_price, stop_loss, 'long')
    
    print(f"Entry: ${entry_price}")
    print(f"Stop Loss: ${stop_loss:.2f}")
    print(f"Take Profits: {[f'${tp:.2f}' for tp in take_profits]}")
    
    # Get risk metrics
    metrics = risk_mgr.get_risk_metrics()
    print(f"\nRisk Score: {metrics.risk_score:.1f}/100")
    print(f"Daily P&L: {metrics.daily_pnl_pct:.2f}%")
    print(f"Drawdown: {metrics.current_drawdown:.2f}%")
