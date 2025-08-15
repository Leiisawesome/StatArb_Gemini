"""
Asset-Specific Templates
=======================

Templates specialized for different asset classes with asset-specific
parameters, risk models, and execution logic.

Author: Pro Quant Desk Trader
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..base.template_registry import BaseTemplate, TemplateMetadata, TemplateCategory, TemplateType, TemplateStatus

logger = logging.getLogger(__name__)

class AssetSpecificTemplates:
    """
    Manager for asset-specific template adaptations
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Asset class configurations
        self.asset_configs = {
            'equities': self._get_equity_config(),
            'fixed_income': self._get_fixed_income_config(),
            'currencies': self._get_currency_config(),
            'commodities': self._get_commodity_config(),
            'derivatives': self._get_derivatives_config(),
            'crypto': self._get_crypto_config()
        }
        
        self.logger.info("AssetSpecificTemplates initialized")
    
    def create_equity_template(self, base_template_id: str, 
                              equity_config: Optional[Dict[str, Any]] = None) -> BaseTemplate:
        """Create equity-specific template"""
        
        config = equity_config or self.asset_configs['equities']
        
        metadata = TemplateMetadata(
            template_id=f"{base_template_id}_equity",
            name=f"Equity Strategy - {base_template_id}",
            version="1.0.0",
            category=TemplateCategory.SPECIFIC,
            template_type=TemplateType.COMPLETE_STRATEGY,
            status=TemplateStatus.DRAFT,
            description="Equity-specific strategy template with sector rotation and fundamental analysis",
            author="Pro Quant Desk Trader",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["equity", "stocks", "fundamental", "sector"],
            parent_templates=[base_template_id],
            dependencies=["market_data_equity", "fundamental_data"]
        )
        
        parameters = {
            # Asset-specific parameters
            'asset_class': 'equities',
            'sectors': ['technology', 'healthcare', 'financials', 'consumer'],
            'market_cap_min': 1e9,  # $1B minimum market cap
            'avg_volume_min': 1e6,  # $1M minimum daily volume
            
            # Risk parameters
            'max_sector_concentration': 0.3,  # 30% max in any sector
            'max_single_position': 0.05,      # 5% max in any single stock
            'beta_range': [0.5, 1.5],         # Beta limits
            
            # Trading parameters
            'rebalance_frequency': 'weekly',
            'min_holding_period': 5,  # 5 days minimum
            'transaction_cost_bps': 5,  # 5 bps transaction costs
            
            # Fundamental filters
            'pe_ratio_max': 25,
            'debt_to_equity_max': 0.6,
            'roe_min': 0.15,  # 15% minimum ROE
            
            # Technical parameters
            'momentum_lookback': 20,
            'volatility_lookback': 60,
            'rsi_overbought': 70,
            'rsi_oversold': 30
        }
        
        components = {
            'data_sources': {
                'price_data': 'equity_prices',
                'fundamental_data': 'equity_fundamentals',
                'sector_data': 'sector_classifications'
            },
            'signal_generation': {
                'fundamental_signals': {
                    'type': 'fundamental_analysis',
                    'metrics': ['pe_ratio', 'roe', 'debt_to_equity'],
                    'weights': [0.4, 0.3, 0.3]
                },
                'technical_signals': {
                    'type': 'technical_analysis',
                    'indicators': ['rsi', 'momentum', 'bollinger_bands'],
                    'weights': [0.3, 0.4, 0.3]
                },
                'sector_rotation': {
                    'type': 'sector_momentum',
                    'lookback_period': 60,
                    'weight': 0.3
                }
            },
            'risk_management': {
                'position_sizing': {
                    'type': 'volatility_adjusted',
                    'target_volatility': 0.15,
                    'lookback_period': 252
                },
                'sector_limits': {
                    'max_concentration': 0.3,
                    'rebalance_threshold': 0.05
                },
                'drawdown_protection': {
                    'max_drawdown': 0.2,
                    'stop_loss': 0.1
                }
            },
            'execution': {
                'order_type': 'adaptive',
                'participation_rate': 0.1,
                'time_horizon': '1_day',
                'market_impact_model': 'linear'
            }
        }
        
        return BaseTemplate(
            metadata=metadata,
            configuration=config,
            parameters=parameters,
            components=components
        )
    
    def create_fixed_income_template(self, base_template_id: str,
                                   bond_config: Optional[Dict[str, Any]] = None) -> BaseTemplate:
        """Create fixed income-specific template"""
        
        config = bond_config or self.asset_configs['fixed_income']
        
        metadata = TemplateMetadata(
            template_id=f"{base_template_id}_fixed_income",
            name=f"Fixed Income Strategy - {base_template_id}",
            version="1.0.0",
            category=TemplateCategory.SPECIFIC,
            template_type=TemplateType.COMPLETE_STRATEGY,
            status=TemplateStatus.DRAFT,
            description="Fixed income strategy with duration and credit risk management",
            author="Pro Quant Desk Trader",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["fixed_income", "bonds", "duration", "credit"],
            parent_templates=[base_template_id],
            dependencies=["bond_data", "yield_curves", "credit_ratings"]
        )
        
        parameters = {
            'asset_class': 'fixed_income',
            'duration_range': [2, 10],  # 2-10 year duration
            'credit_quality_min': 'BBB',  # Investment grade minimum
            'yield_min': 0.02,  # 2% minimum yield
            
            # Risk parameters
            'duration_limit': 8.0,
            'credit_concentration_max': 0.25,  # 25% max in any credit rating
            'sector_concentration_max': 0.4,   # 40% max in any sector
            
            # Strategy parameters
            'carry_weight': 0.4,
            'momentum_weight': 0.3,
            'mean_reversion_weight': 0.3,
            'rebalance_frequency': 'monthly'
        }
        
        components = {
            'yield_curve_analysis': {
                'type': 'duration_positioning',
                'curve_fitting': 'nelson_siegel',
                'carry_calculation': 'roll_down'
            },
            'credit_analysis': {
                'type': 'credit_spread_analysis',
                'default_model': 'merton',
                'rating_transitions': True
            },
            'duration_hedging': {
                'type': 'key_rate_hedging',
                'hedge_ratio': 0.95,
                'rebalance_threshold': 0.1
            }
        }
        
        return BaseTemplate(
            metadata=metadata,
            configuration=config,
            parameters=parameters,
            components=components
        )
    
    def create_currency_template(self, base_template_id: str,
                               fx_config: Optional[Dict[str, Any]] = None) -> BaseTemplate:
        """Create currency-specific template"""
        
        config = fx_config or self.asset_configs['currencies']
        
        metadata = TemplateMetadata(
            template_id=f"{base_template_id}_currency",
            name=f"Currency Strategy - {base_template_id}",
            version="1.0.0", 
            category=TemplateCategory.SPECIFIC,
            template_type=TemplateType.COMPLETE_STRATEGY,
            status=TemplateStatus.DRAFT,
            description="Currency strategy with carry trade and momentum factors",
            author="Pro Quant Desk Trader",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["currency", "fx", "carry", "momentum"],
            parent_templates=[base_template_id],
            dependencies=["fx_rates", "interest_rates", "economic_data"]
        )
        
        parameters = {
            'asset_class': 'currencies',
            'currency_pairs': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD'],
            'base_currency': 'USD',
            
            # Carry trade parameters
            'interest_rate_differential_min': 0.01,  # 1% minimum differential
            'carry_lookback': 30,
            
            # Risk parameters
            'var_limit': 0.02,  # 2% daily VaR
            'max_leverage': 3.0,
            'correlation_limit': 0.7,
            
            # Trading parameters
            'holding_period_target': 30,  # 30 days
            'transaction_cost_bps': 2,    # 2 bps spread
            'funding_cost_bps': 1        # 1 bps funding
        }
        
        components = {
            'carry_signals': {
                'type': 'interest_rate_differential',
                'forward_premium_adjustment': True,
                'central_bank_policy_factor': True
            },
            'momentum_signals': {
                'type': 'trend_following',
                'lookback_periods': [10, 20, 60],
                'weights': [0.3, 0.4, 0.3]
            },
            'fundamental_signals': {
                'type': 'purchasing_power_parity',
                'economic_indicators': ['inflation', 'gdp_growth', 'current_account'],
                'weights': [0.4, 0.3, 0.3]
            }
        }
        
        return BaseTemplate(
            metadata=metadata,
            configuration=config,
            parameters=parameters,
            components=components
        )
    
    def create_commodity_template(self, base_template_id: str,
                                commodity_config: Optional[Dict[str, Any]] = None) -> BaseTemplate:
        """Create commodity-specific template"""
        
        config = commodity_config or self.asset_configs['commodities']
        
        metadata = TemplateMetadata(
            template_id=f"{base_template_id}_commodity",
            name=f"Commodity Strategy - {base_template_id}",
            version="1.0.0",
            category=TemplateCategory.SPECIFIC,
            template_type=TemplateType.COMPLETE_STRATEGY,
            status=TemplateStatus.DRAFT,
            description="Commodity strategy with seasonal patterns and inventory analysis",
            author="Pro Quant Desk Trader",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=["commodity", "seasonal", "inventory", "momentum"],
            parent_templates=[base_template_id],
            dependencies=["commodity_prices", "inventory_data", "weather_data"]
        )
        
        parameters = {
            'asset_class': 'commodities',
            'commodity_sectors': ['energy', 'metals', 'agriculture'],
            'seasonal_factor_weight': 0.3,
            'inventory_factor_weight': 0.3,
            'momentum_factor_weight': 0.4,
            
            # Risk parameters
            'volatility_target': 0.2,  # 20% target volatility
            'max_sector_concentration': 0.5,
            'contango_backwardation_limit': 0.1,
            
            # Trading parameters
            'roll_schedule': 'optimal',  # Optimal contract rolling
            'storage_cost_adjustment': True
        }
        
        components = {
            'seasonal_analysis': {
                'type': 'historical_seasonal_patterns',
                'lookback_years': 10,
                'weather_adjustment': True
            },
            'inventory_analysis': {
                'type': 'supply_demand_balance',
                'inventory_change_signals': True,
                'production_forecasts': True
            },
            'curve_analysis': {
                'type': 'term_structure_momentum',
                'contango_backwardation_signals': True,
                'roll_yield_optimization': True
            }
        }
        
        return BaseTemplate(
            metadata=metadata,
            configuration=config,
            parameters=parameters,
            components=components
        )
    
    def _get_equity_config(self) -> Dict[str, Any]:
        """Get equity asset class configuration"""
        return {
            'asset_class': 'equities',
            'market_hours': {'start': '09:30', 'end': '16:00', 'timezone': 'US/Eastern'},
            'settlement': 'T+2',
            'liquidity_requirements': {'min_adv': 1e6, 'min_market_cap': 1e9},
            'corporate_actions': ['dividends', 'splits', 'spinoffs'],
            'risk_models': ['factor_model', 'covariance_estimation'],
            'data_requirements': ['prices', 'fundamentals', 'estimates']
        }
    
    def _get_fixed_income_config(self) -> Dict[str, Any]:
        """Get fixed income asset class configuration"""
        return {
            'asset_class': 'fixed_income',
            'market_hours': {'start': '08:00', 'end': '17:00', 'timezone': 'US/Eastern'},
            'settlement': 'T+1',
            'duration_calculation': 'modified_duration',
            'yield_conventions': {'accrual': '30/360', 'compounding': 'semi_annual'},
            'credit_risk_models': ['structural', 'reduced_form'],
            'data_requirements': ['prices', 'yields', 'ratings', 'fundamentals']
        }
    
    def _get_currency_config(self) -> Dict[str, Any]:
        """Get currency asset class configuration"""
        return {
            'asset_class': 'currencies',
            'market_hours': {'start': '17:00', 'end': '17:00', 'timezone': 'UTC'},  # 24/7
            'settlement': 'T+2',
            'quotation': 'direct',
            'funding_currency': 'USD',
            'data_requirements': ['spot_rates', 'forwards', 'interest_rates', 'volatility']
        }
    
    def _get_commodity_config(self) -> Dict[str, Any]:
        """Get commodity asset class configuration"""
        return {
            'asset_class': 'commodities',
            'market_hours': {'varies_by_commodity': True},
            'settlement': 'physical_or_cash',
            'contract_specifications': {'size': 'varies', 'delivery': 'varies'},
            'storage_costs': True,
            'seasonality': True,
            'data_requirements': ['futures_prices', 'inventory', 'production', 'weather']
        }
    
    def _get_derivatives_config(self) -> Dict[str, Any]:
        """Get derivatives asset class configuration"""
        return {
            'asset_class': 'derivatives',
            'margin_requirements': True,
            'mark_to_market': 'daily',
            'greeks_calculation': True,
            'volatility_surface': True,
            'data_requirements': ['underlying_prices', 'volatility', 'interest_rates']
        }
    
    def _get_crypto_config(self) -> Dict[str, Any]:
        """Get cryptocurrency asset class configuration"""
        return {
            'asset_class': 'crypto',
            'market_hours': {'start': '00:00', 'end': '23:59', 'timezone': 'UTC'},  # 24/7
            'settlement': 'varies_by_exchange',
            'high_volatility': True,
            'regulatory_considerations': True,
            'data_requirements': ['prices', 'volume', 'on_chain_metrics', 'sentiment']
        }
