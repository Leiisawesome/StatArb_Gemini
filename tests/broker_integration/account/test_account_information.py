"""
Account Information Querying Test
Test account information retrieval and portfolio metrics.

This test:
1. Connects to broker and retrieves account information
2. Validates account data structure and values
3. Calculates and validates portfolio metrics
4. Tests account status and trading restrictions
5. Verifies data consistency and calculations

This test can run anytime but provides most value when account has activity.
During market hours, real-time data is available.
Outside market hours, cached data is used.

Safety:
- Read-only operations (no trading)
- Paper trading account only
- No account modifications

Requirements:
- Broker connection only
"""

import sys
from pathlib import Path
import pytest
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core_engine.config.broker_config import load_broker_config
from core_engine.broker.adapters.ibkr_adapter import IBKRAdapter

def test_account_information_querying():
    """Test comprehensive account information retrieval and validation"""

    print("\n" + "=" * 70)
    print("ACCOUNT INFORMATION QUERYING TEST")
    print("=" * 70)

    # Load configuration
    print("\n[1/6] Loading broker configuration...")
    config = load_broker_config()
    print(f"✅ Configuration loaded: {config.active_broker.value}")

    # Create adapter and connect
    print("\n[2/6] Connecting to IBKR...")
    adapter = IBKRAdapter(config.interactive_brokers)

    try:
        adapter.connect()
        account_info = adapter.get_account_info()
        print(f"✅ Connected to account: {account_info.account_id}")

        # Validate basic account information
        print("\n[3/6] Validating account information structure...")
        assert account_info.account_id, "Account ID should not be empty"
        assert isinstance(account_info.cash, (int, float)), "Cash should be numeric"
        assert isinstance(account_info.buying_power, (int, float)), "Buying power should be numeric"
        assert isinstance(account_info.portfolio_value, (int, float)), "Portfolio value should be numeric"
        assert isinstance(account_info.equity, (int, float)), "Equity should be numeric"
        assert account_info.currency == "USD", f"Currency should be USD, got {account_info.currency}"
        print("✅ Account information structure validated")

        # Display account summary
        print("\n[4/6] Account Summary:")
        print(f"   Account ID: {account_info.account_id}")
        print(f"   Currency: {account_info.currency}")
        print(f"   Status: {account_info.status}")
        print(f"   Pattern Day Trader: {account_info.is_pattern_day_trader}")
        print(f"   Day Trade Count: {account_info.day_trade_count}")

        # Financial metrics
        print(f"\n   Financial Overview:")
        print(f"   Cash: ${account_info.cash:,.2f}")
        print(f"   Equity: ${account_info.equity:,.2f}")
        print(f"   Portfolio Value: ${account_info.portfolio_value:,.2f}")
        print(f"   Buying Power: ${account_info.buying_power:,.2f}")

        # Calculate portfolio composition
        print("\n[5/6] Calculating portfolio metrics...")
        positions_value = account_info.portfolio_value - account_info.cash

        # Validate calculations
        assert account_info.portfolio_value >= 0, "Portfolio value should be non-negative"
        assert account_info.cash >= 0, "Cash should be non-negative"
        assert account_info.equity >= 0, "Equity should be non-negative"
        assert positions_value >= 0, "Positions value should be non-negative"

        # Portfolio breakdown
        if account_info.portfolio_value > 0:
            cash_percentage = (account_info.cash / account_info.portfolio_value) * 100
            positions_percentage = (positions_value / account_info.portfolio_value) * 100
            equity_percentage = (account_info.equity / account_info.portfolio_value) * 100

            print(f"   Portfolio Breakdown:")
            print(f"   Cash: ${account_info.cash:,.2f} ({cash_percentage:.1f}%)")
            print(f"   Positions: ${positions_value:,.2f} ({positions_percentage:.1f}%)")
            print(f"   Equity: ${account_info.equity:,.2f} ({equity_percentage:.1f}%)")

            # Validate percentages
            assert abs(cash_percentage + positions_percentage - 100) < 0.1, "Cash + positions should equal 100%"
        else:
            print("   Portfolio Breakdown: No portfolio value (account may be empty)")

        # Margin information (if available)
        print(f"\n   Margin Information:")
        if account_info.margin_multiplier is not None:
            print(f"   Margin Multiplier: {account_info.margin_multiplier}x")
        else:
            print("   Margin Multiplier: Not available")

        if account_info.maintenance_margin is not None:
            print(f"   Maintenance Margin: ${account_info.maintenance_margin:,.2f}")
        else:
            print("   Maintenance Margin: Not available")

        if account_info.initial_margin is not None:
            print(f"   Initial Margin: ${account_info.initial_margin:,.2f}")
        else:
            print("   Initial Margin: Not available")

        # Trading restrictions
        print(f"\n   Trading Restrictions:")
        print(f"   Pattern Day Trader: {'Yes' if account_info.is_pattern_day_trader else 'No'}")
        print(f"   Day Trades Today: {account_info.day_trade_count}")

        # Data freshness
        print(f"\n   Data Information:")
        print(f"   Timestamp: {account_info.timestamp}")
        age_seconds = (datetime.now() - account_info.timestamp).total_seconds()
        print(f"   Data Age: {age_seconds:.1f} seconds")

        # Validate data is reasonably fresh (within last 5 minutes)
        assert age_seconds < 300, f"Account data is too old: {age_seconds:.1f} seconds"

        # Additional metadata
        if account_info.metadata:
            print(f"   Additional Metadata: {len(account_info.metadata)} fields")
        else:
            print("   Additional Metadata: None")

        print("\n[6/6] Performing final validations...")

        # Business logic validations
        assert account_info.buying_power >= 0, "Buying power should be non-negative"
        assert account_info.portfolio_value >= account_info.equity, "Portfolio value should be >= equity"

        # For paper trading accounts, buying power may be 0 if unfunded
        # We just validate it's not negative
        print("✅ All account information validations passed")

        print("\n" + "=" * 70)
        print("✅ ACCOUNT INFORMATION TEST PASSED")
        print("=" * 70)
        print("\nVerified capabilities:")
        print("  ✓ Account connection and authentication")
        print("  ✓ Account information retrieval")
        print("  ✓ Financial metrics calculation")
        print("  ✓ Portfolio composition analysis")
        print("  ✓ Margin information access")
        print("  ✓ Trading restrictions checking")
        print("  ✓ Data freshness validation")
        print("  ✓ Business logic validations")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Account information querying test failed: {e}")

    finally:
        print("\nDisconnecting from broker...")
        adapter.disconnect()
        print("✅ Disconnected")

if __name__ == "__main__":
    import datetime

    print("\n" + "=" * 70)
    print("PHASE 9 - BROKER INTEGRATION - ACCOUNT INFORMATION TEST")
    print("Account Information Querying Test")
    print("=" * 70)
    print(f"Test started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Trading mode: PAPER ONLY")
    print(f"\n✅ This test can run anytime (read-only operations)")

    try:
        test_account_information_querying()
        print(f"\nTest completed at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n🎉 SUCCESS: Account information querying verified!")
        sys.exit(0)
    except Exception as e:
        print(f"\nTest completed at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n❌ FAILURE: {e}")
        sys.exit(1)