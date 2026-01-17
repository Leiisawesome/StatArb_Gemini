
import asyncio
import os
from pathlib import Path
from core_engine.system.circuit_breakers import TradingCircuitBreakers, CircuitBreakerConfig, CircuitBreakerLevel

async def test_external_kill_switch():
    print("Testing External Kill Switch...")
    config = CircuitBreakerConfig(external_kill_switch_path="test_kill_switch.stop")
    cb = TradingCircuitBreakers(config)
    
    # 1. Check normal state
    status = await cb.check_circuit_breakers()
    print(f"Normal State: Level={status.level}, Can Trade={status.can_trade}")
    assert status.level == CircuitBreakerLevel.NORMAL
    
    # 2. Trigger kill switch
    print("Creating kill switch file...")
    Path("test_kill_switch.stop").touch()
    
    try:
        statusRed = await cb.check_circuit_breakers()
        print(f"Kill State: Level={statusRed.level}, Can Trade={statusRed.can_trade}, Reason={statusRed.halt_reason}")
        assert statusRed.level == CircuitBreakerLevel.HALT
        assert statusRed.can_trade == False
        assert "External kill switch" in statusRed.halt_reason
    finally:
        os.remove("test_kill_switch.stop")
        print("Test file removed.")

if __name__ == "__main__":
    asyncio.run(test_external_kill_switch())
