SHELL:=bash

PYTHON_MODULE=lizmap

QGIS_VERSION ?= 3.40

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
UV_RUN=uv run $(ACTIVE_VENV)
endif


REQUIREMENTS_GROUPS= \
	dev \
	tests \
	lint \
	packaging \
	$(NULL)

.PHONY: update-requirements

REQUIREMENTS=$(patsubst %, requirements/%.txt, $(REQUIREMENTS_GROUPS))

# Update only packaging dependencies
# Waiting for https://github.com/astral-sh/uv/issues/12848
update-packaging-dependencies::
	uv lock -P qgis-plugin-package-ci -P qgis-plugin-transifex-ci

update-packaging-dependencies:: update-requirements

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

LINT_TARGETS=$(PYTHON_MODULE) tests $(EXTRA_LINT_TARGETS)

lint:
	@ $(UV_RUN) ruff check --preview  --output-format=concise $(LINT_TARGETS)

lint-fix:
	@ $(UV_RUN) ruff check --preview --fix $(LINT_TARGETS)

format:
	@ $(UV_RUN) ruff format $(LINT_TARGETS) 

typecheck:
	$(UV_RUN)  mypy $(patsubst %, -p %, $(LINT_TARGETS))

scan:
	@ $(UV_RUN) bandit -r $(PYTHON_MODULE) $(SCAN_OPTS)


check-uv-install:
	@which uv > /dev/null || { \
		echo "You must install uv (https://docs.astral.sh/uv/)"; \
		exit 1; \
	}

#
# Tests
#

test:
	$(UV_RUN) pytest -v tests/

#
# Test using docker image
#
QGIS_IMAGE_REPOSITORY ?= qgis/qgis
QGIS_IMAGE_TAG ?= $(QGIS_IMAGE_REPOSITORY):$(QGIS_VERSION)

export QGIS_VERSION
export QGIS_IMAGE_TAG
export UID=$(shell id -u)
export GID=$(shell id -g)
docker-test:
	cd .docker && docker compose up \
		--quiet-pull \
		--abort-on-container-exit \
		--exit-code-from qgis
	cd .docker && docker compose down -v

#
# Code managment
#

# Display a summary of codes annotations
show-annotation-%:
	@grep -nR --color=auto --include=*.py '# $*' lizmap/ || true

# Output variable
echo-variable-%:
	@echo "$($*)"
