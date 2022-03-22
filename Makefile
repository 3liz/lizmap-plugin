# default is no locales
# Empty in Transifex for now 20/09/2019 : bg_BG zh_CN lt_LT tr
# TODO CHECK TRANSLATIONS
# IT IS NOT USED ANYMORE
LOCALES = "cs de el en es eu fi fr gl hu_HU id it nl no pl_PL pt pt_BR ro ru sl sv_SE tr"

start_tests:
	@echo 'Start docker-compose'
	@cd .docker && ./start.sh

run_tests:
	@echo 'Running tests, containers must be running'
	@cd .docker && ./exec.sh
	@flake8

stop_tests:
	@echo 'Stopping/killing containers'
	@cd .docker && ./stop.sh

tests: start_tests run_tests stop_tests

SHELL:=bash

COMMITID=$(shell git rev-parse --short HEAD)

REGISTRY_URL ?= 3liz

ifdef REGISTRY_URL
	REGISTRY_PREFIX=$(REGISTRY_URL)/
endif

FLAVOR:=3.16

BECOME_USER:=$(shell id -u)

QGIS_IMAGE=$(REGISTRY_PREFIX)qgis-platform:$(FLAVOR)

LOCAL_HOME ?= $(shell pwd)

SRCDIR=$(shell realpath .)

test_server:
	@mkdir -p $$(pwd)/.local $(LOCAL_HOME)/.cache
	@docker run --rm --name qgis-server-lizmap-test-$(FLAVOR)-$(COMMITID) -w /src/test/server \
		-u $(BECOME_USER) \
		-v $(SRCDIR):/src \
		-v $$(pwd)/.local:/.local \
		-v $(LOCAL_HOME)/.cache:/.cache \
		-e PIP_CACHE_DIR=/.cache \
		-e QGIS_SERVER_LIZMAP_REVEAL_SETTINGS=TRUE \
		-e PYTEST_ADDOPTS="$(TEST_OPTS)" \
		$(QGIS_IMAGE) ./run-tests.sh
	@flake8
