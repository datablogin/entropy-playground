# Docker Environment Setup

This guide explains how to use Docker for local development and running the Entropy Playground agents.

## Prerequisites

- Docker Engine 20.10+ 
- Docker Compose v2.0+
- Git

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/datablogin/entropy-playground.git
   cd entropy-playground
   ```

2. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and add your API keys:
   - `GITHUB_TOKEN`: Your GitHub personal access token
   - `CLAUDE_API_KEY`: Your Claude API key
   - `OPENAI_API_KEY`: (Optional) Your OpenAI API key

4. Build and start the services:
   ```bash
   docker-compose up --build
   ```

## Services

### Redis
- **Purpose**: State management and inter-agent communication
- **Port**: 6379
- **Health check**: Automatically configured
- **Data persistence**: Stored in `redis-data` volume

### Agent
- **Purpose**: Main agent runtime
- **Security**: Runs as non-root user, read-only filesystem
- **Volumes**:
  - Source code (read-only)
  - Agent workspace at `/workspace`
  - Logs at `./logs`

### Dev
- **Purpose**: Development environment with build tools
- **Usage**: Interactive bash shell for development
- **Access**: `docker-compose run --rm dev`

## Common Commands

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f agent

# Access development shell
docker-compose run --rm dev

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Development Workflow

1. Make code changes locally
2. The agent service automatically sees changes (mounted volume)
3. Restart agent if needed: `docker-compose restart agent`
4. Run tests in dev container: `docker-compose run --rm dev pytest`

## Security Features

- Non-root user execution
- Read-only root filesystem
- No new privileges flag
- Isolated network
- Minimal base images (alpine/slim)

## Troubleshooting

### Permission Issues
If you encounter permission errors, ensure your user has Docker permissions:
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

### Port Conflicts
If port 6379 is already in use, modify the Redis port in `docker-compose.yml`:
```yaml
redis:
  ports:
    - "16379:6379"  # Change to unused port
```

### Build Failures
Clean rebuild:
```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```