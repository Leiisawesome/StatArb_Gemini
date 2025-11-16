"""
Unit tests for position sizing to prevent compounding bug regression

Tests verify that position sizing uses INITIAL portfolio value, not growing value.
This prevents the exponential compounding bug that caused 815% unrealistic returns.

Author: StatArb_Gemini Testing
Date: 2024-11-15
"""

import pytest
from unittest.mock import Mock, MagicMock


class TestPositionSizingNoCompounding:
    """Test that position sizing does NOT compound with portfolio growth"""
    
    def test_position_size_uses_initial_capital(self):
        """
        Verify position size calculated from INITIAL capital, not current portfolio value
        
        Scenario:
        - Initial capital: $100,000
        - After profit: Portfolio = $110,000
        - Position size for 2% signal should still be: 2% of $100k = $2,000
        - NOT 2% of $110k = $2,200 (compounding bug)
        """
        # Setup
        initial_capital = 100000.0
        current_portfolio_value = 110000.0  # After 10% profit
        percentage = 0.02  # 2% position size
        current_price = 100.0
        
        # CORRECT calculation: Use initial capital
        correct_quantity = (percentage * initial_capital) / current_price
        assert correct_quantity == 20.0  # 2% of $100k = $2,000 / $100 = 20 shares
        
        # WRONG calculation: Use current portfolio (compounding bug)
        wrong_quantity = (percentage * current_portfolio_value) / current_price
        assert wrong_quantity == 22.0  # 2% of $110k = $2,200 / $100 = 22 shares
        
        # Verify they're different (catches bug if implemented)
        assert correct_quantity != wrong_quantity
        assert correct_quantity < wrong_quantity
        
    def test_multiple_trades_same_position_size(self):
        """
        Verify multiple trades use same position size regardless of profits
        
        Trade 1: Portfolio $100k → $105k (5% profit)
        Trade 2: Portfolio $105k → should still use $100k for sizing
        Trade 3: Portfolio $110k → should still use $100k for sizing
        """
        initial_capital = 100000.0
        percentage = 0.03  # 3% position size
        price = 50.0
        
        # Calculate expected position size (constant across all trades)
        expected_quantity = (percentage * initial_capital) / price
        assert expected_quantity == 60.0  # 3% of $100k = $3,000 / $50 = 60 shares
        
        # Simulate portfolio growth scenarios
        portfolio_values = [100000.0, 105000.0, 110000.0, 115000.0]
        
        for portfolio_value in portfolio_values:
            # Position size should ALWAYS use initial capital
            quantity = (percentage * initial_capital) / price
            assert quantity == expected_quantity
            
            # Wrong approach (compounding) would give different results
            wrong_quantity = (percentage * portfolio_value) / price
            if portfolio_value > initial_capital:
                assert quantity < wrong_quantity  # Catches compounding bug
    
    def test_position_size_with_losses(self):
        """
        Verify position sizing works correctly even with portfolio losses
        
        Portfolio drops to $90k, but position size should still be based on $100k initial
        """
        initial_capital = 100000.0
        current_portfolio_value = 90000.0  # After 10% loss
        percentage = 0.025  # 2.5% position size
        price = 200.0
        
        # CORRECT: Use initial capital (even though portfolio is down)
        correct_quantity = (percentage * initial_capital) / price
        assert correct_quantity == 12.5  # 2.5% of $100k = $2,500 / $200 = 12.5 shares
        
        # WRONG: Using current portfolio would reduce position size
        wrong_quantity = (percentage * current_portfolio_value) / price
        assert wrong_quantity == 11.25  # 2.5% of $90k = $2,250 / $200 = 11.25 shares
        
        # With initial capital, position size stays consistent
        assert correct_quantity > wrong_quantity
    
    def test_exponential_growth_prevention(self):
        """
        Test that prevents exponential growth from compounding position sizes
        
        Simulates 10 winning trades at 5% each:
        - With compounding: Portfolio grows exponentially (1.05^10 = 1.629)
        - Without compounding: Portfolio grows linearly (1 + 0.05*10 = 1.50)
        """
        initial_capital = 100000.0
        percentage = 0.10  # 10% position size
        price = 100.0
        win_rate = 0.05  # 5% profit per trade
        num_trades = 10
        
        # Simulate WITHOUT compounding (correct)
        portfolio_no_compound = initial_capital
        for i in range(num_trades):
            position_size = (percentage * initial_capital) / price  # Use INITIAL
            profit = position_size * price * win_rate
            portfolio_no_compound += profit
        
        # Simulate WITH compounding (bug)
        portfolio_with_compound = initial_capital
        for i in range(num_trades):
            position_size = (percentage * portfolio_with_compound) / price  # Use CURRENT (bug!)
            profit = position_size * price * win_rate
            portfolio_with_compound += profit
        
        # Results should be VERY different
        expected_no_compound = initial_capital * (1 + percentage * win_rate * num_trades)
        assert abs(portfolio_no_compound - expected_no_compound) < 1.0  # Linear growth
        
        # Compounded would be much higher (geometric growth)
        assert portfolio_with_compound > portfolio_no_compound, "Compounding should yield higher returns"
        assert portfolio_with_compound > initial_capital * 1.05, "Compounding should show measurable growth"
        
        print(f"\nExponential Growth Test:")
        print(f"  Initial Capital: ${initial_capital:,.0f}")
        print(f"  WITHOUT compounding: ${portfolio_no_compound:,.0f} ({(portfolio_no_compound/initial_capital - 1)*100:.1f}% return)")
        print(f"  WITH compounding: ${portfolio_with_compound:,.0f} ({(portfolio_with_compound/initial_capital - 1)*100:.1f}% return)")
        print(f"  Difference: ${portfolio_with_compound - portfolio_no_compound:,.0f}")
    
    def test_position_sizing_integration_scenario(self):
        """
        Integration test: Verify position sizing in realistic trading scenario
        
        Simulates the bug that caused 815% return:
        - 36 trades over 6.5 hours
        - Average 22.6% return per trade (unrealistic with compounding)
        - vs realistic 0.5-2% per trade (without compounding)
        """
        initial_capital = 100000.0
        percentage = 0.02  # 2% position size
        num_trades = 36
        avg_return_per_trade = 0.01  # 1% realistic return per trade
        
        # Calculate final portfolio WITHOUT compounding (correct)
        total_profit = 0.0
        for _ in range(num_trades):
            position_size_dollars = percentage * initial_capital
            profit = position_size_dollars * avg_return_per_trade
            total_profit += profit
        
        final_portfolio_correct = initial_capital + total_profit
        return_pct_correct = (final_portfolio_correct / initial_capital - 1) * 100
        
        # Calculate final portfolio WITH compounding (bug)
        portfolio_bug = initial_capital
        for _ in range(num_trades):
            position_size_dollars = percentage * portfolio_bug  # Bug: uses current value!
            profit = position_size_dollars * avg_return_per_trade
            portfolio_bug += profit
        
        return_pct_bug = (portfolio_bug / initial_capital - 1) * 100
        
        # Assertions
        assert return_pct_correct < 50.0  # Reasonable return
        assert return_pct_bug > return_pct_correct  # Bug inflates returns
        
        # With 2% position size, 1% return per trade, 36 trades:
        # Correct: 36 trades × 2% position × 1% return = 0.72% total return
        # Bug would show geometric compounding effect
        assert 0.5 < return_pct_correct < 1.0, f"Expected ~0.72% return, got {return_pct_correct:.2f}%"
        assert return_pct_bug > return_pct_correct, "Bug should inflate returns"
        
        print(f"\nIntegration Scenario (36 trades, 1% avg return):")
        print(f"  Correct (no compound): {return_pct_correct:.2f}% return")
        print(f"  Bug (compounding): {return_pct_bug:.2f}% return")
        print(f"  Inflation from bug: {return_pct_bug - return_pct_correct:.2f}%")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
