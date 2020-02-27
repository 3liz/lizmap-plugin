"""Tools about version."""

from .resources import metadata_config


def version() -> str:
    """Return the version defined in metadata.txt."""
    return metadata_config()['general']['version']


def is_dev_version() -> bool:
    """Return if the plugin is in a dev version."""
    is_dev = version().find('-beta') != -1
    return is_dev
