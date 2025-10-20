"""
Trading Execution Module - Paper trading and live trading with risk management
"""
import ccxt
from typing import Dict, Optional, Tuple
from datetime import datetime
from logger import get_logger
from database import TradingDatabase
import time


class Trader:
    """
    Trading execution engine with paper and live trading modes
    """
    
    def __init__(self, mode='paper', initial_balance=10000, 
                 api_key=None, api_secret=None, config: Dict = None):
        """
        Initialize trader
        
        Args:
            mode: 'paper' or 'live'
            initial_balance: Starting balance for paper trading
            api_key: Exchange API key
            api_secret: Exchange API secret
            config: Trading configuration
        """
        self.logger = get_logger()
        self.mode = mode.lower()
        self.config = config or {}
        self.db = TradingDatabase()
        
        # Risk management parameters
        self.max_positions = self.config.get('risk', {}).get('max_positions', 3)
        self.position_size_percent = self.config.get('risk', {}).get('position_size_percent', 10)
        self.stop_loss_percent = self.config.get('risk', {}).get('stop_loss', {}).get('percent', 3)
        self.take_profit_levels = self.config.get('risk', {}).get('take_profit', {}).get('levels', [])
        
        # Paper trading
        if self.mode == 'paper':
            self.balance = initial_balance
            self.initial_balance = initial_balance
            self.positions = {}  # symbol -> {'amount': float, 'entry_price': float, 'stop_loss': float}
            self.logger.info(f"Initialized paper trading with balance: ${initial_balance}")
            
            # Initialize balance in database
            self.db.update_balance(self.balance, self.balance)
        
        # Live trading
        elif self.mode == 'live':
            if not api_key or not api_secret:
                raise ValueError("API key and secret required for live trading")
            
            try:
                # First, fetch server time to calculate offset
                import requests
                try:
                    response = requests.get('https://api.binance.com/api/v3/time', timeout=5)
                    server_time = response.json()['serverTime']
                    local_time = int(time.time() * 1000)
                    time_offset = server_time - local_time
                    self.logger.info(f"Time offset with Binance: {time_offset}ms")
                except Exception as time_err:
                    time_offset = 0
                    self.logger.warning(f"Could not sync time with Binance: {time_err}")
                
                self.exchange = ccxt.binance({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot',
                        'adjustForTimeDifference': True,
                        'recvWindow': 60000
                    }
                })
                
                # Set time offset if needed
                if abs(time_offset) > 500:  # More than 500ms difference
                    self.exchange.options['timeDifference'] = time_offset
                
                # Load markets to sync with exchange
                for attempt in range(3):
                    try:
                        self.exchange.load_markets()
                        break
                    except Exception as sync_error:
                        if attempt == 2:
                            self.logger.warning(f"Could not sync markets after 3 attempts: {sync_error}")
                        else:
                            time.sleep(1)
                
                # Fetch actual balance
                balance_info = self.exchange.fetch_balance()
                self.balance = balance_info['USDT']['free']
                self.logger.info(f"Initialized live trading with balance: ${self.balance} USDT")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize live trading: {e}")
                raise
        else:
            raise ValueError(f"Invalid trading mode: {mode}")
        
        self.trade_history = []
    
    def execute_buy(self, symbol: str, price: float, reason: str = '', 
                   signal_strength: int = 0) -> Optional[Dict]:
        """
        Execute buy order
        
        Args:
            symbol: Trading pair
            price: Current price
            reason: Reason for buying
            signal_strength: Signal strength (0-100)
        
        Returns:
            Trade details or None
        """
        try:
            # Check if we can open new position
            current_positions = len(self.positions) if self.mode == 'paper' else self._get_live_positions()
            if current_positions >= self.max_positions:
                self.logger.warning(f"Maximum positions ({self.max_positions}) reached. Cannot buy {symbol}")
                return None
            
            # Check if we already have this position
            if self.mode == 'paper' and symbol in self.positions:
                self.logger.warning(f"Already have position in {symbol}")
                return None
            
            # Calculate position size
            available_balance = self._get_available_balance()
            position_size = self._calculate_position_size(available_balance, price, signal_strength)
            
            if position_size <= 0:
                self.logger.warning(f"Insufficient balance for {symbol}")
                return None
            
            # Calculate stop loss and take profit
            stop_loss = price * (1 - self.stop_loss_percent / 100)
            
            # Execute trade
            if self.mode == 'paper':
                trade = self._execute_paper_buy(symbol, price, position_size, stop_loss, reason)
            else:
                trade = self._execute_live_buy(symbol, price, position_size, stop_loss, reason)
            
            if trade:
                self.logger.log_trade('BUY', symbol, price, position_size, reason)
                
                # Store in database
                self.db.insert_trade(
                    symbol=symbol,
                    action='BUY',
                    price=price,
                    amount=position_size,
                    commission=trade.get('commission', 0),
                    reason=reason,
                    order_id=trade.get('order_id', ''),
                    metadata={'signal_strength': signal_strength, 'stop_loss': stop_loss}
                )
                
                return trade
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error executing buy for {symbol}: {e}", exc_info=True)
            return None
    
    def execute_sell(self, symbol: str, price: float, reason: str = '') -> Optional[Dict]:
        """
        Execute sell order
        
        Args:
            symbol: Trading pair
            price: Current price
            reason: Reason for selling
        
        Returns:
            Trade details or None
        """
        try:
            # Check if we have position
            if self.mode == 'paper':
                if symbol not in self.positions:
                    self.logger.warning(f"No position in {symbol} to sell")
                    return None
                
                position = self.positions[symbol]
                amount = position['amount']
            else:
                # Get position from exchange
                amount = self._get_live_position_amount(symbol)
                if amount <= 0:
                    self.logger.warning(f"No position in {symbol} to sell")
                    return None
            
            # Execute trade
            if self.mode == 'paper':
                trade = self._execute_paper_sell(symbol, price, amount, reason)
            else:
                trade = self._execute_live_sell(symbol, price, amount, reason)
            
            if trade:
                self.logger.log_trade('SELL', symbol, price, amount, reason)
                
                # Calculate profit/loss
                profit_loss = trade.get('profit_loss', 0)
                
                # Store in database
                self.db.insert_trade(
                    symbol=symbol,
                    action='SELL',
                    price=price,
                    amount=amount,
                    commission=trade.get('commission', 0),
                    profit_loss=profit_loss,
                    reason=reason,
                    order_id=trade.get('order_id', '')
                )
                
                return trade
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error executing sell for {symbol}: {e}", exc_info=True)
            return None
    
    def _execute_paper_buy(self, symbol: str, price: float, amount: float,
                          stop_loss: float, reason: str) -> Dict:
        """Execute paper trading buy"""
        total_cost = price * amount
        commission = total_cost * 0.001  # 0.1% commission
        total_with_commission = total_cost + commission
        
        if total_with_commission > self.balance:
            self.logger.warning(f"Insufficient balance for paper buy")
            return None
        
        # Update balance and positions
        self.balance -= total_with_commission
        self.positions[symbol] = {
            'amount': amount,
            'entry_price': price,
            'stop_loss': stop_loss,
            'entry_time': datetime.now()
        }
        
        # Update database
        self.db.update_portfolio(symbol, amount, price, price)
        equity = self._calculate_equity(price)
        self.db.update_balance(self.balance, equity)
        
        return {
            'symbol': symbol,
            'action': 'BUY',
            'price': price,
            'amount': amount,
            'total': total_cost,
            'commission': commission,
            'balance': self.balance,
            'timestamp': datetime.now().isoformat()
        }
    
    def _execute_paper_sell(self, symbol: str, price: float, amount: float, 
                           reason: str) -> Dict:
        """Execute paper trading sell"""
        total_value = price * amount
        commission = total_value * 0.001  # 0.1% commission
        total_after_commission = total_value - commission
        
        # Calculate profit/loss
        position = self.positions[symbol]
        entry_price = position['entry_price']
        profit_loss = (price - entry_price) * amount - commission
        profit_loss_percent = (profit_loss / (entry_price * amount)) * 100
        
        # Update balance and remove position
        self.balance += total_after_commission
        del self.positions[symbol]
        
        # Update database
        self.db.update_portfolio(symbol, 0, entry_price, price)
        equity = self._calculate_equity(price)
        total_pnl = self.balance + equity - self.initial_balance
        total_pnl_percent = (total_pnl / self.initial_balance) * 100
        self.db.update_balance(self.balance, equity, total_pnl, total_pnl_percent)
        
        return {
            'symbol': symbol,
            'action': 'SELL',
            'price': price,
            'amount': amount,
            'total': total_value,
            'commission': commission,
            'profit_loss': profit_loss,
            'profit_loss_percent': profit_loss_percent,
            'balance': self.balance,
            'timestamp': datetime.now().isoformat()
        }
    
    def _execute_live_buy(self, symbol: str, price: float, amount: float,
                         stop_loss: float, reason: str) -> Optional[Dict]:
        """Execute live trading buy"""
        try:
            # Place market buy order
            order = self.exchange.create_market_buy_order(symbol, amount)
            
            # Wait for order to fill
            time.sleep(1)
            order = self.exchange.fetch_order(order['id'], symbol)
            
            if order['status'] == 'closed':
                filled_price = order['average']
                filled_amount = order['filled']
                commission = order.get('fee', {}).get('cost', 0)
                
                self.logger.info(f"Live buy executed: {filled_amount} {symbol} @ {filled_price}")
                
                return {
                    'symbol': symbol,
                    'action': 'BUY',
                    'price': filled_price,
                    'amount': filled_amount,
                    'total': filled_price * filled_amount,
                    'commission': commission,
                    'order_id': order['id'],
                    'timestamp': datetime.now().isoformat()
                }
            else:
                self.logger.error(f"Order not filled: {order['status']}")
                return None
                
        except Exception as e:
            self.logger.error(f"Live buy execution failed: {e}", exc_info=True)
            return None
    
    def _execute_live_sell(self, symbol: str, price: float, amount: float,
                          reason: str) -> Optional[Dict]:
        """Execute live trading sell"""
        try:
            # Place market sell order
            order = self.exchange.create_market_sell_order(symbol, amount)
            
            # Wait for order to fill
            time.sleep(1)
            order = self.exchange.fetch_order(order['id'], symbol)
            
            if order['status'] == 'closed':
                filled_price = order['average']
                filled_amount = order['filled']
                commission = order.get('fee', {}).get('cost', 0)
                
                self.logger.info(f"Live sell executed: {filled_amount} {symbol} @ {filled_price}")
                
                return {
                    'symbol': symbol,
                    'action': 'SELL',
                    'price': filled_price,
                    'amount': filled_amount,
                    'total': filled_price * filled_amount,
                    'commission': commission,
                    'order_id': order['id'],
                    'timestamp': datetime.now().isoformat()
                }
            else:
                self.logger.error(f"Order not filled: {order['status']}")
                return None
                
        except Exception as e:
            self.logger.error(f"Live sell execution failed: {e}", exc_info=True)
            return None
    
    def check_stop_loss_take_profit(self, symbol: str, current_price: float) -> Optional[str]:
        """
        Check if stop loss or take profit should be triggered
        
        Args:
            symbol: Trading pair
            current_price: Current market price
        
        Returns:
            Action to take ('SELL' or None)
        """
        if self.mode == 'paper':
            if symbol not in self.positions:
                return None
            
            position = self.positions[symbol]
            entry_price = position['entry_price']
            stop_loss = position['stop_loss']
            
            # Check stop loss
            if current_price <= stop_loss:
                self.logger.warning(f"Stop loss triggered for {symbol} at {current_price}")
                return 'SELL'
            
            # Check take profit levels
            for level in self.take_profit_levels:
                tp_price = entry_price * (1 + level['percent'] / 100)
                if current_price >= tp_price:
                    self.logger.info(f"Take profit level {level['percent']}% reached for {symbol}")
                    return 'SELL'
            
            # Update trailing stop loss
            if self.config.get('risk', {}).get('stop_loss', {}).get('type') == 'trailing':
                new_stop_loss = current_price * (1 - self.stop_loss_percent / 100)
                if new_stop_loss > stop_loss:
                    position['stop_loss'] = new_stop_loss
                    self.logger.debug(f"Updated trailing stop loss for {symbol}: {new_stop_loss}")
        
        return None
    
    def _calculate_position_size(self, available_balance: float, price: float,
                                signal_strength: int) -> float:
        """
        Calculate position size based on balance and signal strength
        
        Args:
            available_balance: Available balance
            price: Current price
            signal_strength: Signal strength (0-100)
        
        Returns:
            Position size (amount to buy)
        """
        # Base position size
        base_size = (available_balance * self.position_size_percent / 100) / price
        
        # Adjust based on signal strength if dynamic sizing enabled
        if self.config.get('risk', {}).get('dynamic_sizing', {}).get('enabled', False):
            min_size = self.config.get('risk', {}).get('dynamic_sizing', {}).get('min_size', 50)
            max_size = self.config.get('risk', {}).get('dynamic_sizing', {}).get('max_size', 100)
            
            # Scale between min and max based on signal strength
            size_multiplier = min_size + (max_size - min_size) * (signal_strength / 100)
            base_size *= (size_multiplier / 100)
        
        return round(base_size, 8)
    
    def _get_available_balance(self) -> float:
        """Get available balance for trading"""
        if self.mode == 'paper':
            return self.balance
        else:
            try:
                balance_info = self.exchange.fetch_balance()
                return balance_info['USDT']['free']
            except Exception as e:
                self.logger.error(f"Error fetching balance: {e}")
                return 0
    
    def _calculate_equity(self, current_prices = None) -> float:
        """Calculate total equity (balance + position values)"""
        if self.mode == 'paper':
            equity = self.balance
            if current_prices:
                # Handle both dict and float inputs
                if isinstance(current_prices, dict):
                    for symbol, position in self.positions.items():
                        price = current_prices.get(symbol, position['entry_price'])
                        equity += position['amount'] * price
                else:
                    # Single price value - use for all positions
                    for symbol, position in self.positions.items():
                        equity += position['amount'] * position['entry_price']
            return equity
        else:
            try:
                balance_info = self.exchange.fetch_balance()
                return balance_info['total']['USDT']
            except Exception as e:
                self.logger.error(f"Error calculating equity: {e}")
                return 0
    
    def _get_live_positions(self) -> int:
        """Get number of open positions in live trading"""
        try:
            balance = self.exchange.fetch_balance()
            positions = sum(1 for currency, amount in balance['total'].items() 
                          if currency != 'USDT' and amount > 0)
            return positions
        except Exception as e:
            self.logger.error(f"Error fetching positions: {e}")
            return 0
    
    def _get_live_position_amount(self, symbol: str) -> float:
        """Get position amount for symbol in live trading"""
        try:
            base_currency = symbol.split('/')[0]
            balance = self.exchange.fetch_balance()
            return balance[base_currency]['free']
        except Exception as e:
            self.logger.error(f"Error fetching position amount: {e}")
            return 0
    
    def get_status(self) -> Dict:
        """
        Get current trading status
        
        Returns:
            Dictionary with status information
        """
        status = {
            'mode': self.mode,
            'balance': self.balance if self.mode == 'paper' else self._get_available_balance(),
            'positions': len(self.positions) if self.mode == 'paper' else self._get_live_positions(),
            'equity': self._calculate_equity()
        }
        
        if self.mode == 'paper':
            status['position_details'] = self.positions
            status['total_pnl'] = status['equity'] - self.initial_balance
            status['total_pnl_percent'] = ((status['equity'] - self.initial_balance) / 
                                          self.initial_balance * 100)
        
        return status


if __name__ == "__main__":
    # Test paper trading
    trader = Trader(mode='paper', initial_balance=10000)
    
    # Simulate buy
    trade = trader.execute_buy('BTC/USDT', 45000.0, 'Test buy signal', signal_strength=85)
    print(f"Buy trade: {trade}")
    
    # Check status
    status = trader.get_status()
    print(f"Status: {status}")
    
    # Simulate sell
    trade = trader.execute_sell('BTC/USDT', 46000.0, 'Test sell signal')
    print(f"Sell trade: {trade}")
    
    # Final status
    status = trader.get_status()
    print(f"Final status: {status}")
