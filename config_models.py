"""
Configuration Management with Pydantic Models
Provides type-safe, validated configuration with schema validation
"""

from pydantic import BaseModel, Field, validator, SecretStr
from typing import List, Dict, Optional, Literal
from pathlib import Path
import yaml
import os
from dotenv import load_dotenv

load_dotenv()


class ExchangeConfig(BaseModel):
    """Exchange configuration"""
    name: str = Field(..., description="Exchange name (e.g., 'binance')")
    api_key: Optional[SecretStr] = Field(None, description="API key")
    api_secret: Optional[SecretStr] = Field(None, description="API secret")
    testnet: bool = Field(False, description="Use testnet/sandbox mode")
    rate_limit: bool = Field(True, description="Enable rate limiting")
    
    @validator('name')
    def validate_exchange_name(cls, v):
        valid_exchanges = ['binance', 'kraken', 'coinbasepro', 'bybit', 'okx']
        if v.lower() not in valid_exchanges:
            raise ValueError(f"Exchange must be one of {valid_exchanges}")
        return v.lower()


class TradingConfig(BaseModel):
    """Trading strategy configuration"""
    mode: Literal['paper', 'live'] = Field('paper', description="Trading mode")
    initial_balance: float = Field(10000.0, ge=0, description="Initial balance in USDT")
    symbols: List[str] = Field(..., description="Trading pairs to monitor")
    timeframe: str = Field('15m', description="Primary timeframe")
    update_interval: int = Field(300, ge=60, description="Update interval in seconds")
    max_positions: int = Field(3, ge=1, le=10, description="Maximum concurrent positions")
    position_size_pct: float = Field(10.0, ge=1.0, le=100.0, description="Position size as % of balance")
    
    @validator('symbols')
    def validate_symbols(cls, v):
        if not v:
            raise ValueError("At least one symbol must be specified")
        # Validate format
        for symbol in v:
            if '/' not in symbol:
                raise ValueError(f"Invalid symbol format: {symbol}. Use 'BASE/QUOTE' format")
        return v
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d']
        if v not in valid_timeframes:
            raise ValueError(f"Timeframe must be one of {valid_timeframes}")
        return v


class IndicatorThresholds(BaseModel):
    """Dynamic indicator thresholds"""
    rsi_oversold: float = Field(30.0, ge=0, le=100)
    rsi_overbought: float = Field(70.0, ge=0, le=100)
    rsi_weight: float = Field(1.0, ge=0, le=10)
    
    macd_signal_weight: float = Field(1.5, ge=0, le=10)
    bb_weight: float = Field(1.2, ge=0, le=10)
    volume_threshold: float = Field(1.5, ge=0)
    volume_weight: float = Field(1.0, ge=0, le=10)
    
    ema_fast: int = Field(12, ge=5, le=50)
    ema_slow: int = Field(26, ge=10, le=100)
    
    adaptive: bool = Field(True, description="Use adaptive thresholds based on volatility")
    
    @validator('rsi_overbought')
    def validate_rsi_levels(cls, v, values):
        if 'rsi_oversold' in values and v <= values['rsi_oversold']:
            raise ValueError("RSI overbought must be > oversold")
        return v


class RiskManagementConfig(BaseModel):
    """Risk management parameters"""
    use_stop_loss: bool = Field(True)
    stop_loss_pct: float = Field(2.0, ge=0.1, le=20.0, description="Stop loss %")
    use_take_profit: bool = Field(True)
    take_profit_pct: float = Field(4.0, ge=0.1, le=50.0, description="Take profit %")
    
    use_trailing_stop: bool = Field(True)
    trailing_stop_pct: float = Field(1.0, ge=0.1, le=10.0)
    
    max_daily_loss_pct: float = Field(5.0, ge=0, le=100, description="Max daily loss %")
    max_drawdown_pct: float = Field(20.0, ge=0, le=100, description="Max drawdown %")
    
    position_sizing_method: Literal['fixed', 'kelly', 'volatility'] = Field('volatility')
    kelly_fraction: float = Field(0.25, ge=0.01, le=1.0, description="Kelly criterion fraction")
    
    use_dynamic_sizing: bool = Field(True, description="Adjust position size based on volatility")
    volatility_lookback: int = Field(20, ge=5, le=100, description="Volatility calculation period")
    
    @validator('take_profit_pct')
    def validate_risk_reward(cls, v, values):
        if 'stop_loss_pct' in values and v < values['stop_loss_pct']:
            raise ValueError("Take profit should be >= stop loss for positive R:R")
        return v


