"""Configure QGIS settings"""

import os

from qgis.core import (
    QgsSettings,
)

from ..definitions.qgis_settings import Settings
from ..toolbelt.convert import as_boolean


def configure_qgis_settings():
    # Keep it for a few months
    # 2023/04/15
    QgsSettings().remove("lizmap/instance_target_repository")
    # 04/01/2022
    QgsSettings().remove("lizmap/instance_target_url_authid")

    if as_boolean(os.getenv("LIZMAP_NORMAL_MODE")):
        QgsSettings().setValue(Settings.key(Settings.BeginnerMode), False)
        QgsSettings().setValue(Settings.key(Settings.PreventPgService), False)

    # Set some default settings when loading the plugin
    beginner_mode = QgsSettings().value(Settings.key(Settings.BeginnerMode), defaultValue=None)
    if beginner_mode is None:
        QgsSettings().setValue(Settings.key(Settings.BeginnerMode), True)

    prevent_ecw = QgsSettings().value(Settings.key(Settings.PreventEcw), defaultValue=None)
    if prevent_ecw is None:
        QgsSettings().setValue(Settings.key(Settings.PreventEcw), True)

    prevent_auth_id = QgsSettings().value(Settings.key(Settings.PreventPgAuthDb), defaultValue=None)
    if prevent_auth_id is None:
        QgsSettings().setValue(Settings.key(Settings.PreventPgAuthDb), True)

    prevent_service = QgsSettings().value(Settings.key(Settings.PreventPgService), defaultValue=None)
    if prevent_service is None:
        QgsSettings().setValue(Settings.key(Settings.PreventPgService), True)

    force_pg_user_pass = QgsSettings().value(Settings.key(Settings.ForcePgUserPass), defaultValue=None)
    if force_pg_user_pass is None:
        QgsSettings().setValue(Settings.key(Settings.ForcePgUserPass), True)

    prevent_other_drive = QgsSettings().value(Settings.key(Settings.PreventDrive), defaultValue=None)
    if prevent_other_drive is None:
        QgsSettings().setValue(Settings.key(Settings.PreventDrive), True)

    allow_parent_folder = QgsSettings().value(Settings.key(Settings.AllowParentFolder), defaultValue=None)
    if allow_parent_folder is None:
        QgsSettings().setValue(Settings.key(Settings.AllowParentFolder), False)

    parent_folder = QgsSettings().value(Settings.key(Settings.NumberParentFolder), defaultValue=None)
    if parent_folder is None:
        QgsSettings().setValue(Settings.key(Settings.NumberParentFolder), 2)
