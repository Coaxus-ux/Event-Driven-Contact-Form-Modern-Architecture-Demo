#!/bin/bash

# Event-Driven PoC Test Runner
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if pytest is available
check_pytest() {
    if ! command -v pytest > /dev/null 2>&1; then
        print_error "pytest is not installed. Installing pytest..."
        pip install pytest pytest-cov pytest-html
    fi
    print_success "pytest is available"
}

# Function to install test dependencies
install_test_dependencies() {
    print_status "Installing test dependencies..."
    
    # Create requirements-test.txt if it doesn't exist
    if [ ! -f requirements-test.txt ]; then
        cat > requirements-test.txt << EOF
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-html>=3.1.0
pytest-mock>=3.10.0
requests>=2.28.0
kafka-python>=2.0.2
selenium>=4.0.0
EOF
    fi
    
    pip install -r requirements-test.txt
    print_success "Test dependencies installed"
}

# Function to run unit tests
run_unit_tests() {
    print_status "Running unit tests..."
    
    # API unit tests
    if [ -d "api/tests" ]; then
        print_status "Running API unit tests..."
        cd api
        python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing
        cd ..
    fi
    
    # Mailer service unit tests
    if [ -d "mailer-service/tests" ]; then
        print_status "Running Mailer service unit tests..."
        cd mailer-service
        python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing
        cd ..
    fi
    
    # Workflow agent unit tests
    if [ -d "workflow-agent/tests" ]; then
        print_status "Running Workflow Agent unit tests..."
        cd workflow-agent
        python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing
        cd ..
    fi
    
    print_success "Unit tests completed"
}

# Function to run integration tests
run_integration_tests() {
    print_status "Running integration tests..."
    
    # Check if services are running
    if ! curl -f http://localhost:5000/health > /dev/null 2>&1; then
        print_warning "API service not running. Some integration tests may be skipped."
    fi
    
    if ! curl -f http://localhost:9092 > /dev/null 2>&1; then
        print_warning "Kafka not running. Some integration tests may be skipped."
    fi
    
    python -m pytest tests/integration/ -v --tb=short
    
    print_success "Integration tests completed"
}

# Function to run end-to-end tests
run_e2e_tests() {
    print_status "Running end-to-end tests..."
    
    # Check if services are running
    services_running=true
    
    if ! curl -f http://localhost:3000 > /dev/null 2>&1; then
        print_warning "Frontend service not running. E2E tests may fail."
        services_running=false
    fi
    
    if ! curl -f http://localhost:5000/health > /dev/null 2>&1; then
        print_warning "API service not running. E2E tests may fail."
        services_running=false
    fi
    
    if [ "$services_running" = false ]; then
        print_warning "Some services are not running. Consider running './deploy.sh start' first."
        read -p "Continue with E2E tests anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Skipping E2E tests"
            return
        fi
    fi
    
    python -m pytest tests/e2e/ -v --tb=short
    
    print_success "End-to-end tests completed"
}

# Function to run all tests with coverage
run_all_tests_with_coverage() {
    print_status "Running all tests with coverage report..."
    
    # Create coverage configuration
    cat > .coveragerc << EOF
[run]
source = .
omit = 
    */tests/*
    */venv/*
    */env/*
    */__pycache__/*
    */migrations/*
    */node_modules/*
    */dist/*
    */build/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    class .*\(Protocol\):
    @(abc\.)?abstractmethod

[html]
directory = htmlcov
EOF
    
    # Run tests with coverage
    python -m pytest \
        api/tests/ \
        mailer-service/tests/ \
        workflow-agent/tests/ \
        tests/integration/ \
        tests/e2e/ \
        -v \
        --tb=short \
        --cov=. \
        --cov-report=html \
        --cov-report=term-missing \
        --html=test-report.html \
        --self-contained-html
    
    print_success "All tests completed with coverage report"
    print_status "Coverage report: htmlcov/index.html"
    print_status "Test report: test-report.html"
}

# Function to run quick smoke tests
run_smoke_tests() {
    print_status "Running smoke tests..."
    
    # Basic connectivity tests
    echo "Testing service connectivity..."
    
    # Test API
    if curl -f http://localhost:5000/health > /dev/null 2>&1; then
        print_success "API service is healthy"
    else
        print_error "API service is not reachable"
    fi
    
    # Test Frontend
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        print_success "Frontend service is reachable"
    else
        print_error "Frontend service is not reachable"
    fi
    
    # Test Kafka UI
    if curl -f http://localhost:8080 > /dev/null 2>&1; then
        print_success "Kafka UI is reachable"
    else
        print_warning "Kafka UI is not reachable"
    fi
    
    # Run basic API test
    print_status "Testing API endpoint..."
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health)
    if [ "$response" = "200" ]; then
        print_success "API health endpoint working"
    else
        print_error "API health endpoint returned: $response"
    fi
    
    print_success "Smoke tests completed"
}

# Function to clean test artifacts
clean_test_artifacts() {
    print_status "Cleaning test artifacts..."
    
    # Remove coverage files
    rm -rf .coverage htmlcov/ .pytest_cache/
    rm -f test-report.html .coveragerc
    
    # Remove Python cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    
    print_success "Test artifacts cleaned"
}

# Function to show test help
show_help() {
    echo "Event-Driven PoC Test Runner"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  unit           Run unit tests only"
    echo "  integration    Run integration tests only"
    echo "  e2e            Run end-to-end tests only"
    echo "  all            Run all tests with coverage"
    echo "  smoke          Run quick smoke tests"
    echo "  install-deps   Install test dependencies"
    echo "  clean          Clean test artifacts"
    echo "  help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 unit                # Run unit tests"
    echo "  $0 smoke               # Quick connectivity tests"
    echo "  $0 all                 # Full test suite with coverage"
    echo ""
    echo "Prerequisites:"
    echo "  - Python 3.11+ with pip"
    echo "  - Services running (for integration/e2e tests)"
    echo "  - Chrome/Chromium (for E2E tests with Selenium)"
}

# Main script logic
case "$1" in
    "unit")
        check_pytest
        run_unit_tests
        ;;
    "integration")
        check_pytest
        run_integration_tests
        ;;
    "e2e")
        check_pytest
        run_e2e_tests
        ;;
    "all")
        check_pytest
        run_all_tests_with_coverage
        ;;
    "smoke")
        run_smoke_tests
        ;;
    "install-deps")
        install_test_dependencies
        ;;
    "clean")
        clean_test_artifacts
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    "")
        print_status "Running default test suite (unit + integration)..."
        check_pytest
        run_unit_tests
        run_integration_tests
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac

