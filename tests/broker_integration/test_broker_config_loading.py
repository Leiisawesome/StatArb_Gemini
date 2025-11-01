"""
Phase 9 Day 1: Configuration Loading Test

Tests:
- Configuration file loading
- Environment variable parsing
- Alpaca config validation
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
    print("Broker Integration: Configuration Loading Test")
    print("=" * 60)
    
    try:
        # Load configuration
        print("\n⏳ Loading configuration from .env...")
        config = load_broker_config()
        
        # Test Alpaca config
        print("\n🔧 Testing Alpaca Configuration:")
        alpaca_config = config.alpaca
        
        # Check that credentials are loaded
        if not alpaca_config.api_key:
            print("❌ ALPACA_API_KEY not found in .env")
            return False
        
        if not alpaca_config.secret_key:
            print("❌ ALPACA_SECRET_KEY not found in .env")
            return False
        
        # Display config (masked)
        print(f"   ✓ API Key: {alpaca_config.api_key[:8]}...")
        print(f"   ✓ Base URL: {alpaca_config.base_url}")
        print(f"   ✓ Paper Trading: {alpaca_config.paper_trading}")
        
        # Validate configuration
        print("\n🔍 Validating Alpaca Configuration:")
        if alpaca_config.validate():
            print("   ✅ Configuration validation: PASSED")
        else:
            print("   ❌ Configuration validation: FAILED")
            return False
        
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
            return False
        
        # Test trading mode
        print("\n🎯 Testing Trading Mode:")
        trading_mode = config.trading_mode
        print(f"   Current Mode: {trading_mode.value}")
        
        if trading_mode.value == "paper":
            print("   ✅ Paper trading mode confirmed")
        else:
            print("   ⚠️  WARNING: Not in paper trading mode!")
        
        print("\n" + "=" * 60)
        print("✅ Broker Configuration Test: SUCCESS")
        print("=" * 60)
        print("\n📝 Next Steps:")
        print("   1. Verify your Alpaca credentials are correct")
        print("   2. Run connection test: python tests/broker_integration/test_alpaca_connection.py")
        print("   3. Check Alpaca dashboard: https://app.alpaca.markets/paper/dashboard/overview")
        return True
        
    except FileNotFoundError as e:
        print(f"\n❌ ERROR: .env file not found!")
        print(f"   {str(e)}")
        print("\n📝 Create .env file in project root with:")
        print("   ALPACA_API_KEY=your_key_here")
        print("   ALPACA_SECRET_KEY=your_secret_here")
        print("   ALPACA_BASE_URL=https://paper-api.alpaca.markets")
        print("   TRADING_MODE=paper")
        return False
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}")
        print(f"   {str(e)}")
        return False


if __name__ == "__main__":
    success = test_config_loading()
    sys.exit(0 if success else 1)
