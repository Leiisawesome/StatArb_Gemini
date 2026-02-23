import pytest
from datetime import datetime

from core_engine.type_definitions.broker_types import AccountInfo


class FakeAccountAdapter:
    async def connect(self):
        return True

    async def disconnect(self):
        return None

    async def get_account_info(self):
        return AccountInfo(
            account_id="DU123456",
            cash=100_000.0,
            buying_power=200_000.0,
            portfolio_value=100_000.0,
            equity=100_000.0,
            status="active",
            timestamp=datetime.now(),
        )


@pytest.mark.asyncio
async def test_account_information_querying():
    adapter = FakeAccountAdapter()
    assert await adapter.connect() is True

    account_info = await adapter.get_account_info()

    assert account_info.account_id == "DU123456"
    assert account_info.cash >= 0
    assert account_info.buying_power >= 0
    assert account_info.portfolio_value >= 0
    assert account_info.equity >= 0
    assert account_info.currency == "USD"
    assert account_info.status == "active"

    age_seconds = (datetime.now() - account_info.timestamp).total_seconds()
    assert age_seconds < 5

    await adapter.disconnect()
