#!/bin/bash

# =============================================================================
# Kwamz AI Production Deployment Script
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
DOMAIN=${DOMAIN:-""}
EMAIL=${EMAIL:-""}
COMPOSE_FILE="docker-compose.prod.yml"

# =============================================================================
# Functions
# =============================================================================

check_requirements() {
    log_info "Checking requirements..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    log_success "All requirements met."
}

setup_environment() {
    log_info "Setting up environment..."

    if [ ! -f ".env.prod" ]; then
        log_warning ".env.prod not found. Creating from template..."
        cp .env.prod.example .env.prod
        log_warning "Please edit .env.prod with your production values!"
        exit 1
    fi

    # Source production environment
    set -a
    source .env.prod
    set +a

    log_success "Environment loaded."
}

setup_ssl_initial() {
    log_info "Setting up initial SSL certificates..."

    if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
        log_error "DOMAIN and EMAIL must be set in .env.prod"
        exit 1
    fi

    # Create directories
    mkdir -p certbot/conf certbot/www

    # Create temporary self-signed certificate for initial nginx startup
    if [ ! -f "certbot/conf/fullchain.pem" ]; then
        log_info "Creating temporary self-signed certificate..."
        mkdir -p certbot/conf
        openssl req -x509 -nodes -newkey rsa:4096 \
            -keyout certbot/conf/privkey.pem \
            -out certbot/conf/fullchain.pem \
            -days 1 \
            -subj "/CN=localhost"
    fi

    log_success "Initial SSL setup complete."
}

obtain_ssl_certificate() {
    log_info "Obtaining Let's Encrypt SSL certificate..."

    if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
        log_error "DOMAIN and EMAIL must be set in .env.prod"
        exit 1
    fi

    # Start nginx for ACME challenge
    docker compose -f $COMPOSE_FILE up -d nginx
    sleep 5

    # Obtain certificate
    docker compose -f $COMPOSE_FILE run --rm certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email $EMAIL \
        --agree-tos \
        --no-eff-email \
        -d $DOMAIN

    # Copy certificates to nginx ssl directory
    if [ -d "certbot/conf/live/$DOMAIN" ]; then
        cp certbot/conf/live/$DOMAIN/fullchain.pem certbot/conf/fullchain.pem
        cp certbot/conf/live/$DOMAIN/privkey.pem certbot/conf/privkey.pem
        log_success "SSL certificate obtained successfully!"
    else
        log_error "Failed to obtain SSL certificate"
        exit 1
    fi

    # Restart nginx with new certificate
    docker compose -f $COMPOSE_FILE restart nginx
}

deploy() {
    log_info "Starting deployment..."

    # Pull latest code (if in git repo)
    if [ -d ".git" ]; then
        log_info "Pulling latest code..."
        git pull origin main || true
    fi

    # Build and start services
    log_info "Building Docker images..."
    docker compose -f $COMPOSE_FILE build

    log_info "Starting services..."
    docker compose -f $COMPOSE_FILE up -d

    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 10

    # Show status
    docker compose -f $COMPOSE_FILE ps

    log_success "Deployment complete!"
}

backup_database() {
    log_info "Backing up database..."

    BACKUP_FILE="backups/db_backup_$(date +%Y%m%d_%H%M%S).sql"
    mkdir -p backups

    docker compose -f $COMPOSE_FILE exec -T db pg_dump -U postgres mpesaglobal > $BACKUP_FILE

    # Compress backup
    gzip $BACKUP_FILE

    log_success "Database backed up to ${BACKUP_FILE}.gz"
}

restore_database() {
    if [ -z "$1" ]; then
        log_error "Please provide backup file path"
        exit 1
    fi

    log_warning "This will overwrite the current database. Are you sure? (y/N)"
    read -r response
    if [ "$response" != "y" ]; then
        log_info "Restore cancelled."
        exit 0
    fi

    log_info "Restoring database from $1..."

    if [[ $1 == *.gz ]]; then
        gunzip -c $1 | docker compose -f $COMPOSE_FILE exec -T db psql -U postgres mpesaglobal
    else
        docker compose -f $COMPOSE_FILE exec -T db psql -U postgres mpesaglobal < $1
    fi

    log_success "Database restored."
}

show_logs() {
    SERVICE=${1:-""}
    if [ -n "$SERVICE" ]; then
        docker compose -f $COMPOSE_FILE logs -f $SERVICE
    else
        docker compose -f $COMPOSE_FILE logs -f
    fi
}

stop() {
    log_info "Stopping all services..."
    docker compose -f $COMPOSE_FILE down
    log_success "All services stopped."
}

restart() {
    log_info "Restarting services..."
    docker compose -f $COMPOSE_FILE restart
    log_success "Services restarted."
}

status() {
    docker compose -f $COMPOSE_FILE ps
}

cleanup() {
    log_warning "This will remove unused Docker resources. Continue? (y/N)"
    read -r response
    if [ "$response" = "y" ]; then
        docker system prune -af
        docker volume prune -f
        log_success "Cleanup complete."
    fi
}

# =============================================================================
# Main
# =============================================================================

show_help() {
    echo "Kwamz AI Deployment Script"
    echo ""
    echo "Usage: ./deploy.sh [command]"
    echo ""
    echo "Commands:"
    echo "  deploy          Full deployment (build and start all services)"
    echo "  setup-ssl       Initial SSL setup with Let's Encrypt"
    echo "  renew-ssl       Renew SSL certificate"
    echo "  backup          Backup PostgreSQL database"
    echo "  restore [file]  Restore database from backup"
    echo "  logs [service]  Show logs (optionally for specific service)"
    echo "  status          Show service status"
    echo "  stop            Stop all services"
    echo "  restart         Restart all services"
    echo "  cleanup         Remove unused Docker resources"
    echo "  help            Show this help message"
    echo ""
    echo "Environment variables (set in .env.prod):"
    echo "  DOMAIN          Your domain name (e.g., app.example.com)"
    echo "  EMAIL           Email for Let's Encrypt notifications"
}

case "${1:-deploy}" in
    deploy)
        check_requirements
        setup_environment
        setup_ssl_initial
        deploy
        ;;
    setup-ssl)
        check_requirements
        setup_environment
        obtain_ssl_certificate
        ;;
    renew-ssl)
        docker compose -f $COMPOSE_FILE run --rm certbot renew
        docker compose -f $COMPOSE_FILE restart nginx
        ;;
    backup)
        backup_database
        ;;
    restore)
        restore_database "$2"
        ;;
    logs)
        show_logs "$2"
        ;;
    status)
        status
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
