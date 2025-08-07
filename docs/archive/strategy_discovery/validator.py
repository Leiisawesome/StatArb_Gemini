"""
Strategy Validation Framework
Comprehensive validation and quality control for discovered strategies
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of strategy validation"""
    is_valid: bool
    score: float
    issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    validation_date: str

class StrategyValidator:
    """Comprehensive strategy validation"""
    
    def __init__(self):
        self.validators = {
            'schema': SchemaValidator(),
            'logic': LogicValidator(),
            'performance': PerformanceValidator(),
            'risk': RiskValidator(),
            'reproducibility': ReproducibilityValidator()
        }
        self.logger = logging.getLogger(__name__)
        
        # Quality thresholds
        self.quality_thresholds = {
            'min_sharpe_ratio': 0.5,
            'max_drawdown': 0.20,
            'min_annual_return': 0.05,
            'min_information_ratio': 0.3,
            'max_volatility': 0.25,
            'min_win_rate': 0.45
        }
    
    def validate_strategy(self, strategy: Dict) -> ValidationResult:
        """
        Comprehensive strategy validation
        
        Args:
            strategy: Strategy dictionary to validate
            
        Returns:
            ValidationResult object
        """
        self.logger.info(f"Validating strategy: {strategy.get('name', 'Unknown')}")
        
        results = {}
        total_score = 0.0
        all_issues = []
        all_warnings = []
        all_recommendations = []
        
        # Schema validation
        schema_result = self.validators['schema'].validate(strategy)
        results['schema'] = schema_result
        total_score += schema_result.score * 0.2  # 20% weight
        
        if not schema_result.is_valid:
            all_issues.extend(schema_result.issues)
        
        # Logic validation
        logic_result = self.validators['logic'].validate(strategy)
        results['logic'] = logic_result
        total_score += logic_result.score * 0.25  # 25% weight
        
        if not logic_result.is_valid:
            all_issues.extend(logic_result.issues)
        
        # Performance validation
        performance_result = self.validators['performance'].validate(strategy)
        results['performance'] = performance_result
        total_score += performance_result.score * 0.25  # 25% weight
        
        if not performance_result.is_valid:
            all_issues.extend(performance_result.issues)
        
        # Risk validation
        risk_result = self.validators['risk'].validate(strategy)
        results['risk'] = risk_result
        total_score += risk_result.score * 0.2  # 20% weight
        
        if not risk_result.is_valid:
            all_issues.extend(risk_result.issues)
        
        # Reproducibility validation
        reproducibility_result = self.validators['reproducibility'].validate(strategy)
        results['reproducibility'] = reproducibility_result
        total_score += reproducibility_result.score * 0.1  # 10% weight
        
        if not reproducibility_result.is_valid:
            all_issues.extend(reproducibility_result.issues)
        
        # Collect warnings and recommendations
        for result in results.values():
            all_warnings.extend(result.warnings)
            all_recommendations.extend(result.recommendations)
        
        # Determine overall validity
        is_valid = all(result.is_valid for result in results.values()) and total_score >= 0.7
        
        return ValidationResult(
            is_valid=is_valid,
            score=total_score,
            issues=all_issues,
            warnings=all_warnings,
            recommendations=all_recommendations,
            validation_date=datetime.now().isoformat()
        )
    
    def filter_strategies(self, strategies: List[Dict], criteria: Dict) -> List[Dict]:
        """
        Filter strategies based on criteria
        
        Args:
            strategies: List of strategies to filter
            criteria: Filtering criteria
            
        Returns:
            Filtered list of strategies
        """
        filtered_strategies = []
        
        for strategy in strategies:
            validation_result = self.validate_strategy(strategy)
            
            if self.meets_criteria(validation_result, criteria):
                filtered_strategies.append(strategy)
        
        return filtered_strategies
    
    def meets_criteria(self, validation_result: ValidationResult, criteria: Dict) -> bool:
        """Check if validation result meets criteria"""
        if 'min_score' in criteria and validation_result.score < criteria['min_score']:
            return False
        
        if 'max_issues' in criteria and len(validation_result.issues) > criteria['max_issues']:
            return False
        
        if 'require_performance' in criteria and criteria['require_performance']:
            if not validation_result.is_valid:
                return False
        
        return True


