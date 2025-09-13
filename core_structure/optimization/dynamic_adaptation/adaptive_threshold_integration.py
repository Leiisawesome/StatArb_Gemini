"""
Adaptive Threshold Integration Script.

This script integrates the AdaptiveThresholdManager with the existing trading system
and provides utility functions for managing adaptive thresholds.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd

from .adaptive_threshold_manager import AdaptiveThresholdManager, ThresholdType
from .adaptation_config import AdaptationConfig, AdaptationMode
from ..memory import CacheManager

logger = logging.getLogger(__name__)


class AdaptiveThresholdIntegration:
    """
    Integration layer for adaptive thresholds with the trading system.
    """
    
    def __init__(self, strategy_manager: Any, regime_engine: Any):
        """
        Initialize adaptive threshold integration.
        
        Args:
            strategy_manager: Reference to the StrategyManager
            regime_engine: Reference to the UnifiedRegimeEngine
        """
        self.strategy_manager = strategy_manager
        self.regime_engine = regime_engine
        self.logger = logging.getLogger(__name__)
        
        # Threshold managers for each strategy
        self.threshold_managers: Dict[str, AdaptiveThresholdManager] = {}
        
        # Performance monitoring
        self.performance_monitor = AdaptiveThresholdPerformanceMonitor()
        
        # Cache for performance data
        self.cache_manager = CacheManager("adaptive_thresholds_system")
        
    async def initialize_adaptive_thresholds(self, strategies: Dict[str, Any]) -> None:
        """
        Initialize adaptive threshold managers for all strategies.
        
        Args:
            strategies: Dictionary of strategy configurations
        """
        try:
            for strategy_id, strategy_config in strategies.items():
                if strategy_config.get('enable_adaptive_thresholds', True):
                    await self.create_threshold_manager(strategy_id, strategy_config)
            
            self.logger.info(f"✅ Initialized adaptive thresholds for {len(self.threshold_managers)} strategies")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize adaptive thresholds: {e}")
            raise
    
    async def create_threshold_manager(self, strategy_id: str, strategy_config: Dict[str, Any]) -> AdaptiveThresholdManager:
        """Create and configure a threshold manager for a strategy."""
        try:
            # Determine adaptation mode from config
            adaptation_mode_str = strategy_config.get('adaptation_mode', 'moderate')
            adaptation_mode = AdaptationMode(adaptation_mode_str)
            
            # Create adaptation config
            adaptation_config = AdaptationConfig(mode=adaptation_mode)
            
            # Create threshold manager
            threshold_manager = AdaptiveThresholdManager(
                strategy_id=strategy_id,
                adaptation_config=adaptation_config,
                regime_engine=self.regime_engine
            )
            
            # Import any existing threshold configuration
            cached_config = await self.cache_manager.get(f"threshold_config_{strategy_id}")
            if cached_config:
                threshold_manager.import_threshold_configuration(cached_config)
                self.logger.info(f"📥 Imported cached threshold configuration for {strategy_id}")
            
            self.threshold_managers[strategy_id] = threshold_manager
            
            self.logger.info(f"🔧 Created adaptive threshold manager for {strategy_id} "
                           f"(mode: {adaptation_mode.value})")
            
            return threshold_manager
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create threshold manager for {strategy_id}: {e}")
            raise
    
    async def update_all_thresholds(self, market_data: Dict[str, pd.DataFrame], 
                                  performance_data: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, Any]]:
        """
        Update thresholds for all strategies based on performance and market conditions.
        
        Args:
            market_data: Market data for each symbol
            performance_data: Performance metrics for each strategy
            
        Returns:
            Dictionary of update results for each strategy
        """
        update_results = {}
        
        try:
            # Calculate market conditions
            market_conditions = self._calculate_market_conditions(market_data)
            
            # Update thresholds for each strategy
            for strategy_id, threshold_manager in self.threshold_managers.items():
                strategy_performance = performance_data.get(strategy_id, {})
                recent_signals = await self._get_recent_signals(strategy_id)
                
                update_result = await threshold_manager.update_thresholds_based_on_performance(
                    performance_metrics=strategy_performance,
                    market_conditions=market_conditions,
                    recent_signals=recent_signals
                )
                
                update_results[strategy_id] = update_result
                
                # Cache updated configuration
                if update_result.get('thresholds_updated'):
                    config = threshold_manager.export_threshold_configuration()
                    await self.cache_manager.set(f"threshold_config_{strategy_id}", config, ttl=86400)
                
                # Track performance
                self.performance_monitor.record_update(strategy_id, update_result)
            
            self.logger.info(f"🔄 Updated adaptive thresholds for {len(self.threshold_managers)} strategies")
            return update_results
            
        except Exception as e:
            self.logger.error(f"❌ Failed to update adaptive thresholds: {e}")
            return {'error': str(e)}
    
    def get_threshold_manager(self, strategy_id: str) -> Optional[AdaptiveThresholdManager]:
        """Get threshold manager for a specific strategy."""
        return self.threshold_managers.get(strategy_id)
    
    def get_current_thresholds_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of current thresholds for all strategies."""
        summary = {}
        
        for strategy_id, threshold_manager in self.threshold_managers.items():
            current_regime = None
            if self.regime_engine:
                current_regime = getattr(self.regime_engine, 'current_regime', None)
            
            summary[strategy_id] = {
                'current_regime': current_regime,
                'thresholds': threshold_manager.get_all_current_thresholds(current_regime)
            }
        
        return summary
    
    async def backup_threshold_configurations(self) -> Dict[str, Any]:
        """Backup all threshold configurations."""
        backup = {
            'timestamp': datetime.now().isoformat(),
            'strategies': {}
        }
        
        for strategy_id, threshold_manager in self.threshold_managers.items():
            backup['strategies'][strategy_id] = threshold_manager.export_threshold_configuration()
        
        # Cache backup
        await self.cache_manager.set('threshold_backup', backup, ttl=7*24*3600)  # 7 days
        
        self.logger.info(f"💾 Backed up threshold configurations for {len(self.threshold_managers)} strategies")
        return backup
    
    async def restore_threshold_configurations(self, backup: Dict[str, Any]) -> bool:
        """Restore threshold configurations from backup."""
        try:
            strategies_restored = 0
            
            for strategy_id, config in backup.get('strategies', {}).items():
                if strategy_id in self.threshold_managers:
                    success = self.threshold_managers[strategy_id].import_threshold_configuration(config)
                    if success:
                        strategies_restored += 1
            
            self.logger.info(f"📥 Restored threshold configurations for {strategies_restored} strategies")
            return strategies_restored > 0
            
        except Exception as e:
            self.logger.error(f"❌ Failed to restore threshold configurations: {e}")
            return False
    
    def _calculate_market_conditions(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Calculate current market conditions from market data."""
        conditions = {
            'volatility': 0.2,  # Default
            'volume_trend': 1.0,
            'price_momentum': 0.0,
            'cross_asset_correlation': 0.5
        }
        
        try:
            # Aggregate volatility across all symbols
            volatilities = []
            momentums = []
            
            for symbol, data in market_data.items():
                if len(data) >= 20:
                    # Calculate volatility
                    returns = data['close'].pct_change().dropna()
                    if len(returns) >= 10:
                        vol = returns.tail(20).std() * (252**0.5)  # Annualized
                        volatilities.append(vol)
                    
                    # Calculate momentum
                    if len(data) >= 10:
                        momentum = (data['close'].iloc[-1] / data['close'].iloc[-10] - 1) * 100
                        momentums.append(momentum)
            
            if volatilities:
                conditions['volatility'] = sum(volatilities) / len(volatilities)
            
            if momentums:
                conditions['price_momentum'] = sum(momentums) / len(momentums)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error calculating market conditions: {e}")
        
        return conditions
    
    async def _get_recent_signals(self, strategy_id: str) -> List[Dict[str, Any]]:
        """Get recent signals for a strategy."""
        # This would integrate with the strategy's signal history
        # For now, return empty list
        return []


class AdaptiveThresholdPerformanceMonitor:
    """Monitor performance of adaptive threshold updates."""
    
    def __init__(self):
        self.update_history: List[Dict[str, Any]] = []
        self.performance_impact: Dict[str, List[float]] = {}
    
    def record_update(self, strategy_id: str, update_result: Dict[str, Any]) -> None:
        """Record a threshold update for performance tracking."""
        record = {
            'timestamp': datetime.now(),
            'strategy_id': strategy_id,
            'thresholds_changed': len(update_result.get('thresholds_updated', [])),
            'performance_score': update_result.get('performance_score', 0.0),
            'adaptation_reason': update_result.get('adaptation_reason', '')
        }
        
        self.update_history.append(record)
        
        # Keep only recent history
        if len(self.update_history) > 1000:
            self.update_history = self.update_history[-500:]
    
    def get_update_statistics(self, strategy_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about threshold updates."""
        relevant_updates = self.update_history
        if strategy_id:
            relevant_updates = [u for u in self.update_history if u['strategy_id'] == strategy_id]
        
        if not relevant_updates:
            return {'total_updates': 0}
        
        return {
            'total_updates': len(relevant_updates),
            'avg_thresholds_per_update': sum(u['thresholds_changed'] for u in relevant_updates) / len(relevant_updates),
            'avg_performance_score': sum(u['performance_score'] for u in relevant_updates) / len(relevant_updates),
            'recent_update': relevant_updates[-1]['timestamp'] if relevant_updates else None
        }


async def setup_adaptive_thresholds(strategy_manager: Any, regime_engine: Any, 
                                  strategies: Dict[str, Any]) -> AdaptiveThresholdIntegration:
    """
    Setup adaptive thresholds for the trading system.
    
    Args:
        strategy_manager: The strategy manager instance
        regime_engine: The regime engine instance
        strategies: Strategy configurations
        
    Returns:
        Configured AdaptiveThresholdIntegration instance
    """
    integration = AdaptiveThresholdIntegration(strategy_manager, regime_engine)
    await integration.initialize_adaptive_thresholds(strategies)
    
    logger.info("🎯 Adaptive threshold system setup complete")
    return integration


# Convenience functions for easy integration

def enable_adaptive_thresholds_for_strategy(strategy: Any, threshold_manager: AdaptiveThresholdManager) -> None:
    """Enable adaptive thresholds for a strategy instance."""
    strategy.threshold_manager = threshold_manager
    logger.info(f"✅ Enabled adaptive thresholds for strategy {strategy.strategy_id}")


async def update_strategy_thresholds_from_performance(strategy_id: str, 
                                                    threshold_manager: AdaptiveThresholdManager,
                                                    recent_trades: List[Dict[str, Any]],
                                                    market_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Update a strategy's thresholds based on recent performance.
    
    Args:
        strategy_id: Strategy identifier
        threshold_manager: The strategy's threshold manager
        recent_trades: Recent trade results
        market_data: Recent market data
        
    Returns:
        Update results
    """
    try:
        # Calculate performance metrics from recent trades
        performance_metrics = calculate_performance_metrics(recent_trades)
        
        # Calculate market conditions
        market_conditions = calculate_market_conditions_from_data(market_data)
        
        # Convert trades to signals format
        recent_signals = convert_trades_to_signals(recent_trades)
        
        # Update thresholds
        update_result = await threshold_manager.update_thresholds_based_on_performance(
            performance_metrics=performance_metrics,
            market_conditions=market_conditions,
            recent_signals=recent_signals
        )
        
        logger.info(f"🔄 Updated thresholds for {strategy_id}: {len(update_result.get('thresholds_updated', []))} changes")
        return update_result
        
    except Exception as e:
        logger.error(f"❌ Failed to update thresholds for {strategy_id}: {e}")
        return {'error': str(e)}


def calculate_performance_metrics(trades: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate performance metrics from trade history."""
    if not trades:
        return {
            'sharpe_ratio': 0.0,
            'win_rate': 0.5,
            'profit_factor': 1.0,
            'max_drawdown': 0.0,
            'total_return': 0.0
        }
    
    # Calculate basic metrics
    pnls = [trade.get('pnl', 0) for trade in trades]
    total_pnl = sum(pnls)
    winning_trades = [pnl for pnl in pnls if pnl > 0]
    
    win_rate = len(winning_trades) / len(pnls) if pnls else 0.5
    
    # Simple Sharpe calculation
    pnl_std = pd.Series(pnls).std() if len(pnls) > 1 else 1.0
    sharpe_ratio = (total_pnl / len(pnls)) / pnl_std if pnl_std > 0 else 0.0
    
    # Simple profit factor
    gross_profit = sum(winning_trades) if winning_trades else 1.0
    gross_loss = abs(sum(pnl for pnl in pnls if pnl < 0)) or 1.0
    profit_factor = gross_profit / gross_loss
    
    # Simple max drawdown
    cumulative_pnl = pd.Series(pnls).cumsum()
    running_max = cumulative_pnl.expanding().max()
    drawdown = running_max - cumulative_pnl
    max_drawdown = drawdown.max() / abs(running_max.max()) if running_max.max() != 0 else 0.0
    
    return {
        'sharpe_ratio': sharpe_ratio,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'total_return': total_pnl
    }


def calculate_market_conditions_from_data(market_data: pd.DataFrame) -> Dict[str, float]:
    """Calculate market conditions from price data."""
    if len(market_data) < 2:
        return {'volatility': 0.2, 'momentum': 0.0}
    
    returns = market_data['close'].pct_change().dropna()
    
    return {
        'volatility': returns.std() * (252**0.5) if len(returns) > 1 else 0.2,
        'momentum': (market_data['close'].iloc[-1] / market_data['close'].iloc[0] - 1) * 100 if len(market_data) > 1 else 0.0
    }


def convert_trades_to_signals(trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert trade history to signal format for analysis."""
    signals = []
    
    for trade in trades:
        signal = {
            'timestamp': trade.get('timestamp', datetime.now()),
            'outcome': trade.get('pnl', 0),
            'confidence': trade.get('confidence', 0.5),
            'signal_type': trade.get('action', 'unknown')
        }
        signals.append(signal)
    
    return signals
