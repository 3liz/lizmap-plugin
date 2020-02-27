#!/usr/bin/env bash

LOCALES=$*

files_to_translate=`find .. -regex ".*\(ui\|py\)$" -type f`

for LOCALE in ${LOCALES}
do
    echo "resources/i18n/"${LOCALE}".ts"
    pylupdate5 -noobsolete ${files_to_translate} -ts ../resources/i18n/${LOCALE}.ts
done
