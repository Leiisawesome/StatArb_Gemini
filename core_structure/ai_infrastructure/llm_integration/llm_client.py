"""
LLM Integration Client

Professional LLM integration for institutional trading system including:
- Multi-provider support (OpenAI, Anthropic, local models)
- Trading-specific prompt engineering and safety
- Response caching and optimization
- Cost tracking and rate limiting
- Security and compliance features

Author: Pro Quant Desk Trader
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
import hashlib
import uuid

# Optional imports for different providers
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class ModelType(Enum):
    """Supported LLM model types"""
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    LOCAL_MODEL = "local"


class ProviderType(Enum):
    """LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


@dataclass
class LLMConfig:
    """LLM client configuration"""
    model_type: ModelType = ModelType.GPT_4_TURBO
    provider: ProviderType = ProviderType.OPENAI
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    # Performance settings
    max_tokens: int = 4096
    temperature: float = 0.1  # Low temperature for financial analysis
    timeout: int = 60
    max_retries: int = 3
    
    # Rate limiting
    requests_per_minute: int = 60
    tokens_per_minute: int = 150000
    
    # Caching
    enable_cache: bool = True
    cache_ttl_minutes: int = 60
    max_cache_size: int = 1000
    
    # Safety and compliance
    enable_content_filter: bool = True
    enable_pii_detection: bool = True
    enable_cost_tracking: bool = True
    max_daily_cost: float = 100.0


@dataclass
class LLMResponse:
    """LLM response structure"""
    request_id: str
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    response_time: float
    cost_estimate: float
    cached: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Safety checks
    content_filtered: bool = False
    pii_detected: bool = False
    confidence_score: float = 1.0


class TokenTracker:
    """Token usage and cost tracking"""
    
    def __init__(self):
        """Initialize token tracker"""
        self.daily_usage: Dict[str, Dict[str, int]] = {}
        self.total_cost = 0.0
        self.request_count = 0
        
        # Pricing per 1K tokens (approximate)
        self.pricing = {
            ModelType.GPT_4: {"input": 0.03, "output": 0.06},
            ModelType.GPT_4_TURBO: {"input": 0.01, "output": 0.03},
            ModelType.GPT_3_5_TURBO: {"input": 0.0015, "output": 0.002},
            ModelType.CLAUDE_3_OPUS: {"input": 0.015, "output": 0.075},
            ModelType.CLAUDE_3_SONNET: {"input": 0.003, "output": 0.015},
            ModelType.CLAUDE_3_HAIKU: {"input": 0.00025, "output": 0.00125},
        }
    
    def track_usage(self, model: ModelType, input_tokens: int, output_tokens: int) -> float:
        """Track token usage and calculate cost"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in self.daily_usage:
            self.daily_usage[today] = {"input_tokens": 0, "output_tokens": 0, "requests": 0}
        
        self.daily_usage[today]["input_tokens"] += input_tokens
        self.daily_usage[today]["output_tokens"] += output_tokens
        self.daily_usage[today]["requests"] += 1
        self.request_count += 1
        
        # Calculate cost
        cost = 0.0
        if model in self.pricing:
            pricing = self.pricing[model]
            cost = (input_tokens / 1000 * pricing["input"] + 
                   output_tokens / 1000 * pricing["output"])
        
        self.total_cost += cost
        return cost
    
    def get_daily_stats(self, date: str = None) -> Dict[str, Any]:
        """Get usage statistics for a specific date"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        return self.daily_usage.get(date, {
            "input_tokens": 0,
            "output_tokens": 0,
            "requests": 0
        })


