import pytest


class FakeConnectionAdapter:
    def __init__(self, should_connect: bool):
        self.should_connect = should_connect

    async def connect(self):
        return self.should_connect


@pytest.mark.asyncio
async def test_ibkr_connection_errors():
    bad_adapter = FakeConnectionAdapter(should_connect=False)
    ok_adapter = FakeConnectionAdapter(should_connect=True)

    assert await bad_adapter.connect() is False
    assert await ok_adapter.connect() is True
