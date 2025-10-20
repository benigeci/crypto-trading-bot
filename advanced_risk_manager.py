"""
Advanced Risk Management Module
Implements Kelly Criterion, dynamic position sizing, portfolio heat, and circuit breakers
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from logger import get_logger


class AdvancedRiskManager:
    """
    Advanced risk management for live trading
    Protects capital through multiple layers of risk controls
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize advanced risk manager
        
        Args:
            config: Risk management configuration
        """
        self.logger = get_logger()
        self.config = config or {}
        
        # Portfolio limits
        self.max_positions = self.config.get('max_positions', 3)
        self.max_portfolio_risk = self.config.get('max_portfolio_risk', 0.10)  # 10%
        self.max_position_size = self.config.get('max_position_size', 0.20)  # 20% per trade
        
        # Daily/Weekly/Monthly loss limits
        self.max_daily_loss_percent = self.config.get('max_daily_loss', 0.02)  # 2%
        self.max_weekly_loss_percent = self.config.get('max_weekly_loss', 0.05)  # 5%
        self.max_monthly_loss_percent = self.config.get('max_monthly_loss', 0.10)  # 10%
        
        # Circuit breaker
        self.circuit_breaker_loss = self.config.get('circuit_breaker_loss', 0.05)  # 5% intraday
        self.circuit_breaker_active = False
        
        # Tracking
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.monthly_pnl = 0.0
        self.starting_balance_today = 0.0
        self.starting_balance_week = 0.0
        self.starting_balance_month = 0.0
        
        # Kelly Criterion parameters
        self.kelly_fraction = self.config.get('kelly_fraction', 0.25)  # Use 25% of Kelly
        
        # Trade history for statistics
        self.trade_history = []
        
        self.logger.info("Advanced Risk Manager initialized")
    
    def calculate_kelly_position_size(self, win_rate: float, avg_win: float, 
                                     avg_loss: float, balance: float) -> float:
        """
        Calculate optimal position size using Kelly Criterion
        
        Kelly % = W - [(1 - W) / R]
        Where:
        - W = Win rate
        - R = Avg Win / Avg Loss
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive number)
            balance: Current account balance
            
        Returns:
            Position size in dollars
        """
        if avg_loss == 0 or win_rate <= 0 or win_rate >= 1:
            self.logger.warning("Invalid Kelly Criterion parameters")
            return balance * 0.02  # Fallback to 2%
        
        # Calculate win/loss ratio
        win_loss_ratio = abs(avg_win / avg_loss)
        
        # Kelly formula
        kelly_percent = win_rate - ((1 - win_rate) / win_loss_ratio)
        
        # Apply safety fraction (typically 25-50% of full Kelly)
        fractional_kelly = kelly_percent * self.kelly_fraction
        
        # Ensure it's positive and reasonable
        fractional_kelly = max(0.01, min(0.20, fractional_kelly))
        
        position_size = balance * fractional_kelly
        
        self.logger.debug(
            f"Kelly Criterion: WR={win_rate:.1%}, W/L={win_loss_ratio:.2f}, "
            f"Kelly={kelly_percent:.1%}, Fractional={fractional_kelly:.1%}"
        )
        
        return position_size
    
    def calculate_volatility_adjusted_size(self, atr: float, price: float, 
                                           balance: float, risk_per_trade: float = 0.01) -> float:
        """
        Calculate position size based on volatility (ATR)
        
        Position Size = (Account Risk) / (ATR * Number of Units)
        
        Args:
            atr: Average True Range
            price: Current price
            balance: Account balance
            risk_per_trade: Risk percentage per trade (default 1%)
            
        Returns:
            Number of units to trade
        """
        if atr == 0 or price == 0:
            return 0
        
        # Risk amount in dollars
        risk_amount = balance * risk_per_trade
        
        # ATR as percentage of price
        atr_percent = atr / price
        
        # Position size
        position_value = risk_amount / atr_percent
        units = position_value / price
        
        self.logger.debug(
            f"Volatility-adjusted size: ATR={atr:.2f}, Risk=${risk_amount:.2f}, "
            f"Position=${position_value:.2f}"
        )
        
        return units
    
    def calculate_confidence_adjusted_size(self, base_size: float, confidence: float,
                                          min_confidence: float = 0.6) -> float:
        """
        Adjust position size based on ML model confidence
        
        Args:
            base_size: Base position size
            confidence: Model confidence (0-1)
            min_confidence: Minimum confidence threshold
            
        Returns:
            Adjusted position size
        """
        if confidence < min_confidence:
            return 0  # Don't trade if confidence too low
        
        # Scale position size by confidence
        # 60% confidence = 50% size
        # 80% confidence = 100% size
        # 100% confidence = 150% size
        confidence_multiplier = ((confidence - min_confidence) / (1 - min_confidence)) * 1.5
        confidence_multiplier = max(0.5, min(1.5, confidence_multiplier))
        
        adjusted_size = base_size * confidence_multiplier
        
        self.logger.debug(
            f"Confidence adjustment: {confidence:.1%} -> {confidence_multiplier:.2f}x"
        )
        
        return adjusted_size
    
    def check_portfolio_heat(self, open_positions: List[Dict], balance: float) -> bool:
        """
        Check if portfolio heat (total risk) is within limits
        
        Args:
            open_positions: List of open positions with risk amounts
            balance: Current account balance
            
        Returns:
            True if safe to add more positions
        """
        total_risk = sum(pos.get('risk_amount', 0) for pos in open_positions)
        portfolio_heat = total_risk / balance
        
        self.logger.debug(f"Portfolio heat: {portfolio_heat:.1%} (max: {self.max_portfolio_risk:.1%})")
        
        if portfolio_heat >= self.max_portfolio_risk:
            self.logger.warning(
                f"⚠️ Portfolio heat limit reached: {portfolio_heat:.1%} >= {self.max_portfolio_risk:.1%}"
            )
            return False
        
        return True
    
    def check_correlation_risk(self, symbol: str, open_positions: List[Dict],
                               correlation_threshold: float = 0.7) -> bool:
        """
        Check if new position would create excessive correlation risk
        
        Args:
            symbol: Symbol to check
            open_positions: Current open positions
            correlation_threshold: Max acceptable correlation
            
        Returns:
            True if safe to add position
        """
        # Simplified correlation check
        # In production, use historical correlation matrix
        
        # Extract base currency (e.g., BTC from BTC/USDT)
        base = symbol.split('/')[0]
        
        # Check if we already have positions in same asset
        same_asset_positions = [
            pos for pos in open_positions 
            if pos['symbol'].startswith(base)
        ]
        
        if len(same_asset_positions) > 0:
            self.logger.warning(
                f"⚠️ Correlation risk: Already have {len(same_asset_positions)} position(s) in {base}"
            )
            return False
        
        # Check for sector correlation (all cryptos are somewhat correlated)
        if len(open_positions) >= self.max_positions:
            self.logger.warning(
                f"⚠️ Max positions reached: {len(open_positions)}/{self.max_positions}"
            )
            return False
        
        return True
    
    def calculate_dynamic_stop_loss(self, entry_price: float, atr: float,
                                   atr_multiplier: float = 2.0,
                                   min_stop_percent: float = 0.02,
                                   max_stop_percent: float = 0.05) -> float:
        """
        Calculate dynamic stop loss based on ATR
        
        Args:
            entry_price: Entry price
            atr: Average True Range
            atr_multiplier: ATR multiplier (default 2.0)
            min_stop_percent: Minimum stop loss %
            max_stop_percent: Maximum stop loss %
            
        Returns:
            Stop loss price
        """
        # ATR-based stop
        atr_stop_distance = atr * atr_multiplier
        atr_stop_percent = atr_stop_distance / entry_price
        
        # Ensure within min/max bounds
        stop_percent = max(min_stop_percent, min(max_stop_percent, atr_stop_percent))
        
        stop_price = entry_price * (1 - stop_percent)
        
        self.logger.debug(
            f"Dynamic stop loss: {stop_percent:.1%} below entry (${stop_price:.2f})"
        )
        
        return stop_price
    
    def calculate_dynamic_take_profit(self, entry_price: float, atr: float,
                                     risk_reward_ratio: float = 2.0,
                                     volatility_adjusted: bool = True) -> List[float]:
        """
        Calculate dynamic take profit levels
        
        Args:
            entry_price: Entry price
            atr: Average True Range
            risk_reward_ratio: Risk/reward ratio
            volatility_adjusted: Adjust targets based on volatility
            
        Returns:
            List of take profit levels
        """
        # Base stop loss distance (2 ATR)
        stop_distance = atr * 2.0
        
        # Target distances based on R:R ratio
        targets = []
        
        if volatility_adjusted:
            # In high volatility, use wider targets
            atr_percent = atr / entry_price
            
            if atr_percent > 0.03:  # High volatility (>3%)
                multipliers = [1.5, 2.5, 4.0]
            else:  # Normal volatility
                multipliers = [2.0, 3.0, 5.0]
        else:
            multipliers = [risk_reward_ratio, risk_reward_ratio * 1.5, risk_reward_ratio * 2]
        
        for mult in multipliers:
            target_price = entry_price + (stop_distance * mult)
            targets.append(target_price)
        
        self.logger.debug(
            f"Dynamic take profit: ${targets[0]:.2f}, ${targets[1]:.2f}, ${targets[2]:.2f}"
        )
        
        return targets
    
    def check_daily_loss_limit(self, current_balance: float) -> bool:
        """
        Check if daily loss limit has been hit
        
        Args:
            current_balance: Current account balance
            
        Returns:
            True if trading allowed
        """
        if self.starting_balance_today == 0:
            self.starting_balance_today = current_balance
        
        daily_loss = (self.starting_balance_today - current_balance) / self.starting_balance_today
        
        if daily_loss >= self.max_daily_loss_percent:
            self.logger.error(
                f"🛑 DAILY LOSS LIMIT REACHED: {daily_loss:.1%} >= {self.max_daily_loss_percent:.1%}"
            )
            self.activate_circuit_breaker("Daily loss limit")
            return False
        
        return True
    
    def check_circuit_breaker(self, current_balance: float, starting_balance: float) -> bool:
        """
        Check if circuit breaker should activate
        
        Args:
            current_balance: Current balance
            starting_balance: Starting balance for the day
            
        Returns:
            True if trading allowed
        """
        if self.circuit_breaker_active:
            self.logger.warning("🛑 Circuit breaker is ACTIVE - No trading allowed")
            return False
        
        intraday_loss = (starting_balance - current_balance) / starting_balance
        
        if intraday_loss >= self.circuit_breaker_loss:
            self.logger.critical(
                f"🚨 CIRCUIT BREAKER ACTIVATED: {intraday_loss:.1%} loss!"
            )
            self.activate_circuit_breaker("Intraday loss threshold")
            return False
        
        return True
    
    def activate_circuit_breaker(self, reason: str):
        """
        Activate circuit breaker - stop all trading
        
        Args:
            reason: Reason for activation
        """
        self.circuit_breaker_active = True
        self.logger.critical(f"🚨🚨🚨 CIRCUIT BREAKER ACTIVATED: {reason} 🚨🚨🚨")
        
        # TODO: Send emergency alerts (Telegram, email, SMS)
        # TODO: Close all positions
        # TODO: Require manual reset
    
    def reset_circuit_breaker(self, manual: bool = True):
        """
        Reset circuit breaker (requires manual confirmation)
        
        Args:
            manual: Requires manual reset (safety feature)
        """
        if manual:
            self.logger.warning("Circuit breaker can only be reset manually for safety")
            return False
        
        self.circuit_breaker_active = False
        self.logger.info("✅ Circuit breaker reset")
        return True
    
    def update_trade_statistics(self, trade: Dict):
        """
        Update trade statistics for Kelly Criterion
        
        Args:
            trade: Trade dictionary with profit/loss
        """
        self.trade_history.append(trade)
        
        # Keep only last 100 trades
        if len(self.trade_history) > 100:
            self.trade_history.pop(0)
    
    def get_trade_statistics(self) -> Dict:
        """
        Get trading statistics for risk calculations
        
        Returns:
            Dictionary with stats
        """
        if not self.trade_history:
            return {
                'win_rate': 0.5,  # Assume 50% initially
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'total_trades': 0
            }
        
        wins = [t for t in self.trade_history if t.get('profit_loss', 0) > 0]
        losses = [t for t in self.trade_history if t.get('profit_loss', 0) < 0]
        
        win_rate = len(wins) / len(self.trade_history) if self.trade_history else 0.5
        avg_win = np.mean([t['profit_loss'] for t in wins]) if wins else 0.0
        avg_loss = abs(np.mean([t['profit_loss'] for t in losses])) if losses else 0.0
        
        return {
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_trades': len(self.trade_history),
            'wins': len(wins),
            'losses': len(losses)
        }
    
    def get_risk_report(self) -> Dict:
        """
        Get comprehensive risk report
        
        Returns:
            Risk metrics dictionary
        """
        stats = self.get_trade_statistics()
        
        return {
            'circuit_breaker_active': self.circuit_breaker_active,
            'max_daily_loss': f"{self.max_daily_loss_percent:.1%}",
            'max_weekly_loss': f"{self.max_weekly_loss_percent:.1%}",
            'max_monthly_loss': f"{self.max_monthly_loss_percent:.1%}",
            'max_portfolio_risk': f"{self.max_portfolio_risk:.1%}",
            'max_positions': self.max_positions,
            'trade_statistics': {
                'total_trades': stats['total_trades'],
                'win_rate': f"{stats['win_rate']:.1%}",
                'avg_win': f"${stats['avg_win']:.2f}",
                'avg_loss': f"${stats['avg_loss']:.2f}"
            }
        }


# Example usage
if __name__ == "__main__":
    print("\n" + "="*60)
    print("ADVANCED RISK MANAGEMENT SYSTEM")
    print("="*60)
    
    # Initialize risk manager
    risk_mgr = AdvancedRiskManager()
    
    # Example: Calculate Kelly position size
    print("\n💰 Kelly Criterion Position Sizing:")
    position_size = risk_mgr.calculate_kelly_position_size(
        win_rate=0.55,
        avg_win=100,
        avg_loss=50,
        balance=10000
    )
    print(f"  Optimal position size: ${position_size:.2f}")
    
    # Example: Dynamic stop loss
    print("\n🛑 Dynamic Stop Loss (ATR-based):")
    stop_price = risk_mgr.calculate_dynamic_stop_loss(
        entry_price=50000,
        atr=1500
    )
    print(f"  Stop loss price: ${stop_price:.2f}")
    
    # Example: Dynamic take profit
    print("\n🎯 Dynamic Take Profit Targets:")
    targets = risk_mgr.calculate_dynamic_take_profit(
        entry_price=50000,
        atr=1500
    )
    for i, target in enumerate(targets, 1):
        print(f"  Target {i}: ${target:.2f}")
    
    # Risk report
    print("\n📊 Risk Management Report:")
    report = risk_mgr.get_risk_report()
    print(f"  Circuit Breaker: {'🚨 ACTIVE' if report['circuit_breaker_active'] else '✅ Inactive'}")
    print(f"  Max Daily Loss: {report['max_daily_loss']}")
    print(f"  Max Weekly Loss: {report['max_weekly_loss']}")
    print(f"  Max Portfolio Risk: {report['max_portfolio_risk']}")
    print(f"  Max Positions: {report['max_positions']}")
    
    print("\n✅ Risk management system ready!")
