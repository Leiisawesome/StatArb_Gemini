"""
Classifier ensemble logic for trade confirmation.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from typing import Tuple

def generate_features_and_labels(spread_series: pd.Series, lookahead_period: int = 20) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Generates features and labels for the classifier using vectorized operations.
    Label is 1 if the spread crosses zero within the lookahead period, 0 otherwise.
    """
    features = pd.DataFrame(index=spread_series.index)
    features['spread'] = spread_series
    features['spread_lag_1'] = spread_series.shift(1)
    features['volatility_10d'] = spread_series.rolling(window=10).std()
    
    current_sign = np.sign(spread_series)
    future_min = spread_series.shift(-lookahead_period).rolling(window=lookahead_period).min()
    future_max = spread_series.shift(-lookahead_period).rolling(window=lookahead_period).max()
    
    reverted = (current_sign != 0) & ((np.sign(future_min) != current_sign) | (np.sign(future_max) != current_sign))
    labels = reverted.astype(int)
    
    data = pd.concat([features, labels.rename('label')], axis=1).dropna()
    return data.drop('label', axis=1), data['label']

def train_classifier(spread_series: pd.Series) -> RandomForestClassifier | None:
    """
    Trains a Random Forest classifier to predict successful trades.
    """
    X, y = generate_features_and_labels(spread_series)
    
    if len(X) < 50 or y.nunique() < 2:
        print("Warning: Not enough data or only one class to train classifier. Skipping.")
        return None
        
    clf = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42, class_weight='balanced')
    clf.fit(X, y)
    print("Classifier trained successfully.")
    return clf 