#!/bin/bash

# =============================================================================
# DigitalOcean Server Setup Script
# Run this on a fresh Ubuntu 22.04/24.04 droplet
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
APP_USER="deploy"
APP_DIR="/home/$APP_USER/kwamz-ai"

# =============================================================================
# System Setup
# =============================================================================

setup_system() {
    log_info "Updating system packages..."
    apt-get update && apt-get upgrade -y

    log_info "Installing required packages..."
    apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        git \
        ufw \
        fail2ban \
        htop \
        unzip

    log_success "System packages installed."
}

# =============================================================================
# Docker Installation
# =============================================================================

install_docker() {
    log_info "Installing Docker..."

    # Remove old versions
    apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Set up repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Start and enable Docker
    systemctl start docker
    systemctl enable docker

    log_success "Docker installed successfully."
}

# =============================================================================
# Create Deploy User
# =============================================================================

create_deploy_user() {
    log_info "Creating deploy user..."

    if id "$APP_USER" &>/dev/null; then
        log_warning "User $APP_USER already exists."
    else
        useradd -m -s /bin/bash $APP_USER
        usermod -aG docker $APP_USER
        log_success "User $APP_USER created."
    fi

    # Create app directory
    mkdir -p $APP_DIR
    chown -R $APP_USER:$APP_USER /home/$APP_USER

    log_success "Deploy user configured."
}

# =============================================================================
# SSH Configuration
# =============================================================================

configure_ssh() {
    log_info "Configuring SSH..."

    # Create .ssh directory for deploy user
    mkdir -p /home/$APP_USER/.ssh
    chmod 700 /home/$APP_USER/.ssh

    # Copy authorized_keys from root to deploy user
    if [ -f /root/.ssh/authorized_keys ]; then
        cp /root/.ssh/authorized_keys /home/$APP_USER/.ssh/
        chmod 600 /home/$APP_USER/.ssh/authorized_keys
        chown -R $APP_USER:$APP_USER /home/$APP_USER/.ssh
    fi

    # Harden SSH configuration
    cat > /etc/ssh/sshd_config.d/hardening.conf << EOF
# Disable root login
PermitRootLogin no

# Disable password authentication
PasswordAuthentication no

# Only allow specific users
AllowUsers $APP_USER

# Connection settings
MaxAuthTries 3
LoginGraceTime 60
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

    log_warning "SSH will be hardened. Make sure you have your SSH key configured!"
    log_warning "Run: ssh-copy-id -i ~/.ssh/id_rsa.pub $APP_USER@<server-ip>"

    log_success "SSH configured."
}

# =============================================================================
# Firewall Configuration
# =============================================================================

configure_firewall() {
    log_info "Configuring firewall..."

    ufw default deny incoming
    ufw default allow outgoing

    # Allow SSH
    ufw allow 22/tcp

    # Allow HTTP and HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp

    # Enable firewall
    echo "y" | ufw enable

    log_success "Firewall configured."
}

# =============================================================================
# Fail2Ban Configuration
# =============================================================================

configure_fail2ban() {
    log_info "Configuring Fail2Ban..."

    cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s
maxretry = 3
bantime = 24h
EOF

    systemctl restart fail2ban
    systemctl enable fail2ban

    log_success "Fail2Ban configured."
}

# =============================================================================
# Swap Configuration
# =============================================================================

configure_swap() {
    log_info "Configuring swap..."

    # Check if swap exists
    if [ -f /swapfile ]; then
        log_warning "Swap already exists."
        return
    fi

    # Create 2GB swap
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile

    # Make permanent
    echo '/swapfile none swap sw 0 0' >> /etc/fstab

    # Optimize swap settings
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
    echo 'vm.vfs_cache_pressure=50' >> /etc/sysctl.conf
    sysctl -p

    log_success "Swap configured."
}

# =============================================================================
# Application Setup
# =============================================================================

