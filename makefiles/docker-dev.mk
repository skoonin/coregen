# Docker Development Environment

################################################
##@ Docker Development
################################################

# Configuration
DOCKER_IMAGE := coregen-dev
DOCKER_CONTAINER := coregen-dev-$(shell basename "$(PWD)")
GITHUB_SSH_KEY_FILE=private_ssh_key

.PHONY: docker-build
docker-build: ## Build development container
	@echo "Building Docker development image..."
	@if ! docker info >/dev/null 2>&1; then \
		echo "Error: Docker daemon not running"; \
		exit 1; \
	fi
	docker build -t $(DOCKER_IMAGE) devcontainer/
	@echo "Build complete: $(DOCKER_IMAGE)"

.PHONY: docker-build-nc
docker-build-nc: ## Build container (no cache)
	@echo "Building Docker image (no cache)..."
	@if ! docker info >/dev/null 2>&1; then \
		echo "Error: Docker daemon not running"; \
		exit 1; \
	fi
	docker build --no-cache -t $(DOCKER_IMAGE) devcontainer/

.PHONY: docker-run
docker-run: ## Run development container
	@echo "Running Docker development container..."
	@# Ensure image exists
	@if ! docker image inspect $(DOCKER_IMAGE) >/dev/null 2>&1; then \
		echo "Image not found. Building..."; \
		$(MAKE) docker-build; \
	fi
	@# Clean up any existing container
	@docker stop $(DOCKER_CONTAINER) 2>/dev/null || true
	@docker rm $(DOCKER_CONTAINER) 2>/dev/null || true
	@# Start fresh container with persistent home directory
	@# Mount entire repo but exclude Python environments and caches via anonymous volumes
	@docker run -d \
		--name $(DOCKER_CONTAINER) \
		--privileged \
		--cap-add=NET_ADMIN \
		--cap-add=NET_RAW \
		-e CONTAINER_NAME=$(DOCKER_CONTAINER) \
		-e PYTHONDONTWRITEBYTECODE=1 \
		-e PYTHONUNBUFFERED=1 \
		-e VIRTUAL_ENV=/opt/venv \
		-e PATH="/opt/venv/bin:$$PATH" \
		-v "$(PWD):/home/node/coregen" \
		-v /home/node/coregen/.venv \
		-v /home/node/coregen/venv \
		-v /home/node/coregen/env \
		-v /home/node/coregen/ENV \
		-v /home/node/coregen/__pycache__ \
		-v /home/node/coregen/.pytest_cache \
		-v /home/node/coregen/.mypy_cache \
		-v /home/node/coregen/.tox \
		-v "$(DOCKER_CONTAINER)-home:/home/node" \
		$(if $(devcontainer/$(GITHUB_SSH_KEY_FILE)),-v "devcontainer/$(GITHUB_SSH_KEY_FILE):/home/node/.ssh/$(GITHUB_SSH_KEY_FILE):ro",) \
		-w "/home/node/coregen" \
		$(DOCKER_IMAGE) \
		tail -f /dev/null
	@# Install project dependencies including dev tools
	@echo "Setting up Python environment, please wait..."
	@docker exec -u node $(DOCKER_CONTAINER) bash -c " \
		cd /home/node/coregen && \
		source /opt/venv/bin/activate && \
		pip install -q --upgrade pip setuptools wheel && \
		pip install -q -e '.[dev]' && \
		echo 'Development environment ready.' \
	"
	@echo ""
	@echo "=== Setup Git Authentication ==="
	@echo ""
	@echo "Git configuration from your host system has been mounted."
	@echo "You should be able to use git as you normally would."
	@echo "If not, run the following commands inside the container:"
	@echo ""
	@echo "================================"
	@echo "Run this inside the container:"
	@echo "  gh auth login        # Authenticate with GitHub"
	@echo "                       # (use the same authentication method as your repo (SSH/HTTPS))"
	@echo "  gh auth setup-git    # Configure git to use GitHub CLI"
	@echo "  gh auth status       # Verify authentication"
	@echo "================================"
	@echo ""
	@# Enter shell immediately
	@$(MAKE) docker-shell

.PHONY: docker-shell
docker-shell: ## Interactive container shell
	@if ! docker ps -q -f name=$(DOCKER_CONTAINER) -f status=running | grep -q .; then \
		echo "Container not running. Use 'make docker-run' first."; \
		exit 1; \
	fi
	@echo "Entering container..."
	@docker exec -it -u node $(DOCKER_CONTAINER) bash -l

.PHONY: docker-stop
docker-stop: ## Stop running container
	@echo "Stopping Docker container..."
	@if docker ps -q -f name=$(DOCKER_CONTAINER) -f status=running | grep -q .; then \
		docker stop $(DOCKER_CONTAINER); \
		echo "Container stopped. Use 'make docker-run' to restart."; \
	else \
		echo "Container is not running."; \
	fi

.PHONY: docker-clean
docker-clean: ## Remove container and images
	@echo "Cleaning Docker resources..."
	@docker stop $(DOCKER_CONTAINER) 2>/dev/null || true
	@docker rm $(DOCKER_CONTAINER) 2>/dev/null || true
	@docker volume rm $(DOCKER_CONTAINER)-home 2>/dev/null || true
	@docker rmi $(DOCKER_IMAGE) 2>/dev/null || true
	@echo "Cleanup complete"

.PHONY: docker-clean-all
docker-clean-all: ## Remove all coregen Docker resources
	@echo "Cleaning up ALL coregen Docker resources..."
	@echo "This will remove:"
	@echo "  - All coregen containers (running and stopped)"
	@echo "  - All coregen images"
	@echo "  - All coregen volumes"
	@echo ""
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo ""
	@echo "Stopping and removing all coregen containers..."
	@docker ps -a --filter "name=coregen-dev-" --format "{{.Names}}" | xargs -r docker stop 2>/dev/null || true
	@docker ps -a --filter "name=coregen-dev-" --format "{{.Names}}" | xargs -r docker rm 2>/dev/null || true
	@echo "Removing all coregen images..."
	@docker images --filter "reference=coregen-dev*" --format "{{.Repository}}:{{.Tag}}" | xargs -r docker rmi 2>/dev/null || true
	@echo "Removing all coregen volumes..."
	@docker volume ls --filter "name=coregen-dev-" --format "{{.Name}}" | xargs -r docker volume rm 2>/dev/null || true
	@echo "Cleanup complete - all coregen Docker resources removed"