class SchemaValidator:
    """Validates strategy schema compliance"""
    
    def validate(self, strategy: Dict) -> ValidationResult:
        """Validate strategy against JSON schema"""
        issues = []
        warnings = []
        recommendations = []
        score = 1.0
        
        # Check required fields
        required_fields = ['strategy_id', 'name', 'strategy_type', 'signals']
        for field in required_fields:
            if field not in strategy:
                issues.append(f"Missing required field: {field}")
                score -= 0.2
        
        # Check signal structure
        if 'signals' in strategy:
            for i, signal in enumerate(strategy['signals']):
                if not isinstance(signal, dict):
                    issues.append(f"Signal {i} is not a dictionary")
                    score -= 0.1
                else:
                    if 'signal_type' not in signal:
                        issues.append(f"Signal {i} missing signal_type")
                        score -= 0.1
                    if 'signal_id' not in signal:
                        warnings.append(f"Signal {i} missing signal_id")
                        score -= 0.05
        
        # Check data types
        if 'strategy_type' in strategy and not isinstance(strategy['strategy_type'], str):
            issues.append("strategy_type must be a string")
            score -= 0.1
        
        # Add recommendations
        if 'description' not in strategy:
            recommendations.append("Add strategy description for better documentation")
        
        if 'version' not in strategy:
            recommendations.append("Add version field for strategy versioning")
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            score=max(0.0, score),
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
            validation_date=datetime.now().isoformat()
        )


class LogicValidator:
    """Validates strategy logic consistency"""
    
    def validate(self, strategy: Dict) -> ValidationResult:
        """Validate strategy logic"""
        issues = []
        warnings = []
        recommendations = []
        score = 1.0
        
        # Check signal consistency
        if 'signals' in strategy:
            signal_types = [s.get('signal_type', '') for s in strategy['signals']]
            
            # Check for conflicting signal types
            if 'momentum' in signal_types and 'mean_reversion' in signal_types:
                warnings.append("Mixing momentum and mean reversion signals may cause conflicts")
                score -= 0.1
            
            # Check signal weights
            weights = [s.get('weight', 1.0) for s in strategy['signals']]
            total_weight = sum(weights)
            if abs(total_weight - 1.0) > 0.01:
                warnings.append(f"Signal weights sum to {total_weight}, should be 1.0")
                score -= 0.05
        
        # Check risk management consistency
        if 'risk_management' in strategy:
            risk_mgmt = strategy['risk_management']
            
            # Check position sizing
            if 'position_sizing' in risk_mgmt:
                pos_sizing = risk_mgmt['position_sizing']
                if 'max_position_size' in pos_sizing:
                    max_pos = pos_sizing['max_position_size']
                    if max_pos > 0.5:
                        warnings.append("Maximum position size > 50% may be too risky")
                        score -= 0.1
            
            # Check stop loss vs take profit
            if 'stop_loss' in risk_mgmt and 'take_profit' in risk_mgmt:
                stop_loss = risk_mgmt['stop_loss']
                take_profit = risk_mgmt['take_profit']
                
                if 'percentage' in stop_loss and 'percentage' in take_profit:
                    if stop_loss['percentage'] >= take_profit['percentage']:
                        issues.append("Stop loss percentage >= take profit percentage")
                        score -= 0.2
        
        # Check asset universe
        if 'assets' in strategy:
            assets = strategy['assets']
            if 'universe' in assets and len(assets['universe']) == 0:
                warnings.append("Empty asset universe")
                score -= 0.1
        
        # Add recommendations
        if 'signals' in strategy and len(strategy['signals']) == 1:
            recommendations.append("Consider adding multiple signals for diversification")
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            score=max(0.0, score),
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
            validation_date=datetime.now().isoformat()
        )


class PerformanceValidator:
    """Validates strategy performance metrics"""
    
    def __init__(self):
        self.minimum_criteria = {
            'sharpe_ratio': 0.5,
            'max_drawdown': 0.20,
            'annual_return': 0.05,
            'information_ratio': 0.3,
            'volatility': 0.25,
            'win_rate': 0.45
        }
    
    def validate(self, strategy: Dict) -> ValidationResult:
        """Validate strategy performance"""
        issues = []
        warnings = []
        recommendations = []
        score = 1.0
        
        performance = strategy.get('performance_metrics', {})
        
        # Check each performance metric
        for metric, threshold in self.minimum_criteria.items():
            if metric in performance:
                value = performance[metric]
                
                if not self.meets_threshold(value, threshold, metric):
                    if metric in ['max_drawdown', 'volatility']:
                        issues.append(f"{metric} ({value:.3f}) exceeds threshold ({threshold:.3f})")
                    else:
                        issues.append(f"{metric} ({value:.3f}) below threshold ({threshold:.3f})")
                    score -= 0.2
                else:
                    # Bonus for exceeding thresholds
                    if metric in ['sharpe_ratio', 'annual_return', 'information_ratio']:
                        if value > threshold * 1.5:
                            score += 0.1
                    elif metric in ['max_drawdown', 'volatility']:
                        if value < threshold * 0.7:
                            score += 0.1
        
        # Check for missing performance metrics
        missing_metrics = set(self.minimum_criteria.keys()) - set(performance.keys())
        if missing_metrics:
            warnings.append(f"Missing performance metrics: {', '.join(missing_metrics)}")
            score -= 0.1 * len(missing_metrics)
        
        # Check performance consistency
        if 'sharpe_ratio' in performance and 'volatility' in performance:
            sharpe = performance['sharpe_ratio']
            vol = performance['volatility']
            if vol > 0 and sharpe / vol > 2.0:
                warnings.append("Sharpe ratio per unit volatility seems unusually high")
                score -= 0.05
        
        # Add recommendations
        if 'sharpe_ratio' in performance and performance['sharpe_ratio'] < 1.0:
            recommendations.append("Consider optimizing for higher Sharpe ratio")
        
        if 'max_drawdown' in performance and performance['max_drawdown'] > 0.15:
            recommendations.append("Consider improving risk management to reduce drawdown")
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            score=max(0.0, score),
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
            validation_date=datetime.now().isoformat()
        )
    
    def meets_threshold(self, value: float, threshold: float, metric: str) -> bool:
        """Check if metric meets threshold"""
        if metric in ['max_drawdown', 'volatility']:
            return value <= threshold  # Lower is better
        else:
            return value >= threshold  # Higher is better


