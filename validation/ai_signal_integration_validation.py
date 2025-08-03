#!/usr/bin/env python3
"""
AI Signal Integration Validation Script
=======================================

Comprehensive validation script for AI signal enhancement system.
Validates AI infrastructure, signal integration, and performance.

Author: AI Integration Team
Date: 2025-01-27
"""

import asyncio
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core_structure.signal_generation.ai_signal_enhancer import (
    AISignalEnhancer, 
    AIEnhancementConfig,
    AIEnhancementResult
)

@dataclass
class ValidationResult:
    """Result of a validation check"""
    check_name: str
    status: str  # 'PASS', 'FAIL', 'WARNING'
    message: str
    details: Optional[Dict[str, Any]] = None
    duration_ms: float = 0.0

@dataclass
class ValidationReport:
    """Complete validation report"""
    timestamp: str
    overall_status: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    results: List[ValidationResult]
    summary: Dict[str, Any]

class AISignalIntegrationValidator:
    """Validator for AI signal integration system"""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None
    
    async def run_comprehensive_validation(self) -> ValidationReport:
        """Run comprehensive validation of AI signal integration"""
        print("🔍 Starting AI Signal Integration Validation...")
        print("=" * 80)
        
        self.start_time = datetime.now()
        
        # Run validation checks
        await self._validate_ai_infrastructure()
        await self._validate_signal_integration()
        await self._validate_performance()
        await self._validate_feature_extraction()
        await self._validate_risk_assessment()
        await self._validate_error_handling()
        
        self.end_time = datetime.now()
        
        # Generate report
        report = self._generate_validation_report()
        
        # Print results
        self._print_validation_results(report)
        
        return report
    
    async def _run_check(self, check_name: str, check_function):
        """Run a validation check and record results"""
        start_time = time.time()
        
        try:
            result = await check_function()
            duration_ms = (time.time() - start_time) * 1000
            
            validation_result = ValidationResult(
                check_name=check_name,
                status=result['status'],
                message=result['message'],
                details=result.get('details'),
                duration_ms=duration_ms
            )
            
            self.results.append(validation_result)
            
            # Print check result
            status_icon = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "⚠️"
            print(f"{status_icon} {check_name}: {result['message']}")
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            validation_result = ValidationResult(
                check_name=check_name,
                status='FAIL',
                message=f"Check failed with error: {str(e)}",
                duration_ms=duration_ms
            )
            
            self.results.append(validation_result)
            print(f"❌ {check_name}: Failed with error: {str(e)}")
    
    async def _check_ai_signal_enhancer_init(self) -> Dict[str, Any]:
        """Check AI Signal Enhancer initialization"""
        try:
            config = AIEnhancementConfig()
            enhancer = AISignalEnhancer(config)
            
            return {
                'status': 'PASS',
                'message': 'AI Signal Enhancer initialized successfully',
                'details': {
                    'config_loaded': True,
                    'enhancer_created': True
                }
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': f'Failed to initialize AI Signal Enhancer: {str(e)}'
            }
    
    async def _check_configuration_validation(self) -> Dict[str, Any]:
        """Check configuration validation"""
        try:
            # Test default configuration
            config = AIEnhancementConfig()
            
            # Test custom configuration
            custom_config = AIEnhancementConfig(
                llm_model="gpt-3.5-turbo",
                llm_temperature=0.2,
                knowledge_base_enabled=False,
                vector_db_enabled=False,
                risk_assessment_enabled=True
            )
            
            return {
                'status': 'PASS',
                'message': 'Configuration validation passed',
                'details': {
                    'default_config_valid': True,
                    'custom_config_valid': True,
                    'llm_model': config.llm_model,
                    'knowledge_base_enabled': config.knowledge_base_enabled
                }
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': f'Configuration validation failed: {str(e)}'
            }
    
    async def _check_component_availability(self) -> Dict[str, Any]:
        """Check component availability"""
        try:
            config = AIEnhancementConfig()
            enhancer = AISignalEnhancer(config)
            
            # Check component availability
            llm_available = enhancer._is_llm_available()
            kb_available = enhancer._is_knowledge_base_available()
            vdb_available = enhancer._is_vector_db_available()
            
            return {
                'status': 'PASS' if any([llm_available, kb_available, vdb_available]) else 'WARNING',
                'message': 'Component availability check completed',
                'details': {
                    'llm_available': llm_available,
                    'knowledge_base_available': kb_available,
                    'vector_db_available': vdb_available
                }
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': f'Component availability check failed: {str(e)}'
            }
    
    async def _validate_ai_infrastructure(self):
        """Validate AI infrastructure components"""
        print("\n🤖 Validating AI Infrastructure...")
        print("-" * 50)
        
        # Check AI Signal Enhancer initialization
        await self._run_check(
            "AI Signal Enhancer Initialization",
            self._check_ai_signal_enhancer_init
        )
        
        # Check configuration validation
        await self._run_check(
            "Configuration Validation",
            self._check_configuration_validation
        )
        
        # Check component availability
        await self._run_check(
            "Component Availability",
            self._check_component_availability
        )
    
    async def _validate_signal_integration(self):
        """Validate signal integration functionality"""
        print("\n📊 Validating Signal Integration...")
        print("-" * 50)
        
        # Check basic signal enhancement
        await self._run_check(
            "Basic Signal Enhancement",
            self._check_basic_signal_enhancement
        )
        
        # Check signal enhancement with different configurations
        await self._run_check(
            "Signal Enhancement with Custom Config",
            self._check_signal_enhancement_custom_config
        )
        
        # Check signal enhancement performance
        await self._run_check(
            "Signal Enhancement Performance",
            self._check_signal_enhancement_performance
        )
    
    async def _check_basic_signal_enhancement(self) -> Dict[str, Any]:
        """Check basic signal enhancement functionality"""
        try:
            import pandas as pd
            import numpy as np
            
            # Create test data
            dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
            n_days = len(dates)
            
            # Generate test market data
            np.random.seed(42)
            base_price = 100.0
            returns = np.random.normal(0.001, 0.02, n_days)
            prices = [base_price]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            data = []
            for i, (date, price) in enumerate(zip(dates, prices)):
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                open_price = prices[i-1] if i > 0 else price
                volume = np.random.randint(1000000, 10000000)
                
                data.append({
                    'date': date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': price,
                    'volume': volume
                })
            
            market_data = pd.DataFrame(data)
            market_data.set_index('date', inplace=True)
            
            # Create test signal
            signal = {
                'symbol': 'AAPL',
                'type': 'LONG',
                'confidence': 0.75,
                'price': 150.0,
                'timestamp': datetime.now().isoformat(),
                'reason': 'Technical breakout above resistance'
            }
            
            # Test signal enhancement
            config = AIEnhancementConfig()
            enhancer = AISignalEnhancer(config)
            
            result = await enhancer.enhance_signal(
                signal=signal,
                market_data=market_data,
                symbol='AAPL'
            )
            
            return {
                'status': 'PASS',
                'message': 'Basic signal enhancement completed successfully',
                'details': {
                    'original_confidence': result.original_confidence,
                    'enhanced_confidence': result.enhanced_confidence,
                    'processing_time_ms': result.processing_time_ms,
                    'cache_hit': result.cache_hit
                }
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': f'Basic signal enhancement failed: {str(e)}'
            }
    
    async def _check_signal_enhancement_custom_config(self) -> Dict[str, Any]:
        """Check signal enhancement with custom configuration"""
        try:
            import pandas as pd
            import numpy as np
            
            # Create test data
            dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
            n_days = len(dates)
            
            np.random.seed(42)
            base_price = 100.0
            returns = np.random.normal(0.001, 0.02, n_days)
            prices = [base_price]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            data = []
            for i, (date, price) in enumerate(zip(dates, prices)):
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                open_price = prices[i-1] if i > 0 else price
                volume = np.random.randint(1000000, 10000000)
                
                data.append({
                    'date': date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': price,
                    'volume': volume
                })
            
            market_data = pd.DataFrame(data)
            market_data.set_index('date', inplace=True)
            
            signal = {
                'symbol': 'TSLA',
                'type': 'SHORT',
                'confidence': 0.65,
                'price': 200.0,
                'timestamp': datetime.now().isoformat(),
                'reason': 'Bearish divergence detected'
            }
            
            # Test with custom configuration
            custom_config = AIEnhancementConfig(
                llm_model=None,  # Disable LLM
                knowledge_base_enabled=False,
                vector_db_enabled=False,
                risk_assessment_enabled=True,
                enable_caching=True
            )
            
            enhancer = AISignalEnhancer(custom_config)
            
            result = await enhancer.enhance_signal(
                signal=signal,
                market_data=market_data,
                symbol='TSLA'
            )
            
            return {
                'status': 'PASS',
                'message': 'Custom configuration signal enhancement completed',
                'details': {
                    'original_confidence': result.original_confidence,
                    'enhanced_confidence': result.enhanced_confidence,
                    'processing_time_ms': result.processing_time_ms,
                    'config_used': 'custom'
                }
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': f'Custom configuration signal enhancement failed: {str(e)}'
            }
    
    async def _check_signal_enhancement_performance(self) -> Dict[str, Any]:
        """Check signal enhancement performance"""
        try:
            import pandas as pd
            import numpy as np
            
            # Create test data
            dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
            n_days = len(dates)
            
            np.random.seed(42)
            base_price = 100.0
            returns = np.random.normal(0.001, 0.02, n_days)
            prices = [base_price]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            data = []
            for i, (date, price) in enumerate(zip(dates, prices)):
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                open_price = prices[i-1] if i > 0 else price
                volume = np.random.randint(1000000, 10000000)
                
                data.append({
                    'date': date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': price,
                    'volume': volume
                })
            
            market_data = pd.DataFrame(data)
            market_data.set_index('date', inplace=True)
            
            signal = {
                'symbol': 'MSFT',
                'type': 'LONG',
                'confidence': 0.80,
                'price': 300.0,
                'timestamp': datetime.now().isoformat(),
                'reason': 'Strong earnings beat'
            }
            
            config = AIEnhancementConfig()
            enhancer = AISignalEnhancer(config)
            
            # Test performance with multiple signals
            start_time = time.time()
            results = []
            
            for i in range(10):
                result = await enhancer.enhance_signal(
                    signal=signal,
                    market_data=market_data,
                    symbol='MSFT'
                )
                results.append(result)
            
            end_time = time.time()
            total_time = (end_time - start_time) * 1000
            avg_time = total_time / 10
            
            # Check performance requirements
            performance_ok = avg_time < 500  # Less than 500ms per signal
            
            return {
                'status': 'PASS' if performance_ok else 'WARNING',
                'message': f'Performance test completed: {avg_time:.2f}ms average',
                'details': {
                    'total_time_ms': total_time,
                    'avg_time_per_signal_ms': avg_time,
                    'num_signals_processed': 10,
                    'performance_requirement_met': performance_ok
                }
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': f'Performance test failed: {str(e)}'
            }
    
    async def _validate_performance(self):
        """Validate performance characteristics"""
        print("\n⚡ Validating Performance...")
        print("-" * 50)
        
        # Check processing time
        await self._run_check(
            "Processing Time Validation",
            self._check_processing_time
        )
        
        # Check memory usage
        await self._run_check(
            "Memory Usage Validation",
            self._check_memory_usage
        )
        
        # Check throughput
        await self._run_check(
            "Throughput Validation",
            self._check_throughput
        ) 

    async def _check_processing_time(self) -> Dict[str, Any]:
        """Check processing time requirements"""
        try:
            import pandas as pd
            import numpy as np
            
            # Create test data
            dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
            n_days = len(dates)
            
            np.random.seed(42)
            base_price = 100.0
            returns = np.random.normal(0.001, 0.02, n_days)
            prices = [base_price]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            data = []
            for i, (date, price) in enumerate(zip(dates, prices)):
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                open_price = prices[i-1] if i > 0 else price
                volume = np.random.randint(1000000, 10000000)
                
                data.append({
                    'date': date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': price,
                    'volume': volume
                })
            
            market_data = pd.DataFrame(data)
            market_data.set_index('date', inplace=True)
            
            signal = {
                'symbol': 'GOOGL',
                'type': 'LONG',
                'confidence': 0.70,
                'price': 2500.0,
                'timestamp': datetime.now().isoformat(),
                'reason': 'AI breakthrough announcement'
            }
            
            config = AIEnhancementConfig()
            enhancer = AISignalEnhancer(config)
            
            # Test processing time
            start_time = time.time()
            result = await enhancer.enhance_signal(
                signal=signal,
                market_data=market_data,
                symbol='GOOGL'
            )
            end_time = time.time()
            
            processing_time_ms = (end_time - start_time) * 1000
            
            # Check if processing time meets requirements
            time_ok = processing_time_ms < 500  # Less than 500ms
            
            return {
                'status': 'PASS' if time_ok else 'WARNING',
                'message': f'Processing time: {processing_time_ms:.2f}ms',
                'details': {
                    'processing_time_ms': processing_time_ms,
                    'requirement_met': time_ok,
                    'requirement_threshold_ms': 500
                }
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': f'Processing time check failed: {str(e)}'
            }
    
    async def _check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            import psutil
            import pandas as pd
            import numpy as np
            
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            # Create test data
            dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
            n_days = len(dates)
            
            np.random.seed(42)
            base_price = 100.0
            returns = np.random.normal(0.001, 0.02, n_days)
            prices = [base_price]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            data = []
            for i, (date, price) in enumerate(zip(dates, prices)):
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                open_price = prices[i-1] if i > 0 else price
                volume = np.random.randint(1000000, 10000000)
                
                data.append({
                    'date': date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': price,
                    'volume': volume
                })
            
            market_data = pd.DataFrame(data)
            market_data.set_index('date', inplace=True)
            
            signal = {
                'symbol': 'AMZN',
                'type': 'SHORT',
                'confidence': 0.60,
                'price': 150.0,
                'timestamp': datetime.now().isoformat(),
                'reason': 'Weak Q4 guidance'
            }
            
            config = AIEnhancementConfig()
            enhancer = AISignalEnhancer(config)
            
            # Process signal
            result = await enhancer.enhance_signal(
                signal=signal,
                market_data=market_data,
                symbol='AMZN'
            )
            
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_delta = memory_after - memory_before
            
            # Check memory usage
            memory_ok = memory_delta < 100  # Less than 100MB increase
            
            return {
                'status': 'PASS' if memory_ok else 'WARNING',
                'message': f'Memory usage: {memory_delta:.2f}MB',
                'details': {
                    'memory_before_mb': memory_before,
                    'memory_after_mb': memory_after,
                    'memory_delta_mb': memory_delta,
                    'memory_ok': memory_ok
                }
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': f'Memory usage check failed: {str(e)}'
            }
    
    async def _check_throughput(self) -> Dict[str, Any]:
        """Check throughput performance"""
        try:
            import pandas as pd
            import numpy as np
            
            # Create test data
            dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
            n_days = len(dates)
            
            np.random.seed(42)
            base_price = 100.0
            returns = np.random.normal(0.001, 0.02, n_days)
            prices = [base_price]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            data = []
            for i, (date, price) in enumerate(zip(dates, prices)):
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                open_price = prices[i-1] if i > 0 else price
                volume = np.random.randint(1000000, 10000000)
                
                data.append({
                    'date': date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': price,
                    'volume': volume
                })
            
            market_data = pd.DataFrame(data)
            market_data.set_index('date', inplace=True)
            
            signal = {
                'symbol': 'NVDA',
                'type': 'LONG',
                'confidence': 0.85,
                'price': 500.0,
                'timestamp': datetime.now().isoformat(),
                'reason': 'AI chip demand surge'
            }
            
            config = AIEnhancementConfig()
            enhancer = AISignalEnhancer(config)
            
            # Test throughput with multiple signals
            start_time = time.time()
            num_signals = 20
            
            for i in range(num_signals):
                await enhancer.enhance_signal(
                    signal=signal,
                    market_data=market_data,
                    symbol='NVDA'
                )
            
            end_time = time.time()
            total_time = end_time - start_time
            throughput = num_signals / total_time  # signals per second
            
            # Check throughput requirements
            throughput_ok = throughput > 1  # More than 1 signal per second
            
            return {
                'status': 'PASS' if throughput_ok else 'WARNING',
                'message': f'Throughput: {throughput:.2f} signals/sec',
                'details': {
                    'num_signals': num_signals,
                    'total_time_seconds': total_time,
                    'throughput_signals_per_sec': throughput,
                    'throughput_ok': throughput_ok
                }
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': f'Throughput check failed: {str(e)}'
            }
    
    async def _validate_feature_extraction(self):
        """Validate feature extraction functionality"""
        print("\n🔧 Validating Feature Extraction...")
        print("-" * 50)
        
        await self._run_check(
            "Market Feature Extraction",
            self._check_market_feature_extraction
        )
        
        await self._run_check(
            "Technical Feature Extraction",
            self._check_technical_feature_extraction
        )
    
    async def _check_market_feature_extraction(self) -> Dict[str, Any]:
        """Check market feature extraction"""
        try:
            import pandas as pd
            import numpy as np
            
            # Create test data
            dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
            n_days = len(dates)
            
            np.random.seed(42)
            base_price = 100.0
            returns = np.random.normal(0.001, 0.02, n_days)
            prices = [base_price]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            data = []
            for i, (date, price) in enumerate(zip(dates, prices)):
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                open_price = prices[i-1] if i > 0 else price
                volume = np.random.randint(1000000, 10000000)
                
                data.append({
                    'date': date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': price,
                    'volume': volume
                })
            
            market_data = pd.DataFrame(data)
            market_data.set_index('date', inplace=True)
            
            config = AIEnhancementConfig()
            enhancer = AISignalEnhancer(config)
            
            # Extract features
            features = enhancer._extract_market_features(market_data)
            
            # Check if features were extracted
            features_extracted = len(features) > 0
            required_features = ['current_price', 'price_change', 'volume', 'volatility']
            all_required_present = all(feature in features for feature in required_features)
            
            return {
                'status': 'PASS' if features_extracted and all_required_present else 'FAIL',
                'message': f'Extracted {len(features)} market features',
                'details': {
                    'features_extracted': features_extracted,
                    'num_features': len(features),
                    'all_required_present': all_required_present,
                    'feature_names': list(features.keys())
                }
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': f'Market feature extraction failed: {str(e)}'
            }
    
    async def _check_technical_feature_extraction(self) -> Dict[str, Any]:
        """Check technical feature extraction"""
        try:
            import pandas as pd
            import numpy as np
            
            # Create test data
            dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
            n_days = len(dates)
            
            np.random.seed(42)
            base_price = 100.0
            returns = np.random.normal(0.001, 0.02, n_days)
            prices = [base_price]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            data = []
            for i, (date, price) in enumerate(zip(dates, prices)):
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                open_price = prices[i-1] if i > 0 else price
                volume = np.random.randint(1000000, 10000000)
                
                data.append({
                    'date': date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': price,
                    'volume': volume
                })
            
            market_data = pd.DataFrame(data)
            market_data.set_index('date', inplace=True)
            
            config = AIEnhancementConfig()
            enhancer = AISignalEnhancer(config)
            
            # Extract technical features
            features = enhancer._extract_technical_features(market_data)
            
            # Check if features were extracted
            features_extracted = len(features) > 0
            
            return {
                'status': 'PASS' if features_extracted else 'WARNING',
                'message': f'Extracted {len(features)} technical features',
                'details': {
                    'features_extracted': features_extracted,
                    'num_features': len(features),
                    'feature_names': list(features.keys())
                }
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': f'Technical feature extraction failed: {str(e)}'
            }
    
    async def _validate_risk_assessment(self):
        """Validate risk assessment functionality"""
        print("\n⚠️ Validating Risk Assessment...")
        print("-" * 50)
        
        await self._run_check(
            "Risk Metrics Calculation",
            self._check_risk_metrics_calculation
        )
        
        await self._run_check(
            "Risk Level Classification",
            self._check_risk_level_classification
        )
    
    async def _check_risk_metrics_calculation(self) -> Dict[str, Any]:
        """Check risk metrics calculation"""
        try:
            import pandas as pd
            import numpy as np
            
            # Create test data
            dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
            n_days = len(dates)
            
            np.random.seed(42)
            base_price = 100.0
            returns = np.random.normal(0.001, 0.02, n_days)
            prices = [base_price]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            data = []
            for i, (date, price) in enumerate(zip(dates, prices)):
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                open_price = prices[i-1] if i > 0 else price
                volume = np.random.randint(1000000, 10000000)
                
                data.append({
                    'date': date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': price,
                    'volume': volume
                })
            
            market_data = pd.DataFrame(data)
            market_data.set_index('date', inplace=True)
            
            signal = {
                'symbol': 'META',
                'type': 'LONG',
                'confidence': 0.75,
                'price': 300.0,
                'timestamp': datetime.now().isoformat(),
                'reason': 'VR breakthrough'
            }
            
            config = AIEnhancementConfig()
            enhancer = AISignalEnhancer(config)
            
            # Extract features
            features = enhancer._extract_market_features(market_data)
            
            # Calculate risk metrics
            risk_metrics = enhancer._calculate_risk_metrics(signal, features, market_data)
            
            # Check if risk metrics were calculated
            metrics_calculated = len(risk_metrics) > 0
            risk_score_present = 'risk_score' in risk_metrics
            
            return {
                'status': 'PASS' if metrics_calculated and risk_score_present else 'FAIL',
                'message': f'Calculated {len(risk_metrics)} risk metrics',
                'details': {
                    'metrics_calculated': metrics_calculated,
                    'num_metrics': len(risk_metrics),
                    'risk_score_present': risk_score_present,
                    'risk_score': risk_metrics.get('risk_score', 0)
                }
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': f'Risk metrics calculation failed: {str(e)}'
            }
    
    async def _check_risk_level_classification(self) -> Dict[str, Any]:
        """Check risk level classification"""
        try:
            config = AIEnhancementConfig()
            enhancer = AISignalEnhancer(config)
            
            # Test different risk scores
            test_cases = [
                (0.1, 'very_low'),
                (0.3, 'low'),
                (0.5, 'medium'),
                (0.7, 'high'),
                (0.9, 'very_high')
            ]
            
            results = []
            for risk_score, expected_level in test_cases:
                actual_level = enhancer._classify_risk_level(risk_score)
                results.append({
                    'risk_score': risk_score,
                    'expected': expected_level,
                    'actual': actual_level,
                    'correct': actual_level == expected_level
                })
            
            all_correct = all(r['correct'] for r in results)
            
            return {
                'status': 'PASS' if all_correct else 'FAIL',
                'message': f'Risk level classification: {sum(r["correct"] for r in results)}/{len(results)} correct',
                'details': {
                    'all_correct': all_correct,
                    'test_cases': results
                }
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': f'Risk level classification failed: {str(e)}'
            }
    
    async def _validate_error_handling(self):
        """Validate error handling"""
        print("\n🛡️ Validating Error Handling...")
        print("-" * 50)
        
        await self._run_check(
            "Invalid Data Handling",
            self._check_invalid_data_handling
        )
        
        await self._run_check(
            "Missing Components Handling",
            self._check_missing_components_handling
        )
    
    async def _check_invalid_data_handling(self) -> Dict[str, Any]:
        """Check handling of invalid data"""
        try:
            config = AIEnhancementConfig()
            enhancer = AISignalEnhancer(config)
            
            # Test with empty market data
            import pandas as pd
            empty_data = pd.DataFrame()
            
            signal = {
                'symbol': 'TEST',
                'type': 'LONG',
                'confidence': 0.5,
                'price': 100.0,
                'timestamp': datetime.now().isoformat(),
                'reason': 'Test signal'
            }
            
            # Should handle gracefully
            result = await enhancer.enhance_signal(
                signal=signal,
                market_data=empty_data,
                symbol='TEST'
            )
            
            return {
                'status': 'PASS',
                'message': 'Invalid data handled gracefully',
                'details': {
                    'result_type': type(result).__name__,
                    'enhanced_confidence': result.enhanced_confidence
                }
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': f'Invalid data handling failed: {str(e)}'
            }
    
    async def _check_missing_components_handling(self) -> Dict[str, Any]:
        """Check handling of missing components"""
        try:
            # Test with minimal configuration
            minimal_config = AIEnhancementConfig(
                llm_model=None,
                knowledge_base_enabled=False,
                vector_db_enabled=False,
                risk_assessment_enabled=False
            )
            
            enhancer = AISignalEnhancer(minimal_config)
            
            # Should still work with basic functionality
            import pandas as pd
            import numpy as np
            
            # Create minimal test data
            dates = pd.date_range(start='2024-01-01', end='2024-01-10', freq='D')
            data = []
            for i, date in enumerate(dates):
                data.append({
                    'date': date,
                    'open': 100 + i,
                    'high': 102 + i,
                    'low': 98 + i,
                    'close': 101 + i,
                    'volume': 1000000
                })
            
            market_data = pd.DataFrame(data)
            market_data.set_index('date', inplace=True)
            
            signal = {
                'symbol': 'TEST',
                'type': 'LONG',
                'confidence': 0.5,
                'price': 100.0,
                'timestamp': datetime.now().isoformat(),
                'reason': 'Test signal'
            }
            
            result = await enhancer.enhance_signal(
                signal=signal,
                market_data=market_data,
                symbol='TEST'
            )
            
            return {
                'status': 'PASS',
                'message': 'Missing components handled gracefully',
                'details': {
                    'result_type': type(result).__name__,
                    'enhanced_confidence': result.enhanced_confidence
                }
            }
        except Exception as e:
            return {
                'status': 'FAIL',
                'message': f'Missing components handling failed: {str(e)}'
            }
    
    def _generate_validation_report(self) -> ValidationReport:
        """Generate comprehensive validation report"""
        # Calculate statistics
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r.status == 'PASS')
        failed_checks = sum(1 for r in self.results if r.status == 'FAIL')
        warning_checks = sum(1 for r in self.results if r.status == 'WARNING')
        
        # Determine overall status
        if failed_checks == 0 and warning_checks == 0:
            overall_status = 'PASS'
        elif failed_checks == 0:
            overall_status = 'WARNING'
        else:
            overall_status = 'FAIL'
        
        # Calculate summary statistics
        total_duration = sum(r.duration_ms for r in self.results)
        avg_duration = total_duration / total_checks if total_checks > 0 else 0
        
        summary = {
            'total_duration_ms': total_duration,
            'avg_check_duration_ms': avg_duration,
            'success_rate': (passed_checks / total_checks * 100) if total_checks > 0 else 0,
            'validation_time': (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0
        }
        
        return ValidationReport(
            timestamp=datetime.now().isoformat(),
            overall_status=overall_status,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warning_checks=warning_checks,
            results=self.results,
            summary=summary
        )
    
    def _print_validation_results(self, report: ValidationReport):
        """Print validation results"""
        print("\n" + "=" * 80)
        print("📊 VALIDATION RESULTS SUMMARY")
        print("=" * 80)
        print(f"Overall Status: {report.overall_status}")
        print(f"Total Checks: {report.total_checks}")
        print(f"Passed: {report.passed_checks}")
        print(f"Failed: {report.failed_checks}")
        print(f"Warnings: {report.warning_checks}")
        print(f"Success Rate: {report.summary['success_rate']:.1f}%")
        print(f"Total Duration: {report.summary['total_duration_ms']:.2f}ms")
        print(f"Average Check Duration: {report.summary['avg_check_duration_ms']:.2f}ms")
        print(f"Validation Time: {report.summary['validation_time']:.2f}s")
        
        # Print detailed results
        print(f"\n📋 DETAILED RESULTS:")
        print("-" * 80)
        for result in report.results:
            status_icon = "✅" if result.status == 'PASS' else "❌" if result.status == 'FAIL' else "⚠️"
            print(f"{status_icon} {result.check_name}: {result.message} ({result.duration_ms:.2f}ms)")
        
        print("=" * 80)

async def main():
    """Main validation function"""
    validator = AISignalIntegrationValidator()
    report = await validator.run_comprehensive_validation()
    
    # Save report to file
    report_file = project_root / "validation" / "ai_signal_validation_report.json"
    
    # Convert report to JSON-serializable format
    report_dict = {
        'timestamp': report.timestamp,
        'overall_status': report.overall_status,
        'total_checks': report.total_checks,
        'passed_checks': report.passed_checks,
        'failed_checks': report.failed_checks,
        'warning_checks': report.warning_checks,
        'summary': report.summary,
        'results': [
            {
                'check_name': r.check_name,
                'status': r.status,
                'message': r.message,
                'details': r.details,
                'duration_ms': r.duration_ms
            }
            for r in report.results
        ]
    }
    
    with open(report_file, 'w') as f:
        json.dump(report_dict, f, indent=2)
    
    print(f"\n📄 Validation report saved to: {report_file}")
    
    # Return exit code
    return 0 if report.overall_status in ['PASS', 'WARNING'] else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 