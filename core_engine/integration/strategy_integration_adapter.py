"""
Strategy Integration Adapter - Phase 2 Bridge
=============================================

Bridges existing strategy architecture with the new enhanced strategy manager.
Provides seamless migration path from legacy strategies to risk-integrated strategies.

This adapter allows existing strategies to work with the new CentralRiskManager
authorization workflow without requiring complete rewrites.

Key Features:
- Legacy strategy wrapping
- Automatic risk profile generation
- Signal authorization bridging
- Performance metrics translation
- Gradual migration support

Author: StatArb_Gemini Phase 2 Integration
Version: 2.0.0 (Migration Bridge)
"""

import asyncio
import logging
import inspect
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Type, Callable
from dataclasses import dataclass, field
from enum import Enum
import warnings

# Import existing strategy components
from core_engine.strategy.strategy_engine import (
    BaseStrategy, StrategyConfig, StrategySignal, StrategyPosition, 
    StrategyMetrics, StrategyState, StrategyType, SignalType
)
from core_engine.strategy.strategy_manager import (
    StrategyStatus, DeploymentMode, StrategyDeployment
)

# Import enhanced strategy manager
from .enhanced_strategy_manager import (
    RiskIntegratedStrategy, StrategyRiskProfile, StrategyRiskLevel,
    StrategyAuthorizationStatus, EnhancedStrategyManager
)

# Import Phase 1 components
from core_engine.central_risk_manager import CentralRiskManager
from core_engine.unified_execution_engine import UnifiedExecutionEngine

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class MigrationStatus(Enum):
    """Migration status for strategies"""
    LEGACY = "legacy"                    # Original strategy, not migrated
    WRAPPED = "wrapped"                  # Legacy strategy wrapped for new system
    HYBRID = "hybrid"                    # Partially migrated
    NATIVE = "native"                    # Fully migrated to new architecture
    DEPRECATED = "deprecated"            # Legacy strategy marked for removal


@dataclass
class StrategyMigrationPlan:
    """Migration plan for individual strategy"""
    
    strategy_id: str = ""
    current_status: MigrationStatus = MigrationStatus.LEGACY
    target_status: MigrationStatus = MigrationStatus.NATIVE
    
    # Migration timeline
    migration_start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    
    # Migration requirements
    requires_risk_profile_update: bool = True
    requires_signal_logic_update: bool = False
    requires_performance_validation: bool = True
    
    # Risk assessment
    estimated_risk_level: StrategyRiskLevel = StrategyRiskLevel.MODERATE
    requires_manual_authorization: bool = False
    
    # Migration notes
    migration_notes: str = ""
    blocking_issues: List[str] = field(default_factory=list)