class RiskValidator:
    """Validates strategy risk management"""
    
    def validate(self, strategy: Dict) -> ValidationResult:
        """Validate risk management components"""
        issues = []
        warnings = []
        recommendations = []
        score = 1.0
        
        risk_mgmt = strategy.get('risk_management', {})
        
        # Check position sizing
        if 'position_sizing' in risk_mgmt:
            pos_sizing = risk_mgmt['position_sizing']
            
            if 'max_position_size' in pos_sizing:
                max_pos = pos_sizing['max_position_size']
                if max_pos > 0.3:
                    issues.append("Maximum position size > 30% is too risky")
                    score -= 0.3
                elif max_pos > 0.2:
                    warnings.append("Maximum position size > 20% may be risky")
                    score -= 0.1
        
        # Check stop loss
        if 'stop_loss' in risk_mgmt:
            stop_loss = risk_mgmt['stop_loss']
            
            if 'percentage' in stop_loss:
                stop_pct = stop_loss['percentage']
                if stop_pct > 0.1:
                    issues.append("Stop loss > 10% is too wide")
                    score -= 0.2
                elif stop_pct < 0.01:
                    warnings.append("Stop loss < 1% may be too tight")
                    score -= 0.05
        
        # Check portfolio risk limits
        if 'portfolio_risk' in risk_mgmt:
            portfolio_risk = risk_mgmt['portfolio_risk']
            
            if 'var_limit' in portfolio_risk:
                var_limit = portfolio_risk['var_limit']
                if var_limit > 0.05:
                    issues.append("VaR limit > 5% is too high")
                    score -= 0.2
            
            if 'drawdown_limit' in portfolio_risk:
                dd_limit = portfolio_risk['drawdown_limit']
                if dd_limit > 0.25:
                    issues.append("Drawdown limit > 25% is too high")
                    score -= 0.2
        
        # Check for missing risk components
        missing_components = []
        if 'position_sizing' not in risk_mgmt:
            missing_components.append('position_sizing')
        if 'stop_loss' not in risk_mgmt:
            missing_components.append('stop_loss')
        
        if missing_components:
            warnings.append(f"Missing risk management components: {', '.join(missing_components)}")
            score -= 0.1 * len(missing_components)
        
        # Add recommendations
        if 'position_sizing' not in risk_mgmt:
            recommendations.append("Add position sizing rules")
        
        if 'stop_loss' not in risk_mgmt:
            recommendations.append("Add stop loss rules")
        
        if 'take_profit' not in risk_mgmt:
            recommendations.append("Consider adding take profit rules")
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            score=max(0.0, score),
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
            validation_date=datetime.now().isoformat()
        )


class ReproducibilityValidator:
    """Validates strategy reproducibility"""
    
    def validate(self, strategy: Dict) -> ValidationResult:
        """Validate strategy reproducibility"""
        issues = []
        warnings = []
        recommendations = []
        score = 1.0
        
        # Check for required reproducibility fields
        required_fields = ['strategy_id', 'signals', 'assets']
        for field in required_fields:
            if field not in strategy:
                issues.append(f"Missing field required for reproducibility: {field}")
                score -= 0.2
        
        # Check signal parameters
        if 'signals' in strategy:
            for i, signal in enumerate(strategy['signals']):
                if 'parameters' not in signal:
                    warnings.append(f"Signal {i} missing parameters")
                    score -= 0.05
                else:
                    params = signal['parameters']
                    if len(params) == 0:
                        warnings.append(f"Signal {i} has empty parameters")
                        score -= 0.05
        
        # Check for source information
        if 'source' not in strategy:
            warnings.append("Missing source information")
            score -= 0.05
        
        if 'authors' not in strategy:
            warnings.append("Missing author information")
            score -= 0.05
        
        # Check for documentation
        if 'description' not in strategy or len(strategy['description']) < 50:
            warnings.append("Insufficient strategy description")
            score -= 0.05
        
        # Add recommendations
        if 'version' not in strategy:
            recommendations.append("Add version field for tracking changes")
        
        if 'created_date' not in strategy:
            recommendations.append("Add creation date for tracking")
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            score=max(0.0, score),
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
            validation_date=datetime.now().isoformat()
        ) 