class MLConfig(BaseModel):
    """Machine learning configuration"""
    enabled: bool = Field(True, description="Enable ML predictions")
    model_type: Literal['rf', 'xgb', 'ensemble'] = Field('ensemble')
    
    retrain_interval_hours: int = Field(168, ge=24, description="Retrain every N hours")
    min_training_samples: int = Field(1000, ge=100)
    
    feature_importance_threshold: float = Field(0.01, ge=0, le=1)
    prediction_confidence_threshold: float = Field(0.6, ge=0, le=1)
    
    use_prediction_cache: bool = Field(True)
    cache_ttl_seconds: int = Field(300, ge=60)
    
    ensemble_weights: Dict[str, float] = Field(
        default={'rf': 0.4, 'xgb': 0.4, 'indicators': 0.2}
    )
    
    @validator('ensemble_weights')
    def validate_weights(cls, v):
        total = sum(v.values())
        if not (0.99 <= total <= 1.01):  # Allow small floating point errors
            raise ValueError(f"Ensemble weights must sum to 1.0, got {total}")
        return v


class TelegramConfig(BaseModel):
    """Telegram bot configuration"""
    enabled: bool = Field(True)
    bot_token: SecretStr = Field(..., description="Telegram bot token")
    chat_id: str = Field(..., description="Telegram chat ID")
    
    enable_notifications: bool = Field(True)
    notify_on_trade: bool = Field(True)
    notify_on_signal: bool = Field(False)
    notify_on_error: bool = Field(True)
    
    rate_limit_per_user: int = Field(10, ge=1, description="Commands per minute per user")
    allowed_users: List[str] = Field(default_factory=list, description="Whitelisted user IDs")


class DatabaseConfig(BaseModel):
    """Database configuration"""
    type: Literal['sqlite', 'postgresql'] = Field('sqlite')
    path: Optional[Path] = Field(Path('trading_bot.db'), description="SQLite database path")
    
    # PostgreSQL settings
    host: Optional[str] = None
    port: Optional[int] = Field(5432, ge=1, le=65535)
    database: Optional[str] = None
    user: Optional[SecretStr] = None
    password: Optional[SecretStr] = None
    ssl_mode: Optional[str] = Field('prefer')
    
    encrypt_local: bool = Field(False, description="Encrypt local SQLite database")
    backup_enabled: bool = Field(True)
    backup_interval_hours: int = Field(24, ge=1)


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = Field('INFO')
    log_to_file: bool = Field(True)
    log_file_path: Path = Field(Path('logs/bot.log'))
    max_file_size_mb: int = Field(10, ge=1, le=1000)
    backup_count: int = Field(5, ge=1, le=100)
    
    log_trades: bool = Field(True)
    log_signals: bool = Field(True)
    log_api_calls: bool = Field(False, description="Log all API calls (verbose)")


class BacktestConfig(BaseModel):
    """Backtesting configuration"""
    enabled: bool = Field(True)
    lookback_days: int = Field(30, ge=7, le=365)
    
    walk_forward_enabled: bool = Field(False)
    walk_forward_train_pct: float = Field(0.7, ge=0.5, le=0.9)
    
    monte_carlo_enabled: bool = Field(False)
    monte_carlo_simulations: int = Field(1000, ge=100, le=10000)
    
    commission_pct: float = Field(0.1, ge=0, le=5.0)
    slippage_pct: float = Field(0.05, ge=0, le=2.0)


