# Installation targets for pip-based distribution

################################################
##@ Package Building
################################################

.PHONY: package-build
package-build: ## Build Python wheel and source distribution
	@echo "Building Python package..."
	@$(PYTHON) -m pip install --upgrade build
	@$(PYTHON) -m build
	@echo "✓ Package built successfully"

.PHONY: package-test
package-test: ## Test package installation
	@echo "Testing package installation..."
	@$(PYTHON) -m pip install dist/coregen-*.whl --force-reinstall
	@coregen --version
	@echo "✓ Package test complete"

################################################
##@ Installation
################################################

# Install to user directory
.PHONY: install
install: check-env ## Install coregen package
	@echo "Installing to user directory..."
	@if [ -n "$$VIRTUAL_ENV" ]; then \
	echo "Error: Cannot install to user directory from within a virtual environment"; \
	echo "Please \`deactivate\` your virtual environment first"; \
	exit 1; \
	fi
	@pip install --user git+file://$(PWD)
	@echo "✓ User installation complete"

.PHONY: install-dev
install-dev: ## Install in development mode (pip install -e .)
	@echo "Installing coregen in development mode..."
	@$(PYTHON) -m pip install -e .
	@echo "✓ Development installation complete"

.PHONY: uninstall
uninstall: ## Uninstall coregen package
	@echo "Uninstalling coregen..."
	@pip uninstall -y coregen || echo "Package not installed"
	@echo "✓ Uninstall complete"

# Test git installation (for CI/testing)
.PHONY: test-git-install
test-git-install: ## Test installation from git repository
	@echo "Testing git-based installation..."
	@rm -rf test_git_env
	@python -m venv test_git_env
	@source test_git_env/bin/activate && \
	pip install git+file://$(PWD) && \
	coregen version && \
	coregen --help > /dev/null
	@rm -rf test_git_env
	@echo "✓ Git installation test passed"
