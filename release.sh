#!/bin/bash
PLUGIN_NAME="lizmap"
REMOTE_NAME="origin"

# There is a better and improved file in QuickOSM plugin.
# This one is a lighter version of it for now.

VERSION=$1
METADATA=$(cat metadata.txt | grep "version=" |  cut -d '=' -f2)

if [ "$METADATA" != "$VERSION" ];
then
    echo "The metadata file has ${METADATA} while the requested tag is ${VERSION}."
    echo "Aborting"
    exit 1
fi

if [ -n "$(git status --porcelain)" ];
then
    echo "Git working directory is not clean. Aborting."
    exit 1
fi

count=`ls -1 i18n/*.qm 2>/dev/null | wc -l`
if [ $count = 0 ]
then
    echo "No binary translation files found. Aborting."
    echo "follow lizmap-locales"
    exit 1
fi

echo "You are going to create the new tag:"
echo ${VERSION}
read -p "Are you sure you want to continue?[y/n] " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Building ${PLUGIN_NAME}.zip"
    git archive --prefix=${PLUGIN_NAME}/ -o ${PLUGIN_NAME}.zip HEAD
    # git tag ${VERSION}
    # git push --tags ${REMOTE_NAME}
fi
