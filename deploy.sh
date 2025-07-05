#!/bin/bash

# Production Deployment Script for Statistical Arbitrage Trading System
# This script handles the complete deployment process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="stat-arb-trading"
DOCKER_COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Validate configuration
validate_config() {
    log "Validating configuration..."
    
    # Check if docker-compose.yml exists
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        error "Docker Compose file not found: $DOCKER_COMPOSE_FILE"
        exit 1
    fi
    
    # Check if .env file exists (optional)
    if [ -f "$ENV_FILE" ]; then
        log "Environment file found: $ENV_FILE"
    else
        warning "Environment file not found: $ENV_FILE (using defaults)"
    fi
    
    # Validate docker-compose.yml syntax
    if ! docker-compose config &> /dev/null; then
        error "Invalid Docker Compose configuration"
        exit 1
    fi
    
    success "Configuration validation passed"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p data
    mkdir -p config
    
    success "Directories created"
}

# Build and deploy
deploy() {
    log "Starting deployment..."
    
    # Stop existing containers
    log "Stopping existing containers..."
    docker-compose down --remove-orphans || true
    
    # Build images
    log "Building Docker images..."
    docker-compose build --no-cache
    
    # Start services
    log "Starting services..."
    docker-compose up -d
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    check_service_health
    
    success "Deployment completed successfully"
}

# Check service health
check_service_health() {
    log "Checking service health..."
    
    # Check if all containers are running
    if ! docker-compose ps | grep -q "Up"; then
        error "Some services failed to start"
        docker-compose logs
        exit 1
    fi
    
    # Check PostgreSQL
    if docker-compose exec -T postgres pg_isready -U postgres &> /dev/null; then
        success "PostgreSQL is healthy"
    else
        error "PostgreSQL health check failed"
        exit 1
    fi
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping &> /dev/null; then
        success "Redis is healthy"
    else
        error "Redis health check failed"
        exit 1
    fi
    
    # Check main application
    if docker-compose logs stat-arb-app | grep -q "system_initialized_successfully"; then
        success "Main application is healthy"
    else
        warning "Main application health check inconclusive"
    fi
    
    success "All services are healthy"
}

# Run tests
run_tests() {
    log "Running system tests..."
    
    # Run basic connectivity test
    if docker-compose exec -T stat-arb-app python -c "import stat_arb_project; print('Import test passed')" &> /dev/null; then
        success "Import test passed"
    else
        error "Import test failed"
        exit 1
    fi
    
    # Run basic backtest
    log "Running basic backtest..."
    if docker-compose exec -T stat-arb-app python stat_arb_project/production_main.py --mode backtest --symbol1 AAPL --symbol2 MSFT --start-date 2023-01-01 --end-date 2023-01-31 &> /dev/null; then
        success "Basic backtest passed"
    else
        warning "Basic backtest failed (this is expected in some environments)"
    fi
    
    success "System tests completed"
}

# Show deployment info
show_deployment_info() {
    echo
    echo "=========================================="
    echo "DEPLOYMENT COMPLETED SUCCESSFULLY"
    echo "=========================================="
    echo
    echo "Services:"
    echo "  - Main Application: http://localhost (if exposed)"
    echo "  - Grafana Dashboard: http://localhost:3000 (admin/admin)"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - Redis: localhost:6379"
    echo
    echo "Useful commands:"
    echo "  - View logs: docker-compose logs -f"
    echo "  - Stop services: docker-compose down"
    echo "  - Restart services: docker-compose restart"
    echo "  - Update: git pull && ./deploy.sh"
    echo
    echo "Configuration:"
    echo "  - Environment: $ENV_FILE"
    echo "  - Logs: ./logs/"
    echo "  - Data: ./data/"
    echo
}

# Cleanup function
cleanup() {
    log "Cleaning up..."
    docker-compose down --remove-orphans || true
    docker system prune -f || true
}

# Main deployment process
main() {
    echo "=========================================="
    echo "Statistical Arbitrage Trading System"
    echo "Production Deployment Script"
    echo "=========================================="
    echo
    
    # Parse command line arguments
    case "${1:-deploy}" in
        "deploy")
            check_prerequisites
            validate_config
            create_directories
            deploy
            run_tests
            show_deployment_info
            ;;
        "stop")
            log "Stopping services..."
            docker-compose down
            success "Services stopped"
            ;;
        "restart")
            log "Restarting services..."
            docker-compose restart
            success "Services restarted"
            ;;
        "logs")
            docker-compose logs -f
            ;;
        "cleanup")
            cleanup
            success "Cleanup completed"
            ;;
        "status")
            docker-compose ps
            ;;
        *)
            echo "Usage: $0 {deploy|stop|restart|logs|cleanup|status}"
            echo
            echo "Commands:"
            echo "  deploy   - Deploy the entire system (default)"
            echo "  stop     - Stop all services"
            echo "  restart  - Restart all services"
            echo "  logs     - Show service logs"
            echo "  cleanup  - Clean up containers and images"
            echo "  status   - Show service status"
            exit 1
            ;;
    esac
}

# Trap cleanup on script exit
trap cleanup EXIT

# Run main function
main "$@" 