"""
IBKR Paper Trading Account Funding Utility
Provides instructions and utilities for funding Interactive Brokers paper trading accounts.
"""

import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core_engine.config.broker_config import load_broker_config
from core_engine.broker.adapters.ibkr_adapter import IBKRAdapter

logger = logging.getLogger(__name__)


class IBKRPaperTradingFunder:
    """Utility for funding IBKR paper trading accounts"""

    def __init__(self):
        self.config = load_broker_config()
        self.adapter = IBKRAdapter(self.config.interactive_brokers)

    def show_funding_instructions(self):
        """Display instructions for funding IBKR paper trading account"""
        print("\n" + "=" * 80)
        print("IBKR PAPER TRADING ACCOUNT FUNDING INSTRUCTIONS")
        print("=" * 80)

        print("\n📋 Interactive Brokers Paper Trading accounts start with $0.00 balance.")
        print("   To enable trading, you need to fund your paper account with virtual money.")
        print("\n" + "-" * 80)

        print("\n🔧 METHOD 1: Fund via Trader Workstation (TWS) - RECOMMENDED")
        print("   1. Launch IBKR Trader Workstation (TWS)")
        print("   2. Log in with your paper trading credentials")
        print("   3. Go to: File → Global Configuration → Display → Ticker Row")
        print("   4. Check: 'Show Cash Qty'")
        print("   5. In the main window, right-click on your account number")
        print("   6. Select: 'Transfer & Pay' → 'Transfer Funds'")
        print("   7. Choose 'Deposit' and enter amount (e.g., $100,000)")
        print("   8. Select 'USD' as currency")
        print("   9. Click 'Transfer'")

        print("\n🔧 METHOD 2: Fund via IBKR Account Management Website")
        print("   1. Go to: https://www.ibkr.com")
        print("   2. Log in to Account Management")
        print("   3. Navigate to 'Account' → 'Transfer & Pay'")
        print("   4. Select your paper trading account")
        print("   5. Choose 'Deposit Funds'")
        print("   6. Enter amount and confirm")

        print("\n🔧 METHOD 3: Fund via IBKR Mobile App")
        print("   1. Open IBKR Mobile app")
        print("   2. Log in with paper trading credentials")
        print("   3. Go to 'Account' → 'Transfer & Pay'")
        print("   4. Select 'Deposit'")
        print("   5. Enter amount and confirm")

        print("\n💡 RECOMMENDED FUNDING AMOUNTS:")
        print("   • Small testing: $10,000 - $25,000")
        print("   • Strategy testing: $50,000 - $100,000")
        print("   • Full portfolio: $250,000 - $500,000")
        print("   • Conservative limit: $1,000,000")

        print("\n⚠️  IMPORTANT NOTES:")
        print("   • Paper trading funds are virtual - no real money involved")
        print("   • Funds persist until you reset the account")
        print("   • You can add/remove funds anytime")
        print("   • All trading costs (commissions, fees) are simulated")
        print("   • Market data may be delayed without subscription")

        print("\n" + "=" * 80)

    def check_account_balance(self) -> dict:
        """Check current account balance and display funding status"""
        try:
            self.adapter.connect()
            account_info = self.adapter.get_account_info()

            balance_info = {
                'account_id': account_info.account_id,
                'cash': account_info.cash,
                'buying_power': account_info.buying_power,
                'portfolio_value': account_info.portfolio_value,
                'equity': account_info.equity,
                'currency': account_info.currency
            }

            print("\n" + "=" * 60)
            print("CURRENT ACCOUNT BALANCE")
            print("=" * 60)
            print(f"Account ID: {balance_info['account_id']}")
            print(f"Cash: ${balance_info['cash']:,.2f}")
            print(f"Buying Power: ${balance_info['buying_power']:,.2f}")
            print(f"Portfolio Value: ${balance_info['portfolio_value']:,.2f}")
            print(f"Equity: ${balance_info['equity']:,.2f}")
            print(f"Currency: {balance_info['currency']}")

            # Funding status
            if balance_info['cash'] == 0 and balance_info['buying_power'] == 0:
                print("\n❌ STATUS: Account is unfunded - cannot place orders")
                print("   💡 Follow funding instructions above to add virtual money")
            elif balance_info['cash'] > 0:
                print("\n✅ STATUS: Account is funded and ready for trading")
                print(f"   💰 Available cash: ${balance_info['cash']:,.2f}")
            else:
                print("\n⚠️  STATUS: Account has positions but no cash")
                print("   💡 May need additional funds for new positions")

            return balance_info

        except Exception as e:
            print(f"❌ Error checking account balance: {e}")
            return {}
        finally:
            try:
                self.adapter.disconnect()
            except:
                pass

    def simulate_funding(self, amount: float = 100000.00) -> bool:
        """
        Simulate funding for testing purposes
        NOTE: This is just for demonstration - actual funding must be done through IBKR
        """
        print(f"\n💡 SIMULATION: Adding ${amount:,.2f} to paper trading account")
        print("   ⚠️  This is just a simulation for testing purposes!")
        print("   ⚠️  Actual funding must be done through IBKR TWS/Account Management")
        print("\n   To actually fund your account:")
        print("   1. Open IBKR Trader Workstation")
        print("   2. Right-click account → Transfer & Pay → Transfer Funds")
        print(f"   3. Deposit ${amount:,.2f} USD")
        print("   4. Run this balance check again to verify")
        return False  # Always return false since we can't actually fund


def main():
    """Main function for the funding utility"""
    import argparse

    parser = argparse.ArgumentParser(description="IBKR Paper Trading Account Funding Utility")
    parser.add_argument("--check", action="store_true", help="Check current account balance")
    parser.add_argument("--instructions", action="store_true", help="Show funding instructions")
    parser.add_argument("--simulate", type=float, help="Simulate funding with specified amount")

    args = parser.parse_args()

    funder = IBKRPaperTradingFunder()

    if args.instructions or not any([args.check, args.simulate]):
        funder.show_funding_instructions()

    if args.check:
        funder.check_account_balance()

    if args.simulate:
        funder.simulate_funding(args.simulate)


if __name__ == "__main__":
    main()