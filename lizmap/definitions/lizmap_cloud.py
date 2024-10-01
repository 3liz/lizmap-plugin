__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

CLOUD_DOMAIN = 'lizmap.com'
CLOUD_NAME = 'Lizmap Cloud'
CLOUD_MAX_PARENT_FOLDER = 2

CLOUD_ONLINE_URL = 'https://docs.lizmap.cloud'
CLOUD_ONLINE_LANGUAGES = ('en', 'fr')

# TODO Fixme, the minimum version recommended varies on the LWC version
CLOUD_QGIS_MIN_RECOMMENDED = (3, 28, 0)

UPLOAD_EXTENSIONS = ('fgb', 'gpkg', 'xlsx', 'xls', 'csv', 'ods', 'kml', 'geojson')
UPLOAD_MAX_SIZE = 11000000  # 11 Mb

# Excluded domains from Plausible
EXCLUDED_DOMAINS = ('demo.snap.lizmap.com', 'demo.lizmap.com', 'localhost:8130', )
# Domains which are designed for workshops
# For the "Training" panel and excluded from Plausible as well
WORKSHOP_DOMAINS = ('workshop.lizmap.com', 'formation.lizmap.com', )

# When the folder for storing QGS files is already created before the workshop
WORKSHOP_FOLDER_ID = 'themeurbanism'
WORKSHOP_FOLDER_PATH = 'theme_urbanism'
# Name of the ZIP in the "qgis/" folder in one of these servers
TRAINING_ZIP = 'training.zip'
TRAINING_PROJECT = "demo.qgs"


class WorkshopType:
    IndividualQgsFile = 'IndividualQgsFile'
    ZipFile = 'ZipFile'
