import pytest


class FakeIBKRAdapter:
    def __init__(self, can_connect: bool = True):
        self.can_connect = can_connect
        self.connected = False

    async def connect(self):
        self.connected = self.can_connect
        return self.can_connect

    async def disconnect(self):
        self.connected = False

    async def check_connection_health(self):
        return {
            "connected": self.connected,
            "status": "healthy" if self.connected else "disconnected",
            "broker": "Interactive Brokers",
        }


@pytest.mark.asyncio
async def test_ibkr_connection():
    adapter = FakeIBKRAdapter(can_connect=True)

    assert await adapter.connect() is True

    health = await adapter.check_connection_health()
    assert health["connected"] is True
    assert health["status"] == "healthy"
    assert health["broker"] == "Interactive Brokers"

    await adapter.disconnect()
    health_after = await adapter.check_connection_health()
    assert health_after["connected"] is False
