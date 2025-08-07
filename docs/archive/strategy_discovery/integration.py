"""
Strategy Discovery Integration
Connects hybrid strategy discovery with Trading Strategy Layer
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

class StrategyDiscoveryIntegration:
    """Integrates discovered strategies with Trading Strategy Layer"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.parser_integration = StrategyParserIntegration()
        self.bridge_integration = BridgeLayerIntegration()
    
    def integrate_strategy(self, strategy: Dict) -> Dict:
        """
        Integrate discovered strategy with Trading Strategy Layer
        
        Args:
            strategy: Discovered strategy dictionary
            
        Returns:
            Integrated strategy configuration
        """
        self.logger.info(f"Integrating strategy: {strategy.get('name', 'Unknown')}")
        
        # Convert to parser format
        parser_config = self.parser_integration.convert_to_parser_format(strategy)
        
        # Integrate with bridge layer
        bridge_config = self.bridge_integration.integrate_strategy(strategy)
        
        # Create deployment configuration
        deployment_config = self.create_deployment_config(strategy)
        
        return {
            'strategy': strategy,
            'parser_config': parser_config,
            'bridge_config': bridge_config,
            'deployment_config': deployment_config,
            'integration_date': datetime.now().isoformat()
        }
    
    def create_deployment_config(self, strategy: Dict) -> Dict:
        """Create deployment configuration"""
        return {
            'deployment_stage': 'paper_trading',
            'position_size': 0.01,  # 1% for paper trading
            'risk_limits': {
                'max_drawdown': 0.05,
                'max_position_size': 0.02,
                'max_daily_loss': 0.01
            },
            'monitoring': {
                'performance_tracking': True,
                'risk_monitoring': True,
                'alert_thresholds': {
                    'drawdown': 0.03,
                    'daily_loss': 0.005
                }
            }
        }


class StrategyParserIntegration:
    """Integrates with Strategy Parser from Trading Strategy Layer"""
    
    def convert_to_parser_format(self, strategy: Dict) -> Dict:
        """Convert strategy to parser-compatible format"""
        return {
            'strategy_definition': strategy,
            'execution_config': self.generate_execution_config(strategy),
            'monitoring_config': self.generate_monitoring_config(strategy)
        }
    
    def generate_execution_config(self, strategy: Dict) -> Dict:
        """Generate execution configuration"""
        return {
            'execution_engine': 'unified_core_system',
            'risk_manager': 'enhanced_risk_manager',
            'position_manager': 'dynamic_position_manager',
            'order_manager': 'smart_order_manager',
            'data_sources': self.map_data_sources(strategy),
            'signal_processors': self.map_signal_processors(strategy)
        }
    
    def generate_monitoring_config(self, strategy: Dict) -> Dict:
        """Generate monitoring configuration"""
        return {
            'performance_metrics': ['sharpe_ratio', 'max_drawdown', 'annual_return'],
            'risk_metrics': ['var', 'volatility', 'correlation'],
            'alert_thresholds': {
                'drawdown': 0.15,
                'daily_loss': 0.02,
                'volatility': 0.25
            }
        }
    
    def map_data_sources(self, strategy: Dict) -> List[str]:
        """Map strategy to required data sources"""
        data_sources = ['price_data', 'volume_data']
        
        # Add specific data sources based on signals
        for signal in strategy.get('signals', []):
            signal_type = signal.get('signal_type', '')
            if signal_type in ['rsi', 'macd', 'bollinger_bands']:
                data_sources.append('technical_indicators')
            elif signal_type == 'fundamental':
                data_sources.append('fundamental_data')
        
        return list(set(data_sources))
    
    def map_signal_processors(self, strategy: Dict) -> List[str]:
        """Map strategy to signal processors"""
        processors = []
        
        for signal in strategy.get('signals', []):
            signal_type = signal.get('signal_type', '')
            if signal_type == 'moving_average':
                processors.append('ma_processor')
            elif signal_type == 'rsi':
                processors.append('rsi_processor')
            elif signal_type == 'macd':
                processors.append('macd_processor')
            elif signal_type == 'bollinger_bands':
                processors.append('bb_processor')
        
        return list(set(processors))


