"""
Backtesting Module - Test trading strategies on historical data
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from logger import get_logger
from data_fetcher import DataFetcher
from analyzer import TechnicalAnalyzer


class Backtester:
    """
    Backtest trading strategies on historical data
    """
    
    def __init__(self, initial_balance=10000, commission=0.001, slippage=0.0005):
        """
        Initialize backtester
        
        Args:
            initial_balance: Starting capital
            commission: Commission per trade (0.001 = 0.1%)
            slippage: Slippage per trade (0.0005 = 0.05%)
        """
        self.logger = get_logger()
        self.initial_balance = initial_balance
        self.commission = commission
        self.slippage = slippage
        
        # Trading state
        self.balance = initial_balance
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        
    def run_backtest(self, df: pd.DataFrame, symbol: str, analyzer: TechnicalAnalyzer,
                    stop_loss_percent=3, take_profit_percent=5) -> Dict:
        """
        Run backtest on historical data
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Trading pair
            analyzer: Technical analyzer instance
            stop_loss_percent: Stop loss percentage
            take_profit_percent: Take profit percentage
        
        Returns:
            Dictionary with backtest results
        """
        self.logger.info(f"Starting backtest for {symbol} with {len(df)} candles")
        
        # Reset state
        self.balance = self.initial_balance
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        
        # Calculate indicators
        df = analyzer.calculate_all_indicators(df)
        
        # Iterate through candles
        for i in range(50, len(df)):  # Start after warmup period
            current_candle = df.iloc[i]
            current_price = current_candle['close']
            current_time = current_candle.name
            
            # Get historical data up to current point
            historical_df = df.iloc[:i+1]
            
            # Check stop loss / take profit for existing positions
            if symbol in self.positions:
                self._check_exit_conditions(
                    symbol, current_price, current_time,
                    stop_loss_percent, take_profit_percent
                )
            
            # Generate signal
            signal, strength, indicators = analyzer.generate_signal(historical_df, symbol)
            
            # Execute trades based on signal
            if signal == 'BUY' and symbol not in self.positions:
                self._execute_backtest_buy(symbol, current_price, current_time, strength)
            
            elif signal == 'SELL' and symbol in self.positions:
                self._execute_backtest_sell(symbol, current_price, current_time, 'Signal')
            
            # Record equity
            equity = self._calculate_backtest_equity(current_price)
            self.equity_curve.append({
                'timestamp': current_time,
                'balance': self.balance,
                'equity': equity,
                'positions': len(self.positions)
            })
        
        # Close any remaining positions at end
        if symbol in self.positions:
            final_price = df.iloc[-1]['close']
            final_time = df.iloc[-1].name
            self._execute_backtest_sell(symbol, final_price, final_time, 'End of backtest')
        
        # Calculate results
        results = self._calculate_backtest_results()
        
        self.logger.info(f"Backtest completed: {results['total_trades']} trades, "
                        f"{results['win_rate']:.2f}% win rate, "
                        f"{results['total_return']:.2f}% return")
        
        return results
    
    def _execute_backtest_buy(self, symbol: str, price: float, timestamp, strength: int):
        """Execute buy in backtest"""
        # Apply slippage
        execution_price = price * (1 + self.slippage)
        
        # Calculate position size (10% of balance)
        position_size = (self.balance * 0.1) / execution_price
        total_cost = execution_price * position_size
        commission_cost = total_cost * self.commission
        
        if total_cost + commission_cost > self.balance:
            return  # Insufficient funds
        
        # Update state
        self.balance -= (total_cost + commission_cost)
        self.positions[symbol] = {
            'amount': position_size,
            'entry_price': execution_price,
            'entry_time': timestamp,
            'entry_balance': self.balance + total_cost
        }
        
        # Record trade
        self.trades.append({
            'timestamp': timestamp,
            'symbol': symbol,
            'action': 'BUY',
            'price': execution_price,
            'amount': position_size,
            'total': total_cost,
            'commission': commission_cost,
            'balance': self.balance
        })
    
    def _execute_backtest_sell(self, symbol: str, price: float, timestamp, reason: str):
        """Execute sell in backtest"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        # Apply slippage
        execution_price = price * (1 - self.slippage)
        
        # Calculate proceeds
        amount = position['amount']
        total_value = execution_price * amount
        commission_cost = total_value * self.commission
        net_proceeds = total_value - commission_cost
        
        # Calculate P&L
        entry_cost = position['entry_price'] * amount
        profit_loss = net_proceeds - entry_cost
        profit_loss_percent = (profit_loss / entry_cost) * 100
        
        # Update state
        self.balance += net_proceeds
        del self.positions[symbol]
        
        # Record trade
        self.trades.append({
            'timestamp': timestamp,
            'symbol': symbol,
            'action': 'SELL',
            'price': execution_price,
            'amount': amount,
            'total': total_value,
            'commission': commission_cost,
            'profit_loss': profit_loss,
            'profit_loss_percent': profit_loss_percent,
            'balance': self.balance,
            'reason': reason,
            'hold_time': (timestamp - position['entry_time']).total_seconds() / 3600  # hours
        })
    
    def _check_exit_conditions(self, symbol: str, price: float, timestamp,
                              stop_loss_percent: float, take_profit_percent: float):
        """Check if stop loss or take profit should trigger"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        entry_price = position['entry_price']
        
        # Stop loss
        stop_loss_price = entry_price * (1 - stop_loss_percent / 100)
        if price <= stop_loss_price:
            self._execute_backtest_sell(symbol, price, timestamp, 'Stop Loss')
            return
        
        # Take profit
        take_profit_price = entry_price * (1 + take_profit_percent / 100)
        if price >= take_profit_price:
            self._execute_backtest_sell(symbol, price, timestamp, 'Take Profit')
            return
    
    def _calculate_backtest_equity(self, current_price: float) -> float:
        """Calculate current equity"""
        equity = self.balance
        for symbol, position in self.positions.items():
            equity += position['amount'] * current_price
        return equity
    
    def _calculate_backtest_results(self) -> Dict:
        """Calculate comprehensive backtest results"""
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'max_drawdown': 0
            }
        
        # Separate buy and sell trades
        buy_trades = [t for t in self.trades if t['action'] == 'BUY']
        sell_trades = [t for t in self.trades if t['action'] == 'SELL']
        
        # Calculate metrics
        total_trades = len(sell_trades)
        winning_trades = len([t for t in sell_trades if t.get('profit_loss', 0) > 0])
        losing_trades = len([t for t in sell_trades if t.get('profit_loss', 0) < 0])
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = sum(t.get('profit_loss', 0) for t in sell_trades if t.get('profit_loss', 0) > 0)
        total_loss = sum(t.get('profit_loss', 0) for t in sell_trades if t.get('profit_loss', 0) < 0)
        net_profit = total_profit + total_loss
        
        final_equity = self.equity_curve[-1]['equity'] if self.equity_curve else self.initial_balance
        total_return = ((final_equity - self.initial_balance) / self.initial_balance) * 100
        
        # Calculate maximum drawdown
        equity_values = [e['equity'] for e in self.equity_curve]
        peak = equity_values[0]
        max_drawdown = 0
        
        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = ((peak - equity) / peak) * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Average trade metrics
        avg_profit = total_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = abs(total_loss / losing_trades) if losing_trades > 0 else 0
        
        profit_factor = abs(total_profit / total_loss) if total_loss != 0 else 0
        
        # Average hold time
        avg_hold_time = np.mean([t.get('hold_time', 0) for t in sell_trades]) if sell_trades else 0
        
        # Sharpe ratio (simplified)
        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_equity = self.equity_curve[i-1]['equity']
            curr_equity = self.equity_curve[i]['equity']
            returns.append((curr_equity - prev_equity) / prev_equity)
        
        sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if len(returns) > 1 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'total_return': round(total_return, 2),
            'net_profit': round(net_profit, 2),
            'total_profit': round(total_profit, 2),
            'total_loss': round(total_loss, 2),
            'avg_profit': round(avg_profit, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'max_drawdown': round(max_drawdown, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'avg_hold_time_hours': round(avg_hold_time, 2),
            'initial_balance': self.initial_balance,
            'final_balance': round(final_equity, 2),
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
    
    def plot_results(self, results: Dict, symbol: str, save_path: str = None):
        """
        Plot backtest results
        
        Args:
            results: Backtest results dictionary
            symbol: Trading pair
            save_path: Path to save plot (optional)
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
            
            # Equity curve
            equity_df = pd.DataFrame(results['equity_curve'])
            equity_df.set_index('timestamp', inplace=True)
            
            ax1.plot(equity_df.index, equity_df['equity'], label='Equity', linewidth=2)
            ax1.axhline(y=self.initial_balance, color='r', linestyle='--', 
                       label=f'Initial Balance: ${self.initial_balance}')
            ax1.set_title(f'Backtest Results - {symbol}', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Equity ($)', fontsize=12)
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # Mark buy/sell trades
            for trade in results['trades']:
                color = 'g' if trade['action'] == 'BUY' else 'r'
                marker = '^' if trade['action'] == 'BUY' else 'v'
                ax1.scatter(trade['timestamp'], 
                          equity_df.loc[trade['timestamp'], 'equity'],
                          color=color, marker=marker, s=100, zorder=5)
            
            # Drawdown
            equity_values = equity_df['equity'].values
            running_max = np.maximum.accumulate(equity_values)
            drawdown = ((running_max - equity_values) / running_max) * 100
            
            ax2.fill_between(equity_df.index, drawdown, 0, color='red', alpha=0.3)
            ax2.set_ylabel('Drawdown (%)', fontsize=12)
            ax2.set_xlabel('Date', fontsize=12)
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                self.logger.info(f"Backtest plot saved to {save_path}")
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error plotting results: {e}")
            return None


if __name__ == "__main__":
    # Test backtester
    from data_fetcher import DataFetcher
    from analyzer import TechnicalAnalyzer
    
    fetcher = DataFetcher()
    analyzer = TechnicalAnalyzer()
    
    # Fetch historical data
    df = fetcher.fetch_ohlcv('BTC/USDT', '1h', 1000)
    
    if df is not None:
        backtester = Backtester(initial_balance=10000)
        results = backtester.run_backtest(df, 'BTC/USDT', analyzer)
        
        print("\n=== Backtest Results ===")
        print(f"Total Trades: {results['total_trades']}")
        print(f"Win Rate: {results['win_rate']}%")
        print(f"Total Return: {results['total_return']}%")
        print(f"Net Profit: ${results['net_profit']}")
        print(f"Max Drawdown: {results['max_drawdown']}%")
        print(f"Sharpe Ratio: {results['sharpe_ratio']}")
        print(f"Final Balance: ${results['final_balance']}")
