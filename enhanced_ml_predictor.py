"""
Enhanced ML Predictor with Periodic Retraining and Ensemble Logic
Combines Random Forest, XGBoost with technical indicators for robust predictions
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import joblib
import json
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    
from logger import setup_logger

logger = setup_logger('enhanced_ml_predictor')


@dataclass
class ModelPerformance:
    """Model performance metrics"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    sharpe_ratio: float
    profit_factor: float
    win_rate: float
    last_updated: datetime
    training_samples: int
    feature_importance: Dict[str, float] = None


@dataclass
class PredictionResult:
    """ML prediction result with metadata"""
    signal: float  # -1 to 1
    confidence: float  # 0 to 1
    probabilities: Dict[str, float]  # class probabilities
    model_votes: Dict[str, float]  # individual model predictions
    reasoning: List[str]


class EnhancedMLPredictor:
    """
    Enhanced ML predictor with ensemble logic and periodic retraining
    """
    
    def __init__(
        self,
        model_dir: str = './models',
        retrain_interval_hours: int = 168,  # 1 week
        min_training_samples: int = 500,
        ensemble_weights: Optional[Dict[str, float]] = None,
        use_cross_validation: bool = True,
        cv_folds: int = 5
    ):
        """
        Initialize enhanced ML predictor
        
        Args:
            model_dir: Directory to save/load models
            retrain_interval_hours: Hours between retraining
            min_training_samples: Minimum samples for training
            ensemble_weights: Weights for ensemble models
            use_cross_validation: Use CV for validation
            cv_folds: Number of CV folds
        """
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        
        self.retrain_interval = timedelta(hours=retrain_interval_hours)
        self.min_training_samples = min_training_samples
        self.use_cross_validation = use_cross_validation
        self.cv_folds = cv_folds
        
        # Ensemble weights (default: equal)
        if ensemble_weights is None:
            self.ensemble_weights = {
                'random_forest': 0.4,
                'xgboost': 0.4 if XGBOOST_AVAILABLE else 0.0,
                'technical_score': 0.2
            }
        else:
            self.ensemble_weights = ensemble_weights
        
        # Normalize weights
        total_weight = sum(self.ensemble_weights.values())
        self.ensemble_weights = {k: v/total_weight for k, v in self.ensemble_weights.items()}
        
        # Models
        self.rf_model: Optional[RandomForestClassifier] = None
        self.xgb_model = None
        self.scaler: Optional[StandardScaler] = None
        
        # Performance tracking
        self.performance: Dict[str, ModelPerformance] = {}
        self.last_training_time: Optional[datetime] = None
        self.prediction_cache: Dict[str, Tuple[PredictionResult, datetime]] = {}
        self.cache_ttl = 300  # 5 minutes
        
        # Training data buffer
        self.training_buffer: List[Dict] = []
        self.max_buffer_size = 10000
        
        # Load existing models
        self.load_models()
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare feature matrix from DataFrame
        
        Args:
            df: DataFrame with OHLCV and indicators
            
        Returns:
            DataFrame with features
        """
        features = pd.DataFrame(index=df.index)
        
        # Price features
        features['returns'] = df['close'].pct_change()
        features['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        features['price_momentum_5'] = df['close'].pct_change(5)
        features['price_momentum_10'] = df['close'].pct_change(10)
        
        # Volume features
        if 'volume' in df.columns:
            features['volume_change'] = df['volume'].pct_change()
            features['volume_ma_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        # Technical indicators
        if 'rsi' in df.columns:
            features['rsi'] = df['rsi']
            features['rsi_ma'] = df['rsi'].rolling(5).mean()
            features['rsi_oversold'] = (df['rsi'] < 30).astype(int)
            features['rsi_overbought'] = (df['rsi'] > 70).astype(int)
        
        if 'macd' in df.columns:
            features['macd'] = df['macd']
            features['macd_signal'] = df['macd_signal']
            features['macd_hist'] = df['macd_histogram']
            features['macd_bullish'] = (df['macd'] > df['macd_signal']).astype(int)
        
        if 'bb_upper' in df.columns:
            features['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            features['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        if 'atr' in df.columns:
            features['atr'] = df['atr']
            features['atr_pct'] = df['atr'] / df['close']
        
        # EMA features
        if 'ema_12' in df.columns and 'ema_26' in df.columns:
            features['ema_diff'] = (df['ema_12'] - df['ema_26']) / df['ema_26']
            features['ema_bullish'] = (df['ema_12'] > df['ema_26']).astype(int)
        
        # Stochastic
        if 'stoch_k' in df.columns:
            features['stoch_k'] = df['stoch_k']
            features['stoch_d'] = df['stoch_d']
            features['stoch_oversold'] = (df['stoch_k'] < 20).astype(int)
            features['stoch_overbought'] = (df['stoch_k'] > 80).astype(int)
        
        # Lag features
        for col in ['returns', 'volume_change', 'rsi']:
            if col in features.columns:
                for lag in [1, 2, 3]:
                    features[f'{col}_lag{lag}'] = features[col].shift(lag)
        
        # Rolling statistics
        if 'returns' in features.columns:
            features['returns_mean_5'] = features['returns'].rolling(5).mean()
            features['returns_std_5'] = features['returns'].rolling(5).std()
            features['returns_mean_20'] = features['returns'].rolling(20).mean()
            features['returns_std_20'] = features['returns'].rolling(20).std()
        
        # Drop NaN
        features = features.dropna()
        
        return features
    
    def create_labels(self, df: pd.DataFrame, forward_periods: int = 5) -> pd.Series:
        """
        Create labels for supervised learning
        
        Args:
            df: DataFrame with price data
            forward_periods: Periods to look forward
            
        Returns:
            Series with labels (1=buy, 0=hold, -1=sell)
        """
        future_returns = df['close'].shift(-forward_periods) / df['close'] - 1
        
        # Thresholds for classification
        buy_threshold = 0.02  # 2% gain
        sell_threshold = -0.02  # 2% loss
        
        labels = pd.Series(0, index=df.index)  # Default: hold
        labels[future_returns > buy_threshold] = 1  # Buy
        labels[future_returns < sell_threshold] = -1  # Sell
        
        return labels
    
    def train_random_forest(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ) -> RandomForestClassifier:
        """
        Train Random Forest model
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            
        Returns:
            Trained RF model
        """
        logger.info("Training Random Forest model...")
        
        rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            max_features='sqrt',
            random_state=42,
            n_jobs=-1,
            class_weight='balanced'
        )
        
        rf_model.fit(X_train, y_train)
        
        # Evaluate
        train_score = rf_model.score(X_train, y_train)
        logger.info(f"RF Training accuracy: {train_score:.4f}")
        
        if X_val is not None and y_val is not None:
            val_score = rf_model.score(X_val, y_val)
            logger.info(f"RF Validation accuracy: {val_score:.4f}")
        
        # Cross-validation
        if self.use_cross_validation:
            cv_scores = cross_val_score(rf_model, X_train, y_train, cv=self.cv_folds)
            logger.info(f"RF CV Score: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
        
        return rf_model
    
    def train_xgboost(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None
    ):
        """
        Train XGBoost model
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            
        Returns:
            Trained XGB model
        """
        if not XGBOOST_AVAILABLE:
            logger.warning("XGBoost not available, skipping")
            return None
        
        logger.info("Training XGBoost model...")
        
        # Convert labels to 0, 1, 2 (XGBoost requirement)
        y_train_xgb = y_train + 1  # -1,0,1 -> 0,1,2
        
        xgb_model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=10,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            gamma=0.1,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1,
            objective='multi:softprob',
            num_class=3
        )
        
        eval_set = [(X_train, y_train_xgb)]
        if X_val is not None and y_val is not None:
            y_val_xgb = y_val + 1
            eval_set.append((X_val, y_val_xgb))
        
        xgb_model.fit(
            X_train,
            y_train_xgb,
            eval_set=eval_set,
            early_stopping_rounds=20,
            verbose=False
        )
        
        train_score = xgb_model.score(X_train, y_train_xgb)
        logger.info(f"XGB Training accuracy: {train_score:.4f}")
        
        if X_val is not None and y_val is not None:
            val_score = xgb_model.score(X_val, y_val_xgb)
            logger.info(f"XGB Validation accuracy: {val_score:.4f}")
        
        return xgb_model
    
    def train_models(
        self,
        df: pd.DataFrame,
        force_retrain: bool = False
    ) -> bool:
        """
        Train or retrain models
        
        Args:
            df: DataFrame with OHLCV and indicators
            force_retrain: Force retraining regardless of schedule
            
        Returns:
            True if training was performed
        """
        try:
            # Check if retraining needed
            if not force_retrain:
                if self.last_training_time is not None:
                    time_since_training = datetime.now() - self.last_training_time
                    if time_since_training < self.retrain_interval:
                        logger.debug(
                            f"Retraining not needed yet. "
                            f"Next in {self.retrain_interval - time_since_training}"
                        )
                        return False
            
            logger.info("Starting model training...")
            
            # Prepare features and labels
            features = self.prepare_features(df)
            labels = self.create_labels(df)
            
            # Align features and labels
            common_index = features.index.intersection(labels.index)
            features = features.loc[common_index]
            labels = labels.loc[common_index]
            
            if len(features) < self.min_training_samples:
                logger.warning(
                    f"Insufficient training samples: {len(features)} < {self.min_training_samples}"
                )
                return False
            
            logger.info(f"Training with {len(features)} samples")
            
            # Split data
            X_train, X_val, y_train, y_val = train_test_split(
                features.values,
                labels.values,
                test_size=0.2,
                random_state=42,
                stratify=labels.values
            )
            
            # Scale features
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_val_scaled = self.scaler.transform(X_val)
            
            # Train Random Forest
            self.rf_model = self.train_random_forest(X_train_scaled, y_train, X_val_scaled, y_val)
            
            # Train XGBoost
            if XGBOOST_AVAILABLE and self.ensemble_weights.get('xgboost', 0) > 0:
                self.xgb_model = self.train_xgboost(X_train_scaled, y_train, X_val_scaled, y_val)
            
            # Calculate performance metrics
            self.calculate_performance_metrics(X_val_scaled, y_val, features.columns.tolist())
            
            # Save models
            self.save_models(features.columns.tolist())
            
            self.last_training_time = datetime.now()
            logger.info("✅ Model training completed successfully")
            
            return True
            
        except Exception as e:
            logger.exception(f"Error during model training: {e}")
            return False
    
    def calculate_performance_metrics(
        self,
        X_val: np.ndarray,
        y_val: np.ndarray,
        feature_names: List[str]
    ):
        """Calculate and store performance metrics"""
        try:
            for model_name, model in [
                ('random_forest', self.rf_model),
                ('xgboost', self.xgb_model)
            ]:
                if model is None:
                    continue
                
                # Predictions
                if model_name == 'xgboost':
                    y_pred = model.predict(X_val) - 1  # Convert back to -1,0,1
                    y_val_adj = y_val
                else:
                    y_pred = model.predict(X_val)
                    y_val_adj = y_val
                
                # Metrics
                accuracy = accuracy_score(y_val_adj, y_pred)
                precision = precision_score(y_val_adj, y_pred, average='weighted', zero_division=0)
                recall = recall_score(y_val_adj, y_pred, average='weighted', zero_division=0)
                f1 = f1_score(y_val_adj, y_pred, average='weighted', zero_division=0)
                
                # Feature importance
                if hasattr(model, 'feature_importances_'):
                    importance_dict = dict(zip(feature_names, model.feature_importances_))
                    # Top 10 features
                    importance_dict = dict(
                        sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:10]
                    )
                else:
                    importance_dict = {}
                
                # Store performance
                self.performance[model_name] = ModelPerformance(
                    accuracy=accuracy,
                    precision=precision,
                    recall=recall,
                    f1_score=f1,
                    sharpe_ratio=0.0,  # Would need returns data
                    profit_factor=0.0,  # Would need trade results
                    win_rate=accuracy,
                    last_updated=datetime.now(),
                    training_samples=len(X_val),
                    feature_importance=importance_dict
                )
                
                logger.info(
                    f"{model_name.upper()} - Acc: {accuracy:.3f}, "
                    f"Prec: {precision:.3f}, Rec: {recall:.3f}, F1: {f1:.3f}"
                )
                
        except Exception as e:
            logger.exception(f"Error calculating performance metrics: {e}")
    
    def predict(
        self,
        df: pd.DataFrame,
        use_cache: bool = True
    ) -> PredictionResult:
        """
        Make ensemble prediction
        
        Args:
            df: DataFrame with latest data
            use_cache: Use cached predictions
            
        Returns:
            PredictionResult with ensemble prediction
        """
        try:
            # Check cache
            cache_key = f"{df['close'].iloc[-1]}_{df.index[-1]}"
            if use_cache and cache_key in self.prediction_cache:
                cached_result, cache_time = self.prediction_cache[cache_key]
                if (datetime.now() - cache_time).total_seconds() < self.cache_ttl:
                    logger.debug("Using cached prediction")
                    return cached_result
            
            # Check if models are trained
            if self.rf_model is None or self.scaler is None:
                logger.warning("Models not trained, returning neutral prediction")
                return PredictionResult(
                    signal=0.0,
                    confidence=0.3,
                    probabilities={'buy': 0.33, 'hold': 0.34, 'sell': 0.33},
                    model_votes={},
                    reasoning=["Models not trained yet"]
                )
            
            # Prepare features
            features = self.prepare_features(df)
            if features.empty:
                logger.warning("No valid features, returning neutral")
                return PredictionResult(
                    signal=0.0,
                    confidence=0.3,
                    probabilities={'buy': 0.33, 'hold': 0.34, 'sell': 0.33},
                    model_votes={},
                    reasoning=["Insufficient feature data"]
                )
            
            latest_features = features.iloc[-1:].values
            latest_features_scaled = self.scaler.transform(latest_features)
            
            # Collect model predictions
            model_votes = {}
            probabilities_list = []
            reasoning = []
            
            # Random Forest prediction
            if self.rf_model is not None:
                rf_proba = self.rf_model.predict_proba(latest_features_scaled)[0]
                rf_pred = self.rf_model.predict(latest_features_scaled)[0]
                model_votes['random_forest'] = float(rf_pred)
                probabilities_list.append(rf_proba)
                reasoning.append(
                    f"RF: {['Sell', 'Hold', 'Buy'][int(rf_pred)+1]} "
                    f"(conf: {max(rf_proba):.2f})"
                )
            
            # XGBoost prediction
            if self.xgb_model is not None:
                xgb_proba = self.xgb_model.predict_proba(latest_features_scaled)[0]
                xgb_pred = self.xgb_model.predict(latest_features_scaled)[0] - 1
                model_votes['xgboost'] = float(xgb_pred)
                probabilities_list.append(xgb_proba)
                reasoning.append(
                    f"XGB: {['Sell', 'Hold', 'Buy'][int(xgb_pred)+1]} "
                    f"(conf: {max(xgb_proba):.2f})"
                )
            
            # Technical score (simple heuristic)
            tech_score = self.calculate_technical_score(df)
            model_votes['technical_score'] = tech_score
            reasoning.append(f"Technical score: {tech_score:.2f}")
            
            # Ensemble weighted vote
            ensemble_signal = sum(
                vote * self.ensemble_weights.get(name, 0)
                for name, vote in model_votes.items()
            )
            
            # Average probabilities
            if probabilities_list:
                avg_proba = np.mean(probabilities_list, axis=0)
                probabilities = {
                    'sell': float(avg_proba[0]),
                    'hold': float(avg_proba[1]),
                    'buy': float(avg_proba[2])
                }
                confidence = float(max(avg_proba))
            else:
                probabilities = {'buy': 0.33, 'hold': 0.34, 'sell': 0.33}
                confidence = 0.5
            
            result = PredictionResult(
                signal=float(np.clip(ensemble_signal, -1, 1)),
                confidence=confidence,
                probabilities=probabilities,
                model_votes=model_votes,
                reasoning=reasoning
            )
            
            # Cache result
            self.prediction_cache[cache_key] = (result, datetime.now())
            
            return result
            
        except Exception as e:
            logger.exception(f"Error making prediction: {e}")
            return PredictionResult(
                signal=0.0,
                confidence=0.3,
                probabilities={'buy': 0.33, 'hold': 0.34, 'sell': 0.33},
                model_votes={},
                reasoning=[f"Error: {str(e)}"]
            )
    
    def calculate_technical_score(self, df: pd.DataFrame) -> float:
        """
        Calculate simple technical score from indicators
        
        Returns:
            Score from -1 to 1
        """
        score = 0.0
        count = 0
        
        # RSI
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            if rsi < 30:
                score += 1
            elif rsi > 70:
                score -= 1
            else:
                score += (50 - rsi) / 20  # Linear between 30-70
            count += 1
        
        # MACD
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            if df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]:
                score += 0.5
            else:
                score -= 0.5
            count += 1
        
        # EMA trend
        if 'ema_12' in df.columns and 'ema_26' in df.columns:
            if df['ema_12'].iloc[-1] > df['ema_26'].iloc[-1]:
                score += 0.5
            else:
                score -= 0.5
            count += 1
        
        return score / count if count > 0 else 0.0
    
    def save_models(self, feature_names: List[str]):
        """Save models and metadata"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save Random Forest
            if self.rf_model is not None:
                rf_path = self.model_dir / f'rf_model_{timestamp}.joblib'
                joblib.dump(self.rf_model, rf_path)
                logger.info(f"RF model saved to {rf_path}")
            
            # Save XGBoost
            if self.xgb_model is not None:
                xgb_path = self.model_dir / f'xgb_model_{timestamp}.json'
                self.xgb_model.save_model(str(xgb_path))
                logger.info(f"XGB model saved to {xgb_path}")
            
            # Save scaler
            if self.scaler is not None:
                scaler_path = self.model_dir / f'scaler_{timestamp}.joblib'
                joblib.dump(self.scaler, scaler_path)
            
            # Save metadata
            metadata = {
                'timestamp': timestamp,
                'feature_names': feature_names,
                'performance': {
                    name: {
                        'accuracy': perf.accuracy,
                        'f1_score': perf.f1_score,
                        'feature_importance': perf.feature_importance
                    }
                    for name, perf in self.performance.items()
                },
                'ensemble_weights': self.ensemble_weights
            }
            
            metadata_path = self.model_dir / f'metadata_{timestamp}.json'
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info("Model metadata saved")
            
        except Exception as e:
            logger.exception(f"Error saving models: {e}")
    
    def load_models(self):
        """Load latest models"""
        try:
            # Find latest models
            rf_models = sorted(self.model_dir.glob('rf_model_*.joblib'))
            xgb_models = sorted(self.model_dir.glob('xgb_model_*.json'))
            scalers = sorted(self.model_dir.glob('scaler_*.joblib'))
            
            if rf_models:
                self.rf_model = joblib.load(rf_models[-1])
                logger.info(f"Loaded RF model: {rf_models[-1].name}")
            
            if xgb_models and XGBOOST_AVAILABLE:
                self.xgb_model = xgb.XGBClassifier()
                self.xgb_model.load_model(str(xgb_models[-1]))
                logger.info(f"Loaded XGB model: {xgb_models[-1].name}")
            
            if scalers:
                self.scaler = joblib.load(scalers[-1])
                logger.info(f"Loaded scaler: {scalers[-1].name}")
            
            # Load metadata
            metadata_files = sorted(self.model_dir.glob('metadata_*.json'))
            if metadata_files:
                with open(metadata_files[-1], 'r') as f:
                    metadata = json.load(f)
                    logger.info(f"Loaded metadata from {metadata_files[-1].name}")
                    
        except Exception as e:
            logger.exception(f"Error loading models: {e}")


