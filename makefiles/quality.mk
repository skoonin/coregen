# Code quality targets for Coregen

################################################
##@ Code Quality
################################################

.PHONY: lint
lint: check-env ## Run linting (flake8, pylint)
	@$(PYTHON) -m tox -e lint

.PHONY: type-check
type-check: check-env ## Run mypy type checking
	@$(PYTHON) -m tox -e type

.PHONY: format
format: check-env ## Auto-format with black and isort
	@$(PYTHON) -m tox -e format

.PHONY: coverage
coverage: check-env ## Run tests with coverage report
	@$(PYTHON) -m tox -e coverage