class ResponseCache:
    """LLM response caching system"""
    
    def __init__(self, max_size: int = 1000, ttl_minutes: int = 60):
        """Initialize response cache"""
        self.max_size = max_size
        self.ttl = timedelta(minutes=ttl_minutes)
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, datetime] = {}
    
    def _generate_key(self, prompt: str, model: str, temperature: float) -> str:
        """Generate cache key"""
        content = f"{prompt}_{model}_{temperature}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, prompt: str, model: str, temperature: float) -> Optional[LLMResponse]:
        """Get cached response"""
        key = self._generate_key(prompt, model, temperature)
        
        if key in self.cache:
            cached_data = self.cache[key]
            cached_time = cached_data["timestamp"]
            
            # Check if cache is still valid
            if datetime.now() - cached_time < self.ttl:
                self.access_times[key] = datetime.now()
                response = cached_data["response"]
                response.cached = True
                return response
            else:
                # Remove expired cache
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
        
        return None
    
    def set(self, prompt: str, model: str, temperature: float, response: LLMResponse):
        """Cache response"""
        key = self._generate_key(prompt, model, temperature)
        
        # Check cache size and evict if necessary
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        self.cache[key] = {
            "response": response,
            "timestamp": datetime.now()
        }
        self.access_times[key] = datetime.now()
    
    def _evict_oldest(self):
        """Evict oldest cache entry"""
        if self.access_times:
            oldest_key = min(self.access_times, key=self.access_times.get)
            del self.cache[oldest_key]
            del self.access_times[oldest_key]


