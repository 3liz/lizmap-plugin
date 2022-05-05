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