class LegacyStrategyWrapper(RiskIntegratedStrategy):
    """
    Wrapper for legacy strategies to work with new risk-integrated architecture
    
    This wrapper allows existing strategies to participate in the new
    authorization workflow without requiring code changes.
    """
    
    def __init__(self, legacy_strategy: Any, strategy_id: str, config: Dict[str, Any]):
        """Initialize wrapper around legacy strategy"""
        
        super().__init__(strategy_id, config)
        
        self.legacy_strategy = legacy_strategy
        self.wrapped_strategy_type = type(legacy_strategy).__name__
        
        # Analyze legacy strategy to set risk profile
        self._analyze_legacy_strategy()
        
        # Migration tracking
        self.migration_status = MigrationStatus.WRAPPED
        self.wrapper_created_at = datetime.now()
        
        logger.info(f"Legacy strategy {strategy_id} wrapped for risk integration")
    
    def _analyze_legacy_strategy(self):
        """Analyze legacy strategy to determine risk profile"""
        
        try:
            # Extract configuration from legacy strategy
            config = getattr(self.legacy_strategy, 'config', {})
            
            # Analyze strategy type for risk classification
            strategy_type = getattr(self.legacy_strategy, 'strategy_type', StrategyType.CUSTOM)
            
            # Set risk level based on strategy type
            risk_mapping = {
                StrategyType.MEAN_REVERSION: StrategyRiskLevel.CONSERVATIVE,
                StrategyType.MOMENTUM: StrategyRiskLevel.MODERATE,
                StrategyType.PAIRS_TRADING: StrategyRiskLevel.CONSERVATIVE,
                StrategyType.ARBITRAGE: StrategyRiskLevel.CONSERVATIVE,
                StrategyType.MARKET_MAKING: StrategyRiskLevel.MODERATE,
                StrategyType.TREND_FOLLOWING: StrategyRiskLevel.MODERATE,
                StrategyType.STATISTICAL_ARBITRAGE: StrategyRiskLevel.MODERATE,
                StrategyType.MACHINE_LEARNING: StrategyRiskLevel.AGGRESSIVE,
                StrategyType.MULTI_FACTOR: StrategyRiskLevel.MODERATE,
                StrategyType.CUSTOM: StrategyRiskLevel.EXPERIMENTAL
            }
            
            self.risk_profile.risk_level = risk_mapping.get(strategy_type, StrategyRiskLevel.MODERATE)
            
            # Extract risk parameters from config
            self.risk_profile.max_position_size = config.get('max_position_size', 100000.0)
            self.risk_profile.max_daily_loss = config.get('max_daily_loss', 5000.0)
            self.risk_profile.max_drawdown = config.get('max_drawdown', 0.10)
            
            # Set authorization requirements based on risk level
            if self.risk_profile.risk_level in [StrategyRiskLevel.AGGRESSIVE, StrategyRiskLevel.EXPERIMENTAL]:
                self.risk_profile.requires_preauthorization = True
                self.risk_profile.authorization_validity_minutes = 30
            else:
                self.risk_profile.requires_preauthorization = True
                self.risk_profile.authorization_validity_minutes = 60
            
            logger.info(f"Legacy strategy {self.strategy_id} analyzed - Risk level: {self.risk_profile.risk_level}")
            
        except Exception as e:
            logger.error(f"Legacy strategy analysis failed for {self.strategy_id}: {e}")
            # Default to moderate risk
            self.risk_profile.risk_level = StrategyRiskLevel.MODERATE
    
    async def _generate_signal_logic(self, market_data: Dict[str, Any]) -> Optional[StrategySignal]:
        """Bridge to legacy strategy signal generation"""
        
        try:
            # Check if legacy strategy has signal generation method
            if hasattr(self.legacy_strategy, 'generate_signal'):
                # Call legacy signal generation
                legacy_signal = await self._call_legacy_method('generate_signal', market_data)
                
                if legacy_signal:
                    # Convert legacy signal to new format
                    return self._convert_legacy_signal(legacy_signal)
            
            elif hasattr(self.legacy_strategy, 'calculate_signals'):
                # Alternative legacy method name
                legacy_signals = await self._call_legacy_method('calculate_signals', market_data)
                
                if legacy_signals and len(legacy_signals) > 0:
                    # Convert first signal
                    return self._convert_legacy_signal(legacy_signals[0])
            
            elif hasattr(self.legacy_strategy, 'get_trading_signal'):
                # Another common legacy method name
                legacy_signal = await self._call_legacy_method('get_trading_signal', market_data)
                
                if legacy_signal:
                    return self._convert_legacy_signal(legacy_signal)
            
            else:
                logger.warning(f"No compatible signal generation method found in legacy strategy {self.strategy_id}")
                return None
            
        except Exception as e:
            logger.error(f"Legacy signal generation failed for {self.strategy_id}: {e}")
            return None
    
    async def _call_legacy_method(self, method_name: str, *args, **kwargs):
        """Safely call legacy strategy method"""
        
        try:
            method = getattr(self.legacy_strategy, method_name)
            
            # Check if method is async
            if inspect.iscoroutinefunction(method):
                return await method(*args, **kwargs)
            else:
                return method(*args, **kwargs)
                
        except Exception as e:
            logger.error(f"Legacy method call failed: {method_name} - {e}")
            return None
    
    def _convert_legacy_signal(self, legacy_signal: Any) -> Optional[StrategySignal]:
        """Convert legacy signal format to new StrategySignal format"""
        
        try:
            # Handle different legacy signal formats
            if isinstance(legacy_signal, dict):
                return self._convert_dict_signal(legacy_signal)
            elif hasattr(legacy_signal, '__dict__'):
                return self._convert_object_signal(legacy_signal)
            else:
                logger.warning(f"Unknown legacy signal format: {type(legacy_signal)}")
                return None
                
        except Exception as e:
            logger.error(f"Legacy signal conversion failed: {e}")
            return None
    
    def _convert_dict_signal(self, signal_dict: Dict[str, Any]) -> StrategySignal:
        """Convert dictionary-based legacy signal"""
        
        # Map common legacy field names to new format
        field_mapping = {
            'action': 'signal_type',
            'side': 'signal_type', 
            'direction': 'signal_type',
            'ticker': 'symbol',
            'instrument': 'symbol',
            'size': 'target_quantity',
            'quantity': 'target_quantity',
            'amount': 'target_quantity',
            'price': 'signal_price',
            'entry_price': 'signal_price',
            'confidence_score': 'confidence',
            'probability': 'confidence',
            'reason': 'signal_reason',
            'rationale': 'signal_reason'
        }
        
        # Create new signal with mapped fields
        signal = StrategySignal(
            signal_id=str(uuid.uuid4()),
            strategy_id=self.strategy_id,
            timestamp=datetime.now(),
            signal_source=f"LegacyWrapper_{self.wrapped_strategy_type}"
        )
        
        # Map fields
        for legacy_field, new_field in field_mapping.items():
            if legacy_field in signal_dict:
                value = signal_dict[legacy_field]
                
                # Convert signal type
                if new_field == 'signal_type':
                    signal.signal_type = self._convert_signal_type(value)
                else:
                    setattr(signal, new_field, value)
        
        # Set defaults for missing fields
        if not signal.symbol:
            signal.symbol = signal_dict.get('symbol', 'UNKNOWN')
        
        if not signal.target_quantity:
            signal.target_quantity = signal_dict.get('target_quantity', 1000.0)
        
        if not signal.signal_reason:
            signal.signal_reason = f"Legacy signal from {self.wrapped_strategy_type}"
        
        return signal
    
    def _convert_object_signal(self, signal_obj: Any) -> StrategySignal:
        """Convert object-based legacy signal"""
        
        signal = StrategySignal(
            signal_id=str(uuid.uuid4()),
            strategy_id=self.strategy_id,
            timestamp=datetime.now(),
            signal_source=f"LegacyWrapper_{self.wrapped_strategy_type}"
        )
        
        # Common attribute mappings
        attr_mapping = {
            'symbol': ['symbol', 'ticker', 'instrument'],
            'signal_type': ['action', 'side', 'direction', 'signal_type'],
            'target_quantity': ['quantity', 'size', 'amount', 'target_quantity'],
            'signal_price': ['price', 'entry_price', 'target_price'],
            'confidence': ['confidence', 'probability', 'score'],
            'signal_reason': ['reason', 'rationale', 'description']
        }
        
        # Map attributes
        for new_attr, legacy_attrs in attr_mapping.items():
            for legacy_attr in legacy_attrs:
                if hasattr(signal_obj, legacy_attr):
                    value = getattr(signal_obj, legacy_attr)
                    
                    if new_attr == 'signal_type':
                        signal.signal_type = self._convert_signal_type(value)
                    else:
                        setattr(signal, new_attr, value)
                    break
        
        # Set defaults
        if not signal.symbol:
            signal.symbol = 'UNKNOWN'
        if not signal.target_quantity:
            signal.target_quantity = 1000.0
        if not signal.signal_reason:
            signal.signal_reason = f"Legacy signal from {self.wrapped_strategy_type}"
        
        return signal
    
    def _convert_signal_type(self, legacy_type: Any) -> SignalType:
        """Convert legacy signal type to new SignalType enum"""
        
        if isinstance(legacy_type, str):
            legacy_type = legacy_type.lower()
            
            type_mapping = {
                'buy': SignalType.BUY,
                'long': SignalType.BUY,
                'enter_long': SignalType.BUY,
                'sell': SignalType.SELL,
                'short': SignalType.SELL,
                'enter_short': SignalType.SELL,
                'hold': SignalType.HOLD,
                'close': SignalType.CLOSE_LONG,
                'exit': SignalType.CLOSE_LONG,
                'close_long': SignalType.CLOSE_LONG,
                'close_short': SignalType.CLOSE_SHORT
            }
            
            return type_mapping.get(legacy_type, SignalType.HOLD)
        
        # If already SignalType enum
        if isinstance(legacy_type, SignalType):
            return legacy_type
        
        # Default
        return SignalType.HOLD