# Example usage
if __name__ == '__main__':
    predictor = EnhancedMLPredictor(
        model_dir='./models',
        retrain_interval_hours=168,
        ensemble_weights={'random_forest': 0.5, 'xgboost': 0.5}
    )
    
    # Create sample data
    dates = pd.date_range('2023-01-01', periods=1000, freq='1H')
    df = pd.DataFrame({
        'close': 100 + np.cumsum(np.random.randn(1000) * 0.5),
        'volume': np.random.randint(1000, 10000, 1000),
        'rsi': np.random.uniform(20, 80, 1000),
        'macd': np.random.randn(1000),
        'macd_signal': np.random.randn(1000),
        'macd_histogram': np.random.randn(1000),
        'ema_12': 100 + np.cumsum(np.random.randn(1000) * 0.3),
        'ema_26': 100 + np.cumsum(np.random.randn(1000) * 0.4),
        'atr': np.random.uniform(1, 3, 1000)
    }, index=dates)
    
    # Train models
    success = predictor.train_models(df, force_retrain=True)
    print(f"Training success: {success}")
    
    # Make prediction
    prediction = predictor.predict(df)
    print(f"\nPrediction:")
    print(f"  Signal: {prediction.signal:.3f}")
    print(f"  Confidence: {prediction.confidence:.3f}")
    print(f"  Probabilities: {prediction.probabilities}")
    print(f"  Reasoning: {prediction.reasoning}")
