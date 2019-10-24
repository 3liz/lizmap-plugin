#!/usr/bin/env bash

LOCALES=$*

for LOCALE in ${LOCALES}
do
    echo "Compiling lizmap-locales/plugin/i18n/lizmap_"${LOCALE}".ts"
    lrelease lizmap-locales/plugin/i18n/lizmap_${LOCALE}.ts -qm lizmap-locales/plugin/i18n/lizmap_${LOCALE}.qm;
done
