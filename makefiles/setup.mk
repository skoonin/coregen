# Setup and environment management targets for Coregen

################################################
##@ Setup & Development
################################################

# setup - Create virtual environment and install dependencies
# Creates basic production-ready environment for building and running
.PHONY: setup
setup: .venv/touchfile ## Create virtual environment and install dependencies
	@echo "✓ Basic setup completed"
	@echo "To activate: source .venv/bin/activate"

# setup-dev - Development environment with all tools
# Extends basic setup with development tools (pre-commit, linting, etc.)
.PHONY: setup-dev
setup-dev: setup ## Development environment with all tools
	@echo "Installing development tools..."
	@./.venv/bin/pip install pre-commit >/dev/null 2>&1 || true
	@./.venv/bin/pre-commit install >/dev/null 2>&1 || true
	@echo "✓ Development environment ready with pre-commit hooks"

# setup-force - Force recreation of virtual environment
# Works with both setup and setup-dev - recreates environment completely
.PHONY: setup-force
setup-force: ## Force recreation of virtual environment
	@echo "Forcing virtual environment recreation..."
	@$(MAKE) clean-venv
	@$(MAKE) setup-dev
	@echo "✓ Virtual environment forcefully recreated"
	@echo "Note: Use 'make setup' for production-only environment"

# deps-update - Update dependencies
deps-update: .venv/touchfile
	@echo "Updating dependencies..."
	@./.venv/bin/pip install --upgrade pip setuptools wheel --quiet
	@./.venv/bin/pip install -e ".[dev]" --upgrade --quiet
	@echo "✓ Dependencies updated"

#-----------------------------------------------------
# Internal Setup Functions (Not Public Targets)
#-----------------------------------------------------

# Create/update virtual environment
.venv/touchfile: pyproject.toml
	@bash .ci-tools/setup-venv.sh
	@touch $@

# Validate environment
check-env:
	@bash .ci-tools/check-setup.sh

# Clean virtual environment
clean-venv:
	@echo "Removing virtual environment..."
	@rm -rf .venv
	@echo "✓ Virtual environment removed"
