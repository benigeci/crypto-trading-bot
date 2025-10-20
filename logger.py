"""
Logger Module - Comprehensive logging and monitoring for the trading bot
"""
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from colorama import Fore, Style, init
import traceback

# Initialize colorama for Windows support
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color coding for console output"""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{log_color}{record.levelname}{Style.RESET_ALL}"
        record.msg = f"{log_color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)


class TradingLogger:
    """
    Centralized logging system for the trading bot
    """
    
    def __init__(self, log_dir='logs', log_level='INFO', max_bytes=10485760, backup_count=5):
        """
        Initialize the logger
        
        Args:
            log_dir: Directory for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            max_bytes: Maximum size of log file before rotation
            backup_count: Number of backup log files to keep
        """
        self.log_dir = log_dir
        self.log_level = getattr(logging, log_level.upper())
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize loggers
        self.main_logger = self._setup_logger('main', 'bot.log')
        self.trade_logger = self._setup_logger('trades', 'trades.log')
        self.signal_logger = self._setup_logger('signals', 'signals.log')
        self.error_logger = self._setup_logger('errors', 'errors.log', logging.ERROR)
        
    def _setup_logger(self, name, filename, level=None):
        """
        Set up a logger with file and console handlers
        
        Args:
            name: Logger name
            filename: Log file name
            level: Logging level (optional)
        
        Returns:
            Configured logger
        """
        logger = logging.getLogger(name)
        logger.setLevel(level or self.log_level)
        logger.handlers.clear()
        
        # File handler with rotation
        file_path = os.path.join(self.log_dir, filename)
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Console handler with colors
        console_handler = logging.StreamHandler()
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def info(self, message):
        """Log info message"""
        self.main_logger.info(message)
    
    def debug(self, message):
        """Log debug message"""
        self.main_logger.debug(message)
    
    def warning(self, message):
        """Log warning message"""
        self.main_logger.warning(message)
    
    def error(self, message, exc_info=None):
        """Log error message"""
        self.main_logger.error(message)
        self.error_logger.error(message)
        if exc_info:
            self.error_logger.error(traceback.format_exc())
    
    def critical(self, message):
        """Log critical message"""
        self.main_logger.critical(message)
        self.error_logger.critical(message)
    
    def log_trade(self, action, symbol, price, amount, reason=''):
        """
        Log trade execution
        
        Args:
            action: BUY or SELL
            symbol: Trading pair
            price: Execution price
            amount: Trade amount
            reason: Reason for trade
        """
        message = f"{action} {amount} {symbol} @ {price}"
        if reason:
            message += f" | Reason: {reason}"
        
        self.trade_logger.info(message)
        self.main_logger.info(f"TRADE: {message}")
    
    def log_signal(self, signal_type, symbol, price, indicators, strength=None):
        """
        Log trading signal
        
        Args:
            signal_type: BUY, SELL, or HOLD
            symbol: Trading pair
            price: Current price
            indicators: Dictionary of indicator values
            strength: Signal strength (0-100)
        """
        message = f"{signal_type} signal for {symbol} @ {price}"
        if strength:
            message += f" | Strength: {strength}%"
        
        # Add indicator details
        indicator_str = " | ".join([f"{k}: {v}" for k, v in indicators.items()])
        message += f" | {indicator_str}"
        
        self.signal_logger.info(message)
        self.main_logger.info(f"SIGNAL: {message}")
    
    def log_performance(self, metrics):
        """
        Log performance metrics
        
        Args:
            metrics: Dictionary of performance metrics
        """
        message = "Performance Summary: "
        message += " | ".join([f"{k}: {v}" for k, v in metrics.items()])
        self.main_logger.info(message)
    
    def log_exception(self, exc_type, exc_value, exc_traceback):
        """
        Log unhandled exception
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        self.error_logger.critical(f"Unhandled exception:\n{error_msg}")
        self.main_logger.critical("Unhandled exception occurred - check error log")


# Global logger instance
_logger_instance = None


def get_logger(log_dir='logs', log_level='INFO'):
    """
    Get or create global logger instance
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level
    
    Returns:
        TradingLogger instance
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = TradingLogger(log_dir=log_dir, log_level=log_level)
    return _logger_instance


if __name__ == "__main__":
    # Test the logger
    logger = get_logger(log_level='DEBUG')
    
    logger.debug("This is a debug message")
    logger.info("Bot started successfully")
    logger.warning("High API usage detected")
    logger.error("Failed to fetch data")
    logger.critical("Critical system error")
    
    logger.log_signal('BUY', 'BTC/USDT', 45000.00, {'RSI': 28, 'MACD': 'bullish'}, 85)
    logger.log_trade('BUY', 'BTC/USDT', 45000.00, 0.1, 'Strong buy signal')
    logger.log_performance({'Total Profit': '15.5%', 'Win Rate': '68%', 'Total Trades': 24})


# Compatibility function for new modules
def setup_logger(name='trading_bot', log_dir='logs', log_level='INFO'):
    """
    Setup and return a logger instance
    
    Args:
        name: Logger name
        log_dir: Directory for log files
        log_level: Logging level
    
    Returns:
        Logger instance
    """
    logger_obj = get_logger(log_dir=log_dir, log_level=log_level)
    return logger_obj.main_logger  # Return the actual logger object