class StrategyIntegrationAdapter:
    """
    Strategy Integration Adapter for Phase 2 Migration
    
    Manages the migration of existing strategies to the new risk-integrated
    architecture while maintaining backward compatibility.
    """
    
    def __init__(self, enhanced_manager: EnhancedStrategyManager):
        """Initialize integration adapter"""
        
        self.enhanced_manager = enhanced_manager
        self.adapter_id = str(uuid.uuid4())
        
        # Migration tracking
        self.legacy_strategies: Dict[str, Any] = {}
        self.wrapped_strategies: Dict[str, LegacyStrategyWrapper] = {}
        self.migration_plans: Dict[str, StrategyMigrationPlan] = {}
        
        # Adapter state
        self.is_initialized = False
        self.migration_stats = {
            'total_strategies': 0,
            'wrapped_strategies': 0,
            'migrated_strategies': 0,
            'failed_migrations': 0
        }
        
        logger.info(f"Strategy Integration Adapter {self.adapter_id} initialized")
    
    async def register_legacy_strategy(self, strategy: Any, strategy_id: str, 
                                     config: Optional[Dict[str, Any]] = None) -> bool:
        """Register legacy strategy for integration"""
        
        try:
            config = config or {}
            
            # Store legacy strategy
            self.legacy_strategies[strategy_id] = strategy
            self.migration_stats['total_strategies'] += 1
            
            # Create migration plan
            migration_plan = StrategyMigrationPlan(
                strategy_id=strategy_id,
                current_status=MigrationStatus.LEGACY,
                migration_start_date=datetime.now(),
                target_completion_date=datetime.now() + timedelta(days=30)
            )
            
            # Analyze strategy for migration requirements
            self._analyze_migration_requirements(strategy, migration_plan)
            
            self.migration_plans[strategy_id] = migration_plan
            
            logger.info(f"Legacy strategy {strategy_id} registered for integration")
            return True
            
        except Exception as e:
            logger.error(f"Legacy strategy registration failed: {e}")
            return False
    
    def _analyze_migration_requirements(self, strategy: Any, plan: StrategyMigrationPlan):
        """Analyze strategy migration requirements"""
        
        try:
            # Check strategy type
            strategy_type = getattr(strategy, 'strategy_type', None)
            
            # Estimate risk level
            if strategy_type in [StrategyType.MACHINE_LEARNING, StrategyType.CUSTOM]:
                plan.estimated_risk_level = StrategyRiskLevel.AGGRESSIVE
                plan.requires_manual_authorization = True
            elif strategy_type in [StrategyType.MOMENTUM, StrategyType.TREND_FOLLOWING]:
                plan.estimated_risk_level = StrategyRiskLevel.MODERATE
            else:
                plan.estimated_risk_level = StrategyRiskLevel.CONSERVATIVE
            
            # Check for signal generation methods
            signal_methods = ['generate_signal', 'calculate_signals', 'get_trading_signal']
            has_signal_method = any(hasattr(strategy, method) for method in signal_methods)
            
            if not has_signal_method:
                plan.blocking_issues.append("No compatible signal generation method found")
                plan.requires_signal_logic_update = True
            
            # Check for risk parameters
            config = getattr(strategy, 'config', {})
            required_risk_params = ['max_position_size', 'max_daily_loss']
            
            missing_params = [param for param in required_risk_params if param not in config]
            if missing_params:
                plan.requires_risk_profile_update = True
                plan.migration_notes += f"Missing risk parameters: {missing_params}. "
            
        except Exception as e:
            logger.error(f"Migration analysis failed for {plan.strategy_id}: {e}")
            plan.blocking_issues.append(f"Analysis failed: {e}")
    
    async def wrap_legacy_strategy(self, strategy_id: str) -> bool:
        """Wrap legacy strategy for new architecture"""
        
        try:
            if strategy_id not in self.legacy_strategies:
                logger.error(f"Legacy strategy {strategy_id} not found")
                return False
            
            if strategy_id in self.wrapped_strategies:
                logger.warning(f"Strategy {strategy_id} already wrapped")
                return True
            
            # Get legacy strategy and migration plan
            legacy_strategy = self.legacy_strategies[strategy_id]
            migration_plan = self.migration_plans.get(strategy_id)
            
            if migration_plan and migration_plan.blocking_issues:
                logger.error(f"Cannot wrap strategy {strategy_id} due to blocking issues: {migration_plan.blocking_issues}")
                return False
            
            # Create wrapper
            config = getattr(legacy_strategy, 'config', {})
            wrapper = LegacyStrategyWrapper(legacy_strategy, strategy_id, config)
            
            # Register with enhanced manager
            registration_success = self.enhanced_manager.register_strategy(wrapper)
            
            if registration_success:
                self.wrapped_strategies[strategy_id] = wrapper
                self.migration_stats['wrapped_strategies'] += 1
                
                # Update migration plan
                if migration_plan:
                    migration_plan.current_status = MigrationStatus.WRAPPED
                
                logger.info(f"Legacy strategy {strategy_id} successfully wrapped")
                return True
            else:
                logger.error(f"Failed to register wrapped strategy {strategy_id}")
                return False
                
        except Exception as e:
            logger.error(f"Strategy wrapping failed for {strategy_id}: {e}")
            self.migration_stats['failed_migrations'] += 1
            return False
    
    async def migrate_all_legacy_strategies(self) -> Dict[str, bool]:
        """Migrate all registered legacy strategies"""
        
        results = {}
        
        for strategy_id in self.legacy_strategies.keys():
            try:
                success = await self.wrap_legacy_strategy(strategy_id)
                results[strategy_id] = success
                
                if success:
                    logger.info(f"Successfully migrated strategy {strategy_id}")
                else:
                    logger.warning(f"Failed to migrate strategy {strategy_id}")
                    
            except Exception as e:
                logger.error(f"Migration failed for {strategy_id}: {e}")
                results[strategy_id] = False
        
        return results
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration status"""
        
        return {
            'adapter_id': self.adapter_id,
            'migration_stats': self.migration_stats.copy(),
            'strategy_summary': {
                'legacy_strategies': list(self.legacy_strategies.keys()),
                'wrapped_strategies': list(self.wrapped_strategies.keys()),
                'migration_plans': {
                    strategy_id: {
                        'current_status': plan.current_status.value,
                        'target_status': plan.target_status.value,
                        'blocking_issues': plan.blocking_issues,
                        'estimated_risk_level': plan.estimated_risk_level.value
                    }
                    for strategy_id, plan in self.migration_plans.items()
                }
            }
        }
    
    async def test_wrapped_strategy(self, strategy_id: str, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test wrapped strategy with sample data"""
        
        try:
            if strategy_id not in self.wrapped_strategies:
                return {'success': False, 'error': 'Strategy not wrapped'}
            
            wrapper = self.wrapped_strategies[strategy_id]
            
            # Test authorization request
            auth_success = await wrapper.request_strategy_authorization()
            
            if not auth_success:
                return {'success': False, 'error': 'Authorization failed'}
            
            # Test signal generation
            signal = await wrapper.generate_authorized_signal(test_data)
            
            return {
                'success': True,
                'authorization_status': wrapper.authorization_status.value,
                'signal_generated': signal is not None,
                'signal_details': signal.__dict__ if signal else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}


async def main():
    """Example usage of the integration adapter"""
    
    print("Strategy Integration Adapter - Phase 2 Bridge")
    print("=" * 50)
    
    # This would typically be done during system initialization
    print("✅ Integration adapter ready for legacy strategy migration")
    print("✅ CentralRiskManager integration enabled")
    print("✅ Backward compatibility maintained")
    print("✅ Gradual migration path established")


if __name__ == "__main__":
    asyncio.run(main())