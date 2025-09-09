SHELL:=bash

PYTHON_MODULE=lizmap

QGIS_VERSION:=3.40
QGIS_DOCKER_IMAGE:=qgis/qgis:$(QGIS_VERSION)

#
# Configure
#


REQUIREMENTS= \
	dev \
	packaging \
	$(NULL)

.PHONY: uv-required update-requirements $(REQUIREMENTS)

update-requirements: $(REQUIREMENTS)

# Require uv (https://docs.astral.sh/uv/) for extracting
# infos from project's dependency-groups
$(REQUIREMENTS): check-uv-install
	@echo "Updating requirements for '$@'"
	@uv export --format requirements.txt \
		--no-annotate \
		--no-editable \
		--no-hashes \
		--only-group $@ \
		-q -o requirements/$@.txt

#
# Static analysis
#

lint:
	$(UV_RUN) ruff check --preview  --output-format=concise $(PYTHON_MODULE)

lint-fix:
	$(UV_RUN) ruff check --preview --fix $(PYTHON_MODULE)

format:
	$(UV_RUN) format $(PYTHON_MODULE) 

typecheck:
	$(UV_RUN) mypy $(PYTHON_MODULE)

scan:
	$(UV_RUN) bandit -r $(PYTHON_MODULE) $(SCAN_OPTS)


check-uv-install:
	@which uv > /dev/null || { \
		echo "You must install uv (https://docs.astral.sh/uv/)"; \
		exit 1; \
	}

#
# Tests
#

test:
	cd tests && $(UV_RUN) pytest -v

#
# Test using docker image
#
export QGIS_VERSION
export UID=$(shell id -u)
export GID=$(shell id -g)
docker-test:
	cd .docker && docker compose up \
		--quiet-pull \
		--abort-on-container-exit \
		--exit-code-from qgis


