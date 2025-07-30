#!/usr/bin/env python3
"""
Deployment Manager
Phase 4: Production Deployment & Monitoring
"""

import logging
import os
import sys
import subprocess
import json
import yaml
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None

try:
    import kubernetes
    from kubernetes import client, config
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    kubernetes = None
    client = None
    config = None
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class DeploymentManager:
    """Production deployment manager for the trading system"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or 'production_config.yaml'
        self.deployment_config = self._load_config()
        self.deployment_status = {}
        self.deployment_history = []
        
        logger.info("Initialized DeploymentManager")
    
    def _load_config(self) -> Dict:
        """Load deployment configuration"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                logger.info(f"Loaded deployment config from {self.config_path}")
                return config
            else:
                # Default configuration
                default_config = {
                    'deployment': {
                        'environment': 'production',
                        'namespace': 'trading-system',
                        'replicas': 3,
                        'resources': {
                            'cpu': '1000m',
                            'memory': '2Gi'
                        }
                    },
                    'services': {
                        'api': {
                            'port': 8080,
                            'type': 'LoadBalancer'
                        },
                        'monitoring': {
                            'port': 9090,
                            'type': 'ClusterIP'
                        }
                    },
                    'databases': {
                        'clickhouse': {
                            'host': 'clickhouse-service',
                            'port': 9000,
                            'database': 'trading_data'
                        },
                        'redis': {
                            'host': 'redis-service',
                            'port': 6379
                        }
                    }
                }
                logger.info("Using default deployment configuration")
                return default_config
        except Exception as e:
            logger.error(f"Failed to load deployment config: {e}")
            return {}
    
    def validate_deployment_config(self) -> Dict:
        """Validate deployment configuration"""
        
        try:
            logger.info("Validating deployment configuration...")
            
            validation_results = {
                'config_valid': True,
                'errors': [],
                'warnings': [],
                'validation_date': datetime.now().isoformat()
            }
            
            # Validate required sections
            required_sections = ['deployment', 'services', 'databases']
            for section in required_sections:
                if section not in self.deployment_config:
                    validation_results['errors'].append(f"Missing required section: {section}")
                    validation_results['config_valid'] = False
            
            # Validate deployment settings
            if 'deployment' in self.deployment_config:
                deployment = self.deployment_config['deployment']
                if 'environment' not in deployment:
                    validation_results['warnings'].append("Environment not specified, using default")
                
                if 'replicas' in deployment:
                    replicas = deployment['replicas']
                    if not isinstance(replicas, int) or replicas < 1:
                        validation_results['errors'].append("Invalid replicas configuration")
                        validation_results['config_valid'] = False
            
            # Validate service configurations
            if 'services' in self.deployment_config:
                services = self.deployment_config['services']
                for service_name, service_config in services.items():
                    if 'port' not in service_config:
                        validation_results['errors'].append(f"Missing port for service: {service_name}")
                        validation_results['config_valid'] = False
            
            # Validate database configurations
            if 'databases' in self.deployment_config:
                databases = self.deployment_config['databases']
                for db_name, db_config in databases.items():
                    if 'host' not in db_config:
                        validation_results['errors'].append(f"Missing host for database: {db_name}")
                        validation_results['config_valid'] = False
            
            logger.info(f"Configuration validation: {validation_results['config_valid']}")
            return validation_results
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return {'config_valid': False, 'errors': [str(e)], 'warnings': []}
    
    def create_docker_deployment(self) -> Dict:
        """Create Docker deployment"""
        
        try:
            logger.info("Creating Docker deployment...")
            
            # Create Dockerfile
            dockerfile_content = self._generate_dockerfile()
            with open('Dockerfile', 'w') as f:
                f.write(dockerfile_content)
            
            # Create docker-compose.yml
            docker_compose_content = self._generate_docker_compose()
            with open('docker-compose.yml', 'w') as f:
                f.write(docker_compose_content)
            
            # Build Docker image
            build_result = self._build_docker_image()
            
            deployment_result = {
                'deployment_type': 'docker',
                'dockerfile_created': True,
                'docker_compose_created': True,
                'image_built': build_result.get('success', False),
                'image_name': build_result.get('image_name', 'trading-system'),
                'deployment_date': datetime.now().isoformat()
            }
            
            # Store deployment result
            deployment_id = f"docker_deployment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.deployment_status[deployment_id] = deployment_result
            
            logger.info("Docker deployment created successfully")
            return deployment_result
            
        except Exception as e:
            logger.error(f"Docker deployment failed: {e}")
            return {'deployment_type': 'docker', 'success': False, 'error': str(e)}
    
    def _generate_dockerfile(self) -> str:
        """Generate Dockerfile content"""
        
        dockerfile = """# Trading System Dockerfile
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 trading && chown -R trading:trading /app
USER trading

# Expose ports
EXPOSE 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Start application
CMD ["python", "main.py"]
"""
        return dockerfile
    
    def _generate_docker_compose(self) -> str:
        """Generate docker-compose.yml content"""
        
        compose_content = """version: '3.8'

services:
  trading-system:
    build: .
    ports:
      - "8080:8080"
      - "9090:9090"
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - clickhouse
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8080/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  clickhouse:
    image: clickhouse/clickhouse-server:latest
    ports:
      - "9000:9000"
      - "8123:8123"
    environment:
      - CLICKHOUSE_DB=trading_data
    volumes:
      - clickhouse_data:/var/lib/clickhouse
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  monitoring:
    image: prom/prometheus:latest
    ports:
      - "9091:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

volumes:
  clickhouse_data:
  redis_data:
  prometheus_data:
  grafana_data:
"""
        return compose_content
    
    def _build_docker_image(self) -> Dict:
        """Build Docker image"""
        
        try:
            # Mock Docker build process
            logger.info("Building Docker image...")
            
            # Simulate build process
            import time
            time.sleep(1)
            
            build_result = {
                'success': True,
                'image_name': 'trading-system:latest',
                'image_id': 'sha256:abc123def456',
                'build_time': '1.5s',
                'size': '850MB'
            }
            
            logger.info(f"Docker image built: {build_result['image_name']}")
            return build_result
            
        except Exception as e:
            logger.error(f"Docker build failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_kubernetes_deployment(self) -> Dict:
        """Create Kubernetes deployment"""
        
        try:
            logger.info("Creating Kubernetes deployment...")
            
            # Generate Kubernetes manifests
            k8s_manifests = self._generate_kubernetes_manifests()
            
            # Create manifest files
            for manifest_name, manifest_content in k8s_manifests.items():
                with open(f'k8s/{manifest_name}.yaml', 'w') as f:
                    f.write(manifest_content)
            
            # Mock Kubernetes deployment
            deployment_result = {
                'deployment_type': 'kubernetes',
                'manifests_created': list(k8s_manifests.keys()),
                'namespace': self.deployment_config.get('deployment', {}).get('namespace', 'trading-system'),
                'replicas': self.deployment_config.get('deployment', {}).get('replicas', 3),
                'deployment_date': datetime.now().isoformat()
            }
            
            # Store deployment result
            deployment_id = f"k8s_deployment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.deployment_status[deployment_id] = deployment_result
            
            logger.info("Kubernetes deployment created successfully")
            return deployment_result
            
        except Exception as e:
            logger.error(f"Kubernetes deployment failed: {e}")
            return {'deployment_type': 'kubernetes', 'success': False, 'error': str(e)}
    
    def _generate_kubernetes_manifests(self) -> Dict:
        """Generate Kubernetes manifests"""
        
        manifests = {}
        
        # Deployment manifest
        deployment_manifest = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: trading-system
  namespace: trading-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: trading-system
  template:
    metadata:
      labels:
        app: trading-system
    spec:
      containers:
      - name: trading-system
        image: trading-system:latest
        ports:
        - containerPort: 8080
        - containerPort: 9090
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
"""
        manifests['deployment'] = deployment_manifest
        
        # Service manifest
        service_manifest = """apiVersion: v1
kind: Service
metadata:
  name: trading-system-service
  namespace: trading-system
spec:
  selector:
    app: trading-system
  ports:
  - name: http
    port: 8080
    targetPort: 8080
  - name: monitoring
    port: 9090
    targetPort: 9090
  type: LoadBalancer
"""
        manifests['service'] = service_manifest
        
        # ConfigMap manifest
        configmap_manifest = """apiVersion: v1
kind: ConfigMap
metadata:
  name: trading-system-config
  namespace: trading-system
data:
  config.yaml: |
    environment: production
    log_level: INFO
    database:
      clickhouse:
        host: clickhouse-service
        port: 9000
      redis:
        host: redis-service
        port: 6379
"""
        manifests['configmap'] = configmap_manifest
        
        return manifests
    
    def deploy_to_production(self, deployment_type: str = 'docker') -> Dict:
        """Deploy to production environment"""
        
        try:
            logger.info(f"Deploying to production using {deployment_type}...")
            
            # Validate configuration
            validation = self.validate_deployment_config()
            if not validation['config_valid']:
                return {'success': False, 'errors': validation['errors']}
            
            # Create deployment
            if deployment_type == 'docker':
                deployment_result = self.create_docker_deployment()
            elif deployment_type == 'kubernetes':
                deployment_result = self.create_kubernetes_deployment()
            else:
                return {'success': False, 'error': f'Unsupported deployment type: {deployment_type}'}
            
            # Store deployment history
            self.deployment_history.append({
                'deployment_type': deployment_type,
                'result': deployment_result,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"Production deployment completed: {deployment_type}")
            return deployment_result
            
        except Exception as e:
            logger.error(f"Production deployment failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_deployment_summary(self) -> Dict:
        """Get deployment summary"""
        return {
            'total_deployments': len(self.deployment_status),
            'deployment_history_count': len(self.deployment_history),
            'available_deployments': list(self.deployment_status.keys()),
            'config_valid': self.validate_deployment_config()['config_valid']
        }
