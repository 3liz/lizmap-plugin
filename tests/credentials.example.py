__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import os

# Edit the default value in the getenv function if not using environment variable
# Or make your own way to retrieve credentials :)

# For WebDav tests
LIZMAP_HOST_WEB = os.getenv("LIZMAP_HOST_WEB", "")
LIZMAP_HOST_DAV = os.getenv("LIZMAP_HOST_DAV", "")
LIZMAP_USER = os.getenv("LIZMAP_USER", "")
LIZMAP_PASSWORD = os.getenv("LIZMAP_PASSWORD", "")

# For PostgreSQL tests
PG_HOST = os.getenv("PG_HOST", "")
PG_PORT = os.getenv("PG_PORT", "")
PG_USER = os.getenv("PG_USER", "")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")
PG_DATABASE = os.getenv("PG_DATABASE", "")
