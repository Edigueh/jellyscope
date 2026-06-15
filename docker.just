[doc('List recipes in this module')]
default:
    @just --list --justfile {{source_file()}}

[doc('Build the Docker image (tagged with pyproject version)')]
build:
    JELLYSCOPE_VERSION=$(uv version --short 2>/dev/null || echo dev) docker compose build

[doc('Start the containerized service (detached)')]
up:
    JELLYSCOPE_VERSION=$(uv version --short 2>/dev/null || echo dev) docker compose up -d

[doc('Stop and remove the containerized service')]
down:
    docker compose down

[doc('Tail logs from the running container')]
logs:
    docker compose logs -f jellyscope

[doc('Restart container without rebuild (env/state reset only)')]
restart:
    docker compose restart jellyscope

[doc('Rebuild image and recreate container (uses layer cache)')]
reload:
    JELLYSCOPE_VERSION=$(uv version --short 2>/dev/null || echo dev) docker compose up -d --build

[doc('Start dev container with bind-mounted src and uvicorn --reload')]
dev:
    JELLYSCOPE_VERSION=$(uv version --short 2>/dev/null || echo dev) docker compose -f docker-compose.yml -f docker-compose.dev.yml up
