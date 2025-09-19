"""
Signals Engine - Signal Validator
Advanced signal validation with quality assessment, consistency checks, and risk validation
"""

import logging
import threading
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict, deque
from abc import ABC, abstractmethod
import json
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationCategory(Enum):
    """Validation categories"""
    DATA_QUALITY = "data_quality"
    SIGNAL_QUALITY = "signal_quality"
    RISK_VALIDATION = "risk_validation"
    CONSISTENCY = "consistency"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"
    STATISTICAL = "statistical"


class ValidationStatus(Enum):
    """Validation status"""
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    CRITICAL_FAILURE = "critical_failure"


@dataclass
class ValidationRule:
    """Signal validation rule"""
    rule_id: str
    name: str
    description: str
    category: ValidationCategory
    level: ValidationLevel
    
    # Rule parameters
    threshold: Optional[float] = None
    min_threshold: Optional[float] = None
    max_threshold: Optional[float] = None
    
    # Validation function
    validation_function: Optional[Callable] = None
    
    # Rule configuration
    enabled: bool = True
    mandatory: bool = False
    weight: float = 1.0
    
    # Context requirements
    required_fields: List[str] = field(default_factory=list)
    required_context: List[str] = field(default_factory=list)
    
    # Custom parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Validation result for a single rule"""
    rule_id: str
    status: ValidationStatus
    message: str
    
    # Metrics
    score: float  # 0-1 score for this rule
    value: Optional[float] = None
    threshold: Optional[float] = None
    
    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    
    # Timing
    validation_time: datetime = field(default_factory=datetime.now)
    execution_time_ms: float = 0.0


@dataclass
class SignalValidationReport:
    """Comprehensive signal validation report"""
    signal_id: str
    symbol: str
    validation_timestamp: datetime
    
    # Overall assessment
    overall_status: ValidationStatus
    overall_score: float  # 0-1 overall quality score
    confidence_level: float  # 0-1 confidence in signal
    
    # Category scores
    data_quality_score: float = 0.0
    signal_quality_score: float = 0.0
    risk_score: float = 0.0
    consistency_score: float = 0.0
    
    # Individual results
    validation_results: List[ValidationResult] = field(default_factory=list)
    
    # Summary statistics
    rules_passed: int = 0
    rules_warning: int = 0
    rules_failed: int = 0
    rules_critical: int = 0
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    risk_warnings: List[str] = field(default_factory=list)
    
    # Metadata
    validation_duration_ms: float = 0.0
    validator_version: str = "1.0"


@dataclass
class PortfolioValidationReport:
    """Portfolio-level validation report"""
    validation_id: str
    validation_timestamp: datetime
    
    # Portfolio metrics
    total_signals: int
    valid_signals: int
    invalid_signals: int
    
    # Risk metrics
    portfolio_concentration: float
    sector_concentration: Dict[str, float] = field(default_factory=dict)
    total_exposure: float = 0.0
    net_exposure: float = 0.0
    
    # Quality distribution
    signal_quality_distribution: Dict[str, int] = field(default_factory=dict)
    average_signal_quality: float = 0.0
    
    # Portfolio-level issues
    portfolio_issues: List[str] = field(default_factory=list)
    risk_alerts: List[str] = field(default_factory=list)
    
    # Individual signal reports
    signal_reports: List[SignalValidationReport] = field(default_factory=list)


