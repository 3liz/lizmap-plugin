SHELL:=bash

PYTHON_MODULE=lizmap


-include .localconfig.mk

#
# Configure
#

# Check if uv is available
$(eval UV_PATH=$(shell which uv))
ifdef UV_PATH
ifdef VIRTUAL_ENV
# Always prefer active environment
ACTIVE_VENV=--active
endif
UV=uv run $(ACTIVE_VENV)
endif


REQUIREMENTS_GROUPS= \
	dev \
	tests \
	lint \
	packaging \
	$(NULL)

.PHONY: update-requirements

REQUIREMENTS=$(patsubst %, requirements/%.txt, $(REQUIREMENTS_GROUPS))

update-requirements: $(REQUIREMENTS)

# Require uv (https://docs.astral.sh/uv/) for extracting
# infos from project's dependency-groups
requirements/%.txt: uv.lock
	@echo "Updating requirements for '$*'"; \
	uv export --format requirements.txt \
		--no-annotate \
		--no-editable \
		--no-hashes \
		--only-group $* \
		-q -o requirements/$*.txt;

#
# Static analysis
#

LINT_TARGETS=$(PYTHON_MODULE) $(EXTRA_LINT_TARGETS)

lint:
	@ $(UV) ruff check --output-format=concise $(LINT_TARGETS)
	@ $(UV) ruff check --output-format=concise --target-version=py310 tests

lint-fix:
	@ $(UV) ruff check --fix $(LINT_TARGETS)
	@ $(UV) ruff check --fix --target-version=py310 tests

lint-preview:
	@ $(UV) ruff check --preview --output-format=concise  $(LINT_TARGETS)

format:
	@ $(UV) ruff format $(LINT_TARGETS) 

typecheck:
	$(UV) mypy $(PYTHON_MODULE)
	$(UV) mypy tests --python-version 3.10

scan:
	@ $(UV) bandit -r $(PYTHON_MODULE) $(SCAN_OPTS)


#
# Tests
#

test:
	$(UV) pytest -v tests/

#
# Test using docker image
#

ifdef REGISTRY_URL
REGISTRY_PREFIX=$(REGISTRY_URL)/
else
REGISTRY_PREFIX=3liz
endif

QGIS_VERSION ?= 3.44
QGIS_IMAGE_REPOSITORY ?= ${REGISTRY_PREFIX}qgis-platform
QGIS_IMAGE_TAG ?= $(QGIS_IMAGE_REPOSITORY):$(QGIS_VERSION)

export QGIS_VERSION
export QGIS_IMAGE_TAG
export UID=$(shell id -u)
export GID=$(shell id -g)

docker-test:
	set -e; \
	cd .docker; 
	docker compose up \
		--quiet-pull \
		--abort-on-container-exit \
		--exit-code-from qgis; \
	docker compose down -v;

#
# Install/sync
#

sync:
	@echo "Synchronizing python's environment with frozen dependencies"
	uv sync --all-groups --frozen --all-extras

install-dev::
	@echo "Creating virtual python environment"
	uv venv --system-site-packages --no-managed-python

install-dev:: sync

#
# Coverage 
#

# Run tests coverage
covtests:
	@echo "Running coverage tests"
	@ $(UV) coverage run -m pytest tests/

coverage: covtests
	@echo "Building coverage html"
	@ $(UV) coverage html


#
# Code managment
#

# Display a summary of codes annotations
show-annotation-%:
	@grep -nR --color=auto --include=*.py '# $*' lizmap/ || true

# Output variable
echo-variable-%:
	@echo "$($*)"
