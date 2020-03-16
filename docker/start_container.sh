#!/bin/bash

echo 'Start docker-compose'
docker-compose up -d --force-recreate

echo 'Wait 10 seconds'
sleep 10

echo 'Installation of the plugin'
docker exec -it qgis sh -c "qgis_setup.sh lizmap"

echo 'Container is running'
# docker exec -it qgis sh -c "cd /tests_directory/lizmap && qgis_testrunner.sh qgis_plugin_tools.infrastructure.test_runner.test_package"
# docker exec qgis qgis
# docker-compose kill
# docker-compose rm -f

# echo 'Tests finished'
