#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }

mkdir -p "$LOG_DIR"

if [ "${1}" = "stop" ]; then
    info "Stopping services..."
    docker compose -f "$SCRIPT_DIR/docker-compose.deploy.yml" down
    success "All services stopped."
    exit 0
fi

# Start all Docker services (frontend + redis + celery + backend with Xvfb)
info "Starting Docker services..."
docker compose -f "$SCRIPT_DIR/docker-compose.deploy.yml" up --build -d
success "All services running on port 80."
info "Backend logs:  docker compose -f docker-compose.deploy.yml logs -f backend"
info "Scraper logs:  tail -f $LOG_DIR/scraper.log"
echo ""
success "To stop: ./start.sh stop"
