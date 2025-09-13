#!/bin/bash

# Autonomous AI Assistant Deployment Script
# This script automates the setup and deployment process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Docker and Docker Compose
check_dependencies() {
    print_step "Checking system dependencies..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        echo "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    print_status "✓ Docker and Docker Compose are available"
}

# Function to setup environment file
setup_environment() {
    print_step "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_status "✓ Created .env file from template"
            print_warning "Please edit .env file with your API keys and configurations"
        else
            print_error ".env.example file not found"
            exit 1
        fi
    else
        print_status "✓ .env file already exists"
    fi
}

# Function to create necessary directories
create_directories() {
    print_step "Creating necessary directories..."
    
    directories=(
        "data"
        "data/faiss_index"
        "data/logs"
        "data/output"
        "data/uploads"
        "data/output/visualizations"
        "logs"
        "n8n_data"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_status "✓ Created directory: $dir"
        fi
    done
    
    # Set proper permissions
    chmod -R 755 data/
    chmod -R 755 logs/
}

# Function to build and start services
deploy_services() {
    print_step "Building and starting services..."
    
    # Pull latest images and build
    print_status "Pulling Docker images and building application..."
    docker-compose pull
    docker-compose build --no-cache
    
    # Start services
    print_status "Starting services..."
    docker-compose up -d
    
    print_status "✓ Services started successfully"
}

# Function to wait for services to be ready
wait_for_services() {
    print_step "Waiting for services to be ready..."
    
    # Wait for Flask app
    print_status "Waiting for Flask application..."
    for i in {1..30}; do
        if curl -s http://localhost:5000/health >/dev/null 2>&1; then
            break
        fi
        echo -n "."
        sleep 2
    done
    echo
    
    if curl -s http://localhost:5000/health >/dev/null 2>&1; then
        print_status "✓ Flask application is ready"
    else
        print_warning "Flask application may not be fully ready yet"
    fi
    
    # Wait for n8n
    print_status "Waiting for n8n workflow engine..."
    for i in {1..20}; do
        if curl -s http://localhost:5678 >/dev/null 2>&1; then
            break
        fi
        echo -n "."
        sleep 3
    done
    echo
    
    if curl -s http://localhost:5678 >/dev/null 2>&1; then
        print_status "✓ n8n workflow engine is ready"
    else
        print_warning "n8n may not be fully ready yet"
    fi
}

# Function to run initial tests
run_initial_tests() {
    print_step "Running initial system tests..."
    
    # Test health endpoint
    if curl -s http://localhost:5000/health | grep -q "healthy"; then
        print_status "✓ Health check passed"
    else
        print_warning "Health check may have issues"
    fi
    
    # Test NLP processing
    response=$(curl -s -X POST http://localhost:5000/process \
        -H "Content-Type: application/json" \
        -d '{"command": "Create a test folder"}' 2>/dev/null)
    
    if echo "$response" | grep -q "File Management"; then
        print_status "✓ NLP processing test passed"
    else
        print_warning "NLP processing test may have issues"
    fi
}

# Function to setup sample data
setup_sample_data() {
    print_step "Setting up sample data..."
    
    # Create sample CSV for data analysis testing
    cat > data/output/sample_data.csv << EOF
Name,Age,Department,Salary,Performance_Rating
John Doe,28,Engineering,75000,4.2
Jane Smith,32,Marketing,68000,4.5
Mike Johnson,25,Engineering,72000,3.8
Sarah Wilson,29,Sales,71000,4.1
David Brown,35,Management,95000,4.7
Lisa Garcia,27,Marketing,66000,4.0
Tom Anderson,31,Engineering,78000,4.3
Emily Davis,26,Sales,69000,3.9
Chris Martinez,33,Management,92000,4.6
Amanda Taylor,30,Engineering,76000,4.2
EOF
    
    print_status "✓ Created sample CSV file for testing"
    
    # Add some context to RAG system
    curl -s -X POST http://localhost:5000/add_context \
        -H "Content-Type: application/json" \
        -d '{"text": "The Autonomous AI Assistant is a comprehensive system for task automation using NLP and RAG technologies."}' >/dev/null 2>&1
    
    curl -s -X POST http://localhost:5000/add_context \
        -H "Content-Type: application/json" \
        -d '{"text": "The system supports file management, email handling, calendar scheduling, and data analysis operations."}' >/dev/null 2>&1
    
    print_status "✓ Added sample context to RAG system"
}

# Function to display deployment summary
show_deployment_summary() {
    print_step "Deployment Summary"
    echo
    echo "🎉 Autonomous AI Assistant deployed successfully!"
    echo
    echo "📋 Available Services:"
    echo "  • Main Application:    http://localhost:5000"
    echo "  • n8n Workflows:       http://localhost:5678"
    echo "  • Health Check:        http://localhost:5000/health"
    echo "  • API Documentation:   http://localhost:5000 (see endpoint list)"
    echo
    echo "🧪 Quick Tests:"
    echo "  • Test NLP:     curl -X POST http://localhost:5000/process -H 'Content-Type: application/json' -d '{\"command\": \"Create a folder named TestFolder\"}'"
    echo "  • Test Files:   curl -X POST http://localhost:5000/execute/file_management -H 'Content-Type: application/json' -d '{\"action\": \"list_files\"}'"
    echo "  • Test Data:    curl -X POST http://localhost:5000/execute/data_analysis -H 'Content-Type: application/json' -d '{\"action\": \"quick_summary\", \"parameters\": {\"file_path\": \"/usr/src/app/data/output/sample_data.csv\"}}'"
    echo
    echo "📁 Important Directories:"
    echo "  • Output Files:   ./data/output/"
    echo "  • Logs:          ./logs/"
    echo "  • Uploads:       ./data/uploads/"
    echo
    echo "🔧 Management Commands:"
    echo "  • View Logs:     docker-compose logs -f"
    echo "  • Stop:          docker-compose down"
    echo "  • Restart:       docker-compose restart"
    echo "  • Update:        ./deploy.sh --update"
    echo
    echo "📖 For detailed documentation, see DOCUMENTATION.md"
    echo
}

# Function to show usage
show_usage() {
    echo "Autonomous AI Assistant Deployment Script"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --help, -h          Show this help message"
    echo "  --update, -u        Update existing deployment"
    echo "  --clean, -c         Clean deployment (remove containers and volumes)"
    echo "  --dev, -d           Development mode (with hot reload)"
    echo "  --no-test          Skip initial tests"
    echo "  --no-sample-data   Skip sample data setup"
    echo
    echo "Examples:"
    echo "  $0                  # Full deployment"
    echo "  $0 --update         # Update existing deployment"
    echo "  $0 --clean          # Clean everything and redeploy"
    echo "  $0 --dev            # Development mode"
    echo
}

# Function to clean deployment
clean_deployment() {
    print_step "Cleaning existing deployment..."
    
    print_status "Stopping and removing containers..."
    docker-compose down -v
    
    print_status "Removing Docker images..."
    docker-compose down --rmi all 2>/dev/null || true
    
    print_status "Cleaning up data directories..."
    rm -rf data/faiss_index/*
    rm -rf data/logs/*
    rm -rf n8n_data/*
    
    print_status "✓ Cleanup completed"
}

# Function to update deployment
update_deployment() {
    print_step "Updating deployment..."
    
    print_status "Pulling latest changes..."
    docker-compose pull
    
    print_status "Rebuilding services..."
    docker-compose build --no-cache
    
    print_status "Restarting services..."
    docker-compose up -d
    
    wait_for_services
    print_status "✓ Update completed"
}

# Function to development mode
dev_deployment() {
    print_step "Starting in development mode..."
    
    # Use development docker-compose override if it exists
    if [ -f "docker-compose.dev.yml" ]; then
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
    else
        print_warning "docker-compose.dev.yml not found, using regular deployment"
        docker-compose up --build
    fi
}

# Main deployment function
main_deployment() {
    local skip_tests=false
    local skip_sample_data=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-test)
                skip_tests=true
                shift
                ;;
            --no-sample-data)
                skip_sample_data=true
                shift
                ;;
            *)
                break
                ;;
        esac
    done
    
    check_dependencies
    setup_environment
    create_directories
    deploy_services
    wait_for_services
    
    if [ "$skip_sample_data" = false ]; then
        setup_sample_data
    fi
    
    if [ "$skip_tests" = false ]; then
        run_initial_tests
    fi
    
    show_deployment_summary
}

# Main script logic
main() {
    case "${1:-}" in
        --help|-h)
            show_usage
            ;;
        --clean|-c)
            clean_deployment
            main_deployment "${@:2}"
            ;;
        --update|-u)
            update_deployment
            ;;
        --dev|-d)
            check_dependencies
            setup_environment
            create_directories
            dev_deployment
            ;;
        *)
            main_deployment "$@"
            ;;
    esac
}

# Script header
echo "=================================================="
echo "   Autonomous AI Assistant Deployment Script"
echo "=================================================="
echo

# Run main function with all arguments
main "$@"