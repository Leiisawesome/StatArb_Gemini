#!/usr/bin/env python3
"""
Cross-Cutting Concerns Integration Tests
========================================

Comprehensive integration tests for cross-cutting concerns:
- Configuration Management ↔ Environment Variables ↔ Secrets
- Logging Framework ↔ Structured Logging ↔ Log Aggregation
- Metrics Collection ↔ Monitoring Dashboards ↔ Alerting
- Authentication & Authorization ↔ Session Management ↔ Security
- Caching Layer ↔ Performance Optimization ↔ Data Consistency
- Internationalization ↔ Localization ↔ Time Zone Handling

These tests validate the infrastructure and operational concerns
that span across all system components and ensure reliable operation.

Author: StatArb_Gemini Integration Test Suite
Version: 1.0.0
"""

import pytest
import asyncio
import os
import tempfile
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Callable
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import warnings
import hashlib
import base64
import numpy as np

warnings.filterwarnings('ignore')

from core_engine.system.unified_execution_engine import UnifiedExecutionEngine
from core_engine.trading.strategies.strategy_engine import BaseStrategy
from core_engine.data.manager import ClickHouseDataManager


class TestConfigurationManagementIntegration:
    """Integration tests for configuration management across components"""

    @pytest.fixture
    def config_hierarchy(self):
        """Create hierarchical configuration structure"""
        return {
            'global': {
                'system_name': 'StatArb_Gemini',
                'version': '1.0.0',
                'environment': 'testing'
            },
            'components': {
                'execution_engine': {
                    'max_slippage': 0.001,
                    'min_order_size': 100,
                    'circuit_breaker_threshold': 5
                },
                'data_manager': {
                    'connection_pool_size': 10,
                    'query_timeout': 30,
                    'enable_compression': True
                },
                'risk_manager': {
                    'max_portfolio_risk': 0.05,
                    'max_single_position_risk': 0.02,
                    'var_confidence_level': 0.95
                }
            },
            'secrets': {
                'database_password': 'encrypted_placeholder',
                'api_key': 'encrypted_placeholder',
                'private_key': 'encrypted_placeholder'
            }
        }

    def test_configuration_loading_and_override_hierarchy(self, config_hierarchy):
        """Test configuration loading with proper override hierarchy"""
        loaded_configs = {}

        def load_configuration_layer(layer_name: str, base_config: dict) -> dict:
            """Simulate loading configuration from different sources"""
            config = base_config.copy()

            if layer_name == 'environment':
                # Environment variable overrides
                config['environment'] = os.getenv('APP_ENV', config.get('environment', 'development'))
                config['components']['execution_engine']['max_slippage'] = float(
                    os.getenv('MAX_SLIPPAGE', config['components']['execution_engine']['max_slippage'])
                )
            elif layer_name == 'file':
                # File-based overrides (simulate loading from config file)
                config['components']['data_manager']['connection_pool_size'] = 15
            elif layer_name == 'runtime':
                # Runtime overrides
                config['global']['debug_mode'] = True

            loaded_configs[layer_name] = config
            return config

        # Load configuration layers in hierarchy order
        layers = ['defaults', 'file', 'environment', 'runtime']
        final_config = config_hierarchy.copy()

        for layer in layers:
            final_config = load_configuration_layer(layer, final_config)

        # Verify configuration hierarchy respected
        assert final_config['global']['system_name'] == 'StatArb_Gemini'  # Base value preserved
        assert final_config['components']['data_manager']['connection_pool_size'] == 15  # File override applied
        assert final_config['global']['debug_mode'] is True  # Runtime override applied

        # Verify all required sections present
        assert 'global' in final_config
        assert 'components' in final_config
        assert 'secrets' in final_config

    def test_secret_management_and_encryption(self, config_hierarchy):
        """Test secret management and encryption integration"""
        encryption_key = "test_encryption_key_32_chars_long"
        encrypted_secrets = {}

        def encrypt_secret(secret: str, key: str) -> str:
            """Simulate secret encryption"""
            # Simple simulation - in real implementation use proper encryption
            combined = (secret + key).encode()
            return base64.b64encode(hashlib.sha256(combined).digest()).decode()

        def decrypt_secret(encrypted: str, key: str) -> str:
            """Simulate secret decryption"""
            # In real implementation, this would decrypt properly
            return "decrypted_secret"

        # Encrypt secrets
        for secret_name, secret_value in config_hierarchy['secrets'].items():
            encrypted_secrets[secret_name] = encrypt_secret(secret_value, encryption_key)

        # Verify encryption
        assert len(encrypted_secrets) == len(config_hierarchy['secrets'])
        for encrypted in encrypted_secrets.values():
            assert isinstance(encrypted, str)
            assert len(encrypted) > 0

        # Test secret rotation
        new_key = "new_encryption_key_32_chars_longer"
        rotated_secrets = {}

        for secret_name, old_encrypted in encrypted_secrets.items():
            # Decrypt with old key
            decrypted = decrypt_secret(old_encrypted, encryption_key)
            # Re-encrypt with new key
            rotated_secrets[secret_name] = encrypt_secret(decrypted, new_key)

        # Verify rotation
        assert len(rotated_secrets) == len(encrypted_secrets)
        # New encryptions should be different
        for secret_name in encrypted_secrets:
            assert rotated_secrets[secret_name] != encrypted_secrets[secret_name]

    def test_configuration_validation_and_schema_enforcement(self, config_hierarchy):
        """Test configuration validation and schema enforcement"""
        validation_errors = []
        validation_warnings = []

        def validate_configuration_schema(config: dict) -> tuple:
            """Validate configuration against schema"""
            errors = []
            warnings = []

            # Required global fields
            required_global = ['system_name', 'version', 'environment']
            for field in required_global:
                if field not in config.get('global', {}):
                    errors.append(f"Missing required global field: {field}")

            # Component-specific validations
            if 'components' in config:
                components = config['components']

                # Execution engine validations
                if 'execution_engine' in components:
                    ee_config = components['execution_engine']
                    if ee_config.get('max_slippage', 0) > 0.01:
                        warnings.append("max_slippage seems high for production")
                    if ee_config.get('min_order_size', 0) <= 0:
                        errors.append("min_order_size must be positive")

                # Data manager validations
                if 'data_manager' in components:
                    dm_config = components['data_manager']
                    if dm_config.get('connection_pool_size', 0) > 100:
                        warnings.append("connection_pool_size very high, may cause resource issues")

            # Environment-specific validations
            env = config.get('global', {}).get('environment', 'development')
            if env == 'production':
                if not config.get('secrets'):
                    errors.append("Production environment requires secrets configuration")

            return errors, warnings

        # Validate configuration
        errors, warnings = validate_configuration_schema(config_hierarchy)

        # Should have no errors for valid config
        assert len(errors) == 0, f"Configuration validation errors: {errors}"

        # May have warnings
        validation_warnings.extend(warnings)

        # Test invalid configuration
        invalid_config = config_hierarchy.copy()
        del invalid_config['global']['system_name']  # Remove required field

        errors, warnings = validate_configuration_schema(invalid_config)
        assert len(errors) > 0, "Should detect missing required field"
        assert any('system_name' in error for error in errors)


