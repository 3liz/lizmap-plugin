#!/usr/bin/env bash

docker-compose up -d --force-recreate
echo 'Wait 10 seconds'
sleep 10
echo 'Installation of the plugin'
docker exec -t qgis sh -c "qgis_setup.sh lizmap"
echo 'Containers are running'
