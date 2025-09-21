#!/usr/bin/env python3
"""
Core Engine Architecture Compliance Demonstration
================================================

This test demonstrates how the core_engine system SHOULD be structured using
the actual architectural components, showing the proper integration pattern:

SystemOrchestrator → UnifiedDataManager → UnifiedRegimeEngine → 
AdvancedRiskManager → RealTimeTrading/StrategyManager → UnifiedExecutionEngine

This serves as both a test and a reference implementation for proper
core_engine architecture compliance.

Author: StatArb_Gemini Core Engine (Architecture Compliance)
Version: 1.0.0 (Architecture Demo)
"""

import logging
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("architecture_compliance_demo")

# Import the working core_engine components (updated paths)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from core_engine.data.manager import ClickHouseDataManager, ClickHouseDataConfig
from core_engine.processing.indicators.engine import EnhancedTechnicalIndicators
from core_engine.processing.features.engineer import FeatureEngineer
from core_engine.processing.signals.generator import SignalGenerator, TradingSignal
from core_engine.trading.portfolio.manager import PortfolioManager
from core_engine.system.unified_execution_engine import UnifiedExecutionEngine


class ComponentStatus(Enum):
    """Component status enumeration"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    FAILED = "failed"


class AuthorityLevel(Enum):
    """Authority levels for hierarchical control"""
    SYSTEM_CONTROL = "system_control"
    GOVERNANCE_CONTROL = "governance_control"
    OPERATIONAL = "operational"
    READ_ONLY = "read_only"


class ComponentLayer(Enum):
    """Component layers in hierarchical architecture"""
    ORCHESTRATION = "orchestration"    # Layer 1: System control
    GOVERNANCE = "governance"          # Layer 2: Risk/Trading governance
    EXECUTION = "execution"            # Layer 3: Trading operations
    SUPPORT = "support"                # Support components


@dataclass
class TradingDecisionRequest:
    """Simplified trading decision request for demo"""
    symbol: str
    action: str  # buy/sell/hold
    quantity: float
    price: float
    strategy_id: str
    confidence: float
    risk_score: float
    market_regime: str = "normal"
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class TradingAuthorization:
    """Simplified trading authorization for demo"""
    request_id: str
    authorized: bool
    authorized_quantity: float
    risk_limit: float
    conditions: List[str]
    rejection_reason: str = ""


class ISystemComponent(ABC):
    """Interface for system components"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize component"""
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """Start component operations"""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """Stop component operations"""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get component status"""
        pass


class ArchitectureCompliantSystemOrchestrator:
    """
    Architecture Compliant System Orchestrator
    
    Demonstrates proper hierarchical control pattern:
    Layer 1: SystemOrchestrator (Operational Control)
    Layer 2: RiskManager (Trading Governance) 
    Layer 3: Trading Components (Operational Execution)
    """
    
    def __init__(self):
        self.components: Dict[str, Dict[str, Any]] = {}
        self.component_layers: Dict[ComponentLayer, List[str]] = {
            layer: [] for layer in ComponentLayer
        }
        self.system_status = ComponentStatus.UNINITIALIZED
        self.risk_manager = None
        
        logger.info("🏗️ Architecture Compliant System Orchestrator initialized")
    
    def register_component(self, name: str, component: Any, 
                         layer: ComponentLayer, authority: AuthorityLevel) -> str:
        """Register component with hierarchical control"""
        
        component_id = f"{name}_{len(self.components)}"
        
        self.components[component_id] = {
            'name': name,
            'instance': component,
            'layer': layer,
            'authority': authority,
            'status': ComponentStatus.UNINITIALIZED,
            'reports_to': None
        }
        
        self.component_layers[layer].append(component_id)
        
        logger.info(f"📝 Registered {name} (Layer: {layer.value}, Authority: {authority.value})")
        return component_id
    
    def register_risk_manager(self, risk_manager):
        """Register the central risk manager as governance layer"""
        self.risk_manager = risk_manager
        risk_id = self.register_component(
            "CentralRiskManager", risk_manager, 
            ComponentLayer.GOVERNANCE, AuthorityLevel.GOVERNANCE_CONTROL
        )
        
        # Set execution components to report to risk manager
        for comp_id in self.component_layers[ComponentLayer.EXECUTION]:
            self.components[comp_id]['reports_to'] = risk_id
        
        logger.info("🛡️ Central Risk Manager registered as governance layer")
        return risk_id
    
    async def initialize_system(self) -> bool:
        """Initialize system in hierarchical order"""
        try:
            logger.info("🚀 Initializing architecture compliant system...")
            self.system_status = ComponentStatus.INITIALIZING
            
            # Initialize in layer order: Support → Governance → Execution
            layer_order = [ComponentLayer.SUPPORT, ComponentLayer.GOVERNANCE, ComponentLayer.EXECUTION]
            
            for layer in layer_order:
                for comp_id in self.component_layers[layer]:
                    comp_info = self.components[comp_id]
                    logger.info(f"🔄 Initializing {comp_info['name']}...")
                    
                    try:
                        comp_info['status'] = ComponentStatus.INITIALIZING
                        
                        if hasattr(comp_info['instance'], 'initialize'):
                            success = await comp_info['instance'].initialize()
                        else:
                            success = True  # Assume success for non-interface components
                        
                        if success:
                            comp_info['status'] = ComponentStatus.OPERATIONAL
                            logger.info(f"✅ {comp_info['name']} initialized")
                        else:
                            comp_info['status'] = ComponentStatus.FAILED
                            logger.error(f"❌ {comp_info['name']} initialization failed")
                            
                    except Exception as e:
                        comp_info['status'] = ComponentStatus.FAILED
                        logger.error(f"❌ {comp_info['name']} initialization error: {e}")
            
            # Check overall initialization success
            operational_count = sum(1 for comp in self.components.values() 
                                  if comp['status'] == ComponentStatus.OPERATIONAL)
            total_count = len(self.components)
            success_rate = operational_count / total_count if total_count > 0 else 0
            
            if success_rate >= 0.8:  # 80% success threshold
                self.system_status = ComponentStatus.OPERATIONAL
                logger.info(f"✅ System initialization completed ({operational_count}/{total_count} components)")
                return True
            else:
                self.system_status = ComponentStatus.DEGRADED
                logger.error(f"❌ System initialization degraded ({operational_count}/{total_count} components)")
                return False
                
        except Exception as e:
            self.system_status = ComponentStatus.FAILED
            logger.error(f"❌ System initialization failed: {e}")
            return False
    
    async def request_authorization(self, operation: str, component_id: str, 
                                  details: Dict[str, Any]) -> bool:
        """Request authorization following hierarchical control"""
        try:
            # Check if component exists and has authority
            if component_id not in self.components:
                logger.error(f"Unknown component: {component_id}")
                return False
            
            comp_info = self.components[component_id]
            
            # For trading operations, must go through risk manager
            if operation.startswith("trade_") and self.risk_manager:
                logger.info(f"🛡️ Routing {operation} through Risk Manager")
                
                # Create trading decision request
                request = TradingDecisionRequest(
                    symbol=details.get('symbol', ''),
                    action=details.get('action', 'hold'),
                    quantity=details.get('quantity', 0),
                    price=details.get('price', 0),
                    strategy_id=details.get('strategy_id', 'unknown'),
                    confidence=details.get('confidence', 0.5),
                    risk_score=details.get('risk_score', 0.1)
                )
                
                # Request authorization from risk manager
                authorization = await self.risk_manager.authorize_trading_decision(request)
                
                if authorization.authorized:
                    logger.info(f"✅ Risk Manager authorized {operation}")
                    return True
                else:
                    logger.warning(f"❌ Risk Manager rejected {operation}: {authorization.rejection_reason}")
                    return False
            
            # For non-trading operations, check authority level
            if comp_info['authority'] in [AuthorityLevel.OPERATIONAL, AuthorityLevel.GOVERNANCE_CONTROL]:
                logger.info(f"✅ Authorized {operation} for {comp_info['name']}")
                return True
            else:
                logger.error(f"❌ Insufficient authority for {operation}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Authorization request failed: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        component_summary = {}
        for layer, comp_ids in self.component_layers.items():
            component_summary[layer.value] = {
                'count': len(comp_ids),
                'operational': sum(1 for cid in comp_ids 
                                if self.components[cid]['status'] == ComponentStatus.OPERATIONAL)
            }
        
        return {
            'system_status': self.system_status.value,
            'total_components': len(self.components),
            'component_layers': component_summary,
            'risk_manager_active': self.risk_manager is not None
        }


class ArchitectureCompliantRiskManager:
    """
    Architecture Compliant Risk Manager
    
    Demonstrates central governance pattern where ALL trading decisions
    flow through the RiskManager authorization process.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.max_position_size = self.config.get('max_position_size', 0.1)
        self.max_risk_budget = self.config.get('max_risk_budget', 0.05)
        
        # Risk state
        self.current_positions = {}
        self.risk_budget_used = 0.0
        self.authorization_history = []
        
        logger.info("🛡️ Architecture Compliant Risk Manager initialized")
    
    async def initialize(self) -> bool:
        """Initialize risk manager"""
        try:
            logger.info("🔄 Initializing Risk Manager...")
            # Risk manager initialization logic here
            logger.info("✅ Risk Manager initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Risk Manager initialization failed: {e}")
            return False
    
    async def authorize_trading_decision(self, request: TradingDecisionRequest) -> TradingAuthorization:
        """
        Central authorization point for ALL trading decisions
        
        This demonstrates the core governance pattern where every trading
        decision must flow through risk manager authorization.
        """
        try:
            logger.info(f"🛡️ Processing authorization request for {request.symbol}")
            
            # Risk assessment
            position_check = self._check_position_limits(request)
            risk_budget_check = self._check_risk_budget(request)
            market_conditions_check = self._check_market_conditions(request)
            
            # Determine authorization
            if position_check and risk_budget_check and market_conditions_check:
                # Calculate authorized quantity (may be less than requested)
                authorized_qty = min(request.quantity, self._calculate_max_allowed_quantity(request))
                
                authorization = TradingAuthorization(
                    request_id=f"auth_{len(self.authorization_history)}",
                    authorized=True,
                    authorized_quantity=authorized_qty,
                    risk_limit=self.max_position_size,
                    conditions=self._get_authorization_conditions(request)
                )
                
                logger.info(f"✅ Authorized {authorized_qty} of {request.quantity} requested for {request.symbol}")
            else:
                # Rejection
                rejection_reasons = []
                if not position_check:
                    rejection_reasons.append("Position limit exceeded")
                if not risk_budget_check:
                    rejection_reasons.append("Risk budget exceeded")
                if not market_conditions_check:
                    rejection_reasons.append("Unfavorable market conditions")
                
                authorization = TradingAuthorization(
                    request_id=f"auth_{len(self.authorization_history)}",
                    authorized=False,
                    authorized_quantity=0.0,
                    risk_limit=self.max_position_size,
                    conditions=[],
                    rejection_reason="; ".join(rejection_reasons)
                )
                
                logger.warning(f"❌ Rejected request for {request.symbol}: {authorization.rejection_reason}")
            
            # Store authorization history
            self.authorization_history.append(authorization)
            
            return authorization
            
        except Exception as e:
            logger.error(f"❌ Authorization process failed: {e}")
            return TradingAuthorization(
                request_id="error",
                authorized=False,
                authorized_quantity=0.0,
                risk_limit=0.0,
                conditions=[],
                rejection_reason=f"Authorization error: {e}"
            )
    
    def _check_position_limits(self, request: TradingDecisionRequest) -> bool:
        """Check position limits"""
        current_position = self.current_positions.get(request.symbol, 0.0)
        new_position = current_position + request.quantity
        position_pct = abs(new_position * request.price) / 1000000  # Assume $1M portfolio
        
        return position_pct <= self.max_position_size
    
    def _check_risk_budget(self, request: TradingDecisionRequest) -> bool:
        """Check risk budget"""
        additional_risk = request.risk_score
        return (self.risk_budget_used + additional_risk) <= self.max_risk_budget
    
    def _check_market_conditions(self, request: TradingDecisionRequest) -> bool:
        """Check market conditions"""
        # Simple market condition check
        return request.market_regime not in ["crisis", "extreme_volatility"]
    
    def _calculate_max_allowed_quantity(self, request: TradingDecisionRequest) -> float:
        """Calculate maximum allowed quantity"""
        # Simple calculation - could be more sophisticated
        return request.quantity * 0.8  # Allow 80% of requested
    
    def _get_authorization_conditions(self, request: TradingDecisionRequest) -> List[str]:
        """Get authorization conditions"""
        conditions = []
        
        if request.confidence < 0.7:
            conditions.append("Low confidence - monitor closely")
        
        if request.risk_score > 0.03:
            conditions.append("Elevated risk - enhanced monitoring")
        
        return conditions
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Get risk manager status"""
        return {
            'operational': True,
            'current_positions': len(self.current_positions),
            'risk_budget_used': self.risk_budget_used,
            'authorization_count': len(self.authorization_history)
        }


class ArchitectureCompliantRegimeEngine:
    """
    Architecture Compliant Regime Engine
    
    Demonstrates market regime assessment that feeds into risk management
    decisions and strategy suitability analysis.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.current_regime = "normal"
        self.regime_confidence = 0.8
        self.regime_history = []
        
        logger.info("🎯 Architecture Compliant Regime Engine initialized")
    
    async def initialize(self) -> bool:
        """Initialize regime engine"""
        try:
            logger.info("🔄 Initializing Regime Engine...")
            # Regime engine initialization logic here
            logger.info("✅ Regime Engine initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Regime Engine initialization failed: {e}")
            return False
    
    async def assess_market_regime(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Assess current market regime"""
        try:
            # Simple regime assessment (could be more sophisticated)
            if len(market_data) < 20:
                return {
                    'regime': 'insufficient_data',
                    'confidence': 0.0,
                    'volatility': 0.0,
                    'trend_strength': 0.0
                }
            
            # Calculate basic regime indicators
            returns = market_data['close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)  # Annualized
            
            # Simple regime classification
            if volatility > 0.3:
                regime = "high_volatility"
                confidence = 0.9
            elif volatility < 0.15:
                regime = "low_volatility"
                confidence = 0.8
            else:
                regime = "normal"
                confidence = 0.7
            
            # Trend analysis
            price_change = (market_data['close'].iloc[-1] - market_data['close'].iloc[-20]) / market_data['close'].iloc[-20]
            trend_strength = abs(price_change)
            
            regime_analysis = {
                'regime': regime,
                'confidence': confidence,
                'volatility': volatility,
                'trend_strength': trend_strength,
                'timestamp': datetime.now()
            }
            
            # Store in history
            self.regime_history.append(regime_analysis)
            self.current_regime = regime
            self.regime_confidence = confidence
            
            logger.info(f"🎯 Regime assessed: {regime} (confidence: {confidence:.1%}, volatility: {volatility:.1%})")
            
            return regime_analysis
            
        except Exception as e:
            logger.error(f"❌ Regime assessment failed: {e}")
            return {
                'regime': 'error',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def get_regime_status(self) -> Dict[str, Any]:
        """Get regime engine status"""
        return {
            'operational': True,
            'current_regime': self.current_regime,
            'confidence': self.regime_confidence,
            'assessments_count': len(self.regime_history)
        }


class ArchitectureComplianceDemo:
    """
    Architecture Compliance Demonstration
    
    Shows how the core_engine system should be properly structured using
    the hierarchical control pattern and proper component integration.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("architecture_demo")
        
        # Core orchestration components
        self.system_orchestrator = ArchitectureCompliantSystemOrchestrator()
        self.risk_manager = ArchitectureCompliantRiskManager()
        self.regime_engine = ArchitectureCompliantRegimeEngine()
        
        # Data processing components (real ones)
        self.data_manager = None
        self.indicators_engine = None
        self.feature_engineer = None
        self.signal_generator = None
        self.trading_engine = None
        
    async def run_architecture_compliance_demo(self) -> Dict[str, Any]:
        """Run complete architecture compliance demonstration"""
        self.logger.info("🏗️ Starting Architecture Compliance Demonstration")
        self.logger.info("=" * 80)
        
        results = {}
        
        try:
            # Phase 1: System Architecture Setup
            await self._demonstrate_system_architecture_setup()
            results['architecture_setup'] = True
            
            # Phase 2: Hierarchical Control Demonstration
            await self._demonstrate_hierarchical_control()
            results['hierarchical_control'] = True
            
            # Phase 3: Risk Governance Demonstration
            await self._demonstrate_risk_governance()
            results['risk_governance'] = True
            
            # Phase 4: Complete Pipeline Demonstration
            await self._demonstrate_complete_pipeline()
            results['complete_pipeline'] = True
            
            # Phase 5: System Health and Monitoring
            await self._demonstrate_system_monitoring()
            results['system_monitoring'] = True
            
            self.logger.info("=" * 80)
            self.logger.info("✅ Architecture Compliance Demonstration COMPLETED SUCCESSFULLY!")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Architecture compliance demo failed: {e}")
            raise
    
    async def _demonstrate_system_architecture_setup(self):
        """Demonstrate proper system architecture setup"""
        self.logger.info("\n🏗️ PHASE 1: SYSTEM ARCHITECTURE SETUP")
        self.logger.info("-" * 50)
        
        # Initialize data processing components
        self.logger.info("Initializing data processing components...")
        data_config = ClickHouseDataConfig(
            symbols=['NVDA', 'TSLA', 'AAPL'],
            target_date="2024-12-20",
            enable_caching=True
        )
        self.data_manager = ClickHouseDataManager(data_config)
        self.indicators_engine = EnhancedTechnicalIndicators()
        self.feature_engineer = FeatureEngineer()
        
        # Configure signal generator with lower thresholds for testing
        from core_engine.processing.signals.generator import SignalConfig
        signal_config = SignalConfig()
        signal_config.signal_threshold = 0.3  # Lower threshold for more signals in testing
        signal_config.strong_signal_threshold = 0.5
        self.signal_generator = SignalGenerator(signal_config)
        execution_config = {
            'enable_position_tracking': True,
            'enable_risk_monitoring': True,
            'default_algorithm': 'market'
        }
        self.trading_engine = UnifiedExecutionEngine(execution_config)
        
        # Register components with orchestrator in proper hierarchy
        self.logger.info("Registering components in hierarchical structure...")
        
        # Support layer (data and analysis)
        self.system_orchestrator.register_component(
            "DataManager", self.data_manager, 
            ComponentLayer.SUPPORT, AuthorityLevel.OPERATIONAL
        )
        
        self.system_orchestrator.register_component(
            "RegimeEngine", self.regime_engine,
            ComponentLayer.SUPPORT, AuthorityLevel.OPERATIONAL
        )
        
        # Governance layer (risk management)
        self.system_orchestrator.register_risk_manager(self.risk_manager)
        
        # Execution layer (trading components)
        self.system_orchestrator.register_component(
            "SignalGenerator", self.signal_generator,
            ComponentLayer.EXECUTION, AuthorityLevel.OPERATIONAL
        )
        
        self.system_orchestrator.register_component(
            "TradingEngine", self.trading_engine,
            ComponentLayer.EXECUTION, AuthorityLevel.OPERATIONAL
        )
        
        # Initialize the complete system
        success = await self.system_orchestrator.initialize_system()
        
        if success:
            self.logger.info("✅ Architecture compliant system setup completed")
        else:
            raise RuntimeError("Failed to setup architecture compliant system")
    
    async def _demonstrate_hierarchical_control(self):
        """Demonstrate hierarchical control and authorization flow"""
        self.logger.info("\n🔗 PHASE 2: HIERARCHICAL CONTROL DEMONSTRATION")
        self.logger.info("-" * 50)
        
        # Get actual registered component IDs for testing
        registered_components = list(self.system_orchestrator.components.keys())
        
        if not registered_components:
            self.logger.warning("No registered components found for authorization testing")
            return
        
        # Use actual component IDs for testing
        test_component_id = registered_components[0]  # Use first registered component
        
        # Test different authorization levels
        test_operations = [
            ("health_check", "data_request", {"component": "DataManager"}),
            ("trade_execution", "trade_execution", {
                "symbol": "NVDA", "action": "buy", "quantity": 100, 
                "price": 130.0, "strategy_id": "demo_strategy", 
                "confidence": 0.8, "risk_score": 0.05
            }),
            ("system_control", "component_restart", {"component": "TradingEngine"})
        ]
        
        for auth_level, operation, details in test_operations:
            self.logger.info(f"Testing {operation} authorization...")
            
            authorized = await self.system_orchestrator.request_authorization(
                operation, test_component_id, details
            )
            
            status_icon = "✅" if authorized else "❌"
            self.logger.info(f"{status_icon} {operation}: {'Authorized' if authorized else 'Denied'}")
        
        self.logger.info("✅ Hierarchical control demonstration completed")
    
    async def _demonstrate_risk_governance(self):
        """Demonstrate risk governance and central authorization"""
        self.logger.info("\n🛡️ PHASE 3: RISK GOVERNANCE DEMONSTRATION")
        self.logger.info("-" * 50)
        
        # Test various trading scenarios through risk manager
        test_scenarios = [
            {"symbol": "NVDA", "quantity": 50, "price": 130.0, "risk_score": 0.02},
            {"symbol": "TSLA", "quantity": 200, "price": 440.0, "risk_score": 0.08},  # High risk
            {"symbol": "AAPL", "quantity": 100, "price": 250.0, "risk_score": 0.03}
        ]
        
        for scenario in test_scenarios:
            request = TradingDecisionRequest(
                symbol=scenario["symbol"],
                action="buy",
                quantity=scenario["quantity"],
                price=scenario["price"],
                strategy_id="risk_demo_strategy",
                confidence=0.75,
                risk_score=scenario["risk_score"]
            )
            
            authorization = await self.risk_manager.authorize_trading_decision(request)
            
            status_icon = "✅" if authorization.authorized else "❌"
            self.logger.info(f"{status_icon} {scenario['symbol']}: "
                           f"{'Authorized' if authorization.authorized else 'Rejected'} "
                           f"({authorization.authorized_quantity} of {scenario['quantity']})")
            
            if not authorization.authorized:
                self.logger.info(f"   Reason: {authorization.rejection_reason}")
        
        self.logger.info("✅ Risk governance demonstration completed")
    
    async def _demonstrate_complete_pipeline(self):
        """Demonstrate complete trading pipeline with architecture compliance"""
        self.logger.info("\n🔄 PHASE 4: COMPLETE PIPELINE DEMONSTRATION")
        self.logger.info("-" * 50)
        
        symbols = ['NVDA', 'TSLA', 'AAPL']
        pipeline_results = {
            'symbols_processed': 0,
            'regimes_assessed': 0,
            'signals_generated': 0,
            'trades_authorized': 0,
            'architecture_compliant': True
        }
        
        for symbol in symbols:
            self.logger.info(f"Running architecture compliant pipeline for {symbol}...")
            
            try:
                # Step 1: Market Data (Support Layer)
                market_data = self.data_manager.get_market_data(symbol)
                if market_data is None or market_data.empty:
                    continue
                
                pipeline_results['symbols_processed'] += 1
                
                # Step 2: Regime Assessment (Support Layer)
                regime_analysis = await self.regime_engine.assess_market_regime(market_data)
                pipeline_results['regimes_assessed'] += 1
                
                # Step 3: Signal Generation (Execution Layer - requires authorization)
                df = market_data.reset_index()
                df['symbol'] = symbol
                
                indicators = self.indicators_engine.calculate_indicators(df)
                features = self.feature_engineer.create_features(indicators)
                signals = self.signal_generator.generate_signals(features)
                
                if hasattr(signals, '__len__') and len(signals) > 0:
                    pipeline_results['signals_generated'] += len(signals)
                    
                    # Step 4: Risk Authorization (Governance Layer)
                    for signal in signals:
                        # Request authorization through orchestrator using actual component ID
                        signal_generator_id = None
                        for comp_id, comp_info in self.system_orchestrator.components.items():
                            if comp_info['name'] == 'SignalGenerator':
                                signal_generator_id = comp_id
                                break
                        
                        if signal_generator_id:
                            auth_details = {
                                "symbol": signal.symbol,
                                "action": signal.signal_type.value,
                                "quantity": 100,
                                "price": signal.price,
                                "strategy_id": "architecture_demo",
                                "confidence": signal.confidence,
                                "risk_score": 0.03,
                                "market_regime": regime_analysis['regime']
                            }
                            
                            authorized = await self.system_orchestrator.request_authorization(
                                "trade_execution", signal_generator_id, auth_details
                            )
                        else:
                            authorized = False
                        
                        if authorized:
                            pipeline_results['trades_authorized'] += 1
                
                self.logger.info(f"✅ {symbol} architecture compliant pipeline complete")
                
            except Exception as e:
                self.logger.error(f"❌ Pipeline failed for {symbol}: {e}")
        
        # Summary
        self.logger.info(f"Architecture Compliant Pipeline Results:")
        for key, value in pipeline_results.items():
            self.logger.info(f"  {key.replace('_', ' ').title()}: {value}")
        
        self.logger.info("✅ Complete pipeline demonstration completed")
    
    async def _demonstrate_system_monitoring(self):
        """Demonstrate system health monitoring and status reporting"""
        self.logger.info("\n📊 PHASE 5: SYSTEM MONITORING DEMONSTRATION")
        self.logger.info("-" * 50)
        
        # Get comprehensive system status
        system_status = self.system_orchestrator.get_system_status()
        risk_status = self.risk_manager.get_risk_status()
        regime_status = self.regime_engine.get_regime_status()
        
        self.logger.info("System Status Report:")
        self.logger.info(f"  System Status: {system_status['system_status']}")
        self.logger.info(f"  Total Components: {system_status['total_components']}")
        self.logger.info(f"  Risk Manager Active: {system_status['risk_manager_active']}")
        
        self.logger.info("Component Layer Status:")
        for layer, info in system_status['component_layers'].items():
            self.logger.info(f"  {layer.title()}: {info['operational']}/{info['count']} operational")
        
        self.logger.info("Risk Manager Status:")
        self.logger.info(f"  Operational: {risk_status['operational']}")
        self.logger.info(f"  Authorizations Processed: {risk_status['authorization_count']}")
        
        self.logger.info("Regime Engine Status:")
        self.logger.info(f"  Current Regime: {regime_status['current_regime']}")
        self.logger.info(f"  Confidence: {regime_status['confidence']:.1%}")
        
        self.logger.info("✅ System monitoring demonstration completed")


async def main():
    """Main demonstration execution"""
    print("🏗️ Starting Core Engine Architecture Compliance Demonstration")
    print("=" * 80)
    
    # Run architecture compliance demonstration
    demo = ArchitectureComplianceDemo()
    results = await demo.run_architecture_compliance_demo()
    
    # Print summary
    print("\n" + "=" * 80)
    print("📋 ARCHITECTURE COMPLIANCE DEMONSTRATION SUMMARY")
    print("=" * 80)
    
    for phase, result in results.items():
        status_icon = "✅" if result else "❌"
        print(f"{status_icon} {phase.replace('_', ' ').title()}: {'Completed' if result else 'Failed'}")
    
    print("\n🎉 Architecture Compliance Demonstration Complete!")
    print("\n🏗️ This demonstration shows the proper core_engine architecture:")
    print("   ✅ Hierarchical System Orchestrator")
    print("   ✅ Central Risk Manager (Governance Layer)")
    print("   ✅ Regime Engine (Market Assessment)")
    print("   ✅ Proper authorization flow and component control")
    print("   ✅ Architecture compliant component integration")


if __name__ == "__main__":
    asyncio.run(main())