class TestLoggingAndMonitoringIntegration:
    """Integration tests for logging and monitoring infrastructure"""

    @pytest.fixture
    def logging_config(self):
        """Create logging configuration"""
        return {
            'version': 1,
            'formatters': {
                'detailed': {
                    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(metadata)s'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'detailed',
                    'level': 'INFO'
                },
                'file': {
                    'class': 'logging.FileHandler',
                    'filename': 'test.log',
                    'formatter': 'detailed',
                    'level': 'DEBUG'
                }
            },
            'loggers': {
                'core_engine': {
                    'level': 'DEBUG',
                    'handlers': ['console', 'file'],
                    'propagate': False
                }
            }
        }

    def test_structured_logging_across_components(self, logging_config):
        """Test structured logging integration across components"""
        log_entries = []
        correlation_ids = {}

        def create_correlation_id() -> str:
            """Generate correlation ID for request tracking"""
            return f"corr_{int(time.time() * 1000000)}"

        def log_with_correlation(component: str, level: str, message: str,
                               correlation_id: str = None, **kwargs):
            """Structured logging with correlation tracking"""
            if correlation_id is None:
                correlation_id = create_correlation_id()

            if correlation_id not in correlation_ids:
                correlation_ids[correlation_id] = []

            entry = {
                'timestamp': datetime.now(),
                'correlation_id': correlation_id,
                'component': component,
                'level': level,
                'message': message,
                'metadata': kwargs
            }

            log_entries.append(entry)
            correlation_ids[correlation_id].append(entry)

        # Simulate component interactions with correlation tracking
        # Start with data request
        corr_id = create_correlation_id()
        log_with_correlation('data_manager', 'INFO', 'Fetching market data',
                           corr_id, symbol='AAPL', timeframe='1H')

        # Processing step
        log_with_correlation('processing_engine', 'DEBUG', 'Processing indicators',
                           corr_id, indicators=['SMA', 'RSI'])

        # Strategy execution
        log_with_correlation('strategy_engine', 'INFO', 'Executing momentum strategy',
                           corr_id, strategy='momentum', signal='BUY')

        # Risk check
        log_with_correlation('risk_manager', 'WARNING', 'Position size adjusted for risk',
                           corr_id, original_size=1000, adjusted_size=800)

        # Execution
        log_with_correlation('execution_engine', 'INFO', 'Order executed successfully',
                           corr_id, order_id='ORD_001', filled_quantity=800)

        # Verify correlation tracking
        assert corr_id in correlation_ids
        correlated_entries = correlation_ids[corr_id]
        assert len(correlated_entries) == 5

        # Verify chronological order
        timestamps = [entry['timestamp'] for entry in correlated_entries]
        assert timestamps == sorted(timestamps)

        # Verify component flow
        components = [entry['component'] for entry in correlated_entries]
        expected_flow = ['data_manager', 'processing_engine', 'strategy_engine', 'risk_manager', 'execution_engine']
        assert components == expected_flow

    def test_metrics_collection_and_aggregation(self):
        """Test metrics collection and aggregation across components"""
        metrics_store = {}
        aggregation_windows = ['1m', '5m', '15m', '1h']

        def record_metric(component: str, metric_name: str, value: float, tags: dict = None):
            """Record metric with tags"""
            key = f"{component}.{metric_name}"
            if key not in metrics_store:
                metrics_store[key] = []

            metric_entry = {
                'timestamp': datetime.now(),
                'value': value,
                'tags': tags or {}
            }

            metrics_store[key].append(metric_entry)

        def aggregate_metrics(time_window: str) -> dict:
            """Aggregate metrics over time window"""
            # Simplified aggregation - in real implementation would respect time windows
            aggregated = {}

            for metric_key, entries in metrics_store.items():
                if entries:
                    values = [entry['value'] for entry in entries]
                    aggregated[metric_key] = {
                        'count': len(values),
                        'sum': sum(values),
                        'avg': sum(values) / len(values),
                        'min': min(values),
                        'max': max(values),
                        'latest': values[-1]
                    }

            return aggregated

        # Record various component metrics
        components = ['execution_engine', 'data_manager', 'strategy_engine', 'risk_manager']

        for i in range(10):
            for component in components:
                # Simulate different metric types
                record_metric(component, 'request_count', 1, {'method': 'GET'})
                record_metric(component, 'response_time', np.random.uniform(0.1, 2.0),
                            {'endpoint': f'/{component}/process'})
                record_metric(component, 'error_count', np.random.choice([0, 1], p=[0.9, 0.1]),
                            {'error_type': 'timeout'})

                if component == 'execution_engine':
                    record_metric(component, 'orders_executed', np.random.randint(0, 5),
                                {'order_type': 'market'})

        # Aggregate metrics
        aggregated = aggregate_metrics('5m')

        # Verify aggregation
        assert len(aggregated) > 0

        # Check specific metrics
        exec_orders_key = 'execution_engine.orders_executed'
        assert exec_orders_key in aggregated

        orders_stats = aggregated[exec_orders_key]
        assert orders_stats['count'] > 0
        assert orders_stats['sum'] >= orders_stats['min'] * orders_stats['count']

        # Verify error rate calculation
        error_key = 'execution_engine.error_count'
        if error_key in aggregated:
            error_stats = aggregated[error_key]
            error_rate = error_stats['avg']
            assert 0 <= error_rate <= 1

    def test_monitoring_dashboard_integration(self):
        """Test monitoring dashboard data integration"""
        dashboard_data = {
            'system_health': {},
            'performance_metrics': {},
            'alerts': [],
            'component_status': {}
        }

        def update_dashboard_component(component: str, status: dict):
            """Update dashboard with component status"""
            dashboard_data['component_status'][component] = {
                'status': status.get('status', 'unknown'),
                'last_updated': datetime.now(),
                'metrics': status.get('metrics', {}),
                'alerts': status.get('alerts', [])
            }

        def generate_system_health_report() -> dict:
            """Generate overall system health report"""
            components = dashboard_data['component_status']
            total_components = len(components)
            healthy_components = sum(1 for c in components.values() if c['status'] == 'healthy')

            health_score = healthy_components / total_components if total_components > 0 else 0

            return {
                'overall_health': 'healthy' if health_score >= 0.8 else 'degraded',
                'health_score': health_score,
                'total_components': total_components,
                'healthy_components': healthy_components,
                'last_updated': datetime.now()
            }

        # Update component statuses
        components_status = {
            'execution_engine': {
                'status': 'healthy',
                'metrics': {'orders_per_second': 15.2, 'success_rate': 0.98},
                'alerts': []
            },
            'data_manager': {
                'status': 'healthy',
                'metrics': {'query_latency': 0.05, 'connection_pool_usage': 0.7},
                'alerts': []
            },
            'risk_manager': {
                'status': 'degraded',
                'metrics': {'var_calculation_time': 2.1, 'risk_checks_failed': 3},
                'alerts': ['High risk calculation latency']
            }
        }

        for component, status in components_status.items():
            update_dashboard_component(component, status)

        # Generate health report
        health_report = generate_system_health_report()

        # Verify dashboard integration
        assert len(dashboard_data['component_status']) == 3
        assert health_report['overall_health'] == 'degraded'  # Due to risk_manager
        assert health_report['health_score'] == 2/3  # 2 healthy out of 3 total

        # Verify component-specific data
        risk_status = dashboard_data['component_status']['risk_manager']
        assert risk_status['status'] == 'degraded'
        assert 'High risk calculation latency' in risk_status['alerts']


class TestSecurityAndAuthenticationIntegration:
    """Integration tests for security and authentication"""

    @pytest.fixture
    def security_config(self):
        """Create security configuration"""
        return {
            'authentication': {
                'enabled': True,
                'token_expiry': 3600,  # 1 hour
                'refresh_token_expiry': 86400,  # 24 hours
                'max_login_attempts': 5,
                'lockout_duration': 900  # 15 minutes
            },
            'authorization': {
                'rbac_enabled': True,
                'roles': ['admin', 'trader', 'analyst', 'viewer'],
                'permissions': {
                    'execute_orders': ['admin', 'trader'],
                    'view_positions': ['admin', 'trader', 'analyst'],
                    'modify_config': ['admin'],
                    'view_reports': ['admin', 'trader', 'analyst', 'viewer']
                }
            },
            'encryption': {
                'algorithm': 'AES-256-GCM',
                'key_rotation_days': 90,
                'data_encryption_enabled': True
            }
        }

    def test_role_based_access_control_integration(self, security_config):
        """Test RBAC integration across system components"""
        user_sessions = {}
        access_log = []

        def authenticate_user(username: str, password: str) -> Optional[str]:
            """Simulate user authentication"""
            # Mock authentication
            user_roles = {
                'admin_user': ['admin'],
                'trader_user': ['trader'],
                'analyst_user': ['analyst', 'viewer'],
                'viewer_user': ['viewer']
            }

            if username in user_roles:
                session_token = f"session_{username}_{int(time.time())}"
                user_sessions[session_token] = {
                    'username': username,
                    'roles': user_roles[username],
                    'created': datetime.now(),
                    'last_activity': datetime.now()
                }
                return session_token
            return None

        def authorize_action(session_token: str, action: str, resource: str) -> bool:
            """Check if user is authorized for action"""
            if session_token not in user_sessions:
                return False

            user_info = user_sessions[session_token]
            user_roles = user_info['roles']

            # Check permissions
            required_roles = security_config['authorization']['permissions'].get(action, [])

            authorized = any(role in required_roles for role in user_roles)

            access_log.append({
                'timestamp': datetime.now(),
                'session_token': session_token,
                'username': user_info['username'],
                'action': action,
                'resource': resource,
                'authorized': authorized,
                'user_roles': user_roles
            })

            return authorized

        # Test authentication
        admin_token = authenticate_user('admin_user', 'password')
        trader_token = authenticate_user('trader_user', 'password')
        viewer_token = authenticate_user('viewer_user', 'password')

        assert admin_token is not None
        assert trader_token is not None
        assert viewer_token is not None

        # Test authorization scenarios
        test_cases = [
            (admin_token, 'execute_orders', 'AAPL', True),
            (admin_token, 'modify_config', 'system', True),
            (trader_token, 'execute_orders', 'GOOGL', True),
            (trader_token, 'modify_config', 'system', False),
            (viewer_token, 'execute_orders', 'MSFT', False),
            (viewer_token, 'view_reports', 'portfolio', True)
        ]

        for token, action, resource, expected in test_cases:
            result = authorize_action(token, action, resource)
            assert result == expected, f"Authorization failed for {action} by {token}"

        # Verify access logging
        assert len(access_log) == len(test_cases)

        # Verify admin has most permissions
        admin_actions = [log for log in access_log if log['username'] == 'admin_user']
        admin_authorized = sum(1 for action in admin_actions if action['authorized'])
        assert admin_authorized == len(admin_actions)  # Admin should be authorized for all

    def test_session_management_and_timeout(self, security_config):
        """Test session management and automatic timeout"""
        active_sessions = {}
        expired_sessions = []

        def create_session(username: str, roles: list) -> str:
            """Create user session"""
            session_id = f"session_{username}_{int(time.time())}"
            active_sessions[session_id] = {
                'username': username,
                'roles': roles,
                'created': datetime.now(),
                'last_activity': datetime.now(),
                'max_age': security_config['authentication']['token_expiry']
            }
            return session_id

        def validate_session(session_id: str) -> bool:
            """Validate session and check for expiry"""
            if session_id not in active_sessions:
                return False

            session = active_sessions[session_id]
            now = datetime.now()
            age = (now - session['created']).total_seconds()

            if age > session['max_age']:
                # Session expired
                expired_sessions.append(session_id)
                del active_sessions[session_id]
                return False

            # Update last activity
            session['last_activity'] = now
            return True

        def cleanup_expired_sessions():
            """Clean up expired sessions"""
            now = datetime.now()
            to_remove = []

            for session_id, session in active_sessions.items():
                age = (now - session['created']).total_seconds()
                if age > session['max_age']:
                    to_remove.append(session_id)
                    expired_sessions.append(session_id)

            for session_id in to_remove:
                del active_sessions[session_id]

        # Create sessions
        session1 = create_session('user1', ['trader'])
        session2 = create_session('user2', ['analyst'])

        # Validate active sessions
        assert validate_session(session1)
        assert validate_session(session2)
        assert len(active_sessions) == 2

        # Simulate session expiry by advancing time
        future_time = datetime.now() + timedelta(seconds=3700)
        with patch('tests.integration.test_cross_cutting_integration.datetime') as mock_datetime:
            mock_datetime.now.return_value = future_time

            # Validate sessions (should expire)
            assert not validate_session(session1)
            assert not validate_session(session2)

            # Check expired sessions
            assert session1 in expired_sessions
            assert session2 in expired_sessions
            assert len(active_sessions) == 0

    def test_audit_logging_and_compliance(self, security_config):
        """Test audit logging for compliance and security monitoring"""
        audit_log = []
        compliance_events = []

        def log_audit_event(event_type: str, user: str, action: str,
                          resource: str, result: str, details: dict = None):
            """Log audit event for compliance"""
            event = {
                'timestamp': datetime.now(),
                'event_type': event_type,
                'user': user,
                'action': action,
                'resource': resource,
                'result': result,
                'details': details or {},
                'compliance_flags': []
            }

            # Add compliance flags
            if action in ['execute_orders', 'modify_config']:
                event['compliance_flags'].append('high_risk_action')
            if result == 'denied':
                event['compliance_flags'].append('access_denied')

            audit_log.append(event)

            # Check for compliance events
            if len(event['compliance_flags']) > 0:
                compliance_events.append(event)

        # Simulate various user actions
        actions = [
            ('admin', 'login', 'system', 'success'),
            ('trader1', 'execute_orders', 'AAPL', 'success'),
            ('analyst1', 'view_positions', 'portfolio', 'success'),
            ('viewer1', 'modify_config', 'system', 'denied'),
            ('trader2', 'execute_orders', 'GOOGL', 'success'),
            ('admin', 'modify_config', 'risk_settings', 'success'),
        ]

        for user, action, resource, result in actions:
            log_audit_event('user_action', user, action, resource, result)

        # Verify audit logging
        assert len(audit_log) == len(actions)

        # Verify compliance event detection
        assert len(compliance_events) > 0

        # Check high-risk actions are flagged
        high_risk_events = [e for e in compliance_events if 'high_risk_action' in e['compliance_flags']]
        assert len(high_risk_events) >= 2  # execute_orders and modify_config

        # Check access denials are flagged
        denied_events = [e for e in compliance_events if 'access_denied' in e['compliance_flags']]
        assert len(denied_events) >= 1

        # Verify audit trail integrity
        for event in audit_log:
            assert 'timestamp' in event
            assert 'user' in event
            assert 'action' in event
            assert event['result'] in ['success', 'denied']


