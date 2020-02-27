#!/bin/bash

docker stop qgis-infrastructure-environment &> /dev/null
docker rm qgis-infrastructure-environment &> /dev/null
docker run -d --name qgis-infrastructure-environment -v $(dirname $(pwd)):/"$1" -e DISPLAY=:99 qgis/qgis:"$2"
echo "Waiting 10 seconds"
sleep 10
docker exec -it qgis-infrastructure-environment sh -c "qgis_setup.sh $1"
docker exec -it qgis-infrastructure-environment sh -c "cd /$1 && qgis_testrunner.sh qgis_plugin_tools.infrastructure.test_runner.test_package"
status=$?
docker stop qgis-infrastructure-environment &> /dev/null
docker rm qgis-infrastructure-environment &> /dev/null
echo "Kill and removing the container"
exit ${status}