class ValidationRuleEngine:
    """Validation rule engine with built-in rules"""
    
    def __init__(self):
        self.rules = {}
        self._initialize_default_rules()
    
    def _initialize_default_rules(self) -> None:
        """Initialize default validation rules"""
        
        # Data quality rules
        self.register_rule(ValidationRule(
            rule_id="signal_strength_range",
            name="Signal Strength Range",
            description="Signal strength should be within valid range",
            category=ValidationCategory.DATA_QUALITY,
            level=ValidationLevel.ERROR,
            min_threshold=-1.0,
            max_threshold=1.0,
            validation_function=self._validate_signal_strength_range
        ))
        
        self.register_rule(ValidationRule(
            rule_id="confidence_range",
            name="Confidence Range",
            description="Confidence should be between 0 and 1",
            category=ValidationCategory.DATA_QUALITY,
            level=ValidationLevel.ERROR,
            min_threshold=0.0,
            max_threshold=1.0,
            validation_function=self._validate_confidence_range
        ))
        
        self.register_rule(ValidationRule(
            rule_id="min_confidence_threshold",
            name="Minimum Confidence",
            description="Signal confidence should meet minimum threshold",
            category=ValidationCategory.SIGNAL_QUALITY,
            level=ValidationLevel.WARNING,
            threshold=0.5,
            validation_function=self._validate_min_confidence
        ))
        
        # Signal quality rules
        self.register_rule(ValidationRule(
            rule_id="signal_significance",
            name="Signal Significance",
            description="Signal should be statistically significant",
            category=ValidationCategory.STATISTICAL,
            level=ValidationLevel.WARNING,
            threshold=2.0,  # 2 standard deviations
            validation_function=self._validate_signal_significance
        ))
        
        self.register_rule(ValidationRule(
            rule_id="position_size_limit",
            name="Position Size Limit",
            description="Position size should not exceed maximum limit",
            category=ValidationCategory.RISK_VALIDATION,
            level=ValidationLevel.ERROR,
            threshold=0.1,  # 10% maximum position
            validation_function=self._validate_position_size
        ))
        
        # Risk validation rules
        self.register_rule(ValidationRule(
            rule_id="volatility_check",
            name="Volatility Check",
            description="Expected volatility should be within reasonable bounds",
            category=ValidationCategory.RISK_VALIDATION,
            level=ValidationLevel.WARNING,
            max_threshold=1.0,  # 100% annual volatility
            validation_function=self._validate_volatility
        ))
        
        self.register_rule(ValidationRule(
            rule_id="correlation_check",
            name="Correlation Check",
            description="Signal should not be highly correlated with recent signals",
            category=ValidationCategory.CONSISTENCY,
            level=ValidationLevel.INFO,
            threshold=0.9,  # Maximum correlation
            validation_function=self._validate_correlation
        ))
        
        # Performance rules
        self.register_rule(ValidationRule(
            rule_id="historical_performance",
            name="Historical Performance",
            description="Signal type should have positive historical performance",
            category=ValidationCategory.PERFORMANCE,
            level=ValidationLevel.INFO,
            threshold=0.0,  # Positive expected return
            validation_function=self._validate_historical_performance
        ))
        
        logger.info("Default validation rules initialized")
    
    def register_rule(self, rule: ValidationRule) -> None:
        """Register a validation rule"""
        self.rules[rule.rule_id] = rule
        logger.debug(f"Registered validation rule: {rule.rule_id}")
    
    def unregister_rule(self, rule_id: str) -> bool:
        """Unregister a validation rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.debug(f"Unregistered validation rule: {rule_id}")
            return True
        return False
    
    def get_rules(self, category: Optional[ValidationCategory] = None) -> List[ValidationRule]:
        """Get validation rules by category"""
        if category:
            return [rule for rule in self.rules.values() if rule.category == category]
        return list(self.rules.values())
    
    # Built-in validation functions
    def _validate_signal_strength_range(self, signal: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate signal strength is within range"""
        rule = self.rules["signal_strength_range"]
        
        strength = getattr(signal, 'strength', 0.0)
        
        if rule.min_threshold <= strength <= rule.max_threshold:
            return ValidationResult(
                rule_id=rule.rule_id,
                status=ValidationStatus.PASSED,
                message="Signal strength within valid range",
                score=1.0,
                value=strength
            )
        else:
            return ValidationResult(
                rule_id=rule.rule_id,
                status=ValidationStatus.FAILED,
                message=f"Signal strength {strength:.3f} outside valid range [{rule.min_threshold}, {rule.max_threshold}]",
                score=0.0,
                value=strength
            )
    
    def _validate_confidence_range(self, signal: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate confidence is within range"""
        rule = self.rules["confidence_range"]
        
        confidence = getattr(signal, 'confidence', 0.5)
        
        if rule.min_threshold <= confidence <= rule.max_threshold:
            return ValidationResult(
                rule_id=rule.rule_id,
                status=ValidationStatus.PASSED,
                message="Confidence within valid range",
                score=1.0,
                value=confidence
            )
        else:
            return ValidationResult(
                rule_id=rule.rule_id,
                status=ValidationStatus.FAILED,
                message=f"Confidence {confidence:.3f} outside valid range [{rule.min_threshold}, {rule.max_threshold}]",
                score=0.0,
                value=confidence
            )
    
    def _validate_min_confidence(self, signal: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate minimum confidence threshold"""
        rule = self.rules["min_confidence_threshold"]
        
        confidence = getattr(signal, 'confidence', 0.5)
        
        if confidence >= rule.threshold:
            return ValidationResult(
                rule_id=rule.rule_id,
                status=ValidationStatus.PASSED,
                message="Confidence meets minimum threshold",
                score=confidence,
                value=confidence,
                threshold=rule.threshold
            )
        else:
            return ValidationResult(
                rule_id=rule.rule_id,
                status=ValidationStatus.WARNING,
                message=f"Confidence {confidence:.3f} below threshold {rule.threshold:.3f}",
                score=confidence / rule.threshold,
                value=confidence,
                threshold=rule.threshold
            )
    
    def _validate_signal_significance(self, signal: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate signal statistical significance"""
        rule = self.rules["signal_significance"]
        
        strength = getattr(signal, 'strength', 0.0)
        z_score = getattr(signal, 'z_score', None)
        
        if z_score is None:
            # Estimate z-score from strength and context
            historical_volatility = context.get('historical_volatility', 0.2)
            z_score = abs(strength) / max(historical_volatility, 0.01)
        
        if abs(z_score) >= rule.threshold:
            return ValidationResult(
                rule_id=rule.rule_id,
                status=ValidationStatus.PASSED,
                message="Signal is statistically significant",
                score=min(abs(z_score) / rule.threshold, 1.0),
                value=abs(z_score),
                threshold=rule.threshold
            )
        else:
            return ValidationResult(
                rule_id=rule.rule_id,
                status=ValidationStatus.WARNING,
                message=f"Signal z-score {abs(z_score):.2f} below significance threshold {rule.threshold:.2f}",
                score=abs(z_score) / rule.threshold,
                value=abs(z_score),
                threshold=rule.threshold
            )
    
    def _validate_position_size(self, signal: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate position size limits"""
        rule = self.rules["position_size_limit"]
        
        position_size = getattr(signal, 'suggested_position_size', 0.0)
        
        if abs(position_size) <= rule.threshold:
            return ValidationResult(
                rule_id=rule.rule_id,
                status=ValidationStatus.PASSED,
                message="Position size within limits",
                score=1.0,
                value=abs(position_size),
                threshold=rule.threshold
            )
        else:
            return ValidationResult(
                rule_id=rule.rule_id,
                status=ValidationStatus.FAILED,
                message=f"Position size {abs(position_size):.3f} exceeds limit {rule.threshold:.3f}",
                score=0.0,
                value=abs(position_size),
                threshold=rule.threshold,
                suggestions=["Reduce position size", "Apply position scaling"]
            )
    
    def _validate_volatility(self, signal: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate expected volatility"""
        rule = self.rules["volatility_check"]
        
        volatility = getattr(signal, 'expected_volatility', context.get('historical_volatility', 0.2))
        
        if volatility <= rule.max_threshold:
            return ValidationResult(
                rule_id=rule.rule_id,
                status=ValidationStatus.PASSED,
                message="Volatility within acceptable range",
                score=1.0 - (volatility / rule.max_threshold),
                value=volatility,
                threshold=rule.max_threshold
            )
        else:
            return ValidationResult(
                rule_id=rule.rule_id,
                status=ValidationStatus.WARNING,
                message=f"High volatility {volatility:.1%} exceeds threshold {rule.max_threshold:.1%}",
                score=max(0, 1.0 - (volatility - rule.max_threshold)),
                value=volatility,
                threshold=rule.max_threshold,
                suggestions=["Consider volatility scaling", "Review risk parameters"]
            )
    
    def _validate_correlation(self, signal: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate signal correlation with recent signals"""
        rule = self.rules["correlation_check"]
        
        # Get recent signals from context
        recent_signals = context.get('recent_signals', [])
        symbol = getattr(signal, 'symbol', '')
        
        if not recent_signals:
            return ValidationResult(
                rule_id=rule.rule_id,
                status=ValidationStatus.PASSED,
                message="No recent signals to compare",
                score=1.0
            )
        
        # Calculate correlation with recent signals for same symbol
        symbol_signals = [s for s in recent_signals if getattr(s, 'symbol', '') == symbol]
        
        if len(symbol_signals) < 2:
            return ValidationResult(
                rule_id=rule.rule_id,
                status=ValidationStatus.PASSED,
                message="Insufficient recent signals for correlation check",
                score=1.0
            )
        
        # Simplified correlation check
        current_strength = getattr(signal, 'strength', 0.0)
        recent_strengths = [getattr(s, 'strength', 0.0) for s in symbol_signals[-5:]]  # Last 5 signals
        
        if len(recent_strengths) > 1:
            recent_avg = np.mean(recent_strengths)
            correlation = abs(current_strength - recent_avg) / (max(abs(recent_avg), 0.1))
            correlation = min(correlation, 1.0)
            
            if correlation < rule.threshold:
                return ValidationResult(
                    rule_id=rule.rule_id,
                    status=ValidationStatus.PASSED,
                    message="Signal shows good diversification from recent signals",
                    score=1.0 - correlation,
                    value=correlation,
                    threshold=rule.threshold
                )
            else:
                return ValidationResult(
                    rule_id=rule.rule_id,
                    status=ValidationStatus.WARNING,
                    message=f"Signal highly correlated with recent signals (correlation: {correlation:.2f})",
                    score=max(0, 1.0 - correlation),
                    value=correlation,
                    threshold=rule.threshold,
                    suggestions=["Review signal diversification", "Consider signal timing"]
                )
        
        return ValidationResult(
            rule_id=rule.rule_id,
            status=ValidationStatus.PASSED,
            message="Correlation check completed",
            score=0.8
        )
    
    def _validate_historical_performance(self, signal: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate historical performance"""
        rule = self.rules["historical_performance"]
        
        # Get historical performance from context
        signal_type = getattr(signal, 'signal_type', None)
        historical_performance = context.get('historical_performance', {})
        
        if signal_type and signal_type.value in historical_performance:
            performance = historical_performance[signal_type.value]
            
            if performance >= rule.threshold:
                return ValidationResult(
                    rule_id=rule.rule_id,
                    status=ValidationStatus.PASSED,
                    message=f"Signal type has positive historical performance ({performance:.1%})",
                    score=min(performance + 1, 1.0) if performance >= 0 else 0.0,
                    value=performance,
                    threshold=rule.threshold
                )
            else:
                return ValidationResult(
                    rule_id=rule.rule_id,
                    status=ValidationStatus.WARNING,
                    message=f"Signal type has poor historical performance ({performance:.1%})",
                    score=max(0, performance + 1),
                    value=performance,
                    threshold=rule.threshold,
                    suggestions=["Review signal strategy", "Consider alternative approaches"]
                )
        
        return ValidationResult(
            rule_id=rule.rule_id,
            status=ValidationStatus.PASSED,
            message="No historical performance data available",
            score=0.5
        )


class SignalValidator:
    """
    Advanced signal validation system
    
    Provides comprehensive validation of trading signals including
    quality assessment, risk validation, and consistency checks.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize signal validator"""
        self.config = config or {}
        
        # Validation engine
        self.rule_engine = ValidationRuleEngine()
        
        # Validation history
        self._validation_history = deque(maxlen=10000)
        self._signal_history = defaultdict(list)  # symbol -> [signals]
        
        # Performance tracking
        self._validation_times = deque(maxlen=1000)
        self._validation_stats = defaultdict(int)
        
        # Threading
        self._lock = threading.Lock()
        
        # Configuration
        self.enable_all_rules = self.config.get('enable_all_rules', True)
        self.fail_on_critical = self.config.get('fail_on_critical', True)
        self.min_overall_score = self.config.get('min_overall_score', 0.5)
        
        logger.info("SignalValidator initialized")
    
    async def validate_signal(
        self,
        signal: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> SignalValidationReport:
        """Validate a single signal"""
        
        start_time = time.time()
        context = context or {}
        
        # Add recent signals to context
        symbol = getattr(signal, 'symbol', '')
        with self._lock:
            context['recent_signals'] = self._signal_history.get(symbol, [])
        
        # Initialize report
        report = SignalValidationReport(
            signal_id=getattr(signal, 'signal_id', f'signal_{int(time.time())}'),
            symbol=symbol,
            validation_timestamp=datetime.now(),
            overall_status=ValidationStatus.PASSED,
            overall_score=0.0,
            confidence_level=0.0
        )
        
        try:
            # Run all validation rules
            category_scores = defaultdict(list)
            category_weights = {
                ValidationCategory.DATA_QUALITY: 0.3,
                ValidationCategory.SIGNAL_QUALITY: 0.25,
                ValidationCategory.RISK_VALIDATION: 0.25,
                ValidationCategory.CONSISTENCY: 0.1,
                ValidationCategory.STATISTICAL: 0.1
            }
            
            for rule in self.rule_engine.get_rules():
                if not rule.enabled:
                    continue
                
                try:
                    # Run validation rule
                    result = await self._run_validation_rule(rule, signal, context)
                    report.validation_results.append(result)
                    
                    # Update category scores
                    category_scores[rule.category].append(result.score * rule.weight)
                    
                    # Update counts
                    if result.status == ValidationStatus.PASSED:
                        report.rules_passed += 1
                    elif result.status == ValidationStatus.WARNING:
                        report.rules_warning += 1
                    elif result.status == ValidationStatus.FAILED:
                        report.rules_failed += 1
                    elif result.status == ValidationStatus.CRITICAL_FAILURE:
                        report.rules_critical += 1
                    
                    # Check for critical failures
                    if (result.status == ValidationStatus.CRITICAL_FAILURE or 
                        (rule.level == ValidationLevel.CRITICAL and result.status == ValidationStatus.FAILED)):
                        
                        if self.fail_on_critical:
                            report.overall_status = ValidationStatus.CRITICAL_FAILURE
                            report.risk_warnings.append(f"Critical validation failure: {result.message}")
                
                except Exception as e:
                    logger.error(f"Error running validation rule {rule.rule_id}: {e}")
                    continue
            
            # Calculate category scores
            for category, scores in category_scores.items():
                if scores:
                    avg_score = np.mean(scores)
                    
                    if category == ValidationCategory.DATA_QUALITY:
                        report.data_quality_score = avg_score
                    elif category == ValidationCategory.SIGNAL_QUALITY:
                        report.signal_quality_score = avg_score
                    elif category == ValidationCategory.RISK_VALIDATION:
                        report.risk_score = avg_score
                    elif category == ValidationCategory.CONSISTENCY:
                        report.consistency_score = avg_score
            
            # Calculate overall score
            total_score = 0.0
            total_weight = 0.0
            
            for category, weight in category_weights.items():
                if category_scores[category]:
                    category_score = np.mean(category_scores[category])
                    total_score += category_score * weight
                    total_weight += weight
            
            report.overall_score = total_score / total_weight if total_weight > 0 else 0.0
            
            # Determine overall status
            if report.overall_status != ValidationStatus.CRITICAL_FAILURE:
                if report.overall_score >= 0.8:
                    report.overall_status = ValidationStatus.PASSED
                elif report.overall_score >= self.min_overall_score:
                    report.overall_status = ValidationStatus.WARNING
                else:
                    report.overall_status = ValidationStatus.FAILED
            
            # Set confidence level
            report.confidence_level = min(report.overall_score * getattr(signal, 'confidence', 0.5), 1.0)
            
            # Generate recommendations
            report.recommendations = self._generate_recommendations(report)
            
            # Record validation time
            validation_time = (time.time() - start_time) * 1000
            report.validation_duration_ms = validation_time
            
            # Update statistics
            with self._lock:
                self._validation_times.append(validation_time)
                self._validation_stats[report.overall_status.value] += 1
                self._validation_history.append(report)
                
                # Add to signal history
                if symbol:
                    self._signal_history[symbol].append(signal)
                    # Keep only recent signals
                    self._signal_history[symbol] = self._signal_history[symbol][-50:]
            
            logger.debug(f"Signal validation completed: {report.overall_status.value} (score: {report.overall_score:.2f})")
            
            return report
            
        except Exception as e:
            logger.error(f"Error validating signal: {e}")
            report.overall_status = ValidationStatus.CRITICAL_FAILURE
            report.overall_score = 0.0
            report.risk_warnings.append(f"Validation error: {str(e)}")
            return report
    
    async def _run_validation_rule(
        self,
        rule: ValidationRule,
        signal: Any,
        context: Dict[str, Any]
    ) -> ValidationResult:
        """Run a single validation rule"""
        
        start_time = time.time()
        
        try:
            if rule.validation_function:
                result = rule.validation_function(signal, context)
                result.execution_time_ms = (time.time() - start_time) * 1000
                return result
            else:
                # Generic validation based on rule parameters
                return self._generic_validation(rule, signal, context)
                
        except Exception as e:
            logger.error(f"Error in validation rule {rule.rule_id}: {e}")
            return ValidationResult(
                rule_id=rule.rule_id,
                status=ValidationStatus.FAILED,
                message=f"Validation rule error: {str(e)}",
                score=0.0,
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def _generic_validation(
        self,
        rule: ValidationRule,
        signal: Any,
        context: Dict[str, Any]
    ) -> ValidationResult:
        """Generic validation based on rule parameters"""
        
        # This is a fallback for rules without specific validation functions
        return ValidationResult(
            rule_id=rule.rule_id,
            status=ValidationStatus.PASSED,
            message="Generic validation passed",
            score=0.8
        )
    
    def _generate_recommendations(self, report: SignalValidationReport) -> List[str]:
        """Generate recommendations based on validation results"""
        
        recommendations = []
        
        # Overall score recommendations
        if report.overall_score < 0.3:
            recommendations.append("Signal quality is very low - consider rejecting this signal")
        elif report.overall_score < 0.5:
            recommendations.append("Signal quality is below average - use with caution")
        elif report.overall_score < 0.7:
            recommendations.append("Signal quality is moderate - consider position sizing adjustments")
        
        # Category-specific recommendations
        if report.data_quality_score < 0.5:
            recommendations.append("Data quality issues detected - verify data sources")
        
        if report.signal_quality_score < 0.5:
            recommendations.append("Signal quality is poor - review signal generation methodology")
        
        if report.risk_score < 0.5:
            recommendations.append("High risk detected - consider risk mitigation measures")
        
        if report.consistency_score < 0.5:
            recommendations.append("Signal inconsistency detected - review signal timing and correlation")
        
        # Rule-specific recommendations
        for result in report.validation_results:
            if result.suggestions:
                recommendations.extend(result.suggestions)
        
        return list(set(recommendations))  # Remove duplicates
    
    async def validate_portfolio(
        self,
        signals: List[Any],
        context: Optional[Dict[str, Any]] = None
    ) -> PortfolioValidationReport:
        """Validate a portfolio of signals"""
        
        context = context or {}
        
        # Initialize portfolio report
        portfolio_report = PortfolioValidationReport(
            validation_id=f"portfolio_{int(time.time())}",
            validation_timestamp=datetime.now(),
            total_signals=len(signals)
        )
        
        try:
            # Validate individual signals
            signal_reports = []
            valid_signals = 0
            invalid_signals = 0
            
            quality_scores = []
            
            for signal in signals:
                signal_report = await self.validate_signal(signal, context)
                signal_reports.append(signal_report)
                
                if signal_report.overall_status in [ValidationStatus.PASSED, ValidationStatus.WARNING]:
                    valid_signals += 1
                else:
                    invalid_signals += 1
                
                quality_scores.append(signal_report.overall_score)
            
            portfolio_report.signal_reports = signal_reports
            portfolio_report.valid_signals = valid_signals
            portfolio_report.invalid_signals = invalid_signals
            
            # Calculate portfolio-level metrics
            if quality_scores:
                portfolio_report.average_signal_quality = np.mean(quality_scores)
            
            # Portfolio concentration analysis
            symbol_exposures = defaultdict(float)
            sector_exposures = defaultdict(float)
            total_long_exposure = 0.0
            total_short_exposure = 0.0
            
            for signal in signals:
                symbol = getattr(signal, 'symbol', '')
                position_size = getattr(signal, 'suggested_position_size', 0.0)
                sector = context.get('sectors', {}).get(symbol, 'Unknown')
                
                symbol_exposures[symbol] += abs(position_size)
                sector_exposures[sector] += abs(position_size)
                
                if position_size > 0:
                    total_long_exposure += position_size
                else:
                    total_short_exposure += abs(position_size)
            
            # Portfolio risk metrics
            portfolio_report.total_exposure = total_long_exposure + total_short_exposure
            portfolio_report.net_exposure = total_long_exposure - total_short_exposure
            
            # Concentration risk
            if symbol_exposures:
                max_symbol_exposure = max(symbol_exposures.values())
                portfolio_report.portfolio_concentration = max_symbol_exposure / max(portfolio_report.total_exposure, 0.01)
            
            portfolio_report.sector_concentration = dict(sector_exposures)
            
            # Quality distribution
            quality_distribution = defaultdict(int)
            for report in signal_reports:
                if report.overall_score >= 0.8:
                    quality_distribution['High'] += 1
                elif report.overall_score >= 0.6:
                    quality_distribution['Medium'] += 1
                else:
                    quality_distribution['Low'] += 1
            
            portfolio_report.signal_quality_distribution = dict(quality_distribution)
            
            # Portfolio-level issues and alerts
            portfolio_issues = []
            risk_alerts = []
            
            # Concentration checks
            if portfolio_report.portfolio_concentration > 0.2:  # 20% in single position
                risk_alerts.append(f"High concentration risk: {portfolio_report.portfolio_concentration:.1%} in single position")
            
            if portfolio_report.total_exposure > 2.0:  # 200% total exposure
                risk_alerts.append(f"High total exposure: {portfolio_report.total_exposure:.1%}")
            
            if abs(portfolio_report.net_exposure) > 0.5:  # 50% net exposure
                risk_alerts.append(f"High net exposure: {portfolio_report.net_exposure:.1%}")
            
            # Quality checks
            if portfolio_report.average_signal_quality < 0.5:
                portfolio_issues.append("Average signal quality below acceptable threshold")
            
            low_quality_ratio = quality_distribution.get('Low', 0) / len(signals) if signals else 0
            if low_quality_ratio > 0.3:  # 30% low quality
                portfolio_issues.append(f"High proportion of low-quality signals: {low_quality_ratio:.1%}")
            
            portfolio_report.portfolio_issues = portfolio_issues
            portfolio_report.risk_alerts = risk_alerts
            
            logger.info(f"Portfolio validation completed: {valid_signals}/{len(signals)} valid signals, "
                       f"avg quality: {portfolio_report.average_signal_quality:.2f}")
            
            return portfolio_report
            
        except Exception as e:
            logger.error(f"Error validating portfolio: {e}")
            portfolio_report.portfolio_issues.append(f"Portfolio validation error: {str(e)}")
            return portfolio_report
    
    def add_custom_rule(self, rule: ValidationRule) -> None:
        """Add a custom validation rule"""
        self.rule_engine.register_rule(rule)
        logger.info(f"Added custom validation rule: {rule.rule_id}")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a validation rule"""
        return self.rule_engine.unregister_rule(rule_id)
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        
        with self._lock:
            avg_validation_time = np.mean(self._validation_times) if self._validation_times else 0
            
            return {
                'total_validations': len(self._validation_history),
                'average_validation_time_ms': avg_validation_time,
                'validation_status_distribution': dict(self._validation_stats),
                'registered_rules': len(self.rule_engine.rules),
                'enabled_rules': len([r for r in self.rule_engine.rules.values() if r.enabled]),
                'recent_validations': len(self._validation_history)
            }
    
    def get_recent_validations(self, limit: int = 100) -> List[SignalValidationReport]:
        """Get recent validation reports"""
        
        with self._lock:
            return list(self._validation_history)[-limit:]
    
    def get_validation_rules(self) -> List[ValidationRule]:
        """Get all validation rules"""
        return list(self.rule_engine.rules.values())
    
    def update_rule_config(self, rule_id: str, **kwargs) -> bool:
        """Update rule configuration"""
        
        if rule_id not in self.rule_engine.rules:
            return False
        
        rule = self.rule_engine.rules[rule_id]
        
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        logger.info(f"Updated configuration for rule: {rule_id}")
        return True