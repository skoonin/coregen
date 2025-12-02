# Cleanup targets for Coregen

################################################
##@ Cleanup
################################################

# clean - Standard cleanup
.PHONY: clean
clean: ## Standard cleanup
	@echo "Cleaning cache and coverage files..."
	@rm -rf .pytest_cache .coverage .coverage.* htmlcov *.egg-info
	@rm -rf .mypy_cache .ruff_cache .tox output
	@find . -type f \( -name '*.py[co]' -o -name '*.bak' -o -name '*.orig' -o -name '.DS_Store' \) -delete
	@find . -type d -name '__pycache__' -delete
	@echo "✓ Standard cleanup completed"

# clean-all - Deep cleanup including caches
.PHONY: clean-all
clean-all: clean clean-build ## Deep cleanup including caches (no docker)
	@echo "Removing virtual environment..."
	@rm -rf .venv
	@$(MAKE) clean-commit
	@echo "✓ Deep cleanup completed"

# clean-build - Build artifacts only
.PHONY: clean-build
clean-build: ## Build artifacts only
	@echo "Cleaning build artifacts..."
	@rm -rf build dist/build dist/release dist/releases dist/nuitka* dist/packages
	@rm -rf *.egg-info source/*.egg-info source/coregen/*.egg-info
	@find . -path "*/\.*" -name "*.so" -delete
	@find . -name "*.dist" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Build artifacts cleaned"

# clean-commit - Clean commit directories
.PHONY: clean-commit
clean-commit: ## Clean commit directories
	@echo "Cleaning generated directories..."
	@if command -v coregen >/dev/null 2>&1; then \
	.ci-tools/clean-commit.sh --clean --config test_data/.cgconfig.yaml; \
	elif [ -f "dist/build/$(OS_NAME)-$(ARCH)/__main__.dist/coregen" ]; then \
	dist/build/$(OS_NAME)-$(ARCH)/__main__.dist/coregen clean --config test_data/.cgconfig.yaml; \
	else \
	echo "Warning: coregen not available, skipping generated directory cleanup"; \
	fi
	@echo "✓ Commit directories cleaned"
