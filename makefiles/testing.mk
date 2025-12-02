# Testing targets for Coregen

################################################
##@ Testing
################################################

.PHONY: test
test: check-env ## Run standard test suite (all tests)
	@echo "Running standard test suite..."
	@$(MAKE) _ensure-tox
	@$(PYTHON) -m tox -e py311

.PHONY: test-filters
test-filters: ## Manual filter smoke tests for detect-changes
	@echo "Running manual filter smoke tests..."
	@echo "Filter smoke tests not yet implemented"

.PHONY: test-parallel
test-parallel: check-env ## Run tests in parallel (unit/integration only, excludes E2E)
	@echo "Running tests in parallel (unit/integration only, excludes E2E)..."
	@$(MAKE) _ensure-pytest-xdist
	@$(PYTHON) -m pytest tests/ -n auto --dist loadgroup -m "not e2e" --maxfail=5

.PHONY: test-all
test-all: check-env ## All tox environments
	@echo "Running all tox environments..."
	@$(MAKE) _ensure-tox
	@$(PYTHON) -m tox

.PHONY: test-linux
test-linux: ## Run tests in Docker
	@echo "Running tests in Linux container..."
	@command -v docker >/dev/null || (echo "Error: Docker required"; exit 1)
	@docker build -t coregen-test -f Dockerfile.test .
	@docker run --rm -v $(PWD):/workspace -w /workspace coregen-test sh -c "pip install -e . && tox -e py311"

#-----------------------------------------------------
# Internal Testing Functions (Not Public Targets)
#-----------------------------------------------------

# Ensure tox is available
_ensure-tox:
	@if ! $(PYTHON) -m tox --version &> /dev/null; then \
	echo "Installing tox..."; \
	$(PIP) install tox --upgrade --quiet; \
	fi

# Ensure pytest-xdist is available for parallel testing
_ensure-pytest-xdist:
	@if ! $(PYTHON) -c "import xdist" &> /dev/null; then \
	echo "Installing pytest-xdist..."; \
	$(PIP) install pytest-xdist --upgrade --quiet; \
	fi
