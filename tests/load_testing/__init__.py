"""
Load Testing Framework
======================

Production-level load testing for StatArb_Gemini trading system.

Target Performance:
- 10,000+ orders per day
- <100ms average order latency
- 72+ hour continuous operation
- Zero memory leaks

Test Modules:
- order_generator: Realistic order generation and simulation
- performance_monitor: Real-time performance metrics and monitoring
- continuous_test: 72-hour continuous operation testing
- failover_test: Broker and database failover scenarios
- stress_test: System stress testing under extreme loads
"""

__version__ = "1.0.0"