class BridgeLayerIntegration:
    """Integrates with Bridge Layer from existing system"""
    
    def integrate_strategy(self, strategy: Dict) -> Dict:
        """Integrate strategy with bridge layer"""
        return {
            'data_sources': self.map_data_sources(strategy),
            'signal_processors': self.map_signal_processors(strategy),
            'risk_controllers': self.map_risk_controllers(strategy),
            'execution_handlers': self.map_execution_handlers(strategy)
        }
    
    def map_data_sources(self, strategy: Dict) -> List[str]:
        """Map to bridge layer data sources"""
        sources = []
        
        # Map based on asset universe
        assets = strategy.get('assets', {})
        universe = assets.get('universe', [])
        
        if 'SPY' in universe or 'QQQ' in universe:
            sources.append('polygon_data_source')
        if 'IWM' in universe:
            sources.append('yahoo_data_source')
        
        return sources
    
    def map_signal_processors(self, strategy: Dict) -> List[str]:
        """Map to bridge layer signal processors"""
        processors = []
        
        for signal in strategy.get('signals', []):
            signal_type = signal.get('signal_type', '')
            if signal_type == 'moving_average':
                processors.append('ma_signal_processor')
            elif signal_type == 'rsi':
                processors.append('rsi_signal_processor')
            elif signal_type == 'macd':
                processors.append('macd_signal_processor')
        
        return processors
    
    def map_risk_controllers(self, strategy: Dict) -> List[str]:
        """Map to bridge layer risk controllers"""
        controllers = ['position_risk_controller']
        
        risk_mgmt = strategy.get('risk_management', {})
        if 'stop_loss' in risk_mgmt:
            controllers.append('stop_loss_controller')
        if 'take_profit' in risk_mgmt:
            controllers.append('take_profit_controller')
        
        return controllers
    
    def map_execution_handlers(self, strategy: Dict) -> List[str]:
        """Map to bridge layer execution handlers"""
        handlers = ['market_order_handler']
        
        execution = strategy.get('execution', {})
        if execution.get('execution_model') == 'limit_order':
            handlers.append('limit_order_handler')
        
        return handlers


class DeploymentPipeline:
    """Handles strategy deployment through pipeline"""
    
    def __init__(self):
        self.stages = ['validation', 'backtesting', 'paper_trading', 'live_trading']
        self.logger = logging.getLogger(__name__)
    
    def deploy_strategy(self, strategy: Dict, stage: str = 'paper_trading') -> Dict:
        """Deploy strategy through pipeline"""
        if stage not in self.stages:
            raise ValueError(f"Invalid deployment stage: {stage}")
        
        self.logger.info(f"Deploying strategy to {stage} stage")
        
        # Generate deployment configuration
        deployment_config = self.generate_deployment_config(strategy, stage)
        
        # Deploy to Trading Strategy Layer
        result = self.deploy_to_strategy_layer(strategy, deployment_config)
        
        return {
            'strategy_id': strategy.get('strategy_id'),
            'deployment_stage': stage,
            'deployment_config': deployment_config,
            'deployment_result': result,
            'deployment_date': datetime.now().isoformat()
        }
    
    def generate_deployment_config(self, strategy: Dict, stage: str) -> Dict:
        """Generate deployment configuration for stage"""
        configs = {
            'validation': {
                'position_size': 0.0,
                'risk_limits': {'max_drawdown': 0.0},
                'monitoring': {'performance_tracking': True}
            },
            'backtesting': {
                'position_size': 0.0,
                'risk_limits': {'max_drawdown': 0.0},
                'monitoring': {'performance_tracking': True}
            },
            'paper_trading': {
                'position_size': 0.01,
                'risk_limits': {
                    'max_drawdown': 0.05,
                    'max_position_size': 0.02
                },
                'monitoring': {
                    'performance_tracking': True,
                    'risk_monitoring': True
                }
            },
            'live_trading': {
                'position_size': 0.05,
                'risk_limits': {
                    'max_drawdown': 0.15,
                    'max_position_size': 0.1
                },
                'monitoring': {
                    'performance_tracking': True,
                    'risk_monitoring': True,
                    'real_time_alerts': True
                }
            }
        }
        
        return configs.get(stage, configs['paper_trading'])
    
    def deploy_to_strategy_layer(self, strategy: Dict, config: Dict) -> Dict:
        """Deploy strategy to Trading Strategy Layer"""
        # This would integrate with the actual Trading Strategy Layer
        # For now, return success status
        return {
            'status': 'success',
            'message': f"Strategy deployed successfully",
            'config_applied': config
        } 