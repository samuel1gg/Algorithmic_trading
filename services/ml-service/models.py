"""ML models for price prediction and anomaly detection."""
import numpy as np
import pandas as pd
from tensorflow import keras
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import os
from typing import Tuple, Optional
from shared.logger import setup_logger

logger = setup_logger(__name__)


class PricePredictor:
    """LSTM-based price prediction model."""
    
    def __init__(self, sequence_length: int = 30, model_path: Optional[str] = None):
        self.sequence_length = sequence_length
        self.model = None
        self.scaler = MinMaxScaler()
        self.model_path = model_path or "models/lstm_price_predictor.h5"
        self.scaler_path = "models/price_scaler.pkl"
        
        # Create models directory if it doesn't exist
        os.makedirs("models", exist_ok=True)
        
        if os.path.exists(self.model_path):
            self.load_model()
        else:
            self.build_model()
    
    def build_model(self):
        """Build LSTM model architecture."""
        self.model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(self.sequence_length, 1)),
            Dropout(0.2),
            LSTM(50, return_sequences=True),
            Dropout(0.2),
            LSTM(50),
            Dropout(0.2),
            Dense(1)
        ])
        
        self.model.compile(
            optimizer='adam',
            loss='mean_squared_error',
            metrics=['mae']
        )
        logger.info("LSTM model built")
    
    def prepare_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for training."""
        # Use closing prices
        prices = data['close'].values.reshape(-1, 1)
        
        # Scale data
        scaled_prices = self.scaler.fit_transform(prices)
        
        # Create sequences
        X, y = [], []
        for i in range(self.sequence_length, len(scaled_prices)):
            X.append(scaled_prices[i-self.sequence_length:i, 0])
            y.append(scaled_prices[i, 0])
        
        return np.array(X), np.array(y)
    
    def train(self, data: pd.DataFrame, epochs: int = 50, batch_size: int = 32):
        """Train the model."""
        logger.info("Training LSTM model...")
        X, y = self.prepare_data(data)
        
        # Reshape for LSTM
        X = X.reshape((X.shape[0], X.shape[1], 1))
        
        # Split data
        split = int(0.8 * len(X))
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        # Train
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(X_test, y_test),
            verbose=1
        )
        
        # Save model
        self.save_model()
        logger.info("Model training completed")
        
        return history
    
    def predict(self, data: pd.DataFrame) -> float:
        """Predict next price."""
        if len(data) < self.sequence_length:
            raise ValueError(f"Need at least {self.sequence_length} data points")
        
        # Get last sequence_length points
        recent_data = data['close'].tail(self.sequence_length).values.reshape(-1, 1)
        scaled_data = self.scaler.transform(recent_data)
        
        # Reshape for prediction
        X = scaled_data.reshape(1, self.sequence_length, 1)
        
        # Predict
        prediction = self.model.predict(X, verbose=0)
        
        # Inverse transform
        predicted_price = self.scaler.inverse_transform(prediction)[0][0]
        
        return float(predicted_price)
    
    def save_model(self):
        """Save model and scaler."""
        self.model.save(self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        logger.info("Model saved")
    
    def load_model(self):
        """Load model and scaler."""
        self.model = load_model(self.model_path)
        self.scaler = joblib.load(self.scaler_path)
        logger.info("Model loaded")


class AnomalyDetector:
    """Isolation Forest-based anomaly detection."""
    
    def __init__(self, contamination: float = 0.1, model_path: Optional[str] = None):
        self.contamination = contamination
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.scaler = StandardScaler()
        self.model_path = model_path or "models/anomaly_detector.pkl"
        self.scaler_path = "models/anomaly_scaler.pkl"
        
        os.makedirs("models", exist_ok=True)
        
        if os.path.exists(self.model_path):
            self.load_model()
    
    def extract_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extract features for anomaly detection."""
        features = []
        
        # Price features
        features.append(data['close'].values)
        features.append(data['volume'].values)
        
        # Technical indicators
        if len(data) > 1:
            returns = data['close'].pct_change().fillna(0).values
            features.append(returns)
            
            # Volatility (rolling std of returns)
            if len(data) > 10:
                volatility = returns.rolling(window=10).std().fillna(0).values
                features.append(volatility)
            else:
                features.append(np.zeros(len(data)))
        else:
            features.append(np.zeros(len(data)))
            features.append(np.zeros(len(data)))
        
        # High-Low spread
        spread = ((data['high'] - data['low']) / data['close']).values
        features.append(spread)
        
        # Volume change
        if len(data) > 1:
            volume_change = data['volume'].pct_change().fillna(0).values
            features.append(volume_change)
        else:
            features.append(np.zeros(len(data)))
        
        # Stack features
        feature_matrix = np.column_stack(features)
        
        return feature_matrix
    
    def train(self, data: pd.DataFrame):
        """Train the anomaly detector."""
        logger.info("Training anomaly detector...")
        features = self.extract_features(data)
        
        # Scale features
        scaled_features = self.scaler.fit_transform(features)
        
        # Train model
        self.model.fit(scaled_features)
        
        # Save model
        self.save_model()
        logger.info("Anomaly detector trained")
    
    def detect(self, data: pd.DataFrame) -> Tuple[bool, float]:
        """Detect anomalies in data."""
        features = self.extract_features(data)
        
        # Use last data point
        last_features = features[-1:].reshape(1, -1)
        scaled_features = self.scaler.transform(last_features)
        
        # Predict
        prediction = self.model.predict(scaled_features)
        score = self.model.score_samples(scaled_features)[0]
        
        # Anomaly if prediction is -1
        is_anomaly = prediction[0] == -1
        anomaly_score = float(score)
        
        return is_anomaly, anomaly_score
    
    def save_model(self):
        """Save model and scaler."""
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        logger.info("Anomaly detector saved")
    
    def load_model(self):
        """Load model and scaler."""
        self.model = joblib.load(self.model_path)
        self.scaler = joblib.load(self.scaler_path)
        logger.info("Anomaly detector loaded")

