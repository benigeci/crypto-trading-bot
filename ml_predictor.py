"""
Machine Learning Price Prediction Module
Implements LSTM, Random Forest, and XGBoost models for price forecasting
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
import os
from logger import get_logger


class MLPricePredictor:
    """
    Machine Learning ensemble for cryptocurrency price prediction
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize ML predictor
        
        Args:
            config: Configuration dictionary
        """
        self.logger = get_logger()
        self.config = config or {}
        
        # Model paths
        self.model_dir = self.config.get('model_dir', 'models/')
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Models
        self.rf_classifier = None  # Random Forest for direction (UP/DOWN/NEUTRAL)
        self.xgb_regressor = None  # XGBoost for price targets
        self.scaler = StandardScaler()
        
        # Feature configuration
        self.sequence_length = 50  # Number of historical candles to use
        self.prediction_horizon = 5  # Predict next 5 candles
        
        # Model performance tracking
        self.model_metrics = {
            'rf': {'accuracy': 0, 'predictions': 0, 'correct': 0},
            'xgb': {'mae': 0, 'predictions': 0, 'total_error': 0}
        }
        
        self.logger.info("ML Price Predictor initialized")
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for ML models
        
        Args:
            df: DataFrame with OHLCV and indicators
            
        Returns:
            DataFrame with engineered features
        """
        features = df.copy()
        
        # Price-based features
        features['returns'] = features['close'].pct_change()
        features['log_returns'] = np.log(features['close'] / features['close'].shift(1))
        features['high_low_ratio'] = features['high'] / features['low']
        features['close_open_ratio'] = features['close'] / features['open']
        
        # Volume features
        features['volume_change'] = features['volume'].pct_change()
        features['volume_ma_ratio'] = features['volume'] / features['volume'].rolling(20).mean()
        
        # Volatility features
        features['volatility'] = features['returns'].rolling(20).std()
        features['atr_percent'] = features.get('atr', 0) / features['close']
        
        # Momentum features
        for period in [5, 10, 20, 50]:
            features[f'momentum_{period}'] = features['close'] / features['close'].shift(period) - 1
            features[f'roc_{period}'] = features['close'].pct_change(period)
        
        # Moving average convergence/divergence
        features['price_to_sma_20'] = features['close'] / features['close'].rolling(20).mean()
        features['price_to_sma_50'] = features['close'] / features['close'].rolling(50).mean()
        features['sma_20_50_ratio'] = features['close'].rolling(20).mean() / features['close'].rolling(50).mean()
        
        # RSI-based features (if available)
        if 'rsi' in features.columns:
            features['rsi_change'] = features['rsi'].diff()
            features['rsi_momentum'] = features['rsi'].diff(5)
        
        # MACD-based features (if available)
        if 'macd' in features.columns and 'macd_signal' in features.columns:
            features['macd_histogram'] = features['macd'] - features['macd_signal']
            features['macd_cross'] = (features['macd'] > features['macd_signal']).astype(int)
        
        # Bollinger Bands features (if available)
        if all(col in features.columns for col in ['bb_upper', 'bb_middle', 'bb_lower']):
            features['bb_position'] = (features['close'] - features['bb_lower']) / \
                                      (features['bb_upper'] - features['bb_lower'])
            features['bb_width'] = (features['bb_upper'] - features['bb_lower']) / features['bb_middle']
        
        # Trend features
        for period in [10, 20, 50]:
            features[f'trend_{period}'] = np.where(
                features['close'] > features['close'].shift(period), 1, -1
            )
        
        # Time-based features
        if 'timestamp' in features.columns:
            features['hour'] = pd.to_datetime(features['timestamp']).dt.hour
            features['day_of_week'] = pd.to_datetime(features['timestamp']).dt.dayofweek
            features['day_of_month'] = pd.to_datetime(features['timestamp']).dt.day
        
        # Fill NaN values
        features = features.fillna(method='ffill').fillna(0)
        
        return features
    
    def create_sequences(self, features: pd.DataFrame, 
                        target_col: str = 'close') -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for time series prediction
        
        Args:
            features: Feature DataFrame
            target_col: Column to predict
            
        Returns:
            X (features), y (targets)
        """
        X, y = [], []
        
        # Select numeric columns only
        numeric_features = features.select_dtypes(include=[np.number]).columns.tolist()
        
        # Remove target from features if present
        if target_col in numeric_features:
            numeric_features.remove(target_col)
        
        feature_data = features[numeric_features].values
        target_data = features[target_col].values
        
        for i in range(self.sequence_length, len(features) - self.prediction_horizon):
            X.append(feature_data[i-self.sequence_length:i])
            
            # Target: future return
            future_price = target_data[i + self.prediction_horizon]
            current_price = target_data[i]
            future_return = (future_price - current_price) / current_price
            
            y.append(future_return)
        
        return np.array(X), np.array(y)
    
    def train_random_forest(self, df: pd.DataFrame) -> float:
        """
        Train Random Forest classifier for price direction
        
        Args:
            df: DataFrame with features and price data
            
        Returns:
            Model accuracy
        """
        self.logger.info("Training Random Forest classifier...")
        
        # Prepare features
        features = self.prepare_features(df)
        
        # Create classification targets (UP/DOWN/NEUTRAL)
        features['future_return'] = features['close'].shift(-self.prediction_horizon).pct_change()
        
        # Define thresholds
        up_threshold = 0.01  # 1% gain = UP
        down_threshold = -0.01  # 1% loss = DOWN
        
        features['target'] = 0  # NEUTRAL
        features.loc[features['future_return'] > up_threshold, 'target'] = 1  # UP
        features.loc[features['future_return'] < down_threshold, 'target'] = -1  # DOWN
        
        # Remove NaN rows
        features = features.dropna()
        
        if len(features) < 100:
            self.logger.warning("Not enough data to train Random Forest")
            return 0.0
        
        # Select features
        feature_cols = [col for col in features.columns 
                       if col not in ['target', 'future_return', 'timestamp', 'close', 'open', 'high', 'low', 'volume']]
        
        X = features[feature_cols].values
        y = features['target'].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, shuffle=False
        )
        
        # Train model
        self.rf_classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=20,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1
        )
        
        self.rf_classifier.fit(X_train, y_train)
        
        # Evaluate
        accuracy = self.rf_classifier.score(X_test, y_test)
        
        self.logger.info(f"✅ Random Forest trained - Accuracy: {accuracy*100:.1f}%")
        
        # Save model
        model_path = os.path.join(self.model_dir, 'rf_classifier.joblib')
        joblib.dump(self.rf_classifier, model_path)
        joblib.dump(self.scaler, os.path.join(self.model_dir, 'scaler.joblib'))
        
        # Store feature names
        self.feature_cols = feature_cols
        joblib.dump(feature_cols, os.path.join(self.model_dir, 'feature_cols.joblib'))
        
        return accuracy
    
    def train_xgboost(self, df: pd.DataFrame) -> float:
        """
        Train XGBoost regressor for price targets
        
        Args:
            df: DataFrame with features
            
        Returns:
            Model MAE (Mean Absolute Error)
        """
        try:
            from xgboost import XGBRegressor
        except ImportError:
            self.logger.warning("XGBoost not installed. Install with: pip install xgboost")
            return 0.0
        
        self.logger.info("Training XGBoost regressor...")
        
        # Prepare features
        features = self.prepare_features(df)
        
        # Target: future price
        features['target'] = features['close'].shift(-self.prediction_horizon)
        features = features.dropna()
        
        if len(features) < 100:
            self.logger.warning("Not enough data to train XGBoost")
            return 0.0
        
        # Select features
        feature_cols = [col for col in features.columns 
                       if col not in ['target', 'timestamp', 'close', 'open', 'high', 'low', 'volume']]
        
        X = features[feature_cols].values
        y = features['target'].values
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, shuffle=False
        )
        
        # Train model
        self.xgb_regressor = XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        )
        
        self.xgb_regressor.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.xgb_regressor.predict(X_test)
        mae = np.mean(np.abs(y_pred - y_test))
        mae_percent = (mae / np.mean(y_test)) * 100
        
        self.logger.info(f"✅ XGBoost trained - MAE: ${mae:.2f} ({mae_percent:.2f}%)")
        
        # Save model
        model_path = os.path.join(self.model_dir, 'xgb_regressor.joblib')
        joblib.dump(self.xgb_regressor, model_path)
        
        return mae
    
    def load_models(self) -> bool:
        """
        Load trained models from disk
        
        Returns:
            True if successful
        """
        try:
            rf_path = os.path.join(self.model_dir, 'rf_classifier.joblib')
            xgb_path = os.path.join(self.model_dir, 'xgb_regressor.joblib')
            scaler_path = os.path.join(self.model_dir, 'scaler.joblib')
            features_path = os.path.join(self.model_dir, 'feature_cols.joblib')
            
            if all(os.path.exists(p) for p in [rf_path, scaler_path, features_path]):
                self.rf_classifier = joblib.load(rf_path)
                self.scaler = joblib.load(scaler_path)
                self.feature_cols = joblib.load(features_path)
                
                if os.path.exists(xgb_path):
                    self.xgb_regressor = joblib.load(xgb_path)
                
                self.logger.info("✅ ML models loaded successfully")
                return True
            else:
                self.logger.warning("⚠️ Model files not found. Need to train first.")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to load models: {e}")
            return False
    
    def predict(self, df: pd.DataFrame) -> Dict:
        """
        Make predictions using ensemble models
        
        Args:
            df: DataFrame with recent market data
            
        Returns:
            Dictionary with predictions and confidence
        """
        if self.rf_classifier is None:
            if not self.load_models():
                return {
                    'direction': 'NEUTRAL',
                    'confidence': 0.0,
                    'price_target': None,
                    'error': 'Models not trained'
                }
        
        try:
            # Prepare features
            features = self.prepare_features(df)
            
            # Get latest features
            latest = features[self.feature_cols].iloc[-1:].values
            latest_scaled = self.scaler.transform(latest)
            
            # Random Forest prediction
            rf_proba = self.rf_classifier.predict_proba(latest_scaled)[0]
            rf_pred = self.rf_classifier.predict(latest_scaled)[0]
            
            # Map prediction to direction
            direction_map = {-1: 'DOWN', 0: 'NEUTRAL', 1: 'UP'}
            direction = direction_map[rf_pred]
            
            # Confidence = max probability
            confidence = float(np.max(rf_proba))
            
            # XGBoost prediction (if available)
            price_target = None
            if self.xgb_regressor is not None:
                price_target = float(self.xgb_regressor.predict(latest_scaled)[0])
            
            # Update metrics
            self.model_metrics['rf']['predictions'] += 1
            
            result = {
                'direction': direction,
                'confidence': confidence,
                'probabilities': {
                    'down': float(rf_proba[0]),
                    'neutral': float(rf_proba[1]) if len(rf_proba) > 2 else 0.0,
                    'up': float(rf_proba[-1])
                },
                'price_target': price_target,
                'current_price': float(df['close'].iloc[-1]),
                'prediction_horizon': f'{self.prediction_horizon} candles',
                'model_accuracy': f"{self.model_metrics['rf']['accuracy']:.1%}" if self.model_metrics['rf']['predictions'] > 0 else 'N/A'
            }
            
            self.logger.debug(
                f"ML Prediction: {direction} ({confidence*100:.0f}% confidence)"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Prediction failed: {e}")
            return {
                'direction': 'NEUTRAL',
                'confidence': 0.0,
                'price_target': None,
                'error': str(e)
            }
    
    def update_accuracy(self, prediction: str, actual: str):
        """
        Update model accuracy based on actual outcome
        
        Args:
            prediction: Predicted direction (UP/DOWN/NEUTRAL)
            actual: Actual direction
        """
        if prediction == actual:
            self.model_metrics['rf']['correct'] += 1
        
        total = self.model_metrics['rf']['predictions']
        if total > 0:
            self.model_metrics['rf']['accuracy'] = self.model_metrics['rf']['correct'] / total
    
    def get_feature_importance(self) -> pd.DataFrame:
        """
        Get feature importance from Random Forest
        
        Returns:
            DataFrame with feature importance
        """
        if self.rf_classifier is None or not hasattr(self, 'feature_cols'):
            return pd.DataFrame()
        
        importance = self.rf_classifier.feature_importances_
        
        df = pd.DataFrame({
            'feature': self.feature_cols,
            'importance': importance
        })
        
        return df.sort_values('importance', ascending=False)


# Example usage
if __name__ == "__main__":
    from data_fetcher import DataFetcher
    from analyzer import TechnicalAnalyzer
    
    print("\n" + "="*60)
    print("MACHINE LEARNING PRICE PREDICTOR")
    print("="*60)
    
    # Fetch data
    fetcher = DataFetcher()
    df = fetcher.fetch_ohlcv('BTC/USDT', timeframe='1h', limit=500)
    
    if df is not None:
        # Add technical indicators
        analyzer = TechnicalAnalyzer()
        df = analyzer.calculate_all_indicators(df)
        
        # Initialize ML predictor
        predictor = MLPricePredictor()
        
        # Train models
        print("\n🤖 Training Random Forest...")
        rf_accuracy = predictor.train_random_forest(df)
        print(f"  Accuracy: {rf_accuracy*100:.1f}%")
        
        print("\n🤖 Training XGBoost...")
        xgb_mae = predictor.train_xgboost(df)
        print(f"  MAE: ${xgb_mae:.2f}")
        
        # Make prediction
        print("\n🔮 Making prediction...")
        prediction = predictor.predict(df)
        
        print(f"\n  Direction: {prediction['direction']}")
        print(f"  Confidence: {prediction['confidence']*100:.0f}%")
        print(f"  Current Price: ${prediction['current_price']:.2f}")
        if prediction['price_target']:
            print(f"  Price Target: ${prediction['price_target']:.2f}")
        
        # Feature importance
        print("\n📊 Top 10 Most Important Features:")
        importance = predictor.get_feature_importance().head(10)
        for _, row in importance.iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")
        
        print("\n✅ ML predictor ready!")
    else:
        print("❌ Failed to fetch data")
