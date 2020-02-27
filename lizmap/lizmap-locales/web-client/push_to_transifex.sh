#!/usr/bin/env bash

LOCALES_DIR="$(dirname $0)"

source $LOCALES_DIR/module_list.sh

tx push -s --branch $LOCALES_BRANCH
