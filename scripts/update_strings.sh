#!/usr/bin/env bash

LOCALES=$*

files_to_translate=`find . -regex ".*\(ui\|py\)$" -type f`

echo ${files_to_translate}

for LOCALE in ${LOCALES}
do
    echo "lizmap-locales/plugin/i18n/lizmap_"${LOCALE}".ts"
    pylupdate5 -noobsolete -verbose ${files_to_translate} -ts lizmap-locales/plugin/i18n/lizmap_${LOCALE}.ts
done
