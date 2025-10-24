# Spec-Editor Deployment Guide

## Prerequisites
- Docker Engine 20.10+ (install via `curl -fsSL https://get.docker.com | sh`)
- Docker Compose (included with Docker Engine)
- GitHub Personal Access Token with `repo` and `workflow` scopes

## Quick Start (Local Development)

1. **Clone repository**:
   ```bash
   git clone https://github.com/trakrf/action-spec.git
   cd action-spec/demo
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   nano .env  # Add your GH_TOKEN
   ```

3. **Start services**:
   ```bash
   docker compose up -d
   ```

4. **Verify health**:
   ```bash
   curl http://localhost:5000/health
   # Should return: {"status": "healthy", "github": "connected", ...}
   ```

5. **Access UI**:
   - Spec-editor: http://localhost:5000
   - Demo app: http://localhost:8080

## EC2 Deployment

### Prerequisites
- EC2 instance with public IP (t3.small minimum, t3.medium recommended)
- Security group allows inbound TCP 5000 (or 80 if using reverse proxy)
- SSH access to EC2 instance

### Deployment Steps

1. **Install Docker on EC2**:
   ```bash
   # SSH to EC2
   ssh ec2-user@your-ec2-ip

   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker ec2-user

   # Log out and back in for group to take effect
   exit
   ssh ec2-user@your-ec2-ip

   # Verify Docker
   docker --version
   ```

2. **Deploy spec-editor**:
   ```bash
   # Create deployment directory
   mkdir -p ~/spec-editor
   cd ~/spec-editor

   # Download docker-compose.yml
   curl -O https://raw.githubusercontent.com/trakrf/action-spec/main/demo/docker-compose.yml

   # Create .env file
   cat > .env <<EOF
   GH_TOKEN=ghp_your_token_here
   GH_REPO=trakrf/action-spec
   SPECS_PATH=demo/infra
   WORKFLOW_BRANCH=main
   EOF

   # Start services
   docker compose up -d
   ```

3. **Verify deployment**:
   ```bash
   docker ps
   # Should show spec-editor and demo-app running

   curl http://localhost:5000/health
   # Should return healthy status
   ```

4. **Access via browser**:
   - Open http://your-ec2-public-ip:5000

## Development Workflow

### Enable Live Code Reload

Uncomment volume mounts in `docker-compose.yml`:
```yaml
volumes:
  - ./backend/app.py:/app/app.py
  - ./backend/templates:/app/templates
```

Restart containers:
```bash
docker compose restart spec-editor
```

Now edits to `app.py` or templates automatically reload (Flask debug mode).

## Monitoring

**View logs**:
```bash
docker compose logs -f spec-editor
docker compose logs -f demo-app
```

**Check health**:
```bash
docker ps  # Should show "healthy" status
curl http://localhost:5000/health
```

**Restart services**:
```bash
docker compose restart spec-editor
docker compose restart demo-app
```

## Updates

**Pull latest image**:
```bash
docker compose pull
docker compose up -d
```

**Rebuild from source**:
```bash
docker compose build --no-cache
docker compose up -d
```

## Troubleshooting

### Container won't start
**Symptom**: `docker ps` shows container exited

**Debug**:
```bash
docker compose logs spec-editor
```

**Common fixes**:
- Missing GH_TOKEN: Add to .env file
- Invalid GH_TOKEN: Generate new token at https://github.com/settings/tokens/new
- Port conflict: Change port in docker-compose.yml (5000:5000 → 8000:5000)

### Health check failing
**Symptom**: `docker ps` shows "unhealthy" status

**Debug**:
```bash
docker compose exec spec-editor curl http://localhost:5000/health
docker compose logs spec-editor
```

**Common fixes**:
- GitHub connectivity: Test with `curl https://api.github.com/repos/trakrf/action-spec`
- Rate limits: Check /health endpoint response for rate limit info
- Token permissions: Verify token has `repo` and `workflow` scopes

### Can't access UI from browser
**Symptom**: Connection refused when accessing http://ec2-ip:5000

**Debug**:
```bash
# Check container is running
docker ps | grep spec-editor

# Check port binding
docker port spec-editor

# Check EC2 security group
# Ensure inbound rule allows TCP 5000 from your IP
```

**Common fixes**:
- Security group: Add inbound rule for TCP 5000
- Container not running: `docker compose up -d`
- Firewall: Check EC2 firewall settings

### "Permission denied" errors
**Symptom**: Cannot run docker commands

**Fix**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in
exit
ssh ec2-user@your-ec2-ip
```

## Architecture

```
┌─────────────────────────────────┐
│  Browser                        │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Docker Compose                 │
│  ┌──────────────────────────┐   │
│  │  spec-editor:5000        │   │
│  │  - Flask app             │   │
│  │  - GitHub API client     │   │
│  │  - Health check          │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │  demo-app:8080           │   │
│  │  - HTTP echo server      │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
```

## Security Notes

- **Never commit .env files** - They contain GitHub tokens
- **.env is gitignored** - Already excluded in .gitignore
- **Token scopes**: Only grant `repo` and `workflow` (principle of least privilege)
- **Token rotation**: Regenerate tokens periodically
- **EC2 security**: Restrict port 5000 to trusted IPs only

## Production Hardening (Future)

For production deployments beyond demo, consider:
- NGINX reverse proxy with TLS termination
- Gunicorn WSGI server (already in requirements.txt)
- AWS Secrets Manager for GH_TOKEN
- CloudWatch Logs integration
- Multi-stage Docker builds (smaller images)
- Horizontal scaling with ECS/EKS
