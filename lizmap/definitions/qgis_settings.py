"""Definitions for QgsSettings."""

# TODO, use the settings API from QGIS 3.30 etc
# Mail QGIS-Dev 24/10/2023

__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

KEY = 'lizmap'


class Settings:

    @classmethod
    def key(cls, key):
        return KEY + '/' + key

    PreventEcw = 'prevent_ecw'
    PreventPgAuthId = 'prevent_pg_auth_id'
    PreventPgService = 'prevent_pg_service'
    ForcePgUserPass = 'force_pg_user_password'
    PreventNetworkDrive = 'prevent_network_drive'
    AllowParentFolder = 'allow_parent_folder'
    NumberParentFolder = 'number_parent_folder'
    BeginnerMode = 'beginner_mode'
