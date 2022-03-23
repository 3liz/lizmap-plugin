#!/bin/bash

set -e

# Add /.local to path
export PATH=$PATH:/.local/bin

VENV_PATH=/.local/venv

PIP_INSTALL="$VENV_PATH/bin/pip install -U"

echo "Creating virtualenv"
python3 -m venv --system-site-packages $VENV_PATH

echo "Installing required packages..."
$PIP_INSTALL -q pip setuptools wheel
$PIP_INSTALL -q -U --prefer-binary --user -r requirements.txt

# Disable qDebug stuff that bloats test outputs
export QT_LOGGING_RULES="*.debug=false;*.warning=false"

# Disable python hooks/overrides
export QGIS_DISABLE_MESSAGE_HOOKS=1
export QGIS_NO_OVERRIDE_IMPORT=1
export CI=True

pytest -vv --qgis-plugins=/src $@
exit $?
