"""
IBKR Configuration Loading Test

Tests:
- Configuration file loading
- Environment variable parsing
- IBKR config validation
- Risk limits validation
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core_engine.config.broker_config import load_broker_config

def test_config_loading():
    """Test configuration loads correctly from .env file"""
    print("=" * 60)
    print("IBKR Configuration Loading Test")
    print("=" * 60)

    try:
        # Load configuration
        print("\n⏳ Loading configuration from .env...")
        config = load_broker_config()

        # Test IBKR config
        print("\n🔧 Testing Interactive Brokers Configuration:")
        ibkr_config = config.interactive_brokers

        # Check that connection parameters are loaded
        if not ibkr_config.host:
            print("❌ IBKR_HOST not found in .env")
            assert False, "IBKR_HOST not found in .env"

        if not ibkr_config.port:
            print("❌ IBKR_PORT not found in .env")
            assert False, "IBKR_PORT not found in .env"

        if ibkr_config.client_id is None:
            print("❌ IBKR_CLIENT_ID not found in .env")
            assert False, "IBKR_CLIENT_ID not found in .env"

        # Display config
        print(f"   ✓ Host: {ibkr_config.host}")
        print(f"   ✓ Port: {ibkr_config.port}")
        print(f"   ✓ Client ID: {ibkr_config.client_id}")
        print(f"   ✓ Paper Trading: {ibkr_config.paper_trading}")

        # Validate configuration
        print("\n🔍 Validating IBKR Configuration:")
        if ibkr_config.validate():
            print("   ✅ Configuration validation: PASSED")
        else:
            print("   ❌ Configuration validation: FAILED")
            assert False, "Configuration validation failed"

        # Test risk limits
        print("\n📊 Testing Risk Limits:")
        risk_limits = config.risk_limits

        print(f"   Max Position Size: {risk_limits.max_position_size} shares")
        print(f"   Max Position Value: ${risk_limits.max_position_value:,.2f}")
        print(f"   Max Daily Trades: {risk_limits.max_daily_trades}")
        print(f"   Max Daily Loss: ${risk_limits.max_daily_loss:.2f}")
        print(f"   Paper Trading Only: {risk_limits.paper_trading_only}")
        print(f"   Manual Approval Required: {risk_limits.require_manual_approval}")

        # Validate risk limits
        print("\n🔍 Validating Risk Limits:")
        if risk_limits.validate():
            print("   ✅ Risk limits validation: PASSED")
        else:
            print("   ❌ Risk limits validation: FAILED")
            assert False, "Risk limits validation failed"

        # Test trading mode
        print("\n🎯 Testing Trading Mode:")
        trading_mode = config.trading_mode
        print(f"   Current Mode: {trading_mode.value}")

        if trading_mode.value == "paper":
            print("   ✅ Paper trading mode confirmed")
        else:
            print("   ⚠️  WARNING: Not in paper trading mode!")

        print("\n" + "=" * 60)
        print("✅ IBKR Configuration Test: SUCCESS")
        print("=" * 60)
        print("\n📝 Next Steps:")
        print("   1. Verify your IBKR TWS/Gateway is running")
        print("   2. Run connection test: python tests/broker_integration/test_ibkr_connection.py")
        print("   3. Check IBKR Trader Workstation is connected")

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: .env file not found!")
        print(f"   {str(e)}")
        print("\n📝 Create .env file in project root with:")
        print("   IBKR_HOST=127.0.0.1")
        print("   IBKR_PORT=4002")
        print("   IBKR_CLIENT_ID=1")
        print("   TRADING_MODE=paper")
        assert False, ".env file not found"

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}")
        print(f"   {str(e)}")
        assert False, f"Configuration loading failed: {str(e)}"

if __name__ == "__main__":
    test_config_loading()
