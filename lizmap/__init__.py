__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

try:
    # noinspection PyPep8Naming
    def classFactory(iface):
        from lizmap.plugin import Lizmap
        return Lizmap(iface)

except ImportError:
    # We may not have this package when running on a server.
    pass
