#!/usr/bin/env bash
set -e

LIZMAP_DIR="$1"

if [ "$1" == "" ]; then
    echo "Error: path to your lizmap/ directory is missing"
    exit 1
fi

if [ ! -f "$LIZMAP_DIR/scripts/script.php" ]; then
    echo "Error: given path seems to be not the lizmap directory. I don't find scripts/scripts.php"
    exit 2
fi



LOCALES_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

source $LOCALES_DIR/module_list.sh

if [ "$2" != "" ]; then
  MODULES="$2"
fi


(cd $LIZMAP_DIR/../ && git checkout $LIZMAP_BRANCH)

for MODULE in $MODULES
do
    for LIZLOCALE in $OFFICAL_LOCALES
    do
        if [ -f "$LOCALES_DIR/$LIZLOCALE/$MODULE.po" ]; then
            php $LIZMAP_DIR/scripts/script.php lizmap~locale:importpo $LOCALES_DIR/$LIZLOCALE/$MODULE.po $MODULE $LIZLOCALE
        fi
    done
done