class BotConfig(BaseModel):
    """Main bot configuration"""
    exchange: ExchangeConfig
    trading: TradingConfig
    indicators: IndicatorThresholds
    risk_management: RiskManagementConfig
    ml: MLConfig
    telegram: TelegramConfig
    database: DatabaseConfig
    logging: LoggingConfig
    backtest: BacktestConfig
    
    class Config:
        use_enum_values = True
        validate_assignment = True
    
    @classmethod
    def from_yaml(cls, config_path: str = 'config.yaml') -> 'BotConfig':
        """
        Load configuration from YAML file
        
        Args:
            config_path: Path to YAML config file
            
        Returns:
            Validated BotConfig instance
        """
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        # Load secrets from environment variables
        config_dict = cls._load_secrets(config_dict)
        
        return cls(**config_dict)
    
    @staticmethod
    def _load_secrets(config_dict: dict) -> dict:
        """Load sensitive values from environment variables"""
        
        # Exchange API credentials
        if 'exchange' in config_dict:
            config_dict['exchange']['api_key'] = os.getenv('EXCHANGE_API_KEY')
            config_dict['exchange']['api_secret'] = os.getenv('EXCHANGE_API_SECRET')
        
        # Telegram credentials
        if 'telegram' in config_dict:
            config_dict['telegram']['bot_token'] = os.getenv('TELEGRAM_BOT_TOKEN')
            config_dict['telegram']['chat_id'] = os.getenv('TELEGRAM_CHAT_ID')
        
        # Database credentials (for PostgreSQL)
        if 'database' in config_dict and config_dict['database'].get('type') == 'postgresql':
            config_dict['database']['user'] = os.getenv('DB_USER')
            config_dict['database']['password'] = os.getenv('DB_PASSWORD')
        
        return config_dict
    
    def to_yaml(self, output_path: str = 'config_output.yaml'):
        """
        Export configuration to YAML (excluding secrets)
        
        Args:
            output_path: Output file path
        """
        config_dict = self.dict(exclude={'exchange': {'api_key', 'api_secret'},
                                        'telegram': {'bot_token'},
                                        'database': {'user', 'password'}})
        
        with open(output_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
    
    def validate_for_live_trading(self) -> List[str]:
        """
        Validate configuration for live trading
        
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        if self.trading.mode == 'live':
            # Check API credentials
            if not self.exchange.api_key or not self.exchange.api_secret:
                issues.append("API credentials required for live trading")
            
            # Check risk limits
            if self.risk_management.stop_loss_pct > 10:
                issues.append("Stop loss > 10% is risky for live trading")
            
            if self.risk_management.max_daily_loss_pct > 10:
                issues.append("Max daily loss > 10% is very risky")
            
            # Check position sizing
            if self.trading.position_size_pct > 50:
                issues.append("Position size > 50% is risky")
            
            # Check database backup
            if not self.database.backup_enabled:
                issues.append("Database backup should be enabled for live trading")
        
        return issues


# Create default configuration
def create_default_config() -> BotConfig:
    """Create default configuration"""
    return BotConfig(
        exchange=ExchangeConfig(
            name='binance',
            testnet=False
        ),
        trading=TradingConfig(
            mode='paper',
            initial_balance=10000.0,
            symbols=['BTC/USDT', 'ETH/USDT', 'BNB/USDT'],
            timeframe='15m',
            update_interval=300,
            max_positions=3,
            position_size_pct=10.0
        ),
        indicators=IndicatorThresholds(),
        risk_management=RiskManagementConfig(),
        ml=MLConfig(
            bot_token='YOUR_BOT_TOKEN',
            chat_id='YOUR_CHAT_ID'
        ),
        telegram=TelegramConfig(
            bot_token='YOUR_BOT_TOKEN',
            chat_id='YOUR_CHAT_ID'
        ),
        database=DatabaseConfig(),
        logging=LoggingConfig(),
        backtest=BacktestConfig()
    )


# Example usage
if __name__ == '__main__':
    # Create default config
    config = create_default_config()
    
    # Export to YAML
    config.to_yaml('config_default.yaml')
    
    # Validate for live trading
    issues = config.validate_for_live_trading()
    if issues:
        print("Configuration issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Configuration is valid for live trading")
    
    # Load from YAML
    try:
        loaded_config = BotConfig.from_yaml('config.yaml')
        print("Configuration loaded successfully")
    except Exception as e:
        print(f"Error loading configuration: {e}")