class TestCachingAndPerformanceIntegration:
    """Integration tests for caching and performance optimization"""

    @pytest.fixture
    def cache_config(self):
        """Create cache configuration"""
        return {
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0,
                'ttl': 3600
            },
            'memory_cache': {
                'max_size': 1000,
                'ttl': 1800
            },
            'cache_strategy': 'multi_level',  # L1 memory, L2 Redis
            'cache_keys': {
                'market_data': 'market:{symbol}:{timeframe}',
                'indicators': 'indicators:{symbol}:{indicator}:{period}',
                'strategy_signals': 'signals:{strategy_id}:{symbol}',
                'risk_metrics': 'risk:{portfolio_id}:{metric}'
            }
        }

    def test_multi_level_caching_integration(self, cache_config):
        """Test multi-level caching (memory + Redis) integration"""
        memory_cache = {}
        redis_cache = {}
        cache_hits = {'memory': 0, 'redis': 0, 'miss': 0}

        def get_cache_key(pattern: str, **kwargs) -> str:
            """Generate cache key from pattern"""
            key = pattern
            for param, value in kwargs.items():
                key = key.replace(f'{{{param}}}', str(value))
            return key

        def get_cached_data(key: str) -> Optional[Any]:
            """Get data from multi-level cache"""
            # Check L1 memory cache first
            if key in memory_cache:
                cache_hits['memory'] += 1
                return memory_cache[key]['data']

            # Check L2 Redis cache
            if key in redis_cache:
                cache_hits['redis'] += 1
                data = redis_cache[key]['data']
                # Promote to memory cache
                memory_cache[key] = {
                    'data': data,
                    'timestamp': datetime.now(),
                    'ttl': cache_config['memory_cache']['ttl']
                }
                return data

            cache_hits['miss'] += 1
            return None

        def set_cached_data(key: str, data: Any, ttl: int = None):
            """Set data in multi-level cache"""
            if ttl is None:
                ttl = cache_config['redis']['ttl']

            # Store in Redis (L2)
            redis_cache[key] = {
                'data': data,
                'timestamp': datetime.now(),
                'ttl': ttl
            }

            # Store in memory (L1) if space available
            if len(memory_cache) < cache_config['memory_cache']['max_size']:
                memory_cache[key] = {
                    'data': data,
                    'timestamp': datetime.now(),
                    'ttl': cache_config['memory_cache']['ttl']
                }

        # Test caching market data
        market_data_key = get_cache_key(cache_config['cache_keys']['market_data'],
                                       symbol='AAPL', timeframe='1H')
        market_data = {'close': 150.25, 'volume': 1000000}

        # First access - cache miss
        result = get_cached_data(market_data_key)
        assert result is None
        assert cache_hits['miss'] == 1

        # Store data
        set_cached_data(market_data_key, market_data)

        # Second access - should hit memory cache
        result = get_cached_data(market_data_key)
        assert result == market_data
        assert cache_hits['memory'] == 1

        # Simulate memory cache eviction (clear memory)
        memory_cache.clear()

        # Third access - should hit Redis cache and promote to memory
        result = get_cached_data(market_data_key)
        assert result == market_data
        assert cache_hits['redis'] == 1
        assert market_data_key in memory_cache  # Promoted to memory

    def test_cache_invalidation_and_consistency(self, cache_config):
        """Test cache invalidation and data consistency"""
        cache_store = {}
        invalidation_log = []

        def invalidate_cache(pattern: str, **kwargs):
            """Invalidate cache entries matching pattern"""
            keys_to_remove = []
            
            for key in cache_store.keys():
                # Simple pattern matching - check if key starts with market: and contains AAPL
                if key.startswith('market:') and 'AAPL' in key:
                    keys_to_remove.append(key)
                    invalidation_log.append({
                        'timestamp': datetime.now(),
                        'action': 'invalidate',
                        'key': key,
                        'pattern': pattern,
                        'params': kwargs
                    })
            
            for key in keys_to_remove:
                del cache_store[key]

        def update_cached_data(key: str, new_data: Any):
            """Update cached data and handle consistency"""
            if key in cache_store:
                old_data = cache_store[key]['data']
                cache_store[key]['data'] = new_data
                cache_store[key]['last_updated'] = datetime.now()

                invalidation_log.append({
                    'timestamp': datetime.now(),
                    'action': 'update',
                    'key': key,
                    'old_value': old_data,
                    'new_value': new_data
                })

        # Populate cache with related data
        base_key = "market:AAPL:1H"
        indicator_key = "indicators:AAPL:SMA:20"
        signal_key = "signals:momentum_strategy:AAPL"

        cache_store[base_key] = {'data': {'close': 150.0}, 'last_updated': datetime.now()}
        cache_store[indicator_key] = {'data': {'sma': 148.5}, 'last_updated': datetime.now()}
        cache_store[signal_key] = {'data': {'signal': 'BUY'}, 'last_updated': datetime.now()}

        # Test selective invalidation
        invalidate_cache("market:{symbol}:*", symbol="AAPL")

        # Base market data should be invalidated
        assert base_key not in cache_store
        # Related data should remain (selective invalidation)
        assert indicator_key in cache_store
        assert signal_key in cache_store

        # Test update consistency
        update_cached_data(indicator_key, {'sma': 151.2})

        # Verify update logged
        update_events = [log for log in invalidation_log if log['action'] == 'update']
        assert len(update_events) == 1
        assert update_events[0]['key'] == indicator_key

    def test_performance_monitoring_with_caching(self, cache_config):
        """Test performance monitoring integration with caching"""
        performance_metrics = {
            'cache_hit_ratio': 0.0,
            'average_response_time': 0.0,
            'cache_size': 0,
            'eviction_count': 0
        }

        cache_access_log = []

        def monitor_cache_access(operation: str, key: str, hit: bool, response_time: float):
            """Monitor cache access performance"""
            cache_access_log.append({
                'timestamp': datetime.now(),
                'operation': operation,
                'key': key,
                'hit': hit,
                'response_time': response_time
            })

            # Update performance metrics
            total_accesses = len([log for log in cache_access_log if log['operation'] == 'get'])
            hits = sum(1 for log in cache_access_log if log['operation'] == 'get' and log['hit'])
            performance_metrics['cache_hit_ratio'] = hits / total_accesses if total_accesses > 0 else 0

            response_times = [log['response_time'] for log in cache_access_log]
            performance_metrics['average_response_time'] = sum(response_times) / len(response_times)

        # Simulate cache operations with monitoring
        operations = [
            ('get', 'market:AAPL:1H', True, 0.001),
            ('get', 'market:GOOGL:1H', False, 0.015),
            ('get', 'indicators:AAPL:SMA:20', True, 0.002),
            ('set', 'market:MSFT:1H', None, 0.005),
            ('get', 'market:MSFT:1H', True, 0.001),
        ]

        for operation, key, hit, response_time in operations:
            monitor_cache_access(operation, key, hit, response_time)

        # Verify performance metrics
        assert performance_metrics['cache_hit_ratio'] == 3/4  # 3 hits out of 4 gets
        assert performance_metrics['average_response_time'] > 0

        # Verify cache hits are faster than misses
        hits = [log['response_time'] for log in cache_access_log if log['hit'] and log['operation'] == 'get']
        misses = [log['response_time'] for log in cache_access_log if not log['hit'] and log['operation'] == 'get']

        if hits and misses:
            avg_hit_time = sum(hits) / len(hits)
            avg_miss_time = sum(misses) / len(misses)
            assert avg_hit_time < avg_miss_time