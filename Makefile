# Makefile for coregen project
# Requires Python 3.11 or later

.PHONY: help cli-tree tree-help

.ONESHELL:
SHELL := /bin/bash

# Define help as the default target
.DEFAULT_GOAL := help

# Extract project version from source/coregen/__init__.py
VERSION := $(shell grep "__version__ =" source/coregen/__init__.py | cut -d'"' -f2)

# Platform detection with normalized naming
OS_NAME ?= $(strip $(shell uname -s | tr '[:upper:]' '[:lower:]'))
RAW_ARCH := $(strip $(shell uname -m | tr '[:upper:]' '[:lower:]'))

# Normalize architecture names for consistency
# Use amd64/arm64 naming (consistent with Docker/Go conventions)
ifeq ($(RAW_ARCH),x86_64)
	ARCH := amd64
else ifeq ($(RAW_ARCH),aarch64)
	ARCH := arm64
else
	ARCH := $(RAW_ARCH)
endif

# Simplified Python detection - prefer .venv if available
PYTHON := $(shell if [ -f .venv/bin/python ]; then echo .venv/bin/python; else .ci-tools/detect-python.sh 2>/dev/null || echo python3; fi)
PIP := $(PYTHON) -m pip

# Container detection
IN_CONTAINER := $(shell if [ -f /.dockerenv ] || [ -n "$$DEVCONTAINER" ]; then echo "true"; else echo "false"; fi)

# Include utility makefiles
include makefiles/clean.mk
include makefiles/docker-dev.mk
include makefiles/install.mk
include makefiles/setup.mk
include makefiles/testing.mk

#-----------------------------------------------------
# Main Makefile Targets
#-----------------------------------------------------

# Help target with improved formatting
.PHONY: help
help: ## Show this help
	@echo ""
	@echo "Coregen - Configuration Generation Tool (v$(VERSION))"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "  Current Configuration:"
	@printf "    %-18s %s\n" "Version:" "$(VERSION)"
	@printf "    %-18s %s\n" "Platform:" "$(OS_NAME)-$(ARCH)"
	@printf "    %-18s %s\n" "Python:" "$(PYTHON)"
	@printf "    %-18s %s\n" "In Container:" "$(IN_CONTAINER)"
	@echo ""
	@echo "  Project Structure:"
	@printf "    %-18s %s\n" "Source:" "source/coregen/"
	@printf "    %-18s %s\n" "Tests:" "tests/"
	@printf "    %-18s %s\n" "Package:" "dist/"
	@echo ""
	@echo "  Dependencies:"
	@printf "    %-18s" "Python Version:"
	@$(PYTHON) --version 2>/dev/null || echo "Not available"
	@printf "    %-18s" "Virtual Env:"
	@if [ -f .venv/bin/python ]; then echo ".venv/"; else echo "None"; fi
	@printf "    %-18s" "Docker:"
	@if command -v docker >/dev/null 2>&1; then echo "Available"; else echo "Not available"; fi
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##"; OFS = ""} \
		/^##@/ {printf "\n\033[1m%s\033[0m\n", substr($$0, 5)} \
		/^[a-zA-Z0-9_-]+:.*?##/ {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

################################################
##@ Documentation
################################################

.PHONY: cli-tree
cli-tree: .venv/bin/activate ## Display CLI command structure
	@echo "Generating CLI command tree..."
	@$(PYTHON) .ci-tools/cli-tree.py source/coregen/__main__.py

# tree-help - Display CLI tree with full help text
.PHONY: tree-help
tree-help: .venv/bin/activate ## Display CLI tree with help text
	@echo "Generating CLI command tree with help text..."
	@$(PYTHON) .ci-tools/cli-tree.py source/coregen/__main__.py --show-help

# Virtual environment check
.venv/bin/activate:
	@if [ ! -f .venv/bin/activate ]; then \
		echo "Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
