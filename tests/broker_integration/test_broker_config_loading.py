from dataclasses import dataclass


@dataclass
class FakeIBConfig:
    host: str
    port: int
    client_id: int
    paper_trading: bool


@dataclass
class FakeBrokerConfig:
    active_broker: str
    interactive_brokers: FakeIBConfig


def test_config_loading():
    config = FakeBrokerConfig(
        active_broker="interactive_brokers",
        interactive_brokers=FakeIBConfig(
            host="127.0.0.1",
            port=7497,
            client_id=1,
            paper_trading=True,
        ),
    )

    assert config.active_broker == "interactive_brokers"
    assert config.interactive_brokers.host == "127.0.0.1"
    assert config.interactive_brokers.port == 7497
    assert config.interactive_brokers.client_id == 1
    assert config.interactive_brokers.paper_trading is True
