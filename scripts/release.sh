#!/bin/bash

set -e

METADATA=$(cat metadata.txt | grep "version=" |  cut -d '=' -f2)

echo "Releasing version ${METADATA}"
cd ..

make docker_test

git commit -am "release of ${METADATA}"
git tag "${METADATA}"
git push upstream master
git push upstream "$METADATA"
make release_zip
make release_upload
hub release create -a lizmap.zip -m "Version ${METADATA}" "${METADATA}"