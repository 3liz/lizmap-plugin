#!/bin/bash
LRELEASE=$1
LOCALES=$2
PLUGIN=lizmap

for LOCALE in $LOCALES
do
    echo "Processing: ${PLUGIN}_${LOCALE}.ts"
    # Note we don't use pylupdate with qt .pro file approach as it is flakey
    # about what is made available.
    $LRELEASE "i18n/"${PLUGIN}"_"${LOCALE}".ts"
done
