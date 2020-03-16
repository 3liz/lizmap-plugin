# default is no locales
# Empty in Transifex for now 20/09/2019 : bg_BG zh_CN lt_LT tr
LOCALES = "cs de el en es eu fi fr gl hu_HU id it nl no pl_PL pt pt_BR ro ru sl sv_SE tr"
LOCALES_SUBMODULE = lizmap-locales/plugin

PLUGINNAME = lizmap

docker_test:
	$(MAKE) -C lizmap/qgis_plugin_tools docker_test PLUGINNAME=$(PLUGINNAME)

release_%:
	$(MAKE) -C lizmap/qgis_plugin_tools release_$* PLUGINNAME=$(PLUGINNAME)

# i18n_%:
    # Do not use qgis_plugin_tools, translation are shared with LWC
	# $(MAKE) -C qgis_plugin_tools i18n_$* LOCALES=$(LOCALES)
# Instead of using the qgis_plugin_tools makefile for translation:
i18n_1_prepare:
	@echo Updating strings locally 1/4
	@./scripts/update_strings.sh $(LOCALES)

i18n_2_push:
	@echo Push strings to Transifex 2/4
	@cd $(LOCALES_SUBMODULE) && tx push -s

i18n_3_pull:
	@echo Pull strings from Transifex 3/4
	@cd $(LOCALES_SUBMODULE) && tx pull -a -f

i18n_4_compile:
	@echo Compile TS files to QM 4/4
	@./scripts/update_compiled_strings.sh $(LOCALES)

start_tests:
	@echo 'Start docker-compose'
	@cd docker && docker-compose up -d --force-recreate
	@echo 'Wait 10 seconds'
	@sleep 10
	@echo 'Installation of the plugin'
	@docker exec -it qgis sh -c "qgis_setup.sh lizmap"
	@echo 'Container is running'

run_tests:
	@echo 'Running tests, containers must be running'
	@docker exec -it qgis sh -c "cd /tests_directory/lizmap && qgis_testrunner.sh qgis_plugin_tools.infrastructure.test_runner.test_package"

stop_tests:
	@echo 'Stopping/killing containers'
	@cd docker && docker-compose kill
	@cd docker && docker-compose rm -f

SHELL:=bash

COMMITID=$(shell git rev-parse --short HEAD)

REGISTRY_URL=3liz

ifdef REGISTRY_URL
	REGISTRY_PREFIX=$(REGISTRY_URL)/
endif

FLAVOR:=3.4

BECOME_USER:=$(shell id -u)

QGIS_IMAGE=$(REGISTRY_PREFIX)qgis-platform:$(FLAVOR)

LOCAL_HOME ?= $(shell pwd)

SRCDIR=$(shell realpath .)

test_server:
	mkdir -p $$(pwd)/.local $(LOCAL_HOME)/.cache
	docker run --rm --name qgis-server-lizmap-test-$(FLAVOR)-$(COMMITID) -w /src/test/server \
		-u $(BECOME_USER) \
		-v $(SRCDIR):/src \
		-v $$(pwd)/.local:/.local \
		-v $(LOCAL_HOME)/.cache:/.cache \
		-e PIP_CACHE_DIR=/.cache \
		-e PYTEST_ADDOPTS="$(TEST_OPTS)" \
		$(QGIS_IMAGE) ./run-tests.sh
