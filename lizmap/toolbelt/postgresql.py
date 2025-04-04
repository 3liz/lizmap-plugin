""" Helper for PostgreSQL. """

__copyright__ = 'Copyright 2025, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'


def generate_service_content(
        service: str = None,
        host: str = None,
        user: str = None,
        password: str = None,
        db_name: str = None,
        port: str = None,
) -> str:
    """ Generate the content for a service. """
    if not service:
        service = "YOUR_SERVICE_NAME_RANDOM_STRING"

    if not host:
        host = "qgisdb-something.lizmap.com"

    if not port:
        port = "5432"

    if not user:
        user = "USER@INSTANCE_NAME"

    if not db_name:
        db_name = "INSTANCE_NAME"

    if not password:
        password = "PASSWORD"

    template = f"[{service}]\n"
    template += f"host={host}\n"
    template += f"port={port}\n"
    template += f"dbname={db_name}\n"
    template += f"user={user}\n"
    template += f"password={password}\n"
    return template