class LLMClient:
    """
    Professional LLM Client
    
    Comprehensive LLM integration for institutional trading system including:
    - Multi-provider support with fallback mechanisms
    - Trading-specific prompt engineering and optimization
    - Advanced caching and performance optimization
    - Cost tracking and budget management
    - Security and compliance features
    - Rate limiting and error handling
    """
    
    def __init__(self, config: LLMConfig):
        """Initialize LLM client"""
        self.config = config
        self.logger = logging.getLogger("llm_client")
        
        # Initialize providers
        self.openai_client = None
        self.anthropic_client = None
        
        # Performance tracking
        self.token_tracker = TokenTracker()
        self.cache = ResponseCache(config.max_cache_size, config.cache_ttl_minutes)
        
        # Rate limiting
        self.request_times: List[datetime] = []
        self.token_usage_per_minute = 0
        self.last_token_reset = datetime.now()
        
        # Initialize providers
        self._initialize_providers()
        
        self.logger.info(f"LLM client initialized with {config.model_type.value}")
    
    def _initialize_providers(self):
        """Initialize LLM providers"""
        try:
            if self.config.provider == ProviderType.OPENAI and OPENAI_AVAILABLE:
                self.openai_client = openai.AsyncOpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    timeout=self.config.timeout
                )
                self.logger.info("OpenAI client initialized")
            
            elif self.config.provider == ProviderType.ANTHROPIC and ANTHROPIC_AVAILABLE:
                self.anthropic_client = anthropic.AsyncAnthropic(
                    api_key=self.config.api_key,
                    timeout=self.config.timeout
                )
                self.logger.info("Anthropic client initialized")
            
            elif self.config.provider == ProviderType.LOCAL:
                self.logger.info("Local model configuration set")
            
        except Exception as e:
            self.logger.error(f"Error initializing providers: {e}")
            raise
    
    async def generate_response(self, prompt: str, system_prompt: str = None,
                              context: List[Dict[str, str]] = None,
                              temperature: Optional[float] = None) -> LLMResponse:
        """
        Generate LLM response
        
        Args:
            prompt: User prompt
            system_prompt: System/instruction prompt
            context: Conversation context
            temperature: Override default temperature
            
        Returns:
            LLMResponse object
        """
        try:
            request_id = str(uuid.uuid4())
            start_time = time.time()
            
            # Use config temperature if not specified
            temp = temperature if temperature is not None else self.config.temperature
            
            # Check cache first
            if self.config.enable_cache:
                cached_response = self.cache.get(prompt, self.config.model_type.value, temp)
                if cached_response:
                    self.logger.info(f"Cache hit for request {request_id}")
                    return cached_response
            
            # Check rate limits
            await self._check_rate_limits()
            
            # Check daily cost limit
            if self.config.enable_cost_tracking:
                if self.token_tracker.total_cost > self.config.max_daily_cost:
                    raise Exception(f"Daily cost limit exceeded: ${self.token_tracker.total_cost:.2f}")
            
            # Generate response based on provider
            response = await self._generate_provider_response(
                prompt, system_prompt, context, temp, request_id
            )
            
            # Calculate response time
            response.response_time = time.time() - start_time
            
            # Cache response
            if self.config.enable_cache and not response.content_filtered:
                self.cache.set(prompt, self.config.model_type.value, temp, response)
            
            # Update rate limiting
            self.request_times.append(datetime.now())
            
            self.logger.info(f"Generated response {request_id} in {response.response_time:.2f}s")
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            raise
    
    async def _generate_provider_response(self, prompt: str, system_prompt: str,
                                        context: List[Dict[str, str]], temperature: float,
                                        request_id: str) -> LLMResponse:
        """Generate response using appropriate provider"""
        
        if self.config.provider == ProviderType.OPENAI:
            return await self._generate_openai_response(
                prompt, system_prompt, context, temperature, request_id
            )
        elif self.config.provider == ProviderType.ANTHROPIC:
            return await self._generate_anthropic_response(
                prompt, system_prompt, context, temperature, request_id
            )
        else:
            raise NotImplementedError(f"Provider {self.config.provider} not implemented")
    
    async def _generate_openai_response(self, prompt: str, system_prompt: str,
                                      context: List[Dict[str, str]], temperature: float,
                                      request_id: str) -> LLMResponse:
        """Generate response using OpenAI"""
        try:
            # Build messages
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            if context:
                messages.extend(context)
            
            messages.append({"role": "user", "content": prompt})
            
            # Make API call
            response = await self.openai_client.chat.completions.create(
                model=self.config.model_type.value,
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=temperature,
                timeout=self.config.timeout
            )
            
            # Extract response data
            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            # Calculate cost
            cost = self.token_tracker.track_usage(
                self.config.model_type,
                usage["prompt_tokens"],
                usage["completion_tokens"]
            )
            
            # Perform safety checks
            content_filtered, pii_detected = await self._perform_safety_checks(content)
            
            return LLMResponse(
                request_id=request_id,
                content=content,
                model=self.config.model_type.value,
                usage=usage,
                finish_reason=response.choices[0].finish_reason,
                response_time=0.0,  # Will be set by caller
                cost_estimate=cost,
                content_filtered=content_filtered,
                pii_detected=pii_detected
            )
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise
    
    async def _generate_anthropic_response(self, prompt: str, system_prompt: str,
                                         context: List[Dict[str, str]], temperature: float,
                                         request_id: str) -> LLMResponse:
        """Generate response using Anthropic Claude"""
        try:
            # Build message content
            full_prompt = ""
            if system_prompt:
                full_prompt = f"System: {system_prompt}\n\n"
            
            if context:
                for msg in context:
                    full_prompt += f"{msg['role'].title()}: {msg['content']}\n\n"
            
            full_prompt += f"Human: {prompt}\n\nAssistant:"
            
            # Make API call
            response = await self.anthropic_client.completions.create(
                model=self.config.model_type.value,
                prompt=full_prompt,
                max_tokens_to_sample=self.config.max_tokens,
                temperature=temperature,
                timeout=self.config.timeout
            )
            
            # Extract response data
            content = response.completion
            
            # Estimate token usage (Anthropic doesn't always provide exact counts)
            estimated_prompt_tokens = len(full_prompt.split()) * 1.3  # Rough estimate
            estimated_completion_tokens = len(content.split()) * 1.3
            
            usage = {
                "prompt_tokens": int(estimated_prompt_tokens),
                "completion_tokens": int(estimated_completion_tokens),
                "total_tokens": int(estimated_prompt_tokens + estimated_completion_tokens)
            }
            
            # Calculate cost
            cost = self.token_tracker.track_usage(
                self.config.model_type,
                usage["prompt_tokens"],
                usage["completion_tokens"]
            )
            
            # Perform safety checks
            content_filtered, pii_detected = await self._perform_safety_checks(content)
            
            return LLMResponse(
                request_id=request_id,
                content=content,
                model=self.config.model_type.value,
                usage=usage,
                finish_reason=response.stop_reason,
                response_time=0.0,  # Will be set by caller
                cost_estimate=cost,
                content_filtered=content_filtered,
                pii_detected=pii_detected
            )
            
        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            raise
    
    async def _check_rate_limits(self):
        """Check and enforce rate limits"""
        now = datetime.now()
        
        # Clean old requests (older than 1 minute)
        cutoff = now - timedelta(minutes=1)
        self.request_times = [t for t in self.request_times if t > cutoff]
        
        # Check requests per minute
        if len(self.request_times) >= self.config.requests_per_minute:
            sleep_time = 60 - (now - self.request_times[0]).total_seconds()
            if sleep_time > 0:
                self.logger.warning(f"Rate limit hit, sleeping for {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)
        
        # Reset token counter if needed
        if (now - self.last_token_reset).total_seconds() >= 60:
            self.token_usage_per_minute = 0
            self.last_token_reset = now
    
    async def _perform_safety_checks(self, content: str) -> tuple[bool, bool]:
        """Perform content safety and PII detection"""
        content_filtered = False
        pii_detected = False
        
        if self.config.enable_content_filter:
            # Basic content filtering (implement more sophisticated filtering as needed)
            harmful_patterns = [
                "insider trading", "market manipulation", "pump and dump",
                "front running", "illegal", "unauthorized"
            ]
            
            content_lower = content.lower()
            for pattern in harmful_patterns:
                if pattern in content_lower:
                    content_filtered = True
                    self.logger.warning(f"Content filtered: detected '{pattern}'")
                    break
        
        if self.config.enable_pii_detection:
            # Basic PII detection (implement more sophisticated detection as needed)
            import re
            
            # Check for common PII patterns
            patterns = [
                r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
                r'\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b',  # Credit card
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Email
            ]
            
            for pattern in patterns:
                if re.search(pattern, content):
                    pii_detected = True
                    self.logger.warning("PII detected in response")
                    break
        
        return content_filtered, pii_detected
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "total_requests": self.token_tracker.request_count,
            "total_cost": self.token_tracker.total_cost,
            "daily_stats": self.token_tracker.get_daily_stats(),
            "cache_size": len(self.cache.cache),
            "cache_hit_rate": self._calculate_cache_hit_rate(),
            "config": {
                "model": self.config.model_type.value,
                "provider": self.config.provider.value,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature
            }
        }
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        # This is a simplified calculation
        # In practice, you'd track hits/misses more precisely
        total_requests = self.token_tracker.request_count
        if total_requests == 0:
            return 0.0
        
        # Estimate cache hits based on cache size and requests
        estimated_hits = min(len(self.cache.cache), total_requests * 0.3)
        return (estimated_hits / total_requests) * 100
    
    async def analyze_market_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze market sentiment from text"""
        system_prompt = """You are a professional financial analyst specializing in market sentiment analysis.
        Analyze the provided text and return sentiment analysis in the following JSON format:
        {
            "sentiment": "positive|negative|neutral",
            "confidence": 0.85,
            "key_factors": ["factor1", "factor2"],
            "market_impact": "high|medium|low",
            "investment_implications": "brief analysis"
        }"""
        
        prompt = f"Analyze the market sentiment of this text: {text}"
        
        response = await self.generate_response(prompt, system_prompt)
        
        try:
            # Parse JSON response
            sentiment_data = json.loads(response.content)
            return sentiment_data
        except json.JSONDecodeError:
            self.logger.error("Failed to parse sentiment analysis JSON")
            return {
                "sentiment": "neutral",
                "confidence": 0.5,
                "key_factors": [],
                "market_impact": "low",
                "investment_implications": "Unable to analyze"
            }
    
    async def generate_trading_insight(self, data: Dict[str, Any]) -> str:
        """Generate trading insight from market data"""
        system_prompt = """You are a professional quantitative analyst with expertise in statistical arbitrage.
        Provide concise, actionable trading insights based on the provided market data.
        Focus on risk-adjusted opportunities and statistical significance."""
        
        prompt = f"""Analyze this trading data and provide insights:
        
        Market Data:
        {json.dumps(data, indent=2)}
        
        Please provide:
        1. Key observations
        2. Statistical significance of patterns
        3. Risk assessment
        4. Actionable recommendations
        """
        
        response = await self.generate_response(prompt, system_prompt)
        return response.content 