setup_application() {
    log_info "Setting up application directory..."

    # Create necessary directories
    sudo -u $APP_USER mkdir -p $APP_DIR/{nginx,certbot/conf,certbot/www,backups}

    # Create initial self-signed certificate for nginx to start
    if [ ! -f "$APP_DIR/certbot/conf/fullchain.pem" ]; then
        openssl req -x509 -nodes -newkey rsa:4096 \
            -keyout $APP_DIR/certbot/conf/privkey.pem \
            -out $APP_DIR/certbot/conf/fullchain.pem \
            -days 1 \
            -subj "/CN=localhost"
        chown -R $APP_USER:$APP_USER $APP_DIR/certbot
    fi

    # Create .env.prod template
    cat > $APP_DIR/.env.prod << EOF
# Production Environment Configuration
# Update these values!

DOMAIN=your-domain.com
EMAIL=your-email@example.com

POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
MINIO_BUCKET=kwamz-files

FLASK_SECRET_KEY=$(openssl rand -base64 64 | tr -dc 'a-zA-Z0-9' | head -c 64)
JWT_SECRET_KEY=$(openssl rand -base64 64 | tr -dc 'a-zA-Z0-9' | head -c 64)

# GitHub Container Registry
GITHUB_REPOSITORY=your-github-username/your-repo-name
EOF

    chown $APP_USER:$APP_USER $APP_DIR/.env.prod
    chmod 600 $APP_DIR/.env.prod

    log_success "Application directory configured."
    log_warning "Don't forget to update $APP_DIR/.env.prod with your values!"
}

# =============================================================================
# Automatic Updates
# =============================================================================

configure_auto_updates() {
    log_info "Configuring automatic security updates..."

    apt-get install -y unattended-upgrades

    cat > /etc/apt/apt.conf.d/20auto-upgrades << EOF
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

    log_success "Automatic updates configured."
}

# =============================================================================
# Cron Jobs
# =============================================================================

setup_cron_jobs() {
    log_info "Setting up cron jobs..."

    # Create backup script
    cat > $APP_DIR/backup.sh << 'EOF'
#!/bin/bash
cd ~/kwamz-ai
BACKUP_FILE="backups/db_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres mpesaglobal | gzip > $BACKUP_FILE
# Keep only last 7 days of backups
find backups/ -name "*.sql.gz" -mtime +7 -delete
EOF

    chmod +x $APP_DIR/backup.sh
    chown $APP_USER:$APP_USER $APP_DIR/backup.sh

    # Add cron job for deploy user
    sudo -u $APP_USER bash -c "(crontab -l 2>/dev/null; echo '0 3 * * * ~/kwamz-ai/backup.sh') | crontab -"

    # SSL renewal cron
    (crontab -l 2>/dev/null; echo "0 0 * * * docker compose -f $APP_DIR/docker-compose.prod.yml run --rm certbot renew && docker compose -f $APP_DIR/docker-compose.prod.yml restart nginx") | crontab -

    log_success "Cron jobs configured."
}

# =============================================================================
# Print Summary
# =============================================================================

print_summary() {
    echo ""
    echo "============================================================================="
    echo -e "${GREEN}Server Setup Complete!${NC}"
    echo "============================================================================="
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Copy your SSH key to the deploy user:"
    echo "   ssh-copy-id -i ~/.ssh/id_rsa.pub $APP_USER@$(curl -s ifconfig.me)"
    echo ""
    echo "2. Update the environment file:"
    echo "   nano $APP_DIR/.env.prod"
    echo ""
    echo "3. Add GitHub secrets in your repository:"
    echo "   DO_HOST: $(curl -s ifconfig.me)"
    echo "   DO_USERNAME: $APP_USER"
    echo "   DO_SSH_KEY: <your private SSH key>"
    echo ""
    echo "4. Push to main branch to trigger deployment"
    echo ""
    echo "5. After first deployment, get SSL certificate:"
    echo "   cd $APP_DIR && ./deploy.sh setup-ssl"
    echo ""
    echo "============================================================================="
}

# =============================================================================
# Main
# =============================================================================

main() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run as root"
        exit 1
    fi

    log_info "Starting server setup..."

    setup_system
    install_docker
    create_deploy_user
    configure_ssh
    configure_firewall
    configure_fail2ban
    configure_swap
    setup_application
    configure_auto_updates
    setup_cron_jobs

    print_summary
}

main "$@"
