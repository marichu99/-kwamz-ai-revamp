# Kwamz AI - Deployment Guide

This guide covers setting up CI/CD with GitHub Actions and deploying to DigitalOcean.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [DigitalOcean Setup](#digitalocean-setup)
3. [GitHub Repository Setup](#github-repository-setup)
4. [First Deployment](#first-deployment)
5. [SSL Certificate Setup](#ssl-certificate-setup)
6. [Maintenance](#maintenance)

---

## Prerequisites

- GitHub account with your repository
- DigitalOcean account
- Domain name (optional but recommended)
- SSH key pair on your local machine

---

## DigitalOcean Setup

### Step 1: Create a Droplet

1. Log in to [DigitalOcean](https://cloud.digitalocean.com)

2. Click **Create** → **Droplets**

3. Configure your droplet:
   - **Region**: Choose closest to your users
   - **Image**: Ubuntu 24.04 LTS
   - **Size**: Basic → Regular → **$24/mo** (4GB RAM, 2 vCPU)
     - Minimum for this stack with Celery workers
   - **Authentication**: SSH Key (recommended)
   - **Hostname**: `kwamz-ai-prod`

4. Click **Create Droplet**

5. Note the IP address

### Step 2: Point Your Domain (Optional)

1. In DigitalOcean, go to **Networking** → **Domains**

2. Add your domain and create:
   - **A Record**: `@` → Your Droplet IP
   - **A Record**: `www` → Your Droplet IP

### Step 3: Initial Server Setup

SSH into your server and run the setup script:

```bash
# SSH as root
ssh root@YOUR_DROPLET_IP

# Download and run setup script
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/scripts/setup-server.sh | bash
```

Or manually:

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Create deploy user
useradd -m -s /bin/bash deploy
usermod -aG docker deploy

# Setup SSH for deploy user
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
```

### Step 4: Configure SSH Access

On your **local machine**:

```bash
# Copy your SSH key to the deploy user
ssh-copy-id -i ~/.ssh/id_rsa deploy@YOUR_DROPLET_IP

# Test connection
ssh deploy@YOUR_DROPLET_IP
```

---

## GitHub Repository Setup

### Step 1: Add Repository Secrets

Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**

Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `DO_HOST` | Your Droplet IP address |
| `DO_USERNAME` | `deploy` |
| `DO_SSH_KEY` | Your private SSH key (contents of `~/.ssh/id_rsa`) |

To get your private key:
```bash
cat ~/.ssh/id_rsa
```

### Step 2: Create Production Environment

1. Go to **Settings** → **Environments**
2. Click **New environment**
3. Name it `production`
4. (Optional) Add protection rules:
   - Required reviewers
   - Wait timer

### Step 3: Enable GitHub Container Registry

The workflow uses GitHub Container Registry (ghcr.io) to store Docker images.

1. Go to your GitHub **Profile** → **Settings** → **Developer settings**
2. Click **Personal access tokens** → **Tokens (classic)**
3. Generate new token with:
   - `write:packages`
   - `read:packages`
   - `delete:packages`

---

## First Deployment

### Step 1: Prepare Server

SSH into your server as the deploy user:

```bash
ssh deploy@YOUR_DROPLET_IP
cd ~/kwamz-ai
```

Edit the environment file:

```bash
nano .env.prod
```

Update these values:
```env
DOMAIN=your-domain.com
EMAIL=your-email@example.com
GITHUB_REPOSITORY=your-username/your-repo
```

### Step 2: Push to Main Branch

On your local machine, commit and push:

```bash
git add .
git commit -m "Add CI/CD configuration"
git push origin main
```

This triggers the deployment workflow.

### Step 3: Monitor Deployment

1. Go to your repository → **Actions**
2. Watch the "Deploy to Production" workflow
3. Check for any errors

---

## SSL Certificate Setup

After the first deployment succeeds:

```bash
ssh deploy@YOUR_DROPLET_IP
cd ~/kwamz-ai

# Get Let's Encrypt certificate
./deploy.sh setup-ssl
```

---

## Maintenance

### View Logs

```bash
# All services
./deploy.sh logs

# Specific service
./deploy.sh logs backend
./deploy.sh logs celery-worker
```

### Backup Database

```bash
./deploy.sh backup
```

Backups are stored in `~/kwamz-ai/backups/`

### Restore Database

```bash
./deploy.sh restore backups/db_backup_20240115_030000.sql.gz
```

### Restart Services

```bash
./deploy.sh restart
```

### Check Status

```bash
./deploy.sh status
```

### Manual Deployment

```bash
# Pull latest images
docker compose -f docker-compose.prod.yml pull

# Restart with new images
docker compose -f docker-compose.prod.yml up -d
```

### SSL Renewal

SSL certificates auto-renew. To manually renew:

```bash
./deploy.sh renew-ssl
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs backend

# Check if port is in use
sudo netstat -tlnp | grep :80
```

### Database connection issues

```bash
# Check if postgres is healthy
docker compose -f docker-compose.prod.yml ps db

# Connect to database
docker compose -f docker-compose.prod.yml exec db psql -U postgres mpesaglobal
```

### Out of disk space

```bash
# Check disk usage
df -h

# Cleanup Docker
docker system prune -af
docker volume prune -f
```

### Memory issues

```bash
# Check memory
free -m

# Check which container uses most memory
docker stats --no-stream
```

---

## Architecture

```
                    ┌─────────────────┐
                    │   CloudFlare    │
                    │   (Optional)    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │     Nginx       │
                    │  (SSL/Proxy)    │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌────────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│    Frontend     │ │    Backend      │ │     MinIO       │
│    (React)      │ │    (Flask)      │ │   (Storage)     │
└─────────────────┘ └────────┬────────┘ └─────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌────────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│   PostgreSQL    │ │     Redis       │ │  Celery Worker  │
│   (Database)    │ │   (Queue)       │ │  (Background)   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Cost Estimate

| Resource | Monthly Cost |
|----------|-------------|
| DigitalOcean Droplet (4GB) | $24 |
| Domain (optional) | ~$12/year |
| **Total** | ~$24-26/month |

---

## Security Checklist

- [ ] SSH key authentication only (no passwords)
- [ ] Firewall enabled (UFW)
- [ ] Fail2Ban configured
- [ ] SSL certificate installed
- [ ] Environment variables secured
- [ ] Database password randomized
- [ ] MinIO credentials secured
- [ ] Regular backups enabled
