SHELL:=bash
.ONESHELL:
.PHONY: env

QGIS_VERSION ?= release-3_16

start_tests: env
	@echo 'Start docker compose'
	@cd .docker && ./start.sh

run_tests:
	@echo 'Running tests, containers must be running'
	@cd .docker && ./exec.sh
	@flake8

stop_tests:
	@echo 'Stopping/killing containers'
	@cd .docker && ./stop.sh

tests: start_tests run_tests stop_tests

env:
	@echo "Creating environment file for Docker Compose"
	@cat <<-EOF > .docker/.env
	QGIS_VERSION=$(QGIS_VERSION)
	EOF
	@cat .docker/.env
