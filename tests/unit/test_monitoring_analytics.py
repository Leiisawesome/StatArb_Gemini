import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from core_structure.analytics.monitoring_analytics import MonitoringAnalyticsEngine, AlertSeverity, AlertType


@pytest.mark.asyncio
async def test_create_and_acknowledge_alerts():
    engine = MonitoringAnalyticsEngine()

    alert = await engine.create_alert(
        severity=AlertSeverity.WARNING,
        alert_type=AlertType.SYSTEM,
        title="Test Alert",
        message="This is a test"
    )

    assert alert in engine.alerts
    assert alert.acknowledged == False

    # Acknowledge
    ok = engine.acknowledge_alert(alert.id)
    assert ok is True
    assert alert.acknowledged is True

    # Resolve
    ok2 = engine.resolve_alert(alert.id)
    assert ok2 is True
    assert alert.resolved is True


def test_prepare_anomaly_features_and_classify():
    engine = MonitoringAnalyticsEngine()

    # Create a numeric DataFrame
    dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
    data = pd.DataFrame({'value': np.random.normal(0, 1, len(dates))}, index=dates)

    features = engine._prepare_anomaly_features(data)
    assert features is not None
    assert features.shape[0] == len(dates)

    atype = engine._classify_anomaly_type('price')
    assert atype.name == 'PRICE_ANOMALY'
