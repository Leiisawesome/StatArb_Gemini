#!/usr/bin/env python3
"""
Advanced Trading AI Agents

Specialized AI agents for institutional trading operations including:
- Advanced Market Analysis Agent with LLM-powered insights
- Intelligent Risk Agent with predictive risk modeling
- Enhanced trading workflow orchestration

Author: Pro Quant Desk Trader
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .agent_framework import BaseAgent, AgentMessage, AgentStatus, AgentType

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime classifications"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CRISIS = "crisis"


@dataclass
class MarketInsight:
    """Market analysis insight structure"""
    insight_type: str
    confidence: float
    impact_level: str
    timeframe: str
    description: str
    supporting_data: Dict[str, Any]
    timestamp: datetime


@dataclass
class RiskAlert:
    """Risk alert structure"""
    alert_type: str
    severity: str
    description: str
    affected_positions: List[str]
    recommended_actions: List[str]
    confidence: float
    timestamp: datetime


class AdvancedMarketAnalysisAgent(BaseAgent):
    """
    Advanced market analysis agent with LLM integration
    
    Capabilities:
    - Real-time market regime detection
    - Pattern recognition and trend analysis
    - Economic event impact assessment
    - Cross-asset correlation monitoring
    - LLM-powered market commentary generation
    """
    
    def __init__(self, agent_id: str, llm_client=None, vector_db=None, knowledge_base=None):
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.MARKET_ANALYSIS,
            llm_client=llm_client
        )
        self.vector_db = vector_db
        self.knowledge_base = knowledge_base
        self.market_data_cache = {}
        self.regime_history = []
        self.pattern_cache = {}
        
    async def analyze_market_regime(self, market_data: Dict[str, Any]) -> MarketRegime:
        """Detect current market regime using advanced analytics"""
        try:
            # Calculate regime indicators
            volatility = self._calculate_volatility(market_data)
            trend_strength = self._calculate_trend_strength(market_data)
            correlation_breakdown = self._detect_correlation_breakdown(market_data)
            
            # Regime classification logic
            if volatility > 0.3:
                if correlation_breakdown:
                    regime = MarketRegime.CRISIS
                else:
                    regime = MarketRegime.HIGH_VOLATILITY
            elif abs(trend_strength) > 0.6:
                regime = MarketRegime.TRENDING_UP if trend_strength > 0 else MarketRegime.TRENDING_DOWN
            elif volatility < 0.1:
                regime = MarketRegime.LOW_VOLATILITY
            else:
                regime = MarketRegime.SIDEWAYS
            
            # Store regime history
            self.regime_history.append({
                'timestamp': datetime.now(),
                'regime': regime,
                'volatility': volatility,
                'trend_strength': trend_strength,
                'correlation_breakdown': correlation_breakdown
            })
            
            # Keep only last 100 regime observations
            if len(self.regime_history) > 100:
                self.regime_history = self.regime_history[-100:]
            
            logger.info(f"Market regime detected: {regime.value}")
            return regime
            
        except Exception as e:
            logger.error(f"Error in market regime analysis: {e}")
            return MarketRegime.SIDEWAYS
    
    async def generate_market_insights(self, market_data: Dict[str, Any]) -> List[MarketInsight]:
        """Generate comprehensive market insights using LLM analysis"""
        insights = []
        
        try:
            # Technical analysis insights
            technical_insight = await self._analyze_technical_patterns(market_data)
            if technical_insight:
                insights.append(technical_insight)
            
            # Fundamental analysis insights
            fundamental_insight = await self._analyze_fundamentals(market_data)
            if fundamental_insight:
                insights.append(fundamental_insight)
            
            # Cross-asset analysis
            cross_asset_insight = await self._analyze_cross_asset_signals(market_data)
            if cross_asset_insight:
                insights.append(cross_asset_insight)
            
            # LLM-powered market commentary
            if self.llm_client:
                llm_insight = await self._generate_llm_commentary(market_data, insights)
                if llm_insight:
                    insights.append(llm_insight)
            
            # Store insights in knowledge base
            if self.knowledge_base:
                for insight in insights:
                    await self._store_insight(insight)
            
            logger.info(f"Generated {len(insights)} market insights")
            return insights
            
        except Exception as e:
            logger.error(f"Error generating market insights: {e}")
            return []
    
    async def assess_economic_impact(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess impact of economic events on market conditions"""
        try:
            impact_assessment = {
                'high_impact_events': [],
                'medium_impact_events': [],
                'low_impact_events': [],
                'overall_sentiment': 'neutral',
                'risk_adjustment_needed': False
            }
            
            for event in events:
                impact_level = self._classify_event_impact(event)
                event['impact_level'] = impact_level
                
                if impact_level == 'high':
                    impact_assessment['high_impact_events'].append(event)
                elif impact_level == 'medium':
                    impact_assessment['medium_impact_events'].append(event)
                else:
                    impact_assessment['low_impact_events'].append(event)
            
            # Determine overall sentiment and risk adjustment
            if impact_assessment['high_impact_events']:
                impact_assessment['risk_adjustment_needed'] = True
                impact_assessment['overall_sentiment'] = 'cautious'
            
            # Generate LLM-powered event analysis
            if self.llm_client and events:
                llm_analysis = await self._analyze_events_with_llm(events)
                impact_assessment['llm_analysis'] = llm_analysis
            
            logger.info(f"Economic impact assessment completed for {len(events)} events")
            return impact_assessment
            
        except Exception as e:
            logger.error(f"Error in economic impact assessment: {e}")
            return {'error': str(e)}
    
    def _calculate_volatility(self, market_data: Dict[str, Any]) -> float:
        """Calculate market volatility from price data"""
        try:
            prices = market_data.get('prices', [])
            if len(prices) < 2:
                return 0.0
            
            returns = np.diff(np.log(prices))
            return np.std(returns) * np.sqrt(252)  # Annualized volatility
        except:
            return 0.0
    
    def _calculate_trend_strength(self, market_data: Dict[str, Any]) -> float:
        """Calculate trend strength indicator"""
        try:
            prices = market_data.get('prices', [])
            if len(prices) < 20:
                return 0.0
            
            # Simple trend strength using linear regression slope
            x = np.arange(len(prices))
            slope, _ = np.polyfit(x, prices, 1)
            normalized_slope = slope / np.mean(prices)
            
            return np.clip(normalized_slope * 100, -1.0, 1.0)
        except:
            return 0.0
    
    def _detect_correlation_breakdown(self, market_data: Dict[str, Any]) -> bool:
        """Detect correlation breakdown across asset classes"""
        try:
            correlations = market_data.get('correlations', {})
            if not correlations:
                return False
            
            # Check for significant correlation changes
            for pair, current_corr in correlations.items():
                historical_corr = self.market_data_cache.get(f"corr_{pair}", current_corr)
                if abs(current_corr - historical_corr) > 0.3:
                    return True
            
            return False
        except:
            return False
    
    async def _analyze_technical_patterns(self, market_data: Dict[str, Any]) -> Optional[MarketInsight]:
        """Analyze technical patterns in market data"""
        try:
            # Simplified technical pattern analysis
            prices = market_data.get('prices', [])
            if len(prices) < 50:
                return None
            
            # Detect simple patterns
            recent_high = max(prices[-20:])
            recent_low = min(prices[-20:])
            current_price = prices[-1]
            
            if current_price > recent_high * 0.98:
                pattern = "breakout_high"
                confidence = 0.7
            elif current_price < recent_low * 1.02:
                pattern = "breakdown_low"
                confidence = 0.7
            else:
                pattern = "consolidation"
                confidence = 0.5
            
            return MarketInsight(
                insight_type="technical_pattern",
                confidence=confidence,
                impact_level="medium",
                timeframe="short_term",
                description=f"Technical pattern detected: {pattern}",
                supporting_data={"pattern": pattern, "current_price": current_price},
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error in technical analysis: {e}")
            return None
    
    async def _analyze_fundamentals(self, market_data: Dict[str, Any]) -> Optional[MarketInsight]:
        """Analyze fundamental market conditions"""
        try:
            fundamentals = market_data.get('fundamentals', {})
            if not fundamentals:
                return None
            
            # Simplified fundamental analysis
            pe_ratio = fundamentals.get('pe_ratio', 15)
            earnings_growth = fundamentals.get('earnings_growth', 0)
            
            if pe_ratio > 25 and earnings_growth < 0.05:
                assessment = "overvalued"
                confidence = 0.8
            elif pe_ratio < 12 and earnings_growth > 0.15:
                assessment = "undervalued"
                confidence = 0.8
            else:
                assessment = "fairly_valued"
                confidence = 0.6
            
            return MarketInsight(
                insight_type="fundamental_analysis",
                confidence=confidence,
                impact_level="high",
                timeframe="long_term",
                description=f"Fundamental assessment: {assessment}",
                supporting_data={"pe_ratio": pe_ratio, "earnings_growth": earnings_growth},
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error in fundamental analysis: {e}")
            return None
    
    async def _analyze_cross_asset_signals(self, market_data: Dict[str, Any]) -> Optional[MarketInsight]:
        """Analyze cross-asset signals and correlations"""
        try:
            cross_asset = market_data.get('cross_asset', {})
            if not cross_asset:
                return None
            
            # Analyze key cross-asset relationships
            vix_level = cross_asset.get('vix', 20)
            yield_curve = cross_asset.get('yield_curve_slope', 1.0)
            dollar_strength = cross_asset.get('dxy', 100)
            
            signal_strength = 0
            signals = []
            
            if vix_level > 30:
                signals.append("high_fear")
                signal_strength += 0.3
            
            if yield_curve < 0:
                signals.append("inverted_curve")
                signal_strength += 0.4
            
            if dollar_strength > 105:
                signals.append("strong_dollar")
                signal_strength += 0.2
            
            if signals:
                return MarketInsight(
                    insight_type="cross_asset_analysis",
                    confidence=min(signal_strength, 1.0),
                    impact_level="high" if signal_strength > 0.7 else "medium",
                    timeframe="medium_term",
                    description=f"Cross-asset signals: {', '.join(signals)}",
                    supporting_data={"signals": signals, "vix": vix_level, "yield_curve": yield_curve},
                    timestamp=datetime.now()
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in cross-asset analysis: {e}")
            return None
    
    async def _generate_llm_commentary(self, market_data: Dict[str, Any], insights: List[MarketInsight]) -> Optional[MarketInsight]:
        """Generate LLM-powered market commentary"""
        try:
            if not self.llm_client:
                return None
            
            # Prepare context for LLM
            context = {
                "market_data_summary": self._summarize_market_data(market_data),
                "existing_insights": [insight.description for insight in insights],
                "regime_history": self.regime_history[-5:] if self.regime_history else []
            }
            
            prompt = f"""
            As a senior quantitative analyst, provide a concise market commentary based on:
            
            Market Data: {context['market_data_summary']}
            Current Insights: {context['existing_insights']}
            Recent Regimes: {[r['regime'].value for r in context['regime_history']]}
            
            Provide a 2-3 sentence market outlook focusing on key risks and opportunities.
            """
            
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3
            )
            
            if response and response.content:
                return MarketInsight(
                    insight_type="llm_commentary",
                    confidence=0.8,
                    impact_level="high",
                    timeframe="short_term",
                    description=response.content.strip(),
                    supporting_data={"llm_model": response.model_used},
                    timestamp=datetime.now()
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating LLM commentary: {e}")
            return None
    
    def _summarize_market_data(self, market_data: Dict[str, Any]) -> str:
        """Create a summary of market data for LLM context"""
        try:
            summary_parts = []
            
            if 'prices' in market_data and market_data['prices']:
                current_price = market_data['prices'][-1]
                price_change = market_data['prices'][-1] - market_data['prices'][-2] if len(market_data['prices']) > 1 else 0
                summary_parts.append(f"Current price: {current_price:.2f}, Change: {price_change:+.2f}")
            
            if 'volume' in market_data:
                summary_parts.append(f"Volume: {market_data['volume']}")
            
            if 'volatility' in market_data:
                summary_parts.append(f"Volatility: {market_data['volatility']:.2%}")
            
            return "; ".join(summary_parts) if summary_parts else "Limited market data available"
            
        except:
            return "Market data summary unavailable"
    
    def _classify_event_impact(self, event: Dict[str, Any]) -> str:
        """Classify the market impact level of an economic event"""
        try:
            event_type = event.get('type', '').lower()
            importance = event.get('importance', 'medium').lower()
            
            # High impact events
            high_impact_types = ['fomc', 'nfp', 'cpi', 'gdp', 'central_bank']
            if any(term in event_type for term in high_impact_types) or importance == 'high':
                return 'high'
            
            # Medium impact events
            medium_impact_types = ['pmi', 'retail_sales', 'jobless_claims']
            if any(term in event_type for term in medium_impact_types) or importance == 'medium':
                return 'medium'
            
            return 'low'
            
        except:
            return 'low'
    
    async def _analyze_events_with_llm(self, events: List[Dict[str, Any]]) -> str:
        """Analyze economic events using LLM"""
        try:
            if not self.llm_client:
                return "LLM analysis unavailable"
            
            events_summary = []
            for event in events[:5]:  # Limit to 5 most important events
                events_summary.append(f"{event.get('type', 'Unknown')}: {event.get('description', 'No description')}")
            
            prompt = f"""
            Analyze the market impact of these upcoming economic events:
            {chr(10).join(events_summary)}
            
            Provide a brief assessment of potential market reactions and trading considerations.
            """
            
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=150,
                temperature=0.3
            )
            
            return response.content if response else "LLM analysis failed"
            
        except Exception as e:
            logger.error(f"Error in LLM event analysis: {e}")
            return f"Error in analysis: {str(e)}"
    
    async def _store_insight(self, insight: MarketInsight):
        """Store insight in knowledge base"""
        try:
            if self.knowledge_base:
                await self.knowledge_base.add_market_knowledge(
                    content=insight.description,
                    insight_type=insight.insight_type,
                    confidence=insight.confidence,
                    metadata={
                        'impact_level': insight.impact_level,
                        'timeframe': insight.timeframe,
                        'supporting_data': insight.supporting_data,
                        'timestamp': insight.timestamp.isoformat()
                    }
                )
        except Exception as e:
            logger.error(f"Error storing insight: {e}")


class IntelligentRiskAgent(BaseAgent):
    """
    Intelligent risk management agent with predictive capabilities
    
    Features:
    - Predictive risk modeling using ML
    - Automated risk mitigation strategies
    - Dynamic position sizing and limits
    - Real-time anomaly detection
    - LLM-powered risk commentary
    """
    
    def __init__(self, agent_id: str, llm_client=None, knowledge_base=None):
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.RISK_MANAGEMENT,
            llm_client=llm_client
        )
        self.knowledge_base = knowledge_base
        self.risk_models = {}
        self.alert_history = []
        self.risk_limits = {
            'max_portfolio_var': 0.02,  # 2% daily VaR
            'max_position_size': 0.1,   # 10% of portfolio
            'max_correlation': 0.8,     # Maximum correlation between positions
            'max_drawdown': 0.05        # 5% maximum drawdown
        }
    
    async def assess_portfolio_risk(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive portfolio risk assessment"""
        try:
            risk_assessment = {
                'overall_risk_score': 0.0,
                'var_estimate': 0.0,
                'stress_test_results': {},
                'risk_alerts': [],
                'recommended_actions': [],
                'confidence': 0.0
            }
            
            # Calculate VaR
            var_estimate = self._calculate_portfolio_var(portfolio_data)
            risk_assessment['var_estimate'] = var_estimate
            
            # Perform stress tests
            stress_results = await self._perform_stress_tests(portfolio_data)
            risk_assessment['stress_test_results'] = stress_results
            
            # Check for risk limit breaches
            alerts = self._check_risk_limits(portfolio_data, var_estimate)
            risk_assessment['risk_alerts'] = alerts
            
            # Generate risk recommendations
            recommendations = await self._generate_risk_recommendations(portfolio_data, alerts)
            risk_assessment['recommended_actions'] = recommendations
            
            # Calculate overall risk score
            risk_score = self._calculate_risk_score(var_estimate, stress_results, alerts)
            risk_assessment['overall_risk_score'] = risk_score
            risk_assessment['confidence'] = 0.85
            
            # Generate LLM risk commentary
            if self.llm_client:
                commentary = await self._generate_risk_commentary(risk_assessment)
                risk_assessment['llm_commentary'] = commentary
            
            logger.info(f"Portfolio risk assessment completed. Risk score: {risk_score:.2f}")
            return risk_assessment
            
        except Exception as e:
            logger.error(f"Error in portfolio risk assessment: {e}")
            return {'error': str(e)}
    
    async def detect_anomalies(self, market_data: Dict[str, Any], portfolio_data: Dict[str, Any]) -> List[RiskAlert]:
        """Detect risk anomalies in real-time"""
        alerts = []
        
        try:
            # Price anomaly detection
            price_alerts = self._detect_price_anomalies(market_data)
            alerts.extend(price_alerts)
            
            # Volume anomaly detection
            volume_alerts = self._detect_volume_anomalies(market_data)
            alerts.extend(volume_alerts)
            
            # Correlation breakdown detection
            correlation_alerts = self._detect_correlation_anomalies(market_data)
            alerts.extend(correlation_alerts)
            
            # Portfolio concentration alerts
            concentration_alerts = self._detect_concentration_risks(portfolio_data)
            alerts.extend(concentration_alerts)
            
            # Store alerts in history
            self.alert_history.extend(alerts)
            if len(self.alert_history) > 1000:
                self.alert_history = self.alert_history[-1000:]
            
            logger.info(f"Anomaly detection completed. Found {len(alerts)} alerts")
            return alerts
            
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
            return []
    
    async def optimize_position_sizes(self, portfolio_data: Dict[str, Any], risk_target: float = 0.02) -> Dict[str, float]:
        """Optimize position sizes based on risk targets"""
        try:
            positions = portfolio_data.get('positions', {})
            if not positions:
                return {}
            
            # Calculate current risk contribution of each position
            risk_contributions = self._calculate_risk_contributions(portfolio_data)
            
            # Optimize using simplified Kelly criterion
            optimized_sizes = {}
            total_weight = 0
            
            for symbol, position_data in positions.items():
                expected_return = position_data.get('expected_return', 0.0)
                volatility = position_data.get('volatility', 0.2)
                
                if volatility > 0:
                    # Simplified Kelly sizing with risk adjustment
                    kelly_size = (expected_return / (volatility ** 2)) * risk_target
                    kelly_size = max(0, min(kelly_size, self.risk_limits['max_position_size']))
                    optimized_sizes[symbol] = kelly_size
                    total_weight += kelly_size
            
            # Normalize weights if they exceed 100%
            if total_weight > 1.0:
                for symbol in optimized_sizes:
                    optimized_sizes[symbol] /= total_weight
            
            logger.info(f"Position sizes optimized for {len(optimized_sizes)} positions")
            return optimized_sizes
            
        except Exception as e:
            logger.error(f"Error optimizing position sizes: {e}")
            return {}
    
    def _calculate_portfolio_var(self, portfolio_data: Dict[str, Any], confidence_level: float = 0.95) -> float:
        """Calculate portfolio Value at Risk"""
        try:
            positions = portfolio_data.get('positions', {})
            if not positions:
                return 0.0
            
            # Simplified VaR calculation using individual position volatilities
            portfolio_var = 0.0
            
            for symbol, position_data in positions.items():
                weight = position_data.get('weight', 0.0)
                volatility = position_data.get('volatility', 0.2)
                value = position_data.get('value', 0.0)
                
                # Individual position VaR (assuming normal distribution)
                z_score = 1.645 if confidence_level == 0.95 else 2.326  # 95% or 99%
                position_var = value * weight * volatility * z_score
                portfolio_var += position_var ** 2  # Simplified - assumes zero correlation
            
            return np.sqrt(portfolio_var)
            
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return 0.0
    
    async def _perform_stress_tests(self, portfolio_data: Dict[str, Any]) -> Dict[str, float]:
        """Perform various stress test scenarios"""
        try:
            stress_results = {}
            
            # Define stress scenarios
            scenarios = {
                'market_crash': {'equity_shock': -0.20, 'vol_spike': 2.0},
                'interest_rate_shock': {'rate_shock': 0.02, 'duration_impact': -0.15},
                'correlation_breakdown': {'correlation_shock': 0.9},
                'liquidity_crisis': {'liquidity_shock': 0.5}
            }
            
            positions = portfolio_data.get('positions', {})
            current_value = sum(pos.get('value', 0) for pos in positions.values())
            
            for scenario_name, scenario_params in scenarios.items():
                scenario_loss = 0.0
                
                for symbol, position_data in positions.items():
                    value = position_data.get('value', 0.0)
                    
                    # Apply scenario-specific shocks
                    if 'equity_shock' in scenario_params:
                        scenario_loss += value * scenario_params['equity_shock']
                    
                    if 'rate_shock' in scenario_params and 'duration' in position_data:
                        duration = position_data.get('duration', 0.0)
                        rate_impact = duration * scenario_params['rate_shock']
                        scenario_loss += value * rate_impact
                
                stress_results[scenario_name] = scenario_loss / current_value if current_value > 0 else 0.0
            
            return stress_results
            
        except Exception as e:
            logger.error(f"Error in stress testing: {e}")
            return {}
    
    def _check_risk_limits(self, portfolio_data: Dict[str, Any], var_estimate: float) -> List[RiskAlert]:
        """Check for risk limit breaches"""
        alerts = []
        
        try:
            # VaR limit check
            if var_estimate > self.risk_limits['max_portfolio_var']:
                alerts.append(RiskAlert(
                    alert_type="var_breach",
                    severity="high",
                    description=f"Portfolio VaR ({var_estimate:.2%}) exceeds limit ({self.risk_limits['max_portfolio_var']:.2%})",
                    affected_positions=list(portfolio_data.get('positions', {}).keys()),
                    recommended_actions=["Reduce position sizes", "Increase hedging"],
                    confidence=0.9,
                    timestamp=datetime.now()
                ))
            
            # Position size limit checks
            positions = portfolio_data.get('positions', {})
            for symbol, position_data in positions.items():
                weight = position_data.get('weight', 0.0)
                if weight > self.risk_limits['max_position_size']:
                    alerts.append(RiskAlert(
                        alert_type="position_size_breach",
                        severity="medium",
                        description=f"Position {symbol} size ({weight:.2%}) exceeds limit ({self.risk_limits['max_position_size']:.2%})",
                        affected_positions=[symbol],
                        recommended_actions=[f"Reduce {symbol} position size"],
                        confidence=0.95,
                        timestamp=datetime.now()
                    ))
            
            # Drawdown check
            current_drawdown = portfolio_data.get('current_drawdown', 0.0)
            if current_drawdown > self.risk_limits['max_drawdown']:
                alerts.append(RiskAlert(
                    alert_type="drawdown_breach",
                    severity="high",
                    description=f"Current drawdown ({current_drawdown:.2%}) exceeds limit ({self.risk_limits['max_drawdown']:.2%})",
                    affected_positions=list(positions.keys()),
                    recommended_actions=["Reduce overall exposure", "Review strategy parameters"],
                    confidence=0.85,
                    timestamp=datetime.now()
                ))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return []
    
    async def _generate_risk_recommendations(self, portfolio_data: Dict[str, Any], alerts: List[RiskAlert]) -> List[str]:
        """Generate risk management recommendations"""
        try:
            recommendations = []
            
            # General recommendations based on alerts
            if any(alert.severity == "high" for alert in alerts):
                recommendations.append("Immediate risk reduction required - consider closing high-risk positions")
            
            if len(alerts) > 3:
                recommendations.append("Multiple risk issues detected - comprehensive portfolio review recommended")
            
            # Specific recommendations based on portfolio metrics
            positions = portfolio_data.get('positions', {})
            total_positions = len(positions)
            
            if total_positions > 20:
                recommendations.append("High number of positions detected - consider portfolio concentration")
            
            # Correlation-based recommendations
            avg_correlation = portfolio_data.get('avg_correlation', 0.0)
            if avg_correlation > self.risk_limits['max_correlation']:
                recommendations.append("High portfolio correlation detected - increase diversification")
            
            # LLM-powered recommendations
            if self.llm_client and alerts:
                llm_recommendations = await self._generate_llm_recommendations(portfolio_data, alerts)
                if llm_recommendations:
                    recommendations.extend(llm_recommendations)
            
            return recommendations[:10]  # Limit to top 10 recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return ["Error generating recommendations - manual review required"]
    
    def _calculate_risk_score(self, var_estimate: float, stress_results: Dict[str, float], alerts: List[RiskAlert]) -> float:
        """Calculate overall portfolio risk score (0-10 scale)"""
        try:
            risk_score = 0.0
            
            # VaR contribution (0-4 points)
            var_ratio = var_estimate / self.risk_limits['max_portfolio_var']
            risk_score += min(4.0, var_ratio * 4.0)
            
            # Stress test contribution (0-3 points)
            if stress_results:
                worst_stress = min(stress_results.values())
                stress_score = abs(worst_stress) * 15  # Scale stress losses
                risk_score += min(3.0, stress_score)
            
            # Alert contribution (0-3 points)
            high_severity_alerts = sum(1 for alert in alerts if alert.severity == "high")
            medium_severity_alerts = sum(1 for alert in alerts if alert.severity == "medium")
            alert_score = high_severity_alerts * 1.5 + medium_severity_alerts * 0.5
            risk_score += min(3.0, alert_score)
            
            return min(10.0, risk_score)
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 5.0  # Default moderate risk score
    
    def _calculate_risk_contributions(self, portfolio_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate risk contribution of each position"""
        try:
            positions = portfolio_data.get('positions', {})
            risk_contributions = {}
            
            total_portfolio_var = 0.0
            
            for symbol, position_data in positions.items():
                weight = position_data.get('weight', 0.0)
                volatility = position_data.get('volatility', 0.2)
                value = position_data.get('value', 0.0)
                
                # Simplified risk contribution calculation
                position_var = (weight * volatility * value) ** 2
                risk_contributions[symbol] = position_var
                total_portfolio_var += position_var
            
            # Normalize to percentages
            if total_portfolio_var > 0:
                for symbol in risk_contributions:
                    risk_contributions[symbol] = risk_contributions[symbol] / total_portfolio_var
            
            return risk_contributions
            
        except Exception as e:
            logger.error(f"Error calculating risk contributions: {e}")
            return {}
    
    def _detect_price_anomalies(self, market_data: Dict[str, Any]) -> List[RiskAlert]:
        """Detect price-based anomalies"""
        alerts = []
        
        try:
            for symbol, data in market_data.items():
                prices = data.get('prices', [])
                if len(prices) < 2:
                    continue
                
                # Large price movement detection
                price_change = (prices[-1] - prices[-2]) / prices[-2] if prices[-2] != 0 else 0
                if abs(price_change) > 0.05:  # 5% threshold
                    severity = "high" if abs(price_change) > 0.1 else "medium"
                    alerts.append(RiskAlert(
                        alert_type="price_anomaly",
                        severity=severity,
                        description=f"{symbol} price moved {price_change:.2%} - potential anomaly",
                        affected_positions=[symbol],
                        recommended_actions=["Review position", "Check for news/events"],
                        confidence=0.7,
                        timestamp=datetime.now()
                    ))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error detecting price anomalies: {e}")
            return []
    
    def _detect_volume_anomalies(self, market_data: Dict[str, Any]) -> List[RiskAlert]:
        """Detect volume-based anomalies"""
        alerts = []
        
        try:
            for symbol, data in market_data.items():
                volumes = data.get('volumes', [])
                if len(volumes) < 10:
                    continue
                
                # Volume spike detection
                current_volume = volumes[-1]
                avg_volume = np.mean(volumes[-10:-1])
                
                if current_volume > avg_volume * 3:  # 3x average volume
                    alerts.append(RiskAlert(
                        alert_type="volume_anomaly",
                        severity="medium",
                        description=f"{symbol} volume spike detected - {current_volume/avg_volume:.1f}x average",
                        affected_positions=[symbol],
                        recommended_actions=["Monitor for liquidity issues", "Check market news"],
                        confidence=0.8,
                        timestamp=datetime.now()
                    ))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error detecting volume anomalies: {e}")
            return []
    
    def _detect_correlation_anomalies(self, market_data: Dict[str, Any]) -> List[RiskAlert]:
        """Detect correlation breakdown anomalies"""
        alerts = []
        
        try:
            correlations = market_data.get('correlations', {})
            for pair, current_corr in correlations.items():
                # Historical correlation comparison (simplified)
                expected_corr = 0.5  # Placeholder for historical correlation
                
                if abs(current_corr - expected_corr) > 0.3:
                    alerts.append(RiskAlert(
                        alert_type="correlation_anomaly",
                        severity="medium",
                        description=f"Correlation breakdown detected for {pair}: {current_corr:.2f} vs expected {expected_corr:.2f}",
                        affected_positions=pair.split('_'),
                        recommended_actions=["Review hedging strategies", "Reassess diversification"],
                        confidence=0.6,
                        timestamp=datetime.now()
                    ))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error detecting correlation anomalies: {e}")
            return []
    
    def _detect_concentration_risks(self, portfolio_data: Dict[str, Any]) -> List[RiskAlert]:
        """Detect portfolio concentration risks"""
        alerts = []
        
        try:
            positions = portfolio_data.get('positions', {})
            if not positions:
                return alerts
            
            # Check for sector concentration
            sectors = {}
            for symbol, position_data in positions.items():
                sector = position_data.get('sector', 'Unknown')
                weight = position_data.get('weight', 0.0)
                sectors[sector] = sectors.get(sector, 0.0) + weight
            
            for sector, total_weight in sectors.items():
                if total_weight > 0.3:  # 30% sector concentration threshold
                    alerts.append(RiskAlert(
                        alert_type="concentration_risk",
                        severity="medium",
                        description=f"High concentration in {sector} sector: {total_weight:.1%}",
                        affected_positions=[pos for pos, data in positions.items() if data.get('sector') == sector],
                        recommended_actions=["Reduce sector concentration", "Increase diversification"],
                        confidence=0.9,
                        timestamp=datetime.now()
                    ))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error detecting concentration risks: {e}")
            return []
    
    async def _generate_risk_commentary(self, risk_assessment: Dict[str, Any]) -> str:
        """Generate LLM-powered risk commentary"""
        try:
            if not self.llm_client:
                return "LLM risk commentary unavailable"
            
            prompt = f"""
            As a senior risk manager, provide a brief risk assessment summary:
            
            Overall Risk Score: {risk_assessment.get('overall_risk_score', 0):.1f}/10
            Portfolio VaR: {risk_assessment.get('var_estimate', 0):.2%}
            Active Alerts: {len(risk_assessment.get('risk_alerts', []))}
            Key Recommendations: {'; '.join(risk_assessment.get('recommended_actions', [])[:3])}
            
            Provide a 2-3 sentence risk outlook and priority actions.
            """
            
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=150,
                temperature=0.2
            )
            
            return response.content if response else "LLM risk commentary failed"
            
        except Exception as e:
            logger.error(f"Error generating risk commentary: {e}")
            return f"Error in risk commentary: {str(e)}"
    
    async def _generate_llm_recommendations(self, portfolio_data: Dict[str, Any], alerts: List[RiskAlert]) -> List[str]:
        """Generate LLM-powered risk recommendations"""
        try:
            if not self.llm_client or not alerts:
                return []
            
            alert_summary = []
            for alert in alerts[:5]:  # Limit to 5 most critical alerts
                alert_summary.append(f"{alert.alert_type}: {alert.description}")
            
            prompt = f"""
            Based on these risk alerts, provide 3 specific actionable recommendations:
            
            Risk Alerts:
            {chr(10).join(alert_summary)}
            
            Focus on immediate, practical risk management actions.
            """
            
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=200,
                temperature=0.3
            )
            
            if response and response.content:
                # Parse recommendations (assume numbered list)
                recommendations = []
                for line in response.content.split('\n'):
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                        # Clean up the recommendation
                        clean_rec = line.lstrip('0123456789.-• ').strip()
                        if clean_rec:
                            recommendations.append(clean_rec)
                
                return recommendations[:5]  # Limit to 5 recommendations
            
            return []
            
        except Exception as e:
            logger.error(f"Error generating LLM recommendations: {e}")
            return [] 