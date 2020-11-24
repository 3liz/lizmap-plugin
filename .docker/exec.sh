#!/usr/bin/env bash

docker exec -t qgis sh -c "cd /tests_directory/lizmap && qgis_testrunner.sh qgis_plugin_tools.infrastructure.test_runner.test_package